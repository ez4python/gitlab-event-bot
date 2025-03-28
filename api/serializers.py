from rest_framework import serializers
from apps.models import GitLabEvent


class GitLabWebhookSerializer(serializers.ModelSerializer):
    gitlab_event = serializers.ChoiceField(choices=GitLabEvent.EVENT_CHOICES)

    class Meta:
        model = GitLabEvent
        fields = ['gitlab_event', 'project_name', 'status', 'branch', 'user_name', 'duration']
