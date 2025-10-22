"""
Google Cloud Storage backend for LangFlix.

This module implements the GoogleCloudStorage backend that uses Google Cloud Storage
for file operations, enabling cloud-based storage for API usage.
"""

from pathlib import Path
from typing import List, Optional
from .base import StorageBackend
from .exceptions import StorageError, StorageNotFoundError, StoragePermissionError


class GoogleCloudStorage(StorageBackend):
    """Google Cloud Storage backend."""
    
    def __init__(self, bucket_name: str, credentials_path: Optional[str] = None):
        """
        Initialize GoogleCloudStorage backend.
        
        Args:
            bucket_name: Name of the GCS bucket
            credentials_path: Path to service account JSON file
        """
        try:
            from google.cloud import storage
        except ImportError:
            raise ImportError("google-cloud-storage package is required for GCS backend")
        
        self.bucket_name = bucket_name
        try:
            self.client = storage.Client.from_service_account_json(
                credentials_path
            ) if credentials_path else storage.Client()
            self.bucket = self.client.bucket(bucket_name)
        except Exception as e:
            raise StorageError(f"Failed to initialize GCS client: {e}")
    
    def save_file(self, local_path: Path, remote_path: str) -> str:
        """
        Upload file to GCS bucket.
        
        Args:
            local_path: Path to local file
            remote_path: Destination path in storage
            
        Returns:
            GCS URL of uploaded file
        """
        try:
            blob = self.bucket.blob(remote_path)
            blob.upload_from_filename(str(local_path))
            return f"gcs://{self.bucket_name}/{remote_path}"
        except Exception as e:
            raise StorageError(f"Failed to upload file {local_path} to {remote_path}: {e}")
    
    def load_file(self, remote_path: str, local_path: Path) -> bool:
        """
        Download file from GCS bucket.
        
        Args:
            remote_path: Path in storage
            local_path: Destination local path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            blob = self.bucket.blob(remote_path)
            blob.download_to_filename(str(local_path))
            return True
        except Exception as e:
            if "not found" in str(e).lower():
                return False
            raise StorageError(f"Failed to download file {remote_path}: {e}")
    
    def delete_file(self, remote_path: str) -> bool:
        """
        Delete file from GCS bucket.
        
        Args:
            remote_path: Path in storage
            
        Returns:
            True if successful, False otherwise
        """
        try:
            blob = self.bucket.blob(remote_path)
            blob.delete()
            return True
        except Exception as e:
            if "not found" in str(e).lower():
                return False
            raise StorageError(f"Failed to delete file {remote_path}: {e}")
    
    def list_files(self, prefix: str) -> List[str]:
        """
        List files with given prefix in GCS bucket.
        
        Args:
            prefix: Path prefix to search for
            
        Returns:
            List of file paths matching the prefix
        """
        try:
            blobs = self.bucket.list_blobs(prefix=prefix)
            return [blob.name for blob in blobs]
        except Exception as e:
            raise StorageError(f"Failed to list files with prefix {prefix}: {e}")
    
    def file_exists(self, remote_path: str) -> bool:
        """
        Check if file exists in GCS bucket.
        
        Args:
            remote_path: Path in storage
            
        Returns:
            True if file exists, False otherwise
        """
        try:
            blob = self.bucket.blob(remote_path)
            return blob.exists()
        except Exception:
            return False
    
    def get_file_url(self, remote_path: str) -> str:
        """
        Get public URL for GCS file.
        
        Args:
            remote_path: Path in storage
            
        Returns:
            Public URL for the file
        """
        try:
            blob = self.bucket.blob(remote_path)
            return blob.public_url
        except Exception as e:
            raise StorageError(f"Failed to get URL for file {remote_path}: {e}")
