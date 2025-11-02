"""
Dependency injection for LangFlix API
"""

from typing import Generator, Optional
from sqlalchemy.orm import Session
from langflix.db.session import DatabaseManager
from langflix.storage.factory import create_storage_backend
from langflix.storage.base import StorageBackend
from langflix import settings

# Global database manager instance
db_manager = DatabaseManager()


def get_db() -> Generator[Optional[Session], None, None]:
    """
    FastAPI dependency for database session.
    
    Returns:
        Session: Database session (or None if database is disabled)
        
    Yields:
        Session: Database session that is automatically committed or rolled back
    """
    if not settings.get_database_enabled():
        # Return None if database is disabled (file-only mode)
        yield None
        return
    
    # Use context manager for automatic resource management
    with db_manager.session() as db:
        yield db


def get_storage() -> StorageBackend:
    """
    FastAPI dependency for storage backend.
    
    Returns:
        StorageBackend: Storage backend instance (Local or GCS)
    """
    return create_storage_backend()
