#!/usr/bin/env python3
"""
Video Editor for LangFlix
Creates educational video sequences with context, expression clips, and educational slides
"""

import json
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
        self.cache_manager = get_cache_manager()  # Cache manager for TTS and other data
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
        expression_index: int = 0,
        pre_extracted_context_clip: Optional[Path] = None,
        language_code: Optional[str] = None
    ) -> str:
        """
        Create long-form video with unified layout:
        - context video → expression repeat (2회) → slide (expression audio 2회)
        - No transition (direct concatenation)
        - Maintains original aspect ratio (16:9 or other)

        Args:
            expression: ExpressionAnalysis object
            context_video_path: Path to context video (used for extracting expression clip if pre_extracted_context_clip not provided)
            expression_video_path: Path to expression video (for audio extraction)
            expression_index: Index of expression (for voice alternation)
            pre_extracted_context_clip: Optional pre-extracted context clip path (reused for multi-language)
            language_code: Optional language code for language-specific subtitle paths
            
        Returns:
            Path to created long-form video
        """
        try:
            from langflix.utils.filename_utils import sanitize_for_expression_filename
            safe_expression = sanitize_for_expression_filename(expression.expression)
            # Simplified filename: just expression name (e.g., "throw_em_off.mkv")
            output_filename = f"{safe_expression}.mkv"
            
            # Use expressions/ directory from paths (created by output_manager)
            if hasattr(self, 'output_dir') and hasattr(self.output_dir, 'parent'):
                # Try to find expressions directory in parent structure
                lang_dir = self.output_dir.parent
                if lang_dir.name in ['ko', 'ja', 'zh', 'en']:  # Language code
                    expressions_dir = lang_dir / "expressions"
                else:
                    expressions_dir = self.output_dir.parent / "expressions"
            else:
                # Fallback: create in output_dir parent
                expressions_dir = Path(self.output_dir).parent / "expressions"
                expressions_dir.mkdir(parents=True, exist_ok=True)
            
            output_path = expressions_dir / output_filename
            
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
            
            # Step 1a: Extract context clip from original video WITH subtitles (or reuse pre-extracted)
            if pre_extracted_context_clip and pre_extracted_context_clip.exists():
                # Reuse pre-extracted context clip (for multi-language support)
                logger.info(f"Reusing pre-extracted context clip: {pre_extracted_context_clip}")
                context_clip_path = pre_extracted_context_clip
                
                # VideoFactory now handles subtitle embedding into this clip ("Master Clip").
                # So we don't need to re-apply subtitles here.
                # If this is called from old code without Factory mastery, it might lack subtitles,
                # but we are assuming Factory control now.
            else:
                # Extract context clip from original video WITH subtitles
                self.output_dir.mkdir(parents=True, exist_ok=True)
                context_clip_path = self.output_dir / f"temp_context_clip_{safe_expression}.mkv"
                self._register_temp_file(context_clip_path)

                context_end_seconds = self._time_to_seconds(expression.context_end_time)
                context_duration = context_end_seconds - context_start_seconds

                logger.info(f"Extracting context clip with subtitles: {context_start_seconds:.2f}s - {context_end_seconds:.2f}s ({context_duration:.2f}s)")

                # Find and apply subtitle file
                subtitle_file = None
                # Try to find subtitle file in subtitles directory (language-specific if paths available)
                if hasattr(self, 'paths') and self.paths:
                    lang_paths = self.paths
                    if 'subtitles' in lang_paths:
                        subtitles_dir = lang_paths['subtitles']
                    else:
                        subtitles_dir = self.output_dir.parent / "subtitles"
                else:
                    subtitles_dir = self.output_dir.parent / "subtitles"
                
                if subtitles_dir.exists():
                    from langflix.utils.filename_utils import sanitize_for_expression_filename
                    safe_expression_short = sanitize_for_expression_filename(expression.expression)[:30]
                    subtitle_filename = f"expression_{expression_index+1:02d}_{safe_expression_short}.srt"
                    subtitle_file_path = Path(subtitles_dir) / subtitle_filename
                    
                    if subtitle_file_path.exists():
                        subtitle_file = subtitle_file_path
                        logger.info(f"Found subtitle file: {subtitle_file}")
                    else:
                        # Try to find any subtitle file matching the expression
                        pattern = f"expression_*_{safe_expression_short}*.srt"
                        matching_files = list(Path(subtitles_dir).glob(pattern))
                        if matching_files:
                            subtitle_file = matching_files[0]
                            logger.info(f"Found matching subtitle file: {subtitle_file}")
                        else:
                            # Fallback: Try to find by index only (most reliable if order is preserved)
                            pattern_index = f"expression_{expression_index+1:02d}_*.srt"
                            matching_files_index = list(Path(subtitles_dir).glob(pattern_index))
                            if matching_files_index:
                                subtitle_file = matching_files_index[0]
                                logger.info(f"Found subtitle file by index: {subtitle_file}")
                            else:
                                logger.warning(f"No subtitle file found for expression '{expression.expression}' (index {expression_index+1})")
                
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

                    # Get quality settings from config (TICKET-072: improved quality)
                    video_args = self._get_video_output_args(source_video_path=context_video_path)
                    (
                        ffmpeg.output(
                            context_video,
                            context_audio,
                            str(context_clip_path),
                            vcodec=video_args.get('vcodec', 'libx264'),
                            acodec=video_args.get('acodec', 'aac'),
                            ac=2,
                            ar=48000,
                            preset=video_args.get('preset', 'medium'),
                            crf=video_args.get('crf', 18),
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

            # Get quality settings from config (TICKET-072: improved quality)
            video_args = self._get_video_output_args(source_video_path=context_video_path)
            (
                ffmpeg.output(
                    reset_video,
                    reset_audio,
                    str(context_clip_reset_path),
                    vcodec=video_args.get('vcodec', 'libx264'),
                    acodec=video_args.get('acodec', 'aac'),
                    ac=2,
                    ar=48000,
                    preset=video_args.get('preset', 'medium'),
                    crf=video_args.get('crf', 18)
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
                # Get quality settings from config (TICKET-072: improved quality)
                video_args = self._get_video_output_args(source_video_path=context_video_path)
                (
                    ffmpeg.output(
                        video_stream,
                        audio_stream,
                        str(expression_video_clip_path),
                        vcodec=video_args.get('vcodec', 'libx264'),
                        acodec=video_args.get('acodec', 'aac'),
                        ac=2,
                        ar=48000,
                        preset=video_args.get('preset', 'medium'),
                        crf=video_args.get('crf', 18),
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
            # get_duration_seconds is already imported at module level (line 16)
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
            logger.info("Adding logo to long-form video (right-top, 25% size, 50% opacity)")
            long_form_with_logo_path = self.output_dir / f"temp_long_form_with_logo_{safe_expression}.mkv"
            self._register_temp_file(long_form_with_logo_path)
            
            logo_path = Path(__file__).parent.parent.parent / "assets" / "top_logo.png"
            if logo_path.exists():
                try:
                    # Load long-form video
                    long_form_input = ffmpeg.input(str(long_form_temp_path))
                    long_form_video = long_form_input['v']
                    # ffmpeg-python doesn't support 'in' operator - use direct access with try/except
                    try:
                        long_form_audio = long_form_input['a']
                    except Exception:
                        long_form_audio = None
                    
                    # Load logo image - use simple input without loop/framerate for PNG
                    logo_input = ffmpeg.input(str(logo_path))
                    logo_video = logo_input['v'].filter('scale', -1, 250)  # Logo height doubled
                    logo_video = logo_video.filter('format', 'rgba')
                    logo_video = logo_video.filter('geq', r='r(X,Y)', g='g(X,Y)', b='b(X,Y)', a='0.5*alpha(X,Y)')
                    
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
                    
                    # Output video with logo - Get quality settings from config (TICKET-072)
                    video_args = self._get_video_output_args(source_video_path=long_form_video_path)
                    if long_form_audio:
                        (
                            ffmpeg.output(
                                final_video,
                                long_form_audio,
                                str(long_form_with_logo_path),
                                vcodec=video_args.get('vcodec', 'libx264'),
                                acodec=video_args.get('acodec', 'aac'),
                                ac=2,
                                ar=48000,
                                preset=video_args.get('preset', 'medium'),
                                crf=video_args.get('crf', 18)
                            )
                            .overwrite_output()
                            .run(capture_stdout=True, capture_stderr=True)
                        )
                    else:
                        (
                            ffmpeg.output(
                                final_video,
                                str(long_form_with_logo_path),
                                vcodec=video_args.get('vcodec', 'libx264'),
                                preset=video_args.get('preset', 'medium'),
                                crf=video_args.get('crf', 18)
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
            
            # Use shorts/ directory from paths (created by output_manager)
            # Priority: 1) self.paths['shorts'], 2) self.paths['language']['shorts'], 3) fallback to output_dir structure
            shorts_dir = None
            if hasattr(self, 'paths') and self.paths:
                if 'shorts' in self.paths:
                    shorts_dir = Path(self.paths['shorts'])
                    logger.debug(f"Using shorts directory from self.paths['shorts']: {shorts_dir}")
                elif 'language' in self.paths and isinstance(self.paths['language'], dict) and 'shorts' in self.paths['language']:
                    shorts_dir = Path(self.paths['language']['shorts'])
                    logger.debug(f"Using shorts directory from self.paths['language']['shorts']: {shorts_dir}")
                elif 'language_dir' in self.paths:
                    shorts_dir = Path(self.paths['language_dir']) / "shorts"
                    logger.debug(f"Using shorts directory from self.paths['language_dir']/shorts: {shorts_dir}")
                elif 'language' in self.paths and isinstance(self.paths['language'], dict) and 'language_dir' in self.paths['language']:
                    shorts_dir = Path(self.paths['language']['language_dir']) / "shorts"
                    logger.debug(f"Using shorts directory from self.paths['language']['language_dir']/shorts: {shorts_dir}")
            
            # Fallback: try to find from output_dir structure
            if shorts_dir is None:
                if hasattr(self, 'output_dir') and hasattr(self.output_dir, 'parent'):
                    lang_dir = self.output_dir.parent
                    if lang_dir.name in ['ko', 'ja', 'zh', 'en', 'es', 'fr']:  # Language code
                        shorts_dir = lang_dir / "shorts"
                        logger.debug(f"Using shorts directory from output_dir.parent (language dir): {shorts_dir}")
                    else:
                        shorts_dir = self.output_dir.parent / "shorts"
                        logger.debug(f"Using shorts directory from output_dir.parent: {shorts_dir}")
                else:
                    # Final fallback: create in output_dir parent
                    shorts_dir = Path(self.output_dir).parent / "shorts"
                    logger.debug(f"Using shorts directory from Path(output_dir).parent: {shorts_dir}")
            
            shorts_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Short video output path: {shorts_dir / output_filename}")
            output_path = shorts_dir / output_filename
            
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
            
            # Output scaled long-form video - Get quality settings from config (TICKET-072)
            video_args = self._get_video_output_args(source_video_path=long_form_video_path)
            if audio_stream:
                (
                    ffmpeg.output(
                        video_stream,
                        audio_stream,
                        str(long_form_scaled_path),
                        vcodec=video_args.get('vcodec', 'libx264'),
                        acodec=video_args.get('acodec', 'aac'),
                        ac=2,
                        ar=48000,
                        preset=video_args.get('preset', 'medium'),
                        crf=video_args.get('crf', 18)
                    )
                    .overwrite_output()
                    .run(quiet=True)
                )
            else:
                (
                    ffmpeg.output(
                        video_stream,
                        str(long_form_scaled_path),
                        vcodec=video_args.get('vcodec', 'libx264'),
                        preset=video_args.get('preset', 'medium'),
                        crf=video_args.get('crf', 18)
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
                if not text:
                    return ""
                # First normalize all quote variants to straight quotes
                text = text.replace("'", "'").replace("'", "'").replace("‚", "'").replace("‛", "'")
                text = text.replace(""", '"').replace(""", '"').replace("„", '"')
                text = text.replace('"', '')  # Remove double quotes
                # Escape for FFmpeg drawtext
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
                
                # Group keywords: one keyword per line (each on its own line)
                keyword_lines = []  # List of lists, each inner list contains one keyword index
                
                for i, keyword in enumerate(formatted_keywords):
                    # Each keyword gets its own line
                    keyword_lines.append([i])
                
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

                        # Add custom font for keywords (prioritize config, then language-specific, then fallback)
                        try:
                            custom_font = settings.get_keywords_font_path()
                            if custom_font and os.path.exists(custom_font):
                                keyword_args['fontfile'] = custom_font
                            else:
                                from langflix.config.font_utils import get_font_file_for_language
                                font_path = get_font_file_for_language(self.language_code)
                                if font_path and os.path.exists(font_path):
                                    keyword_args['fontfile'] = font_path
                        except Exception as e:
                            logger.warning(f"Error getting font for keywords: {e}")
                            # Fallback to old method
                            if font_file:
                                font_path = font_file.replace('fontfile=', '').replace(':', '')
                                if font_path and os.path.exists(font_path):
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
                            # Use language-specific font for comma
                            try:
                                from langflix.config.font_utils import get_font_file_for_language
                                font_path = get_font_file_for_language(self.language_code)
                                if font_path and os.path.exists(font_path):
                                    comma_args['fontfile'] = font_path
                            except Exception as e:
                                logger.warning(f"Error getting font for comma: {e}")
                                # Fallback to old method
                                if font_file:
                                    font_path = font_file.replace('fontfile=', '').replace(':', '')
                                    if font_path and os.path.exists(font_path):
                                        comma_args['fontfile'] = font_path
                            final_video = ffmpeg.filter(final_video, 'drawtext', **comma_args)

                logger.info(f"Added {len(keywords)} catchy keywords in {len(keyword_lines)} line(s) with # prefix, each with random color")

            # Add expression text at bottom (bottom area of video, throughout entire video)
            # Expression + translation displayed throughout video duration (positioning from config)
            expression_text = expression.expression
            expression_translation = expression.expression_translation
            
            # Get line breaking config and apply to long text
            line_breaking = settings.get_educational_slide_line_breaking()
            expr_max_words = line_breaking.get('expression_dialogue_max_words', 8)
            trans_max_words = line_breaking.get('expression_translation_max_words', 6)
            
            # Helper function to add line breaks
            def add_line_breaks_for_padding(text: str, max_words: int) -> str:
                """Add newlines after every max_words words for FFmpeg drawtext"""
                if not text:
                    return text
                words = text.split()
                if len(words) <= max_words:
                    return text
                lines = []
                for i in range(0, len(words), max_words):
                    lines.append(' '.join(words[i:i+max_words]))
                return '\n'.join(lines)
            
            # Apply line breaks to long text
            expression_with_breaks = add_line_breaks_for_padding(expression_text, expr_max_words)
            translation_with_breaks = add_line_breaks_for_padding(expression_translation, trans_max_words)

            escaped_expression = escape_drawtext_string(expression_with_breaks)
            escaped_translation = escape_drawtext_string(translation_with_breaks)

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

            # Get custom font for expression text (prioritize config, then language-specific)
            try:
                custom_font = settings.get_expression_font_path()
                if custom_font and os.path.exists(custom_font):
                    drawtext_args_1['fontfile'] = custom_font
                    logger.debug(f"Using custom font for expression text: {custom_font}")
                else:
                    from langflix.config.font_utils import get_font_file_for_language
                    font_path = get_font_file_for_language(self.language_code)
                    if font_path and os.path.exists(font_path):
                        drawtext_args_1['fontfile'] = font_path
                        logger.debug(f"Using font for expression text (language {self.language_code}): {font_path}")
            except Exception as e:
                logger.warning(f"Error getting font for expression text: {e}")
                # Fallback to old method
                if font_file:
                    font_path = font_file.replace('fontfile=', '').replace(':', '')
                    if font_path and os.path.exists(font_path):
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

            # Get custom font for translation text (prioritize config, then language-specific)
            try:
                custom_font = settings.get_translation_font_path()
                if custom_font and os.path.exists(custom_font):
                    drawtext_args_2['fontfile'] = custom_font
                else:
                    from langflix.config.font_utils import get_font_file_for_language
                    font_path = get_font_file_for_language(self.language_code)
                    if font_path and os.path.exists(font_path):
                        drawtext_args_2['fontfile'] = font_path
            except Exception as e:
                logger.warning(f"Error getting font for translation text: {e}")
                # Fallback to old method
                if font_file:
                    font_path = font_file.replace('fontfile=', '').replace(':', '')
                    if font_path and os.path.exists(font_path):
                        drawtext_args_2['fontfile'] = font_path

            final_video = ffmpeg.filter(final_video, 'drawtext', **drawtext_args_2)
            
            # Add dynamic vocabulary annotations (appear when the word is spoken)
            # These overlays show vocabulary words with translations synchronized to dialogue timing
            if hasattr(expression, 'vocabulary_annotations') and expression.vocabulary_annotations:
                try:
                    # Get subtitles for this expression to map dialogue_index → timestamp
                    # Note: We need to get relative timestamps since video starts at 0
                    context_start_seconds = self._time_to_seconds(expression.context_start_time) if expression.context_start_time else 0
                    
                    # Map dialogue to subtitles for timing
                    # Each dialogue line roughly corresponds to subtitle timing
                    dialogues = expression.dialogues if expression.dialogues else []
                    translations = expression.translation if expression.translation else []
                    
                    # Calculate timing for each dialogue line (estimate based on position)
                    # This is a simple estimation - each dialogue line gets equal time
                    if len(dialogues) > 0:
                        context_duration = self._time_to_seconds(expression.context_end_time) - context_start_seconds if expression.context_end_time else 30.0
                        time_per_dialogue = context_duration / len(dialogues)
                        
                        for idx, vocab_annot in enumerate(expression.vocabulary_annotations[:5]):  # Max 5 annotations (increased)
                            word = vocab_annot.word if hasattr(vocab_annot, 'word') else ''
                            translation = vocab_annot.translation if hasattr(vocab_annot, 'translation') else ''
                            dialogue_index = vocab_annot.dialogue_index if hasattr(vocab_annot, 'dialogue_index') else 0
                            
                            if not word or not translation:
                                continue
                            
                            # Calculate when this annotation should appear (relative to video start)
                            # Estimate: dialogue_index * time_per_dialogue
                            annot_start = max(0, dialogue_index * time_per_dialogue)
                            annot_duration = settings.get_vocabulary_duration()
                            annot_end = annot_start + annot_duration
                            
                            # Create annotation text: "word : translation"
                            annot_text = f"{word} : {translation}"
                            escaped_annot = escape_drawtext_string(annot_text)
                            
                            # RANDOM POSITIONING within video area to avoid overlap and catch attention
                            # Video area: Y from 440 to 1480 (1040px), X from 20 to 1000 (leaving padding)
                            import random
                            
                            # Define the video area bounds (9:16 format)
                            video_area_y_start = 460
                            video_area_y_end = 1200
                            video_area_x_start = 20
                            video_area_x_end = 600
                            
                            # Use different random positions for each annotation
                            # Seed with annotation index for reproducibility per video
                            random.seed(hash(f"{word}_{idx}") % 2**32)
                            
                            # Pick random X and Y within bounds
                            rand_x = random.randint(video_area_x_start, video_area_x_end)
                            rand_y = random.randint(video_area_y_start, video_area_y_end)
                            
                            vocab_drawtext_args = {
                                'text': escaped_annot,
                                'fontsize': settings.get_vocabulary_font_size(),
                                'fontcolor': settings.get_vocabulary_text_color(),
                                'x': rand_x,
                                'y': rand_y,
                                'borderw': settings.get_vocabulary_border_width(),
                                'bordercolor': settings.get_vocabulary_border_color(),
                                'enable': f"between(t,{annot_start:.2f},{annot_end:.2f})"  # Dynamic timing!
                            }
                            
                            # Add custom font for vocabulary (prioritize config, then language-specific)
                            try:
                                custom_font = settings.get_vocabulary_font_path()
                                if custom_font and os.path.exists(custom_font):
                                    vocab_drawtext_args['fontfile'] = custom_font
                                else:
                                    from langflix.config.font_utils import get_font_file_for_language
                                    font_path = get_font_file_for_language(self.language_code)
                                    if font_path and os.path.exists(font_path):
                                        vocab_drawtext_args['fontfile'] = font_path
                            except Exception:
                                pass
                            
                            final_video = ffmpeg.filter(final_video, 'drawtext', **vocab_drawtext_args)
                            logger.debug(f"Added vocabulary annotation: '{word}' at ({rand_x}, {rand_y}), t={annot_start:.2f}-{annot_end:.2f}s")
                        
                        logger.info(f"Added {len(expression.vocabulary_annotations[:5])} vocabulary annotations with random positions")
                except Exception as vocab_error:
                    logger.warning(f"Could not add vocabulary annotations: {vocab_error}")
            
            # Add logo at the very end to ensure it stays at absolute top (y=0)
            # Logo position: absolute top (y=0) of black padding, above hashtags
            # Logo size: 25% of original (59px height), 50% opacity
            logo_path = Path(__file__).parent.parent.parent / "assets" / "top_logo.png"
            if logo_path.exists():
                try:
                    # Load logo image - use simple input without loop/framerate for PNG
                    logo_input = ffmpeg.input(str(logo_path))
                    # Scale logo to 25% of original size (height: 234 * 0.25 = 58.5 ≈ 59px)
                    logo_video = logo_input['v'].filter('scale', -1, 59)
                    # Apply 50% opacity: convert to rgba format and use geq filter to adjust alpha
                    logo_video = logo_video.filter('format', 'rgba')
                    # Use geq filter to set alpha to 50% (0.5 * 255 = 127.5 ≈ 128)
                    logo_video = logo_video.filter('geq', r='r(X,Y)', g='g(X,Y)', b='b(X,Y)', a='0.5*alpha(X,Y)')
                    
                    # Overlay logo at absolute top center - LAST in filter chain
                    final_video = ffmpeg.overlay(
                        final_video,
                        logo_video,
                        x='(W-w)/2',  # Center horizontally (W = canvas width, w = logo width)
                        y=0,  # Absolute top - logo's top-left corner at y=0 (canvas top)
                        enable='between(t,0,999999)'  # Ensure logo appears throughout entire video
                    )
                    logger.info("Added logo at absolute top of short-form video (y=0, 25% size, 50% opacity)")
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
            
            # Get quality settings from config (TICKET-072: improved quality)
            video_args = self._get_video_output_args(source_video_path=long_form_video_path)
            if final_audio:
                (
                    ffmpeg.output(
                        final_video,
                        final_audio,
                        str(temp_with_expression_path),
                        vcodec=video_args.get('vcodec', 'libx264'),
                        acodec=video_args.get('acodec', 'aac'),
                        ac=2,
                        ar=48000,
                        preset=video_args.get('preset', 'medium'),
                        crf=video_args.get('crf', 18)
                    )
                    .overwrite_output()
                    .run(quiet=True)
                )
            else:
                (
                    ffmpeg.output(
                        final_video,
                        str(temp_with_expression_path),
                        vcodec=video_args.get('vcodec', 'libx264'),
                        preset=video_args.get('preset', 'medium'),
                        crf=video_args.get('crf', 18)
                    )
                    .overwrite_output()
                    .run(quiet=True)
                )
            
            # Step 6: Apply dialogue subtitles at bottom (below expression text)
            subtitle_dir = None
            if hasattr(self, 'paths') and self.paths:
                lang_paths = self.paths
                if 'subtitles' in lang_paths:
                    subtitle_dir = lang_paths['subtitles']
                else:
                    subtitle_dir = self.output_dir.parent / "subtitles"
            else:
                subtitle_dir = self.output_dir.parent / "subtitles"

            subtitle_file = None
            if subtitle_dir and Path(subtitle_dir).exists():
                # Look for expression subtitle file by index and name
                from langflix.utils.filename_utils import sanitize_for_expression_filename
                safe_expression_short = sanitize_for_expression_filename(expression.expression)[:30]
                
                # Try exact match first
                subtitle_filename = f"expression_{expression_index+1:02d}_{safe_expression_short}.srt"
                subtitle_file_path = Path(subtitle_dir) / subtitle_filename
                
                if subtitle_file_path.exists():
                    subtitle_file = subtitle_file_path
                    logger.info(f"Found subtitle file: {subtitle_file.name}")
                else:
                    # Try pattern matching
                    pattern = f"expression_{expression_index+1:02d}_*.srt"
                    matches = list(Path(subtitle_dir).glob(pattern))
                    if matches:
                        subtitle_file = matches[0]
                        logger.info(f"Found subtitle file by pattern: {subtitle_file.name}")

                # User request: remove the second "subtitle" layer and keep only the "embedded" one
                # The "embedded" one comes from the long-form context clip which already has subtitles burned in via subs_overlay
                # So we simply pass through the video without adding another subtitle layer
                
                logger.info(f"Skipping second subtitle layer (keeping only embedded subtitles from context clip)")
                
                # Copy video to output (re-encoding to ensure format consistency)
                video_input = ffmpeg.input(str(temp_with_expression_path))
                video_args = self._get_video_output_args(source_video_path=long_form_video_path)
                
                # Get audio stream if available
                audio_stream = None
                try:
                    audio_stream = video_input['a']
                except (KeyError, AttributeError):
                    logger.debug("No audio stream in video")
                    
                if audio_stream:
                    (
                        ffmpeg.output(
                            video_input['v'],
                            audio_stream,
                            str(output_path),
                            vcodec=video_args.get('vcodec', 'libx264'),
                            acodec=video_args.get('acodec', 'aac'),
                            ac=2,
                            ar=48000,
                            preset=video_args.get('preset', 'medium'),
                            crf=video_args.get('crf', 18)
                        )
                        .overwrite_output()
                        .run(capture_stdout=True, capture_stderr=True)
                    )
                else:
                    (
                        ffmpeg.output(
                            video_input['v'],
                            str(output_path),
                            vcodec=video_args.get('vcodec', 'libx264'),
                            preset=video_args.get('preset', 'medium'),
                            crf=video_args.get('crf', 18)
                        )
                        .overwrite_output()
                        .run(capture_stdout=True, capture_stderr=True)
                    )
                
                logger.info(f"✅ Short-form video preserved with embedded subtitles")
            else:
                # No subtitle file found, use video with expression text only
                logger.warning(f"No subtitle file found for expression, using video with expression text only")
                import shutil
                shutil.copy(str(temp_with_expression_path), str(output_path))
            
            # Append ending credit if enabled
            if settings.is_ending_credit_enabled():
                ending_credit_path = settings.get_ending_credit_video_path()
                if ending_credit_path and os.path.exists(ending_credit_path):
                    try:
                        ending_duration = settings.get_ending_credit_duration()
                        logger.info(f"Appending ending credit ({ending_duration}s) from: {ending_credit_path}")
                        
                        # Create temp output with ending credit
                        temp_with_credit = Path(output_path).parent / f"temp_with_credit_{Path(output_path).name}"
                        
                        # Use subprocess for more reliable concat with filter_complex
                        import subprocess
                        
                        # Build ffmpeg command manually for better control
                        cmd = [
                            'ffmpeg', '-y',
                            '-i', str(output_path),
                            '-i', ending_credit_path,
                            '-filter_complex',
                            f'[1:v]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[credit_v];'
                            f'[0:v][0:a][credit_v][1:a]concat=n=2:v=1:a=1[outv][outa]',
                            '-map', '[outv]',
                            '-map', '[outa]',
                            '-t', str(ending_duration + 120),  # Max duration (main + credit)
                            '-c:v', 'libx264',
                            '-c:a', 'aac',
                            '-preset', 'medium',
                            '-crf', '18',
                            str(temp_with_credit)
                        ]
                        
                        result = subprocess.run(cmd, capture_output=True, text=True)
                        
                        if result.returncode == 0 and temp_with_credit.exists():
                            # Replace original with version that has credit
                            import shutil
                            shutil.move(str(temp_with_credit), str(output_path))
                            logger.info(f"✅ Ending credit appended successfully")
                        else:
                            # Try simpler approach without audio from credit
                            logger.info(f"Retrying ending credit with silent audio fallback...")
                            cmd_simple = [
                                'ffmpeg', '-y',
                                '-i', str(output_path),
                                '-i', ending_credit_path,
                                '-filter_complex',
                                f'[1:v]scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[credit_v];'
                                f'anullsrc=r=48000:cl=stereo[silent];'
                                f'[silent]atrim=0:{ending_duration}[credit_a];'
                                f'[0:v][0:a][credit_v][credit_a]concat=n=2:v=1:a=1[outv][outa]',
                                '-map', '[outv]',
                                '-map', '[outa]',
                                '-c:v', 'libx264',
                                '-c:a', 'aac',
                                '-preset', 'medium',
                                '-crf', '18',
                                str(temp_with_credit)
                            ]
                            
                            result2 = subprocess.run(cmd_simple, capture_output=True, text=True)
                            
                            if result2.returncode == 0 and temp_with_credit.exists():
                                import shutil
                                shutil.move(str(temp_with_credit), str(output_path))
                                logger.info(f"✅ Ending credit appended with silent audio")
                            else:
                                logger.warning(f"Failed to append ending credit: {result2.stderr[:500] if result2.stderr else 'Unknown error'}")
                    except Exception as e:
                        logger.warning(f"Failed to append ending credit: {e}")
                        # Continue without ending credit
                else:
                    logger.warning(f"Ending credit enabled but video not found: {ending_credit_path}")
            
            logger.info(f"✅ Short-form video created: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Error creating short-form video from long-form video: {e}")
            raise
    
    def _get_font_option(self) -> str:
        """Get font file option for ffmpeg drawtext using language-specific font"""
        try:
            from langflix.config.font_utils import get_font_file_for_language
            font_path = get_font_file_for_language(self.language_code)
            if font_path and os.path.exists(font_path):
                logger.debug(f"Using font for drawtext (language {self.language_code}): {font_path}")
                return f"fontfile={font_path}:"
            else:
                logger.warning(f"Font not found for language {self.language_code}, using default")
        except Exception as e:
            logger.warning(f"Error getting font option: {e}")
            # Fallback to old method
            try:
                font_file = settings.get_font_file(self.language_code)
                if isinstance(font_file, str) and font_file and os.path.exists(font_file):
                    return f"fontfile={font_file}:"
            except Exception:
                pass
        return ""
    
    def _get_video_output_args(self, source_video_path: Optional[str] = None) -> dict:
        """Get video output arguments from configuration with optional resolution-aware quality.
        
        Args:
            source_video_path: Optional path to source video for resolution-based quality adjustment
            
        Returns:
            Dictionary with vcodec, acodec, preset, and crf values
        """
        video_config = settings.get_video_config()
        # High quality defaults: CRF 16 is visually lossless for most content
        base_crf = video_config.get('crf', 16)
        # Slower preset provides better compression efficiency and quality retention
        base_preset = video_config.get('preset', 'slow')
        
        # If source video provided, adjust quality based on resolution (TICKET-072)
        if source_video_path and os.path.exists(source_video_path):
            try:
                from langflix.media.ffmpeg_utils import get_video_params
                vp = get_video_params(source_video_path)
                height = vp.height or 1080
                
                # Higher quality logic
                if height <= 720:
                    crf = min(base_crf, 16)  # Ensure high quality for 720p
                    logger.debug(f"720p source detected, using CRF {crf} for better quality")
                else:
                    # Use base CRF for 1080p and 4K (don't degrade quality for 4K)
                    crf = base_crf
                    
                return {
                    'vcodec': video_config.get('codec', 'libx264'),
                    'acodec': video_config.get('audio_codec', 'aac'),
                    'preset': base_preset,
                    'crf': crf
                }
            except Exception as e:
                logger.warning(f"Could not detect source resolution, using base settings: {e}")
        
        # Default: use config values
        return {
            'vcodec': video_config.get('codec', 'libx264'),
            'acodec': video_config.get('audio_codec', 'aac'),
            'preset': base_preset,
            'crf': base_crf
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

        # No cache found
        return None
    
    def _cache_tts(self, text: str, expression_index: int, tts_path: str, duration: float) -> None:
        """Cache TTS audio for reuse"""
        # Cache in cache manager
        cache_key = self.cache_manager.get_tts_key(text, "default", "en", expression_index)
        cache_data = {
            'path': tts_path,
            'duration': duration,
            'text': text,
            'expression_index': expression_index
        }
        self.cache_manager.set(cache_key, cache_data, ttl=86400, persist_to_disk=True)  # 24 hours
        logger.info(f"💾 Cached TTS for: '{text}' (duration: {duration:.2f}s)")
    
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
            
            # Note: tts_audio directory is no longer created as it's not needed
            # Audio files are created in temporary locations and embedded directly in videos
            tts_audio_dir = self.output_dir.parent / "tts_audio"  # Used for path reference only, not created
            
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
                # NOTE: We preserve ' and : and , because escape_drawtext_string will handle them
                cleaned = text.replace('"', "") 
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
                """Escape text for FFmpeg drawtext filter
                
                Handles: single quotes, curly quotes, colons, and other problematic characters
                Note: Removes single quotes entirely to prevent FFmpeg filter parsing issues
                """
                if not text:
                    return ""
                # First normalize all quote variants to straight quotes
                # Curly/smart quotes: ' ' ‚ ‛ → '
                text = text.replace("'", "'").replace("'", "'").replace("‚", "'").replace("‛", "'")
                # Double curly quotes: " " „ → "
                text = text.replace(""", '"').replace(""", '"').replace("„", '"')
                # Remove all quotes entirely (they break FFmpeg drawtext filter)
                text = text.replace('"', '').replace("'", '')
                # Escape colons for drawtext
                return text.replace(":", "\\:")
            
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
                
                # Get font option - use educational slide config font
                try:
                    slide_font_path = settings.get_educational_slide_font_path()
                    if slide_font_path and os.path.exists(slide_font_path):
                        font_file_option = f"fontfile={slide_font_path}:"
                    else:
                        # Fallback to language-specific font
                        font_file_option = self._get_font_option()
                    if not isinstance(font_file_option, str):
                        font_file_option = str(font_file_option) if font_file_option else ""
                except Exception as e:
                    logger.warning(f"Error getting font option: {e}")
                    font_file_option = ""
                
                # Get font sizes from config
                font_sizes = settings.get_educational_slide_font_sizes()
                dialogue_font_size = font_sizes.get('expression_dialogue', 36)
                expr_font_size = font_sizes.get('expression', 48)
                dialogue_trans_font_size = font_sizes.get('expression_dialogue_trans', 32)
                trans_font_size = font_sizes.get('expression_translation', 44)
                similar_font_size = font_sizes.get('similar', 28)
                
                # Get positions from config
                positions = settings.get_educational_slide_positions()
                dialogue_y = positions.get('expression_dialogue_y', -220)
                expr_y = positions.get('expression_y', -150)
                dialogue_trans_y = positions.get('expression_dialogue_trans_y', 0)
                trans_y = positions.get('expression_translation_y', 70)
                similar_base_offset = positions.get('similar_base_offset', 250)
                similar_line_spacing = positions.get('similar_line_spacing', 36)
                
                # Get line breaking config
                line_breaking = settings.get_educational_slide_line_breaking()
                dialogue_max_words = line_breaking.get('expression_dialogue_max_words', 8)
                trans_max_words = line_breaking.get('expression_translation_max_words', 6)
                
                # Helper function to add line breaks for long text
                def add_line_breaks(text: str, max_words: int) -> str:
                    """Add newlines after every max_words words for FFmpeg drawtext"""
                    if not text:
                        return text
                    words = text.split()
                    if len(words) <= max_words:
                        return text
                    lines = []
                    for i in range(0, len(words), max_words):
                        lines.append(' '.join(words[i:i+max_words]))
                    return '\n'.join(lines)
                
                # 1. Expression dialogue (full sentence) - upper area (with line break if needed)
                if expression_dialogue and isinstance(expression_dialogue, str):
                    dialogue_with_breaks = add_line_breaks(expression_dialogue, dialogue_max_words)
                    dialogue_with_breaks_escaped = escape_drawtext_string(dialogue_with_breaks)
                    drawtext_filters.append(
                        f"drawtext=text='{dialogue_with_breaks_escaped}':fontsize={dialogue_font_size}:fontcolor=white:"
                        f"{font_file_option}"
                        f"x=(w-text_w)/2:y=h/2{dialogue_y}:"
                        f"borderw=2:bordercolor=black"
                    )
                
                # 2. Expression (key phrase) - highlighted in yellow, below dialogue
                # Only show if enabled in config (default: true, but can be disabled to avoid duplicate)
                if expression_text and isinstance(expression_text, str) and settings.show_expression_highlight():
                    drawtext_filters.append(
                        f"drawtext=text='{expression_text}':fontsize={expr_font_size}:fontcolor=yellow:"
                        f"{font_file_option}"
                        f"x=(w-text_w)/2:y=h/2{expr_y}:"
                        f"borderw=3:bordercolor=black"
                    )
                
                # 3. Expression dialogue translation - middle area (with line break if needed)
                if expression_dialogue_trans and isinstance(expression_dialogue_trans, str):
                    trans_with_breaks = add_line_breaks(expression_dialogue_trans, trans_max_words)
                    trans_with_breaks_escaped = escape_drawtext_string(trans_with_breaks)
                    drawtext_filters.append(
                        f"drawtext=text='{trans_with_breaks_escaped}':fontsize={dialogue_trans_font_size}:fontcolor=white:"
                        f"{font_file_option}"
                        f"x=(w-text_w)/2:y=h/2+{dialogue_trans_y}:"
                        f"borderw=2:bordercolor=black"
                    )
                
                # 4. Expression translation (key phrase) - highlighted in yellow
                # Only show if enabled in config (default: true, but can be disabled to avoid duplicate)
                if translation_text and isinstance(translation_text, str) and settings.show_translation_highlight():
                    drawtext_filters.append(
                        f"drawtext=text='{translation_text}':fontsize={trans_font_size}:fontcolor=yellow:"
                        f"{font_file_option}"
                        f"x=(w-text_w)/2:y=h/2+{trans_y}:"
                        f"borderw=3:bordercolor=black"
                    )
                
                # 5. Similar expressions (bottom area, positioned based on config)
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
                    
                    # Add each similar expression as a separate drawtext for proper line spacing
                    for i, similar_text in enumerate(safe_similar[:2]):  # Limit to 2 expressions
                        if similar_text:
                            similar_text_escaped = escape_drawtext_string(similar_text)
                            y_position = f"h-{similar_base_offset - (i * similar_line_spacing)}"
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
                               preset=video_args.get('preset', 'medium'),  # Updated default for better quality (TICKET-055)
                               crf=video_args.get('crf', 20))  # Updated default for better quality (TICKET-055)
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
                    # Try to get stderr from the FFmpeg error for debugging
                    stderr_output = ""
                    if hasattr(ffmpeg_error, 'stderr'):
                        stderr_output = ffmpeg_error.stderr.decode('utf-8') if isinstance(ffmpeg_error.stderr, bytes) else str(ffmpeg_error.stderr)
                    logger.error(f"FFmpeg error creating slide: {ffmpeg_error}")
                    if stderr_output:
                        logger.error(f"FFmpeg stderr: {stderr_output[:2000]}")  # Limit to 2000 chars
                    # Also log the video_filter that was used
                    logger.error(f"Video filter used: {video_filter[:500] if video_filter else 'empty'}")
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
                               preset=video_args.get('preset', 'medium'),  # Updated default for better quality (TICKET-055)
                               crf=video_args.get('crf', 20))  # Updated default for better quality (TICKET-055)
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
                                   audio_bitrate='256k',
                                   preset=video_args.get('preset', 'slow'),
                                   crf=video_args.get('crf', 18))
                            .overwrite_output()
                            )
                    except Exception as emergency_error:
                        logger.error(f"Emergency fallback also failed: {emergency_error}")
                
                # Check if output_path was actually created
                if not output_path.exists() or output_path.stat().st_size < 100:
                    logger.error(f"Fallback generation produced invalid file: {output_path}")
                    raise RuntimeError("Fallback generation failed")

            except Exception as slide_error:
                # USER REQUEST (Fail-Fast): Stop entire process on failure.
                # Do not produce garbage/blank output.
                logger.critical(f"FATAL: Failed to create critical educational slide: {slide_error}", exc_info=True)
                raise RuntimeError(f"Slide generation failed for expression '{expression.expression}': {slide_error}")
            
            # Move temp slide to final location in slides directory
            slides_dir = self.output_dir.parent / "slides"
            slides_dir.mkdir(exist_ok=True)
            final_slide_path = slides_dir / f"slide_{sanitize_for_expression_filename(expression.expression)}.mkv"
            
            try:
                # Copy the slide (which now already includes audio) to final location
                import shutil
                try:
                    shutil.copy2(str(output_path), str(final_slide_path))
                except PermissionError as perm_error:
                    # Some NAS filesystems (e.g. TrueNAS with ACL) block metadata preservation
                    logger.warning(
                        "Permission error during metadata-preserving copy (%s). "
                        "Falling back to basic copy without metadata.", perm_error
                    )
                    shutil.copyfile(str(output_path), str(final_slide_path))
                logger.info(f"Successfully created educational slide with TTS audio: {final_slide_path}")
            except Exception as copy_error:
                logger.error(f"Error copying slide to final location: {copy_error}")
                # Check if we can fallback to using the temp file (if it exists)
                if output_path.exists():
                     logger.warning(f"Using temp file as fallback: {output_path}")
                     # Try to ignore the fact that it's in temp dir, or return it
                     # Ideally we should try to copy it again or just return it
                     return str(output_path)
                else:
                    logger.error("Temp file also missing, cannot recover slide")
                    raise

            # Final verification
            if not final_slide_path.exists() or final_slide_path.stat().st_size == 0:
                logger.error(f"Final slide path is invalid: {final_slide_path}")
                if output_path.exists():
                    return str(output_path)
                raise FileNotFoundError(f"Failed to create valid slide at {final_slide_path}")

            return str(final_slide_path)
            
        except Exception as e:
            logger.error(f"Error creating educational slide: {e}")
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
                        audio_bitrate='256k',
                        preset=video_args.get('preset', 'slow'), # High quality fallback
                        ac=2,
                        ar=sample_rate,
                        crf=video_args.get('crf', 18) # High quality fallback
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
    
    @handle_error_decorator(
        ErrorContext(
            operation="combine_videos",
            component="core.video_editor"
        ),
        retry=False,
        fallback=False
    )
    def combine_videos(self, video_paths: List[str], output_path: str) -> str:
        """
        Combine multiple videos into a single video file.

        Args:
            video_paths: List of paths to video files to combine.
            output_path: Path where the combined video should be saved.

        Returns:
            str: Path to the combined video.
        """
        if not video_paths:
            raise ValueError("No video paths provided for combination")

        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Combining {len(video_paths)} videos into {output_path}")

        # Create concat file
        concat_file = output_path_obj.parent / f"temp_concat_list_{output_path_obj.stem}.txt"
        self._register_temp_file(concat_file)

        try:
            with open(concat_file, 'w') as f:
                for video_path in video_paths:
                    f.write(f"file '{Path(video_path).absolute()}'\n")

            # Use shared utility for concatenation
            from langflix.media.ffmpeg_utils import concat_demuxer_if_uniform
            concat_demuxer_if_uniform(concat_file, output_path_obj, normalize_audio=True)
            
            logger.info(f"✅ Combined video created: {output_path}")
            return str(output_path)

        except ffmpeg.Error as e:
            stderr_output = e.stderr.decode() if e.stderr else "No stderr details available"
            logger.error(f"FFmpeg Error combining videos:\n{stderr_output}")
            raise
        except Exception as e:
            logger.error(f"Error combining videos: {e}")
            raise

    def _create_video_batch(
        self,
        video_paths: List[str],
        batch_number: int,
        metadata_entries: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Create a single batch video from a list of video paths"""
        try:
            # Use short-form naming convention with episode info
            episode_name = getattr(self, 'episode_name', 'Unknown_Episode')
            batch_filename = f"short-form_{episode_name}_{batch_number:03d}.mkv"
            
            # Use shorts/ directory from paths (created by output_manager)
            # Priority: 1) self.paths['shorts'], 2) self.paths['language']['shorts'], 3) fallback to output_dir structure
            shorts_dir = None
            if hasattr(self, 'paths') and self.paths:
                if 'shorts' in self.paths:
                    shorts_dir = Path(self.paths['shorts'])
                    logger.debug(f"Using shorts directory from self.paths['shorts'] for batch: {shorts_dir}")
                elif 'language' in self.paths and isinstance(self.paths['language'], dict) and 'shorts' in self.paths['language']:
                    shorts_dir = Path(self.paths['language']['shorts'])
                    logger.debug(f"Using shorts directory from self.paths['language']['shorts'] for batch: {shorts_dir}")
                elif 'language_dir' in self.paths:
                    shorts_dir = Path(self.paths['language_dir']) / "shorts"
                    logger.debug(f"Using shorts directory from self.paths['language_dir']/shorts for batch: {shorts_dir}")
                elif 'language' in self.paths and isinstance(self.paths['language'], dict) and 'language_dir' in self.paths['language']:
                    shorts_dir = Path(self.paths['language']['language_dir']) / "shorts"
                    logger.debug(f"Using shorts directory from self.paths['language']['language_dir']/shorts for batch: {shorts_dir}")
            
            # Fallback: try to find from output_dir structure
            if shorts_dir is None:
                if hasattr(self, 'output_dir') and hasattr(self.output_dir, 'parent'):
                    lang_dir = self.output_dir.parent
                    if lang_dir.name in ['ko', 'ja', 'zh', 'en', 'es', 'fr']:  # Language code
                        shorts_dir = lang_dir / "shorts"
                        logger.debug(f"Using shorts directory from output_dir.parent (language dir) for batch: {shorts_dir}")
                    else:
                        shorts_dir = self.output_dir.parent / "shorts"
                        logger.debug(f"Using shorts directory from output_dir.parent for batch: {shorts_dir}")
                else:
                    # Final fallback: create in output_dir parent
                    shorts_dir = Path(self.output_dir).parent / "shorts"
                    logger.debug(f"Using shorts directory from Path(output_dir).parent for batch: {shorts_dir}")
            
            shorts_dir.mkdir(parents=True, exist_ok=True)
            batch_path = shorts_dir / batch_filename
            logger.debug(f"Batch video output path: {batch_path}")
            
            logger.info(f"Creating batch {batch_number} with {len(video_paths)} videos")
            
            # Create concat file
            concat_file = shorts_dir / f"temp_concat_batch_{batch_number}.txt"
            self._register_temp_file(concat_file)
            
            with open(concat_file, 'w') as f:
                for video_path in video_paths:
                    f.write(f"file '{Path(video_path).absolute()}'\n")
            
            # Concatenate videos with concat demuxer and audio normalization
            # Normalize audio to prevent breaking issues when batching videos with different audio parameters
            from langflix.media.ffmpeg_utils import concat_demuxer_if_uniform
            concat_demuxer_if_uniform(concat_file, batch_path, normalize_audio=True)
            
            logger.info(f"✅ Batch {batch_number} created: {batch_path}")

            if metadata_entries:
                metadata_path = Path(batch_path).with_suffix(".meta.json")
                metadata_payload = {
                    "batch_number": batch_number,
                    "episode": episode_name,
                    "language": metadata_entries[0].get("language") or self.language_code or "unknown",
                    "expressions": metadata_entries,
                    "source_videos": [Path(p).name for p in video_paths]
                }
                metadata_path.write_text(json.dumps(metadata_payload, ensure_ascii=False, indent=2))
                logger.info(f"Saved batch metadata: {metadata_path}")

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
