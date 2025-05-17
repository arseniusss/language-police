import logging
from aiogram import Router, types, F, Bot
from aiogram.filters import ChatMemberUpdatedFilter, IS_NOT_MEMBER, IS_MEMBER, MEMBER, ADMINISTRATOR, CREATOR
from aiogram.types import ChatMemberUpdated, ChatMemberOwner, ChatMemberAdministrator
from middlewares.database.db import database

logger = logging.getLogger(__name__)

chat_events_router = Router(name='chat_events_router')

@chat_events_router.my_chat_member()
async def on_chat_member_updated(event: ChatMemberUpdated):
    """Handle updates to bot's chat member status"""
    logger.info(f"Bot's status changed in chat {event.chat.id}")
    
    # Update chat info in the database
    await update_chat_info(event.chat, event.bot)

@chat_events_router.message(F.migrate_to_chat_id)
async def on_chat_migration(message: types.Message):
    """Handle chat migration from group to supergroup"""
    source_chat_id = message.chat.id 
    target_chat_id = message.migrate_to_chat_id

    logger.info(f"Chat migration detected: from {source_chat_id} to {target_chat_id}")
    
    old_chat_db_entry = await database.get_chat(source_chat_id)
    
    if not old_chat_db_entry:
        logger.warning(f"Old chat {source_chat_id} not found in database during migration. Cannot copy settings.")
        # Even if old chat settings aren't copied, we should still migrate user histories
        # and create a basic entry for the new chat if it doesn't exist.
        # Check if the new chat already exists, if not, create it.
        new_chat_exists = await database.chat_exists(target_chat_id)
        if not new_chat_exists:
            new_chat_info_from_telegram = await message.bot.get_chat(target_chat_id)
            await database.create_chat({
                "chat_id": target_chat_id,
                "last_known_name": new_chat_info_from_telegram.title or str(target_chat_id),
                "users": [],
                "blocked_users": [],
                "admins": {}
            })
            logger.info(f"Created a new basic chat record for migrated chat {target_chat_id} as old one was not found.")
    else:
        old_chat_dict = old_chat_db_entry.dict(exclude={'id'}) # Exclude 'id' which Beanie might alias to _id
        old_chat_dict.pop("_id", None) # Explicitly pop _id as well for safety
        
        # Ensure no 'id' or '_id' field is present before creating the new chat document
        if 'id' in old_chat_dict:
            del old_chat_dict['id']
        if '_id' in old_chat_dict:
            del old_chat_dict['_id']
            
        old_chat_dict["chat_id"] = target_chat_id
        new_chat_info_from_telegram = await message.bot.get_chat(target_chat_id)
        old_chat_dict["last_known_name"] = new_chat_info_from_telegram.title or str(target_chat_id)
        
        # Check if a chat with target_chat_id already exists to prevent duplicate creation
        # This could happen if the migration event is processed multiple times or if there's a race condition.
        existing_target_chat = await database.get_chat(target_chat_id)
        if existing_target_chat:
            logger.warning(f"Chat {target_chat_id} already exists in database. Updating with migrated settings from {source_chat_id}.")
            # Update existing chat with potentially newer settings from the old chat
            # but be careful not to overwrite essential new chat data if it was created independently.
            # For simplicity here, we'll assume the migrated data is preferred.
            await database.update_chat(target_chat_id, old_chat_dict)
        else:
            await database.create_chat(old_chat_dict)
            logger.info(f"Created new chat record for {target_chat_id} by copying settings from {source_chat_id}.")

    # Update user chat histories using the new database method
    updated_users_count = await database.migrate_user_chat_histories(source_chat_id, target_chat_id)

    if updated_users_count > 0:
        logger.info(f"Successfully migrated chat history for {updated_users_count} users from chat {source_chat_id} to {target_chat_id}.")
    else:
        logger.info(f"No users found with chat history for old chat {source_chat_id} to migrate.")
    try:
        await message.bot.send_message(
            target_chat_id,
            f"📣 This group has been upgraded to a supergroup!\n"
            f"New chat ID: {target_chat_id}\n"
            f"All settings and message history references have been transferred."
        )
    except Exception as e:
        logger.error(f"Failed to send migration notification to {target_chat_id}: {e}")
        

