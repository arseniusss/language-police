from aiogram import types, Router, F
from aiogram.filters.command import Command
from middlewares.rabbitmq.queue_manager import rabbitmq_manager
from middlewares.rabbitmq.mq_enums import GeneralBackendQueueMessageType
import uuid
import logging
from settings import get_settings
from backend.functions.helpers.get_lang_display import get_language_display

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

@ranking_router.message(Command("global_chat_ranking"))
async def chat_ranking(message: types.Message):
    logging.info(f"Chat ranking command received from user {message.from_user.id}")

    message_data = {
        "message_type": GeneralBackendQueueMessageType.GLOBAL_CHAT_RANKING_COMMAND_TG,
        "user_id": message.from_user.id,
        "chat_id": message.chat.id,
    }

    guid = str(uuid.uuid4())
    await rabbitmq_manager.store_result(settings.RABBITMQ_GENERAL_QUEUE, guid, message_data)

    await message.reply("Finding this chat's ranking among all chats...")

@ranking_router.callback_query(F.data.startswith("my_chat_ranking_lang_"))
async def cb_my_chat_ranking_language(callback: types.CallbackQuery):
    language = callback.data.replace("my_chat_ranking_lang_", "")
    logging.info(f"My chat ranking language filter callback: {language}")
    
    message_data = {
        "message_type": GeneralBackendQueueMessageType.MY_CHAT_RANKING_COMMAND_TG,
        "user_id": callback.from_user.id,
        "chat_id": callback.message.chat.id,
        "message_id": callback.message.message_id,
        "language": language
    }

    guid = str(uuid.uuid4())
    await rabbitmq_manager.store_result(settings.RABBITMQ_GENERAL_QUEUE, guid, message_data)
    
    await callback.answer(f"Getting your ranking for {get_language_display(language)} messages...")

@ranking_router.callback_query(F.data.startswith("my_global_ranking_lang_"))
async def cb_my_global_ranking_language(callback: types.CallbackQuery):
    language = callback.data.replace("my_global_ranking_lang_", "")
    logging.info(f"My global ranking language filter callback: {language}")
    
    message_data = {
        "message_type": GeneralBackendQueueMessageType.MY_GLOBAL_RANKING_COMMAND_TG,
        "user_id": callback.from_user.id,
        "chat_id": callback.message.chat.id,
        "message_id": callback.message.message_id,
        "language": language
    }

    guid = str(uuid.uuid4())
    await rabbitmq_manager.store_result(settings.RABBITMQ_GENERAL_QUEUE, guid, message_data)
    
    await callback.answer(f"Getting your global ranking for {get_language_display(language)} messages...")

@ranking_router.callback_query(F.data.startswith("global_chat_ranking_lang_"))
async def cb_chat_ranking_language(callback: types.CallbackQuery):
    language = callback.data.replace("global_chat_ranking_lang_", "")
    logging.info(f"Chat ranking language filter callback: {language}")
    
    message_data = {
        "message_type": GeneralBackendQueueMessageType.GLOBAL_CHAT_RANKING_COMMAND_TG,
        "user_id": callback.from_user.id,
        "chat_id": callback.message.chat.id,
        "message_id": callback.message.message_id,
        "language": language
    }

    guid = str(uuid.uuid4())
    await rabbitmq_manager.store_result(settings.RABBITMQ_GENERAL_QUEUE, guid, message_data)
    
    await callback.answer(f"Getting chat ranking for {get_language_display(language)} messages...")

@ranking_router.callback_query(F.data == "my_chat_ranking_all_langs")
async def cb_my_chat_ranking_all_langs(callback: types.CallbackQuery):
    logging.info(f"My chat ranking all languages callback")
    
    message_data = {
        "message_type": GeneralBackendQueueMessageType.MY_CHAT_RANKING_COMMAND_TG,
        "user_id": callback.from_user.id,
        "chat_id": callback.message.chat.id,
        "message_id": callback.message.message_id,
    }

    guid = str(uuid.uuid4())
    await rabbitmq_manager.store_result(settings.RABBITMQ_GENERAL_QUEUE, guid, message_data)
    
    await callback.answer("Getting your ranking for all languages...")

@ranking_router.callback_query(F.data == "my_global_ranking_all_langs")
async def cb_my_global_ranking_all_langs(callback: types.CallbackQuery):
    logging.info(f"My global ranking all languages callback")
    
    message_data = {
        "message_type": GeneralBackendQueueMessageType.MY_GLOBAL_RANKING_COMMAND_TG,
        "user_id": callback.from_user.id,
        "chat_id": callback.message.chat.id,
        "message_id": callback.message.message_id,
    }

    guid = str(uuid.uuid4())
    await rabbitmq_manager.store_result(settings.RABBITMQ_GENERAL_QUEUE, guid, message_data)
    
    await callback.answer("Getting your global ranking for all languages...")

@ranking_router.callback_query(F.data == "global_chat_ranking_all_langs")
async def cb_chat_ranking_all_langs(callback: types.CallbackQuery):
    logging.info(f"Chat ranking all languages callback")
    
    message_data = {
        "message_type": GeneralBackendQueueMessageType.GLOBAL_CHAT_RANKING_COMMAND_TG,
        "user_id": callback.from_user.id,
        "chat_id": callback.message.chat.id,
        "message_id": callback.message.message_id,
    }

    guid = str(uuid.uuid4())
    await rabbitmq_manager.store_result(settings.RABBITMQ_GENERAL_QUEUE, guid, message_data)
    
    await callback.answer("Getting chat ranking for all languages...")