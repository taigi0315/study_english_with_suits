"""
Font Resolver - Centralized font management for multi-language videos.

This module is responsible for:
- Resolving fonts for different languages and use cases
- Managing font cache for performance
- Providing FFmpeg font options
- Dual-font rendering support (source + target language)
- Font validation and fallback handling

Use Cases:
- default: General text rendering
- expression: Main expression text (source language)
- keywords: Hashtag keywords (target language)  
- translation: Translated text (target language)
- vocabulary: Vocabulary annotations (dual-language)
- narration: Narration overlays (target language)
- dialogue: Dialogue subtitles (source or target)
- title: Video titles
- educational_slide: Educational slide content

Extracted and enhanced from video_editor.py lines 1740-1769
"""

import os
import logging
from typing import Optional, Dict, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class FontResolver:
    """
    Resolves fonts for different languages and use cases.

    Responsibilities:
    - Get font paths for specific languages
    - Cache font lookups for performance
    - Provide FFmpeg-compatible font options
    - Support dual-font rendering (source + target language)
    - Validate font availability

    Example:
        >>> resolver = FontResolver(
        ...     default_language_code="es",
        ...     source_language_code="ko"
        ... )
        >>> # Get target language font
        >>> font_path = resolver.get_font_for_language(use_case="translation")
        >>> # Get source language font
        >>> source_font = resolver.get_source_font(use_case="expression")
        >>> # Get dual fonts for vocabulary annotations
        >>> source_font, target_font = resolver.get_dual_fonts(use_case="vocabulary")
    """

    def __init__(
        self,
        default_language_code: Optional[str] = None,
        source_language_code: Optional[str] = None
    ):
        """
        Initialize FontResolver with language codes.

        Args:
            default_language_code: Target language code (user's native language, e.g., "es")
            source_language_code: Source language code (language being learned, e.g., "ko")
        """
        self.font_cache: Dict[str, str] = {}
        self.default_language_code = default_language_code  # Target language
        self.source_language_code = source_language_code or "en"  # Source language
        
        logger.info(
            f"FontResolver initialized "
            f"(target={default_language_code}, source={source_language_code})"
        )

    def get_font_for_language(
        self,
        language_code: Optional[str] = None,
        use_case: str = "default"
    ) -> Optional[str]:
        """
        Get font path for language and use case.

        Args:
            language_code: Language code (e.g., "ko", "es", "en"). 
                          Uses default (target) language if not provided.
            use_case: Use case (e.g., "default", "expression", "keywords")

        Returns:
            Font file path or None if not found

        Example:
            >>> resolver.get_font_for_language("es", "keywords")
            "/path/to/spanish/font.ttf"
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

    def get_source_font(self, use_case: str = "expression") -> Optional[str]:
        """
        Get font for source language (the language being learned).

        This is a convenience method for getting fonts for the source language,
        commonly used for expressions, vocabulary words, and dialogues.

        Args:
            use_case: Use case (e.g., "expression", "vocabulary", "dialogue")

        Returns:
            Font file path or None if not found

        Example:
            >>> # For Korean source language
            >>> resolver.get_source_font("expression")
            "/path/to/korean/font.ttf"
        """
        return self.get_font_for_language(self.source_language_code, use_case)

    def get_target_font(self, use_case: str = "translation") -> Optional[str]:
        """
        Get font for target language (user's native language).

        This is a convenience method for getting fonts for translations,
        keywords, narrations, and other target-language text.

        Args:
            use_case: Use case (e.g., "translation", "keywords", "narration")

        Returns:
            Font file path or None if not found

        Example:
            >>> # For Spanish target language
            >>> resolver.get_target_font("keywords")
            "/path/to/spanish/font.ttf"
        """
        return self.get_font_for_language(self.default_language_code, use_case)

    def get_dual_fonts(
        self, 
        use_case: str = "vocabulary"
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Get both source and target language fonts for dual-language rendering.

        Used for vocabulary annotations, expression annotations, and other
        overlays that need to display both source and target text.

        Args:
            use_case: Use case for font selection

        Returns:
            Tuple of (source_font_path, target_font_path)

        Example:
            >>> source_font, target_font = resolver.get_dual_fonts("vocabulary")
            >>> # source_font for Korean word, target_font for Spanish translation
        """
        source_font = self.get_source_font(use_case)
        target_font = self.get_target_font(use_case)
        return (source_font, target_font)

    def get_font_option_string(
        self,
        language_code: Optional[str] = None,
        use_case: str = "default"
    ) -> str:
        """
        Get FFmpeg font option string (fontfile=<path>:).

        Args:
            language_code: Language code. Uses default (target) if not provided.
            use_case: Use case for font selection

        Returns:
            FFmpeg fontfile option string, or empty string if font not found

        Example:
            >>> resolver.get_font_option_string("es", "keywords")
            "fontfile=/path/to/font.ttf:"
        """
        font_path = self.get_font_for_language(language_code, use_case)
        if font_path:
            return f"fontfile={font_path}:"
        return ""

    def get_source_font_option(self, use_case: str = "expression") -> str:
        """
        Get FFmpeg font option for source language.

        Args:
            use_case: Use case for font selection

        Returns:
            FFmpeg fontfile option string
        """
        return self.get_font_option_string(self.source_language_code, use_case)

    def get_target_font_option(self, use_case: str = "translation") -> str:
        """
        Get FFmpeg font option for target language.

        Args:
            use_case: Use case for font selection

        Returns:
            FFmpeg fontfile option string
        """
        return self.get_font_option_string(self.default_language_code, use_case)

    def validate_font_support(self, language_code: str) -> bool:
        """
        Validate that fonts are available for the given language.

        Args:
            language_code: Language code to validate

        Returns:
            True if fonts are available, False otherwise

        Example:
            >>> resolver.validate_font_support("es")
            True
        """
        font_path = self.get_font_for_language(language_code, "default")
        return font_path is not None and os.path.exists(font_path)

    def validate_dual_language_support(self) -> Dict[str, bool]:
        """
        Validate that fonts are available for both source and target languages.

        Returns:
            Dictionary with validation status for each language

        Example:
            >>> resolver.validate_dual_language_support()
            {"source": True, "target": True}
        """
        return {
            "source": self.validate_font_support(self.source_language_code or "en"),
            "target": self.validate_font_support(self.default_language_code or "en"),
            "source_language": self.source_language_code,
            "target_language": self.default_language_code,
        }

    def get_all_fonts_for_language(self, language_code: str) -> Dict[str, Optional[str]]:
        """
        Get all font paths for all use cases for a given language.

        Useful for debugging and validation.

        Args:
            language_code: Language code

        Returns:
            Dictionary mapping use_case to font_path

        Example:
            >>> resolver.get_all_fonts_for_language("es")
            {"default": "/path/1.ttf", "keywords": "/path/2.ttf", ...}
        """
        use_cases = [
            "default", "expression", "keywords", "translation",
            "vocabulary", "narration", "dialogue", "title", "educational_slide"
        ]
        
        fonts = {}
        for use_case in use_cases:
            fonts[use_case] = self.get_font_for_language(language_code, use_case)
        
        return fonts

    def clear_cache(self) -> None:
        """Clear the font cache."""
        self.font_cache.clear()
        logger.debug("Font cache cleared")

    def _cache_font(self, key: str, font_path: str) -> None:
        """Cache font lookup result."""
        self.font_cache[key] = font_path
        logger.debug(f"Cached font: {key} -> {font_path}")

    def _get_cached_font(self, key: str) -> Optional[str]:
        """Get cached font path."""
        return self.font_cache.get(key)

    def __repr__(self) -> str:
        """String representation for debugging."""
        return (
            f"FontResolver("
            f"target={self.default_language_code}, "
            f"source={self.source_language_code}, "
            f"cache_size={len(self.font_cache)})"
        )
