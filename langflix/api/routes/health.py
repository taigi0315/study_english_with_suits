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
