from aiogram import types, Router, F
from aiogram.filters.command import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from middlewares.rabbitmq.queue_manager import rabbitmq_manager
from middlewares.rabbitmq.mq_enums import GeneralBackendQueueMessageType
import uuid
import logging
from settings import get_settings
from backend.functions.helpers.get_lang_display import get_language_display

settings = get_settings()

top_router = Router(name='top_router')

@top_router.message(Command("chat_top"))
async def chat_top(message: types.Message):
    logging.info(f"Chat top command received from user {message.from_user.id}")

    message_data = {
        "message_type": GeneralBackendQueueMessageType.CHAT_TOP_COMMAND_TG,
        "user_id": message.from_user.id,
        "chat_id": message.chat.id,
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
    }

    guid = str(uuid.uuid4())
    await rabbitmq_manager.store_result(settings.RABBITMQ_GENERAL_QUEUE, guid, message_data)

    await message.reply("Processing global top statistics...")

@top_router.callback_query(F.data.startswith("chat_top_lang_"))
async def cb_chat_top_language(callback: types.CallbackQuery):
    language = callback.data.replace("chat_top_lang_", "")
    logging.info(f"Chat top language filter callback: {language}")
    
    message_data = {
        "message_type": GeneralBackendQueueMessageType.CHAT_TOP_COMMAND_TG,
        "user_id": callback.from_user.id,
        "chat_id": callback.message.chat.id,
        "message_id": callback.message.message_id,
        "language": language
    }

    guid = str(uuid.uuid4())
    await rabbitmq_manager.store_result(settings.RABBITMQ_GENERAL_QUEUE, guid, message_data)
    
    await callback.answer(f"Getting stats for {get_language_display(language)} messages...")

@top_router.callback_query(F.data.startswith("global_top_lang_"))
async def cb_global_top_language(callback: types.CallbackQuery):
    language = callback.data.replace("global_top_lang_", "")
    logging.info(f"Global top language filter callback: {language}")
    
    message_data = {
        "message_type": GeneralBackendQueueMessageType.GLOBAL_TOP_COMMAND_TG,
        "user_id": callback.from_user.id,
        "chat_id": callback.message.chat.id,
        "message_id": callback.message.message_id,
        "language": language
    }

    guid = str(uuid.uuid4())
    await rabbitmq_manager.store_result(settings.RABBITMQ_GENERAL_QUEUE, guid, message_data)
    
    await callback.answer(f"Getting global stats for {get_language_display(language)} messages...")

@top_router.callback_query(F.data == "chat_top_all_langs")
async def cb_chat_top_all_langs(callback: types.CallbackQuery):
    logging.info(f"Chat top all languages callback")
    
    message_data = {
        "message_type": GeneralBackendQueueMessageType.CHAT_TOP_COMMAND_TG,
        "user_id": callback.from_user.id,
        "chat_id": callback.message.chat.id,
        "message_id": callback.message.message_id,
    }

    guid = str(uuid.uuid4())
    await rabbitmq_manager.store_result(settings.RABBITMQ_GENERAL_QUEUE, guid, message_data)
    
    await callback.answer("Getting stats for all languages...")

@top_router.callback_query(F.data == "global_top_all_langs")
async def cb_global_top_all_langs(callback: types.CallbackQuery):
    logging.info(f"Global top all languages callback")
    
    message_data = {
        "message_type": GeneralBackendQueueMessageType.GLOBAL_TOP_COMMAND_TG,
        "user_id": callback.from_user.id,
        "chat_id": callback.message.chat.id,
        "message_id": callback.message.message_id,
    }

    guid = str(uuid.uuid4())
    await rabbitmq_manager.store_result(settings.RABBITMQ_GENERAL_QUEUE, guid, message_data)
    
    await callback.answer("Getting global stats for all languages...")


@top_router.message(Command("chat_global_top"))
async def chat_global_top(message: types.Message):
    logging.info(f"Chat global top command received from user {message.from_user.id}")

    message_data = {
        "message_type": GeneralBackendQueueMessageType.CHAT_GLOBAL_TOP_COMMAND_TG,
        "user_id": message.from_user.id,
        "chat_id": message.chat.id,
    }

    guid = str(uuid.uuid4())
    await rabbitmq_manager.store_result(settings.RABBITMQ_GENERAL_QUEUE, guid, message_data)

    await message.reply("Processing global chat top statistics...")

@top_router.callback_query(F.data.startswith("chat_global_top_lang_"))
async def cb_chat_global_top_language(callback: types.CallbackQuery):
    language = callback.data.replace("chat_global_top_lang_", "")
    logging.info(f"Chat global top language filter callback: {language}")
    
    message_data = {
        "message_type": GeneralBackendQueueMessageType.CHAT_GLOBAL_TOP_COMMAND_TG,
        "user_id": callback.from_user.id,
        "chat_id": callback.message.chat.id,
        "message_id": callback.message.message_id,
        "language": language
    }

    guid = str(uuid.uuid4())
    await rabbitmq_manager.store_result(settings.RABBITMQ_GENERAL_QUEUE, guid, message_data)
    
    await callback.answer(f"Getting chat rankings for {get_language_display(language)} messages...")

@top_router.callback_query(F.data == "chat_global_top_all_langs")
async def cb_chat_global_top_all_langs(callback: types.CallbackQuery):
    logging.info(f"Chat global top all languages callback")
    
    message_data = {
        "message_type": GeneralBackendQueueMessageType.CHAT_GLOBAL_TOP_COMMAND_TG,
        "user_id": callback.from_user.id,
        "chat_id": callback.message.chat.id,
        "message_id": callback.message.message_id,
    }

    guid = str(uuid.uuid4())
    await rabbitmq_manager.store_result(settings.RABBITMQ_GENERAL_QUEUE, guid, message_data)
    
    await callback.answer("Getting chat rankings for all languages...")