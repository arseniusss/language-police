from aiogram import types, Router
from aiogram.filters.command import Command
from middlewares.rabbitmq.queue_manager import rabbitmq_manager
from middlewares.rabbitmq.mq_enums import GeneralBackendQueueMessageType
import uuid
import logging
from settings import get_settings

settings = get_settings()

ranking_router = Router(name='ranking_router')

@ranking_router.message(Command("my_chat_ranking"))
async def my_chat_ranking(message: types.Message):
    logging.info(f"My chat ranking command received from user {message.from_user.id}")

    message_data = {
        "message_type": GeneralBackendQueueMessageType.MY_CHAT_RANKING_COMMAND_TG,
        "user_id": message.from_user.id,
        "chat_id": message.chat.id,
        "message_id": message.message_id,
    }

    guid = str(uuid.uuid4())
    await rabbitmq_manager.store_result(settings.RABBITMQ_GENERAL_QUEUE, guid, message_data)

    await message.reply("Finding your ranking in chat statistics...")

@ranking_router.message(Command("my_global_ranking"))
async def my_global_ranking(message: types.Message):
    logging.info(f"My global ranking command received from user {message.from_user.id}")

    message_data = {
        "message_type": GeneralBackendQueueMessageType.MY_GLOBAL_RANKING_COMMAND_TG,
        "user_id": message.from_user.id,
        "chat_id": message.chat.id,
        "message_id": message.message_id,
    }

    guid = str(uuid.uuid4())
    await rabbitmq_manager.store_result(settings.RABBITMQ_GENERAL_QUEUE, guid, message_data)

    await message.reply("Finding your ranking in global statistics...")