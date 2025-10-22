"""
Unit tests for expression configuration functionality.
"""

import pytest
from unittest.mock import patch, MagicMock
from langflix.config.expression_config import (
    ExpressionConfig,
    SubtitleStylingConfig,
    PlaybackConfig,
    LayoutConfig
)
from langflix.settings import (
    get_expression_config,
    get_expression_subtitle_styling,
    get_expression_playback,
    get_expression_layout,
    get_expression_llm,
    get_expression_whisper
)


class TestSubtitleStylingConfig:
    """Test SubtitleStylingConfig dataclass."""
    
    def test_default_values(self):
        """Test default styling values are set correctly."""
        config = SubtitleStylingConfig()
        
        # Test default styling
        assert config.default['color'] == '#FFFFFF'
        assert config.default['font_family'] == 'Arial'
        assert config.default['font_size'] == 24
        assert config.default['font_weight'] == 'normal'
        assert config.default['background_color'] == '#000000'
        assert config.default['background_opacity'] == 0.7
        assert config.default['position'] == 'bottom'
        assert config.default['margin_bottom'] == 50
        
        # Test expression highlight styling
        assert config.expression_highlight['color'] == '#FFD700'
        assert config.expression_highlight['font_weight'] == 'bold'
        assert config.expression_highlight['font_size'] == 28
        assert config.expression_highlight['background_color'] == '#1A1A1A'
        assert config.expression_highlight['background_opacity'] == 0.85
        assert config.expression_highlight['animation'] == 'fade_in'
        assert config.expression_highlight['duration_ms'] == 300
    
    def test_custom_values(self):
        """Test custom styling values."""
        custom_default = {
            'color': '#FF0000',
            'font_size': 30
        }
        custom_highlight = {
            'color': '#00FF00',
            'font_size': 35
        }
        
        config = SubtitleStylingConfig(
            default=custom_default,
            expression_highlight=custom_highlight
        )
        
        assert config.default['color'] == '#FF0000'
        assert config.default['font_size'] == 30
        assert config.expression_highlight['color'] == '#00FF00'
        assert config.expression_highlight['font_size'] == 35


class TestPlaybackConfig:
    """Test PlaybackConfig dataclass."""
    
    def test_default_values(self):
        """Test default playback values."""
        config = PlaybackConfig()
        
        assert config.expression_repeat_count == 2
        assert config.context_play_count == 1
        assert config.repeat_delay_ms == 200
        assert config.transition_effect == 'fade'
        assert config.transition_duration_ms == 150
    
    def test_custom_values(self):
        """Test custom playback values."""
        config = PlaybackConfig(
            expression_repeat_count=3,
            context_play_count=2,
            repeat_delay_ms=500,
            transition_effect='slide',
            transition_duration_ms=300
        )
        
        assert config.expression_repeat_count == 3
        assert config.context_play_count == 2
        assert config.repeat_delay_ms == 500
        assert config.transition_effect == 'slide'
        assert config.transition_duration_ms == 300


class TestLayoutConfig:
    """Test LayoutConfig dataclass."""
    
    def test_default_values(self):
        """Test default layout values."""
        config = LayoutConfig()
        
        # Test landscape layout
        assert config.landscape['resolution'] == [1920, 1080]
        assert config.landscape['expression_video']['width_percent'] == 50
        assert config.landscape['expression_video']['position'] == 'left'
        assert config.landscape['educational_slide']['width_percent'] == 50
        assert config.landscape['educational_slide']['position'] == 'right'
        
        # Test portrait layout
        assert config.portrait['resolution'] == [1080, 1920]
        assert config.portrait['context_video']['height_percent'] == 75
        assert config.portrait['context_video']['position'] == 'top'
        assert config.portrait['educational_slide']['height_percent'] == 25
        assert config.portrait['educational_slide']['position'] == 'bottom'
    
    def test_custom_values(self):
        """Test custom layout values."""
        custom_landscape = {
            'resolution': [2560, 1440],
            'expression_video': {'width_percent': 60}
        }
        custom_portrait = {
            'resolution': [1440, 2560],
            'context_video': {'height_percent': 80}
        }
        
        config = LayoutConfig(
            landscape=custom_landscape,
            portrait=custom_portrait
        )
        
        assert config.landscape['resolution'] == [2560, 1440]
        assert config.landscape['expression_video']['width_percent'] == 60
        assert config.portrait['resolution'] == [1440, 2560]
        assert config.portrait['context_video']['height_percent'] == 80


