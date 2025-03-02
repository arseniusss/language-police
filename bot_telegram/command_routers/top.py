from aiogram import types, Router
from aiogram.filters.command import Command
from middlewares.rabbitmq.queue_manager import rabbitmq_manager
from middlewares.rabbitmq.mq_enums import GeneralBackendQueueMessageType
import uuid
import logging
from settings import get_settings

settings = get_settings()

top_router = Router(name='top_router')

@top_router.message(Command("chat_top"))
async def chat_top(message: types.Message):
    logging.info(f"Chat top command received from user {message.from_user.id}")

    message_data = {
        "message_type": GeneralBackendQueueMessageType.CHAT_TOP_COMMAND_TG,
        "user_id": message.from_user.id,
        "chat_id": message.chat.id,
        "message_id": message.message_id,
    }

    guid = str(uuid.uuid4())
    await rabbitmq_manager.store_result(settings.RABBITMQ_GENERAL_QUEUE, guid, message_data)

    await message.reply("Processing chat top statistics...")

@top_router.message(Command("global_top"))
async def global_top(message: types.Message):
    logging.info(f"Global top command received from user {message.from_user.id}")

    message_data = {
        "message_type": GeneralBackendQueueMessageType.GLOBAL_TOP_COMMAND_TG,
        "user_id": message.from_user.id,
        "chat_id": message.chat.id,
        "message_id": message.message_id,
    }

    guid = str(uuid.uuid4())
    await rabbitmq_manager.store_result(settings.RABBITMQ_GENERAL_QUEUE, guid, message_data)

    await message.reply("Processing global top statistics...")