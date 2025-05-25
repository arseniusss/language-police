from aiogram import types, Router
from aiogram.filters.command import Command
from middlewares.database.db import database


start_router = Router(name='start_router')

@start_router.message(Command("start"))
async def start_command(message: types.Message):
    user_data = {
        "user_id": message.from_user.id,
        "name": message.from_user.full_name,
        "is_active": True
    }
    
    if not await database.user_exists(message.from_user.id):
        await database.create_user(user_data)
        await message.reply(f"Welcome, {user_data['name']}! You've been successfully registered in our system.")
    else:
        await message.reply(f"Welcome back, {user_data['name']}! You are already registered in our system. If you want information about specific commands, please type /help.")