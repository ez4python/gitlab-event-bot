from django.core.cache import cache

from root.settings import BOT_USERNAME


def save_telegram_message_id(event_key, message_id, timeout=60 * 60 * 24):
    cache.set(event_key, message_id, timeout=timeout)


def get_telegram_message_id(event_key):
    return cache.get(event_key)


def delete_telegram_message_id(event_key):
    cache.delete(event_key)


def parse_group_info(message):
    if 'chat' not in message:
        raise ValueError("Message does not contain a 'chat' field")

    chat = message['chat']

    if chat['type'] not in ['group', 'supergroup']:
        return None

    if message.get('text', '').startswith(f'/{BOT_USERNAME}'):
        group_info = {
            'chat_id': chat['id'],
            'chat_name': chat.get('title', 'No Title'),
            'username': chat.get('username', 'No Username'),
            'is_forum': chat.get('is_forum', False),
            'message_thread_id': message.get('message_thread_id', None),
        }
        return group_info
    return None