@chat_events_router.chat_member()
async def on_admin_status_changed(event: ChatMemberUpdated):
    """Handles chat member admin status changes and updates the database."""
    logger.info(
        f"Admin status changed for user {event.new_chat_member.user.id} in chat {event.chat.id}. "
        f"Old status: {event.old_chat_member.status}, New status: {event.new_chat_member.status}"
    )

    chat_id = event.chat.id
    bot = event.bot

    try:
        chat_db_entry = await database.get_chat(chat_id)
        if not chat_db_entry:
            logger.warning(f"Chat {chat_id} not found in database. Attempting to create before updating admins.")
            await update_chat_info(event.chat, bot)
            chat_db_entry = await database.get_chat(chat_id)
            if not chat_db_entry:
                logger.error(f"Failed to create chat entry for {chat_id}. Cannot update admins.")
                return

        telegram_chat_admins = await bot.get_chat_administrators(chat_id)
        
        new_admins_dict = {}
        for admin in telegram_chat_admins:
            admin_id_str = str(admin.user.id)
            permissions = []
            if isinstance(admin, ChatMemberOwner):
                permissions = ["all"]
            elif isinstance(admin, ChatMemberAdministrator):
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
                permissions.append("manage_settings") 
            
            if permissions: 
                new_admins_dict[admin_id_str] = permissions

        await database.update_chat(chat_id, {"admins": new_admins_dict})
        logger.info(f"Successfully updated admin list for chat {chat_id} in the database. New admin count: {len(new_admins_dict)}")

    except Exception as e:
        logger.error(f"Error updating admin list for chat {chat_id}: {e}", exc_info=True)


@chat_events_router.message(F.new_chat_title)
async def on_chat_title_changed(message: types.Message):
    """Handle chat title changes"""
    new_title = message.chat.title
    chat_id = message.chat.id
    
    logger.info(f"Chat {chat_id} title changed to: {new_title}")
    
    # Update the chat name in the database
    chat = await database.get_chat(chat_id)
    if chat:
        old_name = chat.last_known_name
        await database.update_chat(chat_id, {"last_known_name": new_title})
        
        # Send notification using bot.send_message instead of message.answer
        try:
            await message.bot.send_message(
                chat_id,
                f"✅ Chat name updated automatically!\n"
                f"Previous name: {old_name}\n"
                f"New name: {new_title}"
            )
            logger.info(f"Successfully sent notification about name change in chat {chat_id}")
        except Exception as e:
            logger.error(f"Failed to send chat name update notification: {e}")
    else:
        # Create new chat entry if it doesn't exist
        await update_chat_info(message.chat, message.bot)
        
async def update_chat_info(chat: types.Chat, bot: Bot = None):
    """Update or create chat information in database"""
    chat_exists = await database.chat_exists(chat.id)
    
    if chat_exists:
        # Update existing chat
        await database.update_chat(chat.id, {"last_known_name": chat.title or str(chat.id)})
        logger.info(f"Updated chat {chat.id} name to: {chat.title}")
    else:
        # Create new chat
        await database.create_chat({
            "chat_id": chat.id,
            "last_known_name": chat.title or str(chat.id),
            "users": [],
            "blocked_users": [],
            "admins": {} # Initialize admins as an empty dictionary
        })
        logger.info(f"Created new chat {chat.id} with name: {chat.title}")
        
        # Welcome message for new chats
        if bot:
            try:
                await bot.send_message(
                    chat.id,
                    f"👋 Hello! I am Language Police Bot.\n\n"
                    f"I'm now tracking this chat. Administrators can use /chat_settings to configure me.\n"
                    f"If you're an admin, use /add_admins to sync permissions."
                )
            except Exception as e:
                logger.error(f"Failed to send welcome message: {e}")
        else:
            logger.warning(f"Could not send welcome message to chat {chat.id}: No bot instance provided")