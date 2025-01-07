import logging
from langdetect import detect_langs
from settings import get_settings
from backend.worker_handlers.celery_config import celery_app
from middlewares.rabbitmq.queue_manager import rabbitmq_manager
from middlewares.rabbitmq.mq_enums import WorkerResQueueMessageType

settings = get_settings()
logger = logging.getLogger(__name__)

@celery_app.task(name='backend.worker_handlers.analyze_language.analyze_language')
def analyze_language(text: str, chat_id: str, message_id: str, user_id: int, timestamp: str):
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
            "analysis_result": analysis_result
        }
        
        rabbitmq_manager.store_result_sync(settings.RABBITMQ_RESULT_QUEUE, chat_id + message_id, result_data)
        return analysis_result
        
    except Exception as e:
        logger.error(f"Error in analyze_language task for message_id {message_id}: {str(e)}")