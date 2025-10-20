"""
Storage abstraction layer for LangFlix
Supports local filesystem and S3 storage backends
"""

import logging
from typing import Optional
from pathlib import Path

from .base import StorageBackend
from .local import LocalStorage
from .s3 import S3Storage

logger = logging.getLogger(__name__)


def get_storage_backend() -> StorageBackend:
    """
    Factory function to get the appropriate storage backend based on configuration
    
    Returns:
        StorageBackend instance (LocalStorage or S3Storage)
    """
    try:
        from ..config.config_loader import ConfigLoader
        
        config_loader = ConfigLoader()
        backend_type = config_loader.get('storage', 'backend', default='local')
        
        logger.info(f"Initializing storage backend: {backend_type}")
        
        if backend_type == 's3':
            s3_config = config_loader.get_section('storage').get('s3', {})
            
            # For input operations, we'll use input bucket by default
            # This could be enhanced to support multiple buckets
            bucket = s3_config.get('input_bucket', 'langflix-input')
            region = s3_config.get('region', 'us-east-1')
            
            return S3Storage(bucket=bucket, region=region)
        else:
            # Default to local storage
            return LocalStorage()
            
    except Exception as e:
        logger.warning(f"Failed to initialize storage backend, falling back to local: {e}")
        return LocalStorage()


__all__ = ['StorageBackend', 'LocalStorage', 'S3Storage', 'get_storage_backend']
