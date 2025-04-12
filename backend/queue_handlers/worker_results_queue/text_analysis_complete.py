import logging
from typing import Dict, Any, List
from datetime import datetime, timedelta
from middlewares.database.db import database
from middlewares.database.models import ChatMessage, ModerationRule, Restriction, RestrictionRecord
from middlewares.rabbitmq.queue_manager import rabbitmq_manager
from middlewares.rabbitmq.mq_enums import TelegramQueueMessageType
from settings import get_settings
from backend.utils.logging_config import logger

settings = get_settings()
logger = logger.getChild('text_analysis_complete')

async def handle_text_analysis_compete(message_data: dict[str, Any]):
    logger.info(f"Handling TEXT_ANALYSIS_COMPLETED queue message:\n{message_data}")
    user_id = message_data.get("user_id", 0)
    name = message_data.get("name", "")
    username = message_data.get("username", "")
    chat_id = message_data.get("chat_id", "")
    message_id = message_data.get("message_id", "")
    text = message_data.get("text", "")
    timestamp = message_data.get("timestamp", "")
    analysis_result = message_data.get("analysis_result", [])

    user_exists = await database.user_exists(user_id)

    if not user_exists:
        await database.create_user({
            "user_id": user_id,
            "name": name,
            "username": username,
            "is_active": True
        })
    
    # Add the message to user's chat history
    await database.add_chat_message(
        user_id, 
        ChatMessage(
            chat_id=chat_id, 
            message_id=message_id, 
            content=text, 
            timestamp=timestamp, 
            analysis_result=analysis_result
        )
    )
    
    # Check if this message violates any moderation rules
    await check_moderation_rules(user_id, chat_id, message_id, text, analysis_result, name)

async def check_moderation_rules(user_id: int, chat_id: str, message_id: str, text: str, analysis_result: List, user_name: str):
    """Check if the message violates any moderation rules and take appropriate action"""
    logger.info(f"Checking moderation rules for user {user_id} in chat {chat_id}")
    
    # Get chat settings and moderation rules
    chat = await database.get_chat(int(chat_id))
    if not chat or not chat.chat_settings or not chat.chat_settings.moderation_rules:
        logger.info("No moderation rules found for this chat")
        return
    
    # Get user data and restriction history
    user = await database.get_user(user_id)
    if not user:
        logger.warning(f"User {user_id} not found in database")
        return
    
    # Check each rule
    for rule_index, rule in enumerate(chat.chat_settings.moderation_rules):
        logger.info(f"Checking rule {rule_index + 1}: {rule.message}")
        
        # Check if the rule conditions are met
        if await rule_conditions_met(rule, user, chat_id, text, analysis_result):
            logger.info(f"Rule {rule_index + 1} triggered for user {user_id} in chat {chat_id}")
            
            await apply_restriction(rule, user_id, chat_id, message_id, text, user_name, rule_index)

async def rule_conditions_met(rule: ModerationRule, user: Any, chat_id: str, text: str, analysis_result: List) -> bool:
    """Check if all conditions for a rule are met"""
    results = []
    
    for condition in rule.conditions:
        condition_met = False
        
        # Check condition based on type
        if condition.type == "single_message_language_confidence":
            condition_met = check_language_confidence_condition(condition, analysis_result)
        
        elif condition.type == "single_message_confidence_not_in_allowed_languages":
            # Get allowed languages from chat settings
            chat = await database.get_chat(int(chat_id))
            allowed_languages = chat.chat_settings.allowed_languages
            condition_met = check_not_allowed_language_condition(condition, analysis_result, allowed_languages)
        
        elif condition.type == "previous_restriction_type_count":
            condition_met = await check_previous_restriction_count(condition, user.user_id, chat_id)
        
        elif condition.type == "previous_restriction_type_time_length":
            condition_met = await check_previous_restriction_time_length(condition, user.user_id, chat_id)
        
        results.append(condition_met)
    
    # Combine results based on the condition relation (AND/OR)
    if rule.condition_relation == "and":
        return all(results)
    else:  # OR relation
        return any(results)

def check_not_allowed_language_condition(condition: Any, analysis_result: List, allowed_languages: List[str]) -> bool:
    """Check if a message is in a non-allowed language with confidence above threshold"""
    threshold = condition.values.get("threshold", 0.0)
    
    # Check if any detected language is not in allowed languages and exceeds threshold
    for lang_result in analysis_result:
        lang_code = lang_result.get("lang", "")
        confidence = lang_result.get("prob", 0.0)
        
        if lang_code not in allowed_languages and confidence >= threshold:
            return True
    
    return False

def check_language_confidence_condition(condition: Any, analysis_result: List) -> bool:
    """Check if a message's language confidence meets the threshold"""
    threshold = condition.values.get("threshold", 0.0)
    language = condition.values.get("language", "")
    
    # If no language specified, condition can't be met
    if not language:
        logger.warning("Language confidence condition missing language parameter")
        return False
    
    # Check if the specified language in the analysis result exceeds the threshold
    for lang_result in analysis_result:
        if lang_result.get("lang", "") == language and lang_result.get("prob", 0.0) >= threshold:
            return True
    
    return False

