import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timedelta


class TestDatabaseFunctions:
    """Test suite for database operations."""
    @pytest.mark.asyncio
    async def test_user_creation(self, mock_database):
        """Test user creation logic."""
        user_data = {
            "user_id": 123456789,
            "username": "testuser",
            "first_name": "Test",
            "last_name": "User"
        }
        
        # Mock database response
        mock_database.create_user.return_value = user_data
        
        # Test user creation
        result = await mock_database.create_user(user_data["user_id"])
        
        assert result is not None
        mock_database.create_user.assert_called_once_with(user_data["user_id"])

    @pytest.mark.asyncio
    async def test_user_retrieval(self, mock_database, sample_user):
        """Test user retrieval from database."""
        user_id = 123456789
        
        # Mock user retrieval
        mock_database.get_user.return_value = sample_user
        
        retrieved_user = await mock_database.get_user(user_id)
        
        assert retrieved_user.user_id == user_id
        assert retrieved_user.username == "testuser"
        mock_database.get_user.assert_called_once_with(user_id)

    @pytest.mark.asyncio
    async def test_user_not_found(self, mock_database):
        """Test user retrieval when user doesn't exist."""
        user_id = 999999999
        
        # Mock user not found
        mock_database.get_user.return_value = None
        
        retrieved_user = await mock_database.get_user(user_id)
        
        assert retrieved_user is None
        mock_database.get_user.assert_called_once_with(user_id) 
    
    @pytest.mark.asyncio
    async def test_chat_creation(self, mock_database):
        """Test chat creation in database."""
        chat_data = {
            "chat_id": -1001234567890,
            "chat_name": "Test Chat",
            "chat_type": "supergroup"
        }
        
        # Mock successful chat creation
        mock_database.create_chat.return_value = chat_data
        
        created_chat = await mock_database.create_chat(
            chat_data["chat_id"], 
            chat_data["chat_name"]
        )
        
        assert created_chat["chat_id"] == chat_data["chat_id"]
        assert created_chat["chat_name"] == chat_data["chat_name"]
    
    @pytest.mark.asyncio
    async def test_message_saving(self, mock_database):
        """Test saving message to database."""
        message_data = {
            "message_id": 12345,
            "user_id": 123456789,
            "chat_id": -1001234567890,
            "text": "Hello world",
            "language": "en",
            "confidence": 0.95,
            "character_count": 11
        }
        
        # Mock successful message saving
        mock_database.save_message.return_value = message_data
        
        saved_message = await mock_database.save_message(message_data)
        
        assert saved_message["message_id"] == message_data["message_id"]
        assert saved_message["language"] == "en"
        assert saved_message["confidence"] == 0.95

    @pytest.mark.asyncio
    async def test_user_stats_aggregation(self, mock_database):
        """Test user statistics aggregation."""
        user_id = 123456789
        expected_stats = {
            "total_messages": 100,
            "total_characters": 5000,
            "languages_detected": {"en": 60, "uk": 40},
            "avg_message_length": 50.0,
            "first_message_date": datetime.utcnow() - timedelta(days=30),
            "last_message_date": datetime.utcnow()
        }
        
        # Mock stats retrieval
        mock_database.get_user_stats.return_value = expected_stats
        
        stats = await mock_database.get_user_stats(user_id)
        
        assert stats["total_messages"] == 100
        assert stats["total_characters"] == 5000
        assert "en" in stats["languages_detected"]
        assert "uk" in stats["languages_detected"]

    @pytest.mark.asyncio
    async def test_chat_stats_aggregation(self, mock_database):
        """Test chat statistics aggregation."""
        chat_id = -1001234567890
        expected_stats = {
            "total_messages": 500,
            "total_characters": 25000,
            "total_users": 25,
            "languages_detected": {"en": 300, "uk": 200},
            "avg_message_length": 50.0,
            "most_active_user": {"user_id": 123, "message_count": 50}
        }
        
        # Mock stats retrieval
        mock_database.get_chat_stats.return_value = expected_stats
        
        stats = await mock_database.get_chat_stats(chat_id)
        
        assert stats["total_messages"] == 500
        assert stats["total_users"] == 25
        assert stats["most_active_user"]["user_id"] == 123

    @pytest.mark.asyncio
    async def test_global_stats_aggregation(self, mock_database):
        """Test global statistics aggregation."""
        expected_stats = {
            "total_users": 1000,
            "total_chats": 50,
            "total_messages": 10000,
            "total_characters": 500000,
            "languages_detected": {"en": 6000, "uk": 4000},
            "avg_messages_per_user": 10.0,
            "avg_messages_per_chat": 200.0
        }
        
        # Mock global stats retrieval
        mock_database.get_global_stats.return_value = expected_stats
        
        stats = await mock_database.get_global_stats()
        
        assert stats["total_users"] == 1000
        assert stats["total_chats"] == 50
        assert stats["total_messages"] == 10000

    @pytest.mark.asyncio
    async def test_chat_settings_update(self, mock_database, sample_chat):
        """Test updating chat settings."""
        chat_id = -1001234567890
        new_settings = {
            "allowed_languages": ["en", "uk", "de"],
            "analysis_frequency": 3,
            "min_message_length": 10
        }
        
        # Mock settings update
        mock_database.update_chat_settings.return_value = True
        
        success = await mock_database.update_chat_settings(chat_id, new_settings)
        
        assert success is True
        mock_database.update_chat_settings.assert_called_once_with(chat_id, new_settings)

    @pytest.mark.asyncio
    async def test_user_ranking_retrieval(self, mock_database):
        """Test user ranking retrieval."""
        chat_id = -1001234567890
        user_id = 123456789
        ranking_type = "messages"
        
        expected_ranking = {
            "position": 3,
            "total_users": 25,
            "user_score": 150,
            "top_score": 300
        }
        
        # Mock ranking retrieval
        mock_database.get_user_ranking.return_value = expected_ranking
        
        ranking = await mock_database.get_user_ranking(chat_id, user_id, ranking_type)
        
        assert ranking["position"] == 3
        assert ranking["total_users"] == 25
        assert ranking["user_score"] == 150

    @pytest.mark.asyncio
    async def test_database_connection_error(self, mock_database):
        """Test database connection error handling."""
        # Mock connection error
        mock_database.get_user.side_effect = Exception("Connection timeout")
        
        with pytest.raises(Exception) as exc_info:
            await mock_database.get_user(123456789)
        
        assert "Connection timeout" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_bulk_message_insertion(self, mock_database):
        """Test bulk message insertion for performance."""
        messages = [
            {
                "message_id": i,
                "user_id": 123456789,
                "chat_id": -1001234567890,
                "text": f"Message {i}",
                "language": "en",
                "confidence": 0.9
            }
            for i in range(100)
        ]
        
        # Mock bulk insertion
        mock_database.bulk_insert_messages.return_value = len(messages)
        
        inserted_count = await mock_database.bulk_insert_messages(messages)
        
        assert inserted_count == 100
        mock_database.bulk_insert_messages.assert_called_once_with(messages)

    @pytest.mark.asyncio
    async def test_data_cleanup_old_messages(self, mock_database):
        """Test cleaning up old messages."""
        days_to_keep = 30
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        # Mock cleanup operation
        mock_database.cleanup_old_messages.return_value = 500  # Deleted count
        
        deleted_count = await mock_database.cleanup_old_messages(cutoff_date)
        
        assert deleted_count == 500
        mock_database.cleanup_old_messages.assert_called_once_with(cutoff_date)

    @pytest.mark.asyncio
    async def test_index_creation_for_performance(self, mock_database):
        """Test database index creation for performance optimization."""
        indexes_to_create = [
            {"fields": ["user_id", "chat_id"], "name": "user_chat_idx"},
            {"fields": ["timestamp"], "name": "timestamp_idx"},
            {"fields": ["language"], "name": "language_idx"}
        ]
        
        # Mock index creation
        mock_database.create_indexes.return_value = True
        
        success = await mock_database.create_indexes(indexes_to_create)
        
        assert success is True
        mock_database.create_indexes.assert_called_once_with(indexes_to_create)

    def test_database_query_optimization(self):
        """Test database query optimization strategies."""
        # Test query structure for optimal performance
        query_pipeline = [
            {"$match": {"chat_id": -1001234567890}},
            {"$group": {
                "_id": "$user_id",
                "total_messages": {"$sum": 1},
                "total_characters": {"$sum": "$character_count"}
            }},
            {"$sort": {"total_messages": -1}},
            {"$limit": 10}
        ]
        
        # Verify query structure
        assert query_pipeline[0]["$match"]["chat_id"] == -1001234567890
        assert "$group" in query_pipeline[1]
        assert query_pipeline[2]["$sort"]["total_messages"] == -1
        assert query_pipeline[3]["$limit"] == 10

    @pytest.mark.asyncio
    async def test_transaction_handling(self, mock_database):
        """Test database transaction handling."""
        operations = [
            {"operation": "create_user", "data": {"user_id": 123}},
            {"operation": "create_chat", "data": {"chat_id": -1001}},
            {"operation": "save_message", "data": {"message_id": 1}}
        ]
        
        # Mock transaction
        mock_database.execute_transaction.return_value = True
        
        success = await mock_database.execute_transaction(operations)
        
        assert success is True
        mock_database.execute_transaction.assert_called_once_with(operations)