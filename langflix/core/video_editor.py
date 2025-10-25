#!/usr/bin/env python3
"""
Video Editor for LangFlix
Creates educational video sequences with context, expression clips, and educational slides
"""

import ffmpeg
import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from .models import ExpressionAnalysis
from .cache_manager import get_cache_manager
from langflix import settings
from langflix.settings import get_expression_subtitle_styling

logger = logging.getLogger(__name__)

class VideoEditor:
    """
    Creates educational video sequences from expression analysis results
    """
    
    def __init__(self, output_dir: str = "output", language_code: str = None):
        """
        Initialize VideoEditor
        
        Args:
            output_dir: Directory for output files
            language_code: Target language code for font selection
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        self._temp_files = []  # Track temporary files for cleanup
        self._tts_cache = {}  # Legacy cache for backward compatibility
        self.cache_manager = get_cache_manager()  # Advanced cache manager
        self.language_code = language_code
        
        # Set up paths for different video types
        self.final_videos_dir = self.output_dir  # This will be final_videos
        self.context_slide_combined_dir = self.output_dir.parent / "context_slide_combined"
        self.short_videos_dir = self.output_dir.parent / "short_videos"
        
        # Ensure directories exist
        self.context_slide_combined_dir.mkdir(exist_ok=True)
        self.short_videos_dir.mkdir(exist_ok=True)
    
    @staticmethod
    def _ensure_expression_dialogue(expression: ExpressionAnalysis) -> ExpressionAnalysis:
        """
        Ensure expression has dialogue fields for backward compatibility.
        If fields are missing, fall back to using expression as dialogue.
        Handle edge cases like very long text and expression==dialogue.
        
        Args:
            expression: ExpressionAnalysis object
            
        Returns:
            ExpressionAnalysis with guaranteed dialogue fields
        """
        # Handle missing expression_dialogue with fallback
        if not hasattr(expression, 'expression_dialogue') or not expression.expression_dialogue:
            logger.warning(f"expression_dialogue missing for '{expression.expression}', using fallback")
            expression.expression_dialogue = expression.expression
        
        # Handle missing expression_dialogue_translation with fallback
        if not hasattr(expression, 'expression_dialogue_translation') or not expression.expression_dialogue_translation:
            logger.warning(f"expression_dialogue_translation missing, using fallback")
            expression.expression_dialogue_translation = expression.expression_translation
        
        # Edge case: If expression is the same as dialogue, avoid duplication in TTS
        if (expression.expression and expression.expression_dialogue and 
            expression.expression.strip() == expression.expression_dialogue.strip()):
            logger.info(f"Expression same as dialogue, will handle in TTS generation")
        
        # Edge case: Truncate very long dialogue lines for better slide display
        MAX_DIALOGUE_LENGTH = 120  # characters
        if len(expression.expression_dialogue) > MAX_DIALOGUE_LENGTH:
            logger.warning(f"Expression dialogue too long ({len(expression.expression_dialogue)} chars), truncating")
            expression.expression_dialogue = expression.expression_dialogue[:MAX_DIALOGUE_LENGTH] + "..."
        
        # Edge case: Truncate very long TTS text for provider limits
        MAX_TTS_CHARS = 500  # Adjust based on provider
        combined_text = f"{expression.expression_dialogue}. {expression.expression}"
        if len(combined_text) > MAX_TTS_CHARS:
            logger.warning(f"TTS text too long ({len(combined_text)} chars), will truncate in TTS generation")
        
        return expression
        
    def create_educational_sequence(self, expression: ExpressionAnalysis, 
                                  context_video_path: str, 
                                  expression_video_path: str, 
                                  expression_index: int = 0) -> str:
        """
        Create educational video sequence:
        1. Context video with subtitles (top: original, bottom: translation)
        2. Educational slide (background + text + audio 3x)
        
        Args:
            expression: ExpressionAnalysis object
            context_video_path: Path to context video
            expression_video_path: Path to expression video
            expression_index: Index of expression (for voice alternation)
            
        Returns:
            Path to created educational video
        """
        try:
            # Create output filename - save to context_slide_combined directory
            safe_expression = self._sanitize_filename(expression.expression)
            output_filename = f"educational_{safe_expression}.mkv"
            output_path = self.context_slide_combined_dir / output_filename
            
            logger.info(f"Creating educational sequence for: {expression.expression}")
            
            # Step 1: Create context video with dual-language subtitles
            context_with_subtitles = self._add_subtitles_to_context(
                context_video_path, expression
            )
            
            # Step 2: Create educational slide with background and 2x audio
            educational_slide = self._create_educational_slide(
                expression_video_path, expression, expression_index  # Use original video for expression audio and pass index
            )
            
            # Step 3: Concatenate the two parts
            final_video = self._concatenate_sequence([
                context_with_subtitles,
                educational_slide
            ], str(output_path))
            
            logger.info(f"Educational sequence created: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error creating educational sequence: {e}")
            raise
    
    def _sanitize_filename(self, text: str) -> str:
        """Sanitize text for filename"""
        import re
        # Remove special characters and replace spaces with underscores
        sanitized = re.sub(r'[^\w\s-]', '', text)
        sanitized = re.sub(r'[-\s]+', '_', sanitized)
        return sanitized[:50]  # Limit length
    
    def _get_font_option(self) -> str:
        """Get font file option for ffmpeg drawtext"""
        try:
            font_file = settings.get_font_file(self.language_code)
            # Ensure font_file is a string
            if isinstance(font_file, str) and font_file and os.path.exists(font_file):
                return f"fontfile={font_file}:"
        except Exception as e:
            logger.warning(f"Error getting font option: {e}")
        return ""
    
    def _get_video_output_args(self) -> dict:
        """Get video output arguments from configuration"""
        video_config = settings.get_video_config()
        return {
            'vcodec': video_config.get('codec', 'libx264'),
            'acodec': video_config.get('audio_codec', 'aac'),
            'preset': video_config.get('preset', 'fast'),
            'crf': video_config.get('crf', 23)
        }
    
    def _get_background_config(self) -> tuple[str, str]:
        """
        Get background configuration with proper fallbacks for missing assets.
        
        Returns:
            Tuple of (background_input, input_type)
        """
        import os
        
        # Try multiple possible background image locations with absolute paths
        possible_paths = [
            Path("assets/education_slide_background.png"),
            Path("assets/education_slide_background.jpg"),
            Path("assets/background.png"),
            Path("assets/background.jpg"),
            Path(".").absolute() / "assets" / "education_slide_background.png",
            Path(os.getcwd()) / "assets" / "education_slide_background.png",
            Path(__file__).parent.parent / "assets" / "education_slide_background.png",
        ]
        
        background_path = None
        for path in possible_paths:
            logger.info(f"Checking background path: {path} (exists: {path.exists()})")
            if path.exists():
                logger.info(f"Found background image: {path.absolute()}")
                background_path = path.absolute()
                break
        
        if background_path:
            logger.info(f"Using background image: {background_path}")
            return str(background_path), "image2"
        else:
            logger.warning("No background image found, using solid color fallback")
            logger.info("To add a custom background, place 'education_slide_background.png' in the assets/ directory")
            # Use a more appealing gradient background instead of solid black
            background_input = "color=c=0x1a1a2e:size=1920x1080"  # Dark blue gradient-like color
            return background_input, "lavfi"
    
    def _register_temp_file(self, file_path: Path) -> None:
        """Register a temporary file for cleanup later"""
        self._temp_files.append(file_path)
    
    def _get_subtitle_style_config(self) -> Dict[str, Any]:
        """Get subtitle styling configuration from expression settings"""
        try:
            styling_config = get_expression_subtitle_styling()
            return styling_config
        except Exception as e:
            logger.warning(f"Failed to load expression subtitle styling: {e}, using defaults")
            return {
                'default': {
                    'color': '#FFFFFF',
                    'font_size': 24,
                    'font_weight': 'normal',
                    'background_color': '#000000',
                    'background_opacity': 0.7
                },
                'expression_highlight': {
                    'color': '#FFD700',
                    'font_size': 28,
                    'font_weight': 'bold',
                    'background_color': '#1A1A1A',
                    'background_opacity': 0.85
                }
            }
    
    def _convert_color_to_ass(self, color_hex: str) -> str:
        """Convert hex color to ASS format (BGR format)"""
        # Remove # if present
        color_hex = color_hex.lstrip('#')
        # Convert to BGR format for ASS
        r = int(color_hex[0:2], 16)
        g = int(color_hex[2:4], 16)
        b = int(color_hex[4:6], 16)
        # ASS uses BGR format
        return f"&H{b:02x}{g:02x}{r:02x}"
    
    def _generate_subtitle_style_string(self, is_expression: bool = False) -> str:
        """Generate ASS style string from expression configuration"""
        styling_config = self._get_subtitle_style_config()
        
        if is_expression:
            style_config = styling_config.get('expression_highlight', {})
        else:
            style_config = styling_config.get('default', {})
        
        # Extract style properties
        color = style_config.get('color', '#FFFFFF')
        font_size = style_config.get('font_size', 24)
        font_weight = style_config.get('font_weight', 'normal')
        background_color = style_config.get('background_color', '#000000')
        background_opacity = style_config.get('background_opacity', 0.7)
        
        # Convert colors to ASS format
        primary_color = self._convert_color_to_ass(color)
        outline_color = self._convert_color_to_ass(background_color)
        
        # Calculate outline width based on font size
        outline_width = max(2, font_size // 12)
        
        # Generate ASS style string
        style_parts = [
            f"FontSize={font_size}",
            f"PrimaryColour={primary_color}",
            f"OutlineColour={outline_color}",
            f"Outline={outline_width}",
            f"Bold={1 if font_weight == 'bold' else 0}",
            f"BackColour={primary_color}",
            f"BorderStyle=3"
        ]
        
        return ",".join(style_parts)
    
    def _get_tts_cache_key(self, text: str, expression_index: int) -> str:
        """Generate cache key for TTS audio"""
        # Normalize text to ensure consistent cache keys
        normalized_text = text.strip()
        return f"{normalized_text}_{expression_index}"
    
    def _get_cached_tts(self, text: str, expression_index: int) -> Optional[Tuple[str, float]]:
        """Get cached TTS audio if available (enhanced with advanced cache)"""
        # Try advanced cache first
        cache_key = self.cache_manager.get_tts_key(text, "default", "en", expression_index)
        cached_data = self.cache_manager.get(cache_key)
        
        if cached_data and isinstance(cached_data, dict):
            tts_path = cached_data.get('path')
            duration = cached_data.get('duration')
            if tts_path and Path(tts_path).exists():
                logger.info(f"✅ Using advanced cached TTS for: '{text}' (duration: {duration:.2f}s)")
                return tts_path, duration
        
        # Fallback to legacy cache
        legacy_cache_key = self._get_tts_cache_key(text, expression_index)
        logger.info(f"Checking legacy cache for key: '{legacy_cache_key}' (text: '{text}', index: {expression_index})")
        logger.info(f"Current legacy cache keys: {list(self._tts_cache.keys())}")
        
        if legacy_cache_key in self._tts_cache:
            cached_path, duration = self._tts_cache[legacy_cache_key]
            if Path(cached_path).exists():
                logger.info(f"✅ Using legacy cached TTS for: '{text}' (duration: {duration:.2f}s)")
                return cached_path, duration
            else:
                # Remove invalid cache entry
                logger.warning(f"❌ Cached file not found, removing from cache: {cached_path}")
                del self._tts_cache[legacy_cache_key]
        else:
            logger.info(f"❌ No cache found for key: '{legacy_cache_key}'")
        return None
    
    def _cache_tts(self, text: str, expression_index: int, tts_path: str, duration: float) -> None:
        """Cache TTS audio for reuse (enhanced with advanced cache)"""
        # Cache in advanced cache manager
        cache_key = self.cache_manager.get_tts_key(text, "default", "en", expression_index)
        cache_data = {
            'path': tts_path,
            'duration': duration,
            'text': text,
            'expression_index': expression_index
        }
        self.cache_manager.set(cache_key, cache_data, ttl=86400, persist_to_disk=True)  # 24 hours
        
        # Also cache in legacy cache for backward compatibility
        legacy_cache_key = self._get_tts_cache_key(text, expression_index)
        self._tts_cache[legacy_cache_key] = (tts_path, duration)
        logger.info(f"💾 Cached TTS for: '{text}' (duration: {duration:.2f}s) with key: '{legacy_cache_key}'")
    
    def _create_timeline_from_tts(self, tts_path: str, tts_duration: float, tts_audio_dir: Path, expression_index: int) -> Tuple[Path, float]:
        """Create timeline from existing TTS audio file"""
        try:
            from langflix import settings
            
            # Get repeat count from settings
            repeat_count = settings.get_tts_repeat_count()
            
            # Create timeline: 1 sec pause - TTS - 0.5 sec pause - TTS - ... - 1 sec pause
            pause_duration = 1.0
            gap_duration = 0.5
            
            # Calculate total duration
            total_duration = pause_duration + (tts_duration * repeat_count) + (gap_duration * (repeat_count - 1)) + pause_duration
            
            # Create timeline audio file
            timeline_filename = f"timeline_{self._sanitize_filename(tts_path.split('/')[-1])}"
            timeline_path = tts_audio_dir / timeline_filename
            
            # Build FFmpeg filter for timeline
            filters = []
            
            # Start with 1 second pause
            filters.append(f"anullsrc=duration={pause_duration}")
            
            # Add TTS repetitions with gaps
            for i in range(repeat_count):
                filters.append(f"amovie={tts_path}")
                if i < repeat_count - 1:  # Add gap between repetitions (except after last)
                    filters.append(f"anullsrc=duration={gap_duration}")
            
            # End with 1 second pause
            filters.append(f"anullsrc=duration={pause_duration}")
            
            # Concatenate all audio segments
            filter_complex = "concat=n=" + str(len(filters)) + ":v=0:a=1[out]"
            
            # Apply the filter
            (
                ffmpeg
                .filter_complex(filter_complex, *filters)
                .output(str(timeline_path), map='[out]', acodec='pcm_s16le', ar=44100)
                .overwrite_output()
                .run(quiet=True)
            )
            
            logger.info(f"Created timeline from cached TTS: {total_duration:.2f}s")
            return timeline_path, total_duration
            
        except Exception as e:
            logger.error(f"Error creating timeline from cached TTS: {e}")
            raise
    
    def _cleanup_temp_files(self) -> None:
        """Clean up all registered temporary files"""
        for temp_file in self._temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
                    logger.debug(f"Cleaned up temporary file: {temp_file}")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary file {temp_file}: {e}")
        self._temp_files.clear()
    
    def __del__(self):
        """Ensure temporary files are cleaned up when object is destroyed"""
        try:
            self._cleanup_temp_files()
        except Exception:
            pass  # Ignore errors during cleanup in destructor
    
    def _add_subtitles_to_context(self, video_path: str, expression: ExpressionAnalysis) -> str:
        """Add target language subtitles to context video (translation only)"""
        try:
            # Save to context_videos directory instead of temp
            context_videos_dir = self.output_dir.parent / "context_videos"
            context_videos_dir.mkdir(exist_ok=True)
            
            safe_name = self._sanitize_filename(expression.expression)
            output_path = context_videos_dir / f"context_{safe_name}.mkv"
            
            # Find the corresponding subtitle file
            subtitle_file = self._find_subtitle_file_for_expression(expression)
            
            if subtitle_file and Path(subtitle_file).exists():
                logger.info(f"Using subtitle file: {subtitle_file}")
                
                try:
                    # Create a temporary dual-language subtitle file 
                    import tempfile
                    temp_dir = Path(tempfile.gettempdir())
                    temp_subtitle_file = temp_dir / f"temp_dual_lang_{self._sanitize_filename(expression.expression)}.srt"
                    self._register_temp_file(temp_subtitle_file)
                    self._create_dual_language_subtitle_file(subtitle_file, temp_subtitle_file)
                    
                    # Add subtitles using the subtitle file with expression styling
                    subtitle_style = self._generate_subtitle_style_string(is_expression=False)
                    logger.info(f"Using subtitle style: {subtitle_style}")
                    
                    (
                        ffmpeg
                        .input(str(video_path))
                        .output(str(output_path),
                               vf=f"subtitles={temp_subtitle_file}:force_style='{subtitle_style}'",
                               vcodec='libx264',
                               acodec='copy',
                               preset='fast')
                        .overwrite_output()
                        .run(quiet=True)
                    )
                    
                    logger.info(f"Successfully added target language subtitles to context video")
                    
                    # Clean up temp file
                    if temp_subtitle_file.exists():
                        temp_subtitle_file.unlink()
                        
                except Exception as subtitle_file_error:
                    logger.warning(f"Subtitle file overlay failed: {subtitle_file_error}, trying drawtext fallback")
                    self._fallback_drawtext_subtitles(video_path, output_path, expression)
                    
            else:
                logger.warning(f"Subtitle file not found for expression: {expression.expression}")
                self._fallback_drawtext_subtitles(video_path, output_path, expression)
            
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error adding subtitles to context: {e}")
            raise
    
    def _find_subtitle_file_for_expression(self, expression: ExpressionAnalysis) -> str:
        """Find the subtitle file for a specific expression using exact matching"""
        try:
            # Build the safe expression name the same way as in main.py
            safe_expression = "".join(c for c in expression.expression if c.isalnum() or c in (' ', '-', '_')).rstrip()
            
            # Build exact path based on output structure
            # Format: output/Series/Episode/translations/{lang}/subtitles/expression_XX_{expression}.srt
            # self.output_dir is translations/{lang}/final_videos, so subtitles is at self.output_dir.parent / "subtitles"
            subtitle_dir = self.output_dir.parent / "subtitles"
            
            logger.info(f"Looking for subtitle files in: {subtitle_dir}")
            logger.info(f"Expression: '{expression.expression}'")
            logger.info(f"Safe expression: '{safe_expression}'")
            
            # Check if subtitle directory exists
            if not subtitle_dir.exists():
                logger.warning(f"Subtitle directory does not exist: {subtitle_dir}")
                return None
            
            # List all subtitle files in the directory for debugging
            try:
                all_subtitle_files = list(subtitle_dir.glob("*.srt"))
                logger.info(f"Available subtitle files: {[f.name for f in all_subtitle_files]}")
            except Exception as e:
                logger.warning(f"Could not list subtitle files: {e}")
            
            # Search for files that match the expected pattern
            import glob
            import re
            
            # Create multiple search strategies
            sanitized_expr = self._sanitize_filename(expression.expression)
            patterns = [
                # Strategy 1: Try exact match with index prefix
                str(subtitle_dir / f"expression_*_{safe_expression[:30]}.srt"),
                # Strategy 2: Try exact match without index
                str(subtitle_dir / f"expression_{safe_expression[:30]}.srt"),
                # Strategy 3: Try sanitized name with index
                str(subtitle_dir / f"expression_*_{sanitized_expr}.srt"),
                # Strategy 4: Try sanitized name without index
                str(subtitle_dir / f"expression_{sanitized_expr}.srt"),
            ]
            
            # Strategy 5: Try partial matching for cases where filename is truncated
            # Look for files that contain a significant part of the expression
            all_files = list(subtitle_dir.glob("expression_*.srt"))
            for file_path in all_files:
                filename_without_ext = file_path.stem
                # Extract the expression part after "expression_XX_"
                match = re.match(r'expression_\d+_(.+)', filename_without_ext)
                if match:
                    file_expr_part = match.group(1)
                    # Check if the file expression is a significant substring of our expression
                    if (file_expr_part in safe_expression or 
                        safe_expression[:len(file_expr_part)] == file_expr_part or
                        file_expr_part in sanitized_expr or
                        sanitized_expr[:len(file_expr_part)] == file_expr_part):
                        logger.info(f"Found potential match via partial matching: {file_path}")
                        return str(file_path)
            
            logger.info(f"Search patterns: {patterns}")
            
            for pattern in patterns:
                matches = glob.glob(pattern)
                logger.info(f"Pattern '{pattern}' found matches: {matches}")
                if matches:
                    # Return the first match, prefer numbered ones
                    matches.sort()  # This will put expression_01 before expression_02, etc.
                    selected_file = matches[0]
                    logger.info(f"Selected subtitle file: {selected_file}")
                    return selected_file
            
            logger.warning(f"Could not find subtitle file for expression: {expression.expression}")
            logger.warning(f"Searched in: {subtitle_dir}")
            logger.warning(f"Tried patterns: {patterns}")
            return None
        except Exception as e:
            logger.error(f"Error finding subtitle file: {e}")
            return None
    
    def _create_dual_language_subtitle_file(self, source_subtitle_file: str, target_subtitle_file: Path) -> None:
        """Create a subtitle file with both original and target language from the validated source"""
        try:
            # Since we have validation that ensures dialogue and translation counts match,
            # we should just copy the dual-language subtitle file as-is
            with open(source_subtitle_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Copy the content directly - validation should have ensured proper format
            with open(target_subtitle_file, 'w', encoding='utf-8') as f:
                f.write(content)
                
            logger.info(f"Created dual-language subtitle file for context: {target_subtitle_file}")
                
        except Exception as e:
            logger.error(f"Error creating dual-language subtitle file: {e}")
            raise
    
    def _fallback_drawtext_subtitles(self, video_path: str, output_path: Path, expression: ExpressionAnalysis) -> None:
        """Fallback method using drawtext for simple subtitle overlay"""
        try:
            # Get translation text only (target language)
            translation_text = ""
            if expression.translation and len(expression.translation) > 0:
                translation_text = expression.translation[0]
            else:
                translation_text = expression.expression_translation
            
            # Clean text for ffmpeg
            def clean_text_for_ffmpeg(text):
                cleaned = text.replace("'", "").replace('"', "").replace("\n", " ")
                cleaned = "".join(c for c in cleaned if c.isprintable())
                # Increased limit to prevent text cutoff - 200 chars should be sufficient for most expressions
                return cleaned[:200] if cleaned else "Translation"
            
            clean_translation = clean_text_for_ffmpeg(translation_text)
            
            # Simple drawtext overlay for target language only with expression styling
            font_file_option = self._get_font_option()
            
            video_args = self._get_video_output_args()
            
            # Get styling configuration
            styling_config = self._get_subtitle_style_config()
            default_style = styling_config.get('default', {})
            
            font_size = default_style.get('font_size', settings.get_font_size())
            font_color = default_style.get('color', '#FFFFFF')
            
            # Convert hex color to ffmpeg format
            color_hex = font_color.lstrip('#')
            r = int(color_hex[0:2], 16)
            g = int(color_hex[2:4], 16)
            b = int(color_hex[4:6], 16)
            ffmpeg_color = f"0x{b:02x}{g:02x}{r:02x}"
            
            subtitle_filter = (
                f"drawtext=text='{clean_translation}':fontsize={font_size}:fontcolor={ffmpeg_color}:"
                f"{font_file_option}"
                f"x=(w-text_w)/2:y=h-70"
            )
            
            (
                ffmpeg
                .input(str(video_path))
                .output(str(output_path), 
                       vf=subtitle_filter,
                       vcodec=video_args['vcodec'],
                       acodec='copy',  # Keep original audio for subtitle overlay
                       preset=video_args['preset'])
                .overwrite_output()
                .run(quiet=True)
            )
            
            logger.info("Successfully added target language subtitles using drawtext fallback")
            
        except Exception as drawtext_error:
            logger.warning(f"Drawtext fallback failed: {drawtext_error}, using original video")
            # Final fallback: just copy the original video
            (
                ffmpeg
                .input(str(video_path))
                .output(str(output_path), 
                       vcodec='copy',
                       acodec='copy')
                .overwrite_output()
                .run(quiet=True)
            )
    
    def _create_expression_clip(self, video_path: str, expression: ExpressionAnalysis) -> str:
        """Create short expression clip (expression part only)"""
        try:
            # For now, use the full video as expression clip
            # TODO: Implement precise expression timing extraction
            output_path = self.output_dir / f"temp_expression_{self._sanitize_filename(expression.expression)}.mkv"
            
            # Copy video as-is for now
            (
                ffmpeg
                .input(str(video_path))
                .output(str(output_path), 
                       vcodec='copy',
                       acodec='copy')
                .overwrite_output()
                .run(quiet=True)
            )
            
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error creating expression clip: {e}")
            raise
    
    def _create_educational_slide(self, expression_source_video: str, expression: ExpressionAnalysis, expression_index: int = 0) -> str:
        """Create educational slide with background image, text, and TTS audio 2x"""
        try:
            # Ensure backward compatibility for expression_dialogue fields
            expression = self._ensure_expression_dialogue(expression)
            
            output_path = self.output_dir / f"temp_slide_{self._sanitize_filename(expression.expression)}.mkv"
            self._register_temp_file(output_path)
            
            # Get background configuration with proper fallbacks
            background_input, input_type = self._get_background_config()
            
            # Generate TTS audio using only expression_dialogue
            tts_text = expression.expression_dialogue
            logger.info(f"Generating TTS audio for: '{tts_text}'")
            
            # Edge case: Truncate if too long for TTS provider
            MAX_TTS_CHARS = 500  # Adjust based on provider
            if len(tts_text) > MAX_TTS_CHARS:
                logger.warning(f"TTS text too long ({len(tts_text)} chars), truncating to {MAX_TTS_CHARS}")
                tts_text = tts_text[:MAX_TTS_CHARS]
            
            # Import TTS modules
            from langflix.tts.factory import create_tts_client
            from langflix import settings
            
            # Get TTS configuration with validation
            tts_config = settings.get_tts_config()
            if not tts_config:
                raise ValueError("TTS configuration is not available")
            
            provider = settings.get_tts_provider()
            if not provider:
                raise ValueError("TTS provider is not configured")
            
            provider_config = tts_config.get(provider, {})
            if not provider_config:
                raise ValueError(f"Configuration for TTS provider '{provider}' is not found")
            
            logger.info(f"Using TTS provider: {provider}")
            logger.info(f"Provider config keys: {list(provider_config.keys())}")
            
            # Create TTS audio directory for permanent storage
            tts_audio_dir = self.output_dir.parent / "tts_audio"
            tts_audio_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"TTS audio directory: {tts_audio_dir}")
            
            # Check if TTS is enabled and decide on audio workflow
            if settings.is_tts_enabled():
                try:
                    # TTS Workflow: Generate synthetic speech
                    logger.info("TTS is enabled - using synthetic speech")
                    logger.info("Creating TTS client...")
                    tts_client = create_tts_client(provider, provider_config)
                    
                    # Generate timeline with voice alternation: 1 sec pause - TTS - 0.5 sec pause - TTS - 0.5 sec pause - TTS - 1 sec pause
                    logger.info(f"Generating TTS timeline for: '{tts_text}' (expression index: {expression_index})")
                    audio_path, expression_duration = self._generate_tts_timeline(
                        tts_text, tts_client, provider_config, tts_audio_dir, expression_index
                    )
                    
                    logger.info(f"Generated TTS timeline duration: {expression_duration:.2f}s")
                    
                except Exception as tts_error:
                    logger.error(f"Error generating TTS audio: {tts_error}")
                    logger.error(f"TTS Error details: {tts_error}")
                    
                    # Fallback to original audio when TTS fails
                    logger.warning("TTS failed, falling back to original audio extraction")
                    audio_path, expression_duration = self._extract_original_audio_timeline(
                        expression, expression_source_video, tts_audio_dir, expression_index, provider_config
                    )
            else:
                # Original Audio Workflow: Extract from source video
                logger.info("TTS is disabled - using original audio extraction")
                audio_path, expression_duration = self._extract_original_audio_timeline(
                    expression, expression_source_video, tts_audio_dir, expression_index, provider_config
                )
            
            # Use the timeline audio directly (no need for 2x conversion since timeline is already complete)
            audio_2x_path = audio_path  # The timeline already includes 2 TTS segments with pauses
            slide_duration = expression_duration + 0.5  # Add small padding for slide
            
            logger.info(f"Using timeline audio directly: {audio_2x_path}")
            logger.info(f"Timeline duration: {expression_duration:.2f}s")
            
            # Clean text properly for educational slide (remove special characters including underscores)
            def clean_text_for_slide(text):
                """Clean text for slide display, removing special characters"""
                if not isinstance(text, str):
                    text = str(text)
                
                # Replace problematic characters for FFmpeg drawtext
                cleaned = text.replace("'", "").replace('"', "").replace(":", "").replace(",", "")
                cleaned = cleaned.replace("\\", "").replace("[", "").replace("]", "")
                cleaned = cleaned.replace("{", "").replace("}", "").replace("(", "").replace(")", "")
                cleaned = cleaned.replace("\n", " ").replace("\t", " ")
                
                # Remove other problematic characters for drawtext (preserve "/" for alternatives like "estafado/perjudicado")
                cleaned = "".join(c for c in cleaned if c.isprintable() and c not in "@#$%^&*+=|<>")
                
                # Proper spacing and length limit
                cleaned = " ".join(cleaned.split())  # Remove extra spaces
                # Increased limit to prevent text cutoff - 100 chars should be sufficient for expressions
                return cleaned[:100] if cleaned else "Expression"
            
            def escape_drawtext_string(text):
                """Escape text for FFmpeg drawtext filter"""
                # Escape single quotes and colons for drawtext
                return text.replace(":", "\\:").replace("'", "\\'")
            
            # Prepare text content with proper cleaning
            # NEW: Add expression_dialogue and expression_dialogue_translation
            expression_dialogue_raw = clean_text_for_slide(expression.expression_dialogue)
            expression_text_raw = clean_text_for_slide(expression.expression)
            expression_dialogue_trans_raw = clean_text_for_slide(expression.expression_dialogue_translation)
            translation_text_raw = clean_text_for_slide(expression.expression_translation)
            
            # Escape for drawtext filter
            expression_dialogue = escape_drawtext_string(expression_dialogue_raw)
            expression_text = escape_drawtext_string(expression_text_raw)
            expression_dialogue_trans = escape_drawtext_string(expression_dialogue_trans_raw)
            translation_text = escape_drawtext_string(translation_text_raw)
            
            # Prepare similar expressions (max 2) - handle different data types safely
            similar_expressions = []
            if hasattr(expression, 'similar_expressions') and expression.similar_expressions:
                raw_similar = expression.similar_expressions
                if isinstance(raw_similar, list):
                    # Extract strings from list, handling mixed types
                    for item in raw_similar[:2]:
                        if isinstance(item, str):
                            similar_expressions.append(item)
                        elif isinstance(item, dict):
                            # If it's a dict, try to extract text from common keys
                            text = item.get('text') or item.get('expression') or item.get('value') or str(item)
                            similar_expressions.append(str(text))
                        else:
                            similar_expressions.append(str(item))
                else:
                    # Handle single item or other types
                    similar_expressions.append(str(raw_similar))
            
            logger.info(f"Creating slide with:")
            logger.info(f"  - expression_dialogue: '{expression_dialogue}'")
            logger.info(f"  - expression: '{expression_text}'")
            logger.info(f"  - dialogue_translation: '{expression_dialogue_trans}'")
            logger.info(f"  - expression_translation: '{translation_text}'")
            if similar_expressions:
                logger.info(f"  - similar_expressions: {similar_expressions}")
            
            # Create slide with NEW 5-section layout:
            # 1. Expression dialogue (full sentence): upper area
            # 2. Expression (key phrase): highlighted, below dialogue
            # 3. Visual separator
            # 4. Expression dialogue translation: middle area
            # 5. Expression translation (key phrase): highlighted, below dialogue translation
            # 6. Similar expressions: bottom (if available)
            
            try:
                # Build drawtext filters for proper layout
                drawtext_filters = []
                
                # Get font option safely
                try:
                    font_file_option = self._get_font_option()
                    if not isinstance(font_file_option, str):
                        font_file_option = str(font_file_option) if font_file_option else ""
                except Exception as e:
                    logger.warning(f"Error getting font option: {e}")
                    font_file_option = ""
                
                # Safe font size retrieval with NEW font size keys
                try:
                    dialogue_font_size = settings.get_font_size('expression_dialogue')
                    if not isinstance(dialogue_font_size, (int, float)):
                        dialogue_font_size = 40
                except:
                    dialogue_font_size = 40
                
                try:
                    expr_font_size = settings.get_font_size('expression')
                    if not isinstance(expr_font_size, (int, float)):
                        expr_font_size = 58
                except:
                    expr_font_size = 58
                    
                try:
                    dialogue_trans_font_size = settings.get_font_size('expression_dialogue_trans')
                    if not isinstance(dialogue_trans_font_size, (int, float)):
                        dialogue_trans_font_size = 36
                except:
                    dialogue_trans_font_size = 36
                
                try:
                    trans_font_size = settings.get_font_size('expression_trans')
                    if not isinstance(trans_font_size, (int, float)):
                        trans_font_size = 48
                except:
                    trans_font_size = 48
                
                # 1. Expression dialogue (full sentence) - upper area
                if expression_dialogue and isinstance(expression_dialogue, str):
                    drawtext_filters.append(
                        f"drawtext=text='{expression_dialogue}':fontsize={dialogue_font_size}:fontcolor=white:"
                        f"{font_file_option}"
                        f"x=(w-text_w)/2:y=h/2-220:"
                        f"borderw=2:bordercolor=black"
                    )
                
                # 2. Expression (key phrase) - highlighted in yellow, below dialogue
                if expression_text and isinstance(expression_text, str):
                    drawtext_filters.append(
                        f"drawtext=text='{expression_text}':fontsize={expr_font_size}:fontcolor=yellow:"
                        f"{font_file_option}"
                        f"x=(w-text_w)/2:y=h/2-150:"
                        f"borderw=3:bordercolor=black"
                    )
                
                # 3. Expression dialogue translation - middle area
                if expression_dialogue_trans and isinstance(expression_dialogue_trans, str):
                    drawtext_filters.append(
                        f"drawtext=text='{expression_dialogue_trans}':fontsize={dialogue_trans_font_size}:fontcolor=white:"
                        f"{font_file_option}"
                        f"x=(w-text_w)/2:y=h/2:"
                        f"borderw=2:bordercolor=black"
                    )
                
                # 4. Expression translation (key phrase) - highlighted in yellow
                if translation_text and isinstance(translation_text, str):
                    drawtext_filters.append(
                        f"drawtext=text='{translation_text}':fontsize={trans_font_size}:fontcolor=yellow:"
                        f"{font_file_option}"
                        f"x=(w-text_w)/2:y=h/2+70:"
                        f"borderw=3:bordercolor=black"
                    )
                
                # 5. Similar expressions (bottom area, positioned higher and with line breaks)
                if similar_expressions:
                    # Ensure all items are strings before processing
                    safe_similar = []
                    for sim in similar_expressions:
                        try:
                            if isinstance(sim, str):
                                safe_similar.append(clean_text_for_slide(sim))
                            elif isinstance(sim, dict):
                                # Extract text from dict safely
                                text = sim.get('text') or sim.get('expression') or sim.get('value', '')
                                if text:
                                    safe_similar.append(clean_text_for_slide(str(text)))
                            else:
                                safe_similar.append(clean_text_for_slide(str(sim)))
                        except Exception as e:
                            logger.warning(f"Could not process similar expression {sim}: {e}")
                            continue
                    
                    # Safe font size retrieval
                    try:
                        similar_font_size = settings.get_font_size('similar')
                    except:
                        similar_font_size = 32
                    
                    # Add each similar expression as a separate drawtext for proper line spacing
                    base_y = 160  # Distance from bottom (moved 3% lower: 130 -> 160)
                    line_spacing = 40  # Space between lines
                    
                    for i, similar_text in enumerate(safe_similar[:2]):  # Limit to 2 expressions
                        if similar_text:
                            similar_text_escaped = escape_drawtext_string(similar_text)
                            y_position = f"h-{base_y + (i * line_spacing)}"
                            drawtext_filters.append(
                                f"drawtext=text='{similar_text_escaped}':fontsize={similar_font_size}:fontcolor=white:"
                                f"{font_file_option}"
                                f"x=(w-text_w)/2:y={y_position}:"
                                f"borderw=1:bordercolor=black"
                            )
                
                # Combine all text filters
                video_filter = ",".join(drawtext_filters)
                
                logger.info("Creating educational slide with text overlay and TTS audio...")
                
                # Create video input based on background type
                if input_type == "image2":
                    video_input = ffmpeg.input(background_input, loop=1, t=slide_duration, f=input_type)
                else:
                    video_input = ffmpeg.input(background_input, f=input_type, t=slide_duration)
                
                # Debug: Check if audio file exists and has content
                if not audio_2x_path.exists():
                    logger.error(f"2x audio file does not exist: {audio_2x_path}")
                    raise FileNotFoundError(f"2x audio file missing: {audio_2x_path}")
                
                audio_file_size = audio_2x_path.stat().st_size
                logger.info(f"Using 2x audio file: {audio_2x_path} (size: {audio_file_size} bytes)")
                
                # Add the 2x TTS audio input
                audio_input = ffmpeg.input(str(audio_2x_path))
                
                logger.info(f"Creating slide with video duration: {slide_duration}s, audio file: {audio_2x_path}")
                
                # Create the slide with both video and audio directly
                try:
                    (
                        ffmpeg
                        .output(video_input['v'], audio_input['a'], str(output_path),
                               vf=f"scale=1280:720,{video_filter}",
                               vcodec='libx264',
                               acodec='aac',
                               t=slide_duration,
                               preset='fast',
                               crf=23)
                        .overwrite_output()
                        .run(capture_stdout=True, capture_stderr=True)
                    )
                    logger.info(f"Successfully created slide with audio: {output_path}")
                    
                    # Verify the output file has audio streams
                    import subprocess
                    result = subprocess.run(['ffprobe', '-v', 'quiet', '-select_streams', 'a', '-show_entries', 'stream=codec_name', '-of', 'csv=p=0', str(output_path)], capture_output=True, text=True)
                    if result.stdout.strip():
                        logger.info(f"Slide video has audio stream: {result.stdout.strip()}")
                    else:
                        logger.warning(f"Slide video may not have audio stream: {output_path}")
                        
                except Exception as ffmpeg_error:
                    logger.error(f"FFmpeg error creating slide: {ffmpeg_error}")
                    raise
                
                logger.info("Educational slide created successfully with text overlay")
                    
            except Exception as slide_error:
                logger.error(f"Failed to create slide with text overlay: {slide_error}")
                logger.info("Creating fallback slide without text...")
                
                # Fallback: create slide without text overlay but with audio
                logger.warning("Creating fallback slide without text overlay due to error")
                try:
                    if input_type == "image2":
                        video_input = ffmpeg.input(background_input, loop=1, t=slide_duration, f=input_type)
                    else:
                        video_input = ffmpeg.input(background_input, f=input_type, t=slide_duration)
                    
                    audio_input = ffmpeg.input(str(audio_2x_path))
                    
                    (
                        ffmpeg
                        .output(video_input['v'], audio_input['a'], str(output_path),
                               vf="scale=1280:720",
                               vcodec='libx264',
                               acodec='aac',
                               t=slide_duration,
                               preset='fast',
                               crf=23)
                        .overwrite_output()
                        .run(capture_stdout=True, capture_stderr=True)
                    )
                except Exception as fallback_error:
                    logger.error(f"Even fallback slide creation failed: {fallback_error}")
                    # Final emergency fallback - basic slide with audio
                    try:
                        video_input = ffmpeg.input("color=c=0x1a1a2e:size=1280:720", f="lavfi", t=slide_duration)
                        audio_input = ffmpeg.input(str(audio_2x_path))
                        
                        (
                            ffmpeg
                            .output(video_input['v'], audio_input['a'], str(output_path),
                                   vcodec='libx264',
                                   acodec='aac',
                                   preset='fast',
                                   crf=23)
                            .overwrite_output()
                            .run(quiet=True)
                        )
                    except Exception as emergency_error:
                        logger.error(f"Emergency fallback also failed: {emergency_error}")
                        # Last resort: create basic video without audio
                        (
                            ffmpeg
                            .input("color=c=0x1a1a2e:size=1280:720", f="lavfi", t=slide_duration)
                            .output(str(output_path),
                                   vcodec='libx264',
                                   acodec='aac',
                                   preset='fast',
                                   crf=23)
                            .overwrite_output()
                            .run(quiet=True)
                        )
            
            # Move temp slide to final location in slides directory
            slides_dir = self.output_dir.parent / "slides"
            slides_dir.mkdir(exist_ok=True)
            final_slide_path = slides_dir / f"slide_{self._sanitize_filename(expression.expression)}.mkv"
            
            try:
                # Copy the slide (which now already includes audio) to final location
                import shutil
                shutil.copy2(str(output_path), str(final_slide_path))
                logger.info(f"Successfully created educational slide with TTS audio: {final_slide_path}")
            except Exception as copy_error:
                logger.error(f"Error copying slide to final location: {copy_error}")
                # Return the temp file path as fallback
                final_slide_path = output_path
            
            return str(final_slide_path)
            
        except Exception as e:
            logger.error(f"Error creating educational slide: {e}")
            raise
    
    def _create_educational_slide_silent(self, expression: ExpressionAnalysis, duration: float) -> str:
        """Create educational slide with background image and text, but without audio"""
        try:
            # Ensure backward compatibility for expression_dialogue fields
            expression = self._ensure_expression_dialogue(expression)
            
            output_path = self.output_dir / f"temp_slide_silent_{self._sanitize_filename(expression.expression)}.mkv"
            self._register_temp_file(output_path)
            
            # Get background configuration with proper fallbacks
            background_input, input_type = self._get_background_config()
            
            logger.info(f"Creating silent slide for: {expression.expression} (duration: {duration:.2f}s)")
            logger.info(f"Dialogue: {expression.expression_dialogue}")
            
            # Clean text properly for educational slide (remove special characters including underscores)
            def clean_text_for_slide(text):
                """Clean text for slide display, removing special characters"""
                if not isinstance(text, str):
                    text = str(text)
                
                # Replace problematic characters for FFmpeg drawtext
                cleaned = text.replace("'", "").replace('"', "").replace(":", "").replace(",", "")
                cleaned = cleaned.replace("\\", "").replace("[", "").replace("]", "")
                cleaned = cleaned.replace("{", "").replace("}", "").replace("(", "").replace(")", "")
                cleaned = cleaned.replace("\n", " ").replace("\t", " ")
                
                # Remove other problematic characters for drawtext (preserve "/" for alternatives like "estafado/perjudicado")
                cleaned = "".join(c for c in cleaned if c.isprintable() and c not in "@#$%^&*+=|<>")
                
                # Proper spacing and length limit
                cleaned = " ".join(cleaned.split())  # Remove extra spaces
                return cleaned[:100] if cleaned else "Expression"
            
            def escape_drawtext_string(text):
                """Escape text for FFmpeg drawtext filter"""
                # Escape single quotes and colons for drawtext
                return text.replace(":", "\\:").replace("'", "\\'")
            
            # Prepare text content with proper cleaning
            # NEW: Add expression_dialogue and expression_dialogue_translation
            expression_dialogue_raw = clean_text_for_slide(expression.expression_dialogue)
            expression_text_raw = clean_text_for_slide(expression.expression)
            expression_dialogue_trans_raw = clean_text_for_slide(expression.expression_dialogue_translation)
            translation_text_raw = clean_text_for_slide(expression.expression_translation)
            
            # Escape for drawtext filter
            expression_dialogue = escape_drawtext_string(expression_dialogue_raw)
            expression_text = escape_drawtext_string(expression_text_raw)
            expression_dialogue_trans = escape_drawtext_string(expression_dialogue_trans_raw)
            translation_text = escape_drawtext_string(translation_text_raw)
            
            # Prepare similar expressions (max 2) - handle different data types safely
            similar_expressions = []
            if hasattr(expression, 'similar_expressions') and expression.similar_expressions:
                raw_similar = expression.similar_expressions
                if isinstance(raw_similar, list):
                    # Extract strings from list, handling mixed types
                    for item in raw_similar[:2]:
                        if isinstance(item, str):
                            similar_expressions.append(item)
                        elif isinstance(item, dict):
                            # If it's a dict, try to extract text from common keys
                            text = item.get('text') or item.get('expression') or item.get('value') or str(item)
                            similar_expressions.append(str(text))
                        else:
                            similar_expressions.append(str(item))
                else:
                    # Handle single item or other types
                    similar_expressions.append(str(raw_similar))
            
            logger.info(f"Creating silent slide with:")
            logger.info(f"  - expression_dialogue: '{expression_dialogue}'")
            logger.info(f"  - expression: '{expression_text}'")
            logger.info(f"  - dialogue_translation: '{expression_dialogue_trans}'")
            logger.info(f"  - expression_translation: '{translation_text}'")
            if similar_expressions:
                logger.info(f"Similar expressions: {similar_expressions}")
            
            # Create slide with NEW 5-section layout (same as main educational slide)
            try:
                # Build drawtext filters for proper layout
                drawtext_filters = []
                
                # Get font option safely
                try:
                    font_file_option = self._get_font_option()
                    if not isinstance(font_file_option, str):
                        font_file_option = str(font_file_option) if font_file_option else ""
                except Exception as e:
                    logger.warning(f"Error getting font option: {e}")
                    font_file_option = ""
                
                # Safe font size retrieval with NEW font size keys (same as main slide)
                try:
                    dialogue_font_size = settings.get_font_size('expression_dialogue')
                    if not isinstance(dialogue_font_size, (int, float)):
                        dialogue_font_size = 40
                except:
                    dialogue_font_size = 40
                
                try:
                    expr_font_size = settings.get_font_size('expression')
                    if not isinstance(expr_font_size, (int, float)):
                        expr_font_size = 58
                except:
                    expr_font_size = 58
                    
                try:
                    dialogue_trans_font_size = settings.get_font_size('expression_dialogue_trans')
                    if not isinstance(dialogue_trans_font_size, (int, float)):
                        dialogue_trans_font_size = 36
                except:
                    dialogue_trans_font_size = 36
                
                try:
                    trans_font_size = settings.get_font_size('expression_trans')
                    if not isinstance(trans_font_size, (int, float)):
                        trans_font_size = 48
                except:
                    trans_font_size = 48
                
                # 1. Expression dialogue (full sentence) - upper area
                if expression_dialogue and isinstance(expression_dialogue, str):
                    drawtext_filters.append(
                        f"drawtext=text='{expression_dialogue}':fontsize={dialogue_font_size}:fontcolor=white:"
                        f"{font_file_option}"
                        f"x=(w-text_w)/2:y=h/2-220:"
                        f"borderw=2:bordercolor=black"
                    )
                
                # 2. Expression (key phrase) - highlighted in yellow, below dialogue
                if expression_text and isinstance(expression_text, str):
                    drawtext_filters.append(
                        f"drawtext=text='{expression_text}':fontsize={expr_font_size}:fontcolor=yellow:"
                        f"{font_file_option}"
                        f"x=(w-text_w)/2:y=h/2-150:"
                        f"borderw=3:bordercolor=black"
                    )
                
                # 3. Expression dialogue translation - middle area
                if expression_dialogue_trans and isinstance(expression_dialogue_trans, str):
                    drawtext_filters.append(
                        f"drawtext=text='{expression_dialogue_trans}':fontsize={dialogue_trans_font_size}:fontcolor=white:"
                        f"{font_file_option}"
                        f"x=(w-text_w)/2:y=h/2:"
                        f"borderw=2:bordercolor=black"
                    )
                
                # 4. Expression translation (key phrase) - highlighted in yellow
                if translation_text and isinstance(translation_text, str):
                    drawtext_filters.append(
                        f"drawtext=text='{translation_text}':fontsize={trans_font_size}:fontcolor=yellow:"
                        f"{font_file_option}"
                        f"x=(w-text_w)/2:y=h/2+70:"
                        f"borderw=3:bordercolor=black"
                    )
                
                # 5. Similar expressions (bottom area, positioned higher and with line breaks)
                if similar_expressions:
                    # Ensure all items are strings before processing
                    safe_similar = []
                    for sim in similar_expressions:
                        try:
                            if isinstance(sim, str):
                                safe_similar.append(clean_text_for_slide(sim))
                            elif isinstance(sim, dict):
                                # Extract text from dict safely
                                text = sim.get('text') or sim.get('expression') or sim.get('value', '')
                                if text:
                                    safe_similar.append(clean_text_for_slide(str(text)))
                            else:
                                safe_similar.append(clean_text_for_slide(str(sim)))
                        except Exception as e:
                            logger.warning(f"Could not process similar expression {sim}: {e}")
                            continue
                    
                    # Safe font size retrieval
                    try:
                        similar_font_size = settings.get_font_size('similar')
                    except:
                        similar_font_size = 32
                    
                    # Add each similar expression as a separate drawtext for proper line spacing
                    base_y = 160  # Distance from bottom (moved 3% lower: 130 -> 160)
                    line_spacing = 40  # Space between lines
                    
                    for i, similar_text in enumerate(safe_similar[:2]):  # Limit to 2 expressions
                        if similar_text:
                            similar_text_escaped = escape_drawtext_string(similar_text)
                            y_position = f"h-{base_y + (i * line_spacing)}"
                            drawtext_filters.append(
                                f"drawtext=text='{similar_text_escaped}':fontsize={similar_font_size}:fontcolor=white:"
                                f"{font_file_option}"
                                f"x=(w-text_w)/2:y={y_position}:"
                                f"borderw=1:bordercolor=black"
                            )
                
                # Combine all text filters
                video_filter = ",".join(drawtext_filters)
                
                logger.info("Creating silent educational slide with text overlay...")
                
                # Create video input based on background type - NO AUDIO
                if input_type == "image2":
                    video_input = ffmpeg.input(background_input, loop=1, t=duration, f=input_type)
                else:
                    video_input = ffmpeg.input(background_input, f=input_type, t=duration)
                
                logger.info(f"Creating slide with video duration: {duration}s, NO AUDIO")
                
                # Create the slide with video only (completely silent, no audio track)
                try:
                    (
                        ffmpeg
                        .output(video_input['v'], str(output_path),
                               vf=f"scale=1280:720,{video_filter}",
                               vcodec='libx264',
                               t=duration,
                               preset='fast',
                               crf=23)
                        .overwrite_output()
                        .run(capture_stdout=True, capture_stderr=True)
                    )
                    logger.info(f"Successfully created silent slide: {output_path}")
                        
                except Exception as ffmpeg_error:
                    logger.error(f"FFmpeg error creating silent slide: {ffmpeg_error}")
                    raise
                
                logger.info("Silent educational slide created successfully with text overlay")
                    
            except Exception as slide_error:
                logger.error(f"Failed to create silent slide with text overlay: {slide_error}")
                logger.info("Creating fallback silent slide without text...")
                
                # Fallback: create slide without text overlay and without audio
                logger.warning("Creating fallback silent slide without text overlay due to error")
                try:
                    if input_type == "image2":
                        video_input = ffmpeg.input(background_input, loop=1, t=duration, f=input_type)
                    else:
                        video_input = ffmpeg.input(background_input, f=input_type, t=duration)
                    
                    (
                        ffmpeg
                        .output(video_input['v'], str(output_path),
                               vf="scale=1280:720",
                               vcodec='libx264',
                               t=duration,
                               preset='fast',
                               crf=23)
                        .overwrite_output()
                        .run(capture_stdout=True, capture_stderr=True)
                    )
                except Exception as fallback_error:
                    logger.error(f"Even fallback silent slide creation failed: {fallback_error}")
                    # Final emergency fallback - basic slide without audio
                    try:
                        video_input = ffmpeg.input("color=c=0x1a1a2e:size=1280:720", f="lavfi", t=duration)
                        
                        (
                            ffmpeg
                            .output(video_input['v'], str(output_path),
                                   vcodec='libx264',
                                   preset='fast',
                                   crf=23)
                            .overwrite_output()
                            .run(quiet=True)
                        )
                    except Exception as emergency_error:
                        logger.error(f"Emergency fallback also failed: {emergency_error}")
                        raise
            
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error creating silent educational slide: {e}")
            raise
    
    def _time_to_seconds(self, time_str: str) -> float:
        """Convert time string to seconds"""
        try:
            # Handle format like "00:01:25,657" or "00:01:25.657"
            time_str = time_str.replace(',', '.')
            parts = time_str.split(':')
            
            if len(parts) == 3:
                hours = float(parts[0])
                minutes = float(parts[1])
                seconds = float(parts[2])
                return hours * 3600 + minutes * 60 + seconds
            elif len(parts) == 2:
                minutes = float(parts[0])
                seconds = float(parts[1])
                return minutes * 60 + seconds
            else:
                return float(parts[0])
        except Exception as e:
            logger.warning(f"Could not parse time {time_str}: {e}")
            return 0.0
    
    def _concatenate_sequence(self, video_paths: List[str], output_path: str) -> str:
        """Concatenate video sequence with smooth transitions"""
        try:
            # If only 2 videos (context + slide), apply xfade transition
            if len(video_paths) == 2:
                try:
                    logger.info("Applying xfade transition between context and slide...")
                    context_path = video_paths[0]
                    slide_path = video_paths[1]
                    
                    # Get video durations - using correct format like in step-by-step test
                    try:
                        context_probe = ffmpeg.probe(context_path)
                        slide_probe = ffmpeg.probe(slide_path)
                        
                        context_duration = float(context_probe['format']['duration'])
                        slide_duration = float(slide_probe['format']['duration'])
                        
                        logger.info(f"Context duration: {context_duration:.2f}s, Slide duration: {slide_duration:.2f}s")
                        
                    except Exception as probe_error:
                        logger.warning(f"Could not probe video durations: {probe_error}")
                        context_duration = 1.0
                        slide_duration = 1.0
                    
                    # Transition settings
                    transition_effect = "slideup"
                    transition_duration = 0.5
                    
                    # Create inputs
                    context_input = ffmpeg.input(context_path)
                    slide_input = ffmpeg.input(slide_path)
                    
                    # Normalize frame rates for compatibility
                    v0 = ffmpeg.filter(context_input['v'], 'fps', fps=25)
                    v1 = ffmpeg.filter(slide_input['v'], 'fps', fps=25)
                    
                    # Apply xfade transition - offset is context duration minus transition duration
                    transition_offset = max(0, context_duration - transition_duration)
                    
                    video_out = ffmpeg.filter([v0, v1], 'xfade',
                                             transition=transition_effect,
                                             duration=transition_duration,
                                             offset=transition_offset)
                    
                    # Concatenate audio streams separately for proper sequencing
                    audio_out = ffmpeg.filter([context_input['a'], slide_input['a']], 'concat', n=2, v=0, a=1)
                    
                    # Combine video with transition and audio concatenation
                    (
                        ffmpeg
                        .output(video_out, audio_out, str(output_path),
                               vcodec='libx264', acodec='aac', preset='fast',
                               ac=2, ar=48000, crf=23)
                        .overwrite_output()
                        .run(capture_stdout=True, capture_stderr=True)
                    )
                    
                    logger.info(f"✅ Applied xfade transition '{transition_effect}'")
                    return output_path
                    
                except Exception as transition_error:
                    logger.warning(f"Transition failed, falling back to simple concat: {transition_error}")
                    # Fall through to simple concatenation
            
            # Fallback: Simple concatenation for multiple videos or if transition fails
            logger.info("Using simple concatenation (transition failed or multiple videos)")
            concat_file = self.output_dir / "temp_concat.txt"
            self._register_temp_file(concat_file)
            
            with open(concat_file, 'w') as f:
                for video_path in video_paths:
                    f.write(f"file '{Path(video_path).absolute()}'\n")
            
            # Concatenate videos with robust settings like in step-by-step test
            (
                ffmpeg
                .input(str(concat_file), format='concat', safe=0)
                .output(str(output_path),
                       vcodec='libx264',
                       acodec='aac',
                       preset='fast',
                       ac=2,
                       ar=48000,
                       crf=23)
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error concatenating sequence: {e}")
            raise
    
    def _generate_context_subtitles(self, expression: ExpressionAnalysis) -> str:
        """Generate SRT subtitle content for context video"""
        srt_content = []
        
        for i, (dialogue, translation) in enumerate(zip(expression.dialogues, expression.translation)):
            # Calculate timing (simplified - in production, use actual timing)
            start_time = f"00:00:{i*2:02d},000"
            end_time = f"00:00:{i*2+1:02d},500"
            
            srt_content.append(f"{i+1}")
            srt_content.append(f"{start_time} --> {end_time}")
            srt_content.append(dialogue)
            srt_content.append(translation)
            srt_content.append("")
        
        return "\n".join(srt_content)
    
    def _generate_single_tts(self, text: str, expression_index: int = 0) -> Tuple[str, float]:
        """
        Generate single TTS audio and return path + duration.
        For short videos where we need to play TTS with custom timing.
        Uses caching to avoid duplicate TTS generation.
        
        Args:
            text: Text to convert to speech
            expression_index: Index of expression (0-based) for voice alternation
            
        Returns:
            Tuple of (tts_audio_path, duration)
        """
        # Check cache first
        cached_result = self._get_cached_tts(text, expression_index)
        if cached_result:
            return cached_result
        
        try:
            from langflix.tts.factory import create_tts_client
            from langflix import settings
            
            # Get TTS configuration
            tts_config = settings.get_tts_config()
            provider = tts_config.get('provider', 'google')
            provider_config = tts_config.get(provider, {})
            
            # Get alternate voices from config - this is the single source of truth for voice selection
            alternate_voices = provider_config.get('alternate_voices', ['Laomedeia'])
            if not alternate_voices:
                raise ValueError("No alternate_voices configured in TTS config. This is required for voice selection.")
            
            # Select voice based on expression index
            voice_index = expression_index % len(alternate_voices)
            selected_voice = alternate_voices[voice_index]
            
            logger.info(f"Expression {expression_index}: Using voice '{selected_voice}' for short video TTS (from alternate_voices: {alternate_voices})")
            
            # Generate TTS audio file
            voice_config = provider_config.copy()
            voice_config['voice_name'] = selected_voice
            
            tts_client = create_tts_client(provider, voice_config)
            tts_path = tts_client.generate_speech(text)
            
            # Register for cleanup
            self._register_temp_file(tts_path)
            
            # Get duration of the TTS file
            try:
                probe = ffmpeg.probe(str(tts_path))
                if 'streams' in probe and len(probe['streams']) > 0 and 'duration' in probe['streams'][0]:
                    tts_duration = float(probe['streams'][0]['duration'])
                else:
                    tts_duration = 2.0  # Fallback
            except:
                tts_duration = 2.0  # Fallback
            
            logger.info(f"Generated single TTS with {selected_voice}: {tts_duration:.2f}s")
            
            # Cache the TTS for reuse
            self._cache_tts(text, expression_index, str(tts_path), tts_duration)
            
            return str(tts_path), tts_duration
            
        except Exception as e:
            logger.error(f"Error in _generate_single_tts: {e}")
            raise

    def _generate_tts_timeline(self, text: str, tts_client, provider_config: dict, tts_audio_dir: Path, expression_index: int = 0) -> Tuple[Path, float]:
        """
        Generate TTS audio with timeline: 1 sec pause - TTS - 0.5 sec pause - TTS - ... - 1 sec pause
        Uses alternating voices between expressions (not within the same expression).
        Repeat count is configurable via settings.
        Uses caching to avoid duplicate TTS generation.
        
        Args:
            text: Text to convert to speech
            tts_client: TTS client instance
            provider_config: TTS provider configuration
            tts_audio_dir: Directory to save audio files
            expression_index: Index of expression (0-based) for voice alternation
            
        Returns:
            Tuple of (final_audio_path, total_duration)
        """
        # Check cache first for the base TTS audio
        cached_result = self._get_cached_tts(text, expression_index)
        if cached_result:
            # Use cached TTS and create timeline from it
            cached_tts_path, cached_duration = cached_result
            logger.info(f"Using cached TTS for timeline: '{text}' (duration: {cached_duration:.2f}s)")
            
            # Create timeline from cached TTS
            return self._create_timeline_from_tts(cached_tts_path, cached_duration, tts_audio_dir, expression_index)
        
        try:
            import tempfile
            import shutil
            
            # Get alternate voices from config - this is the single source of truth for voice selection
            alternate_voices = provider_config.get('alternate_voices', ['Laomedeia'])
            if not alternate_voices:
                raise ValueError("No alternate_voices configured in TTS config. This is required for voice selection.")
            
            # Select voice based on expression index (alternate between expressions)
            voice_index = expression_index % len(alternate_voices)
            selected_voice = alternate_voices[voice_index]
            
            logger.info(f"Expression {expression_index}: Using voice '{selected_voice}' (from alternate_voices: {alternate_voices})")
            
            # Generate ONE TTS audio file with the selected voice
            from langflix.tts.factory import create_tts_client
            voice_config = provider_config.copy()
            voice_config['voice_name'] = selected_voice
            
            voice_client = create_tts_client('google', voice_config)
            temp_tts_path = voice_client.generate_speech(text)
            
            # Register for cleanup
            self._register_temp_file(temp_tts_path)
            
            # Get duration of the single TTS file
            try:
                probe = ffmpeg.probe(str(temp_tts_path))
                if 'streams' in probe and len(probe['streams']) > 0 and 'duration' in probe['streams'][0]:
                    tts_duration = float(probe['streams'][0]['duration'])
                else:
                    tts_duration = 2.0  # Fallback
            except:
                tts_duration = 2.0  # Fallback
            
            logger.info(f"Generated TTS with {selected_voice}: {tts_duration:.2f}s")
            
            # Get repeat count from settings
            repeat_count = settings.get_tts_repeat_count()
            logger.info(f"Using TTS repeat count: {repeat_count}")
            
            # Create timeline: 1s pause - TTS - 0.5s pause - TTS - ... - 1s pause (repeat_count repetitions)
            timeline_path = self.output_dir / f"temp_timeline_{self._sanitize_filename(text)}.wav"
            self._register_temp_file(timeline_path)
            
            try:
                # Create silence segments
                silence_1s_path = self.output_dir / f"temp_silence_1s_{self._sanitize_filename(text)}.wav"
                silence_0_5s_path = self.output_dir / f"temp_silence_0_5s_{self._sanitize_filename(text)}.wav"
                
                self._register_temp_file(silence_1s_path)
                self._register_temp_file(silence_0_5s_path)
                
                # Generate silence files
                (ffmpeg.input('anullsrc=r=44100:cl=mono', f='lavfi', t=1.0)
                 .output(str(silence_1s_path), acodec='pcm_s16le')
                 .overwrite_output()
                 .run(quiet=True))
                
                (ffmpeg.input('anullsrc=r=44100:cl=mono', f='lavfi', t=0.5)
                 .output(str(silence_0_5s_path), acodec='pcm_s16le')
                 .overwrite_output()
                 .run(quiet=True))
                
                # Convert the single TTS file to WAV for concatenation
                tts_wav_path = self.output_dir / f"temp_tts_{self._sanitize_filename(text)}.wav"
                self._register_temp_file(tts_wav_path)
                
                (ffmpeg.input(str(temp_tts_path))
                 .output(str(tts_wav_path), acodec='pcm_s16le', ar=44100, ac=1)
                 .overwrite_output()
                 .run(quiet=True))
                
                # Build dynamic input files based on repeat_count: silence_1s + (tts + silence_0.5s) * repeat_count + silence_1s
                input_files = [str(silence_1s_path)]  # Start with 1s silence
                
                # Add TTS segments with 0.5s silence between them
                for i in range(repeat_count):
                    input_files.append(str(tts_wav_path))  # TTS audio
                    if i < repeat_count - 1:  # Don't add silence after the last TTS
                        input_files.append(str(silence_0_5s_path))  # 0.5s silence
                
                input_files.append(str(silence_1s_path))  # End with 1s silence
                
                # Create concat file
                concat_file = self.output_dir / f"temp_concat_timeline_{self._sanitize_filename(text)}.txt"
                self._register_temp_file(concat_file)
                
                with open(concat_file, 'w') as f:
                    for file_path in input_files:
                        f.write(f"file '{Path(file_path).absolute()}'\n")
                
                # Concatenate all audio segments
                (ffmpeg.input(str(concat_file), format='concat', safe=0)
                 .output(str(timeline_path), acodec='pcm_s16le', ar=44100, ac=1)
                 .overwrite_output()
                 .run(quiet=True))
                
                # Calculate total duration: 1s start + (tts_duration + 0.5s) * repeat_count - 0.5s + 1s end
                total_duration = 2.0 + (tts_duration * repeat_count) + (0.5 * (repeat_count - 1))
                
                logger.info(f"Created TTS timeline: {total_duration:.2f}s total duration (1 call, {repeat_count} repetitions)")
                
                # Cache the base TTS for reuse
                self._cache_tts(text, expression_index, str(temp_tts_path), tts_duration)
                
                # Save the original TTS file permanently (for reference)
                audio_format = provider_config.get('response_format', 'mp3')
                if audio_format:
                    original_audio_filename = f"tts_original_{self._sanitize_filename(text)}.{audio_format}"
                    original_audio_path = tts_audio_dir / original_audio_filename
                    
                    # Copy the TTS file as the "original"
                    shutil.copy2(str(temp_tts_path), str(original_audio_path))
                    logger.info(f"Saved original TTS file to: {original_audio_path}")
                
                return timeline_path, total_duration
                
            except Exception as timeline_error:
                logger.error(f"Error creating TTS timeline: {timeline_error}")
                # Fallback to simple single TTS
                return temp_tts_path, tts_duration
                
        except Exception as e:
            logger.error(f"Error in _generate_tts_timeline: {e}")
            raise

    def _extract_original_audio_timeline(
        self, 
        expression: ExpressionAnalysis, 
        original_video_path: str, 
        output_dir: Path, 
        expression_index: int = 0,
        provider_config: dict = None
    ) -> Tuple[Path, float]:
        """
        Extract audio from original video and create 3x repetition timeline matching TTS behavior.
        
        Timeline pattern: 1s silence - audio - 0.5s silence - audio - 0.5s silence - audio - 1s silence
        
        Args:
            expression: ExpressionAnalysis object with timestamps
            original_video_path: Path to the original video file
            output_dir: Directory for output files
            expression_index: Index for unique filename generation
            provider_config: TTS provider config (for audio format compatibility)
            
        Returns:
            Tuple of (timeline_audio_path, total_duration)
        """
        try:
            logger.info(f"Extracting original audio timeline for expression {expression_index}: '{expression.expression}'")
            
            # Import the original audio extractor
            from langflix.audio.original_audio_extractor import create_original_audio_timeline
            
            # Determine audio format from provider config (default to wav for compatibility)
            audio_format = "wav"
            if provider_config:
                config_format = provider_config.get('response_format', 'wav')
                if config_format.lower() in ['mp3', 'wav']:
                    audio_format = config_format.lower()
            
            logger.info(f"Using audio format: {audio_format} (from provider config)")
            
            # Validate expression timestamps
            if not expression.expression_start_time or not expression.expression_end_time:
                error_msg = f"Expression '{expression.expression}' missing required timestamps for audio extraction"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            # Create timeline using the original audio extractor
            logger.info(f"Original video path: {original_video_path}")
            logger.info(f"Expression timestamps: {expression.expression_start_time} - {expression.expression_end_time}")
            
            timeline_path, total_duration = create_original_audio_timeline(
                expression=expression,
                original_video_path=original_video_path,
                output_dir=output_dir,
                expression_index=expression_index,
                audio_format=audio_format
            )
            
            # Register the created file for cleanup
            self._register_temp_file(timeline_path)
            
            logger.info(f"Successfully created original audio timeline: {timeline_path}")
            logger.info(f"Timeline duration: {total_duration:.2f}s (3x repetition with pauses)")
            
            return timeline_path, total_duration
            
        except Exception as e:
            error_msg = f"Error extracting original audio timeline: {e}"
            logger.error(error_msg)
            
            # Create a fallback silence audio if original extraction fails
            logger.warning("Original audio extraction failed, creating silence fallback")
            return self._create_silence_fallback(expression, output_dir, expression_index, provider_config)
    
    def _create_silence_fallback(
        self,
        expression: ExpressionAnalysis,
        output_dir: Path,
        expression_index: int = 0,
        provider_config: dict = None
    ) -> Tuple[Path, float]:
        """
        Create silence audio as fallback when both TTS and original audio extraction fail.
        
        Args:
            expression: ExpressionAnalysis object
            output_dir: Directory for output files
            expression_index: Index for unique filename generation
            provider_config: TTS provider config (for audio format compatibility)
            
        Returns:
            Tuple of (silence_audio_path, duration)
        """
        try:
            # Determine audio format from provider config
            audio_format = "wav"
            if provider_config:
                config_format = provider_config.get('response_format', 'wav')
                if config_format.lower() in ['mp3', 'wav']:
                    audio_format = config_format.lower()
            
            # Create silence file with same timeline duration as TTS would have
            fallback_duration = 5.0  # 1s + 2s + 0.5s + 2s + 0.5s + 1s (approximate)
            
            silence_filename = f"silence_fallback_{expression_index}.{audio_format}"
            silence_path = output_dir / silence_filename
            
            # Use ffmpeg to create silence audio with 48kHz (video standard)
            sample_rate = 48000  # Match video audio standard, not CD audio (44.1kHz)
            
            if audio_format.lower() == "mp3":
                codec_args = ["-c:a", "mp3", "-b:a", "192k", "-ar", str(sample_rate)]
            else:  # wav
                codec_args = ["-c:a", "pcm_s16le", "-ar", str(sample_rate)]
            
            import subprocess
            silence_cmd = [
                "ffmpeg",
                "-f", "lavfi",
                "-i", f"anullsrc=channel_layout=stereo:sample_rate={sample_rate}",
                "-t", str(fallback_duration),
                *codec_args,
                "-y",
                str(silence_path)
            ]
            
            subprocess.run(silence_cmd, capture_output=True, text=True, check=True)
            
            # Register for cleanup
            self._register_temp_file(silence_path)
            
            logger.warning(f"Created silence fallback: {silence_path} ({fallback_duration}s)")
            return silence_path, fallback_duration
            
        except Exception as e:
            logger.error(f"Failed to create silence fallback: {e}")
            raise RuntimeError(f"All audio generation methods failed: {e}")

    def _extract_single_original_audio(
        self, 
        expression: ExpressionAnalysis, 
        original_video_path: str, 
        expression_index: int = 0
    ) -> Tuple[Path, float]:
        """
        Extract single audio segment from original video for short video use.
        
        Unlike timeline creation, this extracts just the raw audio segment without repetition.
        
        Args:
            expression: ExpressionAnalysis object with timestamps
            original_video_path: Path to the original video file
            expression_index: Index for unique filename generation
            
        Returns:
            Tuple of (audio_path, duration)
        """
        try:
            logger.info(f"Extracting single original audio segment for short video")
            
            # Import the original audio extractor
            from langflix.audio.original_audio_extractor import OriginalAudioExtractor
            
            # Create extractor instance
            extractor = OriginalAudioExtractor(original_video_path)
            
            # Create output path for single audio segment
            audio_dir = self.output_dir / "temp_short_audio"
            audio_dir.mkdir(parents=True, exist_ok=True)
            
            single_audio_filename = f"short_audio_{expression_index}.wav"
            single_audio_path = audio_dir / single_audio_filename
            
            # Extract just the single audio segment (no timeline)
            extracted_path, duration = extractor.extract_expression_audio(
                expression=expression,
                output_path=single_audio_path,
                audio_format="wav"
            )
            
            # Register for cleanup
            self._register_temp_file(extracted_path)
            
            logger.info(f"Extracted single audio segment: {extracted_path} ({duration:.2f}s)")
            return extracted_path, duration
            
        except Exception as e:
            error_msg = f"Error extracting single original audio: {e}"
            logger.error(error_msg)
            
            # Create fallback silence audio for short video
            logger.warning("Original audio extraction failed, creating silence fallback for short video")
            return self._create_silence_fallback_single(expression_index)
    
    def _create_silence_fallback_single(self, expression_index: int = 0) -> Tuple[Path, float]:
        """
        Create single silence audio file as fallback for short video.
        
        Args:
            expression_index: Index for unique filename generation
            
        Returns:
            Tuple of (silence_audio_path, duration)
        """
        try:
            # Create simple 2-second silence for short video fallback
            fallback_duration = 2.0
            sample_rate = 48000  # Match video audio standard
            
            silence_filename = f"short_silence_fallback_{expression_index}.wav"
            silence_path = self.output_dir / silence_filename
            
            # Use ffmpeg to create silence audio
            codec_args = ["-c:a", "pcm_s16le", "-ar", str(sample_rate)]
            
            import subprocess
            silence_cmd = [
                "ffmpeg",
                "-f", "lavfi",
                "-i", f"anullsrc=channel_layout=stereo:sample_rate={sample_rate}",
                "-t", str(fallback_duration),
                *codec_args,
                "-y",
                str(silence_path)
            ]
            
            subprocess.run(silence_cmd, capture_output=True, text=True, check=True)
            
            # Register for cleanup
            self._register_temp_file(silence_path)
            
            logger.warning(f"Created silence fallback for short video: {silence_path} ({fallback_duration}s)")
            return silence_path, fallback_duration
            
        except Exception as e:
            logger.error(f"Failed to create silence fallback for short video: {e}")
            raise RuntimeError(f"All audio generation methods failed for short video: {e}")
    
    def _time_to_seconds(self, time_str: str) -> float:
        """
        Convert SRT timestamp to seconds.
        
        Args:
            time_str: Timestamp in format "HH:MM:SS,mmm" or "HH:MM:SS.mmm"
            
        Returns:
            Time in seconds as float
        """
        try:
            # Replace comma with dot for milliseconds if needed
            time_str = time_str.replace(',', '.')
            
            # Split by colon and dot
            parts = time_str.split(':')
            if len(parts) != 3:
                raise ValueError(f"Invalid timestamp format: {time_str}")
            
            hours = int(parts[0])
            minutes = int(parts[1])
            
            # Handle seconds and milliseconds
            seconds_part = parts[2]
            if '.' in seconds_part:
                seconds, milliseconds = seconds_part.split('.')
                seconds = int(seconds)
                # Pad milliseconds to 3 digits if needed
                milliseconds = milliseconds.ljust(3, '0')[:3]
                milliseconds = int(milliseconds)
            else:
                seconds = int(seconds_part)
                milliseconds = 0
            
            total_seconds = hours * 3600 + minutes * 60 + seconds + milliseconds / 1000.0
            return total_seconds
            
        except Exception as e:
            logger.error(f"Error parsing timestamp '{time_str}': {e}")
            raise ValueError(f"Invalid timestamp: {time_str}") from e

    def _get_original_video_path(self, context_video_path: str) -> str:
        """
        Get original video path for audio extraction.
        
        If context_video_path is a temporary clip, find the original video file.
        If it's already the original video, return it as is.
        
        Args:
            context_video_path: Path to context video (might be a clip)
            
        Returns:
            Path to original video file for accurate timestamp-based audio extraction
        """
        context_path = Path(context_video_path)
        
        # If the path contains temp directories, it's likely a clip - find original
        if 'tmp' in str(context_path) or 'temp' in str(context_path):
            logger.info(f"Context video appears to be a temporary clip: {context_path.name}")
            
            # Try to find original video in assets/media
            from langflix.core.video_processor import VideoProcessor
            media_dir = Path("assets/media")
            
            # Look for video files in assets/media
            for video_file in media_dir.rglob("*.mkv"):
                if video_file.exists():
                    logger.info(f"Found original video for audio extraction: {video_file}")
                    return str(video_file)
            
            # Fallback: look for any video file
            for ext in ['.mkv', '.mp4', '.avi']:
                for video_file in media_dir.rglob(f"*{ext}"):
                    if video_file.exists():
                        logger.info(f"Using fallback original video: {video_file}")
                        return str(video_file)
            
            logger.warning(f"Could not find original video, using context path: {context_video_path}")
            return context_video_path
        else:
            # Path looks like original video
            logger.info(f"Using provided video path as original: {context_path.name}")
            return context_video_path

    def create_short_format_video(self, context_video_path: str, expression: ExpressionAnalysis, 
                                  expression_index: int = 0) -> Tuple[str, float]:
        """
        Create vertical short-format video (9:16) with context video on top and slide on bottom.
        Total duration = context_duration + (TTS_duration * repeat_count) + (0.5s * (repeat_count - 1))
        Context video plays normally, then freezes on last frame while TTS plays repeat_count times.
        
        Args:
            context_video_path: Path to context video with subtitles
            expression: ExpressionAnalysis object
            expression_index: Index of expression (for voice alternation)
            
        Returns:
            Tuple of (output_path, duration)
        """
        try:
            # Create output filename
            safe_expression = self._sanitize_filename(expression.expression)
            output_filename = f"short_{safe_expression}.mkv"
            output_path = self.context_slide_combined_dir / output_filename
            
            logger.info(f"Creating short-format video for: {expression.expression}")
            
            # Ensure backward compatibility for expression_dialogue fields
            expression = self._ensure_expression_dialogue(expression)
            
            # Get context video duration
            try:
                context_probe = ffmpeg.probe(context_video_path)
                context_duration = float(context_probe['format']['duration'])
                logger.info(f"Context video duration: {context_duration:.2f}s")
            except Exception as e:
                logger.error(f"Error getting context video duration: {e}")
                context_duration = 10.0  # Fallback duration
            
            # Generate audio for short video - check TTS setting like main educational video
            tts_text = expression.expression_dialogue
            logger.info(f"Generating audio for short video: '{tts_text}'")
            
            # Check TTS setting and use appropriate audio source
            if settings.is_tts_enabled():
                logger.info("TTS enabled - using synthetic speech for short video")
                
                # Edge case: Truncate if too long for TTS provider
                MAX_TTS_CHARS = 500  # Adjust based on provider
                if len(tts_text) > MAX_TTS_CHARS:
                    logger.warning(f"TTS text too long ({len(tts_text)} chars), truncating to {MAX_TTS_CHARS}")
                    tts_text = tts_text[:MAX_TTS_CHARS]
                
                logger.info(f"🔍 Calling _generate_single_tts for: '{tts_text}' (index: {expression_index})")
                tts_audio_path, tts_duration = self._generate_single_tts(tts_text, expression_index)
                logger.info(f"TTS audio duration: {tts_duration:.2f}s")
            else:
                logger.info("TTS disabled - using original audio timeline for short video")
                
                # Use SAME complete timeline as final_video (not single segment!)
                # Get original video path for timeline extraction
                original_video = self._get_original_video_path(context_video_path)
                
                # Create TTS audio directory for timeline storage
                tts_audio_dir = self.output_dir.parent / "tts_audio"
                tts_audio_dir.mkdir(parents=True, exist_ok=True)
                
                # Use same complete timeline extraction as final_video
                tts_audio_path, tts_duration = self._extract_original_audio_timeline(
                    expression, original_video, tts_audio_dir, expression_index, {}
                )
                logger.info(f"Original audio timeline duration: {tts_duration:.2f}s")
            
            # Calculate total video duration: context + complete_timeline_duration
            # Note: tts_duration is now the COMPLETE timeline (includes repetitions and pauses)
            total_duration = context_duration + tts_duration
            logger.info(f"Total short video duration: {total_duration:.2f}s (context: {context_duration:.2f}s + complete_timeline: {tts_duration:.2f}s)")
            
            # Create silent slide with total duration (displays throughout entire video)
            slide_path = self._create_educational_slide_silent(expression, total_duration)
            
            # Get resolution from configuration
            resolution = settings.get_short_video_resolution()
            width, height = map(int, resolution.split('x'))
            half_height = height // 2
            
            logger.info(f"Creating vertical short-format video layout ({resolution})")
            logger.info(f"Top half: {width}x{half_height}, Bottom half: {width}x{half_height}")
            
            # Create inputs
            context_input = ffmpeg.input(context_video_path)
            slide_input = ffmpeg.input(slide_path)
            
            # Extend context video by freezing last frame
            # Use tpad filter to clone the last frame for the extended duration
            freeze_duration = total_duration - context_duration
            logger.info(f"Extending context video by {freeze_duration:.2f}s with freeze frame")
            context_extended = ffmpeg.filter(
                context_input['v'],
                'tpad',
                stop_mode='clone',
                stop_duration=freeze_duration
            )
            
            # Scale videos to half height for stacking
            context_scaled = ffmpeg.filter(context_extended, 'scale', width, half_height)
            slide_scaled = ffmpeg.filter(slide_input['v'], 'scale', width, half_height)
            
            # Stack videos vertically (context on top, slide on bottom)
            stacked_video = ffmpeg.filter([context_scaled, slide_scaled], 'vstack', inputs=2)
            
            # Use SAME complete timeline as final_video - much simpler!
            logger.info(f"Using complete audio timeline (same as final_video): {tts_duration:.2f}s")
            
            try:
                # Extract context audio from context video clip (for the video part)
                context_audio_path = self.output_dir / f"temp_context_audio_short_{safe_expression}.wav"
                self._register_temp_file(context_audio_path)
                
                (ffmpeg.input(context_video_path)
                 .output(str(context_audio_path), acodec='pcm_s16le', ar=48000, ac=2, vn=None)
                 .overwrite_output()
                 .run(quiet=True))
                
                # Create simple concatenation: context_audio + complete_timeline
                audio_concat_file = self.output_dir / f"temp_concat_audio_short_{safe_expression}.txt"
                self._register_temp_file(audio_concat_file)
                
                with open(audio_concat_file, 'w') as f:
                    f.write(f"file '{Path(context_audio_path).absolute()}'\n")        # Context audio
                    f.write(f"file '{Path(tts_audio_path).absolute()}'\n")            # Complete timeline (same as final_video)
                
                # Concatenate: context + complete_timeline  
                combined_audio_path = self.output_dir / f"temp_combined_audio_short_{safe_expression}.wav"
                self._register_temp_file(combined_audio_path)
                
                (ffmpeg.input(str(audio_concat_file), format='concat', safe=0)
                 .output(str(combined_audio_path), acodec='pcm_s16le', ar=48000, ac=2)
                 .overwrite_output()
                 .run(quiet=True))
                
                logger.info(f"✅ Combined audio created: context + complete_timeline = {total_duration:.2f}s")
                
                # Create final video with combined audio
                combined_audio_input = ffmpeg.input(str(combined_audio_path))
                
                # Create final video with combined audio - fixed FFmpeg command
                logger.info(f"Creating final short video: {total_duration:.2f}s with combined audio")
                
                (
                    ffmpeg
                    .output(stacked_video, combined_audio_input['a'], str(output_path),
                           vcodec='libx264',
                           acodec='aac',
                           preset='fast',
                           crf=23,
                           ac=2,
                           ar=48000,
                           t=total_duration)  # Remove shortest=None - it was causing audio mux issues
                    .overwrite_output()
                    .run()
                )
                
                logger.info("✅ Short video created with extended audio successfully")
                
            except ffmpeg.Error as e:
                logger.error(f"FFmpeg error creating short video: {e}")
                logger.error(f"FFmpeg stderr: {e.stderr.decode() if e.stderr else 'No stderr'}")
                raise
            except Exception as e:
                logger.error(f"Error creating short video audio timeline: {e}")
                raise
            
            logger.info(f"✅ Short-format video created: {output_path} (duration: {total_duration:.2f}s)")
            return str(output_path), total_duration
            
        except Exception as e:
            logger.error(f"Error creating short-format video: {e}")
            raise

    def create_batched_short_videos(self, short_format_videos: List[Tuple[str, float]], 
                                    target_duration: float = 120.0) -> List[str]:
        """
        Combine short format videos into batches of ~120 seconds each.
        
        Args:
            short_format_videos: List of (video_path, duration) tuples
            target_duration: Target duration for each batch (default: 120 seconds)
        
        Returns:
            List of created batch video paths
        """
        try:
            logger.info(f"Creating batched short videos from {len(short_format_videos)} videos")
            logger.info(f"Target duration per batch: {target_duration}s")
            
            batch_videos = []
            current_batch_videos = []
            current_duration = 0.0
            batch_number = 1
            
            for video_path, duration in short_format_videos:
                # Check if adding this video would exceed target duration
                if current_duration + duration > target_duration and current_batch_videos:
                    # Create batch with current videos
                    batch_path = self._create_video_batch(current_batch_videos, batch_number)
                    batch_videos.append(batch_path)
                    
                    # Reset for next batch
                    current_batch_videos = [video_path]
                    current_duration = duration
                    batch_number += 1
                else:
                    # Add to current batch
                    current_batch_videos.append(video_path)
                    current_duration += duration
            
            # Create final batch if there are remaining videos
            if current_batch_videos:
                batch_path = self._create_video_batch(current_batch_videos, batch_number)
                batch_videos.append(batch_path)
            
            logger.info(f"✅ Created {len(batch_videos)} short video batches")
            return batch_videos
            
        except Exception as e:
            logger.error(f"Error creating batched short videos: {e}")
            raise

    def _create_video_batch(self, video_paths: List[str], batch_number: int) -> str:
        """Create a single batch video from a list of video paths"""
        try:
            batch_filename = f"short_video_{batch_number:03d}.mkv"
            batch_path = self.short_videos_dir / batch_filename
            
            logger.info(f"Creating batch {batch_number} with {len(video_paths)} videos")
            
            # Create concat file
            concat_file = self.short_videos_dir / f"temp_concat_batch_{batch_number}.txt"
            self._register_temp_file(concat_file)
            
            with open(concat_file, 'w') as f:
                for video_path in video_paths:
                    f.write(f"file '{Path(video_path).absolute()}'\n")
            
            # Concatenate videos
            (
                ffmpeg
                .input(str(concat_file), format='concat', safe=0)
                .output(str(batch_path),
                       vcodec='libx264',
                       acodec='aac',
                       preset='fast',
                       crf=23)
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            
            logger.info(f"✅ Batch {batch_number} created: {batch_path}")
            return str(batch_path)
            
        except Exception as e:
            logger.error(f"Error creating video batch {batch_number}: {e}")
            raise


def create_educational_video(expression: ExpressionAnalysis, 
                           context_video_path: str, 
                           expression_video_path: str,
                           output_dir: str = "output",
                           expression_index: int = 0) -> str:
    """
    Convenience function to create educational video
    
    Args:
        expression: ExpressionAnalysis object
        context_video_path: Path to context video
        expression_video_path: Path to expression video
        output_dir: Output directory
        expression_index: Index of expression (for voice alternation)
        
    Returns:
        Path to created educational video
    """
    editor = VideoEditor(output_dir)
    return editor.create_educational_sequence(expression, context_video_path, expression_video_path, expression_index)
