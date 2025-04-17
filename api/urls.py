from django.urls import path
from api.views import GitlabWebhookAPIView, TelegramWebhookAPIView, set_webhook

urlpatterns = [
    path('gitlab/webhook/', GitlabWebhookAPIView.as_view(), name='gitlab-webhook'),
    path('telegram/webhook/', TelegramWebhookAPIView.as_view(), name='telegram-webhook'),
    path('webhook/', set_webhook, name='set-webhook'),
]
