"""
Health check endpoints for LangFlix API
"""

from fastapi import APIRouter
from datetime import datetime, timezone
from typing import Dict, Any

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
    """Detailed health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "LangFlix API",
        "version": "1.0.0",
        "components": {
            "database": "connected",  # TODO: Implement actual health checks
            "storage": "available",
            "tts": "ready"
        }
    }

@router.get("/health/redis")
async def redis_health_check() -> Dict[str, Any]:
    """Redis health check endpoint."""
    try:
        from langflix.core.redis_client import get_redis_job_manager
        redis_manager = get_redis_job_manager()
        health_status = redis_manager.health_check()
        health_status["timestamp"] = datetime.now(timezone.utc).isoformat()
        return health_status
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

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
