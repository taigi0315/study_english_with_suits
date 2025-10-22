"""
Common models for LangFlix API
"""

from pydantic import BaseModel, Field
from typing import Dict, Any, Optional
from datetime import datetime

class HealthResponse(BaseModel):
    """Basic health check response."""
    
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(..., description="Response timestamp")
    service: str = Field(..., description="Service name")

class DetailedHealthResponse(BaseModel):
    """Detailed health check response."""
    
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(..., description="Response timestamp")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    components: Dict[str, str] = Field(..., description="Component health status")

class ErrorResponse(BaseModel):
    """Error response model."""
    
    error: str = Field(..., description="Error message")
    status_code: int = Field(..., description="HTTP status code")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
