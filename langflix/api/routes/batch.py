"""
Batch processing endpoints for LangFlix API
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
import logging

from langflix.services.batch_queue_service import BatchQueueService

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/batch")
async def create_batch(request_data: Dict[str, Any]) -> Dict[str, Any]:
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
        # Validate request
        videos = request_data.get('videos', [])
        if not videos or not isinstance(videos, list):
            raise HTTPException(status_code=400, detail="'videos' array is required and must not be empty")
        
        # Extract configuration
        config = {
            'language_code': request_data.get('language_code'),
            'language_level': request_data.get('language_level', 'intermediate'),
            'test_mode': request_data.get('test_mode', False),
            'max_expressions': request_data.get('max_expressions', 50),
            'no_shorts': request_data.get('no_shorts', False),
            'output_dir': request_data.get('output_dir', 'output')
        }
        
        # Validate required fields
        if not config['language_code']:
            raise HTTPException(status_code=400, detail="'language_code' is required")
        
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

