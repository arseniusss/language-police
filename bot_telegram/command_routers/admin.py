from aiogram import types, Router
from aiogram.filters.command import Command
from aiogram.types import ChatMemberAdministrator, ChatMemberOwner
from middlewares.database.db import database
from middlewares.database.models import Chat
import logging

logger = logging.getLogger(__name__)

admin_router = Router(name='admin_router')

@admin_router.message(Command("add_admins"))
async def add_admins_command(message: types.Message):
    """
    Command to sync Telegram chat admins with the bot's database.
    Fetches all admins/owners from Telegram and adds them to the bot's database.
    """
    # Check if in a group chat
    if message.chat.type == "private":
        await message.reply("This command can only be used in a group chat.")
        return
    
    try:
        # First check if the user is a Telegram admin
        chat_admins = await message.bot.get_chat_administrators(message.chat.id)
        admin_ids = [admin.user.id for admin in chat_admins]
        
        # If the user is not an admin in Telegram, deny access
        if message.from_user.id not in admin_ids:
            await message.reply("You need to be a chat administrator to use this command. Please, ask the chat owner to grant you admin rights.")
            logger.warning(f"User {message.from_user.id} attempted to use add_admins without admin rights")
            return
            
        # Send initial status message
        status_msg = await message.reply("Fetching chat administrators from Telegram...")
        
        # Get or create chat in database
        chat = await database.get_chat(message.chat.id)
        if not chat:
            # Create new chat document if it doesn't exist
            chat = Chat(
                chat_id=message.chat.id,
                last_known_name=message.chat.title or str(message.chat.id),
                admins={}
            )
        
        # Initialize or reset the admins dictionary
        chat.admins = {}
        
        # Process each admin
        for admin in chat_admins:
            admin_id = admin.user.id
            
            # Determine permissions based on admin type
            permissions = []
            if isinstance(admin, ChatMemberOwner):
                permissions = ["all"]  # Owner has all permissions
            elif isinstance(admin, ChatMemberAdministrator):
                # Add specific permissions based on admin rights
                if admin.can_delete_messages:
                    permissions.append("delete_messages")
                if admin.can_restrict_members:
                    permissions.append("restrict_members")
                if admin.can_promote_members:
                    permissions.append("promote_members")
                if admin.can_change_info:
                    permissions.append("change_info")
                if admin.can_invite_users:
                    permissions.append("invite_users")
                if admin.can_pin_messages:
                    permissions.append("pin_messages")
                
                # Add a default permission for all admins
                permissions.append("manage_settings")
            
            # Add admin to the chat's admins dictionary
            chat.admins[admin_id] = permissions
        
        # Update or create the chat in database
        if chat.id:  # If the chat already exists in DB
            await database.update_chat(message.chat.id, {"admins": chat.admins})
        else:
            await database.create_chat(chat)
        
        # Prepare admin list for display
        admin_text = "\n".join([
            f"• {admin.user.full_name} (@{admin.user.username or 'No username'})"
            for admin in chat_admins
        ])
        
        # Update status message with results
        await status_msg.edit_text(
            f"✅ Successfully synced {len(chat_admins)} administrators!\n\n"
            f"Admin list:\n{admin_text}\n\n"
            "These users now have access to bot administration commands."
        )
        
    except Exception as e:
        logging.error(f"Error syncing admins: {e}")
        await status_msg.edit_text(f"❌ Error syncing administrators: {str(e)}")

@admin_router.message(Command("refresh_chat_name"))
async def refresh_chat_name_command(message: types.Message):
    """
    Command to refresh/update the stored chat name in the database.
    Usage: /refresh_chat_name [new_name] (optional)
    If no name is provided, the current chat name will be used.
    """
    logger.info(f"Processing refresh_chat_name command from user {message.from_user.id} in chat {message.chat.id}")
    
    chat_admins = await message.bot.get_chat_administrators(message.chat.id)

    # Check admin status
    is_admin = str(message.from_user.id) in [str(admin.user.id) for admin in chat_admins]

    if not is_admin:
        await message.reply("You need to be an admin to refresh the chat name.")
        logger.warning(f"User {message.from_user.id} attempted to refresh chat name without admin rights")
        return
    
    chat_id = message.chat.id
    
    # Parse command to extract optional new name
    # Format: /refresh_chat_name [new_name]
    command_parts = message.text.split(maxsplit=1)
    
    if len(command_parts) > 1:
        # User provided a custom name
        new_name = command_parts[1].strip()
        if not new_name:
            await message.reply("The chat name cannot be empty.")
            return
    else:
        # Use current chat name
        new_name = message.chat.title if message.chat.title else str(chat_id)
    
    # Get current chat data
    chat = await database.get_chat(chat_id)
    if not chat:
        await message.reply("Chat not found in database. Please try again later.")
        logger.warning(f"Chat {chat_id} not found in database")
        return
    
    old_name = chat.last_known_name
    
    # Update the chat name
    await database.update_chat(chat_id, {"last_known_name": new_name})
    
    await message.reply(f"Chat name updated successfully!\n\nOld name: {old_name}\nNew name: {new_name}")
    logger.info(f"Chat {chat_id} name updated from '{old_name}' to '{new_name}'")