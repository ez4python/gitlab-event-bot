import time

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
from api.utils import save_telegram_message_id, get_telegram_message_id, delete_telegram_message_id, parse_group_info, \
    get_gitlab_mention
from apps.models import GitlabProject, GitlabUser, TelegramAdmin, TelegramGroup
from root.settings import TELEGRAM_BOT_TOKEN, PROJECT_URL


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
                return Response({'error': 'Missing project name in payload'}, status=status.HTTP_200_OK)

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
                object_attributes = payload.get('object_attributes', {})
                branch = object_attributes.get('source_branch')
                status_text = object_attributes.get('state')
                user = payload.get('user', {})
                user_name = user.get('username')
                user_id = user.get('id')
                gitlab_event = 'merge'
                merge_url = object_attributes.get('url')
                full_name = payload.get('user', {}).get('name')
                target_branch = object_attributes.get('target_branch')
                draft = object_attributes.get('draft')
                assignees = ({
                    'id': assignee.get('id'),
                    'name': assignee.get('name'),
                    'username': assignee.get('username')
                } for assignee in payload.get('assignees', []))
                reviewers = ({
                    'id': reviewer.get('id'),
                    'name': reviewer.get('name'),
                    'username': reviewer.get('username')
                } for reviewer in payload.get('reviewers', []))
                event_id = object_attributes.get('id')
                action = object_attributes.get('action')

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
                event_id = attr.get('id')

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
            chat_id = project.telegram_group.chat_id
            thread_id = project.telegram_group.message_thread_id

            if gitlab_event in ['merge', 'pipeline']:
                event_key = f"{event_id}:{gitlab_event}:{branch}"

            user = GitlabUser.objects.filter(gitlab_id=user_id).first()
            mention = f"[{full_name}](tg://user?id={user.telegram_id})" if user else full_name

            message = f"🚀 *Event Update:* `{event_type}`\n"
            status_emoji_map = {
                'pushed': '✅',
                'opened': '✨',
                'pending': '⏳',
                'running': '🏃',
                'success': '🟢',
                'failed': '🔴',
                'canceled': '⚪',
                'skipped': '⏭️',
                'finished': '🏁',
                'manual': '✋',
                'approved': '👍',
                'unapproved': '👎',
                'approval': '✅',
                'unapproval': '❌',
                'merge': '🤝',
                'pipeline started': '⏱️',
                'open': '🔓',
                'close': '🔒',
                'reopen': '🔄',
                'update': '📝',
                'closed': '🔒',
            }
            status_with_emoji = f"{status_text} {status_emoji_map.get(status_text, '')}"

            if gitlab_event in ['push', 'pipeline']:
                if project.show_project:
                    message += f"📣 *Project:* `{project.name}`\n"
                if project.show_status:
                    message += f"📌 *Status:* `{status_with_emoji}`\n"
                if project.show_branch:
                    message += f"🌿 *Branch:* `{branch}`\n"
                if project.show_user:
                    message += f"👤 *User:* {mention}\n"
                if project.show_duration:
                    message += f"⏳ *Duration:* `{event_data['duration']}s`\n"

            if gitlab_event == 'merge':

                assignee_mentions = [
                    get_gitlab_mention(a.get('id'), a.get('name')) for a in assignees
                ]
                reviewer_mentions = [
                    get_gitlab_mention(r.get('id'), r.get('name')) for r in reviewers
                ]

                if project.show_project:
                    message += f"📣 *Project:* `{project.name}`\n"
                    message += f"📑 *Is Draft:* `{draft}`\n"
                if project.show_status:
                    message += f"📌 *Status:* `{status_with_emoji}`\n"
                if project.show_branch:
                    message += f"🌿 *Source:* `{branch}`\n"
                    message += f"🎯 *Target:* `{target_branch}`\n"
                if project.show_user:
                    message += f"👤 *User:* {mention}\n"
                    if assignee_mentions:
                        message += "👥 *Assignees*\n"
                        for assignee in assignee_mentions:
                            message += f"  • {assignee}\n"
                    if reviewer_mentions:
                        message += "👁 *Reviewers:*\n"
                        for reviewer in reviewer_mentions:
                            message += f"  • {reviewer}\n"
                message += f"🔗 *Link:* [tap to view]({merge_url})\n"

                if project.show_duration:
                    message += f"⏳ *Duration:* `{event_data['duration']}s`\n"

            # decide whether to update or send new message
            update_statuses = ['created', 'push', 'opened', 'pipeline started', 'pending', 'running', 'open',
                               'close', 'reopen', 'update', 'approved', 'unapproved', 'approval', 'unapproval']
            final_statuses = ['success', 'failed', 'canceled', 'skipped', 'finished', 'manual', 'merge']

            if gitlab_event == 'merge':
                event_key = f"{event_id}:{gitlab_event}:{branch}"
                msg_id = get_telegram_message_id(event_key)
                if msg_id:
                    edit_message(chat_id, int(msg_id), message)
                    if status_text in final_statuses or action == 'merge':
                        delete_telegram_message_id(event_key)
                else:
                    msg = send_message(chat_id, thread_id, message)
                    save_telegram_message_id(event_key, msg['message_id'])
                    if status_text in final_statuses or action == 'merge':
                        delete_telegram_message_id(event_key)
                time.sleep(0.5)
            elif gitlab_event == 'pipeline':
                cached_status = cache.get(f"pipeline_status:{event_key}")

                if status_text == 'pending':
                    cache.set(f"pipeline_status:{event_key}", {'status': status_text, 'duration': 0}, timeout=60)
                    return Response({'status': 'pending status cached'}, status=status.HTTP_200_OK)
                elif cached_status and cached_status['status'] == 'pending' and status_text in ['running', 'success',
                                                                                                'failed', 'canceled',
                                                                                                'skipped', 'finished',
                                                                                                'manual']:
                    cached_data = cache.get(f"pipeline_status:{event_key}")
                    pending_message = f"🚀 *Event Update:* `Pipeline Hook`\n"
                    if project.show_project:
                        pending_message += f"📣 *Project:* `{project.name}`\n"
                    if project.show_status:
                        pending_message += f"📌 *Status:* `pending` {status_emoji_map.get('pending', '')}\n"
                    if project.show_branch:
                        pending_message += f"🌿 *Branch:* `{branch}`\n"
                    if project.show_user:
                        pending_message += f"👤 *User:* {mention}\n"
                    if project.show_duration and cached_data and 'duration' in cached_data:
                        pending_message += f"⏳ *Duration:* `{cached_data['duration']}s`\n"

                    # Endi yangi statusni qo'shamiz
                    updated_message = f"{pending_message.rstrip()}\n📌 *Status:* `{status_with_emoji}`"
                    if project.show_duration:
                        updated_message += f"\n⏳ *Duration:* `{event_data['duration']}s`"

                    msg_id = get_telegram_message_id(event_key)
                    if msg_id:
                        edit_message(chat_id, int(msg_id), updated_message)
                    else:
                        msg = send_message(chat_id, thread_id, updated_message)
                        save_telegram_message_id(event_key, msg['message_id'])
                    cache.delete(f"pipeline_status:{event_key}")
                    return Response({'status': f'pending and {status_text} sent'}, status=status.HTTP_200_OK)
                else:
                    msg_id = get_telegram_message_id(event_key)
                    if msg_id:
                        edit_message(chat_id, int(msg_id), message)
                    else:
                        msg = send_message(chat_id, thread_id, message)
                        save_telegram_message_id(event_key, msg['message_id'])
                    return Response({'status': f'{status_text} sent'}, status=status.HTTP_200_OK)
            elif gitlab_event == 'push':
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
                if cache.get(f'waiting_id_{telegram_id}') and text != '/start':

                    if text.isdigit():
                        # looking for telegram_id
                        if GitlabUser.objects.filter(telegram_id=telegram_id).exists():
                            bot_answer(telegram_id, "ℹ️ Siz allaqachon ro'yxatdan o'tgansiz.")
                            cache.delete(f'waiting_id_{telegram_id}')
                            return Response({'status': 'already registered'}, status=status.HTTP_200_OK)

                        # looking for gitlab_id
                        if GitlabUser.objects.filter(gitlab_id=text).exists():
                            bot_answer(telegram_id, "❗️Bu GitLab ID allaqachon ishlatilgan.")
                            cache.delete(f'waiting_id_{telegram_id}')
                            return Response({'status': 'gitlab_id taken'}, status=status.HTTP_200_OK)

                        GitlabUser.objects.create(
                            gitlab_id=text,
                            telegram_id=telegram_id
                        )
                        bot_answer(telegram_id, "✅ Ro'yxatdan muvaffaqiyatli o'tdingiz!")
                        cache.delete(f'waiting_id_{telegram_id}')
                        return Response({'status': 'registered'}, status=status.HTTP_200_OK)

                    return Response({'status': 'Gitlab ID must contain only digits!'})

                if text == '/start':
                    cache.set(f'waiting_id_{telegram_id}', True, timeout=300)
                    bot_answer(telegram_id, "🔑 Iltimos, GitLab ID'ingizni yuboring.")
                    return Response({'status': 'asking for gitlab_id'}, status=status.HTTP_200_OK)

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
                group_obj = TelegramGroup.objects.get(chat_id=group_info['chat_id'])
                if group_obj.is_active:
                    bot_answer(group_info['chat_id'], "🤖 Bot allaqachon ishga tushgan.")
                else:
                    TelegramGroup.objects.filter(chat_id=group_info['chat_id']).update(is_active=True)
                    bot_answer(group_info['chat_id'], "🤖 Bot ishga tushdi.")
                return Response({'status': 'started'}, status=status.HTTP_200_OK)

            elif text.startswith('/stop'):
                group_obj = TelegramGroup.objects.get(chat_id=group_info['chat_id'])
                if not group_obj.is_active:
                    TelegramGroup.objects.filter(chat_id=group_info['chat_id']).update(is_active=False)
                    bot_answer(group_info['chat_id'], "🛑 Bot to‘xtatildi.")
                else:
                    bot_answer(group_info['chat_id'], "🛑 Bot allaqachon to'xtatilgan.")
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
