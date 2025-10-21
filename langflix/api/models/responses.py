"""
Response models for LangFlix API
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class JobStatusResponse(BaseModel):
    """Response model for job status."""
    
    job_id: str = Field(..., description="Unique job identifier")
    status: str = Field(..., description="Current job status")
    created_at: datetime = Field(..., description="Job creation timestamp")
    progress: int = Field(0, description="Processing progress percentage")
    error: Optional[str] = Field(None, description="Error message if failed")

class ExpressionResponse(BaseModel):
    """Response model for a single expression."""
    
    expression: str = Field(..., description="The English expression")
    translation: str = Field(..., description="Translation of the expression")
    context: str = Field(..., description="Context where the expression was used")
    similar_expressions: List[str] = Field(..., description="Similar expressions")

class JobExpressionsResponse(BaseModel):
    """Response model for job expressions."""
    
    job_id: str = Field(..., description="Job identifier")
    status: str = Field(..., description="Job status")
    expressions: List[ExpressionResponse] = Field(..., description="List of extracted expressions")
