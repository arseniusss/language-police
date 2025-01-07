import json
import logging
from aiogram import Bot
from aio_pika import IncomingMessage
from settings import get_settings
from middlewares.rabbitmq.queue_manager import rabbitmq_manager
from middlewares.rabbitmq.mq_enums import TelegramQueueMessageType

settings = get_settings()
logger = logging.getLogger(__name__)

async def handle_queue_message(bot: Bot, message: IncomingMessage):
    async with message.process():
        message_data = json.loads(message.body).get("result", {})
        logger.info(f"Received message: {message_data}")
        message_type = message_data.get("message_type", "Unknown")
        
        if message_type == TelegramQueueMessageType.STATS_COMMAND_ANSWER:
            logger.info("Handling STATS_COMMAND_TG message")
            chat_id = message_data.get("chat_id", "")
            text = message_data.get("text", "")
            await bot.send_message(chat_id, text)
        else:
            logger.warning(f"Unhandled message type: {message_type}")

async def consume_telegram_queue_messages(bot: Bot):
    await rabbitmq_manager.connect()
    
    async def on_message(message: IncomingMessage):
        await handle_queue_message(bot, message)
    
    await rabbitmq_manager.telegram_queue.consume(on_message)