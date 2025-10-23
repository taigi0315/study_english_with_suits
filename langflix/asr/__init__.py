#!/usr/bin/env python3
"""
ASR (Automatic Speech Recognition) module for LangFlix

This module provides WhisperX integration for precise timestamp detection
and audio preprocessing capabilities.
"""

from .exceptions import (
    AudioExtractionError,
    WhisperXError,
    TimestampAlignmentError,
    ModelLoadError
)

__all__ = [
    'AudioExtractionError',
    'WhisperXError', 
    'TimestampAlignmentError',
    'ModelLoadError'
]
