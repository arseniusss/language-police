import json
import logging
from aio_pika import IncomingMessage
from settings import get_settings
from middlewares.rabbitmq.rabbitmq import rabbitmq_manager, QueueMessageType
from backend.queue_handlers.general_queue.analyze_text import handle_text_to_analyze
from backend.queue_handlers.general_queue.stats_command import handle_stats_command

settings = get_settings()
logger = logging.getLogger(__name__)

async def handle_general_queue_message(message: IncomingMessage):
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

async def consume_general_queue_messages():
    await rabbitmq_manager.connect()
    
    async def on_message(message: IncomingMessage):
        await handle_general_queue_message(message)
    
    await rabbitmq_manager.backend_general_queue.consume(on_message)
    logger.info("Started consuming messages from main_queue")