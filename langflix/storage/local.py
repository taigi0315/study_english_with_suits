"""
Local filesystem storage backend for LangFlix.

This module implements the LocalStorage backend that uses the local filesystem
for file operations, maintaining backward compatibility with existing CLI usage.
"""

import shutil
from pathlib import Path
from typing import List
from .base import StorageBackend
from .exceptions import StorageError, StorageNotFoundError


class LocalStorage(StorageBackend):
    """Local filesystem storage backend."""
    
    def __init__(self, base_path: Path):
        """
        Initialize LocalStorage backend.
        
        Args:
            base_path: Base directory for storage operations
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def save_file(self, local_path: Path, remote_path: str) -> str:
        """
        Copy file to local storage directory.
        
        Args:
            local_path: Path to local file
            remote_path: Destination path in storage
            
        Returns:
            Local file path where file was saved
        """
        try:
            dest_path = self.base_path / remote_path
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(local_path, dest_path)
            return str(dest_path)
        except Exception as e:
            raise StorageError(f"Failed to save file {local_path} to {remote_path}: {e}")
    
    def load_file(self, remote_path: str, local_path: Path) -> bool:
        """
        Copy file from local storage to destination.
        
        Args:
            remote_path: Path in storage
            local_path: Destination local path
            
        Returns:
            True if successful, False otherwise
        """
        try:
            source_path = self.base_path / remote_path
            if not source_path.exists():
                return False
            shutil.copy2(source_path, local_path)
            return True
        except Exception:
            return False
    
    def delete_file(self, remote_path: str) -> bool:
        """
        Delete file from local storage.
        
        Args:
            remote_path: Path in storage
            
        Returns:
            True if successful, False otherwise
        """
        try:
            file_path = self.base_path / remote_path
            if file_path.exists():
                file_path.unlink()
                return True
            return False
        except Exception:
            return False
    
    def list_files(self, prefix: str) -> List[str]:
        """
        List files with given prefix.
        
        Args:
            prefix: Path prefix to search for
            
        Returns:
            List of file paths matching the prefix
        """
        try:
            search_path = self.base_path / prefix
            if not search_path.exists():
                return []
            return [str(p.relative_to(self.base_path)) 
                       for p in search_path.rglob('*') if p.is_file()]
        except Exception:
            return []
    
    def file_exists(self, remote_path: str) -> bool:
        """
        Check if file exists in local storage.
        
        Args:
            remote_path: Path in storage
            
        Returns:
            True if file exists, False otherwise
        """
        return (self.base_path / remote_path).exists()
    
    def get_file_url(self, remote_path: str) -> str:
        """
        Return local file path.
        
        Args:
            remote_path: Path in storage
            
        Returns:
            Local file path
        """
        return str(self.base_path / remote_path)
