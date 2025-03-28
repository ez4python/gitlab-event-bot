from django.contrib import admin
from .models import WebhookSettings, GitLabEvent


class WebhookSettingsAdmin(admin.ModelAdmin):
    list_display = (
        'chat_id',
        'message_thread_id',
        'topic',
        'show_project',
        'show_status',
        'show_branch',
        'show_user',
        'show_duration'
    )
    list_editable = (
        'message_thread_id',
        'topic',
        'show_project',
        'show_status',
        'show_branch',
        'show_user',
        'show_duration'
    )


admin.site.register(WebhookSettings, WebhookSettingsAdmin)
admin.site.register(GitLabEvent)
