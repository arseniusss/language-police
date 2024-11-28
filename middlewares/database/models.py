from typing import List, Dict, Optional
from pydantic import BaseModel
from beanie import Document

class ChatMessage(BaseModel):
    chat_id: str
    message_id: str
    content: str
    timestamp: str
    analysis_result: Optional[list] = None  # Add this line

class User(Document):
    user_id: int
    name: Optional[str] = None
    username: Optional[str] = None
    is_active: bool = True
    chat_history: Dict[str, List[ChatMessage]] = {}

    class Settings:
        name = "users"
        indexes = ["user_id"]