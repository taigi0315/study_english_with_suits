"""
Custom API exceptions for LangFlix
"""

from fastapi import HTTPException
from typing import Any, Dict, Optional

class APIException(Exception):
    """Base API exception."""
    def __init__(self, message: str, status_code: int = 500, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

class ValidationError(APIException):
    """Validation error exception."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 422, details)

class NotFoundError(APIException):
    """Not found error exception."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 404, details)

class ProcessingError(APIException):
    """Processing error exception."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 500, details)

class StorageError(APIException):
    """Storage error exception."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 500, details)

def api_exception_handler(request, exc):
    """Handle API exceptions."""
    from fastapi.responses import JSONResponse
    from fastapi import HTTPException
    
    if isinstance(exc, APIException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.message,
                "status_code": exc.status_code,
                "details": exc.details
            }
        )
    elif isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.detail,
                "status_code": exc.status_code,
                "details": {}
            }
        )
    else:
        return JSONResponse(
            status_code=500,
            content={
                "error": str(exc),
                "status_code": 500,
                "details": {}
            }
        )
