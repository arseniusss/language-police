from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from .command_routers import main_router
from settings import get_settings
import logging

settings = get_settings()

bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)

storage = MemoryStorage()
dp = Dispatcher(bot=bot, storage=storage, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp.include_router(main_router)

@dp.errors()
async def error_handler(exception):
    logging.exception("Unhandled exception: %s", exception)
    return True