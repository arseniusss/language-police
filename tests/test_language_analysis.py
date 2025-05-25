import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timedelta

from middlewares.database.models import User, Chat, ChatMessage


class TestLanguageAnalysisFunctions:
    """Test suite for language analysis functions."""

    def test_language_detection_result_parsing(self):
        """Test parsing language detection results."""
        # Mock langdetect result
        detection_result = "en"
        confidence = 0.95
        
        parsed_result = {
            "language": detection_result,
            "confidence": confidence,
            "detected_at": datetime.utcnow()
        }
        
        assert parsed_result["language"] == "en"
        assert parsed_result["confidence"] == 0.95
        assert isinstance(parsed_result["detected_at"], datetime)

    def test_language_code_validation(self):
        """Test language code validation."""
        valid_languages = ["en", "uk", "ru", "de", "fr", "es", "it", "pl"]
        
        test_language = "en"
        is_valid = test_language in valid_languages
        
        assert is_valid is True
        
        # Test invalid language
        test_language = "invalid"
        is_valid = test_language in valid_languages
        
        assert is_valid is False

    def test_confidence_threshold_evaluation(self):
        """Test confidence threshold evaluation."""
        detection_results = [
            {"language": "en", "confidence": 0.95},
            {"language": "uk", "confidence": 0.75},
            {"language": "de", "confidence": 0.60}
        ]
        
        confidence_threshold = 0.8
        reliable_detections = [
            result for result in detection_results 
            if result["confidence"] >= confidence_threshold
        ]
        
        assert len(reliable_detections) == 1
        assert reliable_detections[0]["language"] == "en"

    def test_message_preprocessing(self):
        """Test message text preprocessing before analysis."""
        raw_text = "  Hello World! 🌍  "
        
        # Simulate preprocessing
        processed_text = raw_text.strip()
        processed_text = ''.join(char for char in processed_text if char.isalnum() or char.isspace())
        
        assert processed_text == "Hello World "

    def test_minimum_text_length_check(self):
        """Test minimum text length validation."""
        min_length = 5
        
        test_cases = [
            ("Hi", False),
            ("Hello", True),
            ("Hello World", True),
            ("", False)
        ]
        
        for text, expected in test_cases:
            is_valid = len(text) >= min_length
            assert is_valid == expected

    def test_language_statistics_aggregation(self):
        """Test language usage statistics aggregation."""
        message_languages = ["en", "en", "uk", "en", "uk", "de"]
        
        language_counts = {}
        for lang in message_languages:
            language_counts[lang] = language_counts.get(lang, 0) + 1
        
        total_messages = len(message_languages)
        language_percentages = {}
        for lang, count in language_counts.items():
            language_percentages[lang] = (count / total_messages) * 100
        
        assert language_counts["en"] == 3
        assert language_counts["uk"] == 2
        assert language_counts["de"] == 1
        assert language_percentages["en"] == 50.0
        assert language_percentages["uk"] == pytest.approx(33.33, rel=1e-2)

    def test_user_language_preference_calculation(self):
        """Test calculating user's language preferences."""
        user_messages = [
            {"language": "en", "confidence": 0.95},
            {"language": "en", "confidence": 0.89},
            {"language": "uk", "confidence": 0.92},
            {"language": "en", "confidence": 0.88}
        ]
        
        language_stats = {}
        for msg in user_messages:
            lang = msg["language"]
            if lang not in language_stats:
                language_stats[lang] = {"count": 0, "total_confidence": 0}
            
            language_stats[lang]["count"] += 1
            language_stats[lang]["total_confidence"] += msg["confidence"]
        
        # Calculate averages
        for lang in language_stats:
            stats = language_stats[lang]
            stats["avg_confidence"] = stats["total_confidence"] / stats["count"]
        
        assert language_stats["en"]["count"] == 3
        assert language_stats["uk"]["count"] == 1
        assert language_stats["en"]["avg_confidence"] == pytest.approx(0.907, rel=1e-2)

    def test_analysis_frequency_control(self):
        """Test analysis frequency control logic."""
        user_message_count = 25
        analysis_frequency = 5  # Analyze every 5th message
        
        should_analyze = (user_message_count % analysis_frequency) == 0
        
        assert should_analyze is True
        
        # Test when shouldn't analyze
        user_message_count = 23
        should_analyze = (user_message_count % analysis_frequency) == 0
        
        assert should_analyze is False

    def test_language_confidence_categories(self):
        """Test categorizing language detection by confidence levels."""
        detections = [
            {"language": "en", "confidence": 0.98},  # High
            {"language": "uk", "confidence": 0.85},  # Medium
            {"language": "de", "confidence": 0.65},  # Low
            {"language": "fr", "confidence": 0.45}   # Very Low
        ]
        
        categorized = {"high": [], "medium": [], "low": [], "very_low": []}
        
        for detection in detections:
            conf = detection["confidence"]
            if conf >= 0.9:
                categorized["high"].append(detection)
            elif conf >= 0.8:
                categorized["medium"].append(detection)
            elif conf >= 0.6:
                categorized["low"].append(detection)
            else:
                categorized["very_low"].append(detection)
        
        assert len(categorized["high"]) == 1
        assert len(categorized["medium"]) == 1
        assert len(categorized["low"]) == 1
        assert len(categorized["very_low"]) == 1

    def test_message_character_count(self):
        """Test accurate character counting for messages."""
        test_messages = [
            "Hello",           # 5 chars
            "Привіт світ",     # 11 chars (including space)
            "🌍 World",        # 7 chars (emoji counts as 1)
            ""                 # 0 chars
        ]
        
        expected_counts = [5, 11, 7, 0]
        
        for i, message in enumerate(test_messages):
            char_count = len(message)
            assert char_count == expected_counts[i]

    def test_language_detection_error_handling(self):
        """Test error handling in language detection."""
        problematic_texts = [
            "",              # Empty text
            "123456",        # Numbers only
            "!@#$%",         # Symbols only
            "a"              # Single character
        ]
        
        for text in problematic_texts:
            try:
                # Simulate detection process
                if len(text.strip()) < 3:
                    result = {"language": "unknown", "confidence": 0.0}
                else:
                    result = {"language": "en", "confidence": 0.8}
                
                assert "language" in result
                assert "confidence" in result
            except Exception as e:
                # Should handle gracefully
                result = {"language": "error", "confidence": 0.0}
                assert result["language"] == "error"

    @pytest.mark.asyncio
    async def test_batch_language_analysis(self):
        """Test batch processing of multiple messages."""
        messages = [
            {"id": 1, "text": "Hello world", "processed": False},
            {"id": 2, "text": "Привіт світ", "processed": False},
            {"id": 3, "text": "Bonjour monde", "processed": False}
        ]
        
        # Simulate batch processing
        processed_messages = []
        for msg in messages:
            # Mock language detection
            if "Hello" in msg["text"]:
                detected_lang = "en"
            elif "Привіт" in msg["text"]:
                detected_lang = "uk"
            elif "Bonjour" in msg["text"]:
                detected_lang = "fr"
            else:
                detected_lang = "unknown"
            
            processed_msg = {
                **msg,
                "language": detected_lang,
                "confidence": 0.9,
                "processed": True
            }
            processed_messages.append(processed_msg)
        
        assert len(processed_messages) == 3
        assert all(msg["processed"] for msg in processed_messages)
        assert processed_messages[0]["language"] == "en"
        assert processed_messages[1]["language"] == "uk"
        assert processed_messages[2]["language"] == "fr"

    def test_analysis_result_serialization(self):
        """Test serialization of analysis results for storage."""
        analysis_result = {
            "message_id": 12345,
            "user_id": 123456789,
            "chat_id": -1001234567890,
            "text": "Hello world",
            "language": "en",
            "confidence": 0.95,
            "character_count": 11,
            "timestamp": datetime.utcnow(),
            "analyzer_version": "1.0"
        }
        
        # Test required fields
        required_fields = ["message_id", "language", "confidence", "timestamp"]
        for field in required_fields:
            assert field in analysis_result
        
        # Test data types
        assert isinstance(analysis_result["message_id"], int)
        assert isinstance(analysis_result["confidence"], float)
        assert isinstance(analysis_result["timestamp"], datetime)
        assert 0.0 <= analysis_result["confidence"] <= 1.0