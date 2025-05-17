import logging
from middlewares.database.db import database
from middlewares.rabbitmq.queue_manager import rabbitmq_manager
from middlewares.rabbitmq.mq_enums import TelegramQueueMessageType
from backend.functions.stats.personal_stats_analyzer import PersonalStatsAnalyzer
from backend.functions.helpers.get_lang_display import get_language_display
from settings import get_settings
from backend.functions.helpers.get_chat_link import get_chat_name_with_link

settings = get_settings()
logger = logging.getLogger(__name__)

async def format_global_stats_report(stats_data):
    """Format the global stats data into a readable message using HTML"""
    report = "<b>🌎 Your Global Statistics 🌎</b>\n\n"
    
    report += f"💬 Total Chats: <b>{stats_data['total_chats']}</b>\n"
    report += f"📝 Total Messages: <b>{stats_data['total_messages']}</b>\n"
    report += f"📏 Total Message Length: <b>{stats_data['total_message_length']}</b> characters\n"
    report += f"📊 Average Message Length: <b>{stats_data['avg_length']:.2f}</b> characters\n\n"
    
    if 'message_count_by_language' in stats_data and stats_data['message_count_by_language']:
        report += "<b>🌐 Messages by Language:</b>\n"
        for lang, count in sorted(stats_data['message_count_by_language'].items(), 
                                 key=lambda x: x[1], reverse=True):
            lang_display = get_language_display(lang)
            percentage = (count / stats_data['total_messages']) * 100
            report += f"{lang_display}: {count} messages ({percentage:.1f}%)\n"
    
    report += "\n<b>📊 Messages by Chat:</b>\n"
    if stats_data.get('message_count_by_chat'):
        chat_names = stats_data.get('chat_names', {})
        
        for chat_id, count in sorted(stats_data['message_count_by_chat'].items(), 
                                  key=lambda x: x[1], reverse=True)[:5]:  # Top 5 chats
            percentage = (count / stats_data['total_messages']) * 100
            chat_display = chat_names.get(chat_id, f"Chat {chat_id}")
            report += f"• {chat_display}: {count} messages ({percentage:.1f}%)\n"
        
        if len(stats_data['message_count_by_chat']) > 5:
            report += f"... and {len(stats_data['message_count_by_chat']) - 5} more chats\n"
    
    return report

async def handle_my_global_stats_command(message_data: dict):
    logger.info(f"Handling MY_GLOBAL_STATS_COMMAND_TG message:\n{message_data}")
    user_id = message_data.get("user_id", 0)
    message_id = message_data.get("message_id", "")
    chat_id = message_data.get("chat_id", "")
    
    message_text = message_data.get("message_text", "")
    
    if message_text and "@" in message_text:
        logger.info(f"Command with username: {message_text}")

    user = await database.get_user(user_id)
    if not user or not user.chat_history:
        stats = "No messages found in your history!"
    else:
        analyzer = PersonalStatsAnalyzer(user.chat_history)
        stats_data = analyzer.generate_stats_report()
        
        if stats_data.get('message_count_by_chat'):
            chat_names = {}
            for chat_id_str in stats_data['message_count_by_chat'].keys():
                chat_names[chat_id_str] = await get_chat_name_with_link(chat_id_str)
            
            stats_data['chat_names'] = chat_names
        
        stats = await format_global_stats_report(stats_data)

    response_data = {
        "message_type": TelegramQueueMessageType.MY_GLOBAL_STATS_COMMAND_ANSWER,
        "user_id": user_id,
        "chat_id": chat_id,
        "stats": stats,
        "message_id": message_id
    }

    await rabbitmq_manager.store_result(settings.RABBITMQ_TELEGRAM_QUEUE, str(chat_id) + '.' + str(message_id), response_data)