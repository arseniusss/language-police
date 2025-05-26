import logging
from middlewares.database.db import database
from middlewares.rabbitmq.queue_manager import rabbitmq_manager
from middlewares.rabbitmq.mq_enums import TelegramQueueMessageType
from backend.functions.stats.personal_stats_analyzer import PersonalStatsAnalyzer
from settings import get_settings
from backend.functions.helpers.get_lang_display import get_language_display

settings = get_settings()
logger = logging.getLogger(__name__)

def format_stats_report(stats_data):
    """Format the stats data into a readable message"""
    report = "📊 <b>Your Chat Statistics</b> 📊\n\n"
    
    report += f"📝 <b>Total Messages: {stats_data['total_messages']}</b>\n"
    report += f"📏 <b>Total Message Length: {stats_data['total_message_length']}</b> characters\n"
    report += f"📊 <b>Average Message Length: {stats_data['avg_length']:.2f}</b> characters\n\n"
    
    if 'message_count_by_language' in stats_data and stats_data['message_count_by_language']:
        report += "🌐 *Messages by Language:*\n"
        for lang, count in sorted(stats_data['message_count_by_language'].items(), 
                                 key=lambda x: x[1], reverse=True):
            lang_display = get_language_display(lang)
            percentage = (count / stats_data['total_messages']) * 100
            report += f"{lang_display}: <b>{count}</b> messages ({percentage:.2f}%)\n"
    
    return report

async def handle_my_chat_stats_command(message_data: dict):
    logger.info(f"Handling MY_CHAT_STATS_COMMAND_TG message:\n{message_data}")
    user_id = message_data.get("user_id", 0)
    chat_id = message_data.get("chat_id", "")
    message_id = message_data.get("message_id", "")

    user = await database.get_user(user_id)
    if not user or not user.chat_history:
        stats = "No messages found in your history!"
    else:
        analyzer = PersonalStatsAnalyzer(user.chat_history)
        stats_data = analyzer.generate_stats_report(chat_id=chat_id)
        stats = format_stats_report(stats_data)

    response_data = {
        "message_type": TelegramQueueMessageType.MY_CHAT_STATS_COMMAND_ANSWER,
        "chat_id": chat_id,
        "user_id": user_id,
        "stats": stats,
    }

    await rabbitmq_manager.store_result(settings.RABBITMQ_TELEGRAM_QUEUE, str(chat_id) + '.' + str(message_id), response_data)