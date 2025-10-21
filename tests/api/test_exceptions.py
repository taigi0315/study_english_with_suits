"""
Tests for API exception handling.
"""

import pytest
from fastapi import HTTPException
from langflix.api.exceptions import (
    APIException,
    ValidationError,
    NotFoundError,
    ProcessingError,
    StorageError
)

def test_api_exception():
    """Test base APIException."""
    exc = APIException("Test error", 400, {"field": "value"})
    assert exc.message == "Test error"
    assert exc.status_code == 400
    assert exc.details == {"field": "value"}

def test_validation_error():
    """Test ValidationError."""
    exc = ValidationError("Invalid input", {"field": "required"})
    assert exc.message == "Invalid input"
    assert exc.status_code == 400
    assert exc.details == {"field": "required"}

def test_not_found_error():
    """Test NotFoundError."""
    exc = NotFoundError("Resource not found", {"resource_id": "123"})
    assert exc.message == "Resource not found"
    assert exc.status_code == 404
    assert exc.details == {"resource_id": "123"}

def test_processing_error():
    """Test ProcessingError."""
    exc = ProcessingError("Processing failed", {"step": "analysis"})
    assert exc.message == "Processing failed"
    assert exc.status_code == 422
    assert exc.details == {"step": "analysis"}

def test_storage_error():
    """Test StorageError."""
    exc = StorageError("Storage operation failed", {"operation": "save"})
    assert exc.message == "Storage operation failed"
    assert exc.status_code == 500
    assert exc.details == {"operation": "save"}
