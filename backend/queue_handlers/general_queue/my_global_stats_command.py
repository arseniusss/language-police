import logging
from middlewares.database.db import database
from middlewares.rabbitmq.queue_manager import rabbitmq_manager
from middlewares.rabbitmq.mq_enums import TelegramQueueMessageType
from backend.functions.stats.personal_stats_analyzer import PersonalStatsAnalyzer
from settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

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
        stats = analyzer.generate_stats_report()

    response_data = {
        "message_type": TelegramQueueMessageType.MY_GLOBAL_STATS_COMMAND_ANSWER,
        "user_id": user_id,
        "chat_id": chat_id,
        "stats": stats,
    }

    await rabbitmq_manager.store_result(settings.RABBITMQ_TELEGRAM_QUEUE, str(chat_id) + '.' + str(message_id), response_data)