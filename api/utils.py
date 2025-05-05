from django.core.cache import cache

from apps.models import GitlabUser


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

    group_info = {
        'chat_id': chat['id'],
        'chat_name': chat.get('title'),
        'username': chat.get('username', 'No Username'),
        'is_forum': chat.get('is_forum', False),
        'message_thread_id': message.get('message_thread_id') or chat.get('message_thread_id'),
        'chat_type': chat.get('type', '')
    }
    return group_info


def get_gitlab_mention(username, full_name):
    try:
        user = GitlabUser.objects.get(gitlab_username=username)
        return f"[{full_name}](tg://user?id={user.telegram_id})"
    except GitlabUser.DoesNotExist:
        return full_name
