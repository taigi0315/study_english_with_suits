"""
Video Composer - Handles video composition and concatenation.

This module is responsible for:
- Long-form video creation from context and expression clips
- Video clip extraction with precise timing
- Video concatenation and merging
- Quality settings management

Extracted from video_editor.py lines 165-653, 3408-3450
"""

import logging
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

from langflix.core.models import ExpressionAnalysis

logger = logging.getLogger(__name__)


class VideoComposer:
    """
    Handles video composition and concatenation operations.

    Responsibilities:
    - Create long-form educational videos (context → expression → slide)
    - Extract video clips with precise timing
    - Concatenate multiple videos
    - Manage encoding quality settings

    Example:
        >>> composer = VideoComposer(output_dir="/tmp/videos", test_mode=False)
        >>> video_path = composer.create_long_form_video(
        ...     expression=expr,
        ...     context_video_path="context.mp4",
        ...     expression_video_path="expression.mp4",
        ...     expression_index=0
        ... )
    """

    def __init__(
        self,
        output_dir: Path,
        test_mode: bool = False
    ):
        """
        Initialize VideoComposer.

        Args:
            output_dir: Directory for output videos
            test_mode: If True, use faster encoding for testing
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.test_mode = test_mode
        self.encoding_args = self._get_encoding_args()

        # Initialize temp file manager for cleanup
        try:
            from langflix.utils.temp_file_manager import get_temp_manager
            self.temp_manager = get_temp_manager()
        except ImportError:
            logger.warning("Temp file manager not available, temp files won't be tracked")
            self.temp_manager = None

        logger.info(f"VideoComposer initialized: output_dir={output_dir}, test_mode={test_mode}")

    def create_long_form_video(
        self,
        expression: ExpressionAnalysis,
        context_video_path: str,
        expression_video_path: str,
        expression_index: int = 0,
        pre_extracted_context_clip: Optional[Path] = None
    ) -> str:
        """
        Create long-form educational video.

        Video structure: context → expression (2x) → educational slide

        Args:
            expression: Expression analysis data
            context_video_path: Path to context video
            expression_video_path: Path to expression video
            expression_index: Index for file naming
            pre_extracted_context_clip: Optional pre-extracted context clip

        Returns:
            Path to created long-form video

        Note:
            This method will be implemented by copying logic from
            video_editor.py lines 165-653
        """
        # TODO: Implementation in Phase 1, Day 2
        raise NotImplementedError("Will be implemented in Phase 1, Day 2")

    def combine_videos(
        self,
        video_paths: List[str],
        output_path: str
    ) -> str:
        """
        Concatenate multiple videos into one.

        Args:
            video_paths: List of video file paths to combine
            output_path: Output path for combined video

        Returns:
            Path to combined video

        Extracted from video_editor.py lines 3408-3450
        """
        if not video_paths:
            raise ValueError("No video paths provided for combination")

        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Combining {len(video_paths)} videos into {output_path}")

        # Create concat file
        concat_file = output_path_obj.parent / f"temp_concat_list_{output_path_obj.stem}.txt"

        # Register temp file for cleanup (if temp_manager available)
        if hasattr(self, 'temp_manager') and self.temp_manager:
            self.temp_manager.register_file(concat_file)

        try:
            with open(concat_file, 'w') as f:
                for video_path in video_paths:
                    f.write(f"file '{Path(video_path).absolute()}'\n")

            # Use shared utility for concatenation
            from langflix.media.ffmpeg_utils import concat_demuxer_if_uniform
            concat_demuxer_if_uniform(concat_file, output_path_obj, normalize_audio=True)

            logger.info(f"✅ Combined video created: {output_path}")
            return str(output_path)

        except Exception as e:
            import ffmpeg
            if isinstance(e, ffmpeg.Error):
                stderr_output = e.stderr.decode() if e.stderr else "No stderr details available"
                logger.error(f"FFmpeg Error combining videos:\n{stderr_output}")
            else:
                logger.error(f"Error combining videos: {e}")
            raise

    def extract_clip(
        self,
        source_video: str,
        start_time: float,
        end_time: float,
        output_path: str
    ) -> str:
        """
        Extract video clip with precise timing.

        Args:
            source_video: Source video file path
            start_time: Start time in seconds
            end_time: End time in seconds
            output_path: Output path for extracted clip

        Returns:
            Path to extracted clip
        """
        import ffmpeg
        from pathlib import Path

        duration = end_time - start_time
        if duration <= 0:
            raise ValueError(f"Invalid duration: end_time ({end_time}) must be greater than start_time ({start_time})")

        output_path_obj = Path(output_path)
        output_path_obj.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Extracting clip: {start_time:.2f}s - {end_time:.2f}s ({duration:.2f}s)")

        try:
            # Get encoding args based on source video
            video_args = self._get_encoding_args(source_video)

            # Extract clip using ffmpeg
            (
                ffmpeg.input(str(source_video))
                .output(
                    str(output_path),
                    vcodec=video_args['vcodec'],
                    acodec=video_args['acodec'],
                    ac=video_args['ac'],
                    ar=video_args['ar'],
                    preset=video_args['preset'],
                    crf=video_args['crf'],
                    ss=start_time,
                    t=duration
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )

            logger.info(f"✅ Clip extracted: {output_path}")
            return str(output_path)

        except ffmpeg.Error as e:
            stderr = e.stderr.decode('utf-8') if e.stderr else str(e)
            logger.error(f"❌ FFmpeg failed to extract clip: {stderr}")
            raise RuntimeError(f"FFmpeg failed to extract clip: {stderr}") from e

    def _get_encoding_args(self, source_video_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Get encoding arguments based on test mode and configuration.

        Uses fast encoding (ultrafast/crf28) in test mode,
        quality encoding (slow/crf18) in production.

        Args:
            source_video_path: Optional path to source video for resolution-based quality adjustment

        Returns:
            Dictionary with vcodec, acodec, preset, crf, and audio settings

        Extracted from video_editor.py lines 1770-1826
        """
        import os
        from langflix import settings

        # Get encoding preset based on test_mode (fast vs quality)
        encoding_preset = settings.get_encoding_preset(self.test_mode)
        base_preset = encoding_preset['preset']
        base_crf = encoding_preset['crf']
        audio_bitrate = encoding_preset['audio_bitrate']

        # Log which mode is being used
        mode_name = "FAST (test)" if self.test_mode else "QUALITY (production)"
        logger.debug(f"Using {mode_name} encoding: preset={base_preset}, crf={base_crf}")

        # If source video provided and NOT in test mode, adjust quality based on resolution
        if source_video_path and os.path.exists(source_video_path) and not self.test_mode:
            try:
                from langflix.media.ffmpeg_utils import get_video_params
                vp = get_video_params(source_video_path)
                height = vp.height or 1080

                # Higher quality logic for production mode only
                if height <= 720:
                    crf = min(base_crf, 16)  # Ensure high quality for 720p
                    logger.debug(f"720p source detected, using CRF {crf} for better quality")
                else:
                    crf = base_crf

                return {
                    'vcodec': 'libx264',
                    'acodec': 'aac',
                    'preset': base_preset,
                    'crf': crf,
                    'b:a': audio_bitrate,
                    'ac': 2,
                    'ar': 48000
                }
            except Exception as e:
                logger.warning(f"Could not detect source resolution, using base settings: {e}")

        # Default: use preset values
        return {
            'vcodec': 'libx264',
            'acodec': 'aac',
            'preset': base_preset,
            'crf': base_crf,
            'b:a': audio_bitrate,
            'ac': 2,
            'ar': 48000
        }
