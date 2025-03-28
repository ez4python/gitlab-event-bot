# test_telegram_script.py
import os
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'root.settings')
django.setup()

from api.telegram_service import TelegramService


def test_telegram(topic_id, message):
    print(f"Sending test message to topic {topic_id}...")
    telegram_service = TelegramService()
    result = telegram_service.send_message(topic_id, message)

    if result:
        print("Message sent successfully!")
    else:
        print("Failed to send message.")


if __name__ == "__main__":
    import sys

    topic = 2
    msg = input('Enter message: ')

    if len(sys.argv) > 1:
        topic = int(sys.argv[1])
    if len(sys.argv) > 2:
        msg = sys.argv[2]

    test_telegram(topic, msg)
