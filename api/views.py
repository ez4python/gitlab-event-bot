import json
import logging
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from apps.models import GitLabEvent
from api.serializers import GitLabEventSerializer
from api.telegram_service import TelegramService
from api.gitlab_parser import GitLabEventParser

logger = logging.getLogger(__name__)


class GitLabWebhookView(APIView):
    """
    API view to handle GitLab webhook events and forward them to Telegram.
    Only accepts merge, push, and pipeline events.
    """

    # List of allowed event types
    ALLOWED_EVENT_TYPES = ['merge_request', 'push', 'pipeline']

    def post(self, request, format=None):
        # Verify GitLab webhook token if configured
        if settings.GITLAB_TOKEN:
            header_token = request.headers.get('X-Gitlab-Token')
            if not header_token or header_token != settings.GITLAB_TOKEN:
                logger.warning("Invalid GitLab webhook token")
                return Response({"error": "Invalid token"}, status=status.HTTP_403_FORBIDDEN)

        # Get event type from headers
        event_type = request.headers.get('X-Gitlab-Event')
        if not event_type:
            logger.warning("Missing GitLab event type header")
            return Response({"error": "Missing event type"}, status=status.HTTP_400_BAD_REQUEST)

        # Extract event type from header (e.g., "Push Hook" -> "push")
        event_type = event_type.lower().replace(' hook', '').replace(' event', '')

        # Check if the event type is allowed
        if event_type not in self.ALLOWED_EVENT_TYPES:
            logger.info(f"Ignoring unsupported event type: {event_type}")
            return Response(
                {"status": "ignored", "message": f"Event type '{event_type}' is not supported"},
                status=status.HTTP_200_OK
            )

        try:
            # Parse the event data
            event_data = request.data

            # Save the event to the database
            gitlab_event = GitLabEvent(
                event_type=event_type,
                project_name=event_data.get('project', {}).get('name', 'Unknown'),
                user_name=event_data.get('user_name') or event_data.get('user', {}).get('name', 'Unknown'),
                event_data=event_data
            )
            gitlab_event.save()

            # Parse the event into a formatted message
            message = GitLabEventParser.parse_event(event_type, event_data)

            # Determine the topic ID based on the project or event type
            # For simplicity, we'll use a fixed topic ID from settings
            # In a real application, you might want to map projects to specific topics
            topic_id = 1  # Default topic ID

            # Send the message to Telegram
            telegram_service = TelegramService()
            sent = telegram_service.send_message(topic_id, message)

            if sent:
                logger.info(f"Successfully sent {event_type} event to Telegram")
                return Response({"status": "success", "message": "Event processed and sent to Telegram"})
            else:
                logger.error(f"Failed to send {event_type} event to Telegram")
                return Response(
                    {"status": "error", "message": "Failed to send event to Telegram"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except Exception as e:
            logger.exception(f"Error processing GitLab webhook: {e}")
            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
