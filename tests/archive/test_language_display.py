"""
Unit tests for language display functionality
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from langflix.youtube.video_manager import VideoFileManager
from langflix.core.language_config import LanguageConfig


class TestLanguageDisplay:
    """Test language detection and display functionality"""
    
    def test_parse_video_path_korean(self):
        """Test Korean language detection from video path"""
        manager = VideoFileManager()
        
        # Test Korean path with translations directory
        video_path = Path("output/Suits/S01E01/translations/ko/slides/slide_hello.mkv")
        video_type, episode, expression, language = manager._parse_video_path(video_path)
        
        assert language == "ko"
        assert episode == "S01E01"
        assert video_type == "slide"
    
    def test_parse_video_path_spanish(self):
        """Test Spanish language detection from video path"""
        manager = VideoFileManager()
        
        # Test Spanish path with translations directory
        video_path = Path("output/Suits/S01E02/translations/es/short_videos/short_video_001.mkv")
        video_type, episode, expression, language = manager._parse_video_path(video_path)
        
        assert language == "es"
        assert episode == "S01E02"
        assert video_type == "short"
    
    def test_parse_video_path_japanese(self):
        """Test Japanese language detection from video path"""
        manager = VideoFileManager()
        
        # Test Japanese path with translations directory
        video_path = Path("output/Suits/S01E03/translations/ja/context_videos/context_hello.mkv")
        video_type, episode, expression, language = manager._parse_video_path(video_path)
        
        assert language == "ja"
        assert episode == "S01E03"
        assert video_type == "context"
    
    def test_parse_video_path_fallback(self):
        """Test fallback language detection without translations directory"""
        manager = VideoFileManager()
        
        # Test path without translations directory but with language in filename
        video_path = Path("output/Suits/S01E01/korean_slide_hello.mkv")
        video_type, episode, expression, language = manager._parse_video_path(video_path)
        
        assert language == "ko"  # Should detect from "korean" in path
        assert episode == "S01E01"
    
    def test_parse_video_path_unknown_language(self):
        """Test unknown language handling"""
        manager = VideoFileManager()
        
        # Test path without clear language indicators
        video_path = Path("output/Suits/S01E01/slides/slide_hello.mkv")
        video_type, episode, expression, language = manager._parse_video_path(video_path)
        
        assert language == "unknown"
        assert episode == "S01E01"
        assert video_type == "slide"
    
    def test_language_code_mapping(self):
        """Test language code to display name mapping"""
        # This would be tested in frontend JavaScript, but we can test the concept
        language_names = {
            'ko': 'Korean',
            'ja': 'Japanese', 
            'zh': 'Chinese',
            'es': 'Spanish',
            'fr': 'French',
            'en': 'English',
            'unknown': 'Unknown'
        }
        
        assert language_names['ko'] == 'Korean'
        assert language_names['es'] == 'Spanish'
        assert language_names['ja'] == 'Japanese'
        assert language_names.get('invalid', 'Unknown') == 'Unknown'


class TestLanguageConfig:
    """Test LanguageConfig functionality"""
    
    def test_get_config_supported_language(self):
        """Test getting config for supported language"""
        config = LanguageConfig.get_config('es')
        
        assert config['name'] == 'Spanish'
        assert config['prompt_language'] == 'Spanish'
        assert 'special_characters' in config
        assert 'ñ' in config['special_characters']
    
    def test_get_config_unsupported_language(self):
        """Test fallback for unsupported language"""
        config = LanguageConfig.get_config('invalid')
        
        # Should fallback to Korean
        assert config['name'] == 'Korean'
        assert config['prompt_language'] == 'Korean'
    
    def test_get_supported_languages(self):
        """Test getting list of supported languages"""
        languages = LanguageConfig.get_supported_languages()
        
        assert 'ko' in languages
        assert 'es' in languages
        assert 'ja' in languages
        assert 'zh' in languages
        assert 'fr' in languages
    
    def test_is_supported(self):
        """Test language support checking"""
        assert LanguageConfig.is_supported('es') == True
        assert LanguageConfig.is_supported('ko') == True
        assert LanguageConfig.is_supported('invalid') == False
    
    @patch('pathlib.Path.exists')
    def test_get_font_path_primary_exists(self, mock_exists):
        """Test font path when primary font exists"""
        mock_exists.return_value = True
        
        font_path = LanguageConfig.get_font_path('es')
        
        assert '/System/Library/Fonts/HelveticaNeue.ttc' in font_path
    
    @patch('pathlib.Path.exists')
    def test_get_font_path_fallback(self, mock_exists):
        """Test font path fallback mechanism"""
        # Primary font doesn't exist, but first fallback does
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
    
    def test_validate_font_for_language(self):
        """Test font validation for language"""
        result = LanguageConfig.validate_font_for_language('es')
        
        assert 'language_code' in result
        assert 'font_path' in result
        assert 'font_exists' in result
        assert 'special_characters' in result
        assert 'validation_status' in result
        
        assert result['language_code'] == 'es'
        assert 'ñ' in result['special_characters']
    
    @patch('pathlib.Path.exists')
    def test_get_spanish_font_recommendations(self, mock_exists):
        """Test Spanish font recommendations"""
        mock_exists.return_value = True
        
        recommendations = LanguageConfig.get_spanish_font_recommendations()
        
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        # Should include common fonts
        font_names = ' '.join(recommendations)
        assert any(font in font_names for font in ['Arial', 'Helvetica', 'Times'])
