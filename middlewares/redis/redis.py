from redis import Redis
from settings import get_settings
import json

settings = get_settings()

class RedisMiddleware:
    def __init__(self):
        self.redis = Redis.from_url(settings.REDIS_URL)
        
    def store_result(self, job_id: str, result: dict):
        self.redis.set(f"analysis:{job_id}", json.dumps(result))
        
    def get_result(self, job_id: str):
        result = self.redis.get(f"analysis:{job_id}")
        if result:
            return json.loads(result)
        return None

redis = RedisMiddleware()