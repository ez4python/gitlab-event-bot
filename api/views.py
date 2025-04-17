import requests
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from api.bot import send_message, edit_message, bot_answer
from api.serializers import GitLabEventSerializer, TelegramWebhookSerializer
from api.utils import save_telegram_message_id, get_telegram_message_id, delete_telegram_message_id, parse_group_info
from apps.models import GitlabProject, GitlabUser, TelegramAdmin, TelegramGroup
from root.settings import TELEGRAM_BOT_TOKEN, BOT_USERNAME


@extend_schema(
    request=GitLabEventSerializer,
    methods=["POST"],
    description="GitLab webhook endpoint (faqat push, merge-request va pipeline eventlar uchun).",
    responses={200: dict, 400: dict, 500: dict},
)
class GitlabWebhookAPIView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        try:
            event_type = request.headers.get('X-Gitlab-Event')
            payload = request.data

            if event_type not in ['Push Hook', 'Merge Request Hook', 'Pipeline Hook']:
                return Response({'status': 'ignored'}, status=status.HTTP_200_OK)

            # get project name directly from payload
            project_name = payload.get('project', {}).get('name')
            if not project_name:
                return Response({'error': 'Missing project name in payload'}, status=status.HTTP_400_BAD_REQUEST)

            # get or create project
            project, created = GitlabProject.objects.get_or_create(name=project_name)
            if created:
                project.webhook_chat_id = ""
                project.webhook_message_thread_id = None
                project.save()

            # parse event info
            if event_type == 'Push Hook':
                branch = payload.get('ref', '').split('/')[-1]
                user_name = payload.get('user_username')
                user_id = payload.get('user_id')
                status_text = 'pushed'
                gitlab_event = 'push'
                full_name = payload.get('user_name', '')

            elif event_type == 'Merge Request Hook':
                attr = payload.get('object_attributes', {})
                branch = attr.get('source_branch')
                status_text = attr.get('state')
                user = payload.get('user', {})
                user_name = user.get('username')
                user_id = user.get('id')
                gitlab_event = 'merge'
                full_name = payload.get('user', {}).get('name')

            elif event_type == 'Pipeline Hook':
                attr = payload.get('object_attributes', {})
                ref = attr.get('ref') or payload.get('ref')
                branch = ref.split('/')[-1] if ref else ''
                status_text = attr.get('status')
                user = payload.get('user', {})
                user_name = user.get('username')
                user_id = user.get('id')
                gitlab_event = 'pipeline'
                full_name = payload.get('user', {}).get('name')

            else:
                return Response({'status': 'ignored'}, status=status.HTTP_200_OK)

            event_data = {
                'gitlab_event': gitlab_event,
                'project': project.id,
                'status': status_text,
                'branch': branch,
                'user_name': user_name,
                'duration': payload.get('object_attributes', {}).get('duration', 0),
            }

            serializer = GitLabEventSerializer(data=event_data)
            if serializer.is_valid():
                serializer.save()
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

            # prepare telegram message
            chat_id = project.telegram_chat_id
            thread_id = project.telegram_message_thread_id
            event_key = f"{project.id}:{gitlab_event}:{branch}:{user_id}"

            user = GitlabUser.objects.filter(projects=project, gitlab_username=user_name).first()
            mention = f"[`{full_name}`](tg://user?id={user.telegram_id})" if user else full_name

            message = f"🚀 *Event Update:* `{event_type}`\n"
            if project.show_project:
                message += f"🎯 *Project:* `{project.name}`\n"
            if project.show_status:
                message += f"📌 *Status:* `{status_text}`\n"
            if project.show_branch:
                message += f"🌿 *Branch:* `{branch}`\n"
            if project.show_user:
                message += f"👤 *User:* {mention}\n"
            if project.show_duration:
                message += f"⏳ *Duration:* `{event_data['duration']}s`\n"

            # decide whether to update or send new message
            update_statuses = ['created', 'push', 'opened', 'pipeline started', 'pending', 'running']
            final_statuses = ['success', 'failed', 'canceled', 'skipped', 'finished', 'manual']

            if gitlab_event == 'pipeline' and status_text in update_statuses:
                msg_id = get_telegram_message_id(event_key)
                if msg_id:
                    edit_message(chat_id, int(msg_id), message)
                else:
                    msg = send_message(chat_id, thread_id, message)
                    save_telegram_message_id(event_key, msg['message_id'])
            elif gitlab_event == 'pipeline' and status_text in final_statuses:
                msg_id = get_telegram_message_id(event_key)
                if msg_id:
                    edit_message(chat_id, int(msg_id), message)
                    delete_telegram_message_id(event_key)
            else:
                send_message(chat_id, thread_id, message)

            return Response({'status': 'ok'}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(csrf_exempt, name='dispatch')
@extend_schema(
    request=TelegramWebhookSerializer,
    methods=["POST"],
    description="Telegram webhook endpoint for '/start, /stop, /register' commands.",
    responses={200: dict, 403: dict, 400: dict}
)
class TelegramWebhookAPIView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        try:
            data = request.data

            message = data.get('message') or data.get('edited_message')
            if not message:
                return Response({'status': 'no message'}, status=status.HTTP_400_BAD_REQUEST)

            text = message.get('text', '').strip()
            telegram_user = message.get('from', {})
            telegram_id = telegram_user.get('id')
            username = telegram_user.get('username')
            print(text)

            if not telegram_id or not text:
                return Response({'status': 'missing telegram id or text'}, status=status.HTTP_400_BAD_REQUEST)

            is_admin = TelegramAdmin.objects.filter(telegram_id=telegram_id).exists()
            if not is_admin:
                return Response({'status': 'unauthorized'}, status=status.HTTP_403_FORBIDDEN)

            group_info = parse_group_info(message)
            if not group_info:
                return Response({'status': 'not a group chat or not a valid bot command'},
                                status=status.HTTP_400_BAD_REQUEST)

            if text == f'/register{BOT_USERNAME}':
                TelegramGroup.objects.update_or_create(
                    chat_id=group_info['chat_id'],
                    defaults=group_info
                )
                bot_answer(group_info['chat_id'], "✅ Guruh muvaffaqiyatli ro'yxatdan o'tkazildi.")
                return Response({'status': 'registered'}, status=status.HTTP_200_OK)

            elif text == f'/start{BOT_USERNAME}':
                bot_answer(group_info['chat_id'], "🤖 Bot ishga tushdi.")
                return Response({'status': 'started'}, status=status.HTTP_200_OK)

            elif text == f'/stop{BOT_USERNAME}':
                bot_answer(group_info['chat_id'], "🛑 Bot to‘xtatildi.")
                return Response({'status': 'stopped'}, status=status.HTTP_200_OK)

            else:
                return Response({'status': 'unknown command'}, status=status.HTTP_200_OK)

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@csrf_exempt
def set_webhook(request):
    ngrok_url = 'https://a81f-195-158-16-45.ngrok-free.app/'

    response = requests.post(
        f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook',
        data={'url': ngrok_url + 'api/telegram/webhook/'}
    )

    if response.status_code == 200:
        return HttpResponse("Webhook o'rnatildi!", status=200)
    else:
        return HttpResponse(f"Xatolik yuz berdi: {response.text}", status=400)
