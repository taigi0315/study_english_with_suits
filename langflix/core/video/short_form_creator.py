"""
Short Form Creator - Creates 9:16 vertical videos with overlays.

This module is responsible for:
- Creating vertical (9:16) short-form videos from long-form content
- Scaling and padding videos with black bars
- Coordinating overlay rendering (viral title, keywords, narrations, etc.)
- Managing short-form video layout

Extracted from video_editor.py lines 663-1739
"""

import logging
import os
import textwrap
from pathlib import Path
from typing import Optional, Dict, Any

import ffmpeg

from langflix.core.models import ExpressionAnalysis
from langflix.core.video.font_resolver import FontResolver
from langflix.core.video.overlay_renderer import OverlayRenderer
from langflix.media.ffmpeg_utils import get_video_params

logger = logging.getLogger(__name__)


def get_expr_attr(expression, attr_name: str, default=None):
    """Helper to get attribute from expression object or dict."""
    if isinstance(expression, dict):
        return expression.get(attr_name, default)
    return getattr(expression, attr_name, default)


class ShortFormCreator:
    """
    Creates short-form vertical videos (9:16) with text overlays.

    Responsibilities:
    - Convert long-form videos to 9:16 format
    - Add black padding (top/bottom)
    - Scale and center content
    - Coordinate text overlays via OverlayRenderer

    Example:
        >>> creator = ShortFormCreator(
        ...     output_dir="/tmp/shorts",
        ...     source_language_code="ko",
        ...     target_language_code="es"
        ... )
        >>> short_video = creator.create_short_form_from_long_form(
        ...     long_form_video_path="long.mp4",
        ...     expression=expr,
        ...     expression_index=0
        ... )
    """

    def __init__(
        self,
        output_dir: Path,
        source_language_code: str,
        target_language_code: str,
        test_mode: bool = False,
        font_resolver: Optional[FontResolver] = None,
        paths: Optional[Dict[str, Any]] = None,
        show_name: Optional[str] = None
    ):
        """
        Initialize ShortFormCreator.

        Args:
            output_dir: Directory for output videos
            source_language_code: Source language (e.g., "ko" for Korean)
            target_language_code: Target language (e.g., "es" for Spanish)
            test_mode: If True, use faster encoding for testing
            font_resolver: Optional FontResolver instance
            paths: Optional paths dictionary for shorts directory
            show_name: Optional show/series name for YouTube metadata
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.source_language_code = source_language_code
        self.target_language_code = target_language_code
        self.test_mode = test_mode
        self.paths = paths or {}
        self.show_name = show_name or "Unknown Show"

        # Initialize FontResolver
        if font_resolver:
            self.font_resolver = font_resolver
        else:
            self.font_resolver = FontResolver(
                default_language_code=target_language_code,
                source_language_code=source_language_code
            )

        # Initialize OverlayRenderer
        self.overlay_renderer = OverlayRenderer(
            source_language_code=source_language_code,
            target_language_code=target_language_code,
            font_resolver=self.font_resolver
        )

        # Temp files to clean up
        self._temp_files = []

        logger.info(
            f"ShortFormCreator initialized: "
            f"source={source_language_code}, target={target_language_code}, show={show_name}"
        )

    def _register_temp_file(self, path: Path) -> None:
        """Register a temp file for cleanup."""
        self._temp_files.append(path)

    def _get_shorts_dir(self) -> Path:
        """Get the shorts output directory."""
        shorts_dir = None
        
        if self.paths:
            if 'shorts' in self.paths:
                shorts_dir = Path(self.paths['shorts'])
            elif 'language' in self.paths and isinstance(self.paths['language'], dict):
                if 'shorts' in self.paths['language']:
                    shorts_dir = Path(self.paths['language']['shorts'])
                elif 'language_dir' in self.paths['language']:
                    shorts_dir = Path(self.paths['language']['language_dir']) / "shorts"

        if shorts_dir is None:
            # Fallback
            lang_dir = self.output_dir.parent
            if lang_dir.name in ['ko', 'ja', 'zh', 'en', 'es', 'fr']:
                shorts_dir = lang_dir / "shorts"
            else:
                shorts_dir = self.output_dir.parent / "shorts"

        shorts_dir.mkdir(parents=True, exist_ok=True)
        return shorts_dir

    def _get_encoding_args(self, source_video_path: Optional[str] = None) -> Dict[str, Any]:
        """Get encoding arguments based on mode and settings."""
        from langflix import settings

        if self.test_mode:
            return {
                'vcodec': 'libx264',
                'acodec': 'aac',
                'preset': 'ultrafast',
                'crf': 28
            }
        else:
            # get_encoding_preset returns a dict with preset, crf, audio_bitrate
            encoding_settings = settings.get_encoding_preset(test_mode=False)
            return {
                'vcodec': 'libx264',
                'acodec': 'aac',
                'preset': encoding_settings.get('preset', 'slow'),
                'crf': encoding_settings.get('crf', 18)
            }

    def _time_to_seconds(self, time_str: str) -> float:
        """Convert time string (HH:MM:SS,mmm or HH:MM:SS.mmm) to seconds."""
        if not time_str:
            return 0.0
        try:
            time_str = time_str.replace(',', '.')
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
        except (ValueError, AttributeError):
            return 0.0

    def create_short_form_from_long_form(
        self,
        long_form_video_path: str,
        expression: ExpressionAnalysis,
        expression_index: int = 0,
        settings=None
    ) -> str:
        """
        Create 9:16 short-form video from long-form video.

        Applies:
        - Video scaling to 1080x1920
        - Black padding (top: 440px, bottom: 440px)
        - Center video content (1040px height)
        - All text overlays (viral_title, keywords, narrations, etc.)

        Args:
            long_form_video_path: Path to long-form video
            expression: Expression analysis data
            expression_index: Index for file naming
            settings: Settings module (imported if not provided)

        Returns:
            Path to created short-form video
        """
        if settings is None:
            from langflix import settings

        try:
            from langflix.utils.filename_utils import sanitize_for_expression_filename
            
            expr_text = get_expr_attr(expression, 'expression', '')
            safe_expression = sanitize_for_expression_filename(expr_text)
            output_filename = f"short_form_{expression_index+1:02d}_{safe_expression[:50]}.mkv"

            shorts_dir = self._get_shorts_dir()
            output_path = shorts_dir / output_filename
            
            # TrueNAS Fix: Ensure output file does not exist or we have permission to overwrite
            if output_path.exists():
                try:
                    output_path.unlink()
                    logger.info(f"Removed existing output key file: {output_path}")
                except OSError as e:
                    logger.warning(f"Failed to remove existing file {output_path}: {e}")
                    # Change filename to avoid permission conflict if delete failed
                    import time
                    timestamp = int(time.time())
                    output_path = shorts_dir / f"short_form_{expression_index+1:02d}_{safe_expression[:40]}_{timestamp}.mkv"
                    logger.info(f"Using alternative filename: {output_path.name}")

            logger.info(f"Creating short-form video from long-form: {expr_text}")

            # Get layout configuration
            target_width, target_height = settings.get_short_video_dimensions()
            long_form_video_height = settings.get_long_form_video_height()

            # Step 1: Scale and pad the long-form video
            scaled_path = self._scale_and_pad_video(
                long_form_video_path,
                target_width,
                target_height,
                long_form_video_height,
                safe_expression,
                settings
            )

            # Step 2: Apply all overlays
            overlayed_path = self._apply_overlays(
                scaled_path,
                expression,
                expression_index,
                target_width,
                target_height,
                settings
            )

            # Step 3: Final output with optional ending credit
            self._finalize_output(
                overlayed_path,
                output_path,
                long_form_video_path,
                settings
            )
            
            # Step 4: Create metadata file for YouTube upload
            self._write_metadata_file(output_path, expression)

            logger.info(f"✅ Short-form video created: {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"Error creating short-form video: {e}")
            raise

    def _scale_and_pad_video(
        self,
        input_video: str,
        target_width: int,
        target_height: int,
        long_form_video_height: int,
        safe_expression: str,
        settings
    ) -> Path:
        """
        Scale video and add black padding for 9:16 format.

        Args:
            input_video: Input video path
            target_width: Target width (1080)
            target_height: Target height (1920)
            long_form_video_height: Height for the video content (1040)
            safe_expression: Sanitized expression for filename
            settings: Settings module

        Returns:
            Path to scaled and padded video
        """
        from langflix.media.ffmpeg_utils import detect_black_bars

        # Get video parameters
        vp = get_video_params(input_video)
        original_width = vp.width or target_width
        original_height = vp.height or target_height

        # Detect black bars for smart cropping
        crop_params = detect_black_bars(input_video)
        
        content_width = original_width
        content_height = original_height
        crop_filter_str = None

        if crop_params:
            try:
                c_w, c_h, c_x, c_y = map(int, crop_params.split(':'))
                if c_w > 0 and c_h > 0 and (c_w < original_width or c_h < original_height):
                    content_width = c_w
                    content_height = c_h
                    crop_filter_str = crop_params
                    logger.info(f"Detected active content area: {c_w}x{c_h}")
            except Exception as e:
                logger.warning(f"Error parsing crop params: {e}")

        # Calculate scale factor
        scale_factor = long_form_video_height / content_height
        scaled_width = int(content_width * scale_factor)
        scaled_height = long_form_video_height

        # Crop if width exceeds target
        crop_x = 0
        if scaled_width > target_width:
            crop_x = (scaled_width - target_width) // 2

        logger.info(
            f"Scaling: {content_width}x{content_height} -> {scaled_width}x{scaled_height} "
            f"(crop_x={crop_x})"
        )

        # Create scaled video
        scaled_path = self.output_dir / f"temp_scaled_{safe_expression}.mkv"
        self._register_temp_file(scaled_path)

        input_stream = ffmpeg.input(str(input_video))
        video_stream = input_stream['v']

        # Apply crop if black bars detected
        if crop_filter_str:
            cw, ch, cx, cy = crop_filter_str.split(':')
            video_stream = ffmpeg.filter(video_stream, 'crop', cw, ch, cx, cy)

        # Scale to target height
        video_stream = ffmpeg.filter(video_stream, 'scale', -1, scaled_height)

        # Center crop if needed
        if crop_x > 0:
            video_stream = ffmpeg.filter(
                video_stream, 'crop',
                target_width, scaled_height, crop_x, 0
            )

        # Get audio stream
        audio_stream = None
        try:
            audio_stream = input_stream['a']
        except (KeyError, AttributeError):
            logger.debug("No audio stream in input video")

        # Output scaled video
        video_args = self._get_encoding_args(input_video)
        if audio_stream:
            (
                ffmpeg.output(
                    video_stream, audio_stream,
                    str(scaled_path),
                    vcodec=video_args.get('vcodec', 'libx264'),
                    acodec=video_args.get('acodec', 'aac'),
                    ac=2, ar=48000,
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
                    str(scaled_path),
                    vcodec=video_args.get('vcodec', 'libx264'),
                    preset=video_args.get('preset', 'medium'),
                    crf=video_args.get('crf', 18)
                )
                .overwrite_output()
                .run(quiet=True)
            )

        return scaled_path

    def _apply_overlays(
        self,
        scaled_path: Path,
        expression: ExpressionAnalysis,
        expression_index: int,
        target_width: int,
        target_height: int,
        settings
    ) -> Path:
        """
        Apply all overlays to the scaled video.

        Args:
            scaled_path: Path to scaled video
            expression: Expression data
            expression_index: Index for naming
            target_width: Video width
            target_height: Video height
            settings: Settings module

        Returns:
            Path to video with overlays
        """
        from langflix.utils.filename_utils import sanitize_for_expression_filename
        
        expr_text = get_expr_attr(expression, 'expression', '')
        safe_expression = sanitize_for_expression_filename(expr_text)

        # Load scaled video and add padding
        input_stream = ffmpeg.input(str(scaled_path))
        video_stream = input_stream['v']

        # Get the actual scaled height
        long_form_video_height = settings.get_long_form_video_height()
        y_offset = (target_height - long_form_video_height) // 2

        # Add black padding
        video_stream = ffmpeg.filter(
            video_stream, 'pad',
            target_width, target_height,
            0, y_offset,
            color='black'
        )

        # Apply overlays using OverlayRenderer
        
        # 1. Viral title (use title_translation for target language display)
        # LLM returns: title (source lang), title_translation (target lang)
        viral_title = get_expr_attr(expression, 'title_translation') or get_expr_attr(expression, 'viral_title')
        if viral_title:
            video_stream = self.overlay_renderer.add_viral_title(
                video_stream, viral_title, settings
            )

        # 2. Catchy keywords
        keywords = get_expr_attr(expression, 'catchy_keywords', [])
        if keywords:
            video_stream = self.overlay_renderer.add_catchy_keywords(
                video_stream, keywords, settings, target_width
            )

        # 3. Expression text at bottom
        expression_text = get_expr_attr(expression, 'expression', '')
        translation_text = get_expr_attr(expression, 'expression_translation', '')
        if expression_text:
            video_stream = self.overlay_renderer.add_expression_text(
                video_stream, expression_text, translation_text, settings
            )

        # Get timing info for dynamic overlays
        context_start_time = get_expr_attr(expression, 'context_start_time')
        context_end_time = get_expr_attr(expression, 'context_end_time')
        context_start_seconds = self._time_to_seconds(context_start_time) if context_start_time else 0
        context_duration = (
            self._time_to_seconds(context_end_time) - context_start_seconds
            if context_end_time else 30.0
        )
        dialogues = get_expr_attr(expression, 'dialogues', [])
        dialogue_count = len(dialogues) if dialogues else 1

        # 4. Vocabulary annotations
        vocab_annotations = get_expr_attr(expression, 'vocabulary_annotations', [])
        if vocab_annotations:
            video_stream = self.overlay_renderer.add_vocabulary_annotations(
                video_stream, vocab_annotations,
                dialogue_count, context_duration, settings
            )

        # 5. Narrations
        narrations = get_expr_attr(expression, 'narrations', [])
        if narrations:
            video_stream = self.overlay_renderer.add_narrations(
                video_stream, narrations,
                dialogue_count, context_duration, settings
            )

        # 6. Expression annotations
        expr_annotations = get_expr_attr(expression, 'expression_annotations', [])
        if expr_annotations:
            video_stream = self.overlay_renderer.add_expression_annotations(
                video_stream, expr_annotations,
                dialogue_count, context_duration, settings
            )

        # 7. Logo
        logo_path = Path(__file__).parent.parent.parent.parent / "assets" / "top_logo.png"
        if logo_path.exists():
            video_stream = self.overlay_renderer.add_logo(
                video_stream, str(logo_path),
                position="top-center", scale_height=59, opacity=0.5
            )

        # Get audio
        audio_stream = None
        try:
            audio_stream = input_stream['a']
        except (KeyError, AttributeError):
            pass

        # Output with overlays
        overlayed_path = self.output_dir / f"temp_overlayed_{safe_expression}.mkv"
        self._register_temp_file(overlayed_path)

        video_args = self._get_encoding_args()
        if audio_stream:
            (
                ffmpeg.output(
                    video_stream, audio_stream,
                    str(overlayed_path),
                    vcodec=video_args.get('vcodec', 'libx264'),
                    acodec=video_args.get('acodec', 'aac'),
                    ac=2, ar=48000,
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
                    str(overlayed_path),
                    vcodec=video_args.get('vcodec', 'libx264'),
                    preset=video_args.get('preset', 'medium'),
                    crf=video_args.get('crf', 18)
                )
                .overwrite_output()
                .run(quiet=True)
            )

        return overlayed_path

    def _finalize_output(
        self,
        overlayed_path: Path,
        output_path: Path,
        source_video_path: str,
        settings
    ) -> None:
        """
        Finalize the output video with optional ending credit.

        Args:
            overlayed_path: Path to video with overlays
            output_path: Final output path
            source_video_path: Original source video for encoding args
            settings: Settings module
        """
        import shutil
        import subprocess

        # Check for ending credit
        if settings.is_ending_credit_enabled():
            ending_credit_path = settings.get_ending_credit_video_path()
            if ending_credit_path and os.path.exists(ending_credit_path):
                try:
                    ending_duration = settings.get_ending_credit_duration()
                    logger.info(f"Appending ending credit ({ending_duration}s)")

                    temp_with_credit = output_path.parent / f"temp_with_credit_{output_path.name}"

                    cmd = [
                        'ffmpeg', '-y',
                        '-i', str(overlayed_path),
                        '-i', ending_credit_path,
                        '-filter_complex',
                        f'[1:v]scale=1080:1920:force_original_aspect_ratio=decrease,'
                        f'pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[credit_v];'
                        f'[0:v][0:a][credit_v][1:a]concat=n=2:v=1:a=1[outv][outa]',
                        '-map', '[outv]',
                        '-map', '[outa]',
                        '-c:v', 'libx264',
                        '-c:a', 'aac',
                        '-preset', 'medium',
                        '-crf', '18',
                        str(temp_with_credit)
                    ]

                    result = subprocess.run(cmd, capture_output=True, text=True)

                    if result.returncode == 0 and temp_with_credit.exists():
                        shutil.move(str(temp_with_credit), str(output_path))
                        logger.info("✅ Ending credit appended")
                        return
                    else:
                        logger.warning("Ending credit failed, using video without credit")
                        # Clean up failed temp file
                        if temp_with_credit.exists():
                            temp_with_credit.unlink()
                except Exception as e:
                    logger.warning(f"Failed to append ending credit: {e}")
                    # Clean up failed temp file
                    if temp_with_credit.exists():
                        temp_with_credit.unlink()

        # Copy as final output
        shutil.copy(str(overlayed_path), str(output_path))

    def _write_metadata_file(self, video_path: Path, expression: 'ExpressionAnalysis') -> None:
        """Write metadata file for YouTube upload.
        
        Creates a .meta.json file alongside the video with expression data
        for YouTube title, description, and tag generation.
        """
        try:
            import json
            
            # Helper to get attribute from dict or object
            def get_attr(obj, key, default=None):
                if isinstance(obj, dict):
                    return obj.get(key, default)
                return getattr(obj, key, default)
            
            metadata = {
                "expression": get_attr(expression, 'expression', ''),
                "expression_translation": get_attr(expression, 'expression_translation', ''),
                "title": get_attr(expression, 'title', ''),
                "title_translation": get_attr(expression, 'title_translation', ''),
                "catchy_keywords": get_attr(expression, 'catchy_keywords', []),
                "language": self.target_language_code,
                "show_name": self.show_name,
            }
            
            metadata_path = Path(video_path).with_suffix(".meta.json")
            metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')
            logger.debug(f"Saved video metadata: {metadata_path}")
        except Exception as e:
            logger.warning(f"Failed to write metadata file for {video_path}: {e}")

    def cleanup_temp_files(self) -> None:
        """Clean up temporary files."""
        for temp_file in self._temp_files:
            try:
                if temp_file.exists():
                    temp_file.unlink()
            except Exception as e:
                logger.warning(f"Failed to delete temp file {temp_file}: {e}")
        self._temp_files.clear()
