from aiogram import types, Router
from aiogram.filters.command import Command

start_router = Router(name='help_router')

@start_router.message(Command("start"))
async def start_command(message: types.Message):
    await message.reply("Hi")