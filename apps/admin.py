from django.contrib import admin
from apps.models import GitLabEvent


@admin.register(GitLabEvent)
class GitLabEventAdmin(admin.ModelAdmin):
    list_display = ('event_type', 'project_name', 'user_name', 'created_at')
    list_filter = ('event_type', 'project_name')
    search_fields = ('project_name', 'user_name', 'event_type')
    readonly_fields = ('created_at',)
