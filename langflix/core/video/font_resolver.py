"""
Font Resolver - Manages fonts for multi-language videos.

This module is responsible for:
- Resolving fonts for different languages
- Managing font cache
- Providing FFmpeg font options

Extracted from video_editor.py lines 1740-1769
"""

import os
import logging
from typing import Optional, Dict
from pathlib import Path

logger = logging.getLogger(__name__)


class FontResolver:
    """
    Resolves fonts for different languages and use cases.

    Responsibilities:
    - Get font paths for specific languages
    - Cache font lookups for performance
    - Provide FFmpeg-compatible font options

    Example:
        >>> resolver = FontResolver()
        >>> font_path = resolver.get_font_for_language(
        ...     language_code="ko",
        ...     use_case="expression"
        ... )
    """

    def __init__(self, default_language_code: Optional[str] = None):
        """
        Initialize FontResolver with empty cache.

        Args:
            default_language_code: Default language code to use when not specified
        """
        self.font_cache: Dict[str, str] = {}
        self.default_language_code = default_language_code
        logger.info(f"FontResolver initialized (default_language: {default_language_code})")

    def get_font_for_language(
        self,
        language_code: Optional[str] = None,
        use_case: str = "default"
    ) -> Optional[str]:
        """
        Get font path for language and use case.

        Args:
            language_code: Language code (e.g., "ko", "es", "en"). Uses default if not provided.
            use_case: Use case (e.g., "default", "expression", "keywords")

        Returns:
            Font file path or None if not found

        Note:
            Extracted from video_editor.py lines 1754-1772
        """
        # Use default language if not provided
        lang = language_code or self.default_language_code

        # Check cache first
        cache_key = f"{lang}:{use_case}"
        cached = self._get_cached_font(cache_key)
        if cached:
            logger.debug(f"Using cached font for {cache_key}: {cached}")
            return cached

        # Resolve font using font_utils
        try:
            from langflix.config.font_utils import get_font_file_for_language

            font_path = get_font_file_for_language(lang, use_case)
            if font_path and os.path.exists(font_path):
                # Cache the result
                self._cache_font(cache_key, font_path)
                logger.debug(f"Resolved font for {cache_key}: {font_path}")
                return font_path
            else:
                logger.warning(f"No font found for {cache_key}")
                return None
        except Exception as e:
            logger.error(f"Error resolving font for {lang}/{use_case}: {e}")
            return None

    def get_font_option_string(
        self,
        language_code: Optional[str] = None,
        use_case: str = "default"
    ) -> str:
        """
        Get FFmpeg font option string (fontfile=<path>:).

        Args:
            language_code: Language code. Uses default if not provided.
            use_case: Use case for font selection

        Returns:
            FFmpeg fontfile option string, or empty string if font not found

        Note:
            Extracted from video_editor.py lines 1744-1752
        """
        font_path = self.get_font_for_language(language_code, use_case)
        if font_path:
            return f"fontfile={font_path}:"
        return ""

    def validate_font_support(self, language_code: str) -> bool:
        """
        Validate that fonts are available for the given language.

        Args:
            language_code: Language code to validate

        Returns:
            True if fonts are available, False otherwise
        """
        font_path = self.get_font_for_language(language_code, "default")
        return font_path is not None and os.path.exists(font_path)

    def _cache_font(self, key: str, font_path: str) -> None:
        """Cache font lookup result."""
        self.font_cache[key] = font_path
        logger.debug(f"Cached font: {key} -> {font_path}")

    def _get_cached_font(self, key: str) -> Optional[str]:
        """Get cached font path."""
        return self.font_cache.get(key)
