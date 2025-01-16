import json
import logging
from aio_pika import IncomingMessage
from settings import get_settings
from middlewares.rabbitmq.queue_manager import rabbitmq_manager
from middlewares.rabbitmq.mq_enums import GeneralBackendQueueMessageType
from backend.queue_handlers.general_queue.analyze_text import handle_text_to_analyze
from backend.queue_handlers.general_queue.stats_command import handle_stats_command
from backend.queue_handlers.general_queue.my_chat_stats_command import handle_my_chat_stats_command
from backend.queue_handlers.general_queue.my_global_stats_command import handle_my_global_stats_command


settings = get_settings()
logger = logging.getLogger(__name__)

async def handle_general_queue_message(message: IncomingMessage):
    async with message.process():
        message_data = json.loads(message.body).get("result", {})
        logger.info(f"Received message: {message_data}")
        message_type = message_data.get("message_type", "Unknown")
        
        match message_type:
            case GeneralBackendQueueMessageType.TEXT_TO_ANALYZE:
                logger.info("Handling TEXT_TO_ANALYZE message")
                #TODO: ось тут розпарсити message_data і викликати функцію з необхідними параметрами
                await handle_text_to_analyze(message_data)
            # TODO: теж у workers
            case GeneralBackendQueueMessageType.STATS_COMMAND_TG:
                logger.info("Handling STATS_COMMAND_TG message")
                await handle_stats_command(message_data)
            case GeneralBackendQueueMessageType.MY_CHAT_STATS_COMMAND_TG:
                logger.info("Handling MY_CHAT_STATS_COMMAND_TG message")
                await handle_my_chat_stats_command(message_data)
            case GeneralBackendQueueMessageType.MY_GLOBAL_STATS_COMMAND_TG:
                logger.info("Handling MY_GLOBAL_STATS_COMMAND_TG message")
                await handle_my_global_stats_command(message_data)
            case _:
                logger.warning(f"Unhandled message type: {message_type}")

async def consume_general_queue_messages():
    await rabbitmq_manager.connect()
    
    async def on_message(message: IncomingMessage):
        await handle_general_queue_message(message)
    
    await rabbitmq_manager.backend_general_queue.consume(on_message)
    logger.info("Started consuming messages from main_queue")