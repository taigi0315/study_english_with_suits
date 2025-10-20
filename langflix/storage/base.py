"""
Abstract base class for storage backends
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional


class StorageBackend(ABC):
    """
    Abstract base class for storage backends
    """
    
    @property
    @abstractmethod
    def backend_type(self) -> str:
        """Return the type of storage backend (e.g., 'local', 's3')"""
        pass
    
    @abstractmethod
    def download_file(self, remote_path: str, local_path: Path) -> bool:
        """
        Download file from storage to local path
        
        Args:
            remote_path: Path in the remote storage
            local_path: Local path to save the file
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def upload_file(self, local_path: Path, remote_path: str) -> bool:
        """
        Upload file from local path to storage
        
        Args:
            local_path: Local path of the file to upload
            remote_path: Path in the remote storage
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def exists(self, remote_path: str) -> bool:
        """
        Check if file exists in storage
        
        Args:
            remote_path: Path in the remote storage
            
        Returns:
            True if file exists, False otherwise
        """
        pass
    
    def is_s3_path(self, path: str) -> bool:
        """
        Check if path is an S3 path (e.g., s3://bucket/key)
        
        Args:
            path: Path to check
            
        Returns:
            True if path is S3 path, False otherwise
        """
        return path.startswith('s3://')
    
    def extract_s3_key(self, s3_path: str) -> str:
        """
        Extract S3 key from S3 path
        
        Args:
            s3_path: S3 path (e.g., s3://bucket/key)
            
        Returns:
            S3 key (e.g., key)
        """
        if not self.is_s3_path(s3_path):
            raise ValueError(f"Not an S3 path: {s3_path}")
        
        # Remove s3:// prefix and extract key after first /
        parts = s3_path[5:].split('/', 1)
        if len(parts) < 2:
            raise ValueError(f"Invalid S3 path: {s3_path}")
        
        return parts[1]
