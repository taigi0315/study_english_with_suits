"""
Media processing package for LangFlix.

This package handles media file validation, expression video slicing,
and subtitle rendering for the expression-based learning feature.
"""

from .media_validator import MediaValidator, MediaMetadata
from .expression_slicer import ExpressionMediaSlicer
from .subtitle_renderer import SubtitleRenderer
from .media_scanner import MediaScanner
from .exceptions import (
    MediaValidationError,
    VideoSlicingError,
    SubtitleRenderingError
)

__all__ = [
    'MediaValidator',
    'MediaMetadata',
    'ExpressionMediaSlicer',
    'SubtitleRenderer',
    'MediaScanner',
    'MediaValidationError',
    'VideoSlicingError',
    'SubtitleRenderingError'
]
