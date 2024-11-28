from typing import Optional, Dict, List
from beanie import init_beanie
from motor.motor_asyncio import AsyncIOMotorClient
from .models import User, ChatMessage
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
        """Initialize Beanie with the User model."""
        await init_beanie(database=self.db, document_models=[User])

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

    async def __call__(self, handler, event, data):
        data["db"] = self
        return await handler(event, data)

database = DatabaseMiddleware()