class TestExpressionConfig:
    """Test ExpressionConfig main class."""
    
    def test_from_dict_with_defaults(self):
        """Test creating ExpressionConfig from dictionary with defaults."""
        config_dict = {}
        config = ExpressionConfig.from_dict(config_dict)
        
        # Should use default values
        assert config.subtitle_styling.default['color'] == '#FFFFFF'
        assert config.playback.expression_repeat_count == 2
        assert config.layout.landscape['resolution'] == [1920, 1080]
        assert config.llm == {}
        assert config.whisper == {}
    
    def test_from_dict_with_custom_values(self):
        """Test creating ExpressionConfig from dictionary with custom values."""
        config_dict = {
            'subtitle_styling': {
                'default': {'color': '#FF0000'},
                'expression_highlight': {'color': '#00FF00'}
            },
            'playback': {
                'expression_repeat_count': 3,
                'context_play_count': 2
            },
            'layout': {
                'landscape': {'resolution': [2560, 1440]},
                'portrait': {'resolution': [1440, 2560]}
            },
            'llm': {'provider': 'gemini'},
            'whisper': {'model_size': 'large'}
        }
        
        config = ExpressionConfig.from_dict(config_dict)
        
        assert config.subtitle_styling.default['color'] == '#FF0000'
        assert config.subtitle_styling.expression_highlight['color'] == '#00FF00'
        assert config.playback.expression_repeat_count == 3
        assert config.playback.context_play_count == 2
        assert config.layout.landscape['resolution'] == [2560, 1440]
        assert config.layout.portrait['resolution'] == [1440, 2560]
        assert config.llm['provider'] == 'gemini'
        assert config.whisper['model_size'] == 'large'
    
    def test_to_dict(self):
        """Test converting ExpressionConfig to dictionary."""
        config = ExpressionConfig.from_dict({})
        config_dict = config.to_dict()
        
        assert 'subtitle_styling' in config_dict
        assert 'playback' in config_dict
        assert 'layout' in config_dict
        assert 'llm' in config_dict
        assert 'whisper' in config_dict
        
        # Check specific values
        assert config_dict['playback']['expression_repeat_count'] == 2
        assert config_dict['layout']['landscape']['resolution'] == [1920, 1080]
    
    def test_validation_valid_config(self):
        """Test validation with valid configuration."""
        config = ExpressionConfig.from_dict({})
        errors = config.validate()
        
        assert len(errors) == 0
    
    def test_validation_invalid_playback(self):
        """Test validation with invalid playback settings."""
        config = ExpressionConfig.from_dict({
            'playback': {
                'expression_repeat_count': 0,  # Invalid: should be >= 1
                'context_play_count': -1,     # Invalid: should be >= 1
                'repeat_delay_ms': -100,      # Invalid: should be >= 0
                'transition_duration_ms': -50 # Invalid: should be >= 0
            }
        })
        
        errors = config.validate()
        
        assert len(errors) == 4
        assert "expression_repeat_count must be >= 1" in errors
        assert "context_play_count must be >= 1" in errors
        assert "repeat_delay_ms must be >= 0" in errors
        assert "transition_duration_ms must be >= 0" in errors
    
    def test_validation_invalid_layout(self):
        """Test validation with invalid layout settings."""
        config = ExpressionConfig.from_dict({
            'layout': {
                'landscape': {'resolution': [1920]},  # Invalid: should be [width, height]
                'portrait': {'resolution': [1080, -1920]}  # Invalid: negative height
            }
        })
        
        errors = config.validate()
        
        assert len(errors) == 2
        assert "landscape resolution must be [width, height] with positive integers" in errors
        assert "portrait resolution must be [width, height] with positive integers" in errors


