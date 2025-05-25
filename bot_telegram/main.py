from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from aiogram.types import Update, BotCommand
import uvicorn
import logging
import sys
import asyncio
from .bot_setup import dp, bot
from middlewares.database.db import database
from settings import get_settings
from bot_telegram.queue_handlers.main_handler import consume_telegram_queue_messages

settings = get_settings()

WEBHOOK_URL = settings.WEBHOOK_URL
WEBHOOK_PATH = settings.WEBHOOK_PATH

async def set_bot_commands():
    commands = [
        BotCommand(command="start", description="Start the bot"),
        BotCommand(command="help", description="See the list of commands"),
        BotCommand(command="analyze", description="Analyze the language of a message (reply or provide text)"),
        BotCommand(command="chat_stats", description="Get chat language analysis stats"),
        BotCommand(command="global_stats", description="Get global language statistics of all chats"),
        BotCommand(command="my_chat_stats", description="Get your contribution to the chat stats"),
        BotCommand(command="my_global_stats", description="Get your contribution to the global stats"),
        BotCommand(command="chat_global_top", description="Get top of all chats ranked by different metrics"),
        BotCommand(command="chat_top", description="See the top of users in this chat"),
        BotCommand(command="my_chat_ranking", description="Get your ranking in chat top statistics"),
        BotCommand(command="global_top", description="Get top of all users in all chats"),
        BotCommand(command="my_global_ranking", description="Get your ranking in global top"),
        BotCommand(command="global_chat_ranking", description="Get this chat's ranking among all chats"),
        BotCommand(command="chat_settings", description="Configure chat settings (admin only)"),
        BotCommand(command="add_admins", description="Sync chat administrators with bot (admin only)"),
        BotCommand(command="my_data", description="Download all your data as a .json file"),
    ]
    await bot.set_my_commands(commands)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logging.info("Starting up...")
    await database.setup()
    dp.update.middleware.register(database)
    
    webhook_info = await bot.get_webhook_info()
    if webhook_info.url != WEBHOOK_URL:
        logging.info(f"Setting webhook to {WEBHOOK_URL}")
        await bot.set_webhook(url = WEBHOOK_URL + WEBHOOK_PATH,
                              allowed_updates=[
                                "message",
                                "edited_message",
                                "callback_query",
                                "poll",
                                "chat_member",
                                "chat_join_request",
                                "my_chat_member",
                                "message_reaction",
                                "message_reaction_count"
                            ]
        )
    
    asyncio.create_task(consume_telegram_queue_messages(bot))
    await set_bot_commands()
    
    yield
    
    # Shutdown
    logging.info("Shutting down...")
    await bot.delete_webhook()
    await bot.session.close()

app = FastAPI(lifespan=lifespan)

@app.post(WEBHOOK_PATH)
async def handle_webhook(request: Request):
    data = await request.json()
    update = Update(**data)
    await dp.feed_webhook_update(bot=bot, update=update)
    return {"status": "ok"}

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )
    
    uvicorn.run(
        app, 
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        log_level="info"
    )