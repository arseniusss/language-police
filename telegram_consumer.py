import aio_pika
import json
import logging
from aiogram import Bot
from settings import get_settings
from middlewares.rabbitmq.rabbitmq import QueueMessageType

settings = get_settings()
logger = logging.getLogger(__name__)

async def consume_telegram_queue_messages(bot: Bot):
    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=1)
    queue = await channel.declare_queue(settings.RABBITMQ_TELEGRAM_QUEUE, durable=True)
    
    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            async with message.process():
                message_data = json.loads(message.body).get("result", {})
                logger.info(f"Received message: {message_data}")
                message_type = message_data.get("message_type", "Unknown")
                
                if message_type == QueueMessageType.STATS_COMMAND_TG:
                    logger.info("Handling STATS_COMMAND_TG message")
                    chat_id = message_data.get("chat_id", "")
                    text = message_data.get("text", "")
                    await bot.send_message(chat_id, text)
                else:
                    logger.warning(f"Unhandled message type: {message_type}")