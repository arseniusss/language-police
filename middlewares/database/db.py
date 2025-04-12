from datetime import datetime, timedelta
from typing import Optional, Dict, List
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from .models import User, ChatMessage, Chat, ChatSettings, RestrictionType, ModerationRule, ConditionRelationType, RuleCondition, RuleConditionType, RestrictionRecord
from aiogram import BaseMiddleware
from settings import get_settings

settings = get_settings()

class DatabaseMiddleware(BaseMiddleware):
    def __init__(self):
        mongodb_uri = settings.MONGODB_CONNECTION_URI
        mongodb_db = settings.MONGODB_DATABASE
        
        if not mongodb_uri or not mongodb_db:
            raise ValueError("Missing required environment variables: MONGODB_CONNECTION_URI or MONGODB_DATABASE")
            
        self.client = AsyncIOMotorClient(mongodb_uri)
        self.db = self.client[mongodb_db]
        super().__init__()

    async def setup(self):
        """Initialize Beanie with the User and Chat models."""
        await init_beanie(database=self.db, document_models=[User, Chat])

    async def get_user(self, user_id: int) -> Optional[User]:
        """Fetch a user by user_id."""
        return await User.find_one(User.user_id == user_id)
    
    async def user_exists(self, user_id: int) -> bool:
        """Check if user exists in database"""
        user = await self.get_user(user_id)
        return user is not None

    async def create_user(self, user_data: Dict) -> User:
        """Create a new user."""
        user = User(**user_data)
        await user.insert()
        return user

    async def update_user(self, user_id: int, update_data: Dict) -> Optional[User]:
        """Update user data."""
        user = await self.get_user(user_id)
        if user:
            await user.set(update_data)
            return user
        return None

    async def add_chat_message(self, user_id: int, message: ChatMessage) -> Optional[User]:
        """Add a chat message to a user's chat history."""
        user = await self.get_user(user_id)
        if user:
            if message.chat_id not in user.chat_history:
                user.chat_history[message.chat_id] = []
            
            user.chat_history[message.chat_id].append(message)
            await user.save()
            return user
        return None

    async def delete_user(self, user_id: int) -> bool:
        """Delete a user."""
        user = await self.get_user(user_id)
        if user:
            await user.delete()
            return True
        return False

    async def get_chat(self, chat_id: int) -> Optional[Chat]:
        """Fetch a chat by chat_id."""
        return await Chat.find_one(Chat.chat_id == chat_id)

    async def chat_exists(self, chat_id: int) -> bool:
        """Check if chat exists in database"""
        chat = await self.get_chat(chat_id)
        return chat is not None

    async def create_chat(self, chat_data: Dict) -> Chat:
        """Create a new chat."""
        chat = Chat(**chat_data)
        await chat.insert()
        return chat

    async def update_chat(self, chat_id: int, update_data: Dict) -> Optional[Chat]:
        """Update chat data."""
        chat = await self.get_chat(chat_id)
        if chat:
            await chat.set(update_data)
            return chat
        return None

    async def delete_chat(self, chat_id: int) -> bool:
        """Delete a chat."""
        chat = await self.get_chat(chat_id)
        if chat:
            await chat.delete()
            return True
        return False

    async def add_user_to_chat(self, chat_id: int, user_id: int):
        chat = await self.get_chat(chat_id)
        if chat and user_id not in chat.users:
            chat.users.append(user_id)
            await chat.save()
        return chat

    async def remove_user_from_chat(self, chat_id: int, user_id: int):
        chat = await self.get_chat(chat_id)
        if chat and user_id in chat.users:
            chat.users.remove(user_id)
            await chat.save()
        return chat

    async def is_user_in_chat(self, chat_id: int, user_id: int) -> bool:
        chat = await self.get_chat(chat_id)
        return chat and user_id in chat.users

    async def __call__(self, handler, event, data):
        data["db"] = self
        return await handler(event, data)

    async def add_restriction_to_user(self, user_id: int, restriction_record: RestrictionRecord):
        # Convert restriction record to dict if it's a model
        if hasattr(restriction_record, "dict"):
            restriction_record = restriction_record.dict()
        
        # Add record to user's restriction history
        await self.db["users"].update_one(
            {"user_id": int(user_id)}, 
            {"$push": {"restriction_history": restriction_record}}
        )
        
        # For timeouts and bans, also add to active restrictions
        restriction_type = restriction_record.get("restriction_type")
        chat_id = restriction_record.get("chat_id")
        
        if restriction_type in [RestrictionType.TIMEOUT.value, RestrictionType.TEMPORARY_BAN.value, RestrictionType.PERMANENT_BAN.value]:
            # Create restriction object
            restriction = {
                "restriction_type": restriction_type,
                "restriction_justification_message": f"Rule violation: {restriction_record.get('message_text', '')}",
                "granted_date": datetime.now().isoformat(),
                "duration_seconds": restriction_record.get("duration_seconds")
            }
            
            # Calculate expiration if there's a duration
            if restriction_record.get("duration_seconds"):
                restriction["expires_at"] = (
                    datetime.now() + timedelta(seconds=restriction_record.get("duration_seconds"))
                ).isoformat()
            
            # Add to user's active restrictions for this chat
            await self.db["users"].update_one(
                {"user_id": int(user_id)},
                {
                    "$push": {f"restrictions.{chat_id}": restriction}
                }
            )
        
        return True

    async def get_user_restriction_history(self, user_id: int, chat_id: str = None, time_window: timedelta = None):
        """
        Get a user's restriction history, optionally filtered by chat and time window
        
        Args:
            user_id: The ID of the user
            chat_id: Optional chat ID to filter by
            time_window: Optional time window to filter by (e.g., last 7 days)
        
        Returns:
            List of restriction records
        """
        user = await self.get_user(user_id)
        if not user or not hasattr(user, "restriction_history"):
            return []
        
        history = user.restriction_history
        
        # Filter by chat ID if provided
        if chat_id:
            history = [r for r in history if r.chat_id == chat_id]
        
        # Filter by time window if provided
        if time_window:
            cutoff_time = datetime.now() - time_window
            history = [
                r for r in history 
                if datetime.fromisoformat(r.timestamp) >= cutoff_time
            ]
        
        return history

    async def check_rule_condition(self, condition: RuleCondition, user_id: int, chat_id: str, text: str, analysis_result: List):
        """
        Check if a specific rule condition is met
        
        Args:
            condition: The rule condition to check
            user_id: The user's ID
            chat_id: The chat ID
            text: The message text
            analysis_result: The language analysis result
        
        Returns:
            bool: True if condition is met, False otherwise
        """
        # Language confidence check
        if condition.type == RuleConditionType.SINGLE_MESSAGE_LANGUAGE_CONFIDENCE:
            threshold = condition.values.get("threshold", 0.0)
            # Check if any language in the analysis result exceeds the threshold
            for lang_result in analysis_result:
                if lang_result.get("prob", 0.0) >= threshold:
                    return True
            return False
        
        # Not allowed language check
        elif condition.type == RuleConditionType.SINGLE_MESSAGE_CONFIDENCE_NOT_IN_ALLOWED_LANGUAGES:
            threshold = condition.values.get("threshold", 0.0)
            # Get allowed languages from chat settings
            chat = await self.get_chat(int(chat_id))
            allowed_languages = chat.chat_settings.allowed_languages
            
            # Check if any detected language is not in allowed languages and exceeds threshold
            for lang_result in analysis_result:
                lang_code = lang_result.get("lang", "")
                confidence = lang_result.get("prob", 0.0)
                
                if lang_code not in allowed_languages and confidence >= threshold:
                    return True
            return False
        
        # Previous restriction count check
        elif condition.type == RuleConditionType.PREVIOUS_RESTRICTION_TYPE_COUNT:
            target_count = condition.values.get("count", 0)
            restriction_types = condition.values.get("restriction_type", [])
            
            # If "any" is in types, we count all restriction types
            count_all = "any" in restriction_types
            
            # Get user's restriction history
            restriction_history = await self.get_user_restriction_history(
                user_id, 
                chat_id if condition.this_chat_only else None
            )
            
            # Count matching restrictions
            count = 0
            for restriction in restriction_history:
                # Count if restriction type matches or we're counting all types
                if count_all or restriction.restriction_type in restriction_types:
                    count += 1
            
            return count >= target_count
        
        # Previous restriction time length check
        elif condition.type == RuleConditionType.PREVIOUS_RESTRICTION_TYPE_TIME_LENGTH:
            target_seconds = condition.values.get("seconds", 0)
            window_hours = condition.values.get("window_hours", 24.0)
            restriction_types = condition.values.get("restriction_type", [])
            
            # If "any" is in types, we consider all restriction types
            consider_all = "any" in restriction_types
            
            # Get user's restriction history within the time window
            time_window = timedelta(hours=window_hours)
            restriction_history = await self.get_user_restriction_history(
                user_id, 
                chat_id if condition.this_chat_only else None,
                time_window
            )
            
            # Sum durations of matching restrictions
            total_seconds = 0
            for restriction in restriction_history:
                # Add duration if restriction type matches or we're counting all types
                if consider_all or restriction.restriction_type in restriction_types:
                    total_seconds += restriction.duration_seconds or 0
            
            return total_seconds >= target_seconds
        
        # Unknown condition type
        return False

    async def check_moderation_rules(self, user_id: int, chat_id: str, message_id: str, text: str, analysis_result: List):
        """
        Check if a message violates any moderation rules
        
        Args:
            user_id: The user's ID
            chat_id: The chat ID
            message_id: The message ID
            text: The message text
            analysis_result: The language analysis result
        
        Returns:
            tuple: (triggered_rule, rule_index) or (None, None) if no rule was triggered
        """
        # Get chat settings and moderation rules
        chat = await self.get_chat(int(chat_id))
        if not chat or not chat.chat_settings or not chat.chat_settings.moderation_rules:
            return None, None
        
        # Check each rule
        for rule_index, rule in enumerate(chat.chat_settings.moderation_rules):
            # Check conditions based on condition relation type
            condition_results = []
            
            for condition in rule.conditions:
                condition_met = await self.check_rule_condition(
                    condition, user_id, chat_id, text, analysis_result
                )
                condition_results.append(condition_met)
            
            # Determine if rule is triggered based on condition relation
            rule_triggered = False
            if rule.condition_relation == ConditionRelationType.AND:
                rule_triggered = all(condition_results)
            else:  # OR relation
                rule_triggered = any(condition_results)
            
            if rule_triggered:
                return rule, rule_index
        
        return None, None

    async def apply_restriction(self, rule: ModerationRule, user_id: int, chat_id: str, message_id: str, text: str, rule_index: int):
        """
        Apply a restriction based on a triggered rule
        
        Args:
            rule: The triggered moderation rule
            user_id: The user's ID
            chat_id: The chat ID
            message_id: The message ID
            text: The message text
            rule_index: The index of the triggered rule
        
        Returns:
            RestrictionRecord: The created restriction record
        """
        restriction = rule.restriction
        
        # Create restriction record
        now = datetime.now().isoformat()
        restriction_record = RestrictionRecord(
            user_id=user_id,
            chat_id=chat_id,
            message_id=message_id,
            message_text=text,
            restriction_type=restriction.restriction_type,
            rule_index=rule_index,
            timestamp=now,
            duration_seconds=restriction.duration_seconds
        )
        
        # Add restriction to user's history
        await self.add_restriction_to_user(user_id, restriction_record)
        
        return restriction_record

database = DatabaseMiddleware()