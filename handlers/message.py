from aiogram import types, Router
from middlewares.database.models import ChatMessage
from middlewares.database.db import database
import httpx
from settings import get_settings

settings = get_settings()
message_router = Router(name='message_router')

@message_router.message()
async def handle_message(message: types.Message):
    if message.text and message.text.startswith("/"):
        return
    
    if message.from_user.is_bot:
        return

    if not await database.user_exists(message.from_user.id):
        await database.create_user({
            "user_id": message.from_user.id,
            "name": message.from_user.full_name,
            "username": message.from_user.username,
            "is_active": True
        })
    
    await database.add_chat_message(
        message.from_user.id, 
        ChatMessage(
            chat_id=str(message.chat.id),
            message_id=str(message.message_id),
            content=message.text or "",
            timestamp=str(message.date)
        )
    )

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{settings.BACKEND_URL}/analyze_message",
            json={
                "text": message.text,
                "chat_id": str(message.chat.id),
                "message_id": str(message.message_id),
                "user_id": message.from_user.id
            }
        )
        job_data = response.json()
        await message.reply(f"Processing your message. Job ID: {job_data['job_id']}")