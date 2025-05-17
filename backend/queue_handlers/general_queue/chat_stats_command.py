import logging
from middlewares.database.db import database
from middlewares.rabbitmq.queue_manager import rabbitmq_manager
from middlewares.rabbitmq.mq_enums import TelegramQueueMessageType
from backend.functions.stats.chat_stats_analyzer import ChatStatsAnalyzer
from backend.functions.helpers.get_lang_display import get_language_display
from typing import Dict, Any
from settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

async def handle_chat_stats_command(message_data: dict):
    """Handle the chat stats command"""
    logger.info(f"Handling CHAT_STATS_COMMAND_TG message:\n{message_data}")
    user_id = message_data.get("user_id", 0)
    chat_id = message_data.get("chat_id", "")
    message_id = message_data.get("message_id", "")
    
    # Get chat from database to find users
    chat = await database.get_chat(int(chat_id))
    
    if not chat or not chat.users:
        stats = "No users found in this chat!"
    else:
        # Get all users in chat
        users = []
        for chat_user_id in chat.users:
            user = await database.get_user(chat_user_id)
            if user:
                users.append(user)
        
        if not users:
            stats = "No users with message history found in this chat!"
        else:
            # Generate chat stats
            stats_analyzer = ChatStatsAnalyzer(users, str(chat_id))
            stats_data = stats_analyzer.generate_stats_report()
            
            # Format the report
            stats = await format_stats_report(stats_data)
    
    response_data = {
        "message_type": TelegramQueueMessageType.CHAT_STATS_COMMAND_ANSWER,
        "chat_id": chat_id,
        "user_id": user_id,
        "stats": stats,
        "message_id": message_id
    }

    await rabbitmq_manager.store_result(settings.RABBITMQ_TELEGRAM_QUEUE, str(chat_id) + '.' + str(message_id), response_data)

async def format_stats_report(stats_data: Dict[str, Any]) -> str:
    """Format the stats data into a readable HTML message"""
    report = "<b>📊 Chat Statistics 📊</b>\n\n"
    
    total_members = stats_data["total_members"]
    members_with_messages = stats_data["members_with_messages"]
    total_messages = stats_data["total_messages"]
    total_length = stats_data["total_message_length"]
    total_languages = stats_data["total_unique_languages"]
    
    report += f"👥 <b>Total Members:</b> {total_members}\n"
    report += f"💬 <b>Members with Analyzed Messages:</b> {members_with_messages} "
    if total_members > 0:
        report += f"({(members_with_messages / total_members) * 100:.1f}%)\n"
    else:
        report += "(0.0%)\n"
        
    report += f"📝 <b>Total Analyzed Messages:</b> {total_messages}\n"
    report += f"📏 <b>Total Message Length:</b> {total_length} characters\n"
    report += f"🌐 <b>Total Unique Languages:</b> {total_languages}\n\n"
    
    if stats_data["language_counts"]:
        report += "<b>🗣️ Messages by Language:</b>\n"
        for lang, count in stats_data["language_counts"].items():
            lang_display = get_language_display(lang)
            percentage = stats_data["language_percentages"][lang]
            report += f"• {lang_display}: <b>{count}</b> messages ({percentage:.1f}%)\n"
    
    return report