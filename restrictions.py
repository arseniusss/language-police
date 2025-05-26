from aiogram import types, Router, F
from aiogram.filters.command import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any

from middlewares.database.db import database
from middlewares.database.models import Chat, RestrictionType
from bot_telegram.command_routers.settings import is_user_admin

logger = logging.getLogger(__name__)

restrictions_router = Router(name='restrictions_router')

# Define states for the restrictions flow
class RestrictionsStates(StatesGroup):
    waiting_chat_selection = State()
    waiting_restriction_type = State()
    waiting_user_selection = State()
    viewing_user_restrictions = State()

# Helper function to format restriction type for display
def format_restriction_type(restriction_type):
    """Format restriction type with emoji for better visibility"""
    type_mapping = {
        RestrictionType.WARNING.value: "⚠️ Warning",
        RestrictionType.TIMEOUT.value: "⏱️ Timeout",
        RestrictionType.TEMPORARY_BAN.value: "🚫 Temporary Ban",
        RestrictionType.PERMANENT_BAN.value: "🔒 Permanent Ban"
    }
    return type_mapping.get(restriction_type, f"Unknown ({restriction_type})")

# Helper function to format user info for display
def format_user_info(user_data):
    """Format user info for display in restrictions list"""
    name = user_data.get("name", "Unknown User")
    username = user_data.get("username", "")
    user_id = user_data.get("user_id", "")
    
    if username:
        return f"{name} ({user_id})"
    return f"{name} ({user_id})"

# Helper function to format restriction details
def format_restriction_detail(restriction):
    """Format a single restriction for detailed view"""
    # Parse timestamp
    try:
        timestamp = datetime.fromisoformat(restriction["timestamp"])
        formatted_time = timestamp.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, TypeError):
        formatted_time = "Unknown time"
    
    # Format duration if available
    duration_text = ""
    if restriction.get("duration_seconds"):
        duration = timedelta(seconds=restriction["duration_seconds"])
        days, seconds = duration.days, duration.seconds
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        
        duration_parts = []
        if days > 0:
            duration_parts.append(f"{days} day{'s' if days != 1 else ''}")
        if hours > 0:
            duration_parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes > 0:
            duration_parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        if seconds > 0 and not (days or hours or minutes):
            duration_parts.append(f"{seconds} second{'s' if seconds != 1 else ''}")
        
        duration_text = f"\nDuration: {', '.join(duration_parts)}"
    
    # Create the message
    message = f"{format_restriction_type(restriction['restriction_type'])}\n"
    message += f"Time: {formatted_time}{duration_text}\n"
    
    # Add message excerpt if available (truncate if too long)
    if restriction.get("message_text"):
        message_text = restriction["message_text"]
        if len(message_text) > 100:
            message_text = message_text[:97] + "..."
        message += f"Message: {message_text}"
    
    # Add link to original message if available
    if restriction.get("chat_id") and restriction.get("message_id"):
        chat_id = restriction["chat_id"]
        message_id = restriction["message_id"]
        message += f"\n\n[Link to message](https://t.me/c/{str(chat_id).replace('-100', '')}/{message_id})"
    
    return message

# Custom functions to work with the database that weren't provided
async def get_restricted_users_in_chat(chat_id: int, restriction_type: str = 'all') -> List[Dict[str, Any]]:
    """Get users who have restrictions in the specified chat"""
    result = []
    
    # Get all users
    async for user_doc in database.db["users"].find({}):
        user = user_doc.copy()
        
        # Count restrictions for this chat
        restriction_count = 0
        for record in user.get("restriction_history", []):
            if str(record.get("chat_id")) == str(chat_id):
                # Filter by restriction type if specified
                if restriction_type == 'all' or record.get("restriction_type") == restriction_type:
                    restriction_count += 1
        
        # If user has restrictions in this chat, add to result
        if restriction_count > 0:
            result.append({
                "user_id": user.get("user_id"),
                "name": user.get("name"),
                "username": user.get("username"),
                "restriction_count": restriction_count
            })
    
    # Sort users by restriction count (descending)
    return sorted(result, key=lambda x: x["restriction_count"], reverse=True)

