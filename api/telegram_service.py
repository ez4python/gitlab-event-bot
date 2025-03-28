import logging
import asyncio
from telegram import Bot
from telegram.constants import ParseMode
from django.conf import settings

logger = logging.getLogger(__name__)


class TelegramService:
    def __init__(self):
        self.bot_token = settings.BOT_TOKEN
        self.supergroup_id = settings.GROUP_ID
        self.bot = Bot(token=self.bot_token)

    async def send_message_to_topic(self, topic_id, message):
        """Send a message to a specific topic in the supergroup."""
        try:
            await self.bot.send_message(
                chat_id=self.supergroup_id,
                text=message,
                parse_mode=ParseMode.HTML,
                message_thread_id=topic_id
            )
            return True
        except Exception as e:
            logger.error(f"Error sending message to Telegram: {e}")
            return False

    def send_message(self, topic_id, message):
        """Synchronous wrapper for the async send_message_to_topic method."""
        return asyncio.run(self.send_message_to_topic(topic_id, message))
