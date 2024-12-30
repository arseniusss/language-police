from langdetect import detect_langs
from backend.celery_config import celery_app
import logging
from settings import get_settings
from middlewares.rabbitmq.rabbitmq import rabbitmq_manager

settings = get_settings()
logger = logging.getLogger(__name__)

@celery_app.task(name='backend.analyze_language.analyze_language')
def analyze_language(text: str, chat_id: str, message_id: str, user_id: int):
    logger.info(f"Analyzing language for message_id: {message_id}, chat_id: {chat_id}, user_id: {user_id}")
    try:
        result = detect_langs(text)
        analysis_result = [{"lang": lang.lang, "prob": lang.prob} for lang in result]
        logger.info(f"Detected languages for message_id {message_id}: {analysis_result}")
        
        rabbitmq_manager.store_result(settings.RABBITMQ_RESULT_QUEUE, message_id, analysis_result)
        return analysis_result
        
    except Exception as e:
        logger.error(f"Error in analyze_language task for message_id {message_id}: {str(e)}")
        raise