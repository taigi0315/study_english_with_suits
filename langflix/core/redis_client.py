"""
Redis client for shared job state management in Phase 7 architecture.
"""

import redis
import json
import logging
import time
from typing import Dict, Any, Optional, List
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
                elif isinstance(value, (list, dict)):
                    # Serialize lists and dicts as JSON for proper storage/retrieval
                    string_updates[key] = json.dumps(value, default=str)
                elif value is None:
                    string_updates[key] = "None"
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
            
            # Deserialize JSON fields (expressions, educational_videos, short_videos)
            json_fields = ['expressions', 'educational_videos', 'short_videos']
            for field in json_fields:
                if field in job_data:
                    try:
                        # Try to parse as JSON
                        if job_data[field] and job_data[field] != 'None' and job_data[field] != '[]':
                            job_data[field] = json.loads(job_data[field])
                        else:
                            job_data[field] = []
                    except (json.JSONDecodeError, TypeError):
                        # If parsing fails, try to handle legacy string format
                        if job_data[field] == '[]' or job_data[field] == 'None':
                            job_data[field] = []
                        # Otherwise keep as string (for backwards compatibility)
                        pass
            
            # Handle final_video field (might be "None" string or JSON)
            if 'final_video' in job_data:
                if job_data['final_video'] == 'None' or job_data['final_video'] == '':
                    job_data['final_video'] = None
                else:
                    try:
                        # Try to parse as JSON in case it's a dict
                        job_data['final_video'] = json.loads(job_data['final_video'])
                    except (json.JSONDecodeError, TypeError):
                        # Keep as string if not valid JSON
                        pass
            
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
            cleaned_count = 0
            
            for job_id in job_ids:
                # Check if job data exists
                if not self.redis_client.exists(f"job:{job_id}"):
                    # Remove from active jobs set if data doesn't exist
                    self.redis_client.srem("jobs:active", job_id)
                    cleaned_count += 1
                    logger.info(f"Cleaned up orphaned job reference: {job_id}")
            
            logger.info(f"Cleaned up {cleaned_count} expired/orphaned jobs")
            return cleaned_count
        except Exception as e:
            logger.error(f"❌ Failed to cleanup expired jobs: {e}")
            return 0
    
    def cleanup_stale_jobs(self, max_age_hours: int = 24) -> int:
        """Clean up stale jobs older than max_age_hours."""
        try:
            from datetime import datetime, timezone, timedelta
            
            job_ids = self.redis_client.smembers("jobs:active")
            cleaned_count = 0
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
            
            for job_id in job_ids:
                job_data = self.get_job(job_id)
                if job_data and 'created_at' in job_data:
                    try:
                        created_at = datetime.fromisoformat(job_data['created_at'].replace('Z', '+00:00'))
                        if created_at < cutoff_time:
                            self.delete_job(job_id)
                            cleaned_count += 1
                            logger.info(f"Cleaned up stale job: {job_id} (created: {created_at})")
                    except ValueError as e:
                        logger.warning(f"Invalid created_at format for job {job_id}: {e}")
            
            logger.info(f"Cleaned up {cleaned_count} stale jobs")
            return cleaned_count
        except Exception as e:
            logger.error(f"❌ Failed to cleanup stale jobs: {e}")
            return 0
    
    def health_check(self) -> Dict[str, Any]:
        """Check Redis connection health and return status."""
        try:
            # Test basic connectivity
            start_time = time.time()
            self.redis_client.ping()
            ping_time = (time.time() - start_time) * 1000  # Convert to milliseconds
            
            # Get Redis info
            info = self.redis_client.info()
            
            # Count active jobs
            active_jobs_count = self.redis_client.scard("jobs:active")
            
            # Get memory usage
            memory_used = info.get('used_memory_human', 'unknown')
            
            return {
                "status": "healthy",
                "ping_time_ms": round(ping_time, 2),
                "active_jobs": active_jobs_count,
                "memory_used": memory_used,
                "redis_version": info.get('redis_version', 'unknown'),
                "connected_clients": info.get('connected_clients', 0),
                "uptime_seconds": info.get('uptime_in_seconds', 0)
            }
        except Exception as e:
            logger.error(f"❌ Redis health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "ping_time_ms": None,
                "active_jobs": None
            }
    
    def get_video_cache(self) -> Optional[List[Dict[str, Any]]]:
        """Get cached video metadata."""
        try:
            cached_data = self.redis_client.get("langflix:video_cache:all")
            if cached_data:
                import json
                logger.debug("✅ Video cache hit")
                return json.loads(cached_data)
            logger.debug("❌ Video cache miss")
            return None
        except Exception as e:
            logger.error(f"❌ Failed to get video cache: {e}")
            return None
    
    def set_video_cache(self, videos: List[Dict[str, Any]], ttl: int = 300) -> bool:
        """Set video metadata cache with TTL."""
        try:
            import json
            self.redis_client.setex(
                "langflix:video_cache:all", 
                ttl, 
                json.dumps(videos, default=str)
            )
            logger.info(f"✅ Cached {len(videos)} videos for {ttl} seconds")
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
