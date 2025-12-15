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
    
    def __init__(self, language_code: str, output_dir: str = "output", target_languages: Optional[List[str]] = None):
        """
        Initialize the video pipeline service
        
        Args:
            language_code: Primary target language code (e.g., 'ko', 'ja', 'zh')
            output_dir: Output directory for generated files
            target_languages: List of target language codes for multi-language generation (defaults to [language_code])
        """
        self.language_code = language_code
        self.output_dir = output_dir
        self.target_languages = target_languages or [language_code]
        
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
        create_long_form: bool = True,
        create_short_form: bool = True,
        short_form_max_duration: float = 180.0,
        schedule_upload: bool = False,
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
            create_long_form: If True, create combined long-form video (default: True)
            create_short_form: If True, create short-form videos (default: True)
            schedule_upload: If True, upload generated videos to YouTube
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
            import uuid
            job_id = str(uuid.uuid4())[:8]
            logger.info(f"[{job_id}] Starting video processing for '{video_path}' (Episode: {episode_name})")

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
                target_languages=self.target_languages,  # Pass target languages for multi-language support
                progress_callback=progress_callback,
                series_name=show_name,  # Pass show_name to pipeline
                episode_name=episode_name,  # Pass episode_name to pipeline
                video_file=video_path  # Pass direct video file path
            )
            
            if progress_callback:
                progress_callback(20, "Running pipeline...")
            
            # Determine flags
            actual_no_shorts = no_shorts or (not create_short_form)
            actual_no_long_form = not create_long_form
            
            # Run the pipeline
            result = pipeline.run(
                max_expressions=max_expressions,
                dry_run=False,
                language_level=language_level,
                save_llm_output=True,
                test_mode=test_mode,
                no_shorts=actual_no_shorts,
                no_long_form=actual_no_long_form,
                short_form_max_duration=short_form_max_duration,
                schedule_upload=schedule_upload
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
        
        # Helper to get attribute from dict or object
        def get_attr(expr, key, default=None):
            if isinstance(expr, dict):
                return expr.get(key, default)
            return getattr(expr, key, default)
        
        for expression in expressions:
            processed.append({
                "expression": get_attr(expression, 'expression'),
                "translation": get_attr(expression, 'expression_translation'),
                "context": get_attr(expression, 'expression_dialogue'),
                "context_translation": get_attr(expression, 'expression_dialogue_translation'),
                "similar_expressions": get_attr(expression, 'similar_expressions', []),
                "start_time": get_attr(expression, 'context_start_time'),
                "end_time": get_attr(expression, 'context_end_time'),
                "expression_start_time": get_attr(expression, 'expression_start_time'),
                "expression_end_time": get_attr(expression, 'expression_end_time'),
                "difficulty": get_attr(expression, 'difficulty'),
                "category": get_attr(expression, 'category')
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
        short_videos = []
        
        # Collect all language directories to check
        dirs_to_check = []
        
        # 1. Primary language
        if 'language' in paths:
             dirs_to_check.append(paths['language'])
             
        # 2. All other languages
        if 'languages' in paths:
            for lang_paths in paths['languages'].values():
                dirs_to_check.append(lang_paths)
                
        logger.info(f"Checking for short videos in {len(dirs_to_check)} language directories")

        for lang_paths in dirs_to_check:
            short_videos_dir = lang_paths.get('short_videos')
            if short_videos_dir and isinstance(short_videos_dir, Path):
                logger.info(f"Scanning for shorts in: {short_videos_dir}")
                # Look for short videos (mkv files)
                # Exclude hidden files
                for video_file in short_videos_dir.glob("*.mkv"):
                    if video_file.exists() and not video_file.name.startswith('.'):
                        path_str = str(video_file)
                        if path_str not in short_videos:
                            short_videos.append(path_str)
                            logger.debug(f"Found short video: {video_file.name}")
                            
        logger.info(f"Total short videos found: {len(short_videos)}")
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
        # Collect checking directories
        dirs_to_check = []
        if 'language' in paths:
             dirs_to_check.append(paths['language'])
        if 'languages' in paths:
            for lang_paths in paths['languages'].values():
                dirs_to_check.append(lang_paths)
                
        for lang_paths in dirs_to_check:
             # Try finding in the 'long' directory first (new structure)
            long_dir = lang_paths.get('long')
            if long_dir and isinstance(long_dir, Path) and long_dir.exists():
                # Check for combined.mkv (standard name in VideoFactory)
                combined = long_dir / "combined.mkv"
                if combined.exists():
                    return str(combined)
                
                # Check for other patterns in long dir
                for video_file in long_dir.glob("*.mkv"):
                     if video_file.exists():
                         return str(video_file)

            # Fallback to legacy 'final_videos' directory
            final_videos_dir = lang_paths.get('final_videos')
            if final_videos_dir and isinstance(final_videos_dir, Path):
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

