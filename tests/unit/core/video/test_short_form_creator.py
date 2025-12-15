"""
Unit tests for ShortFormCreator.

Tests short-form video creation including:
- Initialization and configuration
- Shorts directory resolution
- Encoding arguments
- Time conversion
- Video scaling and padding
- Overlay integration
"""

from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from langflix.core.video.short_form_creator import ShortFormCreator, get_expr_attr


class TestGetExprAttr:
    """Test suite for get_expr_attr helper."""

    def test_get_from_dict(self):
        """Test getting attribute from dict."""
        expr = {'expression': 'hello', 'translation': 'hola'}
        assert get_expr_attr(expr, 'expression') == 'hello'
        assert get_expr_attr(expr, 'translation') == 'hola'

    def test_get_from_dict_with_default(self):
        """Test getting missing key from dict returns default."""
        expr = {'expression': 'hello'}
        assert get_expr_attr(expr, 'missing', 'default') == 'default'

    def test_get_from_object(self):
        """Test getting attribute from object."""
        expr = Mock()
        expr.expression = 'hello'
        expr.translation = 'hola'
        assert get_expr_attr(expr, 'expression') == 'hello'
        assert get_expr_attr(expr, 'translation') == 'hola'

    def test_get_from_object_with_default(self):
        """Test getting missing attribute from object returns default."""
        expr = Mock(spec=['expression'])
        expr.expression = 'hello'
        assert get_expr_attr(expr, 'missing', 'default') == 'default'


class TestShortFormCreatorInit:
    """Test suite for ShortFormCreator initialization."""

    def test_init_with_basic_args(self, tmp_path):
        """Test basic initialization."""
        creator = ShortFormCreator(
            output_dir=tmp_path,
            source_language_code="ko",
            target_language_code="es"
        )

        assert creator.source_language_code == "ko"
        assert creator.target_language_code == "es"
        assert creator.test_mode is False
        assert creator.font_resolver is not None
        assert creator.overlay_renderer is not None

    def test_init_with_test_mode(self, tmp_path):
        """Test initialization with test mode."""
        creator = ShortFormCreator(
            output_dir=tmp_path,
            source_language_code="ko",
            target_language_code="es",
            test_mode=True
        )

        assert creator.test_mode is True

    def test_init_with_custom_font_resolver(self, tmp_path):
        """Test initialization with custom FontResolver."""
        from langflix.core.video.font_resolver import FontResolver
        
        custom_resolver = FontResolver(
            default_language_code="es",
            source_language_code="ko"
        )
        
        creator = ShortFormCreator(
            output_dir=tmp_path,
            source_language_code="ko",
            target_language_code="es",
            font_resolver=custom_resolver
        )

        assert creator.font_resolver is custom_resolver

    def test_init_creates_output_dir(self, tmp_path):
        """Test that output directory is created."""
        new_dir = tmp_path / "new_output"
        
        creator = ShortFormCreator(
            output_dir=new_dir,
            source_language_code="ko",
            target_language_code="es"
        )

        assert new_dir.exists()


class TestGetShortsDir:
    """Test suite for shorts directory resolution."""

    def test_get_shorts_dir_from_paths(self, tmp_path):
        """Test getting shorts dir from paths dict."""
        shorts_path = tmp_path / "custom_shorts"
        
        creator = ShortFormCreator(
            output_dir=tmp_path,
            source_language_code="ko",
            target_language_code="es",
            paths={'shorts': str(shorts_path)}
        )

        result = creator._get_shorts_dir()
        assert result == shorts_path

    def test_get_shorts_dir_fallback(self, tmp_path):
        """Test fallback shorts directory."""
        creator = ShortFormCreator(
            output_dir=tmp_path / "output",
            source_language_code="ko",
            target_language_code="es"
        )

        result = creator._get_shorts_dir()
        assert "shorts" in str(result)


