# settings.py
from pydantic_settings import BaseSettings
from typing import Optional
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
    
    # Logging
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    return Settings()