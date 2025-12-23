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
import shutil
import os
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Import will be done inside functions to avoid circular imports

router = APIRouter()
logger = logging.getLogger(__name__)

LANGUAGE_CODE_MAP = {
    'ko': 'Korean',
    'en': 'English',
    'ja': 'Japanese',
    'zh': 'Chinese',
    'es': 'Spanish',
    'fr': 'French',
    'de': 'German',
    'it': 'Italian',
    'pt': 'Portuguese',
    'ru': 'Russian'
}

# Redis-based job storage for Phase 7 architecture
from langflix.core.redis_client import get_redis_job_manager
from langflix.utils.temp_file_manager import get_temp_manager
from langflix.core.error_handler import handle_error, ErrorContext

async def process_video_task(
    job_id: str,

    video_path: str,
    subtitle_path: str,
    video_filename: str,
    subtitle_filename: str,
    language_code: str,
    source_language: str,
    show_name: str = "",
    episode_name: str = "",
    max_expressions: int = 10,
    language_level: str = "intermediate",
    test_mode: bool = False,
    test_llm: bool = False,  # Dev: Use cached LLM response
    no_shorts: bool = False,
    short_form_max_duration: float = 180.0,
    target_duration: float = 120.0,
    output_dir: str = "output",
    target_languages: Optional[List[str]] = None,
    create_long_form: bool = True,
    create_short_form: bool = True,
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
        # Files will be manually cleaned up at the end

        
        # Validate paths exist
        if not Path(video_path).exists() or not Path(subtitle_path).exists():
            raise FileNotFoundError("Temp video or subtitle file not found")

        logger.info(f"Processing video: {video_filename} from {video_path}")
        logger.info(f"Processing subtitle: {subtitle_filename} from {subtitle_path}")
        
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
            source_language=source_language,
            target_languages=target_languages
        )
        
        # Process video using unified service
        # Note: Convert Path to string for compatibility
        result = service.process_video(
            video_path=video_path,
            subtitle_path=subtitle_path,
            show_name=show_name,
            episode_name=episode_name,
            max_expressions=max_expressions,
            language_level=language_level,
            test_mode=test_mode,
            test_llm=test_llm,
            no_shorts=no_shorts,
            create_long_form=create_long_form,
            create_short_form=create_short_form,
            short_form_max_duration=short_form_max_duration,
            target_duration=target_duration,
            progress_callback=update_progress
        )
                
        
        # Prepare upload results container
        upload_results = []
        
        # Invalidate video cache since new videos were created
        logger.info("Invalidating video cache after job completion...")
        redis_manager.invalidate_video_cache()
        
        logger.info(f"✅ Completed video processing for job {job_id}")
        
        # Auto Upload Logic
        if auto_upload_config and auto_upload_config.get('enabled'):
            try:
                # Update status to UPLOADING
                redis_manager.update_job(job_id, {
                    "status": "PROCESSING",
                    "progress": 95,
                    "current_step": "Auto-uploading to YouTube..."
                })

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
                
                # Gather all videos to upload
                # 1. Short videos
                short_videos = result.get('short_videos', [])
                if upload_shorts:
                    for video_path in short_videos:
                        videos_to_upload.append((video_path, "short"))
                
                # 2. Long/Final videos
                if upload_long:
                    final_video = result.get('final_video')
                    if final_video:
                        videos_to_upload.append((final_video, "final"))

                logger.info(f"Auto-upload config: shorts={upload_shorts}, long={upload_long}, timing={timing}")
                logger.info(f"Found {len(videos_to_upload)} videos to upload (Shorts: {len(short_videos)}, Final: {1 if result.get('final_video') else 0})")
                
                for video_path_upload, video_type in videos_to_upload:
                    
                    logger.info(f"Preparing to upload {video_type} video: {video_path_upload}")
                    
                    # Generate metadata
                    video_meta = video_manager._extract_video_metadata(Path(video_path_upload))
                    if not video_meta:
                        logger.warning(f"Could not scan video for metadata: {video_path_upload}")
                        continue
                        
                    # Resolve target language name
                    target_lang_code = video_meta.language
                    target_lang_name = LANGUAGE_CODE_MAP.get(target_lang_code, 'English')
                    
                    logger.info(f"Generating metadata with target language: {target_lang_name} (code: {target_lang_code})")
                        
                    youtube_metadata = metadata_generator.generate_metadata(
                        video_meta,
                        target_language=target_lang_name
                    )
                    
                    # Detailed Logging for User
                    logger.info("=" * 50)
                    logger.info(f"UPLOAD METADATA for {video_path_upload}")
                    logger.info(f"Title:       {youtube_metadata.title}")
                    logger.info(f"Privacy:     {youtube_metadata.privacy_status}")
                    logger.info(f"Tags:        {youtube_metadata.tags}")
                    if youtube_metadata.description:
                        logger.info(f"Desc Preview: {youtube_metadata.description[:100]}...")
                    logger.info("=" * 50)
                    
                    # Determine action based on timing and availability
                    should_upload_now = False
                    upload_result_data = {
                        "file": str(video_path_upload),
                        "type": video_type,
                        "title": youtube_metadata.title,
                        "status": "failed",
                        "video_id": None,
                        "url": None
                    }
                    
                    if timing == 'immediate':
                        youtube_metadata.privacy_status = 'private'
                        should_upload_now = True
                        
                    elif timing == 'scheduled':
                        if schedule_manager:
                            # Schedule upload (reserve slot)
                            publish_time = schedule_manager.get_next_available_slot(video_type)
                            success, msg, scheduled_time = schedule_manager.schedule_video(video_path_upload, video_type, publish_time)
                            
                            if success:
                                logger.info(f"Reserved schedule slot: {scheduled_time}")
                                logger.info(f"Starting scheduled upload with publishAt: {scheduled_time}")
                                
                                upload_result = uploader.upload_video(
                                    video_path=video_path_upload,
                                    metadata=youtube_metadata,
                                    publish_at=scheduled_time
                                )
                                
                                if upload_result.success:
                                    logger.info(f"✅ Scheduled upload success: {upload_result.video_id}")
                                    logger.info(f"🔗 Video URL: https://youtu.be/{upload_result.video_id}")
                                    schedule_manager.update_schedule_with_video_id(video_path_upload, upload_result.video_id, 'completed')
                                    
                                    upload_result_data.update({
                                        "status": "scheduled",
                                        "video_id": upload_result.video_id,
                                        "url": f"https://youtu.be/{upload_result.video_id}",
                                        "scheduled_for": str(scheduled_time)
                                    })
                                else:
                                    logger.error(f"Scheduled upload failed: {upload_result.error_message}")
                                    upload_result_data["error"] = upload_result.error_message
                            else:
                                logger.error(f"Scheduling failed: {msg}")
                                upload_result_data["error"] = f"Scheduling failed: {msg}"
                        else:
                            # Stateless fallback
                            publish_time = None
                            yt_scheduler = None
                            
                            try:
                                from langflix.youtube.last_schedule import YouTubeLastScheduleService, LastScheduleConfig
                                yt_scheduler = YouTubeLastScheduleService(LastScheduleConfig())
                                publish_time = yt_scheduler.get_next_available_slot()
                                logger.info(f"Stateless mode: next available slot: {publish_time}")
                            except Exception as e:
                                logger.warning(f"Failed to initialize YouTube scheduler fallback: {e}")
                            
                            if publish_time:
                                logger.info(f"Stateless scheduling: Uploading with publish_at={publish_time}")
                                
                                # Upload with publish_at
                                upload_result = uploader.upload_video(
                                    video_path_upload, 
                                    youtube_metadata, 
                                    publish_at=publish_time
                                )
                                
                                if upload_result.success:
                                    logger.info(f"✅ Stateless upload success: {upload_result.video_id}")
                                    logger.info(f"🔗 Video URL: https://youtu.be/{upload_result.video_id}")
                                    if yt_scheduler:
                                        yt_scheduler.record_local(publish_time)
                                        
                                    upload_result_data.update({
                                        "status": "scheduled (stateless)",
                                        "video_id": upload_result.video_id,
                                        "url": f"https://youtu.be/{upload_result.video_id}",
                                        "scheduled_for": str(publish_time)
                                    })
                                else:
                                    logger.error(f"Stateless upload failed: {upload_result.error_message}")
                                    upload_result_data["error"] = upload_result.error_message
                                    
                                should_upload_now = False
                            else:
                                logger.warning("No scheduling options available. Fallback to immediate private upload.")
                                youtube_metadata.privacy_status = 'private'
                                should_upload_now = True
                    
                    # Execute immediate upload if needed
                    if should_upload_now:
                        logger.info("Performing immediate upload...")
                        upload_result = uploader.upload_video(video_path_upload, youtube_metadata)
                        if upload_result.success:
                            logger.info(f"✅ Immediate upload success: {upload_result.video_id}")
                            logger.info(f"🔗 Video URL: https://youtu.be/{upload_result.video_id}")
                            
                            if schedule_manager:
                                schedule_manager.update_schedule_with_video_id(video_path_upload, upload_result.video_id, 'uploaded')
                            
                            upload_result_data.update({
                                "status": "uploaded",
                                "video_id": upload_result.video_id,
                                "url": f"https://youtu.be/{upload_result.video_id}"
                            })
                        else:
                            logger.error(f"Immediate upload failed: {upload_result.error_message}")
                            upload_result_data["error"] = upload_result.error_message
                    
                    # Add to results list
                    upload_results.append(upload_result_data)

            except Exception as e:
                logger.error(f"Auto-upload failed with exception: {e}", exc_info=True)
                # Don't fail the whole job if upload fails, just log it
                redis_manager.update_job(job_id, {"upload_error": str(e)})

        # Update job with FINAL results
        redis_manager.update_job(job_id, {
            "status": "COMPLETED",
            "progress": 100,
            "current_step": "Completed successfully!",
            "expressions": result.get("expressions", []),
            "educational_videos": result.get("educational_videos", []),
            "short_videos": result.get("short_videos", []),
            "final_video": result.get("final_video"),
            "completed_at": datetime.now(timezone.utc).isoformat(),
            "upload_results": upload_results
        })
        
        # Cleanup temp files explicitly
        temp_manager.cleanup_temp_file(Path(video_path))
        if subtitle_path:  # Dual-subtitle mode: subtitle_path may be empty
            temp_manager.cleanup_temp_file(Path(subtitle_path))
        
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
        # Cleanup temp files even on error
        temp_manager.cleanup_temp_file(Path(video_path))
        if subtitle_path:  # Dual-subtitle mode: subtitle_path may be empty
            temp_manager.cleanup_temp_file(Path(subtitle_path))

