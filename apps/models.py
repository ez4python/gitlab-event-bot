from django.db import models


class GitLabEvent(models.Model):
    EVENT_TYPES = [
        ('push', 'Push'),
        ('merge_request', 'Merge Request'),
        ('pipeline', 'Pipeline'),
    ]

    event_type = models.CharField(max_length=100, choices=EVENT_TYPES)
    project_name = models.CharField(max_length=255)
    user_name = models.CharField(max_length=255)
    event_data = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.event_type} by {self.user_name} on {self.project_name}"
