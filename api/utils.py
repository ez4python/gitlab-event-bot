from django.core.cache import cache


def save_telegram_message_id(event_key, message_id, timeout=86400):
    cache.set(event_key, message_id, timeout=timeout)


def get_telegram_message_id(event_key):
    return cache.get(event_key)


def delete_telegram_message_id(event_key):
    cache.delete(event_key)
