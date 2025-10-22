"""
Expression configuration classes for LangFlix.

This module provides dataclasses for managing expression-based learning feature
configuration, following the existing ConfigLoader pattern.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Tuple


@dataclass
class SubtitleStylingConfig:
    """Subtitle styling configuration for expressions"""
    
    default: Dict[str, Any] = field(default_factory=dict)
    expression_highlight: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Set default values if not provided"""
        if not self.default:
            self.default = {
                'color': '#FFFFFF',
                'font_family': 'Arial',
                'font_size': 24,
                'font_weight': 'normal',
                'background_color': '#000000',
                'background_opacity': 0.7,
                'position': 'bottom',
                'margin_bottom': 50
            }
        
        if not self.expression_highlight:
            self.expression_highlight = {
                'color': '#FFD700',  # Gold
                'font_weight': 'bold',
                'font_size': 28,
                'background_color': '#1A1A1A',
                'background_opacity': 0.85,
                'animation': 'fade_in',
                'duration_ms': 300
            }


@dataclass
class PlaybackConfig:
    """Video playback configuration"""
    
    expression_repeat_count: int = 2
    context_play_count: int = 1
    repeat_delay_ms: int = 200
    transition_effect: str = 'fade'
    transition_duration_ms: int = 150


@dataclass
class LayoutConfig:
    """Video layout configuration for both formats"""
    
    landscape: Dict[str, Any] = field(default_factory=dict)
    portrait: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Set default layout values if not provided"""
        if not self.landscape:
            self.landscape = {
                'resolution': [1920, 1080],
                'expression_video': {
                    'width_percent': 50,
                    'position': 'left',
                    'padding': 10
                },
                'educational_slide': {
                    'width_percent': 50,
                    'position': 'right',
                    'padding': 10
                }
            }
        
        if not self.portrait:
            self.portrait = {
                'resolution': [1080, 1920],
                'context_video': {
                    'height_percent': 75,
                    'position': 'top',
                    'padding': 5
                },
                'educational_slide': {
                    'height_percent': 25,
                    'position': 'bottom',
                    'padding': 5
                }
            }


@dataclass
class ExpressionConfig:
    """Main expression pipeline configuration"""
    
    subtitle_styling: SubtitleStylingConfig
    playback: PlaybackConfig
    layout: LayoutConfig
    llm: Dict[str, Any] = field(default_factory=dict)
    whisper: Dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, config_dict: dict) -> 'ExpressionConfig':
        """
        Create ExpressionConfig from dictionary, following existing pattern
        
        Args:
            config_dict: Configuration dictionary from ConfigLoader
            
        Returns:
            ExpressionConfig instance
        """
        # Extract sections with defaults
        subtitle_styling_data = config_dict.get('subtitle_styling', {})
        playback_data = config_dict.get('playback', {})
        layout_data = config_dict.get('layout', {})
        llm_data = config_dict.get('llm', {})
        whisper_data = config_dict.get('whisper', {})
        
        return cls(
            subtitle_styling=SubtitleStylingConfig(**subtitle_styling_data),
            playback=PlaybackConfig(**playback_data),
            layout=LayoutConfig(**layout_data),
            llm=llm_data,
            whisper=whisper_data
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert ExpressionConfig to dictionary
        
        Returns:
            Dictionary representation of the configuration
        """
        return {
            'subtitle_styling': {
                'default': self.subtitle_styling.default,
                'expression_highlight': self.subtitle_styling.expression_highlight
            },
            'playback': {
                'expression_repeat_count': self.playback.expression_repeat_count,
                'context_play_count': self.playback.context_play_count,
                'repeat_delay_ms': self.playback.repeat_delay_ms,
                'transition_effect': self.playback.transition_effect,
                'transition_duration_ms': self.playback.transition_duration_ms
            },
            'layout': {
                'landscape': self.layout.landscape,
                'portrait': self.layout.portrait
            },
            'llm': self.llm,
            'whisper': self.whisper
        }
    
    def validate(self) -> List[str]:
        """
        Validate configuration values
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Validate playback settings
        if self.playback.expression_repeat_count < 1:
            errors.append("expression_repeat_count must be >= 1")
        
        if self.playback.context_play_count < 1:
            errors.append("context_play_count must be >= 1")
        
        if self.playback.repeat_delay_ms < 0:
            errors.append("repeat_delay_ms must be >= 0")
        
        if self.playback.transition_duration_ms < 0:
            errors.append("transition_duration_ms must be >= 0")
        
        # Validate layout resolutions
        landscape_res = self.layout.landscape.get('resolution', [])
        if len(landscape_res) != 2 or not all(isinstance(x, int) and x > 0 for x in landscape_res):
            errors.append("landscape resolution must be [width, height] with positive integers")
        
        portrait_res = self.layout.portrait.get('resolution', [])
        if len(portrait_res) != 2 or not all(isinstance(x, int) and x > 0 for x in portrait_res):
            errors.append("portrait resolution must be [width, height] with positive integers")
        
        # Validate subtitle styling
        if not isinstance(self.subtitle_styling.default, dict):
            errors.append("subtitle_styling.default must be a dictionary")
        
        if not isinstance(self.subtitle_styling.expression_highlight, dict):
            errors.append("subtitle_styling.expression_highlight must be a dictionary")
        
        return errors
