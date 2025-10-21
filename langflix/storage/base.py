"""
Abstract storage backend interface for LangFlix.

This module defines the abstract base class for storage backends,
providing a unified interface for file operations across different storage systems.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional


class StorageBackend(ABC):
    """Abstract base class for storage backends."""
    
    @abstractmethod
    def save_file(self, local_path: Path, remote_path: str) -> str:
        """
        Save file to storage.
        
        Args:
            local_path: Path to local file
            remote_path: Destination path in storage
            
        Returns:
            URL or path to stored file
        """
        pass
    
    @abstractmethod
    def load_file(self, remote_path: str, local_path: Path) -> bool:
        """
        Load file from storage to local filesystem.
        
        Args:
            remote_path: Path in storage
            local_path: Destination local path
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def delete_file(self, remote_path: str) -> bool:
        """
        Delete file from storage.
        
        Args:
            remote_path: Path in storage
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def list_files(self, prefix: str) -> List[str]:
        """
        List files with given prefix.
        
        Args:
            prefix: Path prefix to search for
            
        Returns:
            List of file paths matching the prefix
        """
        pass
    
    @abstractmethod
    def file_exists(self, remote_path: str) -> bool:
        """
        Check if file exists in storage.
        
        Args:
            remote_path: Path in storage
            
        Returns:
            True if file exists, False otherwise
        """
        pass
    
    @abstractmethod
    def get_file_url(self, remote_path: str) -> str:
        """
        Get public URL for file (if applicable).
        
        Args:
            remote_path: Path in storage
            
        Returns:
            Public URL or local path
        """
        pass
