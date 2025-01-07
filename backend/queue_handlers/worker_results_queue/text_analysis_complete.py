import logging
from typing import Dict, Any
from middlewares.database.db import database
from middlewares.database.models import ChatMessage
from settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

async def handle_text_analysis_compete(message_data: dict [str, Any]):
    logger.info(f"Handling TEXT_ANALYSIS_COMPLETED queue message:\n{message_data}")
    user_id = message_data.get("user_id", 0)
    name = message_data.get("name", "")
    username = message_data.get("username", "")
    chat_id = message_data.get("chat_id", "")
    message_id = message_data.get("message_id", "")
    text = message_data.get("text", "")
    timestamp = message_data.get("timestamp", "")
    analysis_result = message_data.get("analysis_result", [])

    user_exits = await database.user_exists(user_id)

    if not user_exits:
        await database.create_user({
            "user_id": user_id,
            "name": name,
            "username": username,
            "is_active": True
            
        })
    
    await database.add_chat_message(user_id, ChatMessage(chat_id=chat_id, message_id=message_id, content=text, timestamp=timestamp, analysis_result=analysis_result))