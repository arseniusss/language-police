import logging
from middlewares.database.db import database

logger = logging.getLogger(__name__)

def get_chat_link(chat_id: int) -> str:
    """Generate a link to the chat based on its ID"""
    chat_link = f"https://t.me/c/{str(chat_id).replace('-100', '').replace('-', '')}"
    
    return chat_link

async def get_chat_name_with_link(chat_id: str|int) -> str:
    """Get chat name with link from database or use chat_id if not found"""
    try:
        chat = await database.get_chat(int(chat_id))
        chat_link = get_chat_link(chat_id)
        if chat and chat.last_known_name:
            return f'<a href="{chat_link}">{chat.last_known_name}</a>'
        else:
            return f'<a href="{chat_link}">Chat {chat_id}</a>'
    except Exception as e:
        logger.warning(f"Error getting chat name: {e}")
        return f"Chat {chat_id}"