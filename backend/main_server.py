import logging
import asyncio
import sys
from fastapi import FastAPI

from middlewares.database.db import database
from settings import get_settings
from backend.queue_handlers.general_queue.main_handler import consume_general_queue_messages
from backend.queue_handlers.worker_results_queue.main_handler import consume_worker_results_queue_messages

settings = get_settings()
app = FastAPI()

# Configure logging to log to the console with UTF-8 encoding
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    await database.setup()
    asyncio.create_task(consume_general_queue_messages())
    asyncio.create_task(consume_worker_results_queue_messages())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.APP_HOST, port=settings.APP_PORT, log_level="info")