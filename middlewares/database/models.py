from typing import List, Dict, Optional, Tuple, Union
from pydantic import BaseModel, Field, confloat
from typing_extensions import Annotated
from beanie import Document
from datetime import datetime, timedelta
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
    PERMANENT_BAN = "permanent_ban"

class RestrictionRecord(BaseModel):
    """Record of a restriction applied to a user"""
    user_id: int
    chat_id: str
    message_id: str
    message_text: str
    restriction_type: str
    rule_index: int
    timestamp: str
    duration_seconds: Optional[float] = None

class Restriction(BaseModel):
    restriction_type: RestrictionType
    restriction_justification_message: Optional[str] = None
    granted_date: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    expires_at: Optional[datetime] = None

class User(Document):
    user_id: int = Field(..., alias="user_id")
    name: Optional[str] = None
    username: Optional[str] = None
    is_active: bool = True
    chat_history: Dict[str, List[ChatMessage]] = {}
    # we store it in a dict to easily check for specific chat's restrictions on chat join for example
    restrictions: Optional[Dict[str, List[Restriction]]] = Field(default_factory=dict)
    restriction_history: List[RestrictionRecord] = Field(default_factory=list)

    class Settings:
        name = "users"
        indexes = ["user_id"]

class RuleConditionType(str, Enum):
    SINGLE_MESSAGE_CONFIDENCE_NOT_IN_ALLOWED_LANGUAGES = "single_message_confidence_not_in_allowed_languages"
    SINGLE_MESSAGE_LANGUAGE_CONFIDENCE = "single_message_language_confidence"
    PREVIOUS_RESTRICTION_TYPE_TIME_LENGTH = "previous_restriction_type_time_length"
    PREVIOUS_RESTRICTION_TYPE_COUNT = "previous_restriction_type_count"

# TODO: ЯК ЗАДАТИ КОНКРЕТНІ ПОЛЯ ЗАМІСТЬ ПРОСТО СЛОВНИКА (VALUES)
class RuleCondition(BaseModel):
    type: RuleConditionType
    values: Optional[Dict] = None
    this_chat_only: bool = True
    time_window: Optional[timedelta] = None
    extra_data: Optional[Dict] = None

class ConditionRelationType(str, Enum):
    AND = "and"
    OR = "or"

#automatic behaviour for rule breaking
class ModerationRule(BaseModel):
    conditions: List[RuleCondition]
    condition_relation : ConditionRelationType = ConditionRelationType.AND

    restriction: Restriction = Restriction(
        restriction_type=RestrictionType.WARNING,
        restriction_justification_message="You broke the rules!"
    )
    message: str
    name: str
    notify_user: bool = True

class ChatSettings(BaseModel):
    sync_blocklist_with: Optional[List[int]] = []
    sync_settings_with: Optional[int] = None

    moderation_rules: List[ModerationRule] = []
    allowed_languages: Optional[List[str]] = ["ua", "en"]
    analysis_frequency: Annotated[float, Field(strict=True,ge=0.05, le=1)] = 0.05
    new_members_min_analyzed_messages: int = 5
    chat_for_logs: Optional[int] = None
    # screen_group_applications: bool = False
    min_message_length_for_analysis: int = 10
    max_message_length_for_analysis: int = 2000

class Chat(Document):
    chat_id: int
    last_known_name: str
    users: List[int] = []
    blocked_users: List[int] = [] # ids only 
    admins: Dict[int, List[str]] = {} # admins and their permissions in this chat
    chat_settings: ChatSettings = ChatSettings()

    class Settings:
        name = "chats"
        indexes = ["chat_id"]