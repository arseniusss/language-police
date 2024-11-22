from fastapi import FastAPI, Request
from aiogram.types import Update
import uvicorn
import logging
import sys
from bot import dp, bot
from middlewares.database.db import database
from settings import get_settings

settings = get_settings()

WEBHOOK_URL = settings.WEBHOOK_URL
WEBHOOK_PATH = settings.WEBHOOK_PATH

app = FastAPI()

@app.post(WEBHOOK_PATH)
async def handle_webhook(request: Request):
    data = await request.json()
    update = Update(**data)
    await dp.feed_webhook_update(bot=bot, update=update)
    return {"status": "ok"}

@app.on_event("startup")
async def on_startup():
    logging.info("Starting up...")
    await database.setup()

    dp.update.middleware.register(database)

    webhook_info = await bot.get_webhook_info()
    if webhook_info.url != WEBHOOK_URL:
        logging.info(f"Setting webhook to {WEBHOOK_URL}")
        await bot.set_webhook(WEBHOOK_URL + WEBHOOK_PATH)

@app.on_event("shutdown")
async def on_shutdown():
    logging.info("Shutting down...")
    await bot.delete_webhook()
    await bot.session.close()

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        stream=sys.stdout
    )
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000, 
        log_level="info"
    )