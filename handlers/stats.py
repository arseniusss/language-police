from aiogram import types, Router
from aiogram.filters.command import Command

from ..middlewares.database.db import database
start_router = Router(name='stats_router')

@start_router.message(Command("stats"))
async def stats(message: types.Message):
    database.create_user()
    await message.reply("Hi")