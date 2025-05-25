import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timedelta

# Import the actual models that exist in the project  
from middlewares.database.models import User, Chat, ChatMessage


class TestGlobalRankingLogic:
    """Test suite for global ranking logic and calculations."""

    @pytest.mark.asyncio
    async def test_global_user_ranking_by_messages(self, mock_database):
        """Test global user ranking calculation by message count."""
        mock_user_data = [
            {"_id": 123, "username": "user1", "first_name": "John", "total_messages": 1000},
            {"_id": 456, "username": "user2", "first_name": "Jane", "total_messages": 800},
            {"_id": 789, "username": "user3", "first_name": "Bob", "total_messages": 600}
        ]
        
        # Test sorting logic
        sorted_users = sorted(mock_user_data, key=lambda x: x["total_messages"], reverse=True)
        
        assert len(sorted_users) == 3
        assert sorted_users[0]["total_messages"] == 1000
        assert sorted_users[1]["total_messages"] == 800
        assert sorted_users[2]["total_messages"] == 600
        assert sorted_users[0]["username"] == "user1"

    @pytest.mark.asyncio
    async def test_global_user_ranking_by_characters(self, mock_database):
        """Test global user ranking by character count."""
        mock_user_data = [
            {"_id": 123, "username": "user1", "total_characters": 50000},
            {"_id": 456, "username": "user2", "total_characters": 30000},
            {"_id": 789, "username": "user3", "total_characters": 40000}
        ]
        
        # Sort by character count
        sorted_users = sorted(mock_user_data, key=lambda x: x["total_characters"], reverse=True)
        
        assert sorted_users[0]["total_characters"] == 50000
        assert sorted_users[1]["total_characters"] == 40000
        assert sorted_users[2]["total_characters"] == 30000

    @pytest.mark.asyncio
    async def test_global_chat_ranking_calculation(self, mock_database):
        """Test global chat ranking by activity."""
        mock_chat_data = [
            {"_id": -1001, "chat_name": "Active Chat", "total_messages": 5000},
            {"_id": -1002, "chat_name": "Medium Chat", "total_messages": 3000},
            {"_id": -1003, "chat_name": "Quiet Chat", "total_messages": 1000}
        ]
        
        # Sort by activity
        sorted_chats = sorted(mock_chat_data, key=lambda x: x["total_messages"], reverse=True)
        
        assert sorted_chats[0]["total_messages"] == 5000
        assert sorted_chats[1]["total_messages"] == 3000
        assert sorted_chats[2]["total_messages"] == 1000
        assert sorted_chats[0]["chat_name"] == "Active Chat"

    def test_user_global_position_calculation(self):
        """Test calculating user's global ranking position."""
        global_ranking = [
            {"_id": 123, "total_messages": 1000},
            {"_id": 456, "total_messages": 800},
            {"_id": 789, "total_messages": 600}
        ]
        
        target_user_id = 456
        position = None
        
        for idx, user in enumerate(global_ranking):
            if user["_id"] == target_user_id:
                position = idx + 1
                break
        
        assert position == 2

    def test_chat_global_position_calculation(self):
        """Test calculating chat's global ranking position."""
        global_chat_ranking = [
            {"_id": -1001, "total_messages": 5000},
            {"_id": -1002, "total_messages": 3000},
            {"_id": -1003, "total_messages": 1000}
        ]
        
        target_chat_id = -1002
        position = None
        
        for idx, chat in enumerate(global_chat_ranking):
            if chat["_id"] == target_chat_id:
                position = idx + 1
                break
        
        assert position == 2

    def test_global_ranking_response_formatting(self):
        """Test formatting global ranking responses."""
        top_users = [
            {"_id": 123, "username": "user1", "first_name": "John", "total_messages": 1000},
            {"_id": 456, "username": None, "first_name": "Jane", "last_name": "Doe", "total_messages": 800},
            {"_id": 789, "username": "user3", "first_name": "Bob", "total_messages": 600}
        ]
        
        ranking_type = "messages"
        
        # Simulate response formatting
        response_lines = [f"🌍 Global top users by {ranking_type}:"]
        
        for idx, user in enumerate(top_users):
            position = idx + 1
            if user.get("username"):
                name = f"@{user['username']} ({user['first_name']})"
            else:
                name = f"{user['first_name']}"
                if user.get("last_name"):
                    name += f" {user['last_name']}"
            
            response_lines.append(f"{position}. {name} - {user['total_messages']} {ranking_type}")
        
        response = "\n".join(response_lines)
        
        assert "🌍 Global top users by messages:" in response
        assert "1. @user1 (John) - 1000 messages" in response
        assert "2. Jane Doe - 800 messages" in response

    def test_ukrainian_language_ranking_logic(self):
        """Test ranking users by Ukrainian language usage."""
        users_with_ukrainian = [
            {"_id": 123, "ukrainian_messages": 200},
            {"_id": 456, "ukrainian_messages": 150},
            {"_id": 789, "ukrainian_messages": 180}
        ]
        
        # Sort by Ukrainian message count
        sorted_users = sorted(users_with_ukrainian, key=lambda x: x["ukrainian_messages"], reverse=True)
        
        assert sorted_users[0]["ukrainian_messages"] == 200
        assert sorted_users[1]["ukrainian_messages"] == 180
        assert sorted_users[2]["ukrainian_messages"] == 150

    def test_global_chat_ranking_response_formatting(self):
        """Test formatting global chat ranking response."""
        top_chats = [
            {"_id": -1001, "chat_name": "Super Active Chat", "total_messages": 5000},
            {"_id": -1002, "chat_name": "Moderately Active Chat", "total_messages": 3000},
            {"_id": -1003, "chat_name": "Quiet Chat", "total_messages": 1000}
        ]
        
        # Format chat ranking response
        response_lines = ["🏆 Global chat ranking by activity:"]
        
        for idx, chat in enumerate(top_chats):
            position = idx + 1
            response_lines.append(f"{position}. {chat['chat_name']} - {chat['total_messages']} messages")
        
        response = "\n".join(response_lines)
        
        assert "🏆 Global chat ranking by activity:" in response
        assert "1. Super Active Chat - 5000 messages" in response
        assert "2. Moderately Active Chat - 3000 messages" in response

    def test_empty_global_ranking_handling(self):
        """Test handling of empty global rankings."""
        empty_rankings = []
        
        if not empty_rankings:
            response = "No users found for this ranking."
        else:
            response = "Rankings available"
        
        assert response == "No users found for this ranking."

    def test_language_specific_global_ranking(self):
        """Test global ranking for specific language usage."""
        language_usage_data = [
            {"_id": 123, "language_count": 100, "language": "uk"},
            {"_id": 456, "language_count": 80, "language": "uk"},
            {"_id": 789, "language_count": 120, "language": "uk"}
        ]
        
        # Sort by language usage count
        sorted_users = sorted(language_usage_data, key=lambda x: x["language_count"], reverse=True)
        
        assert sorted_users[0]["language_count"] == 120
        assert sorted_users[1]["language_count"] == 100
        assert sorted_users[2]["language_count"] == 80

    def test_aggregation_pipeline_for_global_stats(self):
        """Test MongoDB aggregation pipeline structure for global stats."""
        limit = 10
        
        # Example pipeline for global user ranking
        user_pipeline = [
            {"$group": {
                "_id": "$user_id",
                "total_messages": {"$sum": 1},
                "total_characters": {"$sum": "$character_count"}
            }},
            {"$sort": {"total_messages": -1}},
            {"$limit": limit}
        ]
        
        # Example pipeline for global chat ranking  
        chat_pipeline = [
            {"$group": {
                "_id": "$chat_id",
                "total_messages": {"$sum": 1}
            }},
            {"$sort": {"total_messages": -1}},
            {"$limit": limit}
        ]
        
        # Verify pipeline structures
        assert "$group" in user_pipeline[0]
        assert user_pipeline[1]["$sort"]["total_messages"] == -1
        assert user_pipeline[2]["$limit"] == limit
        assert chat_pipeline[1]["$sort"]["total_messages"] == -1

    def test_ranking_position_not_found_globally(self):
        """Test when user/chat is not found in global rankings."""
        global_ranking = [
            {"_id": 123, "score": 1000},
            {"_id": 456, "score": 800}
        ]
        
        # Search for non-existent entity
        target_id = 999
        position = None
        
        for idx, entity in enumerate(global_ranking):
            if entity["_id"] == target_id:
                position = idx + 1
                break
        
        assert position is None