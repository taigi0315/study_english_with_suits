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
            
            # Get output directory
            output_dir = get_storage_local_path()
            
            # Extract show/episode info from video path
            video_path = Path(job.video_path)
            show_name = video_path.parent.name
            episode = video_path.stem
            
            # Run the actual LangFlix pipeline
            update_progress(10, "Initializing LangFlix pipeline...")
            
            # Create pipeline instance with progress callback
            pipeline = LangFlixPipeline(
                subtitle_file=job.subtitle_path,
                video_dir=os.path.dirname(job.video_path),  # Directory containing the video
                output_dir=output_dir,
                language_code=job.language_code,
                progress_callback=update_progress  # Pass progress callback to pipeline
            )
            
            # Run the pipeline
            update_progress(30, "Running LangFlix pipeline...")
            result = pipeline.run(
                max_expressions=50,
                dry_run=False,
                language_level=job.language_level,
                save_llm_output=False,
                test_mode=False,
                no_shorts=False
            )
            
            update_progress(90, "Pipeline completed!")
            
            # Extract results from pipeline summary
            # Note: pipeline.run() returns summary dict, not direct video paths
            expressions_processed = result.get('expressions_count', 0)
            
            # Extract video paths from pipeline.paths
            # Structure: pipeline.paths['languages'][lang_code]['final_videos'] (dir path)
            # We need to list actual files generated
            final_videos = []
            short_videos = []
            
            if hasattr(pipeline, 'paths') and 'languages' in pipeline.paths:
                 for lang_code, lang_paths in pipeline.paths['languages'].items():
                    # Find long-form videos
                    if 'final_videos' in lang_paths:
                        final_dir = Path(lang_paths['final_videos'])
                        if final_dir.exists():
                             # Get all generated .mkv files in the final folder
                             # excluding temp files just in case
                             videos = [str(p) for p in final_dir.glob("*.mkv") if not p.name.startswith("temp_")]
                             final_videos.extend(videos)
                    
                    # Find short-form videos
                    if 'shorts' in lang_paths:
                        shorts_dir = Path(lang_paths['shorts'])
                        if shorts_dir.exists():
                             shorts = [str(p) for p in shorts_dir.glob("*.mkv") if not p.name.startswith("temp_")]
                             short_videos.extend(shorts)

            # Fallback if no specific language structure (single language mode)
            if not final_videos and hasattr(pipeline, 'paths') and 'final_videos' in pipeline.paths:
                 final_dir = Path(pipeline.paths['final_videos'])
                 if final_dir.exists():
                      videos = [str(p) for p in final_dir.glob("*.mkv") if not p.name.startswith("temp_")]
                      final_videos.extend(videos)

            logger.info(f"Pipeline finished. Found {len(final_videos)} long-form and {len(short_videos)} short-form videos.")

            # Step 6: Finalize (100%)
            update_progress(100, "Completed!")
            
            return {
                "final_videos": final_videos,
                "short_videos": short_videos,
                "expressions_processed": expressions_processed,
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

