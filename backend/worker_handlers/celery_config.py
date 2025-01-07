from celery import Celery
from settings import get_settings

settings = get_settings()

celery_app = Celery(
    "backend.worker_handlers",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=['backend.worker_handlers.analyze_language']
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
        'backend.worker_handlers_analyze_language.analyze_language': {
            'queue': settings.RABBITMQ_WORKER_QUEUE
        }
    }
)