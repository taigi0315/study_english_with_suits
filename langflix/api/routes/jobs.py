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
            f.write(video_content)
        
        with open(temp_subtitle_path, 'wb') as f:
            f.write(subtitle_content)
        
        logger.info(f"Processing video: {video_filename}")
        logger.info(f"Processing subtitle: {subtitle_filename}")
        
        # Update progress
        jobs_db[job_id]["progress"] = 20
        
        # Import LangFlix components inside function to avoid circular imports
        from langflix.core.expression_analyzer import analyze_chunk
        from langflix.core.subtitle_parser import parse_srt_file, chunk_subtitles
        from langflix.core.video_processor import VideoProcessor
        from langflix.core.video_editor import VideoEditor
        from langflix.core.subtitle_processor import SubtitleProcessor
        from langflix.services.output_manager import create_output_structure
        
        # Parse subtitles
        logger.info("Parsing subtitles...")
        subtitles = parse_srt_file(temp_subtitle_path)
        jobs_db[job_id]["progress"] = 30
        
        # Chunk subtitles
        logger.info("Chunking subtitles...")
        chunks = chunk_subtitles(subtitles)
        logger.info(f"Created {len(chunks)} chunks")
        
        # Analyze expressions
        logger.info("Analyzing expressions...")
        expressions = []
        
        # Process in chunks for large files
        chunk_size = 5 if test_mode else 20
        chunks_to_process = [chunks[0]] if test_mode and chunks else chunks
        
        for i, chunk in enumerate(chunks_to_process):
            if len(expressions) >= max_expressions:
                break
                
            logger.info(f"Analyzing chunk {i+1}/{len(chunks_to_process)}...")
            
            try:
                chunk_expressions = analyze_chunk(chunk, language_level=language_level, language_code=language_code)
                
                # Handle None return from analyze_chunk
                if chunk_expressions is not None:
                    expressions.extend(chunk_expressions)
                else:
                    logger.warning(f"analyze_chunk returned None for chunk {i+1}")
                
                if len(expressions) >= max_expressions:
                    break
                    
            except Exception as e:
                logger.error(f"Error analyzing chunk {i+1}: {e}")
                continue
            
            # In test mode, break after first chunk
            if test_mode:
                break
        
        # Limit to max_expressions
        expressions = expressions[:max_expressions]
        logger.info(f"Found {len(expressions)} expressions")
        jobs_db[job_id]["progress"] = 50
        
        # Create organized output structure using the same method as main branch
        # Create a proper subtitle file path that includes series/episode info
        proper_subtitle_path = f"{show_name}/{episode_name}/{subtitle_filename}"
        paths = create_output_structure(proper_subtitle_path, language_code, "output")
        
        # Initialize processors with proper paths
        # Create a temporary directory for video processing
        import tempfile
        temp_video_dir = tempfile.mkdtemp()
        video_processor = VideoProcessor(temp_video_dir)
        subtitle_processor = SubtitleProcessor(temp_subtitle_path)
        video_editor = VideoEditor(str(paths['language']['final_videos']), language_code)
        
        # Use the uploaded video file directly
        video_file = temp_video_path
        
        logger.info(f"Using video file: {video_file}")
        
        # Find expression timing for each expression
        logger.info("Finding exact expression timings from subtitles...")
        for expression in expressions:
            try:
                expression_start, expression_end = subtitle_processor.find_expression_timing(expression)
                expression.expression_start_time = expression_start
                expression.expression_end_time = expression_end
                logger.info(f"Expression '{expression.expression}' timing: {expression_start} to {expression_end}")
            except Exception as e:
                logger.warning(f"Could not find timing for expression '{expression.expression}': {e}")
        
        # Create subtitle files for each expression (required by video editor)
        logger.info("Creating subtitle files for expressions...")
        for i, expression in enumerate(expressions):
            try:
                # Create subtitle file using the same method as main branch
                safe_filename = "".join(c for c in expression.expression if c.isalnum() or c in (' ', '-', '_')).rstrip()
                subtitle_output = paths['language']['subtitles'] / f"expression_{i+1:02d}_{safe_filename[:30]}.srt"
                
                # Ensure the subtitle directory exists
                subtitle_output.parent.mkdir(parents=True, exist_ok=True)
                
                # Create dual language subtitle file
                subtitle_success = subtitle_processor.create_dual_language_subtitle_file(
                    expression,
                    str(subtitle_output)
                )
                
                if subtitle_success:
                    logger.info(f"✅ Subtitle file created: {subtitle_output}")
                else:
                    logger.warning(f"❌ Failed to create subtitle file: {subtitle_output}")
                    
            except Exception as e:
                logger.error(f"Error creating subtitle file for expression {i+1}: {e}")
                continue
        
        # Process each expression - Step 1: Extract video clips and create subtitles
        processed_expressions = []
        educational_videos = []
        temp_clip_files = []
        
        logger.info("Step 1: Processing expressions (extracting clips and creating subtitles)...")
        
        for i, expression in enumerate(expressions):
            logger.info(f"Processing expression {i+1}/{len(expressions)}: {expression.expression}")
            
            try:
                # Update progress
                progress = 50 + (i / len(expressions)) * 20
                jobs_db[job_id]["progress"] = int(progress)
                
                # Create output filenames using organized structure
                safe_expression = "".join(c for c in expression.expression if c.isalnum() or c in (' ', '-', '_')).rstrip()
                safe_filename = "".join(c for c in expression.expression if c.isalnum() or c in (' ', '-', '_')).rstrip()[:30]
                
                # Extract clip to temp directory
                temp_clip_path = f"/tmp/temp_expression_{i+1:02d}_{safe_filename}.mkv"
                success = video_processor.extract_clip(
                    video_file,
                    expression.context_start_time,
                    expression.context_end_time,
                    temp_clip_path
                )
                
                if not success:
                    logger.warning(f"Failed to extract clip for expression {i+1}")
                    continue
                
                temp_clip_files.append(temp_clip_path)
                logger.info(f"✅ Video clip created: {temp_clip_path}")
                
                # Create subtitle file using the same method as main branch
                subtitle_output = paths['language']['subtitles'] / f"expression_{i+1:02d}_{safe_filename}.srt"
                
                # Ensure the subtitle directory exists
                subtitle_output.parent.mkdir(parents=True, exist_ok=True)
                
                # Create dual language subtitle file
                subtitle_success = subtitle_processor.create_dual_language_subtitle_file(
                    expression,
                    str(subtitle_output)
                )
                
                if subtitle_success:
                    logger.info(f"✅ Subtitle file created: {subtitle_output}")
                else:
                    logger.warning(f"❌ Failed to create subtitle file: {subtitle_output}")
                
                processed_expressions.append({
                    "expression": expression.expression,
                    "translation": expression.translation,
                    "context": expression.expression_dialogue,
                    "similar_expressions": expression.similar_expressions,
                    "start_time": expression.context_start_time,
                    "end_time": expression.context_end_time
                })
                
            except Exception as e:
                logger.error(f"Error processing expression {i+1}: {e}")
                continue
        
        # Step 2: Create educational videos
        logger.info("Step 2: Creating educational videos...")
        
        for i, expression in enumerate(expressions):
            if i >= len(temp_clip_files):
                logger.warning(f"No video clip found for expression {i+1}")
                continue
                
            try:
                # Update progress
                progress = 70 + (i / len(expressions)) * 20
                jobs_db[job_id]["progress"] = int(progress)
                
                temp_clip_path = temp_clip_files[i]
                
                # Create educational sequence (handles slides, TTS, subtitles, final video)
                educational_video = video_editor.create_educational_sequence(
                    expression,
                    temp_clip_path,  # context video
                    str(video_file),  # original video for expression audio
                    expression_index=i
                )
                
                educational_videos.append(educational_video)
                
                # Update processed expression with video path
                if i < len(processed_expressions):
                    processed_expressions[i]["video_path"] = educational_video
                
                logger.info(f"✅ Educational video created: {educational_video}")
                
            except Exception as e:
                logger.error(f"Error creating educational video {i+1}: {e}")
                continue
        
        # Step 3: Create short-format videos (if not disabled)
        short_videos = []
        if not no_shorts:
            logger.info("Step 3: Creating short-format videos...")
            
            try:
                # Get context videos with subtitles (created by educational sequence)
                context_videos_dir = paths['language']['context_videos']
                context_videos = sorted(list(context_videos_dir.glob("context_*.mkv")))
                
                logger.info(f"Found {len(context_videos)} context videos for short video creation")
                
                if context_videos:
                    short_format_videos = []
                    
                    # Create a mapping from expression names to context videos
                    context_video_map = {}
                    for context_video in context_videos:
                        # Extract expression name from filename: context_{expression_name}.mkv
                        video_name = context_video.stem  # Remove .mkv extension
                        if video_name.startswith('context_'):
                            expression_name = video_name[8:]  # Remove 'context_' prefix
                            context_video_map[expression_name] = context_video
                    
                    logger.info(f"Context video mapping: {list(context_video_map.keys())}")
                    
                    for i, expression in enumerate(expressions):
                        # Sanitize expression name to match filename format
                        safe_expression_name = "".join(c for c in expression.expression if c.isalnum() or c in (' ', '-', '_')).rstrip()[:30]
                        logger.info(f"Looking for context video: context_{safe_expression_name}.mkv")
                        
                        if safe_expression_name in context_video_map:
                            context_video = context_video_map[safe_expression_name]
                            logger.info(f"Creating short format video {i+1}/{len(expressions)}: {expression.expression}")
                            logger.info(f"Using context video: {context_video.name}")
                            
                            try:
                                output_path, duration = video_editor.create_short_format_video(
                                    str(context_video), expression, i
                                )
                                short_format_videos.append((output_path, duration))
                                short_videos.append(output_path)
                                logger.info(f"✅ Short format video created: {output_path} (duration: {duration:.2f}s)")
                            except Exception as e:
                                logger.error(f"Error creating short format video for expression {i+1}: {e}")
                                continue
                        else:
                            logger.warning(f"No context video found for expression '{expression.expression}' (sanitized: '{safe_expression_name}')")
                            continue
                    
                    if short_format_videos:
                        # Batch into ~120s videos
                        target_duration = 120.0  # Default target duration
                        batch_videos = video_editor.create_batched_short_videos(
                            short_format_videos, target_duration=target_duration
                        )
                        
                        logger.info(f"✅ Created {len(batch_videos)} short video batches")
                        for batch_path in batch_videos:
                            logger.info(f"  - {batch_path}")
                    else:
                        logger.warning("No short format videos were created successfully")
                else:
                    logger.warning("No context videos found for short video creation")
                    
            except Exception as e:
                logger.error(f"Error creating short videos: {e}")
        else:
            logger.info("Step 3: Skipping short-format videos (--no-shorts flag)")
        
        # Step 4: Create final concatenated video (like main branch)
        logger.info("Step 4: Creating final concatenated video...")
        
        if educational_videos:
            try:
                # Create final video path
                final_video_path = paths['language']['final_videos'] / "final_educational_video_with_slides.mkv"
                
                # Create concat file for final video
                concat_file = paths['language']['final_videos'] / "final_concat.txt"
                with open(concat_file, 'w') as f:
                    for video_path in educational_videos:
                        f.write(f"file '{Path(video_path).absolute()}'\n")
                
                # Concatenate all educational videos
                import ffmpeg
                (
                    ffmpeg
                    .input(str(concat_file), format='concat', safe=0)
                    .output(str(final_video_path), 
                           vcodec='libx264', 
                           acodec='aac', 
                           preset='fast',
                           ac=2,  # Force stereo audio
                           ar=48000,  # Set sample rate
                           crf=23)  # Good quality
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True)
                )
                
                logger.info(f"✅ Final concatenated video created: {final_video_path}")
                
            except Exception as e:
                logger.error(f"Error creating final video: {e}")
        
        # Summary of created videos
        if educational_videos:
            logger.info(f"✅ Created {len(educational_videos)} educational videos")
            for i, video_path in enumerate(educational_videos):
                logger.info(f"  Educational Video {i+1}: {video_path}")
        
        if short_videos:
            logger.info(f"✅ Created {len(short_videos)} short-format videos")
            for i, video_path in enumerate(short_videos):
                logger.info(f"  Short Video {i+1}: {video_path}")
        
        # Clean up temporary files
        logger.info("Cleaning up temporary files...")
        try:
            os.unlink(temp_video_path)
            os.unlink(temp_subtitle_path)
            for temp_clip in temp_clip_files:
                if os.path.exists(temp_clip):
                    os.unlink(temp_clip)
        except Exception as e:
            logger.warning(f"Error cleaning up temp files: {e}")
        
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
