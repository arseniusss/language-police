import logging
from middlewares.database.db import database
from middlewares.rabbitmq.queue_manager import rabbitmq_manager
from middlewares.rabbitmq.mq_enums import TelegramQueueMessageType
from backend.functions.stats.personal_stats_analyzer import PersonalStatsAnalyzer
from backend.functions.helpers.get_lang_display import get_language_display
from settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

def format_global_stats_report(stats_data):
    """Format the global stats data into a readable message"""
    report = "🌎 *Your Global Statistics* 🌎\n\n"
    
    report += f"💬 Total Chats: *{stats_data['total_chats']}*\n"
    report += f"📝 Total Messages: *{stats_data['total_messages']}*\n"
    report += f"📏 Total Message Length: *{stats_data['total_message_length']}* characters\n"
    report += f"📊 Average Message Length: *{stats_data['avg_length']:.2f}* characters\n\n"
    
    if 'message_count_by_language' in stats_data and stats_data['message_count_by_language']:
        report += "🌐 *Messages by Language:*\n"
        for lang, count in sorted(stats_data['message_count_by_language'].items(), 
                                 key=lambda x: x[1], reverse=True):
            lang_display = get_language_display(lang)
            percentage = (count / stats_data['total_messages']) * 100
            report += f"{lang_display}: {count} messages ({percentage:.1f}%)\n"
    
    report += "\n📊 *Messages by Chat:*\n"
    if stats_data.get('message_count_by_chat'):
        for chat_id, count in sorted(stats_data['message_count_by_chat'].items(), 
                                  key=lambda x: x[1], reverse=True)[:5]:  # Top 5 chats
            percentage = (count / stats_data['total_messages']) * 100
            report += f"• Chat {chat_id}: {count} messages ({percentage:.1f}%)\n"
        
        if len(stats_data['message_count_by_chat']) > 5:
            report += f"... and {len(stats_data['message_count_by_chat']) - 5} more chats\n"
    
    return report

async def handle_my_global_stats_command(message_data: dict):
    logger.info(f"Handling MY_GLOBAL_STATS_COMMAND_TG message:\n{message_data}")
    user_id = message_data.get("user_id", 0)
    message_id = message_data.get("message_id", "")
    chat_id = message_data.get("chat_id", "")

    user = await database.get_user(user_id)
    if not user or not user.chat_history:
        stats = "No messages found in your history!"
    else:
        analyzer = PersonalStatsAnalyzer(user.chat_history)
        stats_data = analyzer.generate_stats_report()
        stats = format_global_stats_report(stats_data)

    response_data = {
        "message_type": TelegramQueueMessageType.MY_GLOBAL_STATS_COMMAND_ANSWER,
        "user_id": user_id,
        "chat_id": chat_id,
        "stats": stats,
    }

    await rabbitmq_manager.store_result(settings.RABBITMQ_TELEGRAM_QUEUE, str(chat_id) + '.' + str(message_id), response_data)