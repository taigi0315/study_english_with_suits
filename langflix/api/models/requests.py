"""
Request models for LangFlix API
"""

from pydantic import BaseModel, Field
from typing import Optional

class JobCreateRequest(BaseModel):
    """Request model for creating a new job."""
    
    language_code: str = Field(..., description="Language code for processing")
    show_name: str = Field(..., description="Name of the show")
    episode_name: str = Field(..., description="Name of the episode")
    max_expressions: int = Field(10, description="Maximum number of expressions to extract")
    language_level: str = Field("intermediate", description="Language proficiency level")
    test_mode: bool = Field(False, description="Enable test mode for faster processing")
    no_shorts: bool = Field(False, description="Skip short video generation")

class FileUploadRequest(BaseModel):
    """Request model for file upload."""
    
    filename: str = Field(..., description="Name of the uploaded file")
    content_type: str = Field(..., description="MIME type of the file")
    size: int = Field(..., description="Size of the file in bytes")
