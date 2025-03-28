from django.db import models


class WebhookSettings(models.Model):
    chat_id = models.CharField(max_length=50)
    message_thread_id = models.IntegerField()
    topic = models.CharField(max_length=100, blank=True, null=True)

    show_project = models.BooleanField(default=True)
    show_status = models.BooleanField(default=True)
    show_branch = models.BooleanField(default=True)
    show_user = models.BooleanField(default=True)
    show_duration = models.BooleanField(default=True)

    def __str__(self):
        return f"Webhook Settings ({self.chat_id} - {self.topic if self.topic else 'No Topic'})"

    class Meta:
        db_table = 'webhook_settings'


class GitLabEvent(models.Model):
    EVENT_CHOICES = [
        ('push', 'Push Hook'),
        ('merge_request', 'Merge Request Hook'),
        ('pipeline', 'Pipeline Hook'),
    ]

    gitlab_event = models.CharField(max_length=20, choices=EVENT_CHOICES)
    project_name = models.CharField(max_length=255)
    status = models.CharField(max_length=50)
    branch = models.CharField(max_length=100)
    user_name = models.CharField(max_length=255)
    duration = models.IntegerField()

    def __str__(self):
        return f"{self.gitlab_event} - {self.project_name}"
