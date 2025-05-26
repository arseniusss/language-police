import logging
from middlewares.database.db import database
from middlewares.rabbitmq.queue_manager import rabbitmq_manager
from middlewares.rabbitmq.mq_enums import TelegramQueueMessageType
from backend.functions.stats.global_stats_analyzer import GlobalStatsAnalyzer
from backend.functions.helpers.get_lang_display import get_language_display
from backend.functions.helpers.get_chat_link import get_chat_name_with_link
from typing import Dict, Any
from settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

async def handle_global_stats_command(message_data: dict):
    """Handle the global stats command"""
    logger.info(f"Handling GLOBAL_STATS_COMMAND_TG message:\n{message_data}")
    user_id = message_data.get("user_id", 0)
    chat_id = message_data.get("chat_id", "")
    message_id = message_data.get("message_id", "")
    
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
        if user:
            users.append(user)
    
    if not users:
        stats = "No users found in the database!"
    else:
        # Generate global stats
        stats_analyzer = GlobalStatsAnalyzer(users)
        stats_data = stats_analyzer.generate_stats_report()
        
        # Get chat names for the top chats
        chat_names = {}
        for chat_id_str in stats_data['top_chats'].keys():
            chat_names[chat_id_str] = await get_chat_name_with_link(chat_id_str)
        stats_data['chat_names'] = chat_names
        
        # Get user names for the top users
        user_names = {}
        for user_id in stats_data['top_users'].keys():
            for user in users:
                if user.user_id == user_id:
                    user_names[user_id] = user.name or str(user_id)
                    break
        stats_data['user_names'] = user_names
        
        # Format the report
        stats = await format_stats_report(stats_data)
    
    response_data = {
        "message_type": TelegramQueueMessageType.GLOBAL_STATS_COMMAND_ANSWER,
        "chat_id": chat_id,
        "user_id": user_id,
        "stats": stats,
        "message_id": message_id
    }

    await rabbitmq_manager.store_result(settings.RABBITMQ_TELEGRAM_QUEUE, str(chat_id) + '.' + str(message_id), response_data)

async def format_stats_report(stats_data: Dict[str, Any]) -> str:
    """Format the stats data into a readable HTML message"""
    report = "<b>🌎 Global System Statistics 🌎</b>\n\n"
    
    users_with_messages = stats_data["users_with_messages"]
    total_chats = stats_data["total_chats"]
    total_messages = stats_data["total_messages"]
    total_length = stats_data["total_message_length"]
    total_languages = stats_data["total_unique_languages"]
    
    report += f"💬 <b>Users with Analyzed Messages:</b> {users_with_messages}\n"
    report += f"👥 <b>Total Chats:</b> {total_chats}\n"
    report += f"📝 <b>Total Analyzed Messages:</b> {total_messages}\n"
    report += f"📏 <b>Total Message Length:</b> {total_length} characters\n"
    report += f"🌐 <b>Total Unique Languages:</b> {total_languages}\n\n"
    
    # Show top 10 users by message count
    if stats_data["top_users"]:
        report += "<b>👑 Top Users by Message Count:</b>\n"
        for i, (user_id, count) in enumerate(list(stats_data["top_users"].items())[:10], 1):
            user_name = stats_data['user_names'].get(user_id, str(user_id))
            percentage = (count / total_messages) * 100 if total_messages > 0 else 0
            report += f"{i}. <a href='tg://user?id={user_id}'>{user_name}</a>: <b>{count}</b> messages ({percentage:.1f}%)\n"
        report += "\n"
    
    # Show top 10 chats by message count
    if stats_data["top_chats"]:
        report += "<b>👥 Top Chats by Message Count:</b>\n"
        for i, (chat_id, count) in enumerate(list(stats_data["top_chats"].items())[:10], 1):
            chat_name = stats_data['chat_names'].get(chat_id, f"Chat {chat_id}")
            percentage = (count / total_messages) * 100 if total_messages > 0 else 0
            report += f"{i}. {chat_name}: <b>{count}</b> messages ({percentage:.1f}%)\n"
        report += "\n"
    
    if stats_data["language_counts"]:
        report += "<b>🗣️ Messages by Language:</b>\n"
        for lang, count in list(stats_data["language_counts"].items())[:15]:  # Top 15 languages
            lang_display = get_language_display(lang)
            percentage = stats_data["language_percentages"][lang]
            report += f"• {lang_display}: <b>{count}</b> messages ({percentage:.1f}%)\n"
    
    return report