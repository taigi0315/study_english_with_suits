"""
Background processing tasks for LangFlix API
"""

import logging
import asyncio
import tempfile
import os
from pathlib import Path
from typing import Any, Dict
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from langflix.core.expression_analyzer import analyze_chunk
from langflix.core.subtitle_parser import parse_srt_file
from langflix.core.video_processor import VideoProcessor
from langflix.core.video_editor import VideoEditor
from langflix.core.subtitle_processor import SubtitleProcessor
from langflix.services.output_manager import OutputManager
from langflix import settings

logger = logging.getLogger(__name__)

async def process_video_task(job_id: str, video_file: Any, subtitle_file: Any, **kwargs) -> Dict[str, Any]:
    """Process video in background task."""
    
    logger.info(f"Starting background processing for job {job_id}")
    
    try:
        # Create temporary files for processing
        with tempfile.NamedTemporaryFile(suffix='.mkv', delete=False) as temp_video:
            video_content = await video_file.read()
            temp_video.write(video_content)
            temp_video_path = temp_video.name
        
        with tempfile.NamedTemporaryFile(suffix='.srt', delete=False) as temp_subtitle:
            subtitle_content = await subtitle_file.read()
            temp_subtitle.write(subtitle_content)
            temp_subtitle_path = temp_subtitle.name
        
        logger.info(f"Processing video: {video_file.filename}")
        logger.info(f"Processing subtitle: {subtitle_file.filename}")
        
        # Initialize components
        language_code = kwargs.get('language_code', 'en')
        show_name = kwargs.get('show_name', 'Suits')
        episode_name = kwargs.get('episode_name', 'S01E01')
        max_expressions = kwargs.get('max_expressions', 10)
        test_mode = kwargs.get('test_mode', False)
        
        # Create output manager
        output_manager = OutputManager()
        
        # Parse subtitles
        logger.info("Parsing subtitles...")
        subtitles = parse_srt_file(temp_subtitle_path)
        
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
        
        # Create video processor
        video_processor = VideoProcessor()
        
        # Create video editor
        video_editor = VideoEditor(
            output_dir=str(output_manager.get_output_path(show_name, episode_name)),
            language_code=language_code
        )
        
        # Create subtitle processor
        subtitle_processor = SubtitleProcessor()
        
        # Process each expression
        processed_expressions = []
        for i, expression in enumerate(expressions[:max_expressions]):
            logger.info(f"Processing expression {i+1}/{min(len(expressions), max_expressions)}: {expression.expression}")

            try:
                # Create long-form educational video
                # (includes context video, expression repetition, and educational slide)
                long_form_video_path = video_editor.create_long_form_video(
                    expression=expression,
                    context_video_path=temp_video_path,  # Pass original video
                    expression_video_path=temp_video_path,  # Pass original video for audio
                    expression_index=i  # For voice alternation
                )

                logger.info(f"Created long-form video: {long_form_video_path}")

                processed_expressions.append({
                    "expression": expression.expression,
                    "translation": expression.expression_translation,
                    "dialogues": expression.dialogues,
                    "similar_expressions": expression.similar_expressions,
                    "video_path": long_form_video_path
                })

            except Exception as e:
                logger.error(f"Error processing expression {i+1}: {e}", exc_info=True)
                continue
        
        # Clean up temporary files
        try:
            os.unlink(temp_video_path)
            os.unlink(temp_subtitle_path)
        except:
            pass
        
        logger.info(f"Completed processing for job {job_id}")
        
        return {
            "job_id": job_id,
            "status": "COMPLETED",
            "message": "Processing completed successfully",
            "expressions_processed": len(processed_expressions),
            "expressions": processed_expressions
        }
        
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
        
        return {
            "job_id": job_id,
            "status": "FAILED",
            "error": str(e)
        }