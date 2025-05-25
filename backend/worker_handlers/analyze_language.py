import logging
import asyncio
from functools import wraps
from langdetect import detect_langs
from settings import get_settings
from backend.worker_handlers.celery_config import celery_app
from middlewares.rabbitmq.queue_manager import rabbitmq_manager
from middlewares.rabbitmq.mq_enums import WorkerResQueueMessageType

settings = get_settings()
logger = logging.getLogger(__name__)

# Helper function to safely run async code in a sync context
def run_async(async_func):
    @wraps(async_func)
    def wrapper(*args, **kwargs):
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(async_func(*args, **kwargs))
            loop.close()
            return result
        except Exception as e:
            logger.error(f"Error in run_async: {str(e)}")
            raise
    return wrapper

def patched_store_result_sync(queue_name, job_id, result_data):
    """Safely run the async store_result in a sync context"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def _do_store():
            if not rabbitmq_manager.connection or rabbitmq_manager.connection.is_closed:
                await rabbitmq_manager.connect()
            await rabbitmq_manager.store_result(queue_name, job_id, result_data)
        
        # Run the async function in the loop
        result = loop.run_until_complete(_do_store())
        loop.close()
        return result
    except Exception as e:
        logger.error(f"Error in patched_store_result_sync: {str(e)}")
        raise

@celery_app.task(name='backend.worker_handlers.analyze_language.analyze_language')
def analyze_language(text: str, chat_id: str, message_id: str, user_id: int, timestamp: str, name: str, username: str):
    logger.info(f"Analyzing language for message_id: {message_id}, chat_id: {chat_id}, user_id: {user_id}")
    try:
        result = detect_langs(text)
        analysis_result = [{"lang": lang.lang, "prob": lang.prob} for lang in result]
        logger.info(f"Detected languages for message_id {message_id}: {analysis_result}")
        
        result_data = {
            "message_type": WorkerResQueueMessageType.TEXT_ANALYSIS_COMPLETED,
            "text": text,
            "message_id": message_id,
            "chat_id": chat_id,
            "user_id": user_id,
            "timestamp": timestamp,
            "analysis_result": analysis_result,
            "name": name,
            "username": username
        }
        
        try:
            patched_store_result_sync(settings.RABBITMQ_RESULT_QUEUE, chat_id + message_id, result_data)
            logger.info(f"Successfully sent analysis result for message_id {message_id}")
        except Exception as store_error:
            logger.error(f"Failed to store result: {str(store_error)}")
        
        return analysis_result
        
    except Exception as e:
        logger.error(f"Error in analyze_language task for message_id {message_id}: {str(e)}")
        return None