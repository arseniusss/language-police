import logging
from settings import get_settings
from backend.worker_handlers.analyze_language import analyze_language
from middlewares.database.db import database
from middlewares.database.models import User, Chat

settings = get_settings()

logger = logging.getLogger(__name__)

async def handle_text_to_analyze(message_data: dict):
    logger.info(f"Handling TEXT_TO_ANALYZE message:\n{message_data}")
    user_id = message_data.get("user_id", 0)
    chat_id = message_data.get("chat_message", {}).get("chat_id", "")
    message_id = message_data.get("chat_message", {}).get("message_id", "")
    text = message_data.get("chat_message", {}).get("content", "")
    timestamp = message_data.get("chat_message", {}).get("timestamp", "")
    name = message_data.get("name", "")
    username = message_data.get("username", "")

    user_exists = await database.user_exists(user_id)
    if not user_exists:
        await database.create_user({
            "user_id": int(user_id),
            "name": name,
            "username": username
        })

    chat_exists = await database.chat_exists(int(chat_id))
    if not chat_exists:
        await database.create_chat({
            "chat_id": int(chat_id),
            "last_known_name": str(chat_id),
            "users": [],
            "blocked_users": [],
            "admins": {}
        })
    
    user_in_chat = await database.is_user_in_chat(int(chat_id), int(user_id))
    if not user_in_chat:
        await database.add_user_to_chat(int(chat_id), int(user_id))

    analyze_language.apply_async(
        args=[text, chat_id, message_id, user_id, timestamp, name, username],
        queue=settings.RABBITMQ_WORKER_QUEUE
    )