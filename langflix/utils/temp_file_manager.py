"""
Centralized temporary file management utility.

This module provides TempFileManager class for managing temporary files and
directories with automatic cleanup using context managers. This ensures that
temporary files are properly cleaned up even when exceptions occur.

Usage:
    from langflix.utils.temp_file_manager import get_temp_manager
    
    manager = get_temp_manager()
    
    # Create temporary file (automatically cleaned up)
    with manager.create_temp_file(suffix='.mkv') as temp_path:
        # Use temp_path
        temp_path.write_bytes(b"content")
    
    # Create temporary directory (automatically cleaned up)
    with manager.create_temp_dir() as temp_dir:
        # Use temp_dir
        (temp_dir / "file.txt").write_text("content")
"""
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Optional
import tempfile
import logging
import atexit
import shutil

logger = logging.getLogger(__name__)


class TempFileManager:
    """Centralized temporary file management with automatic cleanup."""
    
    def __init__(self, prefix: str = "langflix_", base_dir: Optional[Path] = None):
        """
        Initialize temp file manager.
        
        Args:
            prefix: Prefix for temporary files and directories
            base_dir: Base directory for temp files (default: system temp dir)
        """
        self.prefix = prefix
        self.base_dir = Path(base_dir) if base_dir else Path(tempfile.gettempdir())
        self.temp_files: list[Path] = []
        self.temp_dirs: list[Path] = []
        
        # Register cleanup on exit
        atexit.register(self.cleanup_all)
    
    @contextmanager
    def create_temp_file(
        self, 
        suffix: str = "", 
        prefix: Optional[str] = None,
        delete: bool = True
    ) -> Generator[Path, None, None]:
        """
        Create a temporary file with automatic cleanup.
        
        Args:
            suffix: File suffix (e.g., '.mkv', '.srt')
            prefix: Optional override for prefix
            delete: If True, delete file when context exits
        
        Yields:
            Path to temporary file
        
        Example:
            with manager.create_temp_file(suffix='.mkv') as temp_path:
                temp_path.write_bytes(b"content")
            # File is automatically deleted after context exits
        """
        file_prefix = prefix or self.prefix
        temp_path: Optional[Path] = None
        
        try:
            # Use NamedTemporaryFile for cross-platform compatibility
            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=suffix,
                prefix=file_prefix,
                dir=str(self.base_dir)
            ) as f:
                temp_path = Path(f.name)
            
            # Register file before yielding (so it's tracked even if exception occurs)
            self.temp_files.append(temp_path)
            
            yield temp_path
            
        finally:
            if temp_path is not None:
                if delete and temp_path.exists():
                    try:
                        temp_path.unlink()
                        if temp_path in self.temp_files:
                            self.temp_files.remove(temp_path)
                        logger.debug(f"Cleaned up temp file: {temp_path}")
                    except Exception as e:
                        logger.warning(f"Failed to cleanup temp file {temp_path}: {e}")
                # If delete=False, keep file but leave it in tracking
                # so cleanup_all() can still clean it up if needed
    
    @contextmanager
    def create_temp_dir(self, prefix: Optional[str] = None) -> Generator[Path, None, None]:
        """
        Create a temporary directory with automatic cleanup.
        
        Args:
            prefix: Optional override for prefix
        
        Yields:
            Path to temporary directory
        
        Example:
            with manager.create_temp_dir() as temp_dir:
                (temp_dir / "file.txt").write_text("content")
            # Directory and all contents are automatically deleted after context exits
        """
        dir_prefix = prefix or self.prefix
        temp_dir: Optional[Path] = None
        
        try:
            temp_dir = Path(tempfile.mkdtemp(
                prefix=dir_prefix,
                dir=str(self.base_dir)
            ))
            self.temp_dirs.append(temp_dir)
            
            yield temp_dir
            
        finally:
            if temp_dir is not None:
                if temp_dir.exists():
                    try:
                        shutil.rmtree(temp_dir)
                        if temp_dir in self.temp_dirs:
                            self.temp_dirs.remove(temp_dir)
                        logger.debug(f"Cleaned up temp dir: {temp_dir}")
                    except Exception as e:
                        logger.warning(f"Failed to cleanup temp dir {temp_dir}: {e}")
    
    def register_file(self, file_path: Path) -> None:
        """
        Manually register a file for cleanup.
        
        Useful when you have a file that was created outside of the
        context manager but should still be cleaned up.
        
        Args:
            file_path: Path to file to register
        """
        if file_path not in self.temp_files:
            self.temp_files.append(file_path)
            logger.debug(f"Registered file for cleanup: {file_path}")
    
    def cleanup_all(self) -> None:
        """Clean up all registered temporary files and directories."""
        # Clean up files
        for temp_file in self.temp_files[:]:  # Use slice to avoid modification during iteration
            try:
                if temp_file.exists():
                    temp_file.unlink()
                    logger.debug(f"Cleaned up temp file: {temp_file}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file {temp_file}: {e}")
        
        self.temp_files.clear()
        
        # Clean up directories
        for temp_dir in self.temp_dirs[:]:  # Use slice to avoid modification during iteration
            try:
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)
                    logger.debug(f"Cleaned up temp dir: {temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp dir {temp_dir}: {e}")
        
        self.temp_dirs.clear()


# Global instance
_global_manager: Optional[TempFileManager] = None


def get_temp_manager() -> TempFileManager:
    """
    Get global temporary file manager instance.
    
    Returns:
        Global TempFileManager singleton instance
    
    Example:
        manager = get_temp_manager()
        with manager.create_temp_file(suffix='.mkv') as temp_path:
            # Use temp_path
            pass
    """
    global _global_manager
    if _global_manager is None:
        _global_manager = TempFileManager()
    return _global_manager

