from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from aiogram.types import Update
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

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logging.info("Starting up...")
    await database.setup()
    dp.update.middleware.register(database)
    
    webhook_info = await bot.get_webhook_info()
    if webhook_info.url != WEBHOOK_URL:
        logging.info(f"Setting webhook to {WEBHOOK_URL}")
        await bot.set_webhook(WEBHOOK_URL + WEBHOOK_PATH)
    
    asyncio.create_task(consume_telegram_queue_messages(bot))
    
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