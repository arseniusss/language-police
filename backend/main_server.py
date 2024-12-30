from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import logging
from backend.analyze_language import analyze_language
from settings import get_settings
from middlewares.rabbitmq.rabbitmq import rabbitmq_manager, QueueMessageType
import json
import aio_pika
import asyncio
import sys
from middlewares.database.db import database
from middlewares.database.models import ChatMessage, User
from langdetect import detect

settings = get_settings()
app = FastAPI()

# Configure logging to log to the console with UTF-8 encoding
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class AnalysisRequest(BaseModel):
    text: str
    chat_id: str
    message_id: str
    user_id: int
    timestamp: str
    name: str
    username: str
    is_active: bool

@app.post("/analyze_message")
async def analyze_message(request: AnalysisRequest):
    try:
        logger.info(f"Received analysis request for text: {request.text[:50]}...")

        # Check if user exists in the database
        if not await database.user_exists(request.user_id):
            await database.create_user({
                "user_id": request.user_id,
                "name": request.name,
                "username": request.username,
                "is_active": request.is_active
            })

        # Add chat message to the user's chat history
        await database.add_chat_message(
            request.user_id,
            ChatMessage(
                chat_id=request.chat_id,
                message_id=request.message_id,
                content=request.text,
                timestamp=request.timestamp
            )
        )

        # Pass the message to the worker queue
        task = analyze_language.apply_async(
            args=[request.text, request.chat_id, request.message_id, request.user_id, request.timestamp],
            queue=settings.RABBITMQ_WORKER_QUEUE
        )

        logger.info(f"Created task with ID: {task.id}")
        return {"job_id": task.id}
    except Exception as e:
        logger.error(f"Error creating analysis task: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/{job_id}")
async def get_status(job_id: str):
    try:
        logger.info(f"Checking status for job: {job_id}")
        result = await rabbitmq_manager.get_result(settings.RABBITMQ_RESULT_QUEUE, job_id)
        
        if result is None:
            return {"status": "pending"}
        
        logger.info(f"Task {job_id} result: {result}")
        return {"status": "completed", "result": result}
    except Exception as e:
        logger.error(f"Error checking task status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to check task status")

async def handle_text_to_analyze(message_data):
    logger.info(f"Handling TEXT_TO_ANALYZE message:\n{message_data}")
    user_id = message_data.get("user_id", 0)
    chat_id = message_data.get("chat_message", {}).get("chat_id", "")
    message_id = message_data.get("chat_message", {}).get("message_id", "")
    text = message_data.get("chat_message", {}).get("content", "")
    timestamp = message_data.get("chat_message", {}).get("timestamp", "")

    # Pass the message to the worker queue
    analyze_language.apply_async(
        args=[text, chat_id, message_id, user_id, timestamp],
        queue=settings.RABBITMQ_WORKER_QUEUE
    )

async def handle_stats_command(message_data):
    logger.info(f"Handling STATS_COMMAND_TG message:\n{message_data}")
    user_id = message_data.get("user_id", 0)
    chat_id = message_data.get("chat_id", "")
    message_id = message_data.get("message_id", "")

    user = await database.get_user(user_id)
    if not user or not user.chat_history:
        response_text = "No messages found in your history!"
    else:
        analysis_result = []
        for chat_id, messages in user.chat_history.items():
            analysis_result.append(f"\nChat ID: {chat_id}")
            for chat_message in messages:
                try:
                    if chat_message.content:
                        lang = detect(chat_message.content)
                        analysis_result.append(
                            f"Message: {chat_message.content[:30]}...\n"
                            f"Language: {lang}\n"
                        )
                except Exception as e:
                    logging.error(f"Error analyzing message: {e}")
                    continue

        if len(analysis_result) > 1:
            response_text = "Language Analysis:\n\n" + "\n".join(analysis_result)
        else:
            response_text = "No messages could be analyzed!"

    response_data = {
        "message_type": QueueMessageType.STATS_COMMAND_TG,
        "chat_id": chat_id,
        "user_id": user_id,
        "text": response_text,
    }

    rabbitmq_manager.store_result(settings.RABBITMQ_TELEGRAM_QUEUE, str(chat_id) + '.' + str(message_id), response_data)

async def consume_general_queue_messages():
    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=1)
    queue = await channel.declare_queue(settings.RABBITMQ_GENERAL_QUEUE, durable=True)
    
    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            async with message.process():
                message_data = json.loads(message.body).get("result", {})
                logger.info(f"Received message: {message_data}")
                message_type = message_data.get("message_type", "Unknown")
                
                if message_type == QueueMessageType.TEXT_TO_ANALYZE:
                    logger.info("Handling TEXT_TO_ANALYZE message")
                    await handle_text_to_analyze(message_data)
                elif message_type == QueueMessageType.STATS_COMMAND_TG:
                    logger.info("Handling STATS_COMMAND_TG message")
                    await handle_stats_command(message_data)
                else:
                    logger.warning(f"Unhandled message type: {message_type}")
                    

async def handle_text_analysis_complete(message_data):
    logger.info(f"Handling TEXT_ANALYSIS_COMPLETED queue message:\n{message_data}")
    user_id = message_data.get("user_id", 0)
    print("\n\nuser_id", user_id)
    name = message_data.get("name", "")
    username = message_data.get("username", "")
    chat_id = message_data.get("chat_id", "")
    message_id = message_data.get("message_id", "")
    text = message_data.get("text", "")
    timestamp = message_data.get("timestamp", "")
    analysis_result = message_data.get("analysis_result", [])

    user_exits = await database.user_exists(user_id)

    if not user_exits:
        await database.create_user({
            "user_id": user_id,
            "name": name,
            "username": username,
            "is_active": True
            
        })
    await database.add_chat_message(user_id, ChatMessage(chat_id=chat_id, message_id=message_id, content=text, timestamp=timestamp, analysis_result=analysis_result))

async def consume_worker_results():
    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=1)
    queue = await channel.declare_queue(settings.RABBITMQ_RESULT_QUEUE, durable=True)
    
    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            async with message.process():
                message_data = json.loads(message.body).get("result", {})
                logger.info(f"Received result: {message_data}")
                message_type = message_data.get("message_type", "Unknown")
                
                if message_type == QueueMessageType.TEXT_ANALYSIS_COMPLETED:
                    logger.info("Handling TEXT_ANALYSIS_COMPLETED result")
                    await handle_text_analysis_complete(message_data)
                else:
                    logger.warning(f"Unhandled result type: {message_type}")

@app.on_event("startup")
async def startup_event():
    await database.setup()
    asyncio.create_task(consume_general_queue_messages())
    asyncio.create_task(consume_worker_results())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.APP_HOST, port=settings.APP_PORT, log_level="info")