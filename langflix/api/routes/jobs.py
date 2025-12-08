"""
Job management endpoints for LangFlix API
"""

from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, Depends, HTTPException
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
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
    output_dir: str = "output",
    target_languages: Optional[List[str]] = None,
    auto_upload_config: Optional[Dict[str, Any]] = None
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
                    output_dir=output_dir,
                    target_languages=target_languages
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
                
                # Auto Upload Logic
                if auto_upload_config and auto_upload_config.get('enabled'):
                    try:
                        logger.info(f"Starting auto-upload for job {job_id}")
                        from langflix.youtube.uploader import YouTubeUploader
                        from langflix.youtube.schedule_manager import YouTubeScheduleManager
                        from langflix.youtube.metadata_generator import YouTubeMetadataGenerator, YouTubeVideoMetadata
                        from langflix.youtube.video_manager import VideoFileManager
                        from langflix import settings
                        
                        # Initialize services
                        uploader = YouTubeUploader()
                        schedule_manager = None
                        
                        # Check database availability before initializing schedule manager
                        from langflix.db.session import db_manager
                        if settings.get_database_enabled():
                            if db_manager.check_connection():
                                schedule_manager = YouTubeScheduleManager()
                            else:
                                logger.warning("Database enabled but unreachable. Running in stateless mode (scheduling disabled).")
                        
                        metadata_generator = YouTubeMetadataGenerator()
                        video_manager = VideoFileManager()
                        
                        timing = auto_upload_config.get('timing', 'scheduled')
                        upload_shorts = auto_upload_config.get('upload_shorts', True)
                        upload_long = auto_upload_config.get('upload_long', True)
                        
                        videos_to_upload = []
                        
                        # Add final video if requested
                        if upload_long and result.get('final_video'):
                            videos_to_upload.append({
                                'path': result['final_video'],
                                'type': 'final'
                            })
                            
                        # Add short videos if requested
                        if upload_shorts and result.get('short_videos'):
                            for short_video in result['short_videos']:
                                videos_to_upload.append({
                                    'path': short_video,
                                    'type': 'short'
                                })
                        
                        for video in videos_to_upload:
                            video_path = video['path']
                            video_type = video['type']
                            
                            logger.info(f"Auto-uploading {video_type} video: {video_path}")
                            
                            # Generate metadata
                            # We need to scan the file first to get metadata
                            # Or manually construct it since we have the expressions
                            # Let's use VideoFileManager to be consistent
                            video_meta = video_manager._extract_video_metadata(Path(video_path))
                            if not video_meta:
                                logger.warning(f"Could not scan video for metadata: {video_path}")
                                continue
                                
                            youtube_metadata = metadata_generator.generate_metadata(video_meta)
                            
                            # Determine action based on timing and availability
                            should_upload_now = False
                            
                            if timing == 'immediate':
                                youtube_metadata.privacy_status = 'private'
                                should_upload_now = True
                                
                            elif timing == 'scheduled':
                                if schedule_manager:
                                    # Schedule upload (reserve slot)
                                    publish_time = schedule_manager.get_next_available_slot(video_type)
                                    success, msg, scheduled_time = schedule_manager.schedule_video(video_path, video_type, publish_time)
                                    
                                    if success:
                                        logger.info(f"Reserved schedule slot: {scheduled_time}")
                                        
                                        # Perform the actual upload with publish_at
                                        # This ensures the video is uploaded now but goes live at the scheduled time
                                        logger.info(f"Starting scheduled upload for {video_path} with publishAt: {scheduled_time}")
                                        upload_result = uploader.upload_video(
                                            video_path=video_path,
                                            metadata=youtube_metadata,
                                            publish_at=scheduled_time
                                        )
                                        
                                        if upload_result.success:
                                            logger.info(f"Scheduled upload success: {upload_result.video_id}")
                                            # Update schedule with video ID and status
                                            schedule_manager.update_schedule_with_video_id(
                                                video_path, 
                                                upload_result.video_id, 
                                                'completed'
                                            )
                                        else:
                                            logger.error(f"Scheduled upload failed: {upload_result.error_message}")
                                            # Note: The schedule record remains in DB but without video_id, 
                                            # indicating it was reserved but upload failed.
                                    else:
                                        logger.error(f"Scheduling failed: {msg}")
                                else:
                                    # Stateless fallback: Try YouTube-based scheduler first
                                    publish_time = None
                                    yt_scheduler = None
                                    
                                    try:
                                        from langflix.youtube.last_schedule import YouTubeLastScheduleService, LastScheduleConfig
                                        # Initialize with default config
                                        yt_scheduler = YouTubeLastScheduleService(LastScheduleConfig())
                                        # Map video type to schedule type (context -> short, long-form -> final)
                                        schedule_video_type = 'short' if video_type == 'context' else ('final' if video_type == 'long-form' else video_type)
                                        
                                        # Get next slot from YouTube/cache
                                        publish_time = yt_scheduler.get_next_available_slot()
                                        logger.info(f"Stateless mode: would schedule for next slot: {publish_time}")
                                        
                                    except Exception as e:
                                        logger.warning(f"Failed to initialize YouTube scheduler fallback: {e}")
                                        yt_scheduler = None
                                    
                                    if publish_time:
                                        # We have a slot, so we can "schedule" it by setting publish_at
                                        # Note: We can't store it in DB, but we can tell YouTube to publish it then
                                        logger.info(f"Stateless scheduling: Uploading with publish_at={publish_time}")
                                        
                                        # Upload with publish_at
                                        upload_result = uploader.upload_video(
                                            video_path, 
                                            youtube_metadata, 
                                            publish_at=publish_time
                                        )
                                        
                                        if upload_result.success:
                                            logger.info(f"Stateless upload success: {upload_result.video_id} (scheduled for {publish_time})")
                                            # Update local cache so next video in this batch gets next slot
                                            if yt_scheduler:
                                                yt_scheduler.record_local(publish_time)
                                        else:
                                            logger.error(f"Stateless upload failed: {upload_result.error_message}")
                                            
                                        # Skip the immediate upload block below
                                        should_upload_now = False
                                        
                                    else:
                                        # truly stateless fallback if even YouTube scheduler fails
                                        logger.warning("Database unavailable and YouTube scheduler failed. Falling back to immediate private upload.")
                                        youtube_metadata.privacy_status = 'private'
                                        should_upload_now = True
                            
                            # Execute immediate upload if needed (and not handled by stateless scheduling above)
                            if should_upload_now:
                                upload_result = uploader.upload_video(video_path, youtube_metadata)
                                if upload_result.success:
                                    logger.info(f"Immediate upload success: {upload_result.video_id}")
                                    # Update DB if available
                                    if schedule_manager:
                                        schedule_manager.update_schedule_with_video_id(video_path, upload_result.video_id, 'uploaded')
                                else:
                                    logger.error(f"Immediate upload failed: {upload_result.error_message}")
                                    
                    except Exception as e:
                        logger.error(f"Auto-upload failed: {e}", exc_info=True)
                
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
    target_languages: Optional[str] = Form(None),  # Comma-separated string like "ko,ja,zh"
    auto_upload_config: Optional[str] = Form(None), # JSON string
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
        
        # Parse target_languages if provided
        target_languages_list = None
        if target_languages:
            # Parse comma-separated string to list
            target_languages_list = [lang.strip() for lang in target_languages.split(',') if lang.strip()]
            logger.info(f"Target languages: {target_languages_list}")
            
        # Parse auto_upload_config if provided
        auto_upload_config_dict = None
        if auto_upload_config:
            import json
            try:
                auto_upload_config_dict = json.loads(auto_upload_config)
                logger.info(f"Auto upload config: {auto_upload_config_dict}")
            except Exception as e:
                logger.warning(f"Failed to parse auto_upload_config: {e}")
        
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
            output_dir=output_dir,
            target_languages=target_languages_list,
            auto_upload_config=auto_upload_config_dict
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
