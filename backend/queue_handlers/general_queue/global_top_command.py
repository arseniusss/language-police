import logging
from typing import List, Tuple
from middlewares.database.db import database
from middlewares.rabbitmq.queue_manager import rabbitmq_manager
from middlewares.rabbitmq.mq_enums import TelegramQueueMessageType
from backend.functions.top.top_generator import GlobalTopGenerator
from backend.functions.helpers.get_lang_display import get_language_display
from settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

async def handle_global_top_command(message_data: dict):
    logger.info(f"Handling GLOBAL_TOP_COMMAND_TG message:\n{message_data}")
    user_id = message_data.get("user_id", 0)
    message_id = message_data.get("message_id", "")
    chat_id = message_data.get("chat_id", "")
    language = message_data.get("language", None)
    
    # Get all users from database
    users = []
    
    # Get all chats first to collect all user IDs
    all_chat_users = set()
    async for chat in database.db["chats"].find({}):
        if "users" in chat and chat["users"]:
            all_chat_users.update(chat["users"])
    
    # Fetch user data for all collected user IDs
    for user_id in all_chat_users:
        user = await database.get_user(user_id)
        if user and user.chat_history:
            users.append(user)
    
    if not users:
        top_stats = "No users with message history found in the database!"
    else:
        # Generate global top stats
        top_generator = GlobalTopGenerator(users)
        top_data = top_generator.generate_top_report(limit=10, language=language)
        
        # Format the report
        top_stats = format_top_report(top_data)
    
    response_data = {
        "message_type": TelegramQueueMessageType.GLOBAL_TOP_COMMAND_ANSWER,
        "user_id": user_id,
        "chat_id": chat_id,
        "message_id": message_id,
        "top_stats": top_stats,
        "top_languages": await get_global_top_languages()
    }

    await rabbitmq_manager.store_result(settings.RABBITMQ_TELEGRAM_QUEUE, str(chat_id) + '.' + str(message_id), response_data)

async def get_global_top_languages() -> List[Tuple[str, int, str]]:
    """Get top 10 languages used globally with their display names"""
    users = []
    
    # Get all chats first to collect all user IDs
    all_chat_users = set()
    async for chat in database.db["chats"].find({}):
        if "users" in chat and chat["users"]:
            all_chat_users.update(chat["users"])
    
    # Fetch user data for all collected user IDs
    for user_id in all_chat_users:
        user = await database.get_user(user_id)
        if user and user.chat_history:
            users.append(user)
    
    if not users:
        return []
    
    top_generator = GlobalTopGenerator(users)
    # The _get_top_languages already returns (lang, count, display_name)
    return top_generator._get_top_languages(limit=10)

def format_top_report(top_data):
    language_filter = top_data.get("language_filter")
    
    if language_filter:
        report = f"🌎 Global Top Statistics ({get_language_display(language_filter)} messages only) 🌎\n\n"
    else:
        report = "🌎 Global Top Statistics 🌎\n\n"
    
    # Most messages
    report += "👑 Most Messages:\n"
    for i, (user_id, name, count) in enumerate(top_data["most_messages"], 1):
        report += f"{i}. <a href='tg://user?id={user_id}'>{name}</a>: {count} messages\n"
    report += "\n"
    
    # Most message length
    report += "📏 Most Total Message Length:\n"
    for i, (user_id, name, length) in enumerate(top_data["most_message_length"], 1):
        report += f"{i}. <a href='tg://user?id={user_id}'>{name}</a>: {length} characters\n"
    report += "\n"
    
    # Only add Ukrainian messages section if no language filter
    if not language_filter and "most_ukrainian_messages" in top_data:
        # Most Ukrainian messages
        report += "🇺🇦 Most Ukrainian Messages:\n"
        for i, (user_id, name, count) in enumerate(top_data["most_ukrainian_messages"], 1):
            report += f"{i}. <a href='tg://user?id={user_id}'>{name}</a>: {count} messages\n"
        report += "\n"
    
    # Earliest messages
    report += "🕰️ Earliest Messages:\n"
    for i, (user_id, name, timestamp) in enumerate(top_data["earliest_message_users"], 1):
        report += f"{i}. <a href='tg://user?id={user_id}'>{name}</a>: {timestamp}\n"
    report += "\n"
    
    # Latest messages
    report += "🆕 Latest Messages:\n"
    for i, (user_id, name, timestamp) in enumerate(top_data["latest_message_users"], 1):
        report += f"{i}. <a href='tg://user?id={user_id}'>{name}</a>: {timestamp}\n"
    report += "\n"
    
    # Highest average message length
    report += "📊 Highest Average Message Length:\n"
    for i, (user_id, name, avg_length) in enumerate(top_data["highest_avg_message_length"], 1):
        report += f"{i}. <a href='tg://user?id={user_id}'>{name}</a>: {avg_length:.2f} characters\n"
    
    return report