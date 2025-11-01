#!/usr/bin/env python3
"""
Unit tests for Expression Configuration
"""

import pytest
from langflix.settings import (
    get_expression_config,
    get_expression_subtitle_styling,
    get_expression_playback,
    get_expression_layout,
    get_expression_llm
)
from langflix.config.expression_config import (
    ExpressionConfig,
    SubtitleStylingConfig,
    PlaybackConfig,
    LayoutConfig
)


class TestExpressionConfiguration:
    """Test expression configuration loading and parsing"""
    
    def test_load_expression_config(self):
        """Test loading expression configuration"""
        config = get_expression_config()
        assert isinstance(config, dict)
        assert 'subtitle_styling' in config
        assert 'playback' in config
        assert 'layout' in config
        assert 'llm' in config
        # Note: whisper config removed - using external transcription
    
    def test_subtitle_styling_defaults(self):
        """Test subtitle styling default values"""
        styling = get_expression_subtitle_styling()
        assert isinstance(styling, dict)
        assert 'default' in styling
        assert 'expression_highlight' in styling
        
        # Check default styling
        default = styling['default']
        assert default['color'] == '#FFFFFF'
        assert default['font_family'] == 'Arial'
        assert default['font_size'] == 24
        assert default['font_weight'] == 'normal'
        
        # Check expression highlight styling
        highlight = styling['expression_highlight']
        assert highlight['color'] == '#FFD700'
        assert highlight['font_weight'] == 'bold'
        assert highlight['font_size'] == 28
    
    def test_playback_config(self):
        """Test playback configuration"""
        playback = get_expression_playback()
        assert isinstance(playback, dict)
        assert playback['expression_repeat_count'] == 2
        assert playback['context_play_count'] == 1
        assert playback['repeat_delay_ms'] == 200
        assert playback['transition_effect'] == 'fade'
        assert playback['transition_duration_ms'] == 150
    
    def test_layout_config(self):
        """Test layout configuration"""
        layout = get_expression_layout()
        assert isinstance(layout, dict)
        assert 'landscape' in layout
        assert 'portrait' in layout
        
        # Check landscape layout
        landscape = layout['landscape']
        assert landscape['resolution'] == [1920, 1080]
        assert 'expression_video' in landscape
        assert 'educational_slide' in landscape
        
        # Check portrait layout
        portrait = layout['portrait']
        assert portrait['resolution'] == [1080, 1920]
        assert 'context_video' in portrait
        assert 'educational_slide' in portrait
    
    def test_llm_config(self):
        """Test LLM configuration"""
        llm = get_expression_llm()
        assert isinstance(llm, dict)
        assert 'provider' in llm
        assert 'model' in llm
        assert 'temperature' in llm
    
    # Note: test_whisper_config removed - whisper functionality no longer exists


class TestExpressionConfigDataclass:
    """Test ExpressionConfig dataclass functionality"""
    
    def test_expression_config_from_dict(self):
        """Test ExpressionConfig creation from dictionary"""
        config_dict = get_expression_config()
        expr_config = ExpressionConfig.from_dict(config_dict)
        
        assert isinstance(expr_config, ExpressionConfig)
        assert isinstance(expr_config.subtitle_styling, SubtitleStylingConfig)
        assert isinstance(expr_config.playback, PlaybackConfig)
        assert isinstance(expr_config.layout, LayoutConfig)
    
    def test_subtitle_styling_config(self):
        """Test SubtitleStylingConfig with defaults"""
        styling = SubtitleStylingConfig()
        
        # Check default values are set
        assert styling.default['color'] == '#FFFFFF'
        assert styling.default['font_size'] == 24
        assert styling.expression_highlight['color'] == '#FFD700'
        assert styling.expression_highlight['font_size'] == 28
    
    def test_playback_config_validation(self):
        """Test PlaybackConfig validation"""
        # Test with valid values
        playback = PlaybackConfig(
            expression_repeat_count=3,
            context_play_count=2,
            repeat_delay_ms=300,
            transition_effect='slide',
            transition_duration_ms=200
        )
        
        assert playback.expression_repeat_count == 3
        assert playback.context_play_count == 2
        assert playback.repeat_delay_ms == 300
        assert playback.transition_effect == 'slide'
        assert playback.transition_duration_ms == 200
        
        # Test with invalid values (should be corrected)
        invalid_playback = PlaybackConfig(
            expression_repeat_count=0,  # Should be corrected to 1
            context_play_count=-1,     # Should be corrected to 1
            repeat_delay_ms=-100,      # Should be corrected to 0
            transition_duration_ms=-50 # Should be corrected to 0
        )
        
        assert invalid_playback.expression_repeat_count == 1
        assert invalid_playback.context_play_count == 1
        assert invalid_playback.repeat_delay_ms == 0
        assert invalid_playback.transition_duration_ms == 0
    
    def test_layout_config_defaults(self):
        """Test LayoutConfig with defaults"""
        layout = LayoutConfig()
        
        # Check landscape defaults
        assert layout.landscape['resolution'] == [1920, 1080]
        assert layout.landscape['expression_video']['width_percent'] == 50
        assert layout.landscape['educational_slide']['width_percent'] == 50
        
        # Check portrait defaults
        assert layout.portrait['resolution'] == [1080, 1920]
        assert layout.portrait['context_video']['height_percent'] == 75
        assert layout.portrait['educational_slide']['height_percent'] == 25
    
    def test_expression_config_to_dict(self):
        """Test ExpressionConfig to_dict method"""
        config_dict = get_expression_config()
        expr_config = ExpressionConfig.from_dict(config_dict)
        result_dict = expr_config.to_dict()
        
        assert isinstance(result_dict, dict)
        assert 'subtitle_styling' in result_dict
        assert 'playback' in result_dict
        assert 'layout' in result_dict
        assert 'llm' in result_dict
        # Note: whisper field removed - using external transcription
        
        # Check structure matches original
        assert result_dict['playback']['expression_repeat_count'] == 2
        assert result_dict['layout']['landscape']['resolution'] == [1920, 1080]


class TestExpressionConfigIntegration:
    """Test integration between configuration components"""
    
    def test_config_consistency(self):
        """Test that all configuration components are consistent"""
        # Load all configuration sections
        main_config = get_expression_config()
        styling = get_expression_subtitle_styling()
        playback = get_expression_playback()
        layout = get_expression_layout()
        llm = get_expression_llm()
        # Note: whisper removed - using external transcription
        
        # Verify all sections are present in main config
        assert main_config['subtitle_styling'] == styling
        assert main_config['playback'] == playback
        assert main_config['layout'] == layout
        assert main_config['llm'] == llm
    
    def test_dataclass_roundtrip(self):
        """Test that dataclass can be created from config and converted back"""
        config_dict = get_expression_config()
        expr_config = ExpressionConfig.from_dict(config_dict)
        result_dict = expr_config.to_dict()
        
        # Key values should match
        assert result_dict['playback']['expression_repeat_count'] == config_dict['playback']['expression_repeat_count']
        assert result_dict['layout']['landscape']['resolution'] == config_dict['layout']['landscape']['resolution']
        assert result_dict['subtitle_styling']['default']['color'] == config_dict['subtitle_styling']['default']['color']