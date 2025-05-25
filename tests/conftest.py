import pytest
from unittest.mock import AsyncMock, Mock
from datetime import datetime, timedelta

# Simple mock data classes to avoid Beanie validation issues
class MockUser:
    def __init__(self, user_id, username=None, first_name=None, last_name=None, **kwargs):
        self.user_id = user_id
        self.username = username
        self.first_name = first_name
        self.last_name = last_name
        for key, value in kwargs.items():
            setattr(self, key, value)

class MockChat:
    def __init__(self, chat_id, chat_name=None, chat_type=None, **kwargs):
        self.chat_id = chat_id
        self.chat_name = chat_name
        self.chat_type = chat_type
        self.chat_settings = kwargs.get('chat_settings', MockChatSettings())
        for key, value in kwargs.items():
            if key != 'chat_settings':
                setattr(self, key, value)

class MockChatSettings:
    def __init__(self, **kwargs):
        self.allowed_languages = kwargs.get('allowed_languages', ["en", "uk"])
        self.analysis_frequency = kwargs.get('analysis_frequency', 1)
        self.min_message_length = kwargs.get('min_message_length', 5)
        self.max_message_length = kwargs.get('max_message_length', 1000)
        self.min_analyzed_messages = kwargs.get('min_analyzed_messages', 10)

class MockMessage:
    def __init__(self, message_id, user_id, chat_id, text, language, confidence, **kwargs):
        self.message_id = message_id
        self.user_id = user_id
        self.chat_id = chat_id
        self.text = text
        self.language = language
        self.confidence = confidence
        self.timestamp = kwargs.get('timestamp', datetime.utcnow())
        self.character_count = kwargs.get('character_count', len(text))

class MockModerationRule:
    def __init__(self, name, conditions, action_type, **kwargs):
        self.name = name
        self.conditions = conditions
        self.logical_operator = kwargs.get('logical_operator', 'AND')
        self.action_type = action_type
        self.action_duration = kwargs.get('action_duration', 3600)
        self.user_message = kwargs.get('user_message', '')
        self.reason = kwargs.get('reason', '')


# Remove deprecated event_loop fixture - pytest-asyncio handles this automatically


@pytest.fixture
def mock_database():
    """Create a mock database for testing."""
    database = Mock()
    database.get_user = AsyncMock()
    database.get_chat = AsyncMock()
    database.create_user = AsyncMock()
    database.create_chat = AsyncMock()
    database.save_message = AsyncMock()
    database.get_user_stats = AsyncMock()
    database.get_chat_stats = AsyncMock()
    database.get_global_stats = AsyncMock()
    database.get_user_ranking = AsyncMock()
    database.get_chat_ranking = AsyncMock()
    database.get_global_ranking = AsyncMock()
    database.bulk_insert_messages = AsyncMock()
    database.cleanup_old_messages = AsyncMock()
    database.create_indexes = AsyncMock()
    database.execute_transaction = AsyncMock()
    database.update_chat_settings = AsyncMock()
    return database


@pytest.fixture
def sample_user():
    """Create a sample user for testing."""
    return MockUser(
        user_id=123456789,
        username="testuser",
        first_name="Test",
        last_name="User",
        created_at=datetime.utcnow(),
        total_messages=100,
        total_characters=5000,
        languages_detected={"en": 60, "uk": 40}
    )


@pytest.fixture
def sample_chat():
    """Create a sample chat for testing."""
    return MockChat(
        chat_id=-1001234567890,
        chat_name="Test Chat",
        chat_type="supergroup",
        created_at=datetime.utcnow(),
        total_messages=500,
        total_characters=25000,
        languages_detected={"en": 300, "uk": 200},
        chat_settings=MockChatSettings(
            allowed_languages=["en", "uk"],
            analysis_frequency=1,
            min_message_length=5,
            max_message_length=1000,
            min_analyzed_messages=10
        )
    )


@pytest.fixture
def sample_messages():
    """Create sample messages for testing."""
    return [
        MockMessage(
            message_id=1,
            user_id=123456789,
            chat_id=-1001234567890,
            text="Hello world",
            language="en",
            confidence=0.95,
            timestamp=datetime.utcnow() - timedelta(days=1),
            character_count=11
        ),
        MockMessage(
            message_id=2,
            user_id=123456789,
            chat_id=-1001234567890,
            text="Привіт світ",
            language="uk",
            confidence=0.98,
            timestamp=datetime.utcnow(),
            character_count=10
        )
    ]


@pytest.fixture
def sample_moderation_rule():
    """Create a sample moderation rule."""
    return MockModerationRule(
        name="Ukrainian Only Rule",
        conditions=[
            {
                "type": "language_not_allowed",
                "language": "uk",
                "confidence_threshold": 0.8
            }
        ],
        logical_operator="AND",
        action_type="temporary_restriction",
        action_duration=3600,
        user_message="Please use Ukrainian in this chat.",
        reason="Non-Ukrainian language detected"
    )


@pytest.fixture
def mock_bot():
    """Create a mock bot for testing."""
    bot = AsyncMock()
    bot.get_chat_member = AsyncMock()
    bot.restrict_chat_member = AsyncMock()
    bot.ban_chat_member = AsyncMock()
    bot.send_message = AsyncMock()
    return bot


@pytest.fixture
def mock_callback_query():
    """Create a mock callback query for testing."""
    callback = Mock()
    callback.from_user = Mock()
    callback.from_user.id = 123456789
    callback.from_user.username = "testuser"
    callback.message = Mock()
    callback.message.edit_text = AsyncMock()
    callback.answer = AsyncMock()
    return callback


@pytest.fixture
def mock_message():
    """Create a mock message for testing."""
    message = Mock()
    message.from_user = Mock()
    message.from_user.id = 123456789
    message.from_user.username = "testuser"
    message.chat = Mock()
    message.chat.id = -1001234567890
    message.text = "Test message"
    message.message_id = 1
    message.answer = AsyncMock()
    return message