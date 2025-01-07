import logging
from langdetect import detect
from middlewares.database.db import database
from middlewares.rabbitmq.rabbitmq import rabbitmq_manager, QueueMessageType
from settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

async def handle_stats_command(message_data: dict):
    logger.info(f"Handling STATS_COMMAND_TG message:\n{message_data}")
    user_id = message_data.get("user_id", 0)
    chat_id = message_data.get("chat_id", "")
    message_id = message_data.get("message_id", "")

    user = await database.get_user(user_id)
    if not user or not user.chat_history:
        response_text = "No messages found in your history!"
    else:
        analysis_result = []
        for chat_id, messages in user.chat_history.items():
            analysis_result.append(f"\nChat ID: {chat_id}")
            for chat_message in messages:
                try:
                    if chat_message.content:
                        lang = detect(chat_message.content)
                        analysis_result.append(
                            f"Message: {chat_message.content[:30]}...\n"
                            f"Language: {lang}\n"
                        )
                except Exception as e:
                    logging.error(f"Error analyzing message: {e}")
                    continue

        if len(analysis_result) > 1:
            response_text = "Language Analysis:\n\n" + "\n".join(analysis_result)
        else:
            response_text = "No messages could be analyzed!"

    response_data = {
        "message_type": QueueMessageType.STATS_COMMAND_TG,
        "chat_id": chat_id,
        "user_id": user_id,
        "text": response_text,
    }

    await rabbitmq_manager.store_result(settings.RABBITMQ_TELEGRAM_QUEUE, str(chat_id) + '.' + str(message_id), response_data)
