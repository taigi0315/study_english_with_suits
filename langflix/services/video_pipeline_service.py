"""
Video Pipeline Service
Unified video processing pipeline service for both API and CLI
"""
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime, timezone

from langflix.main import LangFlixPipeline

logger = logging.getLogger(__name__)


class VideoPipelineService:
    """
    Unified video processing pipeline service for both API and CLI.
    
    This service wraps LangFlixPipeline and provides:
    - Consistent interface for API and CLI
    - Progress callback support
    - Standardized result format
    """
    
    def __init__(self, language_code: str, output_dir: str = "output"):
        """
        Initialize the video pipeline service
        
        Args:
            language_code: Target language code (e.g., 'ko', 'ja', 'zh')
            output_dir: Output directory for generated files
        """
        self.language_code = language_code
        self.output_dir = output_dir
        
    def process_video(
        self,
        video_path: str,
        subtitle_path: str,
        show_name: str,
        episode_name: str,
        max_expressions: int = 10,
        language_level: str = "intermediate",
        test_mode: bool = False,
        no_shorts: bool = False,
        short_form_max_duration: float = 180.0,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> Dict[str, Any]:
        """
        Process video with unified pipeline
        
        Args:
            video_path: Path to video file
            subtitle_path: Path to subtitle file
            show_name: Name of the show/series
            episode_name: Name of the episode
            max_expressions: Maximum number of expressions to process
            language_level: Target language level (beginner, intermediate, advanced, mixed)
            test_mode: If True, process only the first chunk for testing
            no_shorts: If True, skip creating short-format videos
            progress_callback: Optional callback function(progress: int, message: str) -> None
            
        Returns:
            Dictionary with processing results:
            {
                "expressions": List[dict],  # Processed expressions
                "educational_videos": List[str],  # Paths to educational videos
                "short_videos": List[str],  # Paths to short videos
                "final_video": str,  # Path to final concatenated video
                "output_directory": str,  # Output directory path
                "summary": dict  # Pipeline summary
            }
        """
        try:
            if progress_callback:
                progress_callback(10, "Initializing video processing...")
            
            # Create pipeline instance
            # Note: LangFlixPipeline expects video_dir (directory), not video_path (file)
            # So we need to pass the directory containing the video
            video_dir = str(Path(video_path).parent)
            
            pipeline = LangFlixPipeline(
                subtitle_file=subtitle_path,
                video_dir=video_dir,
                output_dir=self.output_dir,
                language_code=self.language_code,
                progress_callback=progress_callback,
                series_name=show_name,  # Pass show_name to pipeline
                episode_name=episode_name,  # Pass episode_name to pipeline
                video_file=video_path  # Pass direct video file path
            )
            
            if progress_callback:
                progress_callback(20, "Running pipeline...")
            
            # Run the pipeline
            result = pipeline.run(
                max_expressions=max_expressions,
                dry_run=False,
                language_level=language_level,
                save_llm_output=False,
                test_mode=test_mode,
                no_shorts=no_shorts,
                short_form_max_duration=short_form_max_duration
            )
            
            if progress_callback:
                progress_callback(90, "Pipeline completed, collecting results...")
            
            # Extract expressions from pipeline
            expressions = self._extract_expressions(pipeline.expressions)
            
            # Find generated videos
            paths = pipeline.paths
            educational_videos = self._find_educational_videos(paths)
            short_videos = self._find_short_videos(paths)
            final_video = self._find_final_video(paths, episode_name, video_path)
            
            if progress_callback:
                progress_callback(100, "Completed successfully!")
            
            return {
                "expressions": expressions,
                "educational_videos": educational_videos,
                "short_videos": short_videos,
                "final_video": final_video,
                "output_directory": str(paths['episode']['episode_dir']),
                "summary": result
            }
            
        except Exception as e:
            logger.error(f"Error in video pipeline service: {e}", exc_info=True)
            if progress_callback:
                progress_callback(0, f"Error: {str(e)}")
            raise
    
    def _extract_expressions(self, expressions: List) -> List[Dict[str, Any]]:
        """
        Extract expression data from ExpressionAnalysis objects
        
        Args:
            expressions: List of ExpressionAnalysis objects
            
        Returns:
            List of dictionaries with expression data
        """
        processed = []
        
        for expression in expressions:
            processed.append({
                "expression": expression.expression,
                "translation": expression.expression_translation,
                "context": expression.expression_dialogue,
                "context_translation": expression.expression_dialogue_translation,
                "similar_expressions": expression.similar_expressions,
                "start_time": expression.context_start_time,
                "end_time": expression.context_end_time,
                "expression_start_time": getattr(expression, 'expression_start_time', None),
                "expression_end_time": getattr(expression, 'expression_end_time', None),
                "difficulty": getattr(expression, 'difficulty', None),
                "category": getattr(expression, 'category', None)
            })
        
        return processed
    
    def _find_educational_videos(self, paths: Dict[str, Any]) -> List[str]:
        """
        Find generated educational videos
        
        Args:
            paths: Path mappings from pipeline
            
        Returns:
            List of educational video file paths
        """
        final_videos_dir = paths.get('language', {}).get('final_videos')
        if not final_videos_dir:
            return []
        
        # Look for educational videos (individual expression videos)
        # Pattern: educational_*.mkv or similar
        educational_videos = []
        if isinstance(final_videos_dir, Path):
            for video_file in final_videos_dir.glob("educational_*.mkv"):
                if video_file.exists():
                    educational_videos.append(str(video_file))
        
        return sorted(educational_videos)
    
    def _find_short_videos(self, paths: Dict[str, Any]) -> List[str]:
        """
        Find generated short-format videos
        
        Args:
            paths: Path mappings from pipeline
            
        Returns:
            List of short video file paths
        """
        short_videos_dir = paths.get('language', {}).get('short_videos')
        if not short_videos_dir:
            return []
        
        short_videos = []
        if isinstance(short_videos_dir, Path):
            # Look for short videos and batched short videos
            for video_file in short_videos_dir.glob("*.mkv"):
                if video_file.exists():
                    short_videos.append(str(video_file))
        
        return sorted(short_videos)
    
    def _find_final_video(self, paths: Dict[str, Any], episode_name: str, video_path: str) -> Optional[str]:
        """
        Find final concatenated video
        
        Args:
            paths: Path mappings from pipeline
            episode_name: Episode name
            video_path: Original video path (for filename extraction)
            
        Returns:
            Path to final video, or None if not found
        """
        final_videos_dir = paths.get('language', {}).get('final_videos')
        if not final_videos_dir:
            return None
        
        if isinstance(final_videos_dir, Path):
            # Look for final video (long-form_*.mkv)
            video_filename = Path(video_path).stem if video_path else "video"
            final_video_pattern = f"long-form_{episode_name}_*.mkv"
            
            for video_file in final_videos_dir.glob(final_video_pattern):
                if video_file.exists():
                    return str(video_file)
            
            # Fallback: look for any long-form video
            for video_file in final_videos_dir.glob("long-form_*.mkv"):
                if video_file.exists():
                    return str(video_file)
        
        return None

