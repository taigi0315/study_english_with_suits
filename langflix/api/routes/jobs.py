"""
Job management endpoints for LangFlix API
"""

from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, Depends, HTTPException
from datetime import datetime, timezone
from typing import Dict, Any, List
import uuid
import logging
import asyncio
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Import will be done inside functions to avoid circular imports

router = APIRouter()
logger = logging.getLogger(__name__)

# Redis-based job storage for Phase 7 architecture
from langflix.core.redis_client import get_redis_job_manager
from langflix.utils.temp_file_manager import get_temp_manager
from langflix.core.error_handler import handle_error, ErrorContext

async def process_video_task(
    job_id: str,
    video_content: bytes,
    subtitle_content: bytes,
    video_filename: str,
    subtitle_filename: str,
    language_code: str,
    show_name: str,
    episode_name: str,
    max_expressions: int,
    language_level: str,
    test_mode: bool,
    no_shorts: bool,
    short_form_max_duration: float = 180.0,
    output_dir: str = "output"
):
    """Process video in background task using unified VideoPipelineService."""
    
    logger.info(f"Starting video processing for job {job_id}")
    
    # Get temp file manager for automatic cleanup
    temp_manager = get_temp_manager()
    
    try:
        # Get Redis job manager
        redis_manager = get_redis_job_manager()
        
        # Update job status
        redis_manager.update_job(job_id, {
            "status": "PROCESSING",
            "progress": 10,
            "current_step": "Initializing video processing..."
        })
        
        # Save uploaded file contents using temp file manager
        # Files will be automatically cleaned up when context exits
        # Determine file extensions from filenames
        video_ext = Path(video_filename).suffix or '.mkv'
        subtitle_ext = Path(subtitle_filename).suffix or '.srt'
        
        with temp_manager.create_temp_file(suffix=video_ext, prefix=f'{job_id}_video_') as temp_video_path:
            with temp_manager.create_temp_file(suffix=subtitle_ext, prefix=f'{job_id}_subtitle_') as temp_subtitle_path:
                # Write file contents
                temp_video_path.write_bytes(video_content)
                temp_subtitle_path.write_bytes(subtitle_content)
                
                logger.info(f"Processing video: {video_filename}")
                logger.info(f"Processing subtitle: {subtitle_filename}")
                
                # Progress callback wrapper for Redis updates
                def update_progress(progress: int, message: str):
                    """Update job progress in Redis"""
                    redis_manager.update_job(job_id, {
                        "progress": progress,
                        "current_step": message
                    })
                
                # Use unified pipeline service
                from langflix.services.video_pipeline_service import VideoPipelineService
                
                service = VideoPipelineService(
                    language_code=language_code,
                    output_dir=output_dir
                )
                
                # Process video using unified service
                # Note: Convert Path to string for compatibility
                result = service.process_video(
                    video_path=str(temp_video_path),
                    subtitle_path=str(temp_subtitle_path),
                    show_name=show_name,
                    episode_name=episode_name,
                    max_expressions=max_expressions,
                    language_level=language_level,
                    test_mode=test_mode,
                    no_shorts=no_shorts,
                    short_form_max_duration=short_form_max_duration,
                    progress_callback=update_progress
                )
                
                # Update job with results
                redis_manager.update_job(job_id, {
                    "status": "COMPLETED",
                    "progress": 100,
                    "current_step": "Completed successfully!",
                    "expressions": result.get("expressions", []),
                    "educational_videos": result.get("educational_videos", []),
                    "short_videos": result.get("short_videos", []),
                    "final_video": result.get("final_video"),
                    "completed_at": datetime.now(timezone.utc).isoformat()
                })
                
                # Invalidate video cache since new videos were created
                logger.info("Invalidating video cache after job completion...")
                redis_manager.invalidate_video_cache()
                
                logger.info(f"✅ Completed processing for job {job_id}")
                # Temp files automatically cleaned up when context exits
        
    except Exception as e:
        logger.error(f"Error processing job {job_id}: {e}", exc_info=True)
        
        # Report error to error handler for structured logging
        error_context = ErrorContext(
            operation="process_video_task",
            component="api.routes.jobs",
            additional_data={
                "job_id": job_id,
                "video_filename": video_filename,
                "subtitle_filename": subtitle_filename
            }
        )
        handle_error(e, error_context, retry=False, fallback=False)
        
        # Update job with error
        redis_manager = get_redis_job_manager()
        redis_manager.update_job(job_id, {
            "status": "FAILED",
            "error": str(e),
            "failed_at": datetime.now(timezone.utc).isoformat()
        })
        # Temp files automatically cleaned up by context manager even on exception

