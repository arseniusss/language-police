import logging
import io
from aiogram import Router, types
from aiogram.filters import Command
from aiogram.types import BufferedInputFile
from middlewares.database.db import database
from middlewares.database.models import User

logger = logging.getLogger(__name__)
user_data_router = Router(name="user_data_router")

@user_data_router.message(Command("my_data"))
async def get_my_data(message: types.Message):
    """
    Handles the /my_data command, allowing users to download their data.
    """
    user_id = message.from_user.id
    logger.info(f"User {user_id} requested their data.")

    user = await database.get_user(user_id)

    if not user:
        await message.reply("I don't have any data stored for you.")
        return

    try:
        # Serialize user data to JSON
        user_data_json = user.model_dump_json(indent=2, exclude_none=True)
        
        json_bytes = user_data_json.encode('utf-8')
        file_to_send = BufferedInputFile(json_bytes, filename=f"my_data_{user_id}.json")
        
        # Use message.bot to send the document
        await message.bot.send_document(
            chat_id=user_id, # Sending to the user's private chat
            document=file_to_send,
            caption="Here is your data. This includes your profile information, message history, and any restrictions."
        )
        
        # If the command was issued in a group, you might want to notify them there that the data was sent privately.
        if message.chat.id != user_id:
            await message.reply("I've sent your data to our private chat.")
            
        logger.info(f"Successfully sent data dump to user {user_id}")
    except Exception as e:
        logger.error(f"Error generating or sending data dump for user {user_id}: {e}", exc_info=True)
        await message.reply("Sorry, I encountered an error while preparing your data. Please try again later.")