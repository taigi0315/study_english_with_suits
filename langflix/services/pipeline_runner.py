"""
Pipeline Runner
Wraps the main LangFlix content creation pipeline for async execution
"""
import logging
import sys
import os
from pathlib import Path
from typing import Dict, Any, Optional, Callable
from langflix.services.job_queue import Job

logger = logging.getLogger(__name__)


class PipelineRunner:
    """Wraps the main pipeline for async execution with progress tracking"""
    
    def __init__(self):
        """Initialize pipeline runner"""
        pass
    
    def run_pipeline(
        self, 
        job: Job,
        progress_callback: Optional[Callable[[str, int, str], None]] = None
    ) -> Dict[str, Any]:
        """
        Run the content creation pipeline for a job
        
        Args:
            job: Job to process
            progress_callback: Optional callback for progress updates (job_id, progress, message)
            
        Returns:
            Dictionary with results (final_videos, short_videos, expressions_processed)
        """
        try:
            logger.info(f"Starting pipeline for job {job.job_id}")
            
            # Validate inputs
            if not os.path.exists(job.video_path):
                raise FileNotFoundError(f"Video file not found: {job.video_path}")
            
            if job.subtitle_path and not os.path.exists(job.subtitle_path):
                raise FileNotFoundError(f"Subtitle file not found: {job.subtitle_path}")
            
            # Import main pipeline
            from langflix.main import LangFlixPipeline
            from langflix.settings import get_storage_local_path
            
            # Callback wrapper
            def update_progress(progress: int, message: str):
                if progress_callback:
                    progress_callback(job.job_id, progress, message)
            
            # Step 1: Parse subtitles (10%)
            update_progress(10, "Parsing subtitles...")
            if not job.subtitle_path:
                raise ValueError("Subtitle file is required for content creation")
            
            subtitle_entries = parse_subtitle_file(job.subtitle_path)
            logger.info(f"Parsed {len(subtitle_entries)} subtitle entries")
            
            # Step 2: Analyze expressions (30%)
            update_progress(30, "Analyzing expressions...")
            # Convert subtitle entries to the format expected by analyze_chunk
            subtitle_chunks = [subtitle_entries]  # analyze_chunk expects a list of chunks
            analyzed_expressions = analyze_chunk(
                subtitle_chunks[0], 
                language_level=job.language_level, 
                language_code=job.language_code
            )
            logger.info(f"Analyzed {len(analyzed_expressions)} expressions")
            
            # Step 3: Select expressions (40%)
            update_progress(40, "Selecting expressions...")
            selector = IntelligentExpressionSelector()
            context = {
                'language_level': job.language_level,
                'target_language': job.language_code,
                'max_expressions': 50
            }
            selection_result = selector.select_expressions(
                analyzed_expressions,
                target_count=50,  # Configurable
                context=context
            )
            selected_expressions = selection_result.selected_expressions
            logger.info(f"Selected {len(selected_expressions)} expressions")
            
            # Step 4: Generate videos (60%)
            update_progress(60, "Generating videos...")
            
            # Get output directory
            output_dir = get_storage_local_path()
            
            # Extract show/episode info from video path
            video_path = Path(job.video_path)
            show_name = video_path.parent.name
            episode = video_path.stem
            
            # Run the actual LangFlix pipeline
            update_progress(70, "Running LangFlix pipeline...")
            
            # Create pipeline instance
            pipeline = LangFlixPipeline(
                subtitle_file=job.subtitle_path,
                video_dir=os.path.dirname(job.video_path),  # Directory containing the video
                output_dir=output_dir,
                language_code=job.language_code
            )
            
            # Run the pipeline
            result = pipeline.run(
                max_expressions=50,
                dry_run=False,
                language_level=job.language_level,
                save_llm_output=False,
                test_mode=False,
                no_shorts=False
            )
            
            update_progress(90, "Pipeline completed!")
            
            # Extract results
            final_video_path = result.get('final_video_path', '')
            short_videos = result.get('short_videos', [])
            
            # Step 6: Finalize (100%)
            update_progress(100, "Completed!")
            
            return {
                "final_videos": [final_video_path] if final_video_path else [],
                "short_videos": short_videos,
                "expressions_processed": len(selected_expressions),
                "show_name": show_name,
                "episode": episode
            }
            
        except Exception as e:
            logger.error(f"Pipeline failed for job {job.job_id}: {e}", exc_info=True)
            raise


def create_pipeline_processor(progress_callback: Optional[Callable[[str, int, str], None]] = None) -> Callable[[Job], Dict[str, Any]]:
    """
    Create a pipeline processor function for the job queue
    
    Args:
        progress_callback: Optional callback for progress updates
        
    Returns:
        Processor function
    """
    runner = PipelineRunner()
    
    def processor(job: Job) -> Dict[str, Any]:
        return runner.run_pipeline(job, progress_callback)
    
    return processor

