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
        
        elif message_type == TelegramQueueMessageType.MY_CHAT_STATS_COMMAND_ANSWER:
            logger.info("Handling MY_CHAT_STATS_COMMAND_TG message")
            chat_id = message_data.get("chat_id", "")
            stats = message_data.get("stats", "")
            await bot.send_message(chat_id, stats)  # Don't add "Your chat stats: "

        elif message_type == TelegramQueueMessageType.MY_GLOBAL_STATS_COMMAND_ANSWER:
            logger.info("Handling MY_GLOBAL_STATS_COMMAND_TG message")
            chat_id = message_data.get("chat_id", "")
            stats = message_data.get("stats", "")
            await bot.send_message(chat_id, stats)  # Don't add "Your global stats: "
            
        elif message_type == TelegramQueueMessageType.CHAT_TOP_COMMAND_ANSWER:
            logger.info("Handling CHAT_TOP_COMMAND_ANSWER message")
            chat_id = message_data.get("chat_id", "")
            top_stats = message_data.get("top_stats", "")
            await bot.send_message(chat_id, top_stats, parse_mode="HTML")
            
        elif message_type == TelegramQueueMessageType.GLOBAL_TOP_COMMAND_ANSWER:
            logger.info("Handling GLOBAL_TOP_COMMAND_ANSWER message")
            chat_id = message_data.get("chat_id", "")
            top_stats = message_data.get("top_stats", "")
            await bot.send_message(chat_id, top_stats, parse_mode="HTML")
            
        elif message_type == TelegramQueueMessageType.MY_CHAT_RANKING_COMMAND_ANSWER:
            logger.info("Handling MY_CHAT_RANKING_COMMAND_ANSWER message")
            chat_id = message_data.get("chat_id", "")
            ranking_stats = message_data.get("ranking_stats", "")
            await bot.send_message(chat_id, ranking_stats)
            
        elif message_type == TelegramQueueMessageType.MY_GLOBAL_RANKING_COMMAND_ANSWER:
            logger.info("Handling MY_GLOBAL_RANKING_COMMAND_ANSWER message")
            chat_id = message_data.get("chat_id", "")
            ranking_stats = message_data.get("ranking_stats", "")
            await bot.send_message(chat_id, ranking_stats)
            
        else:
            logger.warning(f"Unhandled message type: {message_type}")

async def consume_telegram_queue_messages(bot: Bot):
    await rabbitmq_manager.connect()
    
    async def on_message(message: IncomingMessage):
        try:
            await handle_queue_message(bot, message)
        except Exception as e:
            logger.error(f"Error while handling queue message {message.body}: {e}")
    
    await rabbitmq_manager.telegram_queue.consume(on_message)