class TestSettingsAccessors:
    """Test settings accessor functions."""
    
    @patch('langflix.settings._config_loader')
    def test_get_expression_config(self, mock_loader):
        """Test get_expression_config function."""
        mock_config = {
            'subtitle_styling': {'default': {'color': '#FFFFFF'}},
            'playback': {'expression_repeat_count': 2}
        }
        mock_loader.get_section.return_value = mock_config
        
        result = get_expression_config()
        
        assert result == mock_config
        mock_loader.get_section.assert_called_once_with('expression')
    
    @patch('langflix.settings._config_loader')
    def test_get_expression_subtitle_styling(self, mock_loader):
        """Test get_expression_subtitle_styling function."""
        mock_styling = {'default': {'color': '#FFFFFF'}}
        mock_loader.get.return_value = mock_styling
        
        result = get_expression_subtitle_styling()
        
        assert result == mock_styling
        mock_loader.get.assert_called_once_with('expression', 'subtitle_styling', default={})
    
    @patch('langflix.settings._config_loader')
    def test_get_expression_playback(self, mock_loader):
        """Test get_expression_playback function."""
        mock_playback = {'expression_repeat_count': 2}
        mock_loader.get.return_value = mock_playback
        
        result = get_expression_playback()
        
        assert result == mock_playback
        mock_loader.get.assert_called_once_with('expression', 'playback', default={})
    
    @patch('langflix.settings._config_loader')
    def test_get_expression_layout(self, mock_loader):
        """Test get_expression_layout function."""
        mock_layout = {'landscape': {'resolution': [1920, 1080]}}
        mock_loader.get.return_value = mock_layout
        
        result = get_expression_layout()
        
        assert result == mock_layout
        mock_loader.get.assert_called_once_with('expression', 'layout', default={})
    
    @patch('langflix.settings._config_loader')
    def test_get_expression_llm(self, mock_loader):
        """Test get_expression_llm function."""
        mock_llm = {'provider': 'gemini'}
        mock_loader.get.return_value = mock_llm
        
        result = get_expression_llm()
        
        assert result == mock_llm
        mock_loader.get.assert_called_once_with('expression', 'llm', default={})
    
    @patch('langflix.settings._config_loader')
    def test_get_expression_whisper(self, mock_loader):
        """Test get_expression_whisper function."""
        mock_whisper = {'model_size': 'base'}
        mock_loader.get.return_value = mock_whisper
        
        result = get_expression_whisper()
        
        assert result == mock_whisper
        mock_loader.get.assert_called_once_with('expression', 'whisper', default={})


class TestIntegration:
    """Integration tests for expression configuration."""
    
    @patch('langflix.settings._config_loader')
    def test_load_expression_config_from_settings(self, mock_loader):
        """Test loading expression configuration through settings."""
        mock_config = {
            'subtitle_styling': {
                'default': {'color': '#FFFFFF'},
                'expression_highlight': {'color': '#FFD700'}
            },
            'playback': {
                'expression_repeat_count': 2,
                'context_play_count': 1
            },
            'layout': {
                'landscape': {'resolution': [1920, 1080]},
                'portrait': {'resolution': [1080, 1920]}
            }
        }
        mock_loader.get_section.return_value = mock_config
        
        # Load through settings
        config_dict = get_expression_config()
        config = ExpressionConfig.from_dict(config_dict)
        
        # Verify the configuration
        assert config.subtitle_styling.default['color'] == '#FFFFFF'
        assert config.subtitle_styling.expression_highlight['color'] == '#FFD700'
        assert config.playback.expression_repeat_count == 2
        assert config.layout.landscape['resolution'] == [1920, 1080]
        assert config.layout.portrait['resolution'] == [1080, 1920]
        
        # Verify validation passes
        errors = config.validate()
        assert len(errors) == 0
