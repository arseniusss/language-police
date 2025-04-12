import aio_pika
import json
import logging
import asyncio
from enum import Enum
from settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

class RabbitMQMiddleware:
    def __init__(self):
        self.connection = None
        self.channel = None
        self.telegram_queue = None

    async def connect(self):
        if self.connection is None or self.connection.is_closed:
            self.connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
        if self.channel is None or self.channel.is_closed:
            self.channel = await self.connection.channel()
            await self.channel.set_qos(prefetch_count=1)
            await self.declare_queues()

    async def declare_queues(self):
        self.backend_general_queue = await self.channel.declare_queue(settings.RABBITMQ_GENERAL_QUEUE, durable=True)
        await self.channel.declare_queue(settings.RABBITMQ_WORKER_QUEUE, durable=True)
        self.telegram_queue = await self.channel.declare_queue(settings.RABBITMQ_TELEGRAM_QUEUE, durable=True)
        self.worker_results_queue = await self.channel.declare_queue(settings.RABBITMQ_RESULT_QUEUE, durable=True)

    async def store_result(self, queue: str, job_id: str, result: dict):
        logger.info(f"Storing result for job_id {job_id} in queue {queue} (sync)")
        connection = await aio_pika.connect_robust(settings.RABBITMQ_URL)
        channel = await connection.channel()
        await channel.default_exchange.publish(
            aio_pika.Message(
                body=json.dumps({"job_id": job_id, "result": result}).encode(),
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            ),
            routing_key=queue
        )
        await connection.close()

    #FIXME: This is a workaround to use async code in sync code
    def store_result_sync(self, queue_name, message_id, result_data):
        """
        Synchronous version of store_result for use in Celery tasks
        """
        if not self.connection or self.connection.is_closed:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.connect())
            finally:
                loop.close()
        
        # Create a new event loop for this operation
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            return loop.run_until_complete(self._store_result(queue_name, message_id, result_data))
        finally:
            loop.close()
    
    async def get_result(self, queue: str, job_id: str):
        if self.channel is None or self.channel.is_closed:
            await self.connect()
        async with self.channel.iterator(queue) as queue_iter:
            async for message in queue_iter:
                async with message.process():
                    message_data = json.loads(message.body)
                    if message_data["job_id"] == job_id:
                        logger.info(f"Retrieved result for job_id {job_id} from queue {queue}")
                        return message_data["result"]
        return None

rabbitmq_manager = RabbitMQMiddleware()