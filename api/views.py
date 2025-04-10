from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from api.bot import send_message, edit_message
from api.serializers import GitLabEventSerializer
from api.utils import save_telegram_message_id, get_telegram_message_id, delete_telegram_message_id
from apps.models import GitlabProject, GitlabUser


@extend_schema(
    request=GitLabEventSerializer,
    methods=["POST"],
    description="GitLab webhook endpoint (faqat push, merge-request va pipeline eventlar uchun).",
    responses={200: dict, 400: dict, 500: dict},
)
class GitLabWebhookView(APIView):
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
                status_text = 'pushed'
                gitlab_event = 'push'

            elif event_type == 'Merge Request Hook':
                attr = payload.get('object_attributes', {})
                branch = attr.get('source_branch')
                status_text = attr.get('state')
                user_name = payload.get('user', {}).get('username')
                gitlab_event = 'merge'

            elif event_type == 'Pipeline Hook':
                attr = payload.get('object_attributes', {})
                ref = attr.get('ref') or payload.get('ref')
                branch = ref.split('/')[-1] if ref else ''
                status_text = attr.get('status')
                user_name = payload.get('user', {}).get('username')
                gitlab_event = 'pipeline'

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
            event_key = f"{project.id}:{gitlab_event}:{branch}:{user_name}"

            user = GitlabUser.objects.filter(project=project, gitlab_username=user_name).first()
            mention = f"[{user_name}](tg://user?id={user.telegram_id})" if user else user_name

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
            update_statuses = ['push', 'opened', 'pipeline started', 'pending', 'running']
            final_statuses = ['success', 'failed', 'canceled', 'skipped', 'finished']

            if gitlab_event == 'pipeline' and status_text in update_statuses:
                msg_id = get_telegram_message_id(event_key)
                if msg_id:
                    edit_message(chat_id, int(msg_id), message)
                else:
                    msg = send_message(chat_id, thread_id, message)
                    save_telegram_message_id(event_key, msg['message_id'])
            elif gitlab_event == 'pipeline' and status_text in final_statuses:
                msg_id = get_telegram_message_id(event_key)
                edit_message(chat_id, int(msg_id), message)
                delete_telegram_message_id(event_key)
            else:
                send_message(chat_id, thread_id, message)

            return Response({'status': 'ok'}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
