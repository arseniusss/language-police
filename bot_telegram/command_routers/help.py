from aiogram import types, Router
from aiogram.filters.command import Command

help_router = Router(name='help_router')

@help_router.message(Command("help"))
async def start_command(message: types.Message):
    await message.reply("Hello! Here are the commands you can use:\n"
                        "/start - Start the bot\n" \
                        "/analyze_language - Analyze the language of a message (reply or provide text)\n" \
                        "/chat_stats - Get chat language analysis stats\n" \
                        "/global_stats - Get global language statistics of all chats\n" \
                        "/my_chat_stats - Get your contribution to the chat stats\n" \
                        "/my_global_stats - Get your contribution to the global stats\n" \
                        "/chat_global_top - Get top of all chats ranked by different metrics\n" \
                        "/chat_top - See the top of users in this chat\n" \
                        "/my_chat_ranking - Get your ranking in chat top statistics\n" \
                        "/global_top - Get top of all users in all chats\n" \
                        "/my_global_ranking - Get your ranking in global top\n" \
                        "/global_chat_ranking - Get this chat's ranking among all chats\n" \
                        "/chat_settings - Configure chat settings (admin only)\n" \
                        "/add_admins - Sync chat administrators with bot (admin only)\n" \
                        "/restrictions - View and manage user restrictions (admin only)\n" \
                        "/my_data - Download all your data as a .json file\n"
                        "/help - See the list of commands (see this message again)\n" \
)
