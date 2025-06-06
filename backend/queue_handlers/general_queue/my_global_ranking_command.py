import logging
from typing import List, Tuple
from middlewares.database.db import database
from middlewares.rabbitmq.queue_manager import rabbitmq_manager
from middlewares.rabbitmq.mq_enums import TelegramQueueMessageType
from backend.functions.top.specific_user_ranking import SpecificUserGlobalRankingGenerator
from backend.functions.helpers.get_lang_display import get_language_display
from settings import get_settings
from backend.functions.top.top_generator import GlobalTopGenerator

settings = get_settings()
logger = logging.getLogger(__name__)

async def handle_my_global_ranking_command(message_data: dict):
    logger.info(f"Handling MY_GLOBAL_RANKING_COMMAND_TG message:\n{message_data}")
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
    for chat_user_id in all_chat_users:
        user = await database.get_user(chat_user_id)
        if user and user.chat_history:
            users.append(user)
    
    if not users:
        ranking_stats = "No users with message history found in the database!"
    else:
        # Generate user ranking stats
        user_ranking_generator = SpecificUserGlobalRankingGenerator(users, int(user_id))
        rankings = user_ranking_generator.get_user_rankings(language)
        
        # Format the report
        ranking_stats = format_ranking_report(rankings, language)
    
    response_data = {
        "message_type": TelegramQueueMessageType.MY_GLOBAL_RANKING_COMMAND_ANSWER,
        "user_id": user_id,
        "chat_id": chat_id,
        "message_id": message_id,
        "ranking_stats": ranking_stats,
        "top_languages": await get_global_top_languages()
    }

    await rabbitmq_manager.store_result(settings.RABBITMQ_TELEGRAM_QUEUE, str(chat_id) + '.' + str(message_id), response_data)

async def get_global_top_languages() -> List[Tuple[str, int, str]]:
    """Get top languages used globally with their display names"""
    # Get all users
    users = []
    
    # Get all chats first to collect all user IDs
    all_chat_users = set()
    async for chat in database.db["chats"].find({}):
        if "users" in chat and chat["users"]:
            all_chat_users.update(chat["users"])
    
    # Fetch user data
    for user_id in all_chat_users:
        user = await database.get_user(user_id)
        if user and user.chat_history:
            users.append(user)
            
    if not users:
        return []
        
    top_generator = GlobalTopGenerator(users)
    # The _get_top_languages already returns (lang, count, display_name)
    return top_generator._get_top_languages(limit=10)

def format_ranking_report(rankings, language=None):
    if language:
        report = f"<b>🏆 Your Global Rankings ({get_language_display(language)} messages only) 🏆</b>\n\n"
    else:
        report = "<b>🏆 Your Global Rankings 🏆</b>\n\n"
    
    # Most messages
    msg_pos, msg_count = rankings.get("most_messages", (0, 0))
    if msg_pos > 0:
        report += f"💬 <b>Messages Count:</b> #{msg_pos} with <b>{msg_count}</b> messages\n\n"
    else:
        report += "💬 <b>Messages Count:</b> No ranking\n\n"
    
    # Most message length
    len_pos, total_len = rankings.get("most_message_length", (0, 0))
    if len_pos > 0:
        report += f"📏 <b>Total Message Length:</b> #{len_pos} with <b>{total_len}</b> characters\n\n"
    else:
        report += "📏 <b>Total Message Length:</b> No ranking\n\n"
    
    # Earliest message
    early_pos, early_time = rankings.get("earliest_message", (0, ""))
    if early_pos > 0:
        report += f"☀️ <b>Earliest Message:</b> #{early_pos} at <b>{early_time}</b>\n\n"
    else:
        report += "☀️ <b>Earliest Message:</b> No ranking\n\n"
    
    # Latest message
    late_pos, late_time = rankings.get("latest_message", (0, ""))
    if late_pos > 0:
        report += f"🌙 <b>Latest Message:</b> #{late_pos} at <b>{late_time}</b>\n\n"
    else:
        report += "🌙 <b>Latest Message:</b> No ranking\n\n"
    
    # Avg message length
    avg_pos, avg_len = rankings.get("avg_message_length", (0, 0.0))
    if avg_pos > 0:
        report += f"📐 <b>Average Message Length:</b> #{avg_pos} with <b>{avg_len:.2f}</b> characters\n\n"
    else:
        report += "📐 <b>Average Message Length:</b> No ranking\n\n"
    
    return report