async def get_user_restrictions(chat_id: int, user_id: int) -> List[Dict[str, Any]]:
    """Get all restrictions for a specific user in a specific chat"""
    user_doc = await database.db["users"].find_one({"user_id": user_id})
    
    if not user_doc:
        return []
    
    # Filter restriction history to only include the specified chat
    restrictions = []
    for record in user_doc.get("restriction_history", []):
        if str(record.get("chat_id")) == str(chat_id):
            restrictions.append(record)
    
    # Sort by timestamp (newest first)
    return sorted(restrictions, key=lambda x: x.get("timestamp", ""), reverse=True)

@restrictions_router.message(Command("restrictions"))
async def restrictions_command(message: types.Message, state: FSMContext):
    """Show list of chats where the user is an admin to view restrictions"""
    logger.info(f"User {message.from_user.id} requested restrictions command")
    
    # Clear any existing state
    await state.clear()
    
    # Show the list of chats where the user is an admin
    await show_admin_chats(message, state)

async def show_admin_chats(message: types.Message, state: FSMContext):
    """Show a list of chats where the user is an admin"""
    logger.info(f"Showing admin chats for user {message.from_user.id} to view restrictions")
    
    # Find all chats where the user is admin
    admin_chats = []
    async for chat in database.db["chats"].find({}):
        if str(message.from_user.id) in chat.get("admins", {}):
            admin_chats.append(Chat(**chat))
    
    if not admin_chats:
        await message.reply(
            "You are not an administrator in any chats, or your admin status hasn't been synced yet.\n\n"
            "To sync admin status, use the /add_admins command in the group chat."
        )
        logger.info(f"No admin chats found for user {message.from_user.id}")
        return
    
    builder = InlineKeyboardBuilder()
    for chat in admin_chats:
        builder.button(
            text=chat.last_known_name or f"Chat {chat.chat_id}", 
            callback_data=f"rest_chat_{chat.chat_id}"
        )
    builder.adjust(1)
    
    await message.reply(
        "Select a chat to view restrictions:",
        reply_markup=builder.as_markup()
    )
    
    await state.set_state(RestrictionsStates.waiting_chat_selection)
    logger.info(f"Displayed {len(admin_chats)} admin chats for user {message.from_user.id} to view restrictions")


@restrictions_router.callback_query(F.data.startswith("rest_chat_"), RestrictionsStates.waiting_chat_selection)
async def select_chat_callback(callback: types.CallbackQuery, state: FSMContext):
    """Handle chat selection for viewing restrictions"""
    chat_id = callback.data.split("_")[2]
    
    # Check if user is still an admin
    chat_doc = await database.db["chats"].find_one({"chat_id": int(chat_id)})
    if not chat_doc or str(callback.from_user.id) not in chat_doc.get("admins", {}):
        await callback.answer("You are no longer an admin in this chat.", show_alert=True)
        logger.warning(f"User {callback.from_user.id} attempted to access restrictions without admin rights")
        return
    
    # Save chat ID to state
    await state.update_data(chat_id=chat_id)
    
    logger.info(f"User {callback.from_user.id} selected chat {chat_id} to view restrictions")
    
    # Show restriction type filter options
    await show_restriction_types(callback.message, state)

async def show_restriction_types(message: types.Message, state: FSMContext):
    """Show restriction type filter options"""
    builder = InlineKeyboardBuilder()
    
    # Add buttons for each restriction type
    builder.button(text="All Types", callback_data="rest_type_all")
    builder.button(text=format_restriction_type(RestrictionType.WARNING.value), callback_data=f"rest_type_{RestrictionType.WARNING.value}")
    builder.button(text=format_restriction_type(RestrictionType.TIMEOUT.value), callback_data=f"rest_type_{RestrictionType.TIMEOUT.value}")
    builder.button(text=format_restriction_type(RestrictionType.TEMPORARY_BAN.value), callback_data=f"rest_type_{RestrictionType.TEMPORARY_BAN.value}")
    builder.button(text=format_restriction_type(RestrictionType.PERMANENT_BAN.value), callback_data=f"rest_type_{RestrictionType.PERMANENT_BAN.value}")
    builder.adjust(1)
    
    await message.edit_text(
        "Select a restriction type to filter by:",
        reply_markup=builder.as_markup()
    )
    
    await state.set_state(RestrictionsStates.waiting_restriction_type)

