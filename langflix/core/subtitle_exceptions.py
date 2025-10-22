#!/usr/bin/env python3
"""
Subtitle-related exceptions for LangFlix

This module defines custom exceptions for subtitle processing errors.
"""


class SubtitleNotFoundError(FileNotFoundError):
    """
    Raised when a subtitle file doesn't exist at the specified path.
    
    Attributes:
        path: The path to the subtitle file that was not found
    """
    
    def __init__(self, path: str):
        self.path = path
        super().__init__(f"Subtitle file not found: {path}")


class SubtitleFormatError(ValueError):
    """
    Raised when a subtitle format is invalid or unsupported.
    
    Attributes:
        format: The format that caused the error (e.g., 'srt', 'vtt')
        reason: Description of why the format is invalid
    """
    
    def __init__(self, format_type: str, reason: str):
        self.format = format_type
        self.reason = reason
        super().__init__(f"Invalid {format_type} format: {reason}")


class SubtitleEncodingError(UnicodeError):
    """
    Raised when subtitle encoding cannot be detected or decoded.
    
    Attributes:
        path: The path to the subtitle file
        attempted_encodings: List of encodings that were tried
    """
    
    def __init__(self, path: str, attempted_encodings: list = None):
        self.path = path
        self.attempted_encodings = attempted_encodings or []
        encodings_str = ", ".join(self.attempted_encodings) if self.attempted_encodings else "unknown"
        super().__init__(f"Failed to decode subtitle file '{path}'. Tried encodings: {encodings_str}")


class SubtitleParseError(ValueError):
    """
    Raised when subtitle parsing fails for structural reasons.
    
    Attributes:
        path: The path to the subtitle file
        line_number: The line number where parsing failed (if applicable)
        reason: Description of the parsing error
    """
    
    def __init__(self, path: str, reason: str, line_number: int = None):
        self.path = path
        self.line_number = line_number
        self.reason = reason
        
        error_msg = f"Failed to parse subtitle file '{path}': {reason}"
        if line_number is not None:
            error_msg += f" (line {line_number})"
        
        super().__init__(error_msg)

