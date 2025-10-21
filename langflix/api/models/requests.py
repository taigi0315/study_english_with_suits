"""
Request models for LangFlix API.

This module defines Pydantic models for API request validation.
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal
from fastapi import UploadFile

class JobCreateRequest(BaseModel):
    """Request model for creating a new processing job."""
    language_code: str = Field(..., description="Language code (e.g., 'en', 'ko')")
    show_name: str = Field(..., description="Name of the TV show")
    episode_name: str = Field(..., description="Name of the episode")
    max_expressions: Optional[int] = Field(10, description="Maximum number of expressions to extract")
    language_level: Optional[Literal["beginner", "intermediate", "advanced", "mixed"]] = Field(
        "intermediate", description="Target language proficiency level"
    )
    test_mode: bool = Field(False, description="Enable test mode (process only first chunk)")
    no_shorts: bool = Field(False, description="Skip short video generation")

class FileUploadRequest(BaseModel):
    """Request model for file uploads."""
    video_file: UploadFile
    subtitle_file: UploadFile
    job_config: JobCreateRequest
