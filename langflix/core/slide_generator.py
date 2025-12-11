#!/usr/bin/env python3
"""
Slide Generator for LangFlix
Creates educational slides with text overlays and audio

Extracted from video_editor.py as part of TICKET-090 refactoring.
"""

import ffmpeg
import logging
import os
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

from langflix.core.models import ExpressionAnalysis
from langflix.utils.filename_utils import sanitize_for_expression_filename
from langflix import settings

logger = logging.getLogger(__name__)


class SlideGenerator:
    """
    Generates educational slides with background, text overlays, and audio.
    
    This class handles:
    - Educational slide creation with expression text
    - TTS audio generation and timeline creation
    - Audio extraction from original video
    - Silence fallback generation
    """
    
    def __init__(
        self,
        output_dir: Path,
        language_code: str,
        episode_name: str,
        cache_manager,
        temp_manager,
        video_editor_ref=None
    ):
        """
        Initialize SlideGenerator.
        
        Args:
            output_dir: Directory for output files
            language_code: Target language code for font selection
            episode_name: Episode name for file naming
            cache_manager: Cache manager for TTS caching
            temp_manager: Temp file manager for cleanup
            video_editor_ref: Reference to parent VideoEditor for shared methods
        """
        self.output_dir = Path(output_dir)
        self.language_code = language_code
        self.episode_name = episode_name
        self.cache_manager = cache_manager
        self.temp_manager = temp_manager
        self._video_editor = video_editor_ref
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def _register_temp_file(self, file_path: Path):
        """Register a temporary file for cleanup later"""
        self.temp_manager.register(file_path)
    
    def _time_to_seconds(self, time_str: str) -> float:
        """
        Convert SRT timestamp to seconds.
        
        Args:
            time_str: Timestamp in format "HH:MM:SS,mmm" or "HH:MM:SS.mmm"
            
        Returns:
            Time in seconds as float
        """
        if not time_str:
            return 0.0
        
        # Replace comma with period for consistency
        time_str = time_str.replace(',', '.')
        
        try:
            parts = time_str.split(':')
            if len(parts) == 3:
                hours = int(parts[0])
                minutes = int(parts[1])
                seconds = float(parts[2])
                return hours * 3600 + minutes * 60 + seconds
            elif len(parts) == 2:
                minutes = int(parts[0])
                seconds = float(parts[1])
                return minutes * 60 + seconds
            else:
                return float(time_str)
        except (ValueError, IndexError):
            logger.warning(f"Could not parse timestamp: {time_str}")
            return 0.0
    
    def _get_font_option(self) -> str:
        """Get font file option for ffmpeg drawtext using language-specific font"""
        try:
            font_path = settings.get_font_path(self.language_code)
            if font_path and Path(font_path).exists():
                return f"fontfile='{font_path}':"
        except Exception as e:
            logger.warning(f"Error getting font path: {e}")
        return ""
    
    def _get_video_output_args(self, source_video_path: Optional[str] = None) -> Dict[str, Any]:
        """Get video output arguments from configuration"""
        try:
            return settings.get_video_output_config()
        except:
            return {
                'vcodec': 'libx264',
                'acodec': 'aac', 
                'preset': 'medium',
                'crf': 20
            }
    
    def _get_background_config(self) -> Tuple[str, str]:
        """
        Get background configuration with proper fallbacks for missing assets.
        
        Returns:
            Tuple of (background_input, input_type)
        """
        try:
            background_path = settings.get_slide_background()
            if background_path and Path(background_path).exists():
                return str(background_path), "image2"
        except:
            pass
        
        # Fallback to solid color
        return "color=c=0x1a1a2e:size=1280x720", "lavfi"
    
    def _get_cached_tts(self, text: str, expression_index: int):
        """Get cached TTS audio if available"""
        if self.cache_manager:
            cache_key = f"tts_{hash(text)}_{expression_index}"
            return self.cache_manager.get(cache_key)
        return None
    
    def _cache_tts(self, text: str, expression_index: int, tts_path: str, duration: float):
        """Cache TTS audio for reuse"""
        if self.cache_manager:
            cache_key = f"tts_{hash(text)}_{expression_index}"
            self.cache_manager.set(cache_key, (tts_path, duration))
    
    def _ensure_expression_dialogue(self, expression: ExpressionAnalysis) -> ExpressionAnalysis:
        """Ensure expression has dialogue fields for backward compatibility."""
        if not hasattr(expression, 'expression_dialogue') or not expression.expression_dialogue:
            expression.expression_dialogue = expression.expression
        
        if not hasattr(expression, 'expression_dialogue_translation') or not expression.expression_dialogue_translation:
            expression.expression_dialogue_translation = expression.expression_translation
        
        return expression
    
    def create_educational_slide(
        self,
        expression_source_video: str,
        expression: ExpressionAnalysis,
        expression_index: int = 0,
        target_duration: Optional[float] = None,
        use_expression_audio: bool = False,
        expression_video_clip_path: Optional[str] = None
    ) -> str:
        """
        Create educational slide with background image, text, and audio.
        
        This is the main entry point for slide generation, delegating to
        the parent VideoEditor's implementation for now to maintain
        backward compatibility.
        
        Args:
            expression_source_video: Source video path for audio extraction
            expression: ExpressionAnalysis object
            expression_index: Index for voice alternation
            target_duration: Target duration for slide
            use_expression_audio: If True, use expression video clip audio
            expression_video_clip_path: Path to expression video clip
            
        Returns:
            Path to the created slide video
        """
        # Delegate to VideoEditor's implementation
        # This allows gradual migration without breaking existing functionality
        if self._video_editor:
            return self._video_editor._create_educational_slide(
                expression_source_video,
                expression,
                expression_index,
                target_duration,
                use_expression_audio,
                expression_video_clip_path
            )
        
        raise RuntimeError("SlideGenerator requires a VideoEditor reference for now")
    
    def generate_tts_timeline(
        self,
        text: str,
        tts_client,
        provider_config: dict,
        tts_audio_dir: Path,
        expression_index: int = 0
    ) -> Tuple[Path, float]:
        """
        Generate TTS audio with timeline.
        
        Delegates to VideoEditor's implementation for now.
        """
        if self._video_editor:
            return self._video_editor._generate_tts_timeline(
                text, tts_client, provider_config, tts_audio_dir, expression_index
            )
        
        raise RuntimeError("SlideGenerator requires a VideoEditor reference for now")
    
    def create_timeline_from_tts(
        self,
        tts_path: str,
        tts_duration: float,
        tts_audio_dir: Path,
        expression_index: int
    ) -> Tuple[Path, float]:
        """
        Create timeline from existing TTS audio file.
        
        Delegates to VideoEditor's implementation for now.
        """
        if self._video_editor:
            return self._video_editor._create_timeline_from_tts(
                tts_path, tts_duration, tts_audio_dir, expression_index
            )
        
        raise RuntimeError("SlideGenerator requires a VideoEditor reference for now")
    
    def extract_original_audio_timeline(
        self,
        expression: ExpressionAnalysis,
        original_video_path: str,
        output_dir: Path,
        expression_index: int = 0,
        provider_config: dict = None,
        repeat_count: int = None
    ) -> Tuple[Path, float]:
        """
        Extract audio from original video and create repetition timeline.
        
        Delegates to VideoEditor's implementation for now.
        """
        if self._video_editor:
            return self._video_editor._extract_original_audio_timeline(
                expression, original_video_path, output_dir,
                expression_index, provider_config, repeat_count
            )
        
        raise RuntimeError("SlideGenerator requires a VideoEditor reference for now")
    
    def create_silence_fallback(
        self,
        expression: ExpressionAnalysis,
        output_dir: Path,
        expression_index: int = 0,
        provider_config: dict = None
    ) -> Tuple[Path, float]:
        """
        Create silence audio as fallback.
        
        Delegates to VideoEditor's implementation for now.
        """
        if self._video_editor:
            return self._video_editor._create_silence_fallback(
                expression, output_dir, expression_index, provider_config
            )
        
        raise RuntimeError("SlideGenerator requires a VideoEditor reference for now")
