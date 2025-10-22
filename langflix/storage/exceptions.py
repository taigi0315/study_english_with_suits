"""
Storage-related exceptions for LangFlix.

This module defines custom exceptions for storage operations.
"""


class StorageError(Exception):
    """Base storage error."""
    pass


class StorageNotFoundError(StorageError):
    """File not found in storage."""
    pass


class StoragePermissionError(StorageError):
    """Permission denied."""
    pass


class StorageQuotaError(StorageError):
    """Storage quota exceeded."""
    pass


class StorageBackendError(StorageError):
    """Storage backend error."""
    pass
