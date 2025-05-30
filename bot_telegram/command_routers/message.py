from aiogram import types, Router
from middlewares.database.models import ChatMessage
from middlewares.rabbitmq.queue_manager import rabbitmq_manager
from middlewares.rabbitmq.mq_enums import GeneralBackendQueueMessageType
from settings import get_settings
import logging
import uuid

settings = get_settings()
message_router = Router(name='message_router')

@message_router.message()
async def handle_message(message: types.Message):
    if message.from_user.is_bot:
        return

    chat_message = ChatMessage(
        chat_id=str(message.chat.id),
        message_id=str(message.message_id),
        content=message.text or "",
        timestamp=str(message.date)
    )

    message_data = {
        "message_type": GeneralBackendQueueMessageType.TEXT_TO_ANALYZE,
        "user_id": message.from_user.id,
        "name": message.from_user.full_name,
        "username": message.from_user.username,
        "is_active": True,
        "chat_message": chat_message.dict()
    }

    guid = str(uuid.uuid4())
    await rabbitmq_manager.store_result(settings.RABBITMQ_GENERAL_QUEUE, guid, message_data)