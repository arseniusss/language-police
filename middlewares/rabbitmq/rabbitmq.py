import pika
import json
import logging
from enum import Enum
from settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

class RabbitMQMiddleware:
    def __init__(self):
        self.connection = None
        self.channel = None
        self.connect()

    def connect(self):
        if self.connection is None or self.connection.is_closed:
            self.connection = pika.BlockingConnection(pika.URLParameters(settings.RABBITMQ_URL))
        if self.channel is None or self.channel.is_closed:
            self.channel = self.connection.channel()
            self.channel.queue_declare(queue=settings.RABBITMQ_GENERAL_QUEUE, durable=True)
            self.channel.queue_declare(queue=settings.RABBITMQ_WORKER_QUEUE, durable=True)
            self.channel.queue_declare(queue=settings.RABBITMQ_TELEGRAM_QUEUE, durable=True)
            self.channel.queue_declare(queue=settings.RABBITMQ_RESULT_QUEUE, durable=True)

    def store_result(self, queue: str, job_id: str, result: dict):
        logger.info(f"Storing result for job_id {job_id} in queue {queue}")
        self.channel.basic_publish(
            exchange='',
            routing_key=queue,
            body=json.dumps({"job_id": job_id, "result": result}),
            properties=pika.BasicProperties(delivery_mode=2)  # make message persistent
        )

    def get_result(self, queue: str, job_id: str):
        method_frame, header_frame, body = self.channel.basic_get(queue=queue)
        if method_frame:
            self.channel.basic_ack(method_frame.delivery_tag)
            message = json.loads(body)
            if message["job_id"] == job_id:
                logger.info(f"Retrieved result for job_id {job_id} from queue {queue}")
                return message["result"]
        return None

class QueueMessageType(str, Enum):
    TEXT_TO_ANALYZE = "text_to_analyze"
    TEXT_ANALYSIS_COMPLETED = "text_analysis_completed"
    STATS_COMMAND_TG = "stats_command_tg"

rabbitmq_manager = RabbitMQMiddleware()