"""
Job management endpoints for LangFlix API
"""

from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, Depends, HTTPException
from datetime import datetime, timezone
from typing import Dict, Any, List
import uuid
import logging
import asyncio
import tempfile
import os
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Import will be done inside functions to avoid circular imports

router = APIRouter()
logger = logging.getLogger(__name__)

# Real job storage with actual processing
jobs_db: Dict[str, Dict[str, Any]] = {}

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
    no_shorts: bool
):
    """Process video in background task with REAL LangFlix pipeline."""
    
    logger.info(f"Starting REAL video processing for job {job_id}")
    
    try:
        # Update job status
        jobs_db[job_id]["status"] = "PROCESSING"
        jobs_db[job_id]["progress"] = 10
        
        # Save uploaded file contents to local filesystem for LangFlix pipeline
        temp_video_path = f"/tmp/{job_id}_video.mkv"
        temp_subtitle_path = f"/tmp/{job_id}_subtitle.srt"
        
        with open(temp_video_path, 'wb') as f:
            f.write(video_content)  # video_content is already bytes from parameter
        
        with open(temp_subtitle_path, 'wb') as f:
            f.write(subtitle_content)  # subtitle_content is already bytes from parameter
        
        logger.info(f"Processing video: {video_filename}")
        logger.info(f"Processing subtitle: {subtitle_filename}")
        
        # Update progress
        jobs_db[job_id]["progress"] = 20
        
        # Import LangFlix components inside function to avoid circular imports
        from langflix.core.expression_analyzer import analyze_chunk
        from langflix.core.subtitle_parser import parse_srt_file
        from langflix.core.video_processor import VideoProcessor
        from langflix.core.video_editor import VideoEditor
        from langflix.core.subtitle_processor import SubtitleProcessor
        from langflix.services.output_manager import OutputManager
        
        # Initialize components
        output_manager = OutputManager()
        
        # Parse subtitles
        logger.info("Parsing subtitles...")
        subtitles = parse_srt_file(temp_subtitle_path)
        jobs_db[job_id]["progress"] = 30
        
        # Analyze expressions
        logger.info("Analyzing expressions...")
        expressions = []
        
        # Process in chunks for large files
        chunk_size = 5 if test_mode else 20
        for i in range(0, len(subtitles), chunk_size):
            chunk = subtitles[i:i + chunk_size]
            chunk_expressions = analyze_chunk(chunk, language_code=language_code)
            expressions.extend(chunk_expressions)
            
            if len(expressions) >= max_expressions:
                break
        
        logger.info(f"Found {len(expressions)} expressions")
        jobs_db[job_id]["progress"] = 50
        
        # Create video processor
        video_processor = VideoProcessor()
        
        # Create episode structure
        episode_paths = output_manager.create_episode_structure(show_name, episode_name)
        language_paths = output_manager.create_language_structure(episode_paths, language_code)
        
        # Create video editor
        video_editor = VideoEditor(
            output_dir=str(language_paths['language_dir']),
            language_code=language_code
        )
        
        # Create subtitle processor
        subtitle_processor = SubtitleProcessor(temp_subtitle_path)
        
        # Process each expression
        processed_expressions = []
        total_expressions = min(len(expressions), max_expressions)
        
        for i, expression in enumerate(expressions[:max_expressions]):
            logger.info(f"Processing expression {i+1}/{total_expressions}: {expression.expression}")
            
            try:
                # Update progress
                progress = 50 + (i / total_expressions) * 40
                jobs_db[job_id]["progress"] = int(progress)
                
                # Create context video
                context_video_path = video_processor.create_context_video(
                    video_path=temp_video_path,
                    start_time=expression.start_time,
                    end_time=expression.end_time,
                    output_path=str(language_paths['context_videos'] / f"context_{i+1:02d}.mkv")
                )
                
                # Create educational slide
                educational_slide_path = video_editor.create_educational_slide(
                    expression=expression,
                    output_path=str(language_paths['slides'] / f"slide_{i+1:02d}.mkv")
                )
                
                # Create context video with subtitles
                context_with_subs_path = video_editor.create_context_video_with_subtitles(
                    context_video_path=context_video_path,
                    expression=expression,
                    output_path=str(language_paths['context_with_subs'] / f"context_with_subs_{i+1:02d}.mkv")
                )
                
                # Create final educational video
                final_video_path = video_editor.create_final_educational_video(
                    context_video_path=context_with_subs_path,
                    educational_slide_path=educational_slide_path,
                    output_path=str(language_paths['final_videos'] / f"final_{i+1:02d}.mkv")
                )
                
                processed_expressions.append({
                    "expression": expression.expression,
                    "translation": expression.translation,
                    "context": expression.context,
                    "similar_expressions": expression.similar_expressions,
                    "video_path": final_video_path,
                    "start_time": expression.start_time,
                    "end_time": expression.end_time
                })
                
            except Exception as e:
                logger.error(f"Error processing expression {i+1}: {e}")
                continue
        
        # Clean up temporary files
        try:
            os.unlink(temp_video_path)
            os.unlink(temp_subtitle_path)
        except:
            pass
        
        # Update job with results
        jobs_db[job_id]["status"] = "COMPLETED"
        jobs_db[job_id]["progress"] = 100
        jobs_db[job_id]["expressions"] = processed_expressions
        jobs_db[job_id]["completed_at"] = datetime.now(timezone.utc).isoformat()
        
        logger.info(f"Completed REAL processing for job {job_id}")
        
    except Exception as e:
        logger.error(f"Error processing job {job_id}: {e}")
        
        # Clean up temporary files
        try:
            if 'temp_video_path' in locals():
                os.unlink(temp_video_path)
            if 'temp_subtitle_path' in locals():
                os.unlink(temp_subtitle_path)
        except:
            pass
        
        # Update job with error
        jobs_db[job_id]["status"] = "FAILED"
        jobs_db[job_id]["error"] = str(e)
        jobs_db[job_id]["failed_at"] = datetime.now(timezone.utc).isoformat()

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
    background_tasks: BackgroundTasks = BackgroundTasks()
) -> Dict[str, Any]:
    """Create a new video processing job."""
    
    try:
        # Validate file types
        if not video_file.filename or not video_file.filename.lower().endswith(('.mp4', '.mkv', '.avi')):
            raise HTTPException(status_code=400, detail="Invalid video file type")
        
        if not subtitle_file.filename or not subtitle_file.filename.lower().endswith('.srt'):
            raise HTTPException(status_code=400, detail="Invalid subtitle file type")
        
        # Check file sizes (optional validation)
        video_content = await video_file.read()
        subtitle_content = await subtitle_file.read()
        
        # Reset file pointers
        await video_file.seek(0)
        await subtitle_file.seek(0)
        
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Store job information
        jobs_db[job_id] = {
            "job_id": job_id,
            "status": "PENDING",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "video_file": video_file.filename,
            "subtitle_file": subtitle_file.filename,
            "video_size": len(video_content),
            "subtitle_size": len(subtitle_content),
            "language_code": language_code,
            "show_name": show_name,
            "episode_name": episode_name,
            "max_expressions": max_expressions,
            "language_level": language_level,
            "test_mode": test_mode,
            "no_shorts": no_shorts,
            "progress": 0,
            "error": None
        }
        
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
            no_shorts=no_shorts
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
    
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs_db[job_id]
    
    # Return actual job status (no simulation)
    # Status is updated by the background task
    
    return job

@router.get("/jobs/{job_id}/expressions")
async def get_job_expressions(job_id: str) -> Dict[str, Any]:
    """Get expressions extracted from the job."""
    
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs_db[job_id]
    
    # Return ACTUAL expressions from processing
    if job["status"] != "COMPLETED":
        return {
            "job_id": job_id,
            "status": job["status"],
            "message": "Processing not completed yet",
            "expressions": []
        }
    
    return {
        "job_id": job_id,
        "status": job["status"],
        "expressions": job.get("expressions", []),
        "total_expressions": len(job.get("expressions", [])),
        "completed_at": job.get("completed_at")
    }

@router.get("/jobs")
async def list_jobs() -> Dict[str, Any]:
    """List all jobs."""
    return {
        "jobs": list(jobs_db.values()),
        "total": len(jobs_db)
    }
