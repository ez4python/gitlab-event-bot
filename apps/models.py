from django.db import models


class GitlabProject(models.Model):
    name = models.CharField(max_length=255, unique=True)

    telegram_group = models.ForeignKey(
        'apps.TelegramGroup',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='projects'
    )

    show_user = models.BooleanField(default=True)
    show_project = models.BooleanField(default=True)
    show_branch = models.BooleanField(default=True)
    show_status = models.BooleanField(default=True)
    show_duration = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'gitlab_projects'
        verbose_name = 'Project'
        verbose_name_plural = 'Projects'


class GitlabUser(models.Model):
    gitlab_username = models.CharField(max_length=255, unique=True)
    telegram_id = models.CharField(max_length=50)
    projects = models.ManyToManyField('apps.GitlabProject', related_name='users')

    def __str__(self):
        return self.gitlab_username

    class Meta:
        db_table = 'gitlab_users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'


class GitLabEvent(models.Model):
    EVENT_CHOICES = (
        ('push', 'Push'),
        ('merge', 'Merge Request'),
        ('pipeline', 'Pipeline'),
    )

    gitlab_event = models.CharField(max_length=20, choices=EVENT_CHOICES)
    project = models.ForeignKey('apps.GitlabProject', on_delete=models.CASCADE, related_name='events')
    status = models.CharField(max_length=50)
    branch = models.CharField(max_length=100)
    user_name = models.CharField(max_length=255)
    duration = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.gitlab_event} - {self.project.name} - {self.user_name}"

    class Meta:
        verbose_name = 'Event'
        verbose_name_plural = 'Events'
        db_table = 'gitlab_events'


class TelegramAdmin(models.Model):
    telegram_id = models.BigIntegerField(unique=True)
    full_name = models.CharField(max_length=255)
    username = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} (@{self.username})"

    class Meta:
        verbose_name = 'TelegramAdmin'
        verbose_name_plural = 'TelegramAdmins'
        db_table = 'telegram_admins'


class TelegramGroup(models.Model):
    chat_id = models.BigIntegerField(unique=True)
    chat_name = models.CharField(max_length=255)
    chat_type = models.CharField(max_length=50)
    username = models.CharField(max_length=255, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    is_forum = models.BooleanField(default=False)
    message_thread_id = models.BigIntegerField(blank=True, null=True)
    message_thread_name = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=False)
    registered_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.chat_name} ({self.chat_id})"

    class Meta:
        verbose_name = 'Telegram Group'
        verbose_name_plural = 'Telegram Groups'
        db_table = 'telegram_groups'
