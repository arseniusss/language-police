from typing import List, Dict, Optional, Tuple
from pydantic import BaseModel, Field, confloat
from typing_extensions import Annotated
from beanie import Document
from datetime import datetime
from enum import Enum


class ChatMessage(BaseModel):
    chat_id: str
    message_id: str
    content: str
    timestamp: str
    analysis_result: Optional[list] = None

class RestrictionType(str, Enum):
    WARNING = "warning"
    TIMEOUT = "timeout"
    TEMPORARY_BAN = "temporary_ban"
    PERMAMENT_BAN = "permanent_ban"

class Restriction(BaseModel):
    restriction_type: RestrictionType
    restriction_justification_message: Optional[str] = None
    granted_date: Optional[datetime] = None
    duration_seconds: Optional[float] = None

class User(Document):
    user_id: int = Field(..., alias="user_id")
    name: Optional[str] = None
    username: Optional[str] = None
    is_active: bool = True
    chat_history: Dict[str, List[ChatMessage]] = {}
    # we store it in a dict to easily check for specific chat's restrictions on chat join for example
    # FIXME: щось не те зі словником 
    # restrictions: Optional[Dict[str, List[Restriction]]] = Field(default_factory=dict)

    class Settings:
        name = "users"
        indexes = ["user_id"]

#automatic behaviour for rule breaking
class RuleBreakingBehaviour(BaseModel):
    notify_privately: bool = False
    language_codes_with_min_confidence: Optional[List[Tuple[str, float]]] = None
    restriction: Restriction = Restriction(
        restriction_type=RestrictionType.WARNING,
        restriction_message="You broke the rules!"
    )
    # TODO: продумати, як краще зберігати обмеження, бо можуть бути і за тривалістю
    # можливо, створити окрему категорію обмежень для цього

    #i.e 3 warnings
    prev_restrictions_threshhold: Optional[int] = None 
    prev_restrictions_type: Optional[RestrictionType] = RestrictionType.WARNING

class ChatSettings(BaseModel):
    sync_blocklist_with: List[int] = []
    sync_settings_with: Optional[int] = None

    rule_breaking_behaviour: List[RuleBreakingBehaviour] = []
    possible_languages: Optional[List[str]] = ["ua", "en"]
    # FIXME:
    analysis_frequency: Annotated[float, Field(strict=True,ge=0, le=1)]
    # TODO: constraints
    new_members_analyzed_messages: int = 10
    chat_for_logs: Optional[int] = None
    screen_group_applications: bool = False
    min_message_length_for_analysis: int = 10

class Chat(Document):
    chat_id: int
    last_known_name: str
    users: List[int] = []
    blocked_users: List[int] = [] # ids only 
    admins: Dict[int, List[str]] = {} # admins and their permissions in this chat
    # FIXME:
    # chat_settings: ChatSettings

    class Settings:
        name = "chats"
        indexes = ["chat_id"]