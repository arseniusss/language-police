import logging
import random
from settings import get_settings
from backend.worker_handlers.analyze_language import analyze_language
from middlewares.database.db import database
from middlewares.database.models import User, Chat

settings = get_settings()

logger = logging.getLogger(__name__)

async def handle_text_to_analyze(message_data: dict):
    logger.info(f"Handling TEXT_TO_ANALYZE message:\n{message_data}")
    user_id = message_data.get("user_id", 0)
    chat_id = message_data.get("chat_message", {}).get("chat_id", "")
    message_id = message_data.get("chat_message", {}).get("message_id", "")
    text = message_data.get("chat_message", {}).get("content", "")
    timestamp = message_data.get("chat_message", {}).get("timestamp", "")
    name = message_data.get("name", "")
    username = message_data.get("username", "")

    # Ensure user exists in database
    user_exists = await database.user_exists(user_id)
    if not user_exists:
        await database.create_user({
            "user_id": int(user_id),
            "name": name,
            "username": username
        })
    else:
        # Update user name if it has changed
        user = await database.get_user(user_id)
        if user.name != name or user.username != username:
            await database.update_user(user_id, {"name": name, "username": username})

    # Ensure chat exists in database
    chat_exists = await database.chat_exists(int(chat_id))
    if not chat_exists:
        await database.create_chat({
            "chat_id": int(chat_id),
            "last_known_name": str(chat_id),
            "users": [],
            "blocked_users": [],
            "admins": {}
        })
    
    # Add user to chat if not already present
    user_in_chat = await database.is_user_in_chat(int(chat_id), int(user_id))
    if not user_in_chat:
        await database.add_user_to_chat(int(chat_id), int(user_id))
    
    # Get chat settings
    chat = await database.get_chat(int(chat_id))
    chat_settings = chat.chat_settings
    
    # Get user data to check message count
    user = await database.get_user(user_id)
    user_message_count = 0
    if str(chat_id) in user.chat_history:
        user_message_count = len(user.chat_history[str(chat_id)])
    
    # Check if we should analyze this message
    met_length_constraints = True

    # 1. Check message length constraints
    message_length = len(text)
    if (message_length < chat_settings.min_message_length_for_analysis or 
            message_length > chat_settings.max_message_length_for_analysis):
        logger.info(f"Skipping analysis: Message length {message_length} outside allowed range "
                   f"({chat_settings.min_message_length_for_analysis}-{chat_settings.max_message_length_for_analysis})")
        met_length_constraints = False
    
    met_random_freq_constraints = True
    # 2. Apply analysis frequency
    # If we've already determined we should skip analysis, don't bother with the random check
    if random.random() > chat_settings.analysis_frequency:
        logger.info(f"Skipping analysis: Random sampling based on frequency {chat_settings.analysis_frequency}")
        met_random_freq_constraints = False
    
    # 3. Check if this is a new member with less than min messages
    # Note: We still need to count the message, but we might not analyze it
    is_new_member = user_message_count < chat_settings.new_members_min_analyzed_messages
    
    # Always send to analysis if user is a new member under the threshold to build up their profile
    if is_new_member:
        logger.info(f"Analyzing message from new member: {user_message_count + 1}/{chat_settings.new_members_min_analyzed_messages} messages")
    
    should_analyze = met_length_constraints and (is_new_member or met_random_freq_constraints)

    # Send to analysis if all conditions are met
    if should_analyze:
        logger.info(f"Sending message for language analysis: user_id={user_id}, chat_id={chat_id}, message_id={message_id}")
        analyze_language.apply_async(
            args=[text, chat_id, message_id, user_id, timestamp, name, username],
            queue=settings.RABBITMQ_WORKER_QUEUE
        )