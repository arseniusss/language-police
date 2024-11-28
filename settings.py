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
    # Redis settings
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_QUEUE_KEY: str = "language_analysis_queue"

    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    CELERY_AUTOSCALE_MIN: int = 2
    CELERY_AUTOSCALE_MAX: int = 8
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    return Settings()