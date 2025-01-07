from aiogram import types, Router
from aiogram.filters.command import Command
from middlewares.rabbitmq.queue_manager import rabbitmq_manager
from middlewares.rabbitmq.mq_enums import GeneralBackendQueueMessageType
import uuid
import logging
from settings import get_settings

settings = get_settings()

stats_router = Router(name='stats_router')

@stats_router.message(Command("stats"))
async def analyze_messages(message: types.Message):
    logging.info(f"Stats command received from user {message.from_user.id}")

    message_data = {
        "message_type": GeneralBackendQueueMessageType.STATS_COMMAND_TG,
        "user_id": message.from_user.id,
        "chat_id": message.chat.id,
        "message_id": message.message_id,
    }

    guid = str(uuid.uuid4())
    await rabbitmq_manager.store_result_sync(settings.RABBITMQ_GENERAL_QUEUE, guid, message_data)

    await message.reply("Your stats request is being processed!")