@restrictions_router.callback_query(F.data.startswith("rest_type_"), RestrictionsStates.waiting_restriction_type)
async def select_restriction_type_callback(callback: types.CallbackQuery, state: FSMContext):
    """Handle restriction type selection"""
    restriction_type = callback.data.split("_")[2]
    
    # Save restriction type to state
    await state.update_data(restriction_type=restriction_type)
    
    data = await state.get_data()
    chat_id = data['chat_id']
    
    logger.info(f"User {callback.from_user.id} selected restriction type {restriction_type} for chat {chat_id}")
    
    # Show users with restrictions
    await show_restricted_users(callback.message, state, 0)

async def show_restricted_users(message: types.Message, state: FSMContext, page: int = 0):
    """Show users with restrictions in the selected chat"""
    data = await state.get_data()
    chat_id = data['chat_id']
    restriction_type = data.get('restriction_type', 'all')
    
    # Get chat info
    chat_doc = await database.db["chats"].find_one({"chat_id": chat_id})
    chat = Chat(**chat_doc) if chat_doc else None
    chat_name = chat.last_known_name if chat else f"Chat {chat_id}"
    
    # Get users with restrictions in this chat
    users = await get_restricted_users_in_chat(chat_id, restriction_type)
    
    if not users:
        await message.edit_text(
            f"No users with {restriction_type} restrictions found in {chat_name}.\n\n"
            f"Use /restrictions to start again."
        )
        await state.clear()
        return
    
    # Pagination setup
    per_page = 5
    total_pages = (len(users) + per_page - 1) // per_page
    start_idx = page * per_page
    end_idx = min(start_idx + per_page, len(users))
    current_users = users[start_idx:end_idx]
    
    builder = InlineKeyboardBuilder()
    for user in current_users:
        builder.button(
            text=f"{format_user_info(user)} ({user['restriction_count']})", 
            callback_data=f"rest_user_{user['user_id']}"
        )
    
    # Add pagination buttons if needed
    if total_pages > 1:
        pagination_row = []
        if page > 0:
            pagination_row.append(types.InlineKeyboardButton(text="◀️ Previous", callback_data=f"rest_page_{page-1}"))
        if page < total_pages - 1:
            pagination_row.append(types.InlineKeyboardButton(text="Next ▶️", callback_data=f"rest_page_{page+1}"))
        builder.row(*pagination_row)
    
    # Add back button
    builder.button(text="⬅️ Back to Restriction Types", callback_data="rest_back_types")
    
    builder.adjust(1)
    
    await message.edit_text(
        f"Users with {restriction_type} restrictions in {chat_name}:\n"
        f"(Page {page + 1}/{total_pages}, sorting by most restrictions)",
        reply_markup=builder.as_markup()
    )
    
    await state.set_state(RestrictionsStates.waiting_user_selection)
    await state.update_data(current_page=page)

@restrictions_router.callback_query(F.data.startswith("rest_page_"), RestrictionsStates.waiting_user_selection)
async def pagination_callback(callback: types.CallbackQuery, state: FSMContext):
    """Handle pagination of users with restrictions"""
    page = int(callback.data.split("_")[2])
    await show_restricted_users(callback.message, state, page)

@restrictions_router.callback_query(F.data == "rest_back_types", RestrictionsStates.waiting_user_selection)
async def back_to_types_callback(callback: types.CallbackQuery, state: FSMContext):
    """Return to restriction type selection"""
    await show_restriction_types(callback.message, state)

