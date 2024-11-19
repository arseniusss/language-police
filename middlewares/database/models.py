from typing import List, Optional
from pydantic import BaseModel
from beanie import Document

class ChatMessage(BaseModel):
    chat_id: str
    message_id: str
    content: str
    timestamp: str

class User(Document):
    user_id: int
    name: Optional[str] = None
    username: Optional[str] = None  # Made optional with default None
    is_active: bool = True  # Added with default True
    chat_history: List[ChatMessage] = []

    class Settings:
        name = "users"
        indexes = ["user_id"]