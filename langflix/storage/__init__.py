"""
Storage module for LangFlix.

This module provides storage abstraction for file operations,
supporting multiple backends (local filesystem and Google Cloud Storage).
"""

from .base import StorageBackend
from .local import LocalStorage
from .gcs import GoogleCloudStorage
from .factory import create_storage_backend, create_storage_backend_with_config
from .exceptions import (
    StorageError,
    StorageNotFoundError,
    StoragePermissionError,
    StorageQuotaError,
    StorageBackendError
)

__all__ = [
    'StorageBackend',
    'LocalStorage',
    'GoogleCloudStorage',
    'create_storage_backend',
    'create_storage_backend_with_config',
    'StorageError',
    'StorageNotFoundError',
    'StoragePermissionError',
    'StorageQuotaError',
    'StorageBackendError'
]
