from rest_framework import serializers

from apps.models import GitLabEvent


class GitLabEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = GitLabEvent
        fields = '__all__'
