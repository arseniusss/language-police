import json
import logging
from aiogram import Bot
from aiogram.types import ChatPermissions
from datetime import datetime, timedelta
from aio_pika import IncomingMessage
from settings import get_settings
from middlewares.rabbitmq.queue_manager import rabbitmq_manager
from middlewares.rabbitmq.mq_enums import TelegramQueueMessageType
from bot_telegram.utils.logging_config import logger

settings = get_settings()
logger = logger.getChild('main_handler')

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
            await bot.send_message(chat_id, stats)

        elif message_type == TelegramQueueMessageType.MY_GLOBAL_STATS_COMMAND_ANSWER:
            logger.info("Handling MY_GLOBAL_STATS_COMMAND_TG message")
            chat_id = message_data.get("chat_id", "")
            stats = message_data.get("stats", "")
            await bot.send_message(chat_id, stats)
            
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
            
        elif message_type == TelegramQueueMessageType.ADMIN_NOTIFICATION:
            logger.info("Handling ADMIN_NOTIFICATION message")
            chat_id = message_data.get("chat_id", "")
            text = message_data.get("text", "")
            await bot.send_message(chat_id, text)
            
        elif message_type == TelegramQueueMessageType.USER_NOTIFICATION:
            logger.info("Handling USER_NOTIFICATION message")
            chat_id = message_data.get("chat_id", "")
            user_id = message_data.get("user_id", "")
            message_id = message_data.get("message_id", "")
            text = message_data.get("text", "")
            
            # Reply to the user's message with the notification
            try:
                await bot.send_message(chat_id, text, reply_to_message_id=message_id)
            except Exception as e:
                logger.error(f"Failed to send user notification: {e}")
                # Try without reply if it fails
                await bot.send_message(chat_id, text)
            
        elif message_type == TelegramQueueMessageType.MODERATION_ACTION:
            logger.info("Handling MODERATION_ACTION message")
            chat_id = message_data.get("chat_id", "")
            user_id = message_data.get("user_id", "")
            action_type = message_data.get("action_type", "")
            duration_seconds = message_data.get("duration_seconds", 0)
            
            try:
                if action_type == "warning":
                    # Warning is just a notification, no action needed
                    logger.info(f"Warning issued to user {user_id} in chat {chat_id}")
                    
                elif action_type == "timeout":
                    # Calculate until_date for restriction
                    until_date = datetime.now() + timedelta(seconds=duration_seconds)
                    logger.info(f"Timing out user {user_id} in chat {chat_id} until {until_date}")
                    
                    # Restrict user permissions
                    permissions = ChatPermissions(
                        can_send_messages=False,
                        can_send_media_messages=False,
                        can_send_polls=False,
                        can_send_other_messages=False,
                        can_add_web_page_previews=False,
                        can_change_info=False,
                        can_invite_users=False,
                        can_pin_messages=False
                    )
                    
                    await bot.restrict_chat_member(
                        chat_id=chat_id,
                        user_id=user_id,
                        permissions=permissions,
                        until_date=until_date
                    )
                    
                elif action_type == "temporary_ban":
                    # Ban user with until_date
                    until_date = datetime.now() + timedelta(seconds=duration_seconds)
                    logger.info(f"Temporary banning user {user_id} in chat {chat_id} until {until_date}")
                    
                    await bot.ban_chat_member(
                        chat_id=chat_id,
                        user_id=user_id,
                        until_date=until_date
                    )
                    
                elif action_type == "permanent_ban":
                    # Permanent ban
                    logger.info(f"Permanently banning user {user_id} in chat {chat_id}")
                    
                    await bot.ban_chat_member(
                        chat_id=chat_id,
                        user_id=user_id
                    )
                    
            except Exception as e:
                logger.error(f"Failed to apply moderation action: {e}")
            
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