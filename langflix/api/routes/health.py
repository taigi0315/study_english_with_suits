"""
Health check routes for LangFlix API.

This module provides health check endpoints for monitoring service status.
"""

from fastapi import APIRouter
from datetime import datetime
from ..models.common import HealthResponse, DetailedHealthResponse

router = APIRouter()

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        service="LangFlix API",
        version="1.0.0"
    )

@router.get("/health/detailed", response_model=DetailedHealthResponse)
async def detailed_health_check():
    """Detailed health check with component status."""
    # TODO: Check database connection
    # TODO: Check storage backends
    # TODO: Check external services
    
    return DetailedHealthResponse(
        status="healthy",
        timestamp=datetime.utcnow().isoformat(),
        components={
            "database": "healthy",
            "storage": "healthy",
            "llm": "healthy"
        }
    )
