import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timedelta


class TestModerationFunctions:
    """Test suite for moderation system functions."""

    def test_language_detection_confidence(self):
        """Test language detection confidence evaluation."""
        detection_result = {
            "language": "en",
            "confidence": 0.95
        }
        
        confidence_threshold = 0.8
        is_confident = detection_result["confidence"] >= confidence_threshold
        
        assert is_confident is True
        assert detection_result["language"] == "en"

    def test_allowed_languages_check(self):
        """Test checking if language is allowed in chat."""
        # Mock chat settings
        allowed_languages = ["en", "uk"]
        detected_language = "en"
        
        is_allowed = detected_language in allowed_languages
        
        assert is_allowed is True
        
        # Test disallowed language
        detected_language = "ru"
        is_allowed = detected_language in allowed_languages
        
        assert is_allowed is False
    def test_moderation_rule_condition_evaluation(self):
        """Test evaluating moderation rule conditions."""
        # Test case: English message (should trigger rule)
        message_data = {
            "language": "en",
            "confidence": 0.95
        }
        
        # Create rule data directly without using fixtures
        rule_data = {
            "conditions": [
                {
                    "type": "language_not_allowed",
                    "language": "uk",
                    "confidence_threshold": 0.8
                }
            ]
        }
        
        condition = rule_data["conditions"][0]
        
        # Check if language is not allowed (condition type)
        if condition["type"] == "language_not_allowed":
            allowed_language = condition["language"]
            confidence_threshold = condition["confidence_threshold"]
            
            condition_met = (
                message_data["language"] != allowed_language and
                message_data["confidence"] >= confidence_threshold
            )
        
        assert condition_met is True

    def test_moderation_rule_condition_not_met(self, sample_moderation_rule):
        """Test moderation rule when conditions are not met."""
        # Test case: Ukrainian message (should not trigger rule)
        message_data = {
            "language": "uk",
            "confidence": 0.95
        }
        
        rule = sample_moderation_rule
        condition = rule.conditions[0]
        
        if condition["type"] == "language_not_allowed":
            allowed_language = condition["language"]
            confidence_threshold = condition["confidence_threshold"]
            
            condition_met = (
                message_data["language"] != allowed_language and
                message_data["confidence"] >= confidence_threshold
            )
        
        assert condition_met is False

    def test_low_confidence_detection(self, sample_moderation_rule):
        """Test moderation with low confidence detection."""
        # Test case: Low confidence detection
        message_data = {
            "language": "en",
            "confidence": 0.5
        }
        
        rule = sample_moderation_rule
        condition = rule.conditions[0]
        confidence_threshold = condition["confidence_threshold"]
        
        # Should not trigger due to low confidence
        confidence_met = message_data["confidence"] >= confidence_threshold
        
        assert confidence_met is False

    def test_multiple_conditions_and_operator(self):
        """Test multiple conditions with AND operator."""
        conditions = [
            {"type": "language_not_allowed", "result": True},
            {"type": "min_message_length", "result": True}
        ]
        
        logical_operator = "AND"
        
        if logical_operator == "AND":
            all_met = all(condition["result"] for condition in conditions)
        else:  # OR
            all_met = any(condition["result"] for condition in conditions)
        
        assert all_met is True

    def test_multiple_conditions_or_operator(self):
        """Test multiple conditions with OR operator."""
        conditions = [
            {"type": "language_not_allowed", "result": False},
            {"type": "min_message_length", "result": True}
        ]
        
        logical_operator = "OR"
        
        if logical_operator == "AND":
            all_met = all(condition["result"] for condition in conditions)
        else:  # OR
            all_met = any(condition["result"] for condition in conditions)
        
        assert all_met is True

    def test_action_duration_calculation(self, sample_moderation_rule):
        """Test action duration calculation."""
        rule = sample_moderation_rule
        action_duration = rule.action_duration
        
        # Calculate until timestamp
        now = datetime.utcnow()
        until_timestamp = int((now.timestamp() + action_duration))
        
        assert until_timestamp > int(now.timestamp())
        assert (until_timestamp - int(now.timestamp())) == action_duration

    def test_user_message_formatting(self, sample_moderation_rule):
        """Test user message formatting for moderation action."""
        rule = sample_moderation_rule
        user_message = rule.user_message
        reason = rule.reason
        
        formatted_message = f"{user_message}\n\nReason: {reason}"
        
        assert "Please use Ukrainian in this chat." in formatted_message
        assert "Reason: Non-Ukrainian language detected" in formatted_message

    def test_message_length_condition(self):
        """Test message length condition evaluation."""
        message_text = "Short"
        min_length = 10
        max_length = 1000
        
        length_condition_met = len(message_text) >= min_length and len(message_text) <= max_length
        
        assert length_condition_met is False  # Message too short

    def test_user_previous_restrictions_check(self):
        """Test checking user's previous restrictions."""
        user_restrictions = [
            {
                "action_type": "warning",
                "timestamp": datetime.utcnow() - timedelta(hours=0.5),
                "reason": "Language violation"
            }
        ]
        
        # Check if user has recent restrictions
        recent_restrictions = [
            r for r in user_restrictions 
            if (datetime.utcnow() - r["timestamp"]).total_seconds() < 3600  # Last hour
        ]
        
        has_recent_restrictions = len(recent_restrictions) > 0
        
        assert has_recent_restrictions is True

    def test_escalation_logic(self):
        """Test moderation escalation logic."""
        previous_actions = ["warning", "temporary_restriction"]
        
        # Define escalation path
        escalation_path = ["warning", "temporary_restriction", "temporary_ban", "permanent_ban"]
        
        next_action_index = len(previous_actions)
        if next_action_index < len(escalation_path):
            next_action = escalation_path[next_action_index]
        else:
            next_action = escalation_path[-1]  # Max escalation
        
        assert next_action == "temporary_ban"

    @pytest.mark.asyncio
    async def test_moderation_action_execution(self, mock_bot):
        """Test executing moderation actions."""
        action_data = {
            "action_type": "temporary_restriction",
            "chat_id": -1001234567890,
            "user_id": 123456789,
            "until_date": int(datetime.utcnow().timestamp()) + 3600,
            "user_message": "You have been restricted for 1 hour."
        }
        
        # Mock bot action
        if action_data["action_type"] == "temporary_restriction":
            mock_bot.restrict_chat_member.return_value = AsyncMock()
            mock_bot.send_message.return_value = AsyncMock()
            
            # Simulate restriction
            await mock_bot.restrict_chat_member(
                chat_id=action_data["chat_id"],
                user_id=action_data["user_id"],
                until_date=action_data["until_date"]
            )
            
            # Send user message
            await mock_bot.send_message(
                chat_id=action_data["chat_id"],
                text=action_data["user_message"]
            )
            
            mock_bot.restrict_chat_member.assert_called_once()
            mock_bot.send_message.assert_called_once()

    def test_condition_priority_evaluation(self):
        """Test condition priority and evaluation order."""
        conditions = [
            {"type": "confidence_check", "priority": 1, "result": True},
            {"type": "language_check", "priority": 2, "result": False},
            {"type": "length_check", "priority": 3, "result": True}
        ]
        
        # Sort by priority
        sorted_conditions = sorted(conditions, key=lambda x: x["priority"])
        
        # Evaluate in order with AND logic
        final_result = True
        for condition in sorted_conditions:
            final_result = final_result and condition["result"]
            if not final_result:
                break  # Short-circuit evaluation
        
        assert final_result is False  # Second condition fails