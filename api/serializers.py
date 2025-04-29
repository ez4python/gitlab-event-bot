from rest_framework import serializers

from apps.models import GitLabEvent, GitlabProject, TelegramAdmin


class GitLabEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = GitLabEvent
        fields = [
            'gitlab_event',
            'project',
            'status',
            'branch',
            'user_name',
            'duration',
            'created_at'
        ]

    def validate(self, data):
        project = GitlabProject.objects.filter(name=data.get('project').name).first()
        if not project:
            raise serializers.ValidationError("Project not found.")

        data['project'] = project
        return data


class TelegramWebhookSerializer(serializers.Serializer):
    # message = serializers.DictField(
    #     child=serializers.CharField(),
    #     required=True,
    #     allow_null=False,
    # )
    # telegram_user = serializers.DictField(
    #     child=serializers.CharField(),
    #     required=False,
    #     allow_null=False,
    # )
    # text = serializers.CharField(required=False)
    # telegram_id = serializers.IntegerField(required=False)
    # username = serializers.CharField(required=False)
    #
    # def validate(self, data):
    #     telegram_id = data.get('telegram_id')
    #     text = data.get('text')
    #
    #     if not telegram_id or not text:
    #         raise serializers.ValidationError("Missing telegram id or text")
    #
    #     if not TelegramAdmin.objects.filter(telegram_id=telegram_id).exists():
    #         raise serializers.ValidationError("Unauthorized")
    #
    #     return data
    message = serializers.DictField(required=False)
    edited_message = serializers.DictField(required=False)

    def validate(self, data):
        if not data.get('message') and not data.get('edited_message'):
            raise serializers.ValidationError("Missing both message and edited_message.")
        return data
