from langdetect import detect_langs
from backend.celery_config import celery_app
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from middlewares.database.models import User, ChatMessage
from settings import get_settings
import asyncio

settings = get_settings()
logger = logging.getLogger(__name__)

def run_async(coro):
    """Helper function to run async code in sync context"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()

@celery_app.task(name='analyze_language')
def analyze_language(text: str, chat_id: str, message_id: str, user_id: int):
    try:
        # Initialize MongoDB connection
        client = AsyncIOMotorClient(settings.MONGODB_CONNECTION_URI)
        db = client[settings.MONGODB_DATABASE]
        
        async def init_and_update():
            # Initialize Beanie
            await init_beanie(database=db, document_models=[User])
            
            # Find user
            user = await User.find_one({"user_id": user_id})
            if not user:
                logger.error(f"User {user_id} not found")
                return None
                
            # Detect languages
            result = detect_langs(text)
            analysis_result = [{"lang": lang.lang, "prob": lang.prob} for lang in result]
            logger.info(f"Detected languages: {analysis_result}")
            
            # Update message
            if chat_id in user.chat_history:
                for message in user.chat_history[chat_id]:
                    if message.message_id == message_id:
                        message.analysis_result = analysis_result
                        await user.save()
                        logger.info(f"Updated analysis result for message {message_id}")
                        break
            
            return analysis_result
            
        return run_async(init_and_update())
        
    except Exception as e:
        logger.error(f"Error in analyze_language task: {str(e)}")
        raise
    finally:
        client.close()