"""
Common models for LangFlix API.

This module defines shared Pydantic models used across the API.
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any

class HealthResponse(BaseModel):
    """Response model for health check."""
    status: str = Field(..., description="Service status")
    timestamp: str = Field(..., description="Current timestamp")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")

class DetailedHealthResponse(BaseModel):
    """Response model for detailed health check."""
    status: str = Field(..., description="Overall service status")
    timestamp: str = Field(..., description="Current timestamp")
    components: Dict[str, str] = Field(..., description="Component status")
