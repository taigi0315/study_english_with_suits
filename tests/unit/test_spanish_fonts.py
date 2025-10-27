"""
Unit tests for Spanish font functionality
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from langflix.core.language_config import LanguageConfig
from langflix.config.font_utils import get_font_file_for_language, validate_spanish_font_support


class TestSpanishFonts:
    """Test Spanish font configuration and rendering support"""
    
    def test_spanish_font_configuration(self):
        """Test Spanish font configuration structure"""
        config = LanguageConfig.get_config('es')
        
        assert config['name'] == 'Spanish'
        assert config['prompt_language'] == 'Spanish'
        assert config['character_encoding'] == 'utf-8'
        assert 'special_characters' in config
        assert 'font_fallback' in config
        
        # Test special characters include Spanish accents
        special_chars = config['special_characters']
        spanish_chars = ['ñ', 'á', 'é', 'í', 'ó', 'ú', 'ü', 'Ñ', 'Á', 'É', 'Í', 'Ó', 'Ú', 'Ü', '¿', '¡']
        
        for char in spanish_chars:
            assert char in special_chars, f"Spanish character '{char}' not found in special_characters"
    
    def test_spanish_font_fallback_chain(self):
        """Test Spanish font fallback chain configuration"""
        config = LanguageConfig.get_config('es')
        fallback_fonts = config['font_fallback']
        
        assert isinstance(fallback_fonts, list)
        assert len(fallback_fonts) > 1
        
        # Should include common fonts that support Spanish
        fallback_str = ' '.join(fallback_fonts)
        assert any(font in fallback_str for font in ['Arial', 'Helvetica', 'Times'])
    
    @patch('pathlib.Path.exists')
    def test_spanish_font_path_resolution(self, mock_exists):
        """Test Spanish font path resolution with fallbacks"""
        # Test primary font exists
        mock_exists.return_value = True
        font_path = LanguageConfig.get_font_path('es')
        assert 'HelveticaNeue.ttc' in font_path
        
        # Test fallback when primary doesn't exist
        def side_effect(path_obj):
            path_str = str(path_obj)
            if 'HelveticaNeue.ttc' in path_str:
                return False
            elif 'Arial.ttf' in path_str:
                return True
            return False
        
        mock_exists.side_effect = side_effect
        font_path = LanguageConfig.get_font_path('es')
        assert 'Arial.ttf' in font_path
    
    @patch('pathlib.Path.exists')
    def test_spanish_font_recommendations(self, mock_exists):
        """Test Spanish font recommendations"""
        mock_exists.return_value = True
        
        recommendations = LanguageConfig.get_spanish_font_recommendations()
        
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        
        # Should include fonts known to support Spanish
        font_names = ' '.join(recommendations)
        expected_fonts = ['HelveticaNeue', 'Arial', 'Helvetica', 'Times']
        
        for font in expected_fonts:
            assert font in font_names, f"Expected font '{font}' not found in recommendations"
    
    @patch('pathlib.Path.exists')
    def test_spanish_font_validation(self, mock_exists):
        """Test Spanish font validation functionality"""
        mock_exists.return_value = True
        
        validation = LanguageConfig.validate_font_for_language('es')
        
        assert validation['language_code'] == 'es'
        assert 'font_path' in validation
        assert 'font_exists' in validation
        assert 'special_characters' in validation
        assert 'validation_status' in validation
        
        assert validation['font_exists'] == True
        assert validation['validation_status'] == 'valid'
        assert 'ñ' in validation['special_characters']
    
    @patch('pathlib.Path.exists')
    def test_spanish_font_validation_missing_font(self, mock_exists):
        """Test Spanish font validation when font is missing"""
        mock_exists.return_value = False
        
        validation = LanguageConfig.validate_font_for_language('es')
        
        assert validation['font_exists'] == False
        assert validation['validation_status'] == 'font_missing'
        assert 'error' in validation
    
    @patch('langflix.core.language_config.LanguageConfig.get_font_path')
    @patch('os.path.exists')
    def test_get_font_file_for_spanish(self, mock_exists, mock_get_font_path):
        """Test getting font file for Spanish language"""
        mock_get_font_path.return_value = '/System/Library/Fonts/HelveticaNeue.ttc'
        mock_exists.return_value = True
        
        font_path = get_font_file_for_language('es')
        
        assert font_path == '/System/Library/Fonts/HelveticaNeue.ttc'
        mock_get_font_path.assert_called_with('es')
    
    @patch('langflix.core.language_config.LanguageConfig.get_font_path')
    @patch('langflix.core.language_config.LanguageConfig.get_spanish_font_recommendations')
    @patch('os.path.exists')
    def test_get_font_file_for_spanish_with_fallback(self, mock_exists, mock_recommendations, mock_get_font_path):
        """Test getting font file for Spanish with fallback to recommendations"""
        # Primary font doesn't exist
        mock_get_font_path.return_value = '/System/Library/Fonts/HelveticaNeue.ttc'
        mock_exists.return_value = False
        
        # But recommendations are available
        mock_recommendations.return_value = ['/System/Library/Fonts/Arial.ttf']
        
        font_path = get_font_file_for_language('es')
        
        assert font_path == '/System/Library/Fonts/Arial.ttf'
    
    @patch('langflix.core.language_config.LanguageConfig.validate_font_for_language')
    def test_validate_spanish_font_support(self, mock_validate):
        """Test Spanish font support validation function"""
        mock_validate.return_value = {
            'language_code': 'es',
            'font_path': '/System/Library/Fonts/Arial.ttf',
            'font_exists': True,
            'validation_status': 'valid',
            'special_characters': 'ñáéíóúüÑÁÉÍÓÚÜ¿¡'
        }
        
        result = validate_spanish_font_support()
        
        assert result['language_code'] == 'es'
        assert result['validation_status'] == 'valid'
        assert 'ñ' in result['special_characters']
        mock_validate.assert_called_with('es')
    
    def test_spanish_character_coverage(self):
        """Test that Spanish special characters are properly defined"""
        config = LanguageConfig.get_config('es')
        special_chars = config['special_characters']
        
        # Test lowercase accented vowels
        lowercase_accents = ['á', 'é', 'í', 'ó', 'ú']
        for char in lowercase_accents:
            assert char in special_chars, f"Lowercase accented '{char}' missing"
        
        # Test uppercase accented vowels
        uppercase_accents = ['Á', 'É', 'Í', 'Ó', 'Ú']
        for char in uppercase_accents:
            assert char in special_chars, f"Uppercase accented '{char}' missing"
        
        # Test ñ/Ñ
        assert 'ñ' in special_chars, "Lowercase ñ missing"
        assert 'Ñ' in special_chars, "Uppercase Ñ missing"
        
        # Test ü/Ü (diaeresis)
        assert 'ü' in special_chars, "Lowercase ü missing"
        assert 'Ü' in special_chars, "Uppercase Ü missing"
        
        # Test inverted punctuation
        assert '¿' in special_chars, "Inverted question mark missing"
        assert '¡' in special_chars, "Inverted exclamation mark missing"
    
    def test_font_fallback_handling(self):
        """Test font fallback handling for different configurations"""
        # Test with list fallback (new format)
        config_with_list = {
            'font_path': '/nonexistent/font.ttc',
            'font_fallback': ['/font1.ttf', '/font2.ttf', '/font3.ttf']
        }
        
        with patch.object(LanguageConfig, 'get_config', return_value=config_with_list):
            with patch('pathlib.Path.exists') as mock_exists:
                # First two fonts don't exist, third one does
                def side_effect(path_obj):
                    return str(path_obj).endswith('font3.ttf')
                mock_exists.side_effect = side_effect
                
                font_path = LanguageConfig.get_font_path('es')
                assert 'font3.ttf' in font_path
        
        # Test with string fallback (backward compatibility)
        config_with_string = {
            'font_path': '/nonexistent/font.ttc',
            'font_fallback': '/fallback/font.ttf'
        }
        
        with patch.object(LanguageConfig, 'get_config', return_value=config_with_string):
            with patch('pathlib.Path.exists') as mock_exists:
                def side_effect(path_obj):
                    return 'fallback' in str(path_obj)
                mock_exists.side_effect = side_effect
                
                font_path = LanguageConfig.get_font_path('es')
                assert 'fallback' in font_path


class TestFontUtilsSpanish:
    """Test font utilities for Spanish language support"""
    
    @patch('langflix.config.font_utils.get_platform_default_font')
    def test_spanish_font_utils_fallback_to_platform(self, mock_platform_font):
        """Test fallback to platform default when Spanish fonts unavailable"""
        mock_platform_font.return_value = '/System/Library/Fonts/Arial.ttf'
        
        with patch('langflix.core.language_config.LanguageConfig.get_font_path') as mock_get_path:
            with patch('os.path.exists', return_value=False):
                mock_get_path.return_value = '/nonexistent/font.ttc'
                
                font_path = get_font_file_for_language('es')
                
                # Should fallback to platform default
                mock_platform_font.assert_called_once()
    
    def test_spanish_font_import_error_handling(self):
        """Test handling of import errors in font utilities"""
        with patch('langflix.config.font_utils.LanguageConfig', side_effect=ImportError):
            result = validate_spanish_font_support()
            
            assert result['validation_status'] == 'error'
            assert 'LanguageConfig not available' in result['error']
