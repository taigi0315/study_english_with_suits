"""
Dependency injection for LangFlix API
"""

from typing import Generator
from sqlalchemy.orm import Session
from langflix.db.session import DatabaseManager
from langflix.storage.factory import create_storage_backend

def get_db() -> Generator[Session, None, None]:
    """Get database session."""
    # TODO: Implement actual database session
    # For now, return None
    yield None

def get_storage():
    """Get storage backend."""
    # TODO: Implement actual storage backend
    # For now, return None
    return None
