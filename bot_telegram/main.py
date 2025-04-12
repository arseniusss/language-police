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
        BotCommand(command="help", description="Get help"),
        BotCommand(command="stats", description="Get language analysis stats"),
        BotCommand(command="my_chat_stats", description="Get your chat stats"),
        BotCommand(command="my_global_stats", description="Get your global stats"),
        BotCommand(command="chat_top", description="Get top statistics for the chat"),
        BotCommand(command="global_top", description="Get top statistics globally"),
        BotCommand(command="my_chat_ranking", description="Get your ranking in chat statistics"),
        BotCommand(command="my_global_ranking", description="Get your ranking in global statistics"),
        BotCommand(command="chat_settings", description="Configure chat settings (admin only)"),
        BotCommand(command="add_admins", description="Sync chat administrators with bot"),
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
                              allowed_updates=["message", "callback_query", "poll", "chat_member", "chat_join_request"])
    
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