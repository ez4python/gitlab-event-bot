from django.contrib import admin
from apps.models import GitlabProject, GitlabUser, GitLabEvent, TelegramGroup, TelegramAdmin


@admin.register(GitlabProject)
class GitlabProjectAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'telegram_group',
        'telegram_group_id',
        'show_user',
        'show_branch',
        'show_project',
        'show_duration',
        'show_status',
    )


@admin.register(GitlabUser)
class GitlabUserAdmin(admin.ModelAdmin):
    list_display = ('gitlab_username', 'telegram_id')
    filter_horizontal = ('projects',)


@admin.register(GitLabEvent)
class GitLabEventAdmin(admin.ModelAdmin):
    list_display = ('gitlab_event', 'project', 'user_name', 'status', 'created_at')


@admin.register(TelegramAdmin)
class TelegramAdminAdmin(admin.ModelAdmin):
    list_display = ('telegram_id', 'full_name', 'username', 'created_at')


@admin.register(TelegramGroup)
class TelegramGroupAdmin(admin.ModelAdmin):
    list_display = (
        'chat_id',
        'chat_name',
        'chat_type',
        'username',
        'message_thread_id',
        'message_thread_name',
        'registered_at',
    )
    search_fields = ('chat_name', 'chat_id', 'username')
