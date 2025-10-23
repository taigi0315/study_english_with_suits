#!/usr/bin/env python3
"""
ASR-related exceptions for LangFlix

This module defines custom exceptions for ASR (Automatic Speech Recognition) operations.
"""


class AudioExtractionError(Exception):
    """
    Raised when audio extraction from media files fails.
    
    Attributes:
        media_path: The path to the media file that failed
        reason: Description of why extraction failed
    """
    
    def __init__(self, media_path: str, reason: str = ""):
        self.media_path = media_path
        self.reason = reason
        message = f"Failed to extract audio from '{media_path}'"
        if reason:
            message += f": {reason}"
        super().__init__(message)


class WhisperXError(Exception):
    """
    Raised when WhisperX transcription fails.
    
    Attributes:
        audio_path: The path to the audio file that failed
        reason: Description of why transcription failed
    """
    
    def __init__(self, audio_path: str, reason: str = ""):
        self.audio_path = audio_path
        self.reason = reason
        message = f"WhisperX transcription failed for '{audio_path}'"
        if reason:
            message += f": {reason}"
        super().__init__(message)


class TimestampAlignmentError(Exception):
    """
    Raised when timestamp alignment fails.
    
    Attributes:
        expression: The expression that failed alignment
        reason: Description of why alignment failed
        line_number: Line number where error occurred (optional)
    """
    
    def __init__(self, expression: str, reason: str = "", line_number: int = None):
        self.expression = expression
        self.reason = reason
        self.line_number = line_number
        message = f"Failed to align timestamps for expression '{expression}'"
        if reason:
            message += f": {reason}"
        if line_number is not None:
            message += f" (line {line_number})"
        super().__init__(message)


class ModelLoadError(Exception):
    """
    Raised when WhisperX model loading fails.
    
    Attributes:
        model_name: The name of the model that failed to load
        reason: Description of why model loading failed
    """
    
    def __init__(self, model_name: str, reason: str = ""):
        self.model_name = model_name
        self.reason = reason
        message = f"Failed to load WhisperX model '{model_name}'"
        if reason:
            message += f": {reason}"
        super().__init__(message)


class AudioPreprocessingError(Exception):
    """
    Raised when audio preprocessing fails.
    
    Attributes:
        audio_path: The path to the audio file that failed preprocessing
        reason: Description of why preprocessing failed
    """
    
    def __init__(self, audio_path: str, reason: str = ""):
        self.audio_path = audio_path
        self.reason = reason
        message = f"Audio preprocessing failed for '{audio_path}'"
        if reason:
            message += f": {reason}"
        super().__init__(message)


class TranscriptionTimeoutError(Exception):
    """
    Raised when transcription takes too long to complete.
    
    Attributes:
        audio_path: The path to the audio file
        timeout_seconds: The timeout that was exceeded
    """
    
    def __init__(self, audio_path: str, timeout_seconds: int):
        self.audio_path = audio_path
        self.timeout_seconds = timeout_seconds
        message = f"Transcription timeout after {timeout_seconds}s for '{audio_path}'"
        super().__init__(message)
