#!/usr/bin/env python3
"""
Video Editor for LangFlix
Creates educational video sequences with context, expression clips, and educational slides
"""

import ffmpeg
import logging
import os
from pathlib import Path
from typing import List, Dict, Any
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
        
    def create_educational_sequence(self, expression: ExpressionAnalysis, 
                                  context_video_path: str, 
                                  expression_video_path: str) -> str:
        """
        Create educational video sequence:
        1. Context video with subtitles (top: original, bottom: translation)
        2. Educational slide (background + text + audio 3x)
        
        Args:
            expression: ExpressionAnalysis object
            context_video_path: Path to context video
            expression_video_path: Path to expression video
            
        Returns:
            Path to created educational video
        """
        try:
            # Create output filename
            safe_expression = self._sanitize_filename(expression.expression)
            output_filename = f"educational_{safe_expression}.mkv"
            output_path = self.output_dir / output_filename
            
            logger.info(f"Creating educational sequence for: {expression.expression}")
            
            # Step 1: Create context video with dual-language subtitles
            context_with_subtitles = self._add_subtitles_to_context(
                context_video_path, expression
            )
            
            # Step 2: Create educational slide with background and 3x audio
            educational_slide = self._create_educational_slide(
                expression_video_path, expression  # Use original video for expression audio
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
    
    def _create_educational_slide(self, expression_source_video: str, expression: ExpressionAnalysis) -> str:
        """Create educational slide with background image, text, and TTS audio 3x"""
        try:
            output_path = self.output_dir / f"temp_slide_{self._sanitize_filename(expression.expression)}.mkv"
            self._register_temp_file(output_path)
            
            # Get background configuration with proper fallbacks
            background_input, input_type = self._get_background_config()
            
            # Generate TTS audio for expression text only
            logger.info(f"Generating TTS audio for expression: '{expression.expression}'")
            
            from .tts.factory import create_tts_client
            from . import settings
            
            tts_config = settings.get_tts_config()
            provider = settings.get_tts_provider()
            provider_config = tts_config.get(provider, {})
            
            try:
                # Create TTS client
                tts_client = create_tts_client(provider, provider_config)
                
                # Generate single audio from expression text
                audio_path = tts_client.generate_speech(expression.expression)
                self._register_temp_file(audio_path)
                
                logger.info(f"Successfully generated TTS audio: {audio_path}")
                
                # Get audio duration using ffmpeg probe
                probe = ffmpeg.probe(str(audio_path))
                expression_duration = float(probe['streams'][0]['duration'])
                
                logger.info(f"TTS audio duration: {expression_duration:.2f}s")
                
            except Exception as tts_error:
                logger.error(f"Error generating TTS audio: {tts_error}")
                # Fallback: create silence as placeholder
                expression_duration = 2.0  # Default 2 seconds
                audio_path = self.output_dir / f"temp_audio_silence_{self._sanitize_filename(expression.expression)}.wav"
                self._register_temp_file(audio_path)
                
                # Generate 2 seconds of silence as fallback
                (
                    ffmpeg
                    .input('anullsrc=r=44100:cl=mono', f='lavfi', t=expression_duration)
                    .output(str(audio_path), acodec='pcm_s16le')
                    .overwrite_output()
                    .run(quiet=True)
                )
                logger.warning(f"Using {expression_duration:.2f}s silence as TTS fallback")
            
            # Create 3x repeated audio
            audio_3x_path = self.output_dir / f"temp_audio_3x_{self._sanitize_filename(expression.expression)}.wav"
            self._register_temp_file(audio_3x_path)
            slide_duration = expression_duration * 3 + 1.0 # 3x expression audio + 1 second padding
            
            try:
                temp_audio_path = self.output_dir / f"temp_3x_{self._sanitize_filename(expression.expression)}.wav"
                self._register_temp_file(temp_audio_path)
                
                # Create 3x repeated audio using ffmpeg aloop filter
                (
                    ffmpeg
                    .input(str(audio_path))
                    .filter('aloop', loop=2, size=2e+09)  # Loop 2 more times (total 3x)
                    .output(str(temp_audio_path), acodec='pcm_s16le')
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True)
                )
                
                # Copy temp file to final location
                import shutil
                shutil.copy2(str(temp_audio_path), str(audio_3x_path))
                logger.info(f"Successfully created 3x repeated TTS audio: {expression_duration * 3:.2f}s")
            except ffmpeg.Error as e:
                logger.error(f"Error creating 3x audio: {e}")
                logger.error(f"FFmpeg stdout: {e.stdout.decode('utf-8') if e.stdout else 'None'}")
                logger.error(f"FFmpeg stderr: {e.stderr.decode('utf-8') if e.stderr else 'None'}")
                raise
            
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
            expression_text_raw = clean_text_for_slide(expression.expression)
            translation_text_raw = clean_text_for_slide(expression.expression_translation)
            
            # Escape for drawtext filter
            expression_text = escape_drawtext_string(expression_text_raw)
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
            
            logger.info(f"Creating slide with expression: '{expression_text}', translation: '{translation_text}'")
            if similar_expressions:
                logger.info(f"Similar expressions: {similar_expressions}")
            
            # Create slide with proper text layout:
            # 1. Original expression: upper middle  
            # 2. Translation: lower middle
            # 3. Similar expressions: bottom (if available)
            
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
                
                # Safe font size retrieval with fallback - increased by 20%
                try:
                    expr_font_size = settings.get_font_size('expression')
                    if not isinstance(expr_font_size, (int, float)):
                        expr_font_size = 48
                    expr_font_size = int(expr_font_size * 1.2)  # Increase by 20%
                except:
                    expr_font_size = 58  # 48 * 1.2 rounded
                    
                try:
                    trans_font_size = settings.get_font_size('translation')
                    if not isinstance(trans_font_size, (int, float)):
                        trans_font_size = 40
                    trans_font_size = int(trans_font_size * 1.2)  # Increase by 20%
                except:
                    trans_font_size = 48  # 40 * 1.2
                
                # 1. Original expression (upper middle area)
                if expression_text and isinstance(expression_text, str):
                    drawtext_filters.append(
                        f"drawtext=text='{expression_text}':fontsize={expr_font_size}:fontcolor=white:"
                        f"{font_file_option}"
                        f"x=(w-text_w)/2:y=h/2-180:"
                        f"borderw=2:bordercolor=black"
                    )
                
                # 2. Translation (lower middle area) 
                if translation_text and isinstance(translation_text, str):
                    drawtext_filters.append(
                        f"drawtext=text='{translation_text}':fontsize={trans_font_size}:fontcolor=white:"
                        f"{font_file_option}"
                        f"x=(w-text_w)/2:y=h/2+30:"
                        f"borderw=2:bordercolor=black"
                    )
                
                # 3. Similar expressions (bottom area, positioned higher and with line breaks)
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
                    base_y = 130  # Distance from bottom
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
                
                # Add the 3x TTS audio input
                audio_input = ffmpeg.input(str(audio_3x_path))
                
                # Create the slide with both video and audio directly
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
                    
                    audio_input = ffmpeg.input(str(audio_3x_path))
                    
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
                        audio_input = ffmpeg.input(str(audio_3x_path))
                        
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


def create_educational_video(expression: ExpressionAnalysis, 
                           context_video_path: str, 
                           expression_video_path: str,
                           output_dir: str = "output") -> str:
    """
    Convenience function to create educational video
    
    Args:
        expression: ExpressionAnalysis object
        context_video_path: Path to context video
        expression_video_path: Path to expression video
        output_dir: Output directory
        
    Returns:
        Path to created educational video
    """
    editor = VideoEditor(output_dir)
    return editor.create_educational_sequence(expression, context_video_path, expression_video_path)