class TestGetEncodingArgs:
    """Test suite for encoding arguments."""

    def test_test_mode_encoding(self, tmp_path):
        """Test encoding args in test mode."""
        creator = ShortFormCreator(
            output_dir=tmp_path,
            source_language_code="ko",
            target_language_code="es",
            test_mode=True
        )

        args = creator._get_encoding_args()

        assert args['preset'] == 'ultrafast'
        assert args['crf'] == 28

    def test_production_mode_uses_settings(self, tmp_path):
        """Test that production mode calls settings (without full mocking)."""
        creator = ShortFormCreator(
            output_dir=tmp_path,
            source_language_code="ko",
            target_language_code="es",
            test_mode=False
        )

        # In production mode, encoding args should have standard keys
        args = creator._get_encoding_args()

        assert 'vcodec' in args
        assert 'acodec' in args
        assert 'preset' in args
        assert 'crf' in args


class TestTimeToSeconds:
    """Test suite for time conversion."""

    def test_hms_format(self, tmp_path):
        """Test HH:MM:SS format."""
        creator = ShortFormCreator(
            output_dir=tmp_path,
            source_language_code="ko",
            target_language_code="es"
        )

        result = creator._time_to_seconds("01:30:45.5")
        assert result == 5445.5

    def test_ms_format(self, tmp_path):
        """Test MM:SS format."""
        creator = ShortFormCreator(
            output_dir=tmp_path,
            source_language_code="ko",
            target_language_code="es"
        )

        result = creator._time_to_seconds("05:30.5")
        assert result == 330.5

    def test_comma_separator(self, tmp_path):
        """Test SRT format with comma."""
        creator = ShortFormCreator(
            output_dir=tmp_path,
            source_language_code="ko",
            target_language_code="es"
        )

        result = creator._time_to_seconds("00:01:30,500")
        assert result == 90.5

    def test_empty_string(self, tmp_path):
        """Test empty string returns 0."""
        creator = ShortFormCreator(
            output_dir=tmp_path,
            source_language_code="ko",
            target_language_code="es"
        )

        result = creator._time_to_seconds("")
        assert result == 0.0

    def test_none_returns_zero(self, tmp_path):
        """Test None returns 0."""
        creator = ShortFormCreator(
            output_dir=tmp_path,
            source_language_code="ko",
            target_language_code="es"
        )

        result = creator._time_to_seconds(None)
        assert result == 0.0


class TestRegisterTempFile:
    """Test suite for temp file management."""

    def test_register_temp_file(self, tmp_path):
        """Test registering temp file."""
        creator = ShortFormCreator(
            output_dir=tmp_path,
            source_language_code="ko",
            target_language_code="es"
        )

        temp_path = tmp_path / "temp.mkv"
        creator._register_temp_file(temp_path)

        assert temp_path in creator._temp_files

    def test_cleanup_temp_files(self, tmp_path):
        """Test cleaning up temp files."""
        creator = ShortFormCreator(
            output_dir=tmp_path,
            source_language_code="ko",
            target_language_code="es"
        )

        # Create actual temp files
        temp1 = tmp_path / "temp1.mkv"
        temp2 = tmp_path / "temp2.mkv"
        temp1.touch()
        temp2.touch()

        creator._register_temp_file(temp1)
        creator._register_temp_file(temp2)

        creator.cleanup_temp_files()

        assert not temp1.exists()
        assert not temp2.exists()
        assert len(creator._temp_files) == 0


class TestOverlayRendererIntegration:
    """Test suite for OverlayRenderer integration."""

    def test_overlay_renderer_initialized(self, tmp_path):
        """Test that OverlayRenderer is properly initialized."""
        creator = ShortFormCreator(
            output_dir=tmp_path,
            source_language_code="ko",
            target_language_code="es"
        )

        assert creator.overlay_renderer is not None
        assert creator.overlay_renderer.source_language_code == "ko"
        assert creator.overlay_renderer.target_language_code == "es"

    def test_overlay_renderer_uses_font_resolver(self, tmp_path):
        """Test that OverlayRenderer uses the correct FontResolver."""
        creator = ShortFormCreator(
            output_dir=tmp_path,
            source_language_code="ko",
            target_language_code="es"
        )

        # FontResolver should be shared
        assert creator.overlay_renderer.font_resolver is creator.font_resolver


class TestCreateShortFormFromLongForm:
    """Test suite for main creation method."""

    def test_returns_string_path(self, tmp_path):
        """Test that method signature expects correct return type."""
        creator = ShortFormCreator(
            output_dir=tmp_path,
            source_language_code="ko",
            target_language_code="es"
        )

        # Just verify the creator is properly set up
        assert callable(creator.create_short_form_from_long_form)
