"""
Health check endpoints for LangFlix API
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from langflix.api.dependencies import get_db, get_storage
from langflix.storage.base import StorageBackend

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
async def detailed_health_check(
    db: Optional[Session] = Depends(get_db),
    storage: StorageBackend = Depends(get_storage)
) -> Dict[str, Any]:
    """
    Detailed health check endpoint.
    
    Checks the health of all system components including database and storage.
    """
    components = {}
    
    # Check database
    if db is not None:
        try:
            # Simple query to check database connectivity
            db.execute(text("SELECT 1"))
            components["database"] = "connected"
        except Exception as e:
            components["database"] = f"error: {str(e)}"
    else:
        components["database"] = "disabled"
    
    # Check storage
    try:
        # Simple check - try to list root path
        storage.list_files("/", limit=1)
        components["storage"] = "available"
    except Exception as e:
        components["storage"] = f"error: {str(e)}"
    
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "LangFlix API",
        "version": "1.0.0",
        "components": components,
        "tts": "ready"
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
