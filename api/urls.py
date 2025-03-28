from django.urls import path
from api.views import GitLabWebhookView

urlpatterns = [
    path('gitlab-webhook/', GitLabWebhookView.as_view(), name='gitlab_webhook'),
]