async def check_previous_restriction_count(condition: Any, user_id: int, chat_id: str) -> bool:
    """Check if user has received a specific number of previous restrictions"""
    target_count = condition.values.get("count", 0)
    restriction_types = condition.values.get("restriction_type", [])
    
    # If "any" is in types, we count all restriction types
    count_all = "any" in restriction_types
    
    # Get user's restriction history
    user = await database.get_user(user_id)
    if not user or not hasattr(user, "restriction_history") or not user.restriction_history:
        return False
    
    # Count matching restrictions
    count = 0
    for restriction in user.restriction_history:
        # Only count restrictions for this chat if this_chat_only is True
        if condition.this_chat_only and restriction.chat_id != chat_id:
            continue
            
        # Count if restriction type matches or we're counting all types
        if count_all or restriction.restriction_type in restriction_types:
            count += 1
    
    return count >= target_count

async def check_previous_restriction_time_length(condition: Any, user_id: int, chat_id: str) -> bool:
    """Check if user has had restrictions of a specific cumulative duration"""
    target_seconds = condition.values.get("seconds", 0)
    window_hours = condition.values.get("window_hours", 24.0)
    restriction_types = condition.values.get("restriction_type", [])
    
    # If "any" is in types, we consider all restriction types
    consider_all = "any" in restriction_types
    
    # Get user's restriction history
    user = await database.get_user(user_id)
    if not user or not hasattr(user, "restriction_history") or not user.restriction_history:
        return False
    
    # Calculate time window
    now = datetime.now()
    window_start = now - timedelta(hours=window_hours)
    
    # Sum durations of matching restrictions within time window
    total_seconds = 0
    for restriction in user.restriction_history:
        # Skip if outside time window
        restriction_time = datetime.fromisoformat(restriction.timestamp)
        if restriction_time < window_start:
            continue
        
        # Only count restrictions for this chat if this_chat_only is True
        if condition.this_chat_only and restriction.chat_id != chat_id:
            continue
            
        # Add duration if restriction type matches or we're counting all types
        if consider_all or restriction.restriction_type in restriction_types:
            total_seconds += restriction.duration_seconds or 0
    
    return total_seconds >= target_seconds

async def apply_restriction(
    rule: ModerationRule, 
    user_id: int, 
    chat_id: str, 
    message_id: str, 
    text: str, 
    user_name: str,
    rule_index: int
):
    """Apply the restriction specified in the rule"""
    restriction = rule.restriction
    restriction_type = restriction.restriction_type
    
    logger.info(f"Applying {restriction_type} to user {user_id} in chat {chat_id}")
    
    # Create restriction record
    now = datetime.now().isoformat()
    restriction_record = RestrictionRecord(
        user_id=user_id,
        chat_id=chat_id,
        message_id=message_id,
        message_text=text,
        restriction_type=restriction_type,
        rule_index=rule_index,
        timestamp=now,
        duration_seconds=restriction.duration_seconds
    )
    
    # Add restriction record to user's history
    await database.add_restriction_to_user(user_id, restriction_record)
    
    # Send appropriate messages to Telegram
    await send_restriction_messages(rule, restriction, user_id, chat_id, message_id, user_name)

async def send_restriction_messages(
    rule: ModerationRule, 
    restriction: Restriction, 
    user_id: int, 
    chat_id: str, 
    message_id: str,
    user_name: str
):
    """Send restriction messages to Telegram"""
    # Message to show in chat
    admin_message = f"User {user_name} ({user_id}) violated a rule: {rule.message}"
    if restriction.restriction_justification_message:
        admin_message += f"\nJustification: {restriction.restriction_justification_message}"
    
    admin_notification_data = {
        "message_type": TelegramQueueMessageType.ADMIN_NOTIFICATION,
        "chat_id": chat_id,
        "text": admin_message
    }
    
    # Send admin notification
    await rabbitmq_manager.store_result(
        settings.RABBITMQ_TELEGRAM_QUEUE, 
        f"{chat_id}.admin.{datetime.now().timestamp()}", 
        admin_notification_data
    )
    
    # If user should be notified, prepare and send user notification
    if rule.notify_user:
        user_message = rule.message
        
        user_notification_data = {
            "message_type": TelegramQueueMessageType.USER_NOTIFICATION,
            "chat_id": chat_id,
            "user_id": user_id,
            "message_id": message_id,
            "text": user_message
        }
        
        await rabbitmq_manager.store_result(
            settings.RABBITMQ_TELEGRAM_QUEUE, 
            f"{chat_id}.{user_id}.{datetime.now().timestamp()}", 
            user_notification_data
        )
    
    # Send moderation action command
    moderation_action_data = {
        "message_type": TelegramQueueMessageType.MODERATION_ACTION,
        "chat_id": chat_id,
        "user_id": user_id,
        "message_id": message_id,
        "action_type": restriction.restriction_type,
        "duration_seconds": restriction.duration_seconds
    }
    
    await rabbitmq_manager.store_result(
        settings.RABBITMQ_TELEGRAM_QUEUE, 
        f"{chat_id}.{user_id}.action.{datetime.now().timestamp()}", 
        moderation_action_data
    )