@router.post("/jobs")
async def create_job(
    video_file: UploadFile = File(...),
    subtitle_file: Optional[UploadFile] = File(None),  # Optional - discovers from Subs/ folder
    language_code: str = Form(...),
    show_name: str = Form(...),
    episode_name: str = Form(...),
    max_expressions: int = Form(10),
    language_level: str = Form("intermediate"),
    test_mode: bool = Form(False),
    test_llm: bool = Form(False),  # Dev: Use cached LLM response
    no_shorts: bool = Form(False),
    short_form_max_duration: float = Form(180.0),
    target_duration: float = Form(120.0),
    output_dir: str = Form("output"),
    target_languages: Optional[str] = Form(None),  # Comma-separated string like "ko,ja,zh"
    source_language: str = Form(...),  # Required explicit source language code (TICKET-VIDEO-002)
    create_long_form: bool = Form(True),
    create_short_form: bool = Form(True),
    auto_upload_config: Optional[str] = Form(None), # JSON string
    background_tasks: BackgroundTasks = BackgroundTasks()
) -> Dict[str, Any]:
    """Create a new video processing job."""
    
    try:
        # RAW PAYLOAD LOGGING (as requested)
        logger.info(f"🚀 JOB CREATION RAW PAYLOAD:")
        logger.info(f"   video_file: {video_file.filename}")
        logger.info(f"   language_code (primary): {language_code}")
        logger.info(f"   display_language: {language_code} (Mapped: {LANGUAGE_CODE_MAP.get(language_code, 'Unknown')})")
        logger.info(f"   source_language (explicit): {source_language}")
        logger.info(f"   target_languages (raw): '{target_languages}'")
        
        # Validate file types
        if not video_file.filename or not video_file.filename.lower().endswith(('.mp4', '.mkv', '.avi')):
            raise HTTPException(status_code=400, detail="Invalid video file type")

        # Validate subtitle file if provided
        # Auto-discovers subtitles from Subs/ folder - no subtitle_file required
        if subtitle_file and subtitle_file.filename:
            supported_subtitle_extensions = ('.srt', '.vtt', '.smi', '.ass', '.ssa')
            if not subtitle_file.filename.lower().endswith(supported_subtitle_extensions):
                raise HTTPException(
                    status_code=400, 
                    detail=f"Invalid subtitle file type. Supported formats: {', '.join(supported_subtitle_extensions)}"
                )
        
        # Check file sizes (optional validation)
        # Generate job ID first for temp file naming
        job_id = str(uuid.uuid4())
        
        # Get temp file manager
        temp_manager = get_temp_manager()
        
        video_ext = Path(video_file.filename).suffix or '.mkv'
        
        # Stream video file to disk (MEMORY OPTIMIZATION: Do not use read())
        logger.info(f"Streaming upload to disk for job {job_id}")
        
        video_temp_path = temp_manager.create_persistent_temp_file(suffix=video_ext, prefix=f'{job_id}_video_')
        with open(video_temp_path, 'wb') as buffer:
            shutil.copyfileobj(video_file.file, buffer)
        
        video_size = video_temp_path.stat().st_size
        if video_size == 0:
            raise HTTPException(status_code=400, detail="Empty video file uploaded")
        
        # Handle subtitle file (optional - auto-discovers from Subs/ folder)
        subtitle_temp_path = None
        if subtitle_file and subtitle_file.filename:
            subtitle_ext = Path(subtitle_file.filename).suffix or '.srt'
            subtitle_temp_path = temp_manager.create_persistent_temp_file(suffix=subtitle_ext, prefix=f'{job_id}_subtitle_')
            with open(subtitle_temp_path, 'wb') as buffer:
                shutil.copyfileobj(subtitle_file.file, buffer)
            
            subtitle_size = subtitle_temp_path.stat().st_size
            if subtitle_size == 0:
                raise HTTPException(status_code=400, detail="Empty subtitle file uploaded")
        
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
        
        logger.info(f"Creating job with test_mode={test_mode} (type: {type(test_mode)})")

        # Store job information in Redis
        job_data = {
            "job_id": job_id,
            "status": "PENDING",
            "video_file": video_file.filename,
            "subtitle_file": subtitle_file.filename if subtitle_file and subtitle_file.filename else "",
            "video_size": str(video_size),
            "subtitle_size": str(subtitle_temp_path.stat().st_size if subtitle_temp_path else 0),
            "language_code": language_code,
            "source_language": source_language,  # Source language for video
            "show_name": show_name,
            "episode_name": episode_name,
            "max_expressions": str(max_expressions),
            "language_level": language_level,
            "test_mode": str(test_mode),
            "test_llm": str(test_llm),
            "no_shorts": str(no_shorts),
            "short_form_max_duration": str(short_form_max_duration),
            "target_duration": str(target_duration),
            "create_long_form": str(create_long_form),
            "create_short_form": str(create_short_form),
            "progress": "0",
            "error": ""
        }
        
        redis_manager.create_job(job_id, job_data)
        
        # Start REAL background processing task with file paths (not content)
        # Dual-subtitle mode: subtitle_path may be empty - pipeline discovers from Subs/ folder
        background_tasks.add_task(
            process_video_task,
            job_id=job_id,
            video_path=str(video_temp_path),
            subtitle_path=str(subtitle_temp_path) if subtitle_temp_path else "",
            video_filename=video_file.filename,
            subtitle_filename=subtitle_file.filename if subtitle_file and subtitle_file.filename else "",
            language_code=language_code,
            source_language=source_language,
            show_name=show_name,
            episode_name=episode_name,
            max_expressions=max_expressions,
            language_level=language_level,
            test_mode=test_mode,
            test_llm=test_llm,
            no_shorts=no_shorts,
            short_form_max_duration=short_form_max_duration,
            target_duration=target_duration,
            output_dir=output_dir,
            target_languages=target_languages_list,
            create_long_form=create_long_form,
            create_short_form=create_short_form,
            auto_upload_config=auto_upload_config_dict
        )
        
        return {
            "job_id": job_id,
            "status": "PENDING",
            "message": "Job created successfully",
            "video_size_mb": round(video_size / (1024 * 1024), 2),
            "subtitle_size_kb": round(subtitle_temp_path.stat().st_size / 1024, 2) if subtitle_temp_path else 0
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
