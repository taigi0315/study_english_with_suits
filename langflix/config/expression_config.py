#!/usr/bin/env python3
"""
Expression Configuration Module for LangFlix
Defines dataclasses for expression-based learning configuration
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List


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
                'color': '#FFD700',
                'font_weight': 'bold',
                'font_size': 28,
                'background_color': '#1A1A1A',
                'background_opacity': 0.85,
                'animation': 'fade_in',
                'duration_ms': 300
            }


@dataclass
class PlaybackConfig:
    """Video playback configuration for expressions"""
    expression_repeat_count: int = 2
    context_play_count: int = 1
    repeat_delay_ms: int = 200
    transition_effect: str = 'fade'
    transition_duration_ms: int = 150
    
    def __post_init__(self):
        """Validate configuration values"""
        if self.expression_repeat_count < 1:
            self.expression_repeat_count = 1
        if self.context_play_count < 1:
            self.context_play_count = 1
        if self.repeat_delay_ms < 0:
            self.repeat_delay_ms = 0
        if self.transition_duration_ms < 0:
            self.transition_duration_ms = 0


@dataclass
class LayoutConfig:
    """Layout configuration for different video formats"""
    landscape: Dict[str, Any] = field(default_factory=dict)
    portrait: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Set default layout configurations"""
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
    """Main expression configuration class"""
    subtitle_styling: SubtitleStylingConfig
    playback: PlaybackConfig
    layout: LayoutConfig
    llm: Dict[str, Any] = field(default_factory=dict)
    # Note: whisper field removed - using external transcription
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'ExpressionConfig':
        """Create ExpressionConfig from dictionary (ConfigLoader result)"""
        # Handle subtitle_styling
        subtitle_styling_data = config_dict.get('subtitle_styling', {})
        subtitle_styling = SubtitleStylingConfig(
            default=subtitle_styling_data.get('default', {}),
            expression_highlight=subtitle_styling_data.get('expression_highlight', {})
        )
        
        # Handle playback
        playback_data = config_dict.get('playback', {})
        playback = PlaybackConfig(
            expression_repeat_count=playback_data.get('expression_repeat_count', 2),
            context_play_count=playback_data.get('context_play_count', 1),
            repeat_delay_ms=playback_data.get('repeat_delay_ms', 200),
            transition_effect=playback_data.get('transition_effect', 'fade'),
            transition_duration_ms=playback_data.get('transition_duration_ms', 150)
        )
        
        # Handle layout
        layout_data = config_dict.get('layout', {})
        layout = LayoutConfig(
            landscape=layout_data.get('landscape', {}),
            portrait=layout_data.get('portrait', {})
        )
        
        # Handle additional configs
        llm = config_dict.get('llm', {})
        # Note: whisper config removed - using external transcription
        
        return cls(
            subtitle_styling=subtitle_styling,
            playback=playback,
            layout=layout,
            llm=llm
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert ExpressionConfig to dictionary"""
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
            'llm': self.llm
            # Note: whisper field removed - using external transcription
        }