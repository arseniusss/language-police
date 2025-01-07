from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from .command_routers import main_router
from settings import get_settings


settings = get_settings()

bot = Bot(token=settings.TELEGRAM_BOT_TOKEN)

storage = MemoryStorage()
dp = Dispatcher(bot=bot, storage=storage, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp.include_router(main_router)