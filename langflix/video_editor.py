#!/usr/bin/env python3
"""
Video Editor for LangFlix
Creates educational video sequences with context, expression clips, and educational slides
"""

import ffmpeg
import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Tuple
from .models import ExpressionAnalysis
from . import settings

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
                    
                    # Add subtitles using the subtitle file
                    (
                        ffmpeg
                        .input(str(video_path))
                        .output(str(output_path),
                               vf=f"subtitles={temp_subtitle_file}:force_style='FontSize=19,PrimaryColour=&Hffffff,OutlineColour=&H000000,Outline=2'",
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
            subtitle_dir = self.output_dir.parent / "subtitles"
            
            # Search for files that match the expected pattern
            import glob
            patterns = [
                # Try with index prefix: expression_01_, expression_02_, etc.
                str(subtitle_dir / f"expression_*_{safe_expression[:30]}.srt"),
                # Try without index: expression_{expression}.srt  
                str(subtitle_dir / f"expression_{safe_expression[:30]}.srt"),
                # Try with sanitized name as fallback
                str(subtitle_dir / f"expression_*_{self._sanitize_filename(expression.expression)}.srt"),
            ]
            
            for pattern in patterns:
                matches = glob.glob(pattern)
                if matches:
                    # Return the first match, prefer numbered ones
                    matches.sort()  # This will put expression_01 before expression_02, etc.
                    logger.info(f"Found subtitle file: {matches[0]}")
                    return matches[0]
            
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
            
            # Simple drawtext overlay for target language only
            font_file_option = self._get_font_option()
            
            video_args = self._get_video_output_args()
            
            subtitle_filter = (
                f"drawtext=text='{clean_translation}':fontsize={settings.get_font_size()}:fontcolor=white:"
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
            
            # Generate TTS audio for dialogue + expression with edge case handling
            # Edge case: If expression is same as dialogue, only read once
            if (expression.expression.strip() == expression.expression_dialogue.strip()):
                tts_text = expression.expression_dialogue  # Only read once to avoid duplication
                logger.info(f"Expression same as dialogue, TTS will read once: '{tts_text}'")
            else:
                tts_text = f"{expression.expression_dialogue}. {expression.expression}"
                logger.info(f"Generating TTS audio for: '{tts_text}'")
            
            # Edge case: Truncate if too long for TTS provider
            MAX_TTS_CHARS = 500  # Adjust based on provider
            if len(tts_text) > MAX_TTS_CHARS:
                logger.warning(f"TTS text too long ({len(tts_text)} chars), truncating to {MAX_TTS_CHARS}")
                tts_text = tts_text[:MAX_TTS_CHARS]
            
            # Import TTS modules
            from .tts.factory import create_tts_client
            from . import settings
            
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
            
            try:
                # Create and validate TTS client
                logger.info("Creating TTS client...")
                tts_client = create_tts_client(provider, provider_config)
                
                # Test if TTS is enabled
                if not settings.is_tts_enabled():
                    logger.warning("TTS is disabled in configuration, using fallback")
                    raise ValueError("TTS is disabled")
                
                # Generate timeline with voice alternation: 1 sec pause - TTS - 0.5 sec pause - TTS - 0.5 sec pause - TTS - 1 sec pause
                logger.info(f"Generating TTS timeline for: '{tts_text}' (expression index: {expression_index})")
                audio_path, expression_duration = self._generate_tts_timeline(
                    tts_text, tts_client, provider_config, tts_audio_dir, expression_index
                )
                
                logger.info(f"Generated TTS timeline duration: {expression_duration:.2f}s")
                
            except Exception as tts_error:
                logger.error(f"Error generating TTS audio: {tts_error}")
                logger.error(f"TTS Error details: {tts_error}")
                
                # Use the configured audio format for fallback as well
                audio_format = provider_config.get('response_format', 'mp3')
                logger.info(f"Using {audio_format} format for fallback audio")
                
                expression_duration = 2.0  # Default 2 seconds
                
                # Create fallback with same format as configured
                if audio_format.lower() == 'mp3':
                    audio_path = self.output_dir / f"temp_audio_silence_{self._sanitize_filename(expression.expression)}.mp3"
                    self._register_temp_file(audio_path)
                    
                    # Generate 2 seconds of silence as MP3 fallback
                    (
                        ffmpeg
                        .input('anullsrc=r=44100:cl=mono', f='lavfi', t=expression_duration)
                        .output(str(audio_path), acodec='libmp3lame', ar=44100)
                        .overwrite_output()
                        .run(quiet=True)
                    )
                else:
                    audio_path = self.output_dir / f"temp_audio_silence_{self._sanitize_filename(expression.expression)}.wav"
                    self._register_temp_file(audio_path)
                    
                    # Generate 2 seconds of silence as WAV fallback
                    (
                        ffmpeg
                        .input('anullsrc=r=44100:cl=mono', f='lavfi', t=expression_duration)
                        .output(str(audio_path), acodec='pcm_s16le')
                        .overwrite_output()
                        .run(quiet=True)
                    )
                
                logger.warning(f"Using {expression_duration:.2f}s silence as TTS fallback in {audio_format} format")
                
                # Save the fallback file to permanent tts_audio directory with correct format
                tts_audio_dir = self.output_dir.parent / "tts_audio"
                tts_audio_dir.mkdir(exist_ok=True)
                fallback_filename = f"tts_fallback_{self._sanitize_filename(expression.expression)}.{audio_format}"
                fallback_permanent_path = tts_audio_dir / fallback_filename
                
                import shutil
                shutil.copy2(str(audio_path), str(fallback_permanent_path))
                logger.warning(f"Fallback silence audio saved to: {fallback_permanent_path}")
            
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
        
        Args:
            text: Text to convert to speech
            expression_index: Index of expression (0-based) for voice alternation
            
        Returns:
            Tuple of (tts_audio_path, duration)
        """
        try:
            from .tts.factory import create_tts_client
            from . import settings
            
            # Get TTS configuration
            tts_config = settings.get_tts_config()
            provider = tts_config.get('provider', 'google')
            provider_config = tts_config.get(provider, {})
            
            # Get alternate voices from config
            alternate_voices = provider_config.get('alternate_voices', ['en-US-Wavenet-D', 'en-US-Wavenet-A'])
            if len(alternate_voices) < 2:
                alternate_voices = ['en-US-Wavenet-D', 'en-US-Wavenet-A']
            
            # Select voice based on expression index
            voice_index = expression_index % len(alternate_voices)
            selected_voice = alternate_voices[voice_index]
            voice_name = "Puck" if voice_index == 0 else "Leda"
            
            logger.info(f"Expression {expression_index}: Using voice {voice_name} ({selected_voice}) for short video TTS")
            
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
            
            logger.info(f"Generated single TTS with {voice_name}: {tts_duration:.2f}s")
            
            return str(tts_path), tts_duration
            
        except Exception as e:
            logger.error(f"Error in _generate_single_tts: {e}")
            raise

    def _generate_tts_timeline(self, text: str, tts_client, provider_config: dict, tts_audio_dir: Path, expression_index: int = 0) -> Tuple[Path, float]:
        """
        Generate TTS audio with timeline: 1 sec pause - TTS - 0.5 sec pause - TTS - 0.5 sec pause - TTS - 1 sec pause
        Uses alternating voices between expressions (not within the same expression).
        
        Args:
            text: Text to convert to speech
            tts_client: TTS client instance
            provider_config: TTS provider configuration
            tts_audio_dir: Directory to save audio files
            expression_index: Index of expression (0-based) for voice alternation
            
        Returns:
            Tuple of (final_audio_path, total_duration)
        """
        try:
            import tempfile
            import shutil
            
            # Get alternate voices from config
            alternate_voices = provider_config.get('alternate_voices', ['en-US-Wavenet-D', 'en-US-Wavenet-A'])
            if len(alternate_voices) < 2:
                alternate_voices = ['en-US-Wavenet-D', 'en-US-Wavenet-A']  # Puck and Leda
            
            # Select voice based on expression index (alternate between expressions)
            voice_index = expression_index % len(alternate_voices)
            selected_voice = alternate_voices[voice_index]
            voice_name = "Puck" if voice_index == 0 else "Leda"
            
            logger.info(f"Expression {expression_index}: Using voice {voice_name} ({selected_voice})")
            
            # Generate ONE TTS audio file with the selected voice
            from .tts.factory import create_tts_client
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
            
            logger.info(f"Generated TTS with {voice_name}: {tts_duration:.2f}s")
            
            # Create timeline: 1s pause - TTS - 0.5s pause - TTS - 1s pause (2 repetitions)
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
                
                # Concatenate: silence_1s + tts + silence_0.5s + tts + silence_1s (2 repetitions)
                input_files = [
                    str(silence_1s_path),
                    str(tts_wav_path),      # First TTS
                    str(silence_0_5s_path),
                    str(tts_wav_path),      # Second TTS (same file)
                    str(silence_1s_path)
                ]
                
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
                
                # Calculate total duration: 1 + tts + 0.5 + tts + 1 = 2.5 + (tts * 2)
                total_duration = 2.5 + (tts_duration * 2)
                
                logger.info(f"Created TTS timeline: {total_duration:.2f}s total duration (1 call, 2 repetitions)")
                
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

    def create_short_format_video(self, context_video_path: str, expression: ExpressionAnalysis, 
                                  expression_index: int = 0) -> Tuple[str, float]:
        """
        Create vertical short-format video (9:16) with context video on top and slide on bottom.
        Total duration = context_duration + (TTS_duration * 2) + 0.5s
        Context video plays normally, then freezes on last frame while TTS plays twice.
        
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
            
            # Generate TTS audio using the same logic as educational slide (dialogue + expression)
            # Edge case: If expression is same as dialogue, only read once
            if (expression.expression.strip() == expression.expression_dialogue.strip()):
                tts_text = expression.expression_dialogue  # Only read once to avoid duplication
                logger.info(f"Expression same as dialogue, TTS will read once: '{tts_text}'")
            else:
                tts_text = f"{expression.expression_dialogue}. {expression.expression}"
                logger.info(f"Generating TTS audio for short video: '{tts_text}'")
            
            # Edge case: Truncate if too long for TTS provider
            MAX_TTS_CHARS = 500  # Adjust based on provider
            if len(tts_text) > MAX_TTS_CHARS:
                logger.warning(f"TTS text too long ({len(tts_text)} chars), truncating to {MAX_TTS_CHARS}")
                tts_text = tts_text[:MAX_TTS_CHARS]
            
            tts_audio_path, tts_duration = self._generate_single_tts(tts_text, expression_index)
            logger.info(f"TTS audio duration: {tts_duration:.2f}s")
            
            # Calculate total video duration: context + (TTS * 2) + 0.5s gap
            total_duration = context_duration + (tts_duration * 2) + 0.5
            logger.info(f"Total short video duration: {total_duration:.2f}s (context: {context_duration:.2f}s + TTS×2: {tts_duration * 2:.2f}s + gap: 0.5s)")
            
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
            
            # Create combined audio: context_audio + TTS (twice with 0.5s gap)
            logger.info("Creating combined audio timeline: context audio + TTS×2 with 0.5s gap")
            
            # Create audio timeline: context_audio + TTS×2 with 0.5s gap
            # First, create TTS timeline (TTS + 0.5s silence + TTS)
            try:
                # Create silence for 0.5s gap
                silence_0_5s_path = self.output_dir / f"temp_silence_0_5s_short_{safe_expression}.wav"
                self._register_temp_file(silence_0_5s_path)
                
                (ffmpeg.input('anullsrc=r=48000:cl=stereo', f='lavfi', t=0.5)
                 .output(str(silence_0_5s_path), acodec='pcm_s16le', ar=48000, ac=2)
                 .overwrite_output()
                 .run(quiet=True))
                
                # Convert TTS to WAV with stereo for concatenation
                tts_wav_path = self.output_dir / f"temp_tts_short_{safe_expression}.wav"
                self._register_temp_file(tts_wav_path)
                
                (ffmpeg.input(str(tts_audio_path))
                 .output(str(tts_wav_path), acodec='pcm_s16le', ar=48000, ac=2)
                 .overwrite_output()
                 .run(quiet=True))
                
                # Extract context audio to WAV
                context_audio_path = self.output_dir / f"temp_context_audio_short_{safe_expression}.wav"
                self._register_temp_file(context_audio_path)
                
                (ffmpeg.input(context_video_path)
                 .output(str(context_audio_path), acodec='pcm_s16le', ar=48000, ac=2, vn=None)
                 .overwrite_output()
                 .run(quiet=True))
                
                # Create concat file for audio timeline: context_audio + TTS + 0.5s silence + TTS
                audio_concat_file = self.output_dir / f"temp_concat_audio_short_{safe_expression}.txt"
                self._register_temp_file(audio_concat_file)
                
                with open(audio_concat_file, 'w') as f:
                    f.write(f"file '{Path(context_audio_path).absolute()}'\n")
                    f.write(f"file '{Path(tts_wav_path).absolute()}'\n")
                    f.write(f"file '{Path(silence_0_5s_path).absolute()}'\n")
                    f.write(f"file '{Path(tts_wav_path).absolute()}'\n")
                
                # Concatenate all audio segments
                combined_audio_path = self.output_dir / f"temp_combined_audio_short_{safe_expression}.wav"
                self._register_temp_file(combined_audio_path)
                
                (ffmpeg.input(str(audio_concat_file), format='concat', safe=0)
                 .output(str(combined_audio_path), acodec='pcm_s16le', ar=48000, ac=2)
                 .overwrite_output()
                 .run(quiet=True))
                
                logger.info(f"✅ Combined audio timeline created: {total_duration:.2f}s")
                
                # Create final video with combined audio
                combined_audio_input = ffmpeg.input(str(combined_audio_path))
                
                (
                    ffmpeg
                    .output(stacked_video, combined_audio_input['a'], str(output_path),
                           vcodec='libx264',
                           acodec='aac',
                           preset='fast',
                           crf=23,
                           ac=2,
                           ar=48000,
                           t=total_duration)
                    .overwrite_output()
                    .run(quiet=True)
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
