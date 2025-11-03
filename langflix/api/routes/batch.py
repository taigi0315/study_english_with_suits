"""
Batch processing endpoints for LangFlix API
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import logging

from langflix.services.batch_queue_service import BatchQueueService

logger = logging.getLogger(__name__)

router = APIRouter()


class VideoItem(BaseModel):
    """Video item in batch request"""
    video_path: str
    subtitle_path: Optional[str] = ""
    episode_name: Optional[str] = None
    show_name: Optional[str] = "Suits"


class BatchCreateRequest(BaseModel):
    """Request model for batch creation"""
    videos: List[VideoItem] = Field(..., min_items=1)
    language_code: str
    language_level: str = "intermediate"
    test_mode: bool = False
    max_expressions: int = 50
    no_shorts: bool = False
    output_dir: str = "output"


@router.post("/batch")
async def create_batch(request: BatchCreateRequest) -> Dict[str, Any]:
    """
    Create a batch of video processing jobs.
    
    Request body:
    {
        "videos": [
            {
                "video_path": "/path/to/video.mp4",
                "subtitle_path": "/path/to/subtitle.srt",
                "episode_name": "Episode 1",
                "show_name": "Suits"  # optional
            },
            ...
        ],
        "language_code": "ko",
        "language_level": "intermediate",
        "test_mode": false,  # optional
        "max_expressions": 50,  # optional
        "no_shorts": false,  # optional
        "output_dir": "output"  # optional
    }
    
    Returns:
    {
        "batch_id": "uuid",
        "total_jobs": 5,
        "jobs": [...],
        "status": "PENDING"
    }
    """
    try:
        # Convert Pydantic models to dictionaries
        videos = [video.dict() for video in request.videos]
        
        # Extract configuration
        config = {
            'language_code': request.language_code,
            'language_level': request.language_level,
            'test_mode': request.test_mode,
            'max_expressions': request.max_expressions,
            'no_shorts': request.no_shorts,
            'output_dir': request.output_dir
        }
        
        # Validate batch size
        batch_service = BatchQueueService()
        if len(videos) > batch_service.MAX_BATCH_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"Batch size {len(videos)} exceeds maximum {batch_service.MAX_BATCH_SIZE}"
            )
        
        # Create batch
        result = batch_service.create_batch(videos, config)
        
        logger.info(f"✅ Created batch {result['batch_id']} with {result['total_jobs']} jobs")
        
        return result
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating batch: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error creating batch: {str(e)}")


@router.get("/batch/{batch_id}")
async def get_batch_status(batch_id: str) -> Dict[str, Any]:
    """
    Get batch status with all job details.
    
    Returns:
    {
        "batch_id": "uuid",
        "status": "PROCESSING",
        "total_jobs": 5,
        "completed_jobs": 2,
        "failed_jobs": 0,
        "jobs": [...],
        "job_details": [...],
        "created_at": "...",
        "updated_at": "..."
    }
    """
    try:
        batch_service = BatchQueueService()
        batch_status = batch_service.get_batch_status(batch_id)
        
        if not batch_status:
            raise HTTPException(status_code=404, detail="Batch not found")
        
        return batch_status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting batch status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting batch status: {str(e)}")

