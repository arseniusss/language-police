import json
import logging
import re
from aiogram import Bot
from aiogram.types import ChatPermissions
from datetime import datetime, timedelta
from aio_pika import IncomingMessage
from settings import get_settings
from middlewares.rabbitmq.queue_manager import rabbitmq_manager
from middlewares.rabbitmq.mq_enums import TelegramQueueMessageType
from bot_telegram.utils.logging_config import logger
from aiogram.utils.keyboard import InlineKeyboardBuilder

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
            logger.info("Handling MY_GLOBAL_STATS_COMMAND_ANSWER message")
            chat_id = message_data.get("chat_id", "")
            stats = message_data.get("stats", "")
            await bot.send_message(chat_id, stats, parse_mode="HTML", disable_web_page_preview=True)
            
        elif message_type == TelegramQueueMessageType.CHAT_TOP_COMMAND_ANSWER:
            logger.info("Handling CHAT_TOP_COMMAND_ANSWER message")
            chat_id = message_data.get("chat_id", "")
            top_stats = message_data.get("top_stats", "")
            message_id = message_data.get("message_id", "")
            top_languages = message_data.get("top_languages", [])
            
            # Create language filter buttons
            builder = InlineKeyboardBuilder()
            builder.button(text="All Languages", callback_data="chat_top_all_langs")
            
            # Add buttons for top languages
            for lang_code, count, lang_display in top_languages:
                builder.button(
                    text=f"{lang_display} ({count})", 
                    callback_data=f"chat_top_lang_{lang_code}"
                )
            
            builder.adjust(2)  # Two buttons per row
            
            try:
                if message_id:
                    await bot.edit_message_text(
                        chat_id = str(chat_id), 
                        message_id = int(message_id), 
                        text = top_stats, 
                        parse_mode="HTML",
                        reply_markup=builder.as_markup()
                    )
                else:
                    await bot.send_message(
                        chat_id, 
                        top_stats, 
                        parse_mode="HTML",
                        reply_markup=builder.as_markup()
                    )
            except Exception as e:
                logger.error(f"Failed to send message: {e}")
            
        elif message_type == TelegramQueueMessageType.GLOBAL_TOP_COMMAND_ANSWER:
            logger.info("Handling GLOBAL_TOP_COMMAND_ANSWER message")
            message_id = message_data.get("message_id", "")
            chat_id = message_data.get("chat_id", "")
            top_stats = message_data.get("top_stats", "")
            top_languages = message_data.get("top_languages", [])
            
            # Create language filter buttons
            builder = InlineKeyboardBuilder()
            builder.button(text="All Languages", callback_data="global_top_all_langs")
            
            # Add buttons for top languages
            for lang_code, count, lang_display in top_languages:
                builder.button(
                    text=f"{lang_display} ({count})", 
                    callback_data=f"global_top_lang_{lang_code}"
                )
            
            builder.adjust(2)  # Two buttons per row
            
            try:
                if message_id:
                    await bot.edit_message_text(
                        chat_id = str(chat_id), 
                        message_id = int(message_id), 
                        text = top_stats, 
                        parse_mode="HTML",
                        reply_markup=builder.as_markup()
                    )
                else:
                    await bot.send_message(
                        chat_id, 
                        top_stats, 
                        parse_mode="HTML",
                        reply_markup=builder.as_markup()
                    )
            except Exception as e:
                logger.error(f"Failed to send message: {e}")
            
        elif message_type == TelegramQueueMessageType.MY_CHAT_RANKING_COMMAND_ANSWER:
            logger.info("Handling MY_CHAT_RANKING_COMMAND_ANSWER message")
            chat_id = message_data.get("chat_id", "")
            message_id = message_data.get("message_id", "")
            ranking_stats = message_data.get("ranking_stats", "")
            top_languages = message_data.get("top_languages", [])
            
            # Create language filter buttons
            builder = InlineKeyboardBuilder()
            builder.button(text="All Languages", callback_data="my_chat_ranking_all_langs")
            
            # Add buttons for top languages
            for lang_code, count, lang_display in top_languages:
                builder.button(
                    text=f"{lang_display} ({count})", 
                    callback_data=f"my_chat_ranking_lang_{lang_code}"
                )
            
            builder.adjust(2)  # Two buttons per row
            
            try:
                if message_id:
                    await bot.edit_message_text(
                        chat_id = str(chat_id), 
                        message_id = int(message_id), 
                        text = ranking_stats, 
                        parse_mode="HTML",
                        reply_markup=builder.as_markup()
                    )
                else:
                    await bot.send_message(
                        chat_id, 
                        ranking_stats, 
                        parse_mode="HTML",
                        reply_markup=builder.as_markup()
                    )
            except Exception as e:
                logger.error(f"Failed to send message: {e}")

        elif message_type == TelegramQueueMessageType.MY_GLOBAL_RANKING_COMMAND_ANSWER:
            logger.info("Handling MY_GLOBAL_RANKING_COMMAND_ANSWER message")
            chat_id = message_data.get("chat_id", "")
            message_id = message_data.get("message_id", "")
            ranking_stats = message_data.get("ranking_stats", "")
            top_languages = message_data.get("top_languages", [])
            
            # Create language filter buttons
            builder = InlineKeyboardBuilder()
            builder.button(text="All Languages", callback_data="my_global_ranking_all_langs")
            
            # Add buttons for top languages
            for lang_code, count, lang_display in top_languages:
                builder.button(
                    text=f"{lang_display} ({count})", 
                    callback_data=f"my_global_ranking_lang_{lang_code}"
                )
            
            builder.adjust(2)  # Two buttons per row
            
            try:
                if message_id:
                    await bot.edit_message_text(
                        chat_id = str(chat_id), 
                        message_id = int(message_id), 
                        text = ranking_stats, 
                        parse_mode="HTML",
                        reply_markup=builder.as_markup()
                    )
                else:
                    await bot.send_message(
                        chat_id, 
                        ranking_stats, 
                        parse_mode="HTML",
                        reply_markup=builder.as_markup()
                    )
            except Exception as e:
                logger.error(f"Failed to send message: {e}")
        
        elif message_type == TelegramQueueMessageType.GLOBAL_CHAT_RANKING_COMMAND_ANSWER:
            logger.info("Handling GLOBAL_CHAT_RANKING_COMMAND_ANSWER message")
            chat_id = message_data.get("chat_id", "")
            ranking_stats = message_data.get("ranking_stats", "")
            message_id = message_data.get("message_id", "")
            top_languages = message_data.get("top_languages", [])
            
            # Create language filter buttons
            builder = InlineKeyboardBuilder()
            builder.button(text="All Languages", callback_data="global_chat_ranking_all_langs")
            
            # Add buttons for top languages
            for lang_code, count, lang_display in top_languages:
                if count > 0:  # Only show languages with messages
                    builder.button(
                        text=f"{lang_display} ({count})", 
                        callback_data=f"global_chat_ranking_lang_{lang_code}"
                    )
            
            builder.adjust(2)  # Two buttons per row
            
            try:
                if message_id:
                    await bot.edit_message_text(
                        chat_id = str(chat_id), 
                        message_id = int(message_id), 
                        text = ranking_stats, 
                        parse_mode="HTML",
                        reply_markup=builder.as_markup()
                    )
                else:
                    await bot.send_message(
                        chat_id, 
                        ranking_stats, 
                        parse_mode="HTML",
                        reply_markup=builder.as_markup()
                    )
            except Exception as e:
                logger.error(f"Failed to send message: {e}")
                
        
        elif message_type == TelegramQueueMessageType.CHAT_STATS_COMMAND_ANSWER:
            logger.info("Handling CHAT_STATS_COMMAND_ANSWER message")
            chat_id = message_data.get("chat_id", "")
            stats = message_data.get("stats", "")
            message_id = message_data.get("message_id", "")
            
            # Get actual member count from Telegram API
            try:
                member_count = await bot.get_chat_member_count(chat_id)

                analyzed_members_match = re.search(r"💬 <b>Members with Analyzed Messages:</b> (\d+)", stats)
                if analyzed_members_match and member_count > 0:
                    analyzed_members = int(analyzed_members_match.group(1))
                    
                    # Calculate the actual percentage based on Telegram's member count
                    percentage = (analyzed_members / member_count) * 100
                    
                    # Update both the total members count and the percentage
                    stats = re.sub(r"(👥 <b>Total Members:</b>) \d+", r"\1 {}".format(member_count), stats)
                    stats = re.sub(
                        r"(💬 <b>Members with Analyzed Messages:</b> \d+) \(\d+\.\d+%\)",
                        r"\1 ({:.1f}%)".format(percentage),
                        stats
                    )

                # Replace the member count in the stats text
                else:
                    stats = re.sub(r"(👥 <b>Total Members:</b>) \d+", r"\1 {}".format(member_count), stats)
                
            except Exception as e:
                logger.error(f"Failed to get chat member count: {e}")
            
            # Send the message with updated stats
            await bot.send_message(
                chat_id,
                stats,
                parse_mode="HTML"
            )
        
        elif message_type == TelegramQueueMessageType.CHAT_STATS_COMMAND_ANSWER:
            logger.info("Handling CHAT_STATS_COMMAND_ANSWER message")
            chat_id = message_data.get("chat_id", "")
            stats = message_data.get("stats", "")
            message_id = message_data.get("message_id", "")
            
            # Get actual member count from Telegram API
            try:
                member_count = await bot.get_chat_member_count(chat_id)

                analyzed_members_match = re.search(r"💬 <b>Members with Analyzed Messages:</b> (\d+)", stats)
                if analyzed_members_match and member_count > 0:
                    analyzed_members = int(analyzed_members_match.group(1))
                    
                    # Calculate the actual percentage based on Telegram's member count
                    percentage = (analyzed_members / member_count) * 100
                    
                    # Update both the total members count and the percentage
                    stats = re.sub(r"(👥 <b>Total Members:</b>) \d+", r"\1 {}".format(member_count), stats)
                    stats = re.sub(
                        r"(💬 <b>Members with Analyzed Messages:</b> \d+) \(\d+\.\d+%\)",
                        r"\1 ({:.1f}%)".format(percentage),
                        stats
                    )

                # Replace the member count in the stats text
                else:
                    stats = re.sub(r"(👥 <b>Total Members:</b>) \d+", r"\1 {}".format(member_count), stats)
                
            except Exception as e:
                logger.error(f"Failed to get chat member count: {e}")
            
            # Send the message with updated stats
            await bot.send_message(
                chat_id,
                stats,
                parse_mode="HTML"
            )
            
        elif message_type == TelegramQueueMessageType.GLOBAL_STATS_COMMAND_ANSWER:
            logger.info("Handling GLOBAL_STATS_COMMAND_ANSWER message")
            chat_id = message_data.get("chat_id", "")
            stats = message_data.get("stats", "")
            message_id = message_data.get("message_id", "")
            
            await bot.send_message(
                chat_id,
                stats,
                parse_mode="HTML",
                disable_web_page_preview=True
            )
        
        elif message_type == TelegramQueueMessageType.CHAT_GLOBAL_TOP_COMMAND_ANSWER:
            logger.info("Handling CHAT_GLOBAL_TOP_COMMAND_ANSWER message")
            chat_id = message_data.get("chat_id", "")
            top_stats = message_data.get("top_stats", "")
            message_id = message_data.get("message_id", "")
            top_languages = message_data.get("top_languages", [])
            
            # Create language filter buttons
            builder = InlineKeyboardBuilder()
            builder.button(text="All Languages", callback_data="chat_global_top_all_langs")
            
            # Add buttons for top languages
            for lang_code, count, lang_display in top_languages:
                if count > 0:  # Only show languages with messages
                    builder.button(
                        text=f"{lang_display} ({count})", 
                        callback_data=f"chat_global_top_lang_{lang_code}"
                    )
            
            builder.adjust(2)  # Two buttons per row
                        
            try:
                if message_id:
                    # Try to edit existing message
                    await bot.edit_message_text(
                        chat_id = chat_id, 
                        message_id = int(message_id), 
                        text = top_stats, 
                        parse_mode="HTML",
                        reply_markup=builder.as_markup(),
                        disable_web_page_preview=True
                    )
                else:
                    # Send new message
                    sent_message = await bot.send_message(
                        chat_id, 
                        top_stats, 
                        parse_mode="HTML",
                        reply_markup=builder.as_markup(),
                        disable_web_page_preview=True
                    )
                    
                    # Store the message ID for future edits
                    # The message cache can be shared with the function below if it exists
                    if not hasattr(handle_queue_message, 'previous_messages'):
                        handle_queue_message.previous_messages = {}
                    if chat_id not in handle_queue_message.previous_messages:
                        handle_queue_message.previous_messages[chat_id] = {}
                    handle_queue_message.previous_messages[chat_id]['chat_global_top'] = sent_message.message_id
            except Exception as e:
                logger.error(f"Failed to send chat global top message: {e}")
        
        
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