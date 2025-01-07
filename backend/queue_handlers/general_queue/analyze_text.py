import logging
from settings import get_settings
from backend.worker_handlers.analyze_language import analyze_language

settings = get_settings()

logger = logging.getLogger(__name__)

async def handle_text_to_analyze(message_data: dict):
    logger.info(f"Handling TEXT_TO_ANALYZE message:\n{message_data}")
    user_id = message_data.get("user_id", 0)
    chat_id = message_data.get("chat_message", {}).get("chat_id", "")
    message_id = message_data.get("chat_message", {}).get("message_id", "")
    text = message_data.get("chat_message", {}).get("content", "")
    timestamp = message_data.get("chat_message", {}).get("timestamp", "")

    analyze_language.apply_async(
        args=[text, chat_id, message_id, user_id, timestamp],
        queue=settings.RABBITMQ_WORKER_QUEUE
    )