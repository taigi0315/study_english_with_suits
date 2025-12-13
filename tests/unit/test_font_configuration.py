
import pytest
from unittest.mock import patch, MagicMock
from langflix import settings
from langflix.config.font_utils import get_font_file_for_language

class TestFontConfiguration:

    @pytest.fixture
    def mock_settings(self):
        with patch('langflix.settings.get_language_fonts_config') as mock_config, \
             patch('langflix.settings.get_educational_slide_font_path') as mock_edu_font, \
             patch('langflix.config.font_utils.get_platform_default_font') as mock_platform_default, \
             patch('pathlib.Path.exists') as mock_exists, \
             patch('os.path.exists') as mock_os_exists:
            
            # Setup default mock behaviors
            mock_config.return_value = {
                'default': {
                    'default': 'assets/fonts/DefaultFont.ttf',
                    'keywords': 'assets/fonts/DefaultKeywords.ttf'
                },
                'ko': {
                    'default': 'assets/fonts/KoreanDefault.ttf',
                    'educational_slide': 'assets/fonts/KoreanEdu.ttf'
                },
                'es': {
                    # No specific default, should fallback
                    'keywords': 'assets/fonts/SpanishKeywords.ttf'
                }
            }
            mock_edu_font.return_value = '/path/to/edu/font.ttf'
            mock_platform_default.return_value = '/system/font/default.ttf'
            
            # Assume all configured paths exist
            mock_exists.return_value = True
            mock_os_exists.return_value = True
            
            with patch('platform.system', return_value='Linux'):
                yield {
                    'config': mock_config,
                    'edu_font': mock_edu_font,
                    'platform_default': mock_platform_default,
                    'exists': mock_os_exists
                }

    def test_specific_language_specific_use_case(self, mock_settings):
        # Case: 'ko' and 'educational_slide' -> should return 'assets/fonts/KoreanEdu.ttf' (resolved absolutly)
        
        # We need to mock how internal path resolution handles "assets/fonts"
        # The real function resolves relative to project root. We can just check if it ends with the expected suffix.
        font_path = get_font_file_for_language('ko', 'educational_slide')
        assert font_path.endswith('KoreanEdu.ttf')

    def test_specific_language_markup_fallback_to_language_default(self, mock_settings):
        # Case: 'ko' and 'keywords' (not defined for ko) -> should fallback to ko 'default'
        font_path = get_font_file_for_language('ko', 'keywords')
        assert font_path.endswith('KoreanDefault.ttf')

    def test_specific_language_partial_config_fallback_to_global_default_use_case(self, mock_settings):
        # Case: 'es' and 'keywords' -> Defined in 'es' so should use it
        font_path = get_font_file_for_language('es', 'keywords')
        assert font_path.endswith('SpanishKeywords.ttf')
        
    def test_specific_language_fallback_to_global_use_case(self, mock_settings):
        # Case: 'es' and 'expression' -> Not in 'es', no 'es' default -> fallback to global 'default' use case if specific use case missing in global?
        # Wait, priority is:
        # 1. Lang UseCase
        # 2. Lang Default
        # 3. Global UseCase ("default" section, "expression" key) -> missing in mock
        # 4. Global Default ("default" section, "default" key)
        
        # Let's adjust mock to have global keywords but not expression
        # 'es' requests 'expression'. 
        # 1. es.expression (miss)
        # 2. es.default (miss)
        # 3. default.expression (miss)
        # 4. default.default (hit -> DefaultFont.ttf)
        
        font_path = get_font_file_for_language('es', 'expression')
        assert font_path.endswith('DefaultFont.ttf')

    def test_global_fallback_use_case(self, mock_settings):
        # Case: 'unknown_lang' and 'keywords'
        # 1. unknown.keywords (miss)
        # 2. unknown.default (miss)
        # 3. default.keywords (hit -> DefaultKeywords.ttf)
        
        font_path = get_font_file_for_language('fr', 'keywords')
        assert font_path.endswith('DefaultKeywords.ttf')

    def test_spanish_macos_override(self, mock_settings):
        # Spanish on macOS should return Helvetica Neue (not AppleSDGothicNeo)
        # because Helvetica Neue has full Latin accent support (é, ó, ñ, etc.)
        with patch('platform.system', return_value='Darwin'), \
             patch('os.path.exists', return_value=True):
            
            font_path = get_font_file_for_language('es', 'any_use_case')
            # Should be Helvetica Neue for proper Spanish accent support
            assert font_path == "/System/Library/Fonts/HelveticaNeue.ttc"


class TestSpanishFontSupport:
    """Tests specifically for Spanish language font support with accented characters."""
    
    def test_spanish_font_returns_valid_path_macos(self):
        """Test that Spanish font returns a valid existing path on macOS."""
        import platform
        if platform.system() != "Darwin":
            pytest.skip("macOS-specific test")
        
        font_path = get_font_file_for_language('es', 'keywords')
        assert font_path is not None
        assert len(font_path) > 0
        
        import os
        assert os.path.exists(font_path), f"Font file not found: {font_path}"
    
    def test_spanish_font_is_not_cjk_font(self):
        """Verify Spanish doesn't use AppleSDGothicNeo (lacks Latin accent support)."""
        import platform
        if platform.system() != "Darwin":
            pytest.skip("macOS-specific test")
        
        font_path = get_font_file_for_language('es', 'keywords')
        # AppleSDGothicNeo doesn't properly support Latin accents (é, ó, ñ)
        assert "AppleSDGothicNeo" not in font_path, \
            f"Spanish should not use AppleSDGothicNeo: {font_path}"
    
    def test_spanish_font_supports_accents(self):
        """Test that the selected Spanish font is known to support accented characters."""
        import platform
        if platform.system() != "Darwin":
            pytest.skip("macOS-specific test")
        
        font_path = get_font_file_for_language('es', 'keywords')
        
        # These fonts are known to have full Latin Unicode support
        latin_compatible_fonts = [
            "HelveticaNeue",
            "Arial",
            "Avenir",
            "SF-Pro",
            "Times",
        ]
        
        assert any(f in font_path for f in latin_compatible_fonts), \
            f"Spanish font {font_path} may not support accented characters"
    
    def test_spanish_font_fallback_priority(self):
        """Test Spanish font fallback order on macOS."""
        import platform
        if platform.system() != "Darwin":
            pytest.skip("macOS-specific test")
        
        # Mock first font not existing to test fallback
        with patch('os.path.exists') as mock_exists:
            def side_effect(path):
                # Only Arial Unicode MS exists
                if "Arial Unicode MS" in path:
                    return True
                if "HelveticaNeue" in path:
                    return False
                return True
            
            mock_exists.side_effect = side_effect
            
            font_path = get_font_file_for_language('es', 'keywords')
            assert "Arial Unicode MS" in font_path

