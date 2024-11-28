from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from celery.result import AsyncResult
from backend.celery_config import celery_app
from backend.analyze_language import analyze_language
from settings import get_settings
import logging

settings = get_settings()
app = FastAPI()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AnalysisRequest(BaseModel):
    text: str
    chat_id: str
    message_id: str
    user_id: int

@app.post("/analyze_message")
async def analyze_message(request: AnalysisRequest):
    try:
        logger.info(f"Received analysis request for text: {request.text[:50]}...")
        
        task = analyze_language.apply_async(
            args=[request.text, request.chat_id, request.message_id, request.user_id],
            queue=settings.REDIS_QUEUE_KEY
        )
        
        logger.info(f"Created task with ID: {task.id}")
        return {"job_id": task.id}
    except Exception as e:
        logger.error(f"Error creating analysis task: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/{job_id}")
async def get_status(job_id: str):
    try:
        logger.info(f"Checking status for job: {job_id}")
        task_result = AsyncResult(job_id, app=celery_app)
        
        if task_result.state == "PENDING":
            return {"status": "pending"}
        elif task_result.state == "FAILURE":
            logger.error(f"Task {job_id} failed: {task_result.info}")
            raise HTTPException(status_code=500, detail=str(task_result.info))
        
        logger.info(f"Task {job_id} status: {task_result.state}, result: {task_result.result}")
        return {"status": task_result.state, "result": task_result.result}
    except Exception as e:
        logger.error(f"Error checking task status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to check task status")