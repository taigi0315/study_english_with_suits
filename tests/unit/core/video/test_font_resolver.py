"""
Unit tests for FontResolver.

Tests font resolution functionality including:
- Language-specific font resolution
- Font caching
- FFmpeg font option string generation
- Font validation
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from langflix.core.video.font_resolver import FontResolver


class TestFontResolver:
    """Test suite for FontResolver class."""

    def test_init_with_default_language(self):
        """Test that FontResolver initializes with default language."""
        resolver = FontResolver(default_language_code="ko")

        assert resolver.default_language_code == "ko"
        assert resolver.font_cache == {}

    def test_init_without_default_language(self):
        """Test that FontResolver initializes without default language."""
        resolver = FontResolver()

        assert resolver.default_language_code is None
        assert resolver.font_cache == {}

    @patch('langflix.config.font_utils.get_font_file_for_language')
    @patch('os.path.exists')
    def test_get_font_for_language_resolves_font(self, mock_exists, mock_get_font):
        """Test that get_font_for_language resolves fonts correctly."""
        mock_get_font.return_value = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
        mock_exists.return_value = True

        resolver = FontResolver()
        font_path = resolver.get_font_for_language(language_code="ko", use_case="default")

        assert font_path == "/System/Library/Fonts/AppleSDGothicNeo.ttc"
        mock_get_font.assert_called_once_with("ko", "default")

    @patch('langflix.config.font_utils.get_font_file_for_language')
    @patch('os.path.exists')
    def test_get_font_for_language_uses_default_language(self, mock_exists, mock_get_font):
        """Test that get_font_for_language uses default language when not specified."""
        mock_get_font.return_value = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
        mock_exists.return_value = True

        resolver = FontResolver(default_language_code="es")
        font_path = resolver.get_font_for_language(use_case="expression")

        assert font_path == "/System/Library/Fonts/AppleSDGothicNeo.ttc"
        mock_get_font.assert_called_once_with("es", "expression")

    @patch('langflix.config.font_utils.get_font_file_for_language')
    @patch('os.path.exists')
    def test_get_font_for_language_caches_result(self, mock_exists, mock_get_font):
        """Test that font lookups are cached."""
        mock_get_font.return_value = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
        mock_exists.return_value = True

        resolver = FontResolver()

        # First call
        font_path1 = resolver.get_font_for_language(language_code="ko", use_case="default")
        assert font_path1 == "/System/Library/Fonts/AppleSDGothicNeo.ttc"

        # Second call (should use cache)
        font_path2 = resolver.get_font_for_language(language_code="ko", use_case="default")
        assert font_path2 == "/System/Library/Fonts/AppleSDGothicNeo.ttc"

        # Should only call get_font_file_for_language once
        assert mock_get_font.call_count == 1

    @patch('langflix.config.font_utils.get_font_file_for_language')
    @patch('os.path.exists')
    def test_get_font_for_language_returns_none_if_not_found(self, mock_exists, mock_get_font):
        """Test that None is returned when font is not found."""
        mock_get_font.return_value = None
        mock_exists.return_value = False

        resolver = FontResolver()
        font_path = resolver.get_font_for_language(language_code="unknown", use_case="default")

        assert font_path is None

    @patch('langflix.config.font_utils.get_font_file_for_language')
    @patch('os.path.exists')
    def test_get_font_for_language_returns_none_if_file_missing(self, mock_exists, mock_get_font):
        """Test that None is returned when font file doesn't exist."""
        mock_get_font.return_value = "/path/to/missing/font.ttf"
        mock_exists.return_value = False

        resolver = FontResolver()
        font_path = resolver.get_font_for_language(language_code="ko", use_case="default")

        assert font_path is None

    @patch('langflix.config.font_utils.get_font_file_for_language')
    @patch('os.path.exists')
    def test_get_font_option_string_returns_correct_format(self, mock_exists, mock_get_font):
        """Test that get_font_option_string returns FFmpeg format."""
        mock_get_font.return_value = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
        mock_exists.return_value = True

        resolver = FontResolver()
        option_string = resolver.get_font_option_string(language_code="ko")

        assert option_string == "fontfile=/System/Library/Fonts/AppleSDGothicNeo.ttc:"

    @patch('langflix.config.font_utils.get_font_file_for_language')
    @patch('os.path.exists')
    def test_get_font_option_string_returns_empty_when_no_font(self, mock_exists, mock_get_font):
        """Test that empty string is returned when font not found."""
        mock_get_font.return_value = None
        mock_exists.return_value = False

        resolver = FontResolver()
        option_string = resolver.get_font_option_string(language_code="unknown")

        assert option_string == ""

    @patch('langflix.config.font_utils.get_font_file_for_language')
    @patch('os.path.exists')
    def test_validate_font_support_returns_true_when_font_exists(self, mock_exists, mock_get_font):
        """Test that validate_font_support returns True when font exists."""
        mock_get_font.return_value = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
        mock_exists.return_value = True

        resolver = FontResolver()
        is_supported = resolver.validate_font_support("ko")

        assert is_supported is True

    @patch('langflix.config.font_utils.get_font_file_for_language')
    @patch('os.path.exists')
    def test_validate_font_support_returns_false_when_font_missing(self, mock_exists, mock_get_font):
        """Test that validate_font_support returns False when font missing."""
        mock_get_font.return_value = None
        mock_exists.return_value = False

        resolver = FontResolver()
        is_supported = resolver.validate_font_support("unknown")

        assert is_supported is False

    @patch('langflix.config.font_utils.get_font_file_for_language')
    def test_get_font_for_language_handles_errors_gracefully(self, mock_get_font):
        """Test that exceptions are handled gracefully."""
        mock_get_font.side_effect = Exception("Font resolution error")

        resolver = FontResolver()
        font_path = resolver.get_font_for_language(language_code="ko", use_case="default")

        assert font_path is None

    @patch('langflix.config.font_utils.get_font_file_for_language')
    @patch('os.path.exists')
    def test_cache_key_includes_use_case(self, mock_exists, mock_get_font):
        """Test that cache key includes both language and use case."""
        mock_get_font.side_effect = [
            "/path/to/default.ttf",
            "/path/to/expression.ttf"
        ]
        mock_exists.return_value = True

        resolver = FontResolver()

        # Different use cases should not share cache
        font1 = resolver.get_font_for_language(language_code="ko", use_case="default")
        font2 = resolver.get_font_for_language(language_code="ko", use_case="expression")

        assert mock_get_font.call_count == 2
        assert font1 == "/path/to/default.ttf"
        assert font2 == "/path/to/expression.ttf"
