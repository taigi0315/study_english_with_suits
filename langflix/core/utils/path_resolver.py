"""
Path Resolver - Centralized path management for video processing.

This module provides a unified interface for resolving paths across the video
processing pipeline, eliminating scattered path construction logic.

Extracted from video_editor.py to reduce duplication and improve maintainability.
"""

import logging
from pathlib import Path
from typing import Optional, Union

logger = logging.getLogger(__name__)


class PathResolver:
    """
    Centralized path resolution for video processing directories and files.

    Manages directory structure for multi-language educational videos:
    ```
    workspace/
    ├── korean/                    # language_dir
    │   ├── long_form_videos/      # output_dir
    │   ├── shorts/                # shorts_dir
    │   ├── expressions/           # expressions_dir
    │   ├── subtitles/             # subtitles_dir
    │   ├── tts_audio/             # tts_audio_dir
    │   └── videos/                # videos_dir
    ```

    Example:
        >>> resolver = PathResolver(output_dir="output/korean/long_form_videos")
        >>> shorts_dir = resolver.get_shorts_dir()
        >>> temp_file = resolver.get_temp_path("context_clip", "hello.mkv")
    """

    def __init__(
        self,
        output_dir: Union[str, Path],
        create_dirs: bool = True
    ):
        """
        Initialize PathResolver.

        Args:
            output_dir: Base output directory (typically long_form_videos)
            create_dirs: If True, create directories as needed
        """
        self.output_dir = Path(output_dir)
        self.create_dirs = create_dirs

        # Detect language directory (parent of output_dir)
        self.language_dir = self.output_dir.parent

        # Create output directory if needed
        if self.create_dirs:
            self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.debug(
            f"PathResolver initialized: output_dir={self.output_dir}, "
            f"language_dir={self.language_dir}"
        )

    # ====================
    # Directory Resolution
    # ====================

    def get_language_dir(self) -> Path:
        """
        Get language directory (parent of output_dir).

        Returns:
            Path to language directory
        """
        return self.language_dir

    def get_shorts_dir(self) -> Path:
        """
        Get shorts (short-form videos) directory.

        Returns:
            Path to shorts directory
        """
        shorts_dir = self.language_dir / "shorts"
        if self.create_dirs:
            shorts_dir.mkdir(parents=True, exist_ok=True)
        return shorts_dir

    def get_expressions_dir(self) -> Path:
        """
        Get expressions directory.

        Returns:
            Path to expressions directory
        """
        expressions_dir = self.language_dir / "expressions"
        if self.create_dirs:
            expressions_dir.mkdir(parents=True, exist_ok=True)
        return expressions_dir

    def get_subtitles_dir(self) -> Path:
        """
        Get subtitles directory.

        Returns:
            Path to subtitles directory
        """
        subtitles_dir = self.language_dir / "subtitles"
        if self.create_dirs:
            subtitles_dir.mkdir(parents=True, exist_ok=True)
        return subtitles_dir

    def get_tts_audio_dir(self) -> Path:
        """
        Get TTS audio cache directory.

        Returns:
            Path to TTS audio directory
        """
        tts_audio_dir = self.language_dir / "tts_audio"
        if self.create_dirs:
            tts_audio_dir.mkdir(parents=True, exist_ok=True)
        return tts_audio_dir

    def get_videos_dir(self) -> Path:
        """
        Get videos (source videos) directory.

        Returns:
            Path to videos directory
        """
        videos_dir = self.language_dir / "videos"
        if self.create_dirs:
            videos_dir.mkdir(parents=True, exist_ok=True)
        return videos_dir

    def get_output_dir(self) -> Path:
        """
        Get output directory (long_form_videos).

        Returns:
            Path to output directory
        """
        return self.output_dir

    # ==========================
    # Temporary File Resolution
    # ==========================

    def get_temp_path(
        self,
        prefix: str,
        identifier: str,
        extension: str = "mkv"
    ) -> Path:
        """
        Get path for temporary file in output directory.

        Args:
            prefix: File prefix (e.g., "context_clip", "expr_repeated")
            identifier: Unique identifier (e.g., expression text, index)
            extension: File extension (default: "mkv")

        Returns:
            Path to temporary file

        Example:
            >>> resolver.get_temp_path("context_clip", "hello", "mkv")
            Path("output/temp_context_clip_hello.mkv")
        """
        filename = f"temp_{prefix}_{identifier}.{extension}"
        return self.output_dir / filename

    def get_temp_concat_list(self, identifier: str) -> Path:
        """
        Get path for temporary concat list file.

        Args:
            identifier: Unique identifier for concat operation

        Returns:
            Path to concat list file
        """
        return self.get_temp_path("concat_list", identifier, "txt")

    # ========================
    # Expression File Naming
    # ========================

    def get_expression_filename(
        self,
        expression_text: str,
        index: Optional[int] = None,
        prefix: str = "",
        suffix: str = "",
        extension: str = "mkv"
    ) -> str:
        """
        Generate standardized expression filename.

        Args:
            expression_text: Expression text to include in filename
            index: Optional expression index
            prefix: Optional filename prefix
            suffix: Optional filename suffix
            extension: File extension (default: "mkv")

        Returns:
            Standardized filename

        Example:
            >>> resolver.get_expression_filename("안녕하세요", index=0)
            "0_annyeonghaseyo.mkv"
        """
        from langflix.utils.filename_utils import sanitize_for_expression_filename

        safe_text = sanitize_for_expression_filename(expression_text)

        parts = []
        if prefix:
            parts.append(prefix)
        if index is not None:
            parts.append(str(index))
        parts.append(safe_text)
        if suffix:
            parts.append(suffix)

        filename = "_".join(parts)
        return f"{filename}.{extension}"

    # =========================
    # Short-Form Video Paths
    # =========================

    def get_short_form_path(
        self,
        expression_text: str,
        index: Optional[int] = None,
        with_logo: bool = False
    ) -> Path:
        """
        Get path for short-form video output.

        Args:
            expression_text: Expression text
            index: Optional expression index
            with_logo: If True, include "with_logo" suffix

        Returns:
            Path to short-form video

        Example:
            >>> resolver.get_short_form_path("hello", index=0, with_logo=True)
            Path("output/korean/shorts/0_hello_with_logo.mkv")
        """
        shorts_dir = self.get_shorts_dir()
        suffix = "with_logo" if with_logo else ""
        filename = self.get_expression_filename(
            expression_text,
            index=index,
            suffix=suffix
        )
        return shorts_dir / filename

    # =========================
    # Long-Form Video Paths
    # =========================

    def get_long_form_path(
        self,
        expression_text: str,
        index: Optional[int] = None,
        with_logo: bool = False
    ) -> Path:
        """
        Get path for long-form video output.

        Args:
            expression_text: Expression text
            index: Optional expression index
            with_logo: If True, include "with_logo" suffix

        Returns:
            Path to long-form video

        Example:
            >>> resolver.get_long_form_path("hello", index=0)
            Path("output/korean/long_form_videos/0_hello.mkv")
        """
        suffix = "with_logo" if with_logo else ""
        filename = self.get_expression_filename(
            expression_text,
            index=index,
            suffix=suffix
        )
        return self.output_dir / filename

    # ===================
    # Subtitle Paths
    # ===================

    def get_subtitle_path(
        self,
        episode_name: str,
        language_code: Optional[str] = None,
        subtitle_type: Optional[str] = None
    ) -> Path:
        """
        Get path for subtitle file.

        Args:
            episode_name: Episode name (e.g., "S01E01")
            language_code: Optional language code (e.g., "ko", "en")
            subtitle_type: Optional subtitle type (e.g., "original", "translated")

        Returns:
            Path to subtitle file

        Example:
            >>> resolver.get_subtitle_path("S01E01", "ko", "original")
            Path("output/korean/subtitles/S01E01.ko.original.srt")
            >>> resolver.get_subtitle_path("S01E01")
            Path("output/korean/subtitles/S01E01.srt")
        """
        subtitles_dir = self.get_subtitles_dir()

        parts = [episode_name]
        if language_code:
            parts.append(language_code)
        if subtitle_type:
            parts.append(subtitle_type)

        filename = ".".join(parts) + ".srt"
        return subtitles_dir / filename

    # ====================
    # Cleanup Utilities
    # ====================

    def get_temp_files(self, pattern: str = "temp_*") -> list[Path]:
        """
        Find temporary files matching pattern.

        Args:
            pattern: Glob pattern for matching files (default: "temp_*")

        Returns:
            List of matching file paths

        Example:
            >>> temp_files = resolver.get_temp_files("temp_*.mkv")
        """
        if not self.output_dir.exists():
            return []

        return list(self.output_dir.glob(pattern))

    def cleanup_temp_files(
        self,
        patterns: Optional[list[str]] = None,
        dry_run: bool = False
    ) -> int:
        """
        Clean up temporary files in output directory.

        Args:
            patterns: List of glob patterns (default: ["temp_*.mkv", "temp_*.txt", "temp_*.wav"])
            dry_run: If True, only report files without deleting

        Returns:
            Number of files cleaned up

        Example:
            >>> count = resolver.cleanup_temp_files(dry_run=True)
            >>> print(f"Would delete {count} files")
        """
        if patterns is None:
            patterns = ["temp_*.mkv", "temp_*.txt", "temp_*.wav", "temp_*.srt"]

        temp_files = []
        for pattern in patterns:
            temp_files.extend(self.get_temp_files(pattern))

        if dry_run:
            for f in temp_files:
                logger.info(f"[DRY RUN] Would delete: {f}")
            return len(temp_files)

        cleaned_count = 0
        for temp_file in temp_files:
            try:
                temp_file.unlink()
                logger.debug(f"Deleted temp file: {temp_file}")
                cleaned_count += 1
            except Exception as e:
                logger.warning(f"Failed to delete {temp_file}: {e}")

        if cleaned_count > 0:
            logger.info(f"✅ Cleaned up {cleaned_count} temporary files")

        return cleaned_count

    # ====================
    # Validation
    # ====================

    def validate_structure(self) -> dict[str, bool]:
        """
        Validate directory structure.

        Returns:
            Dictionary with validation status for each directory

        Example:
            >>> validation = resolver.validate_structure()
            >>> assert validation["output_dir"], "Output directory missing"
        """
        return {
            "output_dir": self.output_dir.exists(),
            "language_dir": self.language_dir.exists(),
            "shorts_dir": self.get_shorts_dir().exists(),
            "expressions_dir": self.get_expressions_dir().exists(),
            "subtitles_dir": self.get_subtitles_dir().exists(),
            "videos_dir": self.get_videos_dir().exists(),
        }

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"PathResolver("
            f"output_dir={self.output_dir}, "
            f"language_dir={self.language_dir})"
        )
