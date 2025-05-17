import logging
from typing import List, Tuple
from middlewares.database.db import database
from middlewares.rabbitmq.queue_manager import rabbitmq_manager
from middlewares.rabbitmq.mq_enums import TelegramQueueMessageType
from backend.functions.top.specific_chat_ranking import SpecificChatRankingGenerator
from backend.functions.top.chat_global_top_generator import ChatGlobalTopGenerator
from backend.functions.helpers.get_lang_display import get_language_display
from settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

async def handle_global_chat_ranking_command(message_data: dict):
    logger.info(f"Handling GLOBAL_CHAT_RANKING_COMMAND_TG message:\n{message_data}")
    user_id = message_data.get("user_id", 0)
    chat_id = message_data.get("chat_id", "")
    message_id = message_data.get("message_id", "")
    language = message_data.get("language", None)
    
    # Get all users from database
    users = []
    
    # Get all chats first to collect all user IDs
    all_chat_users = set()
    async for chat_doc in database.db["chats"].find({}):
        if "users" in chat_doc and chat_doc["users"]:
            all_chat_users.update(chat_doc["users"])
    
    # Fetch user data for all collected user IDs
    for user_id_db in all_chat_users:
        user = await database.get_user(user_id_db)
        if user and user.chat_history:
            users.append(user)
    
    if not users:
        ranking_stats = "No users with message history found in the database!"
    else:
        # Generate chat ranking stats
        chat_ranking_generator = SpecificChatRankingGenerator(users, str(chat_id))
        rankings = chat_ranking_generator.get_chat_rankings(language)
        
        # Format the report
        ranking_stats = await format_ranking_report(rankings, chat_id, language)
    
    # Get chat name for display
    chat = await database.get_chat(int(chat_id))
    chat_name = chat.title if chat and hasattr(chat, 'title') and chat.title else f"Chat {chat_id}"
    
    response_data = {
        "message_type": TelegramQueueMessageType.GLOBAL_CHAT_RANKING_COMMAND_ANSWER,
        "chat_id": chat_id,
        "chat_name": chat_name,
        "user_id": user_id,
        "ranking_stats": ranking_stats,
        "message_id": message_id,
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
        
    global_top_generator = ChatGlobalTopGenerator(users)
    return global_top_generator.get_top_languages_overall(limit=10)

async def format_ranking_report(rankings, chat_id, language=None):
    """Format the chat ranking report in a readable way"""
    # Get chat name
    chat = await database.get_chat(int(chat_id))
    chat_name = chat.title if chat and hasattr(chat, 'title') and chat.title else f"Chat {chat_id}"
    
    if language:
        report = f"<b>🏆 {chat_name} Rankings ({get_language_display(language)} messages only) 🏆</b>\n\n"
    else:
        report = f"<b>🏆 {chat_name} Rankings 🏆</b>\n\n"
    
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
        
    # Most unique users
    users_pos, users_count = rankings.get("most_unique_users", (0, 0))
    if users_pos > 0:
        report += f"👥 <b>Unique Users:</b> #{users_pos} with <b>{users_count}</b> users\n\n"
    else:
        report += "👥 <b>Unique Users:</b> No ranking\n\n"
    
    # Only show Ukrainian messages ranking when no language filter
    if not language:
        # Most Ukrainian messages
        ua_pos, ua_count = rankings.get("most_ukrainian_messages", (0, 0))
        if ua_pos > 0:
            report += f"🇺🇦 <b>Ukrainian Messages:</b> #{ua_pos} with <b>{ua_count}</b> messages\n\n"
        else:
            report += "🇺🇦 <b>Ukrainian Messages:</b> No ranking\n\n"
    
    # Most languages
    langs_pos, langs_count = rankings.get("most_languages", (0, 0))
    if langs_pos > 0:
        report += f"🌐 <b>Languages Used:</b> #{langs_pos} with <b>{langs_count}</b> languages\n\n"
    else:
        report += "🌐 <b>Languages Used:</b> No ranking\n\n"
    
    # Earliest activity
    early_pos, early_time = rankings.get("earliest_activity", (0, ""))
    if early_pos > 0:
        report += f"☀️ <b>Earliest Activity:</b> #{early_pos} at <b>{early_time}</b>\n\n"
    else:
        report += "☀️ <b>Earliest Activity:</b> No ranking\n\n"
    
    # Latest activity
    late_pos, late_time = rankings.get("latest_activity", (0, ""))
    if late_pos > 0:
        report += f"🌙 <b>Latest Activity:</b> #{late_pos} at <b>{late_time}</b>\n\n"
    else:
        report += "🌙 <b>Latest Activity:</b> No ranking\n\n"
    
    # Avg message length
    avg_pos, avg_len = rankings.get("avg_message_length", (0, 0.0))
    if avg_pos > 0:
        report += f"📐 <b>Average Message Length:</b> #{avg_pos} with <b>{avg_len:.2f}</b> characters\n\n"
    else:
        report += "📐 <b>Average Message Length:</b> No ranking\n\n"
    
    return report