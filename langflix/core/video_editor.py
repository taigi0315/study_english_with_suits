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
from langflix.media.ffmpeg_utils import concat_filter_with_explicit_map, build_repeated_av, vstack_keep_width, log_media_params, repeat_av_demuxer, hstack_keep_height, get_duration_seconds, concat_demuxer_if_uniform, apply_final_audio_gain
from langflix.subtitles import overlay as subs_overlay
from langflix.utils.filename_utils import sanitize_for_expression_filename
from .error_handler import handle_error_decorator, ErrorContext, retry_on_error

logger = logging.getLogger(__name__)

class VideoEditor:
    """
    Creates educational video sequences from expression analysis results
    """
    
    def __init__(self, output_dir: str = "output", language_code: str = None, episode_name: str = None, subtitle_processor = None):
        """
        Initialize VideoEditor
        
        Args:
            output_dir: Directory for output files
            language_code: Target language code for font selection
            episode_name: Episode name for file naming
            subtitle_processor: Optional SubtitleProcessor instance for generating expression subtitles
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)  # Create parent directories if needed
        # Use centralized temp file manager instead of local tracking
        from langflix.utils.temp_file_manager import get_temp_manager
        self.temp_manager = get_temp_manager()
        self._tts_cache = {}  # Legacy cache for backward compatibility
        self.cache_manager = get_cache_manager()  # Advanced cache manager
        self.language_code = language_code
        self.episode_name = episode_name or "Unknown_Episode"
        self.subtitle_processor = subtitle_processor  # For generating expression subtitles
        
        # Set up paths for different video types - all videos go to videos/ directory
        # Try to find videos directory in parent structure
        if hasattr(self.output_dir, 'parent'):
            lang_dir = self.output_dir.parent
            if lang_dir.name in ['ko', 'ja', 'zh', 'en']:  # Language code
                self.videos_dir = lang_dir / "videos"
            else:
                self.videos_dir = self.output_dir.parent / "videos"
        else:
            self.videos_dir = Path(self.output_dir).parent / "videos"
        
        # All video outputs go to videos/ directory
        self.final_videos_dir = self.videos_dir
        self.context_slide_combined_dir = self.videos_dir
        self.short_videos_dir = self.videos_dir
        
        # Ensure directories exist (create parent directories if needed)
        self.videos_dir.mkdir(parents=True, exist_ok=True)
        
        # Track short format temp files for preservation (TICKET-029)
        self.short_format_temp_files = []
    
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
    
    @handle_error_decorator(
        ErrorContext(
            operation="create_long_form_video",
            component="core.video_editor"
        ),
        retry=False,
        fallback=False
    )
    def create_long_form_video(
        self,
        expression: ExpressionAnalysis,
        context_video_path: str,
        expression_video_path: str,
        expression_index: int = 0
    ) -> str:
        """
        Create long-form video with unified layout:
        - context video → expression repeat (2회) → slide (expression audio 2회)
        - No transition (direct concatenation)
        - Maintains original aspect ratio (16:9 or other)
        
        Args:
            expression: ExpressionAnalysis object
            context_video_path: Path to context video (used for extracting expression clip)
            expression_video_path: Path to expression video (for audio extraction)
            expression_index: Index of expression (for voice alternation)
            
        Returns:
            Path to created long-form video
        """
        try:
            from langflix.utils.filename_utils import sanitize_for_expression_filename
            safe_expression = sanitize_for_expression_filename(expression.expression)
            output_filename = f"long_form_video_{safe_expression}.mkv"
            
            # Use videos directory from paths (created by output_manager)
            # All videos go to videos/ directory
            if hasattr(self, 'videos_dir'):
                videos_dir = self.videos_dir
            elif hasattr(self, 'output_dir') and hasattr(self.output_dir, 'parent'):
                # Try to find videos directory in parent structure
                lang_dir = self.output_dir.parent
                if lang_dir.name in ['ko', 'ja', 'zh', 'en']:  # Language code
                    videos_dir = lang_dir / "videos"
                else:
                    videos_dir = self.output_dir.parent / "videos"
            else:
                # Fallback: create in output_dir parent
                videos_dir = Path(self.output_dir).parent / "videos"
                videos_dir.mkdir(parents=True, exist_ok=True)
            
            output_path = videos_dir / output_filename
            
            logger.info(f"Creating long-form video for: {expression.expression}")
            
            # Step 1: Extract expression video clip from context and repeat it (2회)
            context_start_seconds = self._time_to_seconds(expression.context_start_time)
            expression_start_seconds = self._time_to_seconds(expression.expression_start_time)
            expression_end_seconds = self._time_to_seconds(expression.expression_end_time)
            
            if expression_start_seconds < context_start_seconds:
                logger.warning(f"Expression start time {expression.expression_start_time} is before context start {expression.context_start_time}")
                expression_start_seconds = context_start_seconds
            
            relative_start = expression_start_seconds - context_start_seconds
            relative_end = expression_end_seconds - context_start_seconds
            expression_duration = relative_end - relative_start
            
            if expression_duration <= 0:
                logger.error(f"Invalid expression duration: {expression_duration:.2f}s")
                raise ValueError(f"Expression duration must be positive, got {expression_duration:.2f}s")
            
            logger.info(f"Expression relative: {relative_start:.2f}s - {relative_end:.2f}s ({expression_duration:.2f}s)")
            
            # Step 1a: Extract context clip from original video WITH subtitles
            self.output_dir.mkdir(parents=True, exist_ok=True)
            context_clip_path = self.output_dir / f"temp_context_clip_{safe_expression}.mkv"
            self._register_temp_file(context_clip_path)

            context_end_seconds = self._time_to_seconds(expression.context_end_time)
            context_duration = context_end_seconds - context_start_seconds

            logger.info(f"Extracting context clip with subtitles: {context_start_seconds:.2f}s - {context_end_seconds:.2f}s ({context_duration:.2f}s)")

            # Find and apply subtitle file
            subtitle_file = None
            # Try to find subtitle file in subtitles directory
            subtitles_dir = self.output_dir.parent / "subtitles"
            if subtitles_dir.exists():
                # Look for subtitle file matching expression pattern
                from langflix.utils.filename_utils import sanitize_for_expression_filename
                safe_expression_short = sanitize_for_expression_filename(expression.expression)[:30]
                subtitle_filename = f"expression_{expression_index+1:02d}_{safe_expression_short}.srt"
                subtitle_file_path = subtitles_dir / subtitle_filename
                
                if subtitle_file_path.exists():
                    subtitle_file = subtitle_file_path
                    logger.info(f"Found subtitle file: {subtitle_file}")
                else:
                    # Try to find any subtitle file matching the expression
                    pattern = f"expression_*_{safe_expression_short}*.srt"
                    matching_files = list(subtitles_dir.glob(pattern))
                    if matching_files:
                        subtitle_file = matching_files[0]
                        logger.info(f"Found matching subtitle file: {subtitle_file}")
            
            if subtitle_file and subtitle_file.exists():
                logger.info(f"Applying subtitles from: {subtitle_file}")

                # Apply subtitles using subs_overlay (extract + apply in one step)
                subs_overlay.apply_dual_subtitle_layers(
                    str(context_video_path),
                    str(subtitle_file),
                    "",  # No expression subtitle for long-form video
                    str(context_clip_path),
                    context_start_seconds,
                    context_end_seconds
                )
            else:
                # No subtitles - extract context clip without them
                logger.warning("No subtitle file found, extracting context without subtitles")
                context_input = ffmpeg.input(str(context_video_path))
                context_video = context_input['v']
                context_audio = context_input['a']

                (
                    ffmpeg.output(
                        context_video,
                        context_audio,
                        str(context_clip_path),
                        vcodec='libx264',
                        acodec='aac',
                        ac=2,
                        ar=48000,
                        preset='fast',
                        crf=23,
                        ss=context_start_seconds,
                        t=context_duration
                    )
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True)
                )

            # Reset timestamps of context clip
            context_clip_reset_path = self.output_dir / f"temp_context_clip_reset_{safe_expression}.mkv"
            self._register_temp_file(context_clip_reset_path)

            reset_input = ffmpeg.input(str(context_clip_path))
            reset_video = ffmpeg.filter(reset_input['v'], 'setpts', 'PTS-STARTPTS')
            reset_audio = ffmpeg.filter(reset_input['a'], 'asetpts', 'PTS-STARTPTS')

            (
                ffmpeg.output(
                    reset_video,
                    reset_audio,
                    str(context_clip_reset_path),
                    vcodec='libx264',
                    acodec='aac',
                    ac=2,
                    ar=48000,
                    preset='fast',
                    crf=23
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )

            # Step 1b: Extract expression video clip from context clip
            expression_video_clip_path = self.output_dir / f"temp_expr_clip_long_form_{safe_expression}.mkv"
            self._register_temp_file(expression_video_clip_path)
            logger.info(f"Extracting expression clip from context ({expression_duration:.2f}s)")
            
            input_stream = ffmpeg.input(str(context_clip_reset_path))
            video_stream = input_stream['v']
            audio_stream = input_stream['a']
            
            try:
                # Extract with output seeking
                (
                    ffmpeg.output(
                        video_stream,
                        audio_stream,
                        str(expression_video_clip_path),
                        vcodec='libx264',
                        acodec='aac',
                        ac=2,
                        ar=48000,
                        preset='fast',
                        crf=23,
                        ss=relative_start,
                        t=expression_duration
                    )
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True)
                )
                
                # Reset timestamps
                temp_clip_path = self.output_dir / f"temp_expr_clip_long_form_reset_{safe_expression}.mkv"
                self._register_temp_file(temp_clip_path)
                
                reset_input = ffmpeg.input(str(expression_video_clip_path))
                reset_video = ffmpeg.filter(reset_input['v'], 'setpts', 'PTS-STARTPTS')
                reset_audio = ffmpeg.filter(reset_input['a'], 'asetpts', 'PTS-STARTPTS')
                
                (
                    ffmpeg.output(
                        reset_video,
                        reset_audio,
                        str(temp_clip_path),
                        vcodec='libx264',
                        acodec='aac',
                        ac=2,
                        ar=48000,
                        preset='fast',
                        crf=23
                    )
                    .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True)
                )
                
                import shutil
                shutil.move(str(temp_clip_path), str(expression_video_clip_path))
                
                if not expression_video_clip_path.exists():
                    raise RuntimeError(f"Expression clip file was not created: {expression_video_clip_path}")
                
                logger.info(f"✅ Expression clip extracted: {expression_video_clip_path}")
            except ffmpeg.Error as e:
                stderr = e.stderr.decode('utf-8') if e.stderr else str(e)
                logger.error(f"❌ FFmpeg failed to extract expression clip: {stderr}")
                raise RuntimeError(f"FFmpeg failed to extract expression clip: {stderr}") from e
            
            # Step 2: Repeat expression clip 2 times
            repeat_count = 2
            repeated_expression_path = self.output_dir / f"temp_expr_repeated_long_form_{safe_expression}.mkv"
            self._register_temp_file(repeated_expression_path)
            logger.info(f"Repeating expression clip {repeat_count} times")
            from langflix.media.ffmpeg_utils import repeat_av_demuxer
            repeat_av_demuxer(str(expression_video_clip_path), repeat_count, str(repeated_expression_path))
            
            # Step 3: Concatenate context + transition + expression repeat
            context_expr_path = self.output_dir / f"temp_context_expr_long_form_{safe_expression}.mkv"
            self._register_temp_file(context_expr_path)

            # Get transition configuration
            transition_config = settings.get_transitions_config().get('context_to_expression_transition', {})
            transition_enabled = transition_config.get('enabled', False)

            if transition_enabled:
                # Create transition video (0.3s with image and sound effect)
                transition_duration = transition_config.get('duration', 0.3)
                transition_image = transition_config.get('image_path_16_9', 'assets/transition_16_9.png')
                sound_effect = transition_config.get('sound_effect_path', 'assets/sound_effect.mp3')

                logger.info(f"Creating {transition_duration}s transition between context and expression")
                transition_video = self._create_transition_video(
                    duration=transition_duration,
                    image_path=transition_image,
                    sound_effect_path=sound_effect,
                    source_video_path=str(context_clip_reset_path),
                    aspect_ratio="16:9"
                )

                if transition_video:
                    # Concatenate: context + transition + expression
                    logger.info("Concatenating context + transition + expression repeat")
                    from langflix.media.ffmpeg_utils import concat_filter_with_explicit_map
                    # Note: concat_filter_with_explicit_map only handles 2 inputs, so we'll do it in two steps
                    temp_context_transition = self.output_dir / f"temp_context_transition_{safe_expression}.mkv"
                    self._register_temp_file(temp_context_transition)
                    concat_filter_with_explicit_map(
                        str(context_clip_reset_path),
                        str(transition_video),
                        str(temp_context_transition)
                    )
                    concat_filter_with_explicit_map(
                        str(temp_context_transition),
                        str(repeated_expression_path),
                        str(context_expr_path)
                    )
                else:
                    # Fallback to direct concatenation if transition creation failed
                    logger.warning("Transition creation failed, concatenating directly")
                    from langflix.media.ffmpeg_utils import concat_filter_with_explicit_map
                    concat_filter_with_explicit_map(
                        str(context_clip_reset_path),
                        str(repeated_expression_path),
                        str(context_expr_path)
                    )
            else:
                # No transition - direct concatenation
                logger.info("Concatenating context + expression repeat (no transition)")
                from langflix.media.ffmpeg_utils import concat_filter_with_explicit_map
                concat_filter_with_explicit_map(
                    str(context_clip_reset_path),
                    str(repeated_expression_path),
                    str(context_expr_path)
                )
            
            # Get duration for slide matching
            from langflix.media.ffmpeg_utils import get_duration_seconds
            context_expr_duration = get_duration_seconds(str(context_expr_path))
            logger.info(f"Context + expression duration: {context_expr_duration:.2f}s")
            
            # Step 4: Create educational slide with expression audio (2회 반복)
            # Extract expression audio and repeat it 2 times
            educational_slide = self._create_educational_slide(
                expression_video_path,
                expression,
                expression_index,
                target_duration=context_expr_duration,
                use_expression_audio=True,
                expression_video_clip_path=str(expression_video_path)
            )
            
            # Step 5: Concatenate context+expression → slide (direct, no transition)
            logger.info("Concatenating context+expression → slide (direct, no transition)")
            long_form_temp_path = self.output_dir / f"temp_long_form_{safe_expression}.mkv"
            self._register_temp_file(long_form_temp_path)

            concat_filter_with_explicit_map(
                str(context_expr_path),
                str(educational_slide),
                str(long_form_temp_path)
            )
            
            # Step 6: Add logo at right-top with 50% opacity (long-form video)
            logger.info("Adding logo to long-form video (right-top, 50% opacity)")
            long_form_with_logo_path = self.output_dir / f"temp_long_form_with_logo_{safe_expression}.mkv"
            self._register_temp_file(long_form_with_logo_path)
            
            logo_path = Path(__file__).parent.parent.parent / "assets" / "top_logo.png"
            if logo_path.exists():
                try:
                    # Load long-form video
                    long_form_input = ffmpeg.input(str(long_form_temp_path))
                    long_form_video = long_form_input['v']
                    long_form_audio = long_form_input['a'] if 'a' in long_form_input else None
                    
                    # Load logo and apply 80% opacity
                    logo_input = ffmpeg.input(str(logo_path))
                    # Scale logo to appropriate size (e.g., 150px height)
                    logo_video = logo_input['v'].filter('scale', -1, 150)
                    # Apply 80% opacity: convert to rgba format and use geq filter to adjust alpha
                    logo_video = logo_video.filter('format', 'rgba')
                    # Use geq filter to set alpha to 80% (0.8 * 255 = 204)
                    logo_video = logo_video.filter('geq', r='r(X,Y)', g='g(X,Y)', b='b(X,Y)', a='0.8*alpha(X,Y)')
                    
                    # Get video dimensions for positioning
                    # Overlay at right-top: x = W - w - margin, y = margin
                    margin = 20  # 20px margin from edges
                    overlay_x = f'W-w-{margin}'  # Right edge minus logo width minus margin
                    overlay_y = margin  # Top margin
                    
                    # Overlay logo on long-form video
                    final_video = ffmpeg.overlay(
                        long_form_video,
                        logo_video,
                        x=overlay_x,
                        y=overlay_y
                    )
                    
                    # Output video with logo
                    if long_form_audio:
                        (
                            ffmpeg.output(
                                final_video,
                                long_form_audio,
                                str(long_form_with_logo_path),
                                vcodec='libx264',
                                acodec='aac',
                                ac=2,
                                ar=48000,
                                preset='fast',
                                crf=23
                            )
                            .overwrite_output()
                            .run(capture_stdout=True, capture_stderr=True)
                        )
                    else:
                        (
                            ffmpeg.output(
                                final_video,
                                str(long_form_with_logo_path),
                                vcodec='libx264',
                                preset='fast',
                                crf=23
                            )
                            .overwrite_output()
                            .run(capture_stdout=True, capture_stderr=True)
                        )
                    
                    logger.info("Added logo to long-form video (right-top, 50% opacity)")
                    # Use video with logo for final audio gain
                    long_form_temp_path = long_form_with_logo_path
                except Exception as e:
                    logger.warning(f"Failed to add logo to long-form video: {e}, continuing without logo")
                    # Continue with original video if logo addition fails
            else:
                logger.debug(f"Logo file not found: {logo_path}, continuing without logo")
            
            # Step 7: Apply final audio gain
            logger.info("Applying final audio gain to long-form video")
            from langflix.media.ffmpeg_utils import apply_final_audio_gain
            apply_final_audio_gain(str(long_form_temp_path), str(output_path), gain_factor=1.69)
            
            logger.info(f"✅ Long-form video created: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error creating long-form video: {e}")
            raise

    @handle_error_decorator(
        ErrorContext(
            operation="create_short_form_from_long_form",
            component="core.video_editor"
        ),
        retry=False,
        fallback=False
    )
    def create_short_form_from_long_form(
        self,
        long_form_video_path: str,
        expression: ExpressionAnalysis,
        expression_index: int = 0
    ) -> str:
        """
        Create short-form video (9:16) from long-form video with special layout:
        - Long-form video: centered, height 960px, left/right cropped (no stretch)
        - Expression text: displayed at top (outside long-form video, black screen)
        - Subtitles: displayed at bottom (outside long-form video, black screen)
        
        Args:
            long_form_video_path: Path to long-form video (16:9 or original ratio)
            expression: ExpressionAnalysis object
            expression_index: Index of expression (for voice alternation)
            
        Returns:
            Path to created short-form video
        """
        try:
            from langflix.utils.filename_utils import sanitize_for_expression_filename
            safe_expression = sanitize_for_expression_filename(expression.expression)
            output_filename = f"short_form_{safe_expression}.mkv"
            
            # Use short_videos directory
            short_videos_dir = self.short_videos_dir
            short_videos_dir.mkdir(parents=True, exist_ok=True)
            output_path = short_videos_dir / output_filename
            
            logger.info(f"Creating short-form video from long-form video: {expression.expression}")

            # Get layout configuration from settings
            target_width, target_height = settings.get_short_video_dimensions()
            long_form_video_height = settings.get_long_form_video_height()
            
            # Step 1: Scale long-form video to height 960px, maintain aspect ratio, crop left/right
            # This ensures no stretching - video is cropped if needed
            from langflix.media.ffmpeg_utils import get_video_params
            long_form_vp = get_video_params(long_form_video_path)
            long_form_width = long_form_vp.width or target_width
            long_form_height = long_form_vp.height or target_height
            
            # Calculate scale to fit height 960px
            scale_factor = long_form_video_height / long_form_height
            scaled_width = int(long_form_width * scale_factor)
            scaled_height = long_form_video_height
            
            # If scaled width exceeds target width, crop from center
            crop_x = 0
            if scaled_width > target_width:
                crop_x = (scaled_width - target_width) // 2
                scaled_width = target_width
            
            logger.info(
                f"Scaling long-form video: {long_form_width}x{long_form_height} -> "
                f"{scaled_width}x{scaled_height} (crop_x={crop_x})"
            )
            
            # Step 2: Create scaled and cropped long-form video
            long_form_scaled_path = self.output_dir / f"temp_long_form_scaled_{safe_expression}.mkv"
            self._register_temp_file(long_form_scaled_path)
            
            long_form_input = ffmpeg.input(str(long_form_video_path))
            video_stream = long_form_input['v']
            
            # Scale to height 960px
            video_stream = ffmpeg.filter(video_stream, 'scale', -1, scaled_height)
            
            # Crop from center if width exceeds target
            if crop_x > 0:
                video_stream = ffmpeg.filter(
                    video_stream,
                    'crop',
                    target_width,
                    scaled_height,
                    crop_x,
                    0
                )
            
            # Get audio stream
            audio_stream = None
            try:
                audio_stream = long_form_input['a']
            except (KeyError, AttributeError):
                logger.debug("No audio stream in long-form video")
            
            # Output scaled long-form video
            if audio_stream:
                (
                    ffmpeg.output(
                        video_stream,
                        audio_stream,
                        str(long_form_scaled_path),
                        vcodec='libx264',
                        acodec='aac',
                        ac=2,
                        ar=48000,
                        preset='fast',
                        crf=23
                    )
                    .overwrite_output()
                    .run(quiet=True)
                )
            else:
                (
                    ffmpeg.output(
                        video_stream,
                        str(long_form_scaled_path),
                        vcodec='libx264',
                        preset='fast',
                        crf=23
                    )
                    .overwrite_output()
                    .run(quiet=True)
                )
            
            # Step 3: Create 1080x1920 black background
            # Calculate y_offset to center long-form video vertically
            y_offset = (target_height - scaled_height) // 2  # Center vertically
            
            logger.info(f"Centering long-form video at y_offset={y_offset}")
            
            # Step 4: Create final layout with expression text at top and subtitles at bottom
            # Use pad filter to create black background and place long-form video in center
            final_input = ffmpeg.input(str(long_form_scaled_path))
            final_video = final_input['v']
            
            # Pad to create black background with long-form video centered
            final_video = ffmpeg.filter(
                final_video,
                'pad',
                target_width,
                target_height,
                0,  # x offset (centered horizontally)
                y_offset,  # y offset (centered vertically)
                color='black'
            )

            # Escape text for drawtext (helper function used for all text)
            def escape_drawtext_string(text):
                escaped = text.replace("\\", "\\\\")
                escaped = escaped.replace(":", "\\:")
                escaped = escaped.replace("'", "\\'")
                escaped = escaped.replace("[", "\\[")
                escaped = escaped.replace("]", "\\]")
                return escaped

            font_file = self._get_font_option()

            # Add catchy keywords at top (outside long-form video area, in top black padding)
            # Display catchy keywords if available (positioning from config)
            if hasattr(expression, 'catchy_keywords') and expression.catchy_keywords:
                import random
                
                # Get all keywords (no limit, display all in one line)
                keywords = expression.catchy_keywords
                
                # Format keywords: add "#" prefix to each
                formatted_keywords = [f"#{keyword}" for keyword in keywords]
                
                # Generate random color for each keyword (deterministic based on keyword text)
                keyword_colors = []
                for keyword in formatted_keywords:
                    random.seed(hash(keyword) % (2**32))  # Deterministic but varied per keyword
                    r = random.randint(100, 255)
                    g = random.randint(100, 255)
                    b = random.randint(100, 255)
                    keyword_colors.append(f"0x{b:02x}{g:02x}{r:02x}")
                
                # Build text with commas: "#keyword1, #keyword2, #keyword3"
                # Render each keyword separately with its own color
                # If total width exceeds max_width, wrap to new lines
                font_size = settings.get_keywords_font_size()
                y_position = settings.get_keywords_y_position()
                line_height_factor = settings.get_keywords_line_height_factor()
                line_height = font_size * line_height_factor  # Line spacing

                # Calculate approximate character width (rough estimate: font_size * 0.6 for monospace-like)
                char_width_estimate = font_size * 0.6
                comma_separator = ",   "  # Comma with double space
                comma_width = len(comma_separator) * char_width_estimate

                # Maximum width for keywords (configurable percentage of video width)
                max_width_percent = settings.get_keywords_max_width_percent()
                max_width = target_width * max_width_percent
                
                # Group keywords into lines based on width
                keyword_lines = []  # List of lists, each inner list is a line of keyword indices
                current_line = []
                current_line_width = 0
                
                for i, keyword in enumerate(formatted_keywords):
                    keyword_width = len(keyword) * char_width_estimate
                    
                    # Check if adding this keyword would exceed max width
                    # Account for comma if not first keyword in line
                    needed_width = keyword_width
                    if current_line:  # Not first keyword in line
                        needed_width += comma_width
                    
                    if current_line_width + needed_width > max_width and current_line:
                        # Start new line
                        keyword_lines.append(current_line)
                        current_line = [i]
                        current_line_width = keyword_width
                    else:
                        # Add to current line
                        if current_line:  # Not first keyword
                            current_line_width += comma_width
                        current_line.append(i)
                        current_line_width += keyword_width
                
                # Add last line if not empty
                if current_line:
                    keyword_lines.append(current_line)
                
                # Render keywords line by line
                for line_idx, line_keyword_indices in enumerate(keyword_lines):
                    line_y = y_position + (line_idx * line_height)
                    
                    # Get keywords and colors for this line
                    line_keywords = [formatted_keywords[i] for i in line_keyword_indices]
                    line_colors = [keyword_colors[i] for i in line_keyword_indices]
                    
                    # Calculate total width of this line for centering
                    line_text = comma_separator.join(line_keywords)
                    line_width = len(line_text) * char_width_estimate
                    
                    # Calculate starting x position: center the entire line
                    # First keyword starts at: center - (half of remaining text width)
                    remaining_after_first = comma_separator.join(line_keywords[1:]) if len(line_keywords) > 1 else ""
                    remaining_width = len(remaining_after_first) * char_width_estimate if remaining_after_first else 0
                    
                    # Add each keyword with its own color, positioned sequentially
                    current_x_offset = 0  # Track cumulative offset from center
                    for i, (keyword, color) in enumerate(zip(line_keywords, line_colors)):
                        escaped_keyword = escape_drawtext_string(keyword)

                        # Calculate x position for this keyword
                        if i == 0:
                            # First keyword: center minus half of remaining text width
                            x_expr = f"(w-text_w)/2-{remaining_width:.0f}"
                        else:
                            # Subsequent keywords: after previous keyword + comma
                            # Calculate width of previous keyword and comma
                            prev_keyword = line_keywords[i-1]
                            prev_keyword_width = len(prev_keyword) * char_width_estimate
                            current_x_offset += prev_keyword_width + comma_width
                            x_expr = f"(w-text_w)/2-{remaining_width:.0f}+{current_x_offset:.0f}"
                        
                        keyword_args = {
                            'text': escaped_keyword,
                            'fontsize': font_size,
                            'fontcolor': color,  # Random color per keyword
                            'x': x_expr,
                            'y': line_y,
                            'borderw': settings.get_keywords_border_width(),
                            'bordercolor': settings.get_keywords_border_color()
                        }

                        # Add fontfile if available
                        if font_file:
                            font_path = font_file.replace('fontfile=', '').replace(':', '')
                            if font_path:
                                keyword_args['fontfile'] = font_path

                        final_video = ffmpeg.filter(final_video, 'drawtext', **keyword_args)

                        # Add comma after keyword (except last in line)
                        if i < len(line_keywords) - 1:
                            # Comma position: after current keyword
                            keyword_width = len(keyword) * char_width_estimate
                            comma_x_offset = current_x_offset + keyword_width
                            if i == 0:
                                comma_x = f"(w-text_w)/2-{remaining_width:.0f}+{keyword_width:.0f}"
                            else:
                                comma_x = f"(w-text_w)/2-{remaining_width:.0f}+{comma_x_offset:.0f}"
                            
                            comma_args = {
                                'text': ', ',
                                'fontsize': font_size,
                                'fontcolor': settings.get_keywords_text_color(),  # Comma color from config
                                'x': comma_x,
                                'y': line_y,
                                'borderw': settings.get_keywords_border_width(),
                                'bordercolor': settings.get_keywords_border_color()
                            }
                            if font_file:
                                font_path = font_file.replace('fontfile=', '').replace(':', '')
                                if font_path:
                                    comma_args['fontfile'] = font_path
                            final_video = ffmpeg.filter(final_video, 'drawtext', **comma_args)

                logger.info(f"Added {len(keywords)} catchy keywords in {len(keyword_lines)} line(s) with # prefix, each with random color")

            # Add expression text at bottom (bottom area of video, throughout entire video)
            # Expression + translation displayed throughout video duration (positioning from config)
            expression_text = expression.expression
            expression_translation = expression.expression_translation

            escaped_expression = escape_drawtext_string(expression_text)
            escaped_translation = escape_drawtext_string(expression_translation)

            # Add expression text at bottom (configurable styling)
            drawtext_args_1 = {
                'text': escaped_expression,
                'fontsize': settings.get_expression_font_size(),
                'fontcolor': settings.get_expression_text_color(),
                'x': '(w-text_w)/2',  # Center horizontally
                'y': settings.get_expression_y_position(),
                'borderw': settings.get_expression_border_width(),
                'bordercolor': settings.get_expression_border_color()
            }

            # Add fontfile if available
            if font_file:
                # Extract font path from "fontfile=path:" format
                font_path = font_file.replace('fontfile=', '').replace(':', '')
                if font_path:
                    drawtext_args_1['fontfile'] = font_path

            final_video = ffmpeg.filter(final_video, 'drawtext', **drawtext_args_1)

            # Add expression translation (line 2) below expression text
            drawtext_args_2 = {
                'text': escaped_translation,
                'fontsize': settings.get_translation_font_size(),
                'fontcolor': settings.get_translation_text_color(),
                'x': '(w-text_w)/2',  # Center horizontally
                'y': settings.get_translation_y_position(),
                'borderw': settings.get_translation_border_width(),
                'bordercolor': settings.get_translation_border_color()
            }

            if font_file:
                font_path = font_file.replace('fontfile=', '').replace(':', '')
                if font_path:
                    drawtext_args_2['fontfile'] = font_path

            final_video = ffmpeg.filter(final_video, 'drawtext', **drawtext_args_2)
            
            # Add logo at the very end to ensure it stays at absolute top (y=0)
            # Logo position: absolute top (y=0) of black padding, above hashtags
            # Reverted to original size to fix positioning issue
            logo_path = Path(__file__).parent.parent.parent / "assets" / "top_logo.png"
            if logo_path.exists():
                try:
                    # Load logo image and overlay it at top center
                    # Reverted to original size (150px height) to fix positioning
                    logo_input = ffmpeg.input(str(logo_path))
                    logo_video = logo_input['v'].filter('scale', -1, 150)  # Original size: 150px height
                    
                    # Overlay logo at absolute top center - LAST in filter chain
                    final_video = ffmpeg.overlay(
                        final_video,
                        logo_video,
                        x='(W-w)/2',  # Center horizontally (W = canvas width, w = logo width)
                        y=0,  # Absolute top - logo's top-left corner at y=0 (canvas top)
                        enable='between(t,0,999999)'  # Ensure logo appears throughout entire video
                    )
                    logger.info("Added logo at absolute top of short-form video (y=0, original size 150px)")
                except Exception as e:
                    logger.warning(f"Failed to add logo to short-form video: {e}")
            else:
                logger.debug(f"Logo file not found: {logo_path}")
            
            # Get audio stream
            final_audio = None
            try:
                final_audio = final_input['a']
            except (KeyError, AttributeError):
                logger.debug("No audio stream in scaled long-form video")
            
            # Step 5: Apply subtitles at bottom (outside long-form video area)
            # Subtitles will be applied using subtitle overlay (ASS format)
            # For now, output video with expression text, then apply subtitles
            temp_with_expression_path = self.output_dir / f"temp_short_with_expression_{safe_expression}.mkv"
            self._register_temp_file(temp_with_expression_path)
            
            if final_audio:
                (
                    ffmpeg.output(
                        final_video,
                        final_audio,
                        str(temp_with_expression_path),
                        vcodec='libx264',
                        acodec='aac',
                        ac=2,
                        ar=48000,
                        preset='fast',
                        crf=23
                    )
                    .overwrite_output()
                    .run(quiet=True)
                )
            else:
                (
                    ffmpeg.output(
                        final_video,
                        str(temp_with_expression_path),
                        vcodec='libx264',
                        preset='fast',
                        crf=23
                    )
                    .overwrite_output()
                    .run(quiet=True)
                )
            
            # Step 6: Skip subtitle overlay - long-form video already contains subtitles
            # Long-form video already has subtitles embedded, so we don't need to add them again
            logger.info("Skipping subtitle overlay - long-form video already contains subtitles")
            import shutil
            shutil.copy(str(temp_with_expression_path), str(output_path))
            
            logger.info(f"✅ Short-form video created: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error creating short-form video from long-form video: {e}")
            raise
    
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
        self.temp_manager.register_file(file_path)
    
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
    
    @retry_on_error(max_attempts=2, delay=1.0)
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
            timeline_filename = f"timeline_{sanitize_for_expression_filename(tts_path.split('/')[-1])}"
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
    
    def _cleanup_temp_files(self, preserve_short_format: bool = False) -> None:
        """Clean up all temporary files created by this VideoEditor instance.
        
        Args:
            preserve_short_format: If True, preserve short format expression videos
        """
        try:
            # Get list of files to preserve
            files_to_preserve = set()
            if preserve_short_format:
                files_to_preserve = set(self.short_format_temp_files)
                # Move preserved files to permanent location
                self._preserve_short_format_files(files_to_preserve)
            
            # Clean up files registered via _register_temp_file
            if hasattr(self, 'temp_manager'):
                # Remove preserved files from temp manager before cleanup
                if preserve_short_format:
                    for file_path in files_to_preserve:
                        if Path(file_path) in self.temp_manager.temp_files:
                            self.temp_manager.temp_files.remove(Path(file_path))
                self.temp_manager.cleanup_all()
            
            # Also clean up any temp_* files in output_dir (long_form_videos)
            # But exclude short format files if preserving
            if hasattr(self, 'output_dir') and self.output_dir.exists():
                temp_files = list(self.output_dir.glob("temp_*.mkv"))
                temp_files.extend(list(self.output_dir.glob("temp_*.txt")))
                temp_files.extend(list(self.output_dir.glob("temp_*.wav")))
                
                cleaned_count = 0
                for temp_file in temp_files:
                    if preserve_short_format and temp_file in files_to_preserve:
                        continue  # Skip preserved files
                    try:
                        if temp_file.exists():
                            temp_file.unlink()
                            cleaned_count += 1
                            logger.debug(f"Cleaned up temp file: {temp_file.name}")
                    except Exception as e:
                        logger.warning(f"Failed to cleanup temp file {temp_file}: {e}")
                
                logger.info(f"✅ Cleaned up {cleaned_count} temporary files from {self.output_dir}")
        except Exception as e:
            logger.warning(f"Error during temp file cleanup: {e}")
    
    def _preserve_short_format_files(self, files_to_preserve: set) -> None:
        """Move short format temp files to permanent location with better naming.
        
        Args:
            files_to_preserve: Set of Path objects to preserve
        """
        try:
            # Create expressions directory in short_videos
            expressions_dir = self.short_videos_dir / "expressions"
            expressions_dir.mkdir(parents=True, exist_ok=True)
            
            for temp_file in files_to_preserve:
                if not Path(temp_file).exists():
                    continue
                
                temp_path = Path(temp_file)
                filename = temp_path.name
                
                # Create better filename (remove temp_ prefix, keep expression name)
                # Priority: vstack files (complete individual videos) -> expression_{expression_name}.mkv
                if "_vstack_short_" in filename:
                    # Extract expression name from "temp_vstack_short_{expression}.mkv"
                    expression_part = filename.replace("temp_vstack_short_", "").replace(".mkv", "")
                    new_name = f"expression_{expression_part}.mkv"
                elif "_expr_clip_long_" in filename:
                    new_name = filename.replace("temp_expr_clip_long_", "expr_clip_")
                elif "_expr_repeated_" in filename:
                    new_name = filename.replace("temp_expr_repeated_", "expr_repeated_")
                else:
                    new_name = filename.replace("temp_", "")
                
                new_path = expressions_dir / new_name
                
                # Move file
                import shutil
                shutil.move(str(temp_path), str(new_path))
                logger.info(f"✅ Preserved short format expression video: {new_path}")
                
        except Exception as e:
            logger.warning(f"Error preserving short format files: {e}")
    
    def __del__(self):
        """Ensure temporary files are cleaned up when object is destroyed"""
        # TempFileManager handles cleanup automatically via atexit
        # Individual files are tracked globally, so no action needed here
        pass
    
    def _add_subtitles_to_context(self, video_path: str, expression: ExpressionAnalysis, group_id: Optional[str] = None) -> str:
        """Add target language subtitles to context video (translation only) using overlay helpers.
        
        Args:
            video_path: Path to context video
            expression: ExpressionAnalysis object
            group_id: Optional group ID for multi-expression groups (creates unique filename per group)
        
        Returns:
            Path to context video with subtitles
        """
        try:
            context_videos_dir = self.output_dir.parent / "context_videos"
            context_videos_dir.mkdir(parents=True, exist_ok=True)

            safe_name = sanitize_for_expression_filename(expression.expression)
            # Use group_id for multi-expression groups to create unique filename per group
            # Single-expression groups use expression name (backward compatible)
            if group_id:
                output_path = context_videos_dir / f"context_{group_id}.mkv"
            else:
                output_path = context_videos_dir / f"context_{safe_name}.mkv"
            
            # Check if file already exists (created by long-form)
            if output_path.exists():
                logger.info(f"Reusing existing context_with_subtitles: {output_path.name}")
                return str(output_path)

            subtitle_dir = self.output_dir.parent / "subtitles"
            sub_path = subs_overlay.find_subtitle_file(subtitle_dir, expression.expression)

            if sub_path and Path(sub_path).exists():
                import tempfile
                temp_dir = Path(tempfile.gettempdir())
                temp_sub_name = f"temp_dual_lang_{group_id or safe_name}.srt"
                temp_sub = temp_dir / temp_sub_name
                self._register_temp_file(temp_sub)
                
                # IMPORTANT: The subtitle file found by find_subtitle_file is already created
                # by create_dual_language_subtitle_file, which has timestamps adjusted relative
                # to context_start_time. However, we need to ensure the timestamps are correct
                # for the context video, which starts at 0.
                
                # Check if the subtitle file needs re-adjustment
                # If the subtitle file was created for this exact expression, it should already be adjusted
                # But we need to verify and potentially re-adjust if needed
                
                # For first context video, the subtitle file might have timestamps that need adjustment
                # Let's ensure the timestamps are correctly adjusted by reading and verifying
                source_sub = Path(sub_path)
                context_start_seconds = self._time_to_seconds(expression.context_start_time)
                
                # Copy the file first
                subs_overlay.create_dual_language_copy(source_sub, temp_sub)
                
                # Verify and adjust if needed: The subtitle file should already have timestamps
                # adjusted relative to context_start_time, but for the first context video,
                # we need to ensure the first subtitle starts at the correct time
                # If the subtitle file was created correctly, it should already be adjusted
                # But we'll apply it directly since create_dual_language_subtitle_file
                # already handles the timestamp adjustment via _generate_dual_language_srt
                
                logger.info(f"Applying subtitles to context video (file: {sub_path.name}, context_start: {expression.context_start_time})")
                
                # TICKET-040: Add expression subtitle at top (yellow) in addition to original subtitles
                # Calculate expression timing relative to context
                expression_start_relative = self._time_to_seconds(expression.expression_start_time) - \
                                           self._time_to_seconds(expression.context_start_time)
                expression_end_relative = self._time_to_seconds(expression.expression_end_time) - \
                                         self._time_to_seconds(expression.context_start_time)
                
                # Expression subtitle should only show during expression segment in context video
                # It will be visible when context video is concatenated with expression repeat
                # The subtitle timing is relative to context video start (0)
                expression_duration = expression_end_relative - expression_start_relative
                
                # Generate expression subtitle SRT (only for the expression segment in context)
                if not self.subtitle_processor:
                    raise RuntimeError("subtitle_processor is required for generating expression subtitles. Please pass subtitle_processor to VideoEditor.__init__()")
                
                expression_subtitle_content = self.subtitle_processor.generate_expression_subtitle_srt(
                    expression,
                    expression_start_relative,  # Start when expression begins in context
                    expression_end_relative     # End when expression ends in context (not including repeats)
                )
                
                # Save expression subtitle to temp file
                expression_subtitle_path = temp_dir / f"temp_expression_subtitle_{group_id or safe_name}.srt"
                expression_subtitle_path.write_text(expression_subtitle_content, encoding='utf-8')
                self._register_temp_file(expression_subtitle_path)
                
                # Apply dual subtitle layers (original at bottom + expression at top)
                # Pass absolute context times (not relative) - the function will extract context segment
                context_end_seconds = self._time_to_seconds(expression.context_end_time)
                subs_overlay.apply_dual_subtitle_layers(
                    str(video_path),
                    str(temp_sub),
                    str(expression_subtitle_path),
                    str(output_path),
                    context_start_seconds,  # Absolute start in source video
                    context_end_seconds     # Absolute end in source video
                )
            else:
                # drawtext fallback with translation only
                translation_text = ""
                if expression.translation and len(expression.translation) > 0:
                    translation_text = expression.translation[0]
                else:
                    translation_text = expression.expression_translation
                subs_overlay.drawtext_fallback_single_line(Path(video_path), translation_text, output_path)

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
            sanitized_expr = sanitize_for_expression_filename(expression.expression)
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
            output_path = self.output_dir / f"temp_expression_{sanitize_for_expression_filename(expression.expression)}.mkv"
            
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
    
    def _create_educational_slide(self, expression_source_video: str, expression: ExpressionAnalysis, expression_index: int = 0, target_duration: Optional[float] = None, use_expression_audio: bool = False, expression_video_clip_path: Optional[str] = None) -> str:
        """Create educational slide with background image, text, and audio.
        
        Args:
            expression_source_video: Source video path for audio extraction (if use_expression_audio=False)
            expression: ExpressionAnalysis object
            expression_index: Index for voice alternation
            target_duration: Target duration for slide (extends if needed)
            use_expression_audio: If True, use expression video clip audio instead of TTS
            expression_video_clip_path: Path to expression video clip (required if use_expression_audio=True)
        """
        try:
            # Ensure backward compatibility for expression_dialogue fields
            expression = self._ensure_expression_dialogue(expression)
            
            output_path = self.output_dir / f"temp_slide_{sanitize_for_expression_filename(expression.expression)}.mkv"
            self._register_temp_file(output_path)
            
            # Get background configuration with proper fallbacks
            background_input, input_type = self._get_background_config()
            
            from langflix import settings
            
            tts_config = settings.get_tts_config() or {}
            provider = settings.get_tts_provider() if tts_config else None
            provider_config = tts_config.get(provider, {}) if provider else {}
            provider_config_for_audio = provider_config if provider_config else {"response_format": "wav"}
            tts_enabled = settings.is_tts_enabled() and provider and bool(provider_config)
            
            # Create audio timeline directory (used for both TTS and original audio)
            tts_audio_dir = self.output_dir.parent / "tts_audio"
            tts_audio_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Audio timeline directory: {tts_audio_dir}")
            
            # Check if we should use expression audio instead of TTS
            if use_expression_audio and expression_video_clip_path:
                logger.info("Using expression audio from original video for slide (instead of TTS)")
                # IMPORTANT: expression_video_clip_path is actually the original expression_video_path
                # (expression_source_video) passed from create_educational_sequence caller
                # Extract audio from original video using expression timestamps for accurate matching
                expression_audio_path = self.output_dir / f"temp_expression_audio_{sanitize_for_expression_filename(expression.expression)}.wav"
                self._register_temp_file(expression_audio_path)
                
                # Extract audio from original expression video using expression timestamps
                # Use output seeking for accurate audio extraction
                expression_start_seconds = self._time_to_seconds(expression.expression_start_time)
                expression_end_seconds = self._time_to_seconds(expression.expression_end_time)
                expression_audio_duration = expression_end_seconds - expression_start_seconds
                
                # Verify we're using the original video path (not a clip)
                original_video_path = expression_video_clip_path  # This is actually the original video
                logger.info(f"Extracting expression audio from original video: {original_video_path}")
                logger.info(f"Expression timestamps: {expression.expression_start_time} - {expression.expression_end_time} ({expression_audio_duration:.2f}s)")
                logger.info(f"Audio segment: {expression_start_seconds:.2f}s - {expression_end_seconds:.2f}s (duration: {expression_audio_duration:.2f}s)")
                
                try:
                    # Use output seeking for accurate audio extraction from original video
                    # Input the original video file
                    audio_input = ffmpeg.input(str(original_video_path))
                    audio_stream = audio_input['a']
                except (KeyError, TypeError) as e:
                    logger.warning(f"No audio stream found in {original_video_path}: {e}, creating silent audio")
                    # Create silent audio as fallback
                    audio_stream = ffmpeg.input('anullsrc=channel_layout=stereo:sample_rate=48000', f='lavfi')
                    # If using silent audio, don't apply seeking
                    expression_start_seconds = 0
                    expression_audio_duration = target_duration or 3.0
                
                # Extract audio segment with output seeking (ss after input for accuracy)
                (
                    ffmpeg
                    .output(
                        audio_stream, 
                        str(expression_audio_path), 
                        acodec='pcm_s16le', 
                        ar=48000, 
                        ac=2,
                        ss=expression_start_seconds,  # Output seeking: apply after input for accuracy
                        t=expression_audio_duration  # Duration limit
                    )
                    .overwrite_output()
                    .run(quiet=True)
                )
                
                # Get expression audio duration
                from langflix.media.ffmpeg_utils import get_duration_seconds
                expression_audio_duration = get_duration_seconds(str(expression_audio_path))
                logger.info(f"Expression audio duration: {expression_audio_duration:.2f}s")
                
                # Loop expression audio based on repeat_count setting
                # CRITICAL: DO NOT extend to match full target_duration - only repeat_count times
                final_audio_path = self.output_dir / f"temp_expression_audio_final_{sanitize_for_expression_filename(expression.expression)}.wav"
                self._register_temp_file(final_audio_path)
                
                # Get repeat count from settings (default: 3, but educational slides use 2)
                # For educational slides, use expression repeat_count from settings
                from langflix import settings
                loop_count = settings.get_expression_repeat_count()
                logger.info(f"Looping expression audio {loop_count} times (repeat_count from settings)")
                
                # Create concat list for looping
                import tempfile
                import os
                concat_list_path = None
                try:
                    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as concat_file:
                        # Write absolute paths to concat file
                        abs_audio_path = Path(expression_audio_path).absolute()
                        for _ in range(loop_count):
                            concat_file.write(f"file '{abs_audio_path}'\n")
                        concat_list_path = concat_file.name
                    
                    # Concatenate audio to loop using concat demuxer
                    (
                        ffmpeg
                        .input(concat_list_path, format='concat', safe=0)
                        .output(str(final_audio_path), acodec='pcm_s16le', ar=48000, ac=2)
                        .overwrite_output()
                        .run(quiet=True)
                    )
                    
                    # Get final audio duration (should be expression audio duration * repeat_count)
                    final_audio_duration = get_duration_seconds(str(final_audio_path))
                    logger.info(f"✅ Audio looped {loop_count}x: final duration {final_audio_duration:.2f}s (expression audio: {expression_audio_duration:.2f}s)")
                finally:
                    # Clean up concat file
                    if concat_list_path and os.path.exists(concat_list_path):
                        try:
                            os.unlink(concat_list_path)
                        except Exception:
                            pass
                
                audio_2x_path = final_audio_path
                # Use exact audio duration (expression audio * repeat_count) - stop video when audio ends
                # Do NOT extend with target_duration or padding - video should end when all audio repeats finish
                slide_duration = final_audio_duration
                
                # CRITICAL: When using expression audio, ignore target_duration to prevent extra playback
                # Video should stop exactly when all expression audio repeats finish
                if target_duration is not None and target_duration > slide_duration:
                    logger.info(f"Ignoring target_duration ({target_duration:.2f}s) for expression audio slide - using exact audio duration ({slide_duration:.2f}s)")
                    logger.info(f"Video will stop when all {loop_count} expression audio repeats finish (no extra playback)")
                
                logger.info(f"Using expression audio for slide: {audio_2x_path}")
                logger.info(f"Expression audio duration: {expression_audio_duration:.2f}s, Repeat count: {loop_count}, Final slide duration: {slide_duration:.2f}s (exact match, no padding)")
                
                # For consistency with other branches, set audio_path and expression_duration
                audio_path = audio_2x_path
                expression_duration = slide_duration
                
            # Check if TTS is enabled and decide on audio workflow
            elif tts_enabled:
                try:
                    from langflix.tts.factory import create_tts_client
                    
                    # Prepare dialogue text for TTS generation
                    tts_text = expression.expression_dialogue or ""
                    if not isinstance(tts_text, str):
                        tts_text = str(tts_text)
                    
                    MAX_TTS_CHARS = 500  # Adjust based on provider
                    if len(tts_text) > MAX_TTS_CHARS:
                        logger.warning(f"TTS text too long ({len(tts_text)} chars), truncating to {MAX_TTS_CHARS}")
                        tts_text = tts_text[:MAX_TTS_CHARS]
                    
                    logger.info(f"TTS enabled - generating synthetic audio for: '{tts_text}'")
                    logger.info(f"Using TTS provider: {provider}")
                    logger.info(f"Provider config keys: {list(provider_config.keys())}")
                    
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
                        expression, expression_source_video, tts_audio_dir, expression_index, provider_config_for_audio
                    )
            else:
                if settings.is_tts_enabled():
                    logger.warning("TTS is enabled but provider configuration is missing; falling back to original audio extraction")
                else:
                    logger.info("TTS is disabled - using original audio extraction")
                audio_path, expression_duration = self._extract_original_audio_timeline(
                    expression, expression_source_video, tts_audio_dir, expression_index, provider_config_for_audio
                )
            
            # audio_path and expression_duration are now set by one of the three branches above
            # Prepare final audio path and slide duration
            audio_2x_path = audio_path  # Unified variable for slide audio
            
            # For expression audio, slide_duration is already set exactly to audio duration (no padding)
            # For TTS/original audio, add small padding
            if use_expression_audio and expression_video_clip_path:
                # Expression audio: slide_duration already set to exact audio duration (no padding, no target_duration override)
                # Do not modify slide_duration here - it's already set correctly above
                # CRITICAL: Do NOT override with target_duration for expression audio
                logger.info(f"Expression audio slide: using exact duration {slide_duration:.2f}s (no padding, no target_duration override)")
            else:
                # TTS or original audio: add small padding
                slide_duration = expression_duration + 0.5  # Add small padding for slide
                
                # If target_duration is provided, use that instead (for hstack matching)
                # But only for non-expression-audio cases
                if target_duration is not None and target_duration > slide_duration:
                    slide_duration = target_duration
                    logger.info(f"Using target duration for hstack: {slide_duration:.2f}s (audio: {expression_duration:.2f}s)")
            
            logger.info(f"Using timeline audio directly: {audio_2x_path}")
            logger.info(f"Timeline duration: {expression_duration:.2f}s, Final slide duration: {slide_duration:.2f}s")
            
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
                
                # Add the 2x TTS audio input with 40% volume boost
                audio_input = ffmpeg.input(str(audio_2x_path))
                # Apply 40% volume boost to final video audio
                boosted_audio = audio_input['a'].filter('volume', '1.25')
                
                logger.info(f"Creating slide with video duration: {slide_duration}s, audio file: {audio_2x_path} (40% volume boost)")
                
                # Create the slide with both video and boosted audio directly
                # CRITICAL: Trim audio to match slide duration to prevent infinite looping
                try:
                    video_args = self._get_video_output_args()
                    
                    # Trim audio to exact slide_duration to prevent infinite looping
                    trimmed_audio = audio_input['a'].filter('atrim', duration=slide_duration).filter('asetpts', 'PTS-STARTPTS')
                    boosted_audio = trimmed_audio.filter('volume', '1.25')
                    
                    (
                        ffmpeg
                        .output(video_input['v'], boosted_audio, str(output_path),
                               vf=f"scale=1280:720,{video_filter}",
                               vcodec=video_args.get('vcodec', 'libx264'),
                               acodec=video_args.get('acodec', 'aac'),
                               preset=video_args.get('preset', 'veryfast'),
                               crf=video_args.get('crf', 25))
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
                    # Trim audio to exact slide_duration to prevent infinite looping
                    trimmed_audio = audio_input['a'].filter('atrim', duration=slide_duration).filter('asetpts', 'PTS-STARTPTS')
                    
                    video_args = self._get_video_output_args()
                    (
                        ffmpeg
                        .output(video_input['v'], trimmed_audio, str(output_path),
                               vf="scale=1280:720",
                               vcodec=video_args.get('vcodec', 'libx264'),
                               acodec=video_args.get('acodec', 'aac'),
                               preset=video_args.get('preset', 'veryfast'),
                               crf=video_args.get('crf', 25))
                        .overwrite_output()
                        .run(capture_stdout=True, capture_stderr=True)
                    )
                except Exception as fallback_error:
                    logger.error(f"Even fallback slide creation failed: {fallback_error}")
                    # Final emergency fallback - basic slide with audio
                    try:
                        video_input = ffmpeg.input("color=c=0x1a1a2e:size=1280:720", f="lavfi", t=slide_duration)
                        audio_input = ffmpeg.input(str(audio_2x_path))
                        
                        video_args = self._get_video_output_args()
                        (
                            ffmpeg
                            .output(video_input['v'], audio_input['a'], str(output_path),
                                   vcodec=video_args.get('vcodec', 'libx264'),
                                   acodec=video_args.get('acodec', 'aac'),
                                   preset=video_args.get('preset', 'veryfast'),
                                   crf=video_args.get('crf', 25))
                            .overwrite_output()
                            .run(quiet=True)
                        )
                    except Exception as emergency_error:
                        logger.error(f"Emergency fallback also failed: {emergency_error}")
                        # Last resort: create basic video without audio
                        video_args = self._get_video_output_args()
                        (
                            ffmpeg
                            .input("color=c=0x1a1a2e:size=1280:720", f="lavfi", t=slide_duration)
                            .output(str(output_path),
                                   vcodec=video_args.get('vcodec', 'libx264'),
                                   acodec=video_args.get('acodec', 'aac'),
                                   preset=video_args.get('preset', 'veryfast'),
                                   crf=video_args.get('crf', 25))
                            .overwrite_output()
                            .run(quiet=True)
                        )
            
            # Move temp slide to final location in slides directory
            slides_dir = self.output_dir.parent / "slides"
            slides_dir.mkdir(exist_ok=True)
            final_slide_path = slides_dir / f"slide_{sanitize_for_expression_filename(expression.expression)}.mkv"
            
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
            
            output_path = self.output_dir / f"temp_slide_silent_{sanitize_for_expression_filename(expression.expression)}.mkv"
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
                    video_args = self._get_video_output_args()
                    (
                        ffmpeg
                        .output(video_input['v'], str(output_path),
                               vf=f"scale=1280:720,{video_filter}",
                               vcodec=video_args.get('vcodec', 'libx264'),
                               t=duration,
                               preset=video_args.get('preset', 'veryfast'),
                               crf=video_args.get('crf', 25))
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
                    video_args = self._get_video_output_args()
                    (
                        ffmpeg
                        .output(video_out, audio_out, str(output_path),
                               vcodec=video_args.get('vcodec', 'libx264'),
                               acodec=video_args.get('acodec', 'aac'),
                               preset=video_args.get('preset', 'veryfast'),
                               ac=2, ar=48000, crf=video_args.get('crf', 25))
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
            timeline_path = self.output_dir / f"temp_timeline_{sanitize_for_expression_filename(text)}.wav"
            self._register_temp_file(timeline_path)
            
            try:
                # Create silence segments
                silence_1s_path = self.output_dir / f"temp_silence_1s_{sanitize_for_expression_filename(text)}.wav"
                silence_0_5s_path = self.output_dir / f"temp_silence_0_5s_{sanitize_for_expression_filename(text)}.wav"
                
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
                tts_wav_path = self.output_dir / f"temp_tts_{sanitize_for_expression_filename(text)}.wav"
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
                concat_file = self.output_dir / f"temp_concat_timeline_{sanitize_for_expression_filename(text)}.txt"
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
                    original_audio_filename = f"tts_original_{sanitize_for_expression_filename(text)}.{audio_format}"
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

    def _extract_context_audio_timeline(
        self, 
        expression: ExpressionAnalysis, 
        context_video_path: str, 
        output_dir: Path, 
        expression_index: int = 0,
        repeat_count: int = None
    ) -> Tuple[Path, float]:
        """
        Extract expression audio timeline from context video using relative timestamps.
        This ensures audio-video synchronization in short videos.
        
        Args:
            expression: Expression analysis object
            context_video_path: Path to context video (already sliced from original)
            output_dir: Output directory for audio files
            expression_index: Index for unique filename generation
            repeat_count: Number of repetitions for expression
            
        Returns:
            Tuple of (audio_timeline_path, duration)
        """
        try:
            from langflix.audio.original_audio_extractor import create_original_audio_timeline
            from langflix import settings
            
            if repeat_count is None:
                repeat_count = settings.get_expression_repeat_count()
            
            logger.info(f"Extracting context audio timeline with {repeat_count} repetitions")
            
            # Calculate relative timestamps within context video
            context_start_seconds = self._time_to_seconds(expression.context_start_time)
            expression_start_seconds = self._time_to_seconds(expression.expression_start_time)
            expression_end_seconds = self._time_to_seconds(expression.expression_end_time)
            
            # Convert to relative position within context video (starts at 0)
            relative_start = expression_start_seconds - context_start_seconds
            relative_end = expression_end_seconds - context_start_seconds
            
            # Create a modified expression object with relative timestamps
            from langflix.core.models import ExpressionAnalysis
            relative_expression = ExpressionAnalysis(
                expression=expression.expression,
                translation=expression.translation,
                context_start_time=self._seconds_to_time(0),  # Context starts at 0
                context_end_time=self._seconds_to_time(relative_end - relative_start + 2),  # Add buffer
                expression_start_time=self._seconds_to_time(relative_start),
                expression_end_time=self._seconds_to_time(relative_end),
                dialogue_line=expression.dialogue_line,
                dialogue_translation=expression.dialogue_translation,
                similar_expressions=expression.similar_expressions
            )
            
            logger.info(f"Context audio extraction - relative timestamps: {relative_start:.2f}s - {relative_end:.2f}s")
            logger.info(f"🎵 Using context video for audio extraction: {context_video_path}")
            
            # Extract audio timeline from context video using relative timestamps
            # Use direct context video extraction to avoid any confusion
            audio_timeline_path, duration = self._create_context_audio_timeline_direct(
                relative_expression, context_video_path, output_dir, expression_index, repeat_count
            )
            
            logger.info(f"Context audio timeline extracted: {audio_timeline_path} ({duration:.2f}s)")
            return audio_timeline_path, duration
            
        except Exception as e:
            logger.error(f"❌ Error extracting context audio timeline: {e}")
            # Fallback: Use context video directly with original timestamps
            logger.warning(f"⚠️ Falling back to direct context video audio extraction")
            logger.warning(f"⚠️ Using context video: {context_video_path}")
            
            # Use context video directly with original expression timestamps
            # This may not be perfectly aligned but is better than using original video
            return self._extract_original_audio_timeline(
                expression, context_video_path,  # Use context video instead of original
                output_dir, expression_index, {}, repeat_count
            )
    
    def _create_context_audio_timeline_direct(
        self, 
        expression: ExpressionAnalysis, 
        context_video_path: str, 
        output_dir: Path, 
        expression_index: int = 0,
        repeat_count: int = None
    ) -> Tuple[Path, float]:
        """
        Create audio timeline directly from context video without using OriginalAudioExtractor.
        This ensures we use the context video path directly.
        
        Args:
            expression: Expression analysis object with relative timestamps
            context_video_path: Path to context video
            output_dir: Output directory for audio files
            expression_index: Index for unique filename generation
            repeat_count: Number of repetitions for expression
            
        Returns:
            Tuple of (audio_timeline_path, duration)
        """
        try:
            logger.info(f"🎵 Creating context audio timeline directly from: {context_video_path}")
            
            # Parse timestamps
            start_seconds = self._time_to_seconds(expression.expression_start_time)
            end_seconds = self._time_to_seconds(expression.expression_end_time)
            segment_duration = end_seconds - start_seconds
            
            logger.info(f"🎵 Expression segment: {start_seconds:.2f}s - {end_seconds:.2f}s ({segment_duration:.2f}s)")
            
            # Create temporary directory for audio processing
            import tempfile
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Extract base audio segment from context video
                base_audio_path = temp_path / f"expression_{expression_index}_base.wav"
                
                # Extract audio segment using FFmpeg
                (ffmpeg.input(context_video_path, ss=start_seconds, t=segment_duration)
                 .audio
                 .output(str(base_audio_path), acodec='pcm_s16le', ar=48000, ac=2)
                 .overwrite_output()
                 .run(quiet=True))
                
                logger.info(f"🎵 Base audio segment extracted: {segment_duration:.2f}s")
                
                # Create silence files
                silence_1s_path = temp_path / "silence_1s.wav"
                silence_05s_path = temp_path / "silence_0.5s.wav"
                
                # Generate silence files
                (ffmpeg.input('anullsrc=r=48000:cl=stereo', f='lavfi', t=1.0)
                 .output(str(silence_1s_path), acodec='pcm_s16le', ar=48000, ac=2)
                 .overwrite_output()
                 .run(quiet=True))
                
                (ffmpeg.input('anullsrc=r=48000:cl=stereo', f='lavfi', t=0.5)
                 .output(str(silence_05s_path), acodec='pcm_s16le', ar=48000, ac=2)
                 .overwrite_output()
                 .run(quiet=True))
                
                # Create concatenation list for timeline
                concat_list_path = temp_path / "concat_list.txt"
                with open(concat_list_path, 'w') as f:
                    f.write(f"file '{silence_1s_path}'\n")  # 1s start silence
                    
                    # Add audio segments with 0.5s silence between them
                    for i in range(repeat_count):
                        f.write(f"file '{base_audio_path}'\n")  # Expression audio
                        if i < repeat_count - 1:  # Don't add silence after the last repetition
                            f.write(f"file '{silence_05s_path}'\n")  # 0.5s silence
                    
                    f.write(f"file '{silence_1s_path}'\n")  # 1s end silence
                
                # Create final timeline audio
                safe_expression = sanitize_for_expression_filename(expression.expression)
                timeline_filename = f"context_audio_timeline_{safe_expression}_{expression_index}.wav"
                timeline_path = output_dir / timeline_filename
                
                # Concatenate all segments
                (ffmpeg.input(str(concat_list_path), format='concat', safe=0)
                 .output(str(timeline_path), acodec='pcm_s16le', ar=48000, ac=2)
                 .overwrite_output()
                 .run(quiet=True))
                
                # Calculate total duration
                total_duration = 2.0 + (segment_duration * repeat_count) + (0.5 * (repeat_count - 1))
                
                logger.info(f"🎵 Context audio timeline created: {timeline_path}")
                logger.info(f"🎵 Timeline duration: {total_duration:.2f}s ({repeat_count} repetitions)")
                
                # Register for cleanup
                self._register_temp_file(timeline_path)
                
                return timeline_path, total_duration
                
        except Exception as e:
            logger.error(f"❌ Error creating context audio timeline directly: {e}")
            raise
    
    def _extract_original_audio_timeline(
        self, 
        expression: ExpressionAnalysis, 
        original_video_path: str, 
        output_dir: Path, 
        expression_index: int = 0,
        provider_config: dict = None,
        repeat_count: int = None
    ) -> Tuple[Path, float]:
        """
        Extract audio from original video and create repetition timeline matching TTS behavior.
        
        Timeline pattern: 1s silence - audio - 0.5s silence - audio - 0.5s silence - audio - 1s silence
        
        Args:
            expression: ExpressionAnalysis object with timestamps
            original_video_path: Path to the original video file
            output_dir: Directory for output files
            expression_index: Index for unique filename generation
            provider_config: TTS provider config (for audio format compatibility)
            repeat_count: Number of times to repeat audio (if None, use TTS repeat count from settings)
            
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
                audio_format=audio_format,
                repeat_count=repeat_count
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
    
    def _seconds_to_time(self, seconds: float) -> str:
        """
        Convert seconds to SRT timestamp format.
        
        Args:
            seconds: Time in seconds as float
            
        Returns:
            Timestamp in format "HH:MM:SS.mmm"
        """
        try:
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = seconds % 60
            return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"
        except Exception as e:
            logger.error(f"Error converting seconds to timestamp: {e}")
            return "00:00:00.000"

    def _get_original_video_path(self, context_video_path: str, subtitle_file_path: str = None) -> str:
        """
        Get original video path for audio extraction using the same logic as educational videos.
        
        Context videos are clips without audio, so we need to find the original video file
        that corresponds to the subtitle file being processed.
        
        Args:
            context_video_path: Path to context video (always a clip)
            subtitle_file_path: Path to subtitle file for matching (if available)
            
        Returns:
            Path to original video file for accurate timestamp-based audio extraction
        """
        context_path = Path(context_video_path)
        
        # Context videos are always clips - find the original video file
        logger.info(f"Finding original video for context clip: {context_path.name}")
        
        # If we have subtitle file path, use the same logic as educational videos
        if subtitle_file_path:
            from langflix.core.video_processor import VideoProcessor
            video_processor = VideoProcessor()
            original_video = video_processor.find_video_file(subtitle_file_path)
            if original_video and original_video.exists():
                logger.info(f"Found original video using subtitle matching: {original_video}")
                return str(original_video)
        
        # Fallback: Try to find original video in assets/media (old logic)
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

    @handle_error_decorator(
        ErrorContext(
            operation="create_short_format_video",
            component="core.video_editor"
        ),
        retry=False,  # Video processing shouldn't auto-retry
        fallback=False
    )
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

    def _create_transition_video(
        self,
        duration: float,
        image_path: str,
        sound_effect_path: str,
        source_video_path: str,
        aspect_ratio: str = "16:9"
    ) -> Path:
        """
        Create transition video from static image with sound effect.

        Args:
            duration: Transition duration in seconds (e.g., 0.3s)
            image_path: Path to transition image
            sound_effect_path: Path to sound effect MP3
            source_video_path: Source video to match codec/resolution/params
            aspect_ratio: "16:9" for long-form or "9:16" for short-form

        Returns:
            Path to created transition video
        """
        try:
            from langflix.media.ffmpeg_utils import get_duration_seconds

            # Resolve asset paths (relative to project root)
            project_root = Path(__file__).parent.parent.parent
            image_full_path = project_root / image_path
            sound_full_path = project_root / sound_effect_path

            if not image_full_path.exists():
                logger.warning(f"Transition image not found: {image_full_path}, skipping transition")
                return None
            if not sound_full_path.exists():
                logger.warning(f"Sound effect not found: {sound_full_path}, skipping transition")
                return None

            # Get source video resolution and params
            probe = ffmpeg.probe(str(source_video_path))
            video_stream = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
            audio_stream = next((s for s in probe['streams'] if s['codec_type'] == 'audio'), None)

            width = int(video_stream.get('width', 1920)) if video_stream else 1920
            height = int(video_stream.get('height', 1080)) if video_stream else 1080

            # Parse frame rate safely
            fps = 25  # default
            if video_stream:
                r_frame_rate = video_stream.get('r_frame_rate', '25/1')
                try:
                    if '/' in r_frame_rate:
                        num, den = map(float, r_frame_rate.split('/'))
                        fps = num / den if den != 0 else 25
                    else:
                        fps = float(r_frame_rate)
                except (ValueError, ZeroDivisionError):
                    fps = 25

            sample_rate = int(audio_stream.get('sample_rate', 48000)) if audio_stream else 48000

            logger.info(f"Creating transition video: {duration}s, resolution: {width}x{height}, fps: {fps}")

            # Create output path
            transition_output = self.output_dir / f"temp_transition_{duration}s_{aspect_ratio.replace(':', 'x')}.mkv"
            self._register_temp_file(transition_output)

            # Create video from static image
            image_input = ffmpeg.input(str(image_full_path), loop=1, t=duration)

            # Scale image to match source resolution and set fps
            video_stream = (
                image_input['v']
                .filter('scale', width, height)
                .filter('fps', fps=fps)
            )

            # Add sound effect - trim to exact duration
            sound_input = ffmpeg.input(str(sound_full_path))
            audio_stream = sound_input['a'].filter('atrim', duration=duration).filter('asetpts', 'PTS-STARTPTS')

            # Get video output args
            video_args = self._get_video_output_args()

            # Create transition video with image and sound effect
            try:
                (
                    ffmpeg
                    .output(
                        video_stream,
                        audio_stream,
                        str(transition_output),
                       vcodec=video_args.get('vcodec', 'libx264'),
                       acodec=video_args.get('acodec', 'aac'),
                        preset=video_args.get('preset', 'fast'),
                        ac=2,
                        ar=sample_rate,
                        crf=video_args.get('crf', 23)
                    )
                .overwrite_output()
                    .run(capture_stdout=True, capture_stderr=True)
                )
            except ffmpeg.Error as e:
                stderr_msg = e.stderr.decode() if e.stderr else 'No stderr'
                logger.error(f"FFmpeg error creating transition: {stderr_msg}")
                raise

            # Verify duration
            actual_duration = get_duration_seconds(str(transition_output))
            logger.info(f"✅ Transition video created: {transition_output} (duration: {actual_duration:.3f}s)")

            return transition_output
            
        except Exception as e:
            logger.error(f"Error creating transition video: {e}")
            return None
    
    def _create_video_batch(self, video_paths: List[str], batch_number: int) -> str:
        """Create a single batch video from a list of video paths"""
        try:
            # Use short-form naming convention with episode info
            episode_name = getattr(self, 'episode_name', 'Unknown_Episode')
            batch_filename = f"short-form_{episode_name}_{batch_number:03d}.mkv"
            batch_path = self.short_videos_dir / batch_filename
            
            logger.info(f"Creating batch {batch_number} with {len(video_paths)} videos")
            
            # Create concat file
            concat_file = self.short_videos_dir / f"temp_concat_batch_{batch_number}.txt"
            self._register_temp_file(concat_file)
            
            with open(concat_file, 'w') as f:
                for video_path in video_paths:
                    f.write(f"file '{Path(video_path).absolute()}'\n")
            
            # Concatenate videos with concat demuxer (copy mode to preserve timestamps)
            concat_demuxer_if_uniform(concat_file, batch_path)
            
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