@router.post("/jobs")
async def create_job(
    video_file: UploadFile = File(...),
    subtitle_file: UploadFile = File(...),
    language_code: str = Form(...),
    show_name: str = Form(...),
    episode_name: str = Form(...),
    max_expressions: int = Form(10),
    language_level: str = Form("intermediate"),
    test_mode: bool = Form(False),
    no_shorts: bool = Form(False),
    short_form_max_duration: float = Form(180.0),
    output_dir: str = Form("output"),
    background_tasks: BackgroundTasks = BackgroundTasks()
) -> Dict[str, Any]:
    """Create a new video processing job."""
    
    try:
        # Validate file types
        if not video_file.filename or not video_file.filename.lower().endswith(('.mp4', '.mkv', '.avi')):
            raise HTTPException(status_code=400, detail="Invalid video file type")
        
        # Support multiple subtitle formats: SRT, VTT, SMI, ASS, SSA
        supported_subtitle_extensions = ('.srt', '.vtt', '.smi', '.ass', '.ssa')
        if not subtitle_file.filename or not subtitle_file.filename.lower().endswith(supported_subtitle_extensions):
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid subtitle file type. Supported formats: {', '.join(supported_subtitle_extensions)}"
            )
        
        # Check file sizes (optional validation)
        video_content = await video_file.read()
        subtitle_content = await subtitle_file.read()
        
        # Reset file pointers
        await video_file.seek(0)
        await subtitle_file.seek(0)
        
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Get Redis job manager
        redis_manager = get_redis_job_manager()
        
        # Store job information in Redis
        job_data = {
            "job_id": job_id,
            "status": "PENDING",
            "video_file": video_file.filename,
            "subtitle_file": subtitle_file.filename,
            "video_size": str(len(video_content)),
            "subtitle_size": str(len(subtitle_content)),
            "language_code": language_code,
            "show_name": show_name,
            "episode_name": episode_name,
            "max_expressions": str(max_expressions),
            "language_level": language_level,
            "test_mode": str(test_mode),
            "no_shorts": str(no_shorts),
            "short_form_max_duration": str(short_form_max_duration),
            "progress": "0",
            "error": ""
        }
        
        redis_manager.create_job(job_id, job_data)
        
        # Start REAL background processing task with file contents
        background_tasks.add_task(
            process_video_task,
            job_id=job_id,
            video_content=video_content,
            subtitle_content=subtitle_content,
            video_filename=video_file.filename,
            subtitle_filename=subtitle_file.filename,
            language_code=language_code,
            show_name=show_name,
            episode_name=episode_name,
            max_expressions=max_expressions,
            language_level=language_level,
            test_mode=test_mode,
            no_shorts=no_shorts,
            short_form_max_duration=short_form_max_duration,
            output_dir=output_dir
        )
        
        return {
            "job_id": job_id,
            "status": "PENDING",
            "message": "Job created successfully",
            "video_size_mb": round(len(video_content) / (1024 * 1024), 2),
            "subtitle_size_kb": round(len(subtitle_content) / 1024, 2)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating job: {str(e)}")

@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str) -> Dict[str, Any]:
    """Get job status and details."""
    
    redis_manager = get_redis_job_manager()
    job = redis_manager.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Return actual job status from Redis
    return job

@router.get("/jobs/{job_id}/expressions")
async def get_job_expressions(job_id: str) -> Dict[str, Any]:
    """Get expressions extracted from the job."""
    
    redis_manager = get_redis_job_manager()
    job = redis_manager.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Return ACTUAL expressions from processing
    if job.get("status") != "COMPLETED":
        return {
            "job_id": job_id,
            "status": job.get("status", "UNKNOWN"),
            "message": "Processing not completed yet",
            "expressions": []
        }
    
    return {
        "job_id": job_id,
        "status": job.get("status", "UNKNOWN"),
        "expressions": job.get("expressions", []),
        "total_expressions": len(job.get("expressions", [])),
        "completed_at": job.get("completed_at")
    }

@router.get("/jobs")
async def list_jobs() -> Dict[str, Any]:
    """List all jobs."""
    redis_manager = get_redis_job_manager()
    jobs = redis_manager.get_all_jobs()
    return {
        "jobs": list(jobs.values()),
        "total": len(jobs)
    }
