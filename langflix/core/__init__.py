"""
LangFlix Core Module

This module contains the core functionality for video processing, subtitle analysis,
and expression extraction.
"""

from .language_config import LanguageConfig
from .subtitle_parser import parse_srt_file
from .subtitle_processor import SubtitleProcessor
from .video_processor import VideoProcessor
from .video_editor import VideoEditor

__all__ = [
    'LanguageConfig', 
    'parse_srt_file',
    'SubtitleProcessor',
    'VideoProcessor',
    'VideoEditor'
]
