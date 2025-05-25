from aiogram import types, Router
from aiogram.filters.command import Command

help_router = Router(name='help_router')

@help_router.message(Command("help"))
async def start_command(message: types.Message):
    await message.reply("Hello! Here are the commands you can use:\n")