"""
Response models for LangFlix API.

This module defines Pydantic models for API response validation.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime

class JobStatusResponse(BaseModel):
    """Response model for job status."""
    job_id: str = Field(..., description="Unique job identifier")
    status: Literal["PENDING", "PROCESSING", "COMPLETED", "FAILED"] = Field(
        ..., description="Current job status"
    )
    progress: int = Field(..., description="Progress percentage (0-100)")
    created_at: datetime = Field(..., description="Job creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Processing start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Processing completion timestamp")
    error_message: Optional[str] = Field(None, description="Error message if failed")

class ExpressionResponse(BaseModel):
    """Response model for individual expressions."""
    id: str = Field(..., description="Expression identifier")
    expression: str = Field(..., description="The expression text")
    translation: str = Field(..., description="Translation of the expression")
    dialogue: str = Field(..., description="Full dialogue containing the expression")
    dialogue_translation: str = Field(..., description="Translation of the dialogue")
    similar_expressions: List[str] = Field(..., description="List of similar expressions")
    context_start_time: str = Field(..., description="Start time in subtitle format")
    context_end_time: str = Field(..., description="End time in subtitle format")
    scene_type: str = Field(..., description="Type of scene (e.g., 'dialogue', 'action')")

class JobExpressionsResponse(BaseModel):
    """Response model for job expressions."""
    job_id: str = Field(..., description="Job identifier")
    expressions: List[ExpressionResponse] = Field(..., description="List of expressions")
    total: int = Field(..., description="Total number of expressions")

class ErrorResponse(BaseModel):
    """Response model for errors."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[dict] = Field(None, description="Additional error details")
