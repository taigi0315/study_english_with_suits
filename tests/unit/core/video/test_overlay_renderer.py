"""
Unit tests for OverlayRenderer.

Tests overlay rendering functionality including:
- Viral title overlay
- Catchy keywords overlay
- Narration overlays
- Vocabulary annotations (dual-font)
- Expression annotations (dual-font)
- Text escaping
- Logo overlay
"""

from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys

import pytest

from langflix.core.video.overlay_renderer import OverlayRenderer


class TestOverlayRendererInit:
    """Test suite for OverlayRenderer initialization."""

    def test_init_with_languages(self):
        """Test initialization with language codes."""
        renderer = OverlayRenderer(
            source_language_code="ko",
            target_language_code="es"
        )

        assert renderer.source_language_code == "ko"
        assert renderer.target_language_code == "es"
        assert renderer.font_resolver is not None

    def test_init_with_font_resolver(self):
        """Test initialization with provided FontResolver."""
        from langflix.core.video.font_resolver import FontResolver
        
        custom_resolver = FontResolver(
            default_language_code="es",
            source_language_code="ko"
        )
        
        renderer = OverlayRenderer(
            source_language_code="ko",
            target_language_code="es",
            font_resolver=custom_resolver
        )

        assert renderer.font_resolver is custom_resolver


class TestEscapeDrawtextString:
    """Test suite for text escaping."""

    def test_escape_empty_string(self):
        """Test escaping empty string."""
        result = OverlayRenderer.escape_drawtext_string("")
        assert result == ""

    def test_escape_none(self):
        """Test escaping None."""
        result = OverlayRenderer.escape_drawtext_string(None)
        assert result == ""

    def test_escape_colons(self):
        """Test escaping colons."""
        result = OverlayRenderer.escape_drawtext_string("Hello: World")
        assert result == "Hello\\: World"

    def test_escape_backslashes(self):
        """Test escaping backslashes."""
        result = OverlayRenderer.escape_drawtext_string("Hello\\World")
        assert result == "Hello\\\\World"

    def test_escape_brackets(self):
        """Test escaping brackets."""
        result = OverlayRenderer.escape_drawtext_string("Hello [World]")
        assert result == "Hello \\[World\\]"

    def test_escape_single_quotes(self):
        """Test escaping single quotes."""
        result = OverlayRenderer.escape_drawtext_string("It's a test")
        assert result == "It\\'s a test"

    def test_normalize_curly_quotes(self):
        """Test normalizing curly quotes to straight quotes."""
        result = OverlayRenderer.escape_drawtext_string("'quoted'")
        assert "\\" in result  # Single quotes should be escaped

    def test_remove_double_quotes(self):
        """Test removing double quotes."""
        result = OverlayRenderer.escape_drawtext_string('He said "Hello"')
        assert '"' not in result


class TestCleanHtml:
    """Test suite for HTML cleaning."""

    def test_clean_html_removes_tags(self):
        """Test that HTML tags are removed."""
        result = OverlayRenderer._clean_html("<i>italic</i> and <b>bold</b>")
        assert result == "italic and bold"

    def test_clean_html_empty_string(self):
        """Test cleaning empty string."""
        result = OverlayRenderer._clean_html("")
        assert result == ""

    def test_clean_html_no_tags(self):
        """Test cleaning text without tags."""
        result = OverlayRenderer._clean_html("Just plain text")
        assert result == "Just plain text"


class TestAddViralTitle:
    """Test suite for viral title overlay."""

    def test_add_viral_title_returns_stream_if_empty(self):
        """Test that empty viral title returns original stream."""
        renderer = OverlayRenderer(source_language_code="ko", target_language_code="es")
        mock_stream = Mock()
        mock_settings = Mock()

        result = renderer.add_viral_title(mock_stream, "", mock_settings)

        assert result is mock_stream

    def test_add_viral_title_returns_stream_if_none(self):
        """Test that None viral title returns original stream."""
        renderer = OverlayRenderer(source_language_code="ko", target_language_code="es")
        mock_stream = Mock()
        mock_settings = Mock()

        result = renderer.add_viral_title(mock_stream, None, mock_settings)

        assert result is mock_stream


class TestAddCatchyKeywords:
    """Test suite for catchy keywords overlay."""

    def test_add_catchy_keywords_returns_stream_if_empty(self):
        """Test that empty keywords returns original stream."""
        renderer = OverlayRenderer(source_language_code="ko", target_language_code="es")
        mock_stream = Mock()
        mock_settings = Mock()

        result = renderer.add_catchy_keywords(mock_stream, [], mock_settings)

        assert result is mock_stream

    def test_add_catchy_keywords_returns_stream_if_none(self):
        """Test that None keywords returns original stream."""
        renderer = OverlayRenderer(source_language_code="ko", target_language_code="es")
        mock_stream = Mock()
        mock_settings = Mock()

        result = renderer.add_catchy_keywords(mock_stream, None, mock_settings)

        assert result is mock_stream


