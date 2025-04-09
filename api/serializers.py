from rest_framework import serializers

from apps.models import GitLabEvent, GitlabProject


class GitLabEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = GitLabEvent
        fields = ['gitlab_event', 'project', 'status', 'branch', 'user_name', 'duration', 'created_at']

    def validate(self, data):
        """
        check the project name coming from the webhook

        :param data: gitlab-event-model fields
        :return: project-data
        """
        project = GitlabProject.objects.filter(name=data.get('project').name).first()
        if not project:
            raise serializers.ValidationError("Project not found.")

        data['project'] = project
        return data
