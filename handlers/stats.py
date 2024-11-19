from aiogram import types, Router
from aiogram.filters.command import Command
from langdetect import detect
from middlewares.database.db import database
import logging

stats_router = Router(name='stats_router')

@stats_router.message(Command("stats"))
async def analyze_messages(message: types.Message):
    logging.info(f"Stats command received from user {message.from_user.id}")
    user = await database.get_user(message.from_user.id)
    if not user or not user.chat_history:
        logging.info("No messages found in history")
        await message.reply("No messages found in your history!")
        return
    
    analysis_result = []
    for chat_message in user.chat_history:
        try:
            if chat_message.content:
                lang = detect(chat_message.content)
                analysis_result.append(f"Message: {chat_message.content[:30]}...\nLanguage: {lang}\n")
        except Exception as e:
            logging.error(f"Error analyzing message: {e}")
            continue
    
    if analysis_result:
        response = "Language Analysis:\n\n" + "\n".join(analysis_result)
        await message.reply(response[:4000])
    else:
        await message.reply("No messages could be analyzed!")