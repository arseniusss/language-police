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

@app.post("/analyze_message")
async def analyze_message(request: AnalysisRequest):
    try:
        logger.info(f"Received analysis request for text: {request.text[:50]}...")
        
        task = analyze_language.apply_async(
            args=[request.text, request.chat_id, request.message_id, request.user_id],
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
    analyze_language.apply_async(
        args=[text, chat_id, message_id, user_id],
        queue=settings.RABBITMQ_WORKER_QUEUE
    )

async def consume_general_queue_messages():
    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=1)
    queue = await channel.declare_queue(settings.RABBITMQ_GENERAL_QUEUE, durable=True)
    
    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            async with message.process():
                message_data = json.loads(message.body)
                logger.info(f"Received message: {message_data}")
                message_type = message_data.get("result", {}).get("message_type", "")
                
                if message_type == QueueMessageType.TEXT_TO_ANALYZE:
                    logger.info("Handling TEXT_TO_ANALYZE message")
                    await handle_text_to_analyze(message_data.get("result", {}))
                else:
                    logger.warning(f"Unhandled message type: {message_type}")

async def consume_worker_results():
    connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
    channel = await connection.channel()
    await channel.set_qos(prefetch_count=1)
    queue = await channel.declare_queue(settings.RABBITMQ_RESULT_QUEUE, durable=True)
    
    async with queue.iterator() as queue_iter:
        async for message in queue_iter:
            async with message.process():
                result_data = json.loads(message.body)
                logger.info(f"Received result: {result_data}")

@app.on_event("startup")
async def startup_event():
    asyncio.create_task(consume_general_queue_messages())
    asyncio.create_task(consume_worker_results())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.APP_HOST, port=settings.APP_PORT, log_level="info")