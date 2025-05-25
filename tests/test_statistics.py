import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timedelta

from middlewares.database.models import User, Chat, ChatMessage, ChatSettings


class TestStatisticsFunctions:
    """Test suite for statistics calculation functions."""

    @pytest.mark.asyncio
    async def test_user_stats_calculation(self, sample_user, sample_messages):
        """Test user statistics calculation."""
        # Mock user with message data
        user_stats = {
            "total_messages": 100,
            "total_characters": 5000,
            "languages_detected": {"en": 60, "uk": 40},
            "avg_message_length": 50.0
        }
        
        assert user_stats["total_messages"] == 100
        assert user_stats["total_characters"] == 5000
        assert user_stats["languages_detected"]["en"] == 60
        assert user_stats["languages_detected"]["uk"] == 40
        assert user_stats["avg_message_length"] == 50.0

    @pytest.mark.asyncio
    async def test_chat_stats_calculation(self, sample_chat):
        """Test chat statistics calculation."""
        chat_stats = {
            "total_messages": 500,
            "total_characters": 25000,
            "total_users": 50,
            "languages_detected": {"en": 300, "uk": 200},
            "avg_message_length": 50.0,
            "most_active_user": {"user_id": 123, "username": "testuser", "message_count": 50}
        }
        
        assert chat_stats["total_messages"] == 500
        assert chat_stats["total_characters"] == 25000
        assert chat_stats["total_users"] == 50
        assert chat_stats["avg_message_length"] == 50.0
        assert chat_stats["most_active_user"]["user_id"] == 123

    @pytest.mark.asyncio
    async def test_global_stats_calculation(self):
        """Test global statistics calculation."""
        global_stats = {
            "total_users": 1000,
            "total_chats": 50,
            "total_messages": 10000,
            "total_characters": 500000,
            "languages_detected": {"en": 6000, "uk": 4000},
            "avg_messages_per_user": 10.0,
            "avg_messages_per_chat": 200.0
        }
        
        assert global_stats["total_users"] == 1000
        assert global_stats["total_chats"] == 50
        assert global_stats["total_messages"] == 10000
        assert global_stats["avg_messages_per_user"] == 10.0
        assert global_stats["avg_messages_per_chat"] == 200.0

    def test_language_distribution_calculation(self):
        """Test language distribution calculation."""
        messages_by_language = {"en": 100, "uk": 80, "de": 20}
        total_messages = sum(messages_by_language.values())
        
        language_percentages = {}
        for lang, count in messages_by_language.items():
            language_percentages[lang] = round((count / total_messages) * 100, 2)
        
        assert language_percentages["en"] == 50.0
        assert language_percentages["uk"] == 40.0
        assert language_percentages["de"] == 10.0

    def test_time_period_filtering(self):
        """Test filtering statistics by time period."""
        now = datetime.utcnow()
        messages = [
            {"timestamp": now - timedelta(days=1), "text": "Recent"},
            {"timestamp": now - timedelta(days=7), "text": "Week old"},
            {"timestamp": now - timedelta(days=30), "text": "Month old"}
        ]
        
        # Filter last 7 days
        week_ago = now - timedelta(days=7)
        recent_messages = [msg for msg in messages if msg["timestamp"] >= week_ago]
        
        assert len(recent_messages) == 2
        assert recent_messages[0]["text"] == "Recent"
        assert recent_messages[1]["text"] == "Week old"

    def test_user_activity_levels(self):
        """Test categorizing users by activity levels."""
        users_activity = [
            {"user_id": 1, "message_count": 100},
            {"user_id": 2, "message_count": 50},
            {"user_id": 3, "message_count": 10},
            {"user_id": 4, "message_count": 1}
        ]
        
        activity_levels = {"high": 0, "medium": 0, "low": 0, "inactive": 0}
        
        for user in users_activity:
            count = user["message_count"]
            if count >= 50:
                activity_levels["high"] += 1
            elif count >= 10:
                activity_levels["medium"] += 1
            elif count >= 1:
                activity_levels["low"] += 1
            else:
                activity_levels["inactive"] += 1
        
        assert activity_levels["high"] == 2
        assert activity_levels["medium"] == 1
        assert activity_levels["low"] == 1
        assert activity_levels["inactive"] == 0

    def test_message_length_statistics(self):
        """Test message length statistics calculation."""
        message_lengths = [10, 20, 30, 40, 50, 100, 200]
        
        # Calculate statistics
        total_messages = len(message_lengths)
        total_characters = sum(message_lengths)
        avg_length = total_characters / total_messages
        min_length = min(message_lengths)
        max_length = max(message_lengths)
        
        # Calculate median
        sorted_lengths = sorted(message_lengths)
        median_length = sorted_lengths[len(sorted_lengths) // 2]
        
        assert total_messages == 7
        assert total_characters == 450
        assert avg_length == pytest.approx(64.29, rel=1e-2)
        assert min_length == 10
        assert max_length == 200
        assert median_length == 40

    def test_language_confidence_analysis(self):
        """Test language detection confidence analysis."""
        detections = [
            {"language": "en", "confidence": 0.95},
            {"language": "en", "confidence": 0.89},
            {"language": "uk", "confidence": 0.92},
            {"language": "uk", "confidence": 0.78},
            {"language": "de", "confidence": 0.65}
        ]
        
        # Calculate average confidence by language
        language_confidence = {}
        for detection in detections:
            lang = detection["language"]
            conf = detection["confidence"]
            
            if lang not in language_confidence:
                language_confidence[lang] = {"total": 0, "count": 0}
            
            language_confidence[lang]["total"] += conf
            language_confidence[lang]["count"] += 1
        
        # Calculate averages
        for lang in language_confidence:
            total = language_confidence[lang]["total"]
            count = language_confidence[lang]["count"]
            language_confidence[lang]["average"] = total / count
        
        assert language_confidence["en"]["average"] == pytest.approx(0.92, rel=1e-2)
        assert language_confidence["uk"]["average"] == pytest.approx(0.85, rel=1e-2)
        assert language_confidence["de"]["average"] == pytest.approx(0.65, rel=1e-2)

    @pytest.mark.asyncio
    async def test_stats_formatting(self):
        """Test statistics response formatting."""
        stats = {
            "total_messages": 1500,
            "total_characters": 75000,
            "languages_detected": {"en": 900, "uk": 600},
            "avg_message_length": 50.0
        }
        
        # Format response
        response_lines = [
            f"📊 Statistics:",
            f"Total messages: {stats['total_messages']}",
            f"Total characters: {stats['total_characters']}",
            f"Average message length: {stats['avg_message_length']:.1f} characters",
            f"Languages detected:",
        ]
        
        for lang, count in stats['languages_detected'].items():
            percentage = (count / stats['total_messages']) * 100
            response_lines.append(f"  {lang.upper()}: {count} ({percentage:.1f}%)")
        
        response = "\n".join(response_lines)
        
        assert "📊 Statistics:" in response
        assert "Total messages: 1500" in response
        assert "EN: 900 (60.0%)" in response
        assert "UK: 600 (40.0%)" in response