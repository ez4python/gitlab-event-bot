from rest_framework.views import APIView
from rest_framework.response import Response
from django.conf import settings
import requests

from api.serializers import GitLabWebhookSerializer
from apps.models import WebhookSettings, GitLabEvent

TELEGRAM_URL = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"


class GitLabWebhookView(APIView):
    def post(self, request):
        x_gitlab_event = request.headers.get("X-Gitlab-Event", "Unknown Event")
        data = {
            "x_gitlab_event": x_gitlab_event,
            "project_name": request.data.get("project", {}).get("name", ""),
            "status": request.data.get("object_attributes", {}).get("status", ""),
            "branch": request.data.get("object_attributes", {}).get("ref", ""),
            "user_name": request.data.get("user", {}).get("name", ""),
            "duration": request.data.get("object_attributes", {}).get("duration"),
        }

        serializer = GitLabWebhookSerializer(data=data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        settings = WebhookSettings.objects.first()
        if not settings:
            return Response({"error": "Webhook settings not found"}, status=400)

        event = GitLabEvent.objects.create(**serializer.validated_data)

        message = f"*🚀 Event Update:* `{x_gitlab_event}`\n"

        if settings.show_project and event.project_name:
            message += f" *🎯 Project:* `{event.project_name}`\n"
        if settings.show_status and event.status:
            message += f" *📌 Status:* `{event.status}`\n"
        if settings.show_branch and event.branch:
            message += f" *🌿 Branch:* `{event.branch}`\n"
        if settings.show_user and event.user_name:
            message += f" *👤 User:* `{event.user_name}`\n"
        if settings.show_duration and event.duration is not None:
            message += f" *⏳ Duration:* `{event.duration}` sec\n"

        payload = {
            "chat_id": settings.chat_id,
            "message_thread_id": settings.message_thread_id,
            "text": f"*📢 Topic: {settings.topic if settings.topic else 'General'}*\n\n{message}",
            "parse_mode": "MarkdownV2"
        }
        requests.post(TELEGRAM_URL, json=payload)

        return Response({"status": "ok"})
