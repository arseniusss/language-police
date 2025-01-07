import json
import logging
from aio_pika import IncomingMessage
from settings import get_settings
from middlewares.rabbitmq.rabbitmq import rabbitmq_manager, QueueMessageType
from backend.queue_handlers.worker_results_queue.text_analysis_complete import handle_text_analysis_compete

settings = get_settings()
logger = logging.getLogger(__name__)

async def handle_worker_result_queue_message(message: IncomingMessage):
    async with message.process():
        message_data = json.loads(message.body).get("result", {})
        logger.info(f"Received result: {message_data}")
        message_type = message_data.get("message_type", "Unknown")
        
        if message_type == QueueMessageType.TEXT_ANALYSIS_COMPLETED:
            logger.info("Handling TEXT_ANALYSIS_COMPLETED result")
            await handle_text_analysis_compete(message_data)
        else:
            logger.warning(f"Unhandled result type: {message_type}")

async def consume_worker_results_queue_messages():
    await rabbitmq_manager.connect()
    
    async def on_message(message: IncomingMessage):
        await handle_worker_result_queue_message(message)
    
    await rabbitmq_manager.worker_results_queue.consume(on_message)
    logger.info("Started consuming messages from worker_results_queue")