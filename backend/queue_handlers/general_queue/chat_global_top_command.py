import logging
from typing import List, Tuple, Dict, Any
from middlewares.database.db import database
from middlewares.rabbitmq.queue_manager import rabbitmq_manager
from middlewares.rabbitmq.mq_enums import TelegramQueueMessageType
from backend.functions.top.chat_global_top_generator import ChatGlobalTopGenerator
from backend.functions.helpers.get_lang_display import get_language_display
from backend.functions.helpers.get_chat_link import get_chat_name_with_link
from settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

async def handle_chat_global_top_command(message_data: dict):
    logger.info(f"Handling CHAT_GLOBAL_TOP_COMMAND_TG message:\n{message_data}")
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
    for user_id_db in all_chat_users:
        user = await database.get_user(user_id_db)
        if user and user.chat_history:
            users.append(user)
    
    if not users:
        top_stats = "No users with message history found in the database!"
    else:
        # Generate chat global top stats
        top_generator = ChatGlobalTopGenerator(users)
        top_data = top_generator.generate_top_report(limit=10, language=language)
        
        # Get chat names for all chat IDs in the report
        chat_names = {}
        all_chat_ids = set()
        
        # Collect all chat IDs from all rankings
        for key, ranking in top_data.items():
            if isinstance(ranking, list):
                for item in ranking:
                    if isinstance(item, tuple) and len(item) >= 1:
                        try:
                            # Check if the first item looks like a chat ID
                            potential_chat_id = str(item[0])
                            if potential_chat_id.startswith('-') or potential_chat_id.isdigit():
                                all_chat_ids.add(potential_chat_id)
                        except Exception:
                            pass
        
        # Get chat names for all collected IDs
        for chat_id_str in all_chat_ids:
            chat_names[chat_id_str] = await get_chat_name_with_link(chat_id_str)
        
        top_data["chat_names"] = chat_names
        
        # Format the report
        top_stats = await format_top_report(top_data)
    
    response_data = {
        "message_type": TelegramQueueMessageType.CHAT_GLOBAL_TOP_COMMAND_ANSWER,
        "user_id": user_id,
        "chat_id": chat_id,
        "message_id": message_id,
        "top_stats": top_stats,
        "top_languages": top_data.get("top_languages", [])
    }

    await rabbitmq_manager.store_result(settings.RABBITMQ_TELEGRAM_QUEUE, str(chat_id) + '.' + str(message_id), response_data)

async def format_top_report(top_data: Dict[str, Any]) -> str:
    """Format the top data into a readable HTML message"""
    language_filter = top_data.get("language_filter")
    chat_names = top_data.get("chat_names", {})
    
    if language_filter:
        report = f"🌍 <b>Global Chat Rankings ({get_language_display(language_filter)} messages only)</b> 🌍\n\n"
    else:
        report = "🌍 <b>Global Chat Rankings</b> 🌍\n\n"
    
    # Most messages
    report += "💬 <b>Most Messages:</b>\n"
    for i, (chat_id, count, users) in enumerate(top_data.get("most_messages", []), 1):
        chat_name = chat_names.get(str(chat_id), f"Chat {chat_id}")
        report += f"{i}. {chat_name}: {count} messages ({users} users)\n"
    report += "\n"
    
    # Most message length
    report += "📏 <b>Most Total Message Length:</b>\n"
    for i, (chat_id, length, users) in enumerate(top_data.get("most_message_length", []), 1):
        chat_name = chat_names.get(str(chat_id), f"Chat {chat_id}")
        report += f"{i}. {chat_name}: {length} characters ({users} users)\n"
    report += "\n"
    
    # Most unique users
    report += "👥 <b>Most Active Users:</b>\n"
    for i, (chat_id, user_count, msg_count) in enumerate(top_data.get("most_unique_users", []), 1):
        chat_name = chat_names.get(str(chat_id), f"Chat {chat_id}")
        report += f"{i}. {chat_name}: {user_count} users ({msg_count} messages)\n"
    report += "\n"
    
    # Most languages
    report += "🌐 <b>Most Languages Used:</b>\n"
    for i, (chat_id, lang_count, users) in enumerate(top_data.get("most_languages", []), 1):
        chat_name = chat_names.get(str(chat_id), f"Chat {chat_id}")
        report += f"{i}. {chat_name}: {lang_count} languages ({users} users)\n"
    report += "\n"
    
    # Earliest activity
    report += "🕰️ <b>Earliest Activity:</b>\n"
    for i, (chat_id, timestamp, users) in enumerate(top_data.get("earliest_activity", []), 1):
        chat_name = chat_names.get(str(chat_id), f"Chat {chat_id}")
        report += f"{i}. {chat_name}: {timestamp} ({users} users)\n"
    report += "\n"
    
    # Latest activity
    report += "🆕 <b>Latest Activity:</b>\n"
    for i, (chat_id, timestamp, users) in enumerate(top_data.get("latest_activity", []), 1):
        chat_name = chat_names.get(str(chat_id), f"Chat {chat_id}")
        report += f"{i}. {chat_name}: {timestamp} ({users} users)\n"
    report += "\n"
    
    # Highest average message length
    report += "📊 <b>Highest Average Message Length:</b>\n"
    for i, (chat_id, avg_length, users) in enumerate(top_data.get("highest_avg_message_length", []), 1):
        chat_name = chat_names.get(str(chat_id), f"Chat {chat_id}")
        report += f"{i}. {chat_name}: {avg_length:.2f} characters/msg ({users} users)\n"
    
    return report