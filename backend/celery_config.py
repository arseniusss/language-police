from celery import Celery
from settings import get_settings

settings = get_settings()

celery_app = Celery(
    "backend",  # Changed to match package name
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=['backend.analyze_language']  # Explicitly include the task module
)

celery_app.conf.update(
    broker_url=settings.CELERY_BROKER_URL,
    result_backend=settings.CELERY_RESULT_BACKEND,
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    worker_prefetch_multiplier=1,
    task_routes={
        'analyze_language': {  # Simplified task name
            'queue': settings.REDIS_QUEUE_KEY
        }
    }
)