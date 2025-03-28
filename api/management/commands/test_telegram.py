from django.core.management.base import BaseCommand
from api.telegram_service import TelegramService


class Command(BaseCommand):
    help = 'Test the Telegram bot by sending a test message'

    def add_arguments(self, parser):
        parser.add_argument('--topic', type=int, default=1, help='Topic ID to send the message to')
        parser.add_argument('--message', type=str, default='Test message from GitLab Event Bot', help='Message to send')

    def handle(self, *args, **options):
        topic_id = options['topic']
        message = options['message']

        self.stdout.write(f"Sending test message to topic {topic_id}...")

        telegram_service = TelegramService()
        result = telegram_service.send_message(topic_id, message)

        if result:
            self.stdout.write(self.style.SUCCESS('Message sent successfully!'))
        else:
            self.stdout.write(self.style.ERROR('Failed to send message.'))
