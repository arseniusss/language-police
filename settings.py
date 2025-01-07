from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Bot settings
    TELEGRAM_BOT_TOKEN: str
    
    # Database settings
    MONGODB_DATABASE: str
    MONGODB_CONNECTION_URI: str
    
    # Webhook settings
    WEBHOOK_URL: str
    WEBHOOK_PATH: str = "/webhook"
    
    # Server settings
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    
    BACKEND_URL: str  = "http://localhost:8001"
    
    # RabbitMQ settings
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"
    RABBITMQ_GENERAL_QUEUE: str = "general_queue"
    RABBITMQ_WORKER_QUEUE: str = "worker_queue"
    RABBITMQ_TELEGRAM_QUEUE: str = "telegram_queue"
    RABBITMQ_RESULT_QUEUE: str = "result_queue"

    # Celery settings
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str
    CELERY_AUTOSCALE_MIN: int = 2
    CELERY_AUTOSCALE_MAX: int = 8
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        
#TODO: пофіксити, щоб не треба було викликати import settings; settings = get_settings() в кожному файлі
@lru_cache()
def get_settings() -> Settings:
    return Settings()