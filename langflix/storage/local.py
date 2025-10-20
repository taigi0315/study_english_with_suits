"""
Local filesystem storage backend
"""

import shutil
import logging
from pathlib import Path
from typing import Optional

from .base import StorageBackend

logger = logging.getLogger(__name__)


class LocalStorage(StorageBackend):
    """
    Local filesystem storage backend - maintains current behavior
    """
    
    @property
    def backend_type(self) -> str:
        return 'local'
    
    def download_file(self, remote_path: str, local_path: Path) -> bool:
        """
        For local storage, this is essentially a copy operation or no-op
        
        Args:
            remote_path: Source path (local)
            local_path: Destination path (local)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            source_path = Path(remote_path)
            
            if not source_path.exists():
                logger.error(f"Source file does not exist: {remote_path}")
                return False
            
            # Ensure destination directory exists
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            # If source and destination are the same, just verify existence
            if source_path.resolve() == local_path.resolve():
                return True
            
            # Copy file to destination
            shutil.copy2(source_path, local_path)
            logger.debug(f"Copied {remote_path} to {local_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to download file {remote_path} to {local_path}: {e}")
            return False
    
    def upload_file(self, local_path: Path, remote_path: str) -> bool:
        """
        For local storage, this is essentially a copy operation or no-op
        
        Args:
            local_path: Source path (local)
            remote_path: Destination path (local)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            dest_path = Path(remote_path)
            
            if not local_path.exists():
                logger.error(f"Source file does not exist: {local_path}")
                return False
            
            # Ensure destination directory exists
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            
            # If source and destination are the same, just verify existence
            if local_path.resolve() == dest_path.resolve():
                return True
            
            # Copy file to destination
            shutil.copy2(local_path, dest_path)
            logger.debug(f"Copied {local_path} to {remote_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to upload file {local_path} to {remote_path}: {e}")
            return False
    
    def exists(self, remote_path: str) -> bool:
        """
        Check if file exists in local filesystem
        
        Args:
            remote_path: Local file path
            
        Returns:
            True if file exists, False otherwise
        """
        try:
            path = Path(remote_path)
            exists = path.exists()
            logger.debug(f"File {remote_path} exists: {exists}")
            return exists
        except Exception as e:
            logger.error(f"Error checking file existence {remote_path}: {e}")
            return False
