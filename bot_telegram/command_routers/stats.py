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

@stats_router.message(Command("my_chat_stats"))
async def my_chat_stats(message: types.Message):
    logging.info(f"My chat stats command received from user {message.from_user.id}")

    message_data = {
        "message_type": GeneralBackendQueueMessageType.MY_CHAT_STATS_COMMAND_TG,
        "user_id": message.from_user.id,
        "chat_id": message.chat.id,
        "message_id": message.message_id,
    }

    guid = str(uuid.uuid4())
    await rabbitmq_manager.store_result(settings.RABBITMQ_GENERAL_QUEUE, guid, message_data)

    await message.reply("Your chat stats request is being processed!")

@stats_router.message(Command("my_global_stats"))
async def my_global_stats(message: types.Message):
    logging.info(f"My global stats command received from user {message.from_user.id}")

    message_data = {
        "message_type": GeneralBackendQueueMessageType.MY_GLOBAL_STATS_COMMAND_TG,
        "chat_id": message.chat.id,
        "user_id": message.from_user.id,
        "message_id": message.message_id,
    }

    guid = str(uuid.uuid4())
    await rabbitmq_manager.store_result(settings.RABBITMQ_GENERAL_QUEUE, guid, message_data)

    await message.reply("Your global stats request is being processed!")

@stats_router.message(Command("chat_stats"))
async def chat_stats(message: types.Message):
    logging.info(f"Chat stats command received from user {message.from_user.id} in chat {message.chat.id}")
    
    message_data = {
        "message_type": GeneralBackendQueueMessageType.CHAT_STATS_COMMAND_TG,
        "user_id": message.from_user.id,
        "chat_id": message.chat.id,
        "message_id": message.message_id,
    }
    
    guid = str(uuid.uuid4())
    await rabbitmq_manager.store_result(settings.RABBITMQ_GENERAL_QUEUE, guid, message_data)
    
    await message.reply("Processing chat statistics...")

@stats_router.message(Command("global_stats"))
async def global_stats(message: types.Message):
    logging.info(f"Global stats command received from user {message.from_user.id}")
    
    message_data = {
        "message_type": GeneralBackendQueueMessageType.GLOBAL_STATS_COMMAND_TG,
        "user_id": message.from_user.id,
        "chat_id": message.chat.id,
        "message_id": message.message_id,
    }
    
    guid = str(uuid.uuid4())
    await rabbitmq_manager.store_result(settings.RABBITMQ_GENERAL_QUEUE, guid, message_data)
    
    await message.reply("Processing global statistics...")