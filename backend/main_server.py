import logging
import asyncio
from fastapi import FastAPI
from middlewares.database.db import database
from settings import get_settings
from backend.queue_handlers.general_queue.main_handler import consume_general_queue_messages
from backend.queue_handlers.worker_results_queue.main_handler import consume_worker_results_queue_messages
from backend.utils.logging_config import logger

settings = get_settings()
logger = logger.getChild('main_server')

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    await database.setup()
    asyncio.create_task(consume_general_queue_messages())
    asyncio.create_task(consume_worker_results_queue_messages())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.APP_HOST, port=settings.APP_PORT, log_level="info")