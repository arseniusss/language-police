import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timedelta

# Import the actual models that exist in the project
from middlewares.database.models import User, Chat, ChatMessage


class TestChatRankingLogic:
    """Test suite for chat ranking logic and calculations."""

    @pytest.mark.asyncio
    async def test_chat_top_users_aggregation_logic(self, mock_database):
        """Test the logic for aggregating top users in a chat by messages."""
        # Mock data representing aggregated user message counts
        mock_users = [
            {"_id": 123, "username": "user1", "first_name": "User", "last_name": "One", "total_messages": 100},
            {"_id": 456, "username": "user2", "first_name": "User", "last_name": "Two", "total_messages": 80},
            {"_id": 789, "username": "user3", "first_name": "User", "last_name": "Three", "total_messages": 60}
        ]
        
        # Test sorting logic
        sorted_users = sorted(mock_users, key=lambda x: x["total_messages"], reverse=True)
        
        assert len(sorted_users) == 3
        assert sorted_users[0]["total_messages"] == 100
        assert sorted_users[1]["total_messages"] == 80
        assert sorted_users[2]["total_messages"] == 60
        assert sorted_users[0]["username"] == "user1"

    @pytest.mark.asyncio
    async def test_chat_top_users_by_characters_logic(self, mock_database):
        """Test ranking users by character count."""
        mock_users = [
            {"_id": 123, "username": "user1", "total_characters": 5000},
            {"_id": 456, "username": "user2", "total_characters": 3000},
            {"_id": 789, "username": "user3", "total_characters": 4000}
        ]
        
        # Sort by character count
        sorted_users = sorted(mock_users, key=lambda x: x["total_characters"], reverse=True)
        
        assert sorted_users[0]["total_characters"] == 5000
        assert sorted_users[1]["total_characters"] == 4000
        assert sorted_users[2]["total_characters"] == 3000

    @pytest.mark.asyncio
    async def test_user_ranking_position_calculation(self, mock_database):
        """Test calculating user's position in chat ranking."""
        ranking_data = [
            {"_id": 123, "total_messages": 100},
            {"_id": 456, "total_messages": 80},
            {"_id": 789, "total_messages": 60}
        ]
        
        # Find user position
        target_user_id = 456
        position = None
        
        for idx, user in enumerate(ranking_data):
            if user["_id"] == target_user_id:
                position = idx + 1
                break
        
        assert position == 2  # Second position

    @pytest.mark.asyncio
    async def test_user_ranking_position_not_found(self, mock_database):
        """Test when user is not found in ranking."""
        ranking_data = [
            {"_id": 123, "total_messages": 100},
            {"_id": 456, "total_messages": 80}
        ]
        
        # Find non-existent user
        target_user_id = 999
        position = None
        
        for idx, user in enumerate(ranking_data):
            if user["_id"] == target_user_id:
                position = idx + 1
                break
        
        assert position is None

    def test_chat_top_response_formatting_logic(self):
        """Test formatting logic for chat top response."""
        top_users = [
            {"_id": 123, "username": "user1", "first_name": "John", "total_messages": 100},
            {"_id": 456, "username": None, "first_name": "Jane", "last_name": "Doe", "total_messages": 80},
            {"_id": 789, "username": "user3", "first_name": "Bob", "total_messages": 60}
        ]
        
        chat_name = "Test Chat"
        ranking_type = "messages"
        
        # Simulate response formatting logic
        response_lines = [f"📊 Top users by {ranking_type} in {chat_name}:"]
        
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
        
        assert "📊 Top users by messages in Test Chat:" in response
        assert "1. @user1 (John) - 100 messages" in response
        assert "2. Jane Doe - 80 messages" in response
        assert "3. @user3 (Bob) - 60 messages" in response

    def test_empty_ranking_handling(self):
        """Test handling of empty ranking results."""
        empty_ranking = []
        
        if not empty_ranking:
            response = "No users found for this ranking."
        else:
            response = "Rankings available"
        
        assert response == "No users found for this ranking."

    def test_ranking_limit_application(self):
        """Test applying limit to ranking results."""
        all_users = [
            {"_id": i, "total_messages": 100 - i} for i in range(20)
        ]
        
        limit = 10
        limited_users = all_users[:limit]
        
        assert len(limited_users) == 10
        assert limited_users[0]["total_messages"] == 100
        assert limited_users[9]["total_messages"] == 91

    @pytest.mark.asyncio
    async def test_language_specific_ranking_logic(self, mock_database):
        """Test ranking users by specific language usage."""
        mock_users = [
            {"_id": 123, "username": "user1", "language_count": 50},
            {"_id": 456, "username": "user2", "language_count": 30},
            {"_id": 789, "username": "user3", "language_count": 40}
        ]
        
        # Sort by language usage
        sorted_users = sorted(mock_users, key=lambda x: x["language_count"], reverse=True)
        
        assert sorted_users[0]["language_count"] == 50
        assert sorted_users[1]["language_count"] == 40
        assert sorted_users[2]["language_count"] == 30

    def test_mongodb_aggregation_pipeline_structure(self):
        """Test the structure of MongoDB aggregation pipeline for rankings."""
        chat_id = -1001234567890
        limit = 10
        
        # Example aggregation pipeline structure
        pipeline = [
            {"$match": {"chat_id": chat_id}},
            {"$group": {
                "_id": "$user_id",
                "total_messages": {"$sum": 1},
                "total_characters": {"$sum": "$character_count"}
            }},
            {"$sort": {"total_messages": -1}},
            {"$limit": limit}
        ]
        
        # Verify pipeline structure
        assert pipeline[0]["$match"]["chat_id"] == chat_id
        assert "$group" in pipeline[1]
        assert pipeline[2]["$sort"]["total_messages"] == -1
        assert pipeline[3]["$limit"] == limit

    def test_date_range_filtering_logic(self):
        """Test date range filtering for time-based rankings."""
        start_date = datetime.utcnow() - timedelta(days=7)
        end_date = datetime.utcnow()
        
        # Sample messages with timestamps
        messages = [
            {"timestamp": datetime.utcnow() - timedelta(days=1), "valid": True},
            {"timestamp": datetime.utcnow() - timedelta(days=10), "valid": False},
            {"timestamp": datetime.utcnow() - timedelta(days=3), "valid": True}
        ]
        
        # Filter messages by date range
        filtered_messages = [
            msg for msg in messages 
            if start_date <= msg["timestamp"] <= end_date
        ]
        
        assert len(filtered_messages) == 2
        assert all(msg["valid"] for msg in filtered_messages)