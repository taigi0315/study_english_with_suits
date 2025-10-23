"""
Media processing exceptions for LangFlix.

This module defines custom exceptions for media validation,
video slicing, and subtitle rendering operations.
"""


class MediaValidationError(Exception):
    """Raised when media validation fails"""
    
    def __init__(self, message: str, file_path: str = None):
        self.file_path = file_path
        self.message = message
        if file_path:
            super().__init__(f"{message} (File: {file_path})")
        else:
            super().__init__(message)


class VideoSlicingError(Exception):
    """Raised when video slicing fails"""
    
    def __init__(self, message: str, expression: str = None, file_path: str = None):
        self.expression = expression
        self.file_path = file_path
        self.message = message
        
        error_msg = message
        if expression:
            error_msg += f" (Expression: {expression})"
        if file_path:
            error_msg += f" (File: {file_path})"
        
        super().__init__(error_msg)


class SubtitleRenderingError(Exception):
    """Raised when subtitle rendering fails"""
    
    def __init__(self, message: str, expression: str = None, file_path: str = None):
        self.expression = expression
        self.file_path = file_path
        self.message = message
        
        error_msg = message
        if expression:
            error_msg += f" (Expression: {expression})"
        if file_path:
            error_msg += f" (File: {file_path})"
        
        super().__init__(error_msg)
