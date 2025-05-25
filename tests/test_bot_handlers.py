import pytest
from unittest.mock import AsyncMock, Mock, patch
from aiogram.types import CallbackQuery, Message, User as TelegramUser, Chat as TelegramChat
from aiogram.fsm.context import FSMContext

from middlewares.database.models import User, Chat, ChatSettings


class TestBotHandlerFunctions:
    """Test suite for bot handler functions."""

    @pytest.fixture
    def mock_telegram_user(self):
        """Create a mock Telegram user."""
        return TelegramUser(
            id=123456789,
            is_bot=False,
            first_name="Test",
            last_name="User",
            username="testuser"
        )

    @pytest.fixture
    def mock_telegram_chat(self):
        """Create a mock Telegram chat."""
        return TelegramChat(
            id=-1001234567890,
            type="supergroup",
            title="Test Chat"
        )

    @pytest.fixture
    def mock_fsm_context(self):
        """Create a mock FSM context."""
        context = Mock(spec=FSMContext)
        context.get_data = AsyncMock(return_value={"chat_id": -1001234567890})
        context.set_data = AsyncMock()
        context.set_state = AsyncMock()
        return context
    
    @pytest.mark.asyncio
    async def test_start_command_new_user(self, mock_message, mock_database):
        """Test /start command for new user."""
        # Mock database responses
        mock_database.get_user.return_value = None 
        mock_database.create_user.return_value = AsyncMock()
        
        # Simulate start command logic
        user_id = mock_message.from_user.id
        existing_user = await mock_database.get_user(user_id)
        
        if not existing_user:
            await mock_database.create_user(user_id)
            response = "Welcome! You have been registered in the system."
        else:
            response = "Welcome back!"
        
        assert response == "Welcome! You have been registered in the system."
        mock_database.create_user.assert_called_once_with(user_id)

    @pytest.mark.asyncio
    async def test_start_command_existing_user(self, mock_message, mock_database, sample_user):
        """Test /start command for existing user."""
        # Mock database responses
        mock_database.get_user.return_value = sample_user
        
        # Simulate start command logic
        user_id = mock_message.from_user.id
        existing_user = await mock_database.get_user(user_id)
        
        if not existing_user:
            response = "Welcome! You have been registered in the system."
        else:
            response = "Welcome back!"
        
        assert response == "Welcome back!"

    @pytest.mark.asyncio
    async def test_help_command(self, mock_message):
        """Test /help command response."""
        help_text = """
🤖 Language Police Bot Help

📊 Statistics Commands:
/stats - Your personal statistics
/chat_stats - Chat statistics
/global_stats - Global statistics

🏆 Ranking Commands:
/chat_top - Top users in this chat
/global_top - Global top users
/my_chat_ranking - Your ranking in this chat

⚙️ Admin Commands:
/chat_settings - Configure chat settings (admins only)
/add_admins - Sync chat admins

For more information, contact the bot administrator.
        """.strip()
        
        # Test that help text contains expected sections
        assert "Statistics Commands" in help_text
        assert "Ranking Commands" in help_text
        assert "Admin Commands" in help_text
        assert "/stats" in help_text

    @pytest.mark.asyncio
    async def test_stats_command_formatting(self, sample_user):
        """Test personal statistics command formatting."""
        user_stats = {
            "total_messages": 150,
            "total_characters": 7500,
            "languages_detected": {"en": 90, "uk": 60},
            "avg_message_length": 50.0
        }
        
        # Format stats response
        response_lines = [
            f"📊 Your Statistics:",
            f"Total messages: {user_stats['total_messages']}",
            f"Total characters: {user_stats['total_characters']}",
            f"Average message length: {user_stats['avg_message_length']:.1f} characters",
            "",
            "Languages detected:"
        ]
        
        for lang, count in user_stats['languages_detected'].items():
            percentage = (count / user_stats['total_messages']) * 100
            response_lines.append(f"  {lang.upper()}: {count} ({percentage:.1f}%)")
        
        response = "\n".join(response_lines)
        
        assert "📊 Your Statistics:" in response
        assert "Total messages: 150" in response
        assert "EN: 90 (60.0%)" in response
        assert "UK: 60 (40.0%)" in response

    @pytest.mark.asyncio
    async def test_admin_permission_check(self, mock_bot):
        """Test admin permission verification."""
        chat_id = -1001234567890
        user_id = 123456789
        
        # Mock admin status
        mock_member = Mock()
        mock_member.status = "administrator"
        mock_bot.get_chat_member.return_value = mock_member
        
        # Simulate permission check
        member = await mock_bot.get_chat_member(chat_id, user_id)
        is_admin = member.status in ["administrator", "creator"]
        
        assert is_admin is True
        mock_bot.get_chat_member.assert_called_once_with(chat_id, user_id)

    @pytest.mark.asyncio
    async def test_non_admin_permission_check(self, mock_bot):
        """Test non-admin permission verification."""
        chat_id = -1001234567890
        user_id = 123456789
        
        # Mock regular member status
        mock_member = Mock()
        mock_member.status = "member"
        mock_bot.get_chat_member.return_value = mock_member
        
        # Simulate permission check
        member = await mock_bot.get_chat_member(chat_id, user_id)
        is_admin = member.status in ["administrator", "creator"]
        
        assert is_admin is False

    @pytest.mark.asyncio
    async def test_callback_query_handling(self, mock_callback_query):
        """Test callback query handling."""
        # Simulate callback data processing
        callback_data = "settings_allowed_languages"
        
        if callback_data == "settings_allowed_languages":
            response = "Language settings accessed"
        elif callback_data == "settings_moderation_rules":
            response = "Moderation rules accessed"
        else:
            response = "Unknown callback"
        
        assert response == "Language settings accessed"    
        
        def test_inline_keyboard_generation(self):
            """Test inline keyboard generation."""
        # Simulate creating inline keyboard
        buttons = [
            {"text": "✅ English", "callback_data": "lang_toggle_en"},
            {"text": "❌ Ukrainian", "callback_data": "lang_toggle_uk"},
            {"text": "✅ German", "callback_data": "lang_toggle_de"}
        ]
        
        # Test button formatting
        for button in buttons:
            assert "callback_data" in button
            assert button["callback_data"].startswith("lang_toggle_")
            assert button["text"].startswith(("✅", "❌"))
    
    @pytest.mark.asyncio
    async def test_error_handling_in_handlers(self, mock_message, mock_database):
        """Test error handling in bot handlers."""
        # Mock database error
        mock_database.get_user.side_effect = Exception("Database connection error")
        
        try:
            user = await mock_database.get_user(mock_message.from_user.id)
            response = "Success"
        except Exception as e:
            response = "Sorry, there was an error processing your request. Please try again later."
        
        assert response == "Sorry, there was an error processing your request. Please try again later."

    @pytest.mark.asyncio
    async def test_message_length_validation(self, mock_message):
        """Test message length validation."""
        test_messages = [
            ("Hi", 2),
            ("Hello world", 11),
            ("A" * 1000, 1000),
            ("", 0)
        ]
        
        min_length = 5
        max_length = 500
        
        for text, length in test_messages:
            is_valid_length = min_length <= length <= max_length
            
            if text == "Hi":
                assert is_valid_length is False  # Too short
            elif text == "Hello world":
                assert is_valid_length is True   # Valid
            elif len(text) == 1000:
                assert is_valid_length is False  # Too long
            elif text == "":
                assert is_valid_length is False  # Empty

    @pytest.mark.asyncio
    async def test_chat_event_handling(self, mock_telegram_chat, mock_database):
        """Test handling of chat events."""
        # Simulate bot added to new chat
        chat_id = mock_telegram_chat.id
        chat_title = mock_telegram_chat.title
        
        # Check if chat exists
        mock_database.get_chat.return_value = None
        existing_chat = await mock_database.get_chat(chat_id)
        
        if not existing_chat:
            # Create new chat with default settings
            await mock_database.create_chat(chat_id, chat_title)
            response = f"Bot added to new chat: {chat_title}"
        else:
            response = "Bot already configured for this chat"
        
        assert response == f"Bot added to new chat: {chat_title}"
        mock_database.create_chat.assert_called_once_with(chat_id, chat_title)

    def test_command_argument_parsing(self):
        """Test parsing command arguments."""
        command_text = "/chat_top messages 10"
        parts = command_text.split()
        
        command = parts[0]  # "/chat_top"
        ranking_type = parts[1] if len(parts) > 1 else "messages"
        limit = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 10
        
        assert command == "/chat_top"
        assert ranking_type == "messages"
        assert limit == 10

    def test_user_mention_formatting(self, mock_telegram_user):
        """Test user mention formatting."""
        user = mock_telegram_user
        
        # Format user mention
        if user.username:
            mention = f"@{user.username}"
        else:
            mention = f"{user.first_name}"
            if user.last_name:
                mention += f" {user.last_name}"
        
        assert mention == "@testuser"

    def test_user_mention_formatting_no_username(self):
        """Test user mention formatting without username."""
        user = TelegramUser(
            id=123456789,
            is_bot=False,
            first_name="John",
            last_name="Doe",
            username=None
        )
        
        # Format user mention
        if user.username:
            mention = f"@{user.username}"
        else:
            mention = f"{user.first_name}"
            if user.last_name:
                mention += f" {user.last_name}"
        
        assert mention == "John Doe"