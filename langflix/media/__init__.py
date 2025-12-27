"""
Media processing package for LangFlix.

This package handles media file scanning and exception handling
for the expression-based learning feature.
"""

from .media_scanner import MediaScanner
from .exceptions import (
    MediaValidationError,
    VideoSlicingError,
    SubtitleRenderingError
)

__all__ = [
    'MediaScanner',
    'MediaValidationError',
    'VideoSlicingError',
    'SubtitleRenderingError'
]
