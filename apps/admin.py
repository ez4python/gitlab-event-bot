from django.contrib import admin
from .models import GitlabProject, ProjectUser


class ProjectUserInline(admin.TabularInline):
    model = ProjectUser
    extra = 1


class ProjectUserAdmin(admin.ModelAdmin):
    list_display = ('gitlab_username', 'telegram_id', 'project')
    search_fields = ('gitlab_username', 'project__name')


class GitlabProjectAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'telegram_chat_id',
        'telegram_message_thread_id',
        'show_user',
        'show_project',
        'show_branch',
        'show_status',
        'show_duration'
    )
    search_fields = ('name',)
    list_filter = ('name',)

    inlines = [ProjectUserInline]


# Register models with updated admin
admin.site.register(GitlabProject, GitlabProjectAdmin)
admin.site.register(ProjectUser, ProjectUserAdmin)
