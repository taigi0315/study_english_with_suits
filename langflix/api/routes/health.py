"""
Health check endpoints for LangFlix API
"""

from fastapi import APIRouter
from datetime import datetime, timezone
from typing import Dict, Any

from langflix.monitoring.health_checker import SystemHealthChecker

router = APIRouter()

@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "LangFlix API"
    }

@router.get("/health/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """
    Detailed health check endpoint with actual component checks.
    
    Checks the health of all system components including database, storage, TTS, and Redis.
    """
    checker = SystemHealthChecker()
    health = checker.get_overall_health()
    
    return {
        "status": health["status"],
        "timestamp": health["timestamp"],
        "service": "LangFlix API",
        "version": "1.0.0",
        "components": health["components"]
    }

@router.get("/health/database")
async def database_health_check() -> Dict[str, Any]:
    """Database health check endpoint."""
    checker = SystemHealthChecker()
    return checker.check_database()

@router.get("/health/storage")
async def storage_health_check() -> Dict[str, Any]:
    """Storage health check endpoint."""
    checker = SystemHealthChecker()
    return checker.check_storage()

@router.get("/health/tts")
async def tts_health_check() -> Dict[str, Any]:
    """TTS service health check endpoint."""
    checker = SystemHealthChecker()
    return checker.check_tts()

@router.get("/health/redis")
async def redis_health_check() -> Dict[str, Any]:
    """Redis health check endpoint."""
    checker = SystemHealthChecker()
    result = checker.check_redis()
    # Ensure timestamp is present for consistency
    if "timestamp" not in result:
        result["timestamp"] = datetime.now(timezone.utc).isoformat()
    return result

@router.post("/health/redis/cleanup")
async def redis_cleanup() -> Dict[str, Any]:
    """Clean up expired and stale Redis jobs."""
    try:
        from langflix.core.redis_client import get_redis_job_manager
        redis_manager = get_redis_job_manager()
        
        expired_count = redis_manager.cleanup_expired_jobs()
        stale_count = redis_manager.cleanup_stale_jobs()
        
        return {
            "status": "success",
            "expired_jobs_cleaned": expired_count,
            "stale_jobs_cleaned": stale_count,
            "total_cleaned": expired_count + stale_count,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
