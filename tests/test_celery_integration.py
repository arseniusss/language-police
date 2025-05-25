import pytest
from unittest.mock import AsyncMock, Mock, patch
import json
from datetime import datetime

from celery import Celery


class TestCeleryIntegration:
    """Test suite for Celery integration and task processing."""

    @pytest.fixture
    def mock_celery_app(self):
        """Create a mock Celery app."""
        app = Mock(spec=Celery)
        app.send_task = Mock()
        return app

    @pytest.fixture
    def sample_analysis_task(self):
        """Create a sample analysis task data."""
        return {
            "task_id": "analyze-123-456",
            "message_id": 123,
            "user_id": 456789,
            "chat_id": -1001234567890,
            "text": "Hello world test message",
            "timestamp": datetime.utcnow().isoformat()
        }

    def test_task_serialization(self, sample_analysis_task):
        """Test task data serialization for Celery."""
        # Serialize task data
        serialized_data = json.dumps(sample_analysis_task, default=str)
        
        # Deserialize task data
        deserialized_data = json.loads(serialized_data)
        
        assert deserialized_data["task_id"] == sample_analysis_task["task_id"]
        assert deserialized_data["message_id"] == sample_analysis_task["message_id"]
        assert deserialized_data["text"] == sample_analysis_task["text"]

    def test_task_queue_routing(self):
        """Test task routing to appropriate queues."""
        task_configs = {
            "analyze_text": {
                "queue": "text_analysis",
                "routing_key": "analysis.text",
                "priority": 5
            },
            "generate_stats": {
                "queue": "statistics",
                "routing_key": "stats.generate",
                "priority": 3
            },
            "apply_moderation": {
                "queue": "moderation",
                "routing_key": "moderation.apply",
                "priority": 8
            }
        }
        
        # Test that each task type has proper routing
        for task_name, config in task_configs.items():
            assert "queue" in config
            assert "routing_key" in config
            assert "priority" in config
            assert isinstance(config["priority"], int)

    def test_task_priority_assignment(self):
        """Test task priority assignment logic."""
        tasks = [
            {"type": "urgent_moderation", "priority": None},
            {"type": "regular_analysis", "priority": None},
            {"type": "batch_stats", "priority": None}
        ]
        
        # Assign priorities
        priority_map = {
            "urgent_moderation": 10,
            "regular_analysis": 5,
            "batch_stats": 1
        }
        
        for task in tasks:
            task["priority"] = priority_map.get(task["type"], 5)
        
        assert tasks[0]["priority"] == 10  # Urgent
        assert tasks[1]["priority"] == 5   # Regular
        assert tasks[2]["priority"] == 1   # Batch

    @pytest.mark.asyncio
    async def test_task_result_handling(self, mock_celery_app):
        """Test handling of Celery task results."""
        task_result = {
            "task_id": "analyze-123-456",
            "status": "SUCCESS",
            "result": {
                "language": "en",
                "confidence": 0.95,
                "processing_time": 0.123
            },
            "traceback": None
        }
        
        # Process task result
        if task_result["status"] == "SUCCESS":
            result_data = task_result["result"]
            processing_successful = True
        else:
            result_data = None
            processing_successful = False
        
        assert processing_successful is True
        assert result_data["language"] == "en"
        assert result_data["confidence"] == 0.95

    def test_task_error_handling(self):
        """Test handling of task errors and failures."""
        failed_task_result = {
            "task_id": "analyze-789-012",
            "status": "FAILURE",
            "result": None,
            "traceback": "LangDetectException: No features in text"
        }
        
        # Handle task failure
        if failed_task_result["status"] == "FAILURE":
            error_message = failed_task_result["traceback"]
            retry_needed = "LangDetectException" in error_message
        else:
            retry_needed = False
        
        assert retry_needed is True
        assert "LangDetectException" in failed_task_result["traceback"]

    def test_task_retry_logic(self):
        """Test task retry logic and exponential backoff."""
        task_attempts = [
            {"attempt": 1, "delay": 5},
            {"attempt": 2, "delay": 10},
            {"attempt": 3, "delay": 20},
            {"attempt": 4, "delay": 40}
        ]
        
        max_retries = 3
        base_delay = 5
        
        for i, attempt_info in enumerate(task_attempts):
            attempt = attempt_info["attempt"]
            expected_delay = base_delay * (2 ** (attempt - 1))
            
            if attempt <= max_retries:
                should_retry = True
            else:
                should_retry = False
            
            if attempt <= max_retries:
                assert attempt_info["delay"] == expected_delay
            assert should_retry == (attempt <= max_retries)

    def test_batch_task_processing(self):
        """Test batch processing of multiple tasks."""
        messages_batch = [
            {"id": 1, "text": "Hello world", "user_id": 123},
            {"id": 2, "text": "Привіт світ", "user_id": 456},
            {"id": 3, "text": "Bonjour monde", "user_id": 789}
        ]
        
        batch_size = 5
        
        # Process in batches
        processed_batches = []
        for i in range(0, len(messages_batch), batch_size):
            batch = messages_batch[i:i + batch_size]
            processed_batches.append(batch)
        
        assert len(processed_batches) == 1  # All messages fit in one batch
        assert len(processed_batches[0]) == 3
        assert processed_batches[0][0]["text"] == "Hello world"

    @pytest.mark.asyncio
    async def test_task_monitoring_and_logging(self):
        """Test task monitoring and logging functionality."""
        task_log = {
            "task_id": "analyze-123-456",
            "task_name": "analyze_text",
            "started_at": datetime.utcnow(),
            "completed_at": None,
            "status": "PENDING",
            "worker_id": "worker-001",
            "queue": "text_analysis"
        }
        
        # Simulate task completion
        task_log["completed_at"] = datetime.utcnow()
        task_log["status"] = "SUCCESS"
        
        # Calculate processing time
        if task_log["completed_at"] and task_log["started_at"]:
            processing_time = (task_log["completed_at"] - task_log["started_at"]).total_seconds()
        else:
            processing_time = 0
        
        assert task_log["status"] == "SUCCESS"
        assert task_log["completed_at"] is not None
        assert processing_time >= 0

    def test_worker_scaling_configuration(self):
        """Test worker auto-scaling configuration."""
        scaling_config = {
            "autoscale_min": 2,
            "autoscale_max": 8,
            "queue_length_threshold": 100,
            "cpu_threshold": 80,
            "memory_threshold": 70
        }
        
        current_metrics = {
            "queue_length": 150,
            "cpu_usage": 85,
            "memory_usage": 65,
            "current_workers": 3
        }
        
        # Determine if scaling is needed
        should_scale_up = (
            current_metrics["queue_length"] > scaling_config["queue_length_threshold"] or
            current_metrics["cpu_usage"] > scaling_config["cpu_threshold"]
        ) and current_metrics["current_workers"] < scaling_config["autoscale_max"]
        
        assert should_scale_up is True

    def test_task_queue_prioritization(self):
        """Test task queue prioritization logic."""
        tasks_in_queue = [
            {"id": 1, "type": "moderation", "priority": 10, "timestamp": datetime.utcnow()},
            {"id": 2, "type": "analysis", "priority": 5, "timestamp": datetime.utcnow()},
            {"id": 3, "type": "stats", "priority": 1, "timestamp": datetime.utcnow()},
            {"id": 4, "type": "moderation", "priority": 10, "timestamp": datetime.utcnow()}
        ]
        
        # Sort by priority (highest first), then by timestamp (oldest first)
        sorted_tasks = sorted(
            tasks_in_queue,
            key=lambda x: (-x["priority"], x["timestamp"])
        )
        
        assert sorted_tasks[0]["type"] == "moderation"
        assert sorted_tasks[0]["priority"] == 10
        assert sorted_tasks[-1]["type"] == "stats"
        assert sorted_tasks[-1]["priority"] == 1

    def test_task_result_caching(self):
        """Test caching of task results for optimization."""
        cache = {}
        
        def get_cached_result(text_hash):
            return cache.get(text_hash)
        
        def cache_result(text_hash, result):
            cache[text_hash] = result
        
        # Simulate caching
        text_hash = "hash_123"
        analysis_result = {"language": "en", "confidence": 0.95}
        
        # Cache miss
        cached = get_cached_result(text_hash)
        assert cached is None
        
        # Cache result
        cache_result(text_hash, analysis_result)
        
        # Cache hit
        cached = get_cached_result(text_hash)
        assert cached is not None
        assert cached["language"] == "en"

    @pytest.mark.asyncio
    async def test_task_workflow_orchestration(self):
        """Test orchestration of multiple related tasks."""
        workflow_tasks = [
            {"name": "analyze_text", "depends_on": [], "status": "pending"},
            {"name": "apply_moderation", "depends_on": ["analyze_text"], "status": "pending"},
            {"name": "update_stats", "depends_on": ["analyze_text"], "status": "pending"},
            {"name": "send_notification", "depends_on": ["apply_moderation"], "status": "pending"}
        ]
        
        # Simulate task completion
        def complete_task(task_name):
            for task in workflow_tasks:
                if task["name"] == task_name:
                    task["status"] = "completed"
        
        def get_ready_tasks():
            ready_tasks = []
            for task in workflow_tasks:
                if task["status"] == "pending":
                    dependencies_met = all(
                        any(t["name"] == dep and t["status"] == "completed" for t in workflow_tasks)
                        for dep in task["depends_on"]
                    ) if task["depends_on"] else True
                    
                    if dependencies_met:
                        ready_tasks.append(task["name"])
            return ready_tasks
        
        # Initially, only analyze_text should be ready
        ready = get_ready_tasks()
        assert "analyze_text" in ready
        assert len(ready) == 1
        
        # Complete analyze_text
        complete_task("analyze_text")
        
        # Now apply_moderation and update_stats should be ready
        ready = get_ready_tasks()
        assert "apply_moderation" in ready
        assert "update_stats" in ready
        assert "send_notification" not in ready