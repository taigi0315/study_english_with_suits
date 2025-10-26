"""
Redis client for shared job state management in Phase 7 architecture.
"""

import redis
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import os

logger = logging.getLogger(__name__)

class RedisJobManager:
    """Redis-based job state management for Flask-FastAPI communication."""
    
    def __init__(self, redis_url: str = None):
        """Initialize Redis connection."""
        if redis_url is None:
            redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        
        try:
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            # Test connection
            self.redis_client.ping()
            logger.info(f"✅ Redis connected: {redis_url}")
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            raise
    
    def create_job(self, job_id: str, job_data: Dict[str, Any]) -> bool:
        """Create a new job in Redis."""
        try:
            job_data['created_at'] = datetime.now(timezone.utc).isoformat()
            job_data['updated_at'] = datetime.now(timezone.utc).isoformat()
            
            # Store job data as JSON
            self.redis_client.hset(f"job:{job_id}", mapping=job_data)
            
            # Set expiration (24 hours)
            self.redis_client.expire(f"job:{job_id}", 86400)
            
            # Add to job list for tracking
            self.redis_client.sadd("jobs:active", job_id)
            
            logger.info(f"✅ Job {job_id} created in Redis")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to create job {job_id}: {e}")
            return False
    
    def update_job(self, job_id: str, updates: Dict[str, Any]) -> bool:
        """Update job data in Redis."""
        try:
            updates['updated_at'] = datetime.now(timezone.utc).isoformat()
            
            # Convert all values to strings for Redis storage
            string_updates = {}
            for key, value in updates.items():
                if isinstance(value, (int, float)):
                    string_updates[key] = str(value)
                elif isinstance(value, bool):
                    string_updates[key] = str(value).lower()
                elif isinstance(value, datetime):
                    string_updates[key] = value.isoformat()
                else:
                    string_updates[key] = str(value)
            
            # Update job data
            self.redis_client.hset(f"job:{job_id}", mapping=string_updates)
            
            logger.debug(f"✅ Job {job_id} updated: {string_updates}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to update job {job_id}: {e}")
            return False
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get job data from Redis."""
        try:
            job_data = self.redis_client.hgetall(f"job:{job_id}")
            if not job_data:
                return None
            
            # Convert string values back to appropriate types
            if 'progress' in job_data:
                job_data['progress'] = int(job_data['progress'])
            if 'max_expressions' in job_data:
                job_data['max_expressions'] = int(job_data['max_expressions'])
            if 'test_mode' in job_data:
                job_data['test_mode'] = job_data['test_mode'].lower() == 'true'
            if 'no_shorts' in job_data:
                job_data['no_shorts'] = job_data['no_shorts'].lower() == 'true'
            
            return job_data
        except Exception as e:
            logger.error(f"❌ Failed to get job {job_id}: {e}")
            return None
    
    def get_all_jobs(self) -> Dict[str, Dict[str, Any]]:
        """Get all active jobs."""
        try:
            job_ids = self.redis_client.smembers("jobs:active")
            jobs = {}
            
            for job_id in job_ids:
                job_data = self.get_job(job_id)
                if job_data:
                    jobs[job_id] = job_data
            
            return jobs
        except Exception as e:
            logger.error(f"❌ Failed to get all jobs: {e}")
            return {}
    
    def delete_job(self, job_id: str) -> bool:
        """Delete job from Redis."""
        try:
            # Remove from active jobs set
            self.redis_client.srem("jobs:active", job_id)
            
            # Delete job data
            self.redis_client.delete(f"job:{job_id}")
            
            logger.info(f"✅ Job {job_id} deleted from Redis")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to delete job {job_id}: {e}")
            return False
    
    def cleanup_expired_jobs(self) -> int:
        """Clean up expired jobs."""
        try:
            job_ids = self.redis_client.smembers("jobs:active")
            cleaned = 0
            
            for job_id in job_ids:
                if not self.redis_client.exists(f"job:{job_id}"):
                    self.redis_client.srem("jobs:active", job_id)
                    cleaned += 1
            
            if cleaned > 0:
                logger.info(f"✅ Cleaned up {cleaned} expired jobs")
            
            return cleaned
        except Exception as e:
            logger.error(f"❌ Failed to cleanup expired jobs: {e}")
            return 0
    
    # Video Cache Methods
    
    def get_video_cache(self) -> Optional[list]:
        """Get cached video list from Redis."""
        try:
            cached_data = self.redis_client.get("langflix:video_cache:all")
            if cached_data:
                logger.debug("✅ Video cache hit")
                return json.loads(cached_data)
            logger.debug("❌ Video cache miss")
            return None
        except Exception as e:
            logger.error(f"❌ Failed to get video cache: {e}")
            return None
    
    def set_video_cache(self, videos: list, ttl: int = 300) -> bool:
        """
        Cache video list in Redis.
        
        Args:
            videos: List of video dictionaries to cache
            ttl: Time-to-live in seconds (default: 300 = 5 minutes)
        """
        try:
            self.redis_client.setex(
                "langflix:video_cache:all",
                ttl,
                json.dumps(videos, default=str)  # default=str handles datetime objects
            )
            logger.info(f"✅ Video cache set with {len(videos)} videos (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to set video cache: {e}")
            return False
    
    def invalidate_video_cache(self) -> bool:
        """Invalidate (delete) video cache."""
        try:
            self.redis_client.delete("langflix:video_cache:all")
            logger.info("✅ Video cache invalidated")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to invalidate video cache: {e}")
            return False

# Global Redis job manager instance
_redis_job_manager: Optional[RedisJobManager] = None

def get_redis_job_manager() -> RedisJobManager:
    """Get global Redis job manager instance."""
    global _redis_job_manager
    if _redis_job_manager is None:
        _redis_job_manager = RedisJobManager()
    return _redis_job_manager

def init_redis_job_manager(redis_url: str = None) -> RedisJobManager:
    """Initialize Redis job manager with custom URL."""
    global _redis_job_manager
    _redis_job_manager = RedisJobManager(redis_url)
    return _redis_job_manager