@restrictions_router.callback_query(F.data.startswith("rest_user_"), RestrictionsStates.waiting_user_selection)
async def select_user_callback(callback: types.CallbackQuery, state: FSMContext):
    """Handle user selection to view their restrictions"""
    user_id = int(callback.data.split("_")[2])
    
    # Save user ID to state
    await state.update_data(user_id=user_id)
    
    data = await state.get_data()
    chat_id = data['chat_id']
    
    logger.info(f"User {callback.from_user.id} selected user {user_id} to view restrictions in chat {chat_id}")
    
    # Show user's restrictions
    await show_user_restrictions(callback.message, state, 0)

async def show_user_restrictions(message: types.Message, state: FSMContext, page: int = 0):
    """Show restrictions for the selected user"""
    data = await state.get_data()
    chat_id = data['chat_id']
    user_id = data['user_id']
    restriction_type = data.get('restriction_type', 'all')
    
    # Get chat info
    chat_doc = await database.db["chats"].find_one({"chat_id": chat_id})
    chat = Chat(**chat_doc) if chat_doc else None
    chat_name = chat.last_known_name if chat else f"Chat {chat_id}"
    
    # Get user's restrictions
    all_restrictions = await get_user_restrictions(chat_id, user_id)
    
    # Filter by type if needed
    if restriction_type != 'all':
        restrictions = [r for r in all_restrictions if r['restriction_type'] == restriction_type]
    else:
        restrictions = all_restrictions
    
    if not restrictions:
        # If no restrictions after filtering, show message
        await message.edit_text(
            f"No {restriction_type} restrictions found for this user in {chat_name}.\n\n"
            f"Use /restrictions to start again."
        )
        return
    
    # Pagination setup - changed from 1 to 5 restrictions per page
    per_page = 5
    total_pages = (len(restrictions) + per_page - 1) // per_page
    start_idx = page * per_page
    end_idx = min(start_idx + per_page, len(restrictions))
    current_restrictions = restrictions[start_idx:end_idx]
    
    # Format restrictions details
    restrictions_text = []
    for i, restriction in enumerate(current_restrictions, start=1):
        detail = format_restriction_detail(restriction)
        restrictions_text.append(f"— Restriction {start_idx + i} —\n{detail}\n")
    
    restrictions_detail = "\n".join(restrictions_text)
    
    builder = InlineKeyboardBuilder()
    
    # Add pagination buttons
    pagination_row = []
    if page > 0:
        pagination_row.append(types.InlineKeyboardButton(text="◀️ Previous", callback_data=f"rest_detail_{page-1}"))
    if page < total_pages - 1:
        pagination_row.append(types.InlineKeyboardButton(text="Next ▶️", callback_data=f"rest_detail_{page+1}"))
    
    if pagination_row:
        builder.row(*pagination_row)
    
    # Add back button
    builder.button(text="⬅️ Back to Users List", callback_data="rest_back_users")
    
    builder.adjust(1)
    
    # Get targeted user info
    user_doc = await database.db["users"].find_one({"user_id": user_id})
    user_name = user_doc.get("name", f"User {user_id}") if user_doc else f"User {user_id}"
    
    await message.edit_text(
        f"Restrictions for {user_name} in {chat_name}:\n"
        f"(Page {page + 1}/{total_pages}, showing {len(current_restrictions)} of {len(restrictions)} restrictions)\n\n"
        f"{restrictions_detail}",
        reply_markup=builder.as_markup(),
        parse_mode="Markdown"
    )
    
    await state.set_state(RestrictionsStates.viewing_user_restrictions)
    await state.update_data(current_detail_page=page)

@restrictions_router.callback_query(F.data.startswith("rest_detail_"), RestrictionsStates.viewing_user_restrictions)
async def restriction_detail_pagination(callback: types.CallbackQuery, state: FSMContext):
    """Handle pagination of user restrictions details"""
    page = int(callback.data.split("_")[2])
    await show_user_restrictions(callback.message, state, page)

@restrictions_router.callback_query(F.data == "rest_back_users", RestrictionsStates.viewing_user_restrictions)
async def back_to_users_callback(callback: types.CallbackQuery, state: FSMContext):
    """Return to users list"""
    data = await state.get_data()
    page = data.get('current_page', 0)
    await show_restricted_users(callback.message, state, page)