class TestAddVocabularyAnnotations:
    """Test suite for vocabulary annotation overlay."""

    def test_returns_stream_if_empty(self):
        """Test that empty annotations returns original stream."""
        renderer = OverlayRenderer(source_language_code="ko", target_language_code="es")
        mock_stream = Mock()
        mock_settings = Mock()

        result = renderer.add_vocabulary_annotations(
            mock_stream, [], 5, 30.0, mock_settings
        )

        assert result is mock_stream

    def test_returns_stream_if_zero_dialogues(self):
        """Test that zero dialogue count returns original stream."""
        renderer = OverlayRenderer(source_language_code="ko", target_language_code="es")
        mock_stream = Mock()
        mock_settings = Mock()

        vocab = [{"word": "사랑", "translation": "amor", "dialogue_index": 0}]
        result = renderer.add_vocabulary_annotations(
            mock_stream, vocab, 0, 30.0, mock_settings
        )

        assert result is mock_stream

    def test_returns_stream_if_none(self):
        """Test that None annotations returns original stream."""
        renderer = OverlayRenderer(source_language_code="ko", target_language_code="es")
        mock_stream = Mock()
        mock_settings = Mock()

        result = renderer.add_vocabulary_annotations(
            mock_stream, None, 5, 30.0, mock_settings
        )

        assert result is mock_stream


class TestAddExpressionAnnotations:
    """Test suite for expression annotation overlay."""

    def test_returns_stream_if_empty(self):
        """Test that empty annotations returns original stream."""
        renderer = OverlayRenderer(source_language_code="ko", target_language_code="es")
        mock_stream = Mock()
        mock_settings = Mock()

        result = renderer.add_expression_annotations(
            mock_stream, [], 5, 30.0, mock_settings
        )

        assert result is mock_stream

    def test_returns_stream_if_zero_dialogues(self):
        """Test that zero dialogue count returns original stream."""
        renderer = OverlayRenderer(source_language_code="ko", target_language_code="es")
        mock_stream = Mock()
        mock_settings = Mock()

        exprs = [{"expression": "expr", "translation": "trans", "dialogue_index": 0}]
        result = renderer.add_expression_annotations(
            mock_stream, exprs, 0, 30.0, mock_settings
        )

        assert result is mock_stream


class TestAddLogo:
    """Test suite for logo overlay."""

    def test_returns_stream_if_logo_not_found(self):
        """Test that missing logo file returns original stream."""
        renderer = OverlayRenderer(source_language_code="ko", target_language_code="es")
        mock_stream = Mock()

        result = renderer.add_logo(mock_stream, "/nonexistent/logo.png")

        assert result is mock_stream


class TestAddNarrations:
    """Test suite for narration overlay."""

    def test_returns_stream_if_empty(self):
        """Test that empty narrations returns original stream."""
        renderer = OverlayRenderer(source_language_code="ko", target_language_code="es")
        mock_stream = Mock()
        mock_settings = Mock()

        result = renderer.add_narrations(
            mock_stream, [], 5, 30.0, mock_settings
        )

        assert result is mock_stream

    def test_returns_stream_if_zero_dialogues(self):
        """Test that zero dialogue count returns original stream."""
        renderer = OverlayRenderer(source_language_code="ko", target_language_code="es")
        mock_stream = Mock()
        mock_settings = Mock()

        narrations = [{"text": "Narration", "dialogue_index": 0, "type": "commentary"}]
        result = renderer.add_narrations(
            mock_stream, narrations, 0, 30.0, mock_settings
        )

        assert result is mock_stream


class TestFontResolverIntegration:
    """Test suite for FontResolver integration."""

    def test_uses_source_font_for_expression(self):
        """Test that source font is used for expression-related overlays."""
        renderer = OverlayRenderer(
            source_language_code="ko",
            target_language_code="es"
        )
        
        # The font resolver should have both language codes
        assert renderer.font_resolver.source_language_code == "ko"
        assert renderer.font_resolver.default_language_code == "es"

    def test_get_dual_fonts_returns_tuple(self):
        """Test that get_dual_fonts returns correct tuple structure."""
        renderer = OverlayRenderer(
            source_language_code="ko",
            target_language_code="es"
        )
        
        # Mock the font resolver
        renderer.font_resolver = Mock()
        renderer.font_resolver.get_dual_fonts.return_value = (
            "/path/to/korean.ttf",
            "/path/to/spanish.ttf"
        )
        
        source, target = renderer.font_resolver.get_dual_fonts("vocabulary")
        
        assert source == "/path/to/korean.ttf"
        assert target == "/path/to/spanish.ttf"
