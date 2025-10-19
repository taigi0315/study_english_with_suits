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
            output_path = self.output_dir / f"temp_context_with_subs_{self._sanitize_filename(expression.expression)}.mkv"
            self._register_temp_file(output_path)
            
            # Find the corresponding subtitle file
            subtitle_file = self._find_subtitle_file_for_expression(expression)
            
            if subtitle_file and Path(subtitle_file).exists():
                logger.info(f"Using subtitle file: {subtitle_file}")
                
                try:
                    # Create a temporary subtitle file with only target language
                    temp_subtitle_file = self.output_dir / f"temp_target_only_{self._sanitize_filename(expression.expression)}.srt"
                    self._register_temp_file(temp_subtitle_file)
                    self._create_target_only_subtitle_file(subtitle_file, temp_subtitle_file)
                    
                    # Add subtitles using the subtitle file
                    (
                        ffmpeg
                        .input(str(video_path))
                        .output(str(output_path),
                               vf=f"subtitles={temp_subtitle_file}:force_style='FontSize=32,PrimaryColour=&Hffffff,OutlineColour=&H000000,Outline=2'",
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
        """Find the subtitle file for the given expression"""
        # Look for subtitle files in the expected locations
        expression_name = self._sanitize_filename(expression.expression)
        
        # Look in common subtitle directories
        possible_paths = [
            Path("output") / "**" / "translations" / "**" / "subtitles" / f"*{expression_name}*.srt",
            Path("output") / "**" / "*" / "subtitles" / f"*{expression_name}*.srt",
        ]
        
        import glob
        for path_pattern in possible_paths:
            matches = glob.glob(str(path_pattern), recursive=True)
            if matches:
                # Return the most recent match
                return max(matches, key=lambda p: Path(p).stat().st_mtime)
        
        logger.warning(f"Could not find subtitle file for expression: {expression.expression}")
        return None
    
    def _create_target_only_subtitle_file(self, source_subtitle_file: str, target_subtitle_file: Path) -> None:
        """Create a subtitle file with only target language (translation)"""
        try:
            with open(source_subtitle_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Process the subtitle file to extract only translation lines
            # SRT format: number, time, original text, translation text, empty line
            lines = content.split('\n')
            output_lines = []
            i = 0
            
            while i < len(lines):
                line = lines[i].strip()
                
                # Add subtitle number and timing directly
                if line.isdigit() or '-->' in line or not line:
                    output_lines.append(line)
                    i += 1
                    continue
                
                # Found text line - this is the original text
                original_text = line
                i += 1
                
                # Look for the translation line (next non-empty line that's not timing/number)
                while i < len(lines):
                    next_line = lines[i].strip()
                    if not next_line:
                        # Empty line - end of subtitle block
                        i += 1
                        break
                    elif next_line.isdigit() or '-->' in next_line:
                        # Next subtitle block started
                        break
                    else:
                        # This should be the translation
                        output_lines.append(next_line)
                        i += 1
                        break
                
                # Add empty line if there's supposed to be one
                if i < len(lines) and lines[i].strip() == '':
                    output_lines.append('')
                    i += 1
            
            # Write the target-only subtitle file
            with open(target_subtitle_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(output_lines))
                
            logger.info(f"Created target-only subtitle file: {target_subtitle_file}")
                
        except Exception as e:
            logger.error(f"Error creating target-only subtitle file: {e}")
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
                return cleaned[:50] if cleaned else "Translation"
            
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
        """Create educational slide with background image, text, and expression audio 3x"""
        try:
            output_path = self.output_dir / f"temp_slide_{self._sanitize_filename(expression.expression)}.mkv"
            self._register_temp_file(output_path)
            
            # Get background configuration with proper fallbacks
            background_input, input_type = self._get_background_config()
            
            # Extract ONLY the expression audio from original video using expression timing
            audio_path = self.output_dir / f"temp_audio_{self._sanitize_filename(expression.expression)}.wav"
            self._register_temp_file(audio_path)
            
            expression_duration = 3.0 # Default fallback 
            
            if (hasattr(expression, 'expression_start_time') and hasattr(expression, 'expression_end_time') and 
                expression.expression_start_time and expression.expression_end_time):
                
                try:
                    # Extract expression audio only from the source video
                    start_time = expression.expression_start_time.replace(',', '.')
                    end_time = expression.expression_end_time.replace(',', '.')
                    
                    # Calculate duration
                    start_seconds = self._time_to_seconds(start_time)
                    end_seconds = self._time_to_seconds(end_time)
                    expression_duration = end_seconds - start_seconds
                    
                    logger.info(f"Extracting expression audio: {start_time} to {end_time} ({expression_duration:.2f}s)")
                    
                    # Extract only the expression part from the original video
                    (
                        ffmpeg
                        .input(expression_source_video, ss=start_seconds, t=expression_duration)
                        .output(str(audio_path), acodec='pcm_s16le')
                        .overwrite_output()
                        .run(quiet=True)
                    )
                    
                    logger.info(f"Successfully extracted expression audio: {expression_duration:.2f}s")
                    
                except Exception as timing_error:
                    logger.warning(f"Could not extract expression timing: {timing_error}, using full audio")
                    # Fallback: extract full audio from the source video
                    (
                        ffmpeg
                        .input(expression_source_video)
                        .output(str(audio_path), acodec='pcm_s16le')
                        .overwrite_output()
                        .run(quiet=True)
                    )
            else:
                logger.warning("No expression timing available, extracting full audio")
                # Extract full audio from the source video
                (
                    ffmpeg
                    .input(expression_source_video)
                    .output(str(audio_path), acodec='pcm_s16le')
                    .overwrite_output()
                    .run(quiet=True)
                )
            
            # Create 3x repeated audio
            audio_3x_path = self.output_dir / f"temp_audio_3x_{self._sanitize_filename(expression.expression)}.wav"
            self._register_temp_file(audio_3x_path)
            slide_duration = expression_duration * 3 + 1.0 # 3x expression audio + 1 second padding
            
            try:
                temp_audio_path = self.output_dir / f"temp_3x_{self._sanitize_filename(expression.expression)}.wav"
                self._register_temp_file(temp_audio_path)
                
                # First create 3x repeated audio
                (
                    ffmpeg
                    .input(str(audio_path))
                    .filter('aloop', loop=2, size=2e+09)  # Loop 2 more times (total 3x)
                    .output(str(temp_audio_path), acodec='pcm_s16le')
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True)
                )
                
                # Copy temp file to final location (no additional padding needed)
                import shutil
                shutil.copy2(str(temp_audio_path), str(audio_3x_path))
                logger.info(f"Successfully created 3x repeated audio: {expression_duration * 3:.2f}s")
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
                return cleaned[:35] if cleaned else "Expression"
            
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
                
                logger.info("Creating educational slide with text overlay...")
                
                # Use proper ffmpeg input based on background type
                if input_type == "image2":
                    (
                        ffmpeg
                        .input(background_input, loop=1, t=slide_duration, f=input_type)
                        .output(str(output_path),
                               vf=f"scale=1280:720,{video_filter}",
                               vcodec='libx264',
                               acodec='aac',
                               t=slide_duration,
                               preset='fast',
                               crf=23)
                        .overwrite_output()
                        .run(quiet=True)
                    )
                else:
                    # For lavfi (color) input
                    (
                        ffmpeg
                        .input(background_input, f=input_type, t=slide_duration)
                        .output(str(output_path),
                               vf=f"scale=1280:720,{video_filter}",
                               vcodec='libx264',
                               acodec='aac',
                               t=slide_duration,
                               preset='fast',
                               crf=23)
                        .overwrite_output()
                        .run(quiet=True)
                    )
                
                logger.info("Educational slide created successfully with text overlay")
                    
            except Exception as slide_error:
                logger.error(f"Failed to create slide with text overlay: {slide_error}")
                logger.info("Creating fallback slide without text...")
                
                # Fallback: create slide without text overlay
                logger.warning("Creating fallback slide without text overlay due to error")
                try:
                    if input_type == "image2":
                        (
                            ffmpeg
                            .input(background_input, loop=1, t=slide_duration, f=input_type)
                            .output(str(output_path),
                                   vf="scale=1280:720",
                                   vcodec='libx264',
                                   acodec='aac',
                                   t=slide_duration,
                                   preset='fast',
                                   crf=23)
                            .overwrite_output()
                            .run(quiet=True)
                        )
                    else:
                        (
                            ffmpeg
                            .input(background_input, f=input_type, t=slide_duration)
                            .output(str(output_path),
                                   vf="scale=1280:720",
                                   vcodec='libx264',
                                   acodec='aac',
                                   t=slide_duration,
                                   preset='fast',
                                   crf=23)
                            .overwrite_output()
                            .run(quiet=True)
                        )
                except Exception as fallback_error:
                    logger.error(f"Even fallback slide creation failed: {fallback_error}")
                    # Final emergency fallback
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
            
            # Combine slide with 3x audio
            final_slide_path = self.output_dir / f"temp_final_slide_{self._sanitize_filename(expression.expression)}.mkv"
            # Note: Don't register final_slide_path as temp file since it's the return value
            
            video_input = ffmpeg.input(str(output_path))
            audio_input = ffmpeg.input(str(audio_3x_path))
            
            try:
                # Combine video and audio streams properly with duration limit
                (
                    ffmpeg
                    .output(video_input['v'], audio_input['a'], str(final_slide_path),
                           vcodec='libx264',
                           acodec='aac',
                           preset='fast',
                           crf=23,
                           t=slide_duration)
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True)
                )
                logger.info(f"Successfully combined video and audio for final slide")
            except ffmpeg.Error as e:
                logger.error(f"FFmpeg error combining video and audio: {e}")
                logger.error(f"FFmpeg stdout: {e.stdout.decode('utf-8') if e.stdout else 'None'}")
                logger.error(f"FFmpeg stderr: {e.stderr.decode('utf-8') if e.stderr else 'None'}")
                raise
            
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
        """Concatenate video sequence"""
        try:
            # Create concat file for ffmpeg
            concat_file = self.output_dir / "temp_concat.txt"
            self._register_temp_file(concat_file)
            
            with open(concat_file, 'w') as f:
                for video_path in video_paths:
                    f.write(f"file '{video_path}'\n")
            
            # Concatenate videos
            (
                ffmpeg
                .input(str(concat_file), format='concat', safe=0)
                .output(str(output_path),
                       vcodec='libx264',
                       acodec='aac')
                .overwrite_output()
                .run(quiet=True)
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
