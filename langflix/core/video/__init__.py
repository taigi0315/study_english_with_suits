"""
Video processing module for LangFlix.

This module contains specialized components for video composition,
short-form creation, and overlay rendering.

Components:
    - VideoComposer: Long-form video composition and concatenation
    - ShortFormCreator: 9:16 vertical video creation
    - OverlayRenderer: Text overlay rendering for short-form videos
    - FontResolver: Font management for multi-language videos
    - TransitionBuilder: Transition video creation

Refactored from original video_editor.py (3,554 lines) into focused modules.
"""

__all__ = [
    'VideoComposer',
    'ShortFormCreator',
    'OverlayRenderer',
    'FontResolver',
    'TransitionBuilder',
]
