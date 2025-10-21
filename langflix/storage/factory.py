"""
Storage backend factory for LangFlix.

This module provides factory functions for creating storage backends
based on configuration or explicit parameters.
"""

from pathlib import Path
from typing import Optional
from .base import StorageBackend
from .local import LocalStorage
from .gcs import GoogleCloudStorage
from .exceptions import StorageBackendError


def create_storage_backend() -> StorageBackend:
    """
    Create storage backend based on configuration.
    
    Returns:
        Configured storage backend instance
        
    Raises:
        StorageBackendError: If backend type is unknown or configuration is invalid
    """
    try:
        from langflix import settings
    except ImportError:
        raise StorageBackendError("Settings module not available")
    
    backend_type = settings.get_storage_backend()
    
    if backend_type == "local":
        base_path = settings.get_storage_local_path()
        return LocalStorage(Path(base_path))
    
    elif backend_type == "gcs":
        bucket_name = settings.get_storage_gcs_bucket()
        credentials_path = settings.get_storage_gcs_credentials()
        if not bucket_name:
            raise StorageBackendError("GCS bucket name not configured")
        return GoogleCloudStorage(bucket_name, credentials_path)
    
    else:
        raise StorageBackendError(f"Unknown storage backend: {backend_type}")


def create_storage_backend_with_config(backend_type: str, **kwargs) -> StorageBackend:
    """
    Create storage backend with explicit configuration.
    
    Args:
        backend_type: Type of storage backend ("local" or "gcs")
        **kwargs: Backend-specific configuration parameters
        
    Returns:
        Configured storage backend instance
        
    Raises:
        StorageBackendError: If backend type is unknown or configuration is invalid
    """
    if backend_type == "local":
        base_path = kwargs.get('base_path', 'output')
        return LocalStorage(Path(base_path))
    
    elif backend_type == "gcs":
        bucket_name = kwargs.get('bucket_name')
        credentials_path = kwargs.get('credentials_path')
        if not bucket_name:
            raise StorageBackendError("bucket_name is required for GCS backend")
        return GoogleCloudStorage(bucket_name, credentials_path)
    
    else:
        raise StorageBackendError(f"Unknown storage backend: {backend_type}")
