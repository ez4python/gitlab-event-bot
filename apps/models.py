from django.db import models

from django.db import models


class GitlabProject(models.Model):
    name = models.CharField(max_length=255)

    telegram_chat_id = models.CharField(max_length=50, blank=True, null=True)
    telegram_message_thread_id = models.IntegerField(blank=True, null=True)
    show_user = models.BooleanField(default=True)
    show_project = models.BooleanField(default=True)
    show_branch = models.BooleanField(default=True)
    show_status = models.BooleanField(default=True)
    show_duration = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class ProjectUser(models.Model):
    project = models.ForeignKey(to='apps.GitlabProject', on_delete=models.CASCADE, related_name='users')
    gitlab_username = models.CharField(max_length=255)
    telegram_id = models.CharField(max_length=50)

    def __str__(self):
        return f"{self.gitlab_username} ({self.project.name})"


class GitLabEvent(models.Model):
    EVENT_CHOICES = (
        ('push', 'Push'),
        ('merge', 'Merge Request'),
        ('pipeline', 'Pipeline'),
    )

    gitlab_event = models.CharField(max_length=20, choices=EVENT_CHOICES)
    project = models.ForeignKey(to='apps.GitlabProject', on_delete=models.CASCADE, related_name='events')
    status = models.CharField(max_length=50)
    branch = models.CharField(max_length=100)
    user_name = models.CharField(max_length=255)
    duration = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.gitlab_event} - {self.project.name} - {self.user_name}"
