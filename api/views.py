import requests
from django.core.cache import cache
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
from root.settings import TELEGRAM_BOT_TOKEN, BOT_USERNAME, PROJECT_URL


@extend_schema(
    request=GitLabEventSerializer,
    methods=['POST'],
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
            # todo
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
    methods=['POST'],
    description="Telegram webhook endpoint for '/start, /stop, /register' commands.",
    responses={200: dict}
)
class TelegramWebhookAPIView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        try:
            serializer = TelegramWebhookSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data

            message = data.get('message') or data.get('edited_message')
            text = message.get('text', '').strip()
            telegram_user = message.get('from', {})
            telegram_id = telegram_user.get('id')

            chat_type = message['chat'].get('type', '')

            if chat_type == 'private':
                if cache.get(f'waiting_username_{telegram_id}'):
                    gitlab_username = text

                    # looking for telegram_id
                    if GitlabUser.objects.filter(telegram_id=telegram_id).exists():
                        bot_answer(telegram_id, "ℹ️ Siz allaqachon ro'yxatdan o'tgansiz.")
                        cache.delete(f'waiting_username_{telegram_id}')
                        return Response({'status': 'already registered'}, status=status.HTTP_200_OK)

                    # looking ofr gitlab_username
                    if GitlabUser.objects.filter(gitlab_username=gitlab_username).exists():
                        bot_answer(telegram_id, "❗️Bu GitLab username allaqachon ishlatilgan.")
                        cache.delete(f'waiting_username_{telegram_id}')
                        return Response({'status': 'username taken'}, status=status.HTTP_200_OK)

                    GitlabUser.objects.create(
                        gitlab_username=gitlab_username,
                        telegram_id=telegram_id
                    )
                    bot_answer(telegram_id, "✅ Ro'yxatdan muvaffaqiyatli o'tdingiz!")
                    cache.delete(f'waiting_username_{telegram_id}')
                    return Response({'status': 'registered'}, status=status.HTTP_200_OK)

                if text == '/start':
                    cache.set(f'waiting_username_{telegram_id}', True, timeout=300)
                    bot_answer(telegram_id, "🔑 Iltimos, GitLab username'ingizni yuboring.")
                    return Response({'status': 'asking for username'}, status=status.HTTP_200_OK)

            is_admin = TelegramAdmin.objects.filter(telegram_id=telegram_id).exists()
            if not is_admin:
                return Response({'status': 'unauthorized'}, status=status.HTTP_200_OK)

            group_info = parse_group_info(message)

            if not group_info:
                return Response({'status': 'not a group chat or not a valid bot command'},
                                status=status.HTTP_200_OK)

            if text.startswith('/register'):
                TelegramGroup.objects.update_or_create(
                    chat_id=group_info['chat_id'],
                    defaults=group_info
                )
                bot_answer(group_info['chat_id'], "✅ Guruh muvaffaqiyatli ro'yxatdan o'tkazildi.")
                return Response({'status': 'registered'}, status=status.HTTP_200_OK)

            elif text.startswith('/start'):
                bot_answer(group_info['chat_id'], "🤖 Bot ishga tushdi.")
                return Response({'status': 'started'}, status=status.HTTP_200_OK)

            elif text.startswith('/stop'):
                bot_answer(group_info['chat_id'], "🛑 Bot to‘xtatildi.")
                return Response({'status': 'stopped'}, status=status.HTTP_200_OK)

            return Response({'status': 'unknown command'}, status=status.HTTP_200_OK)

        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({'error': str(e)}, status=status.HTTP_200_OK)


@method_decorator(csrf_exempt, name='dispatch')
@extend_schema(
    request=None,
    methods=['POST'],
    description="Telegram bot uchun webhook URL ni o'rnatadi.",
    responses={200: dict}
)
class SetWebhookAPIView(APIView):
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        try:
            webhook_url = f"{PROJECT_URL}/api/telegram/webhook/"
            telegram_api_url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook"

            response = requests.post(telegram_api_url, data={'url': webhook_url})

            if response.ok:
                return Response({"message": "Webhook o'rnatildi!"}, status=status.HTTP_200_OK)

            return Response(
                {"error": f"Xatolik yuz berdi: {response.text}"},
                status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_200_OK)
