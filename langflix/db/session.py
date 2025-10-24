"""
Database session management for LangFlix.

This module provides database connection management and session handling.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from langflix import settings


class DatabaseManager:
    """Database connection manager."""
    
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self._initialized = False
    
    def initialize(self):
        """Initialize database connection."""
        if self._initialized:
            return
        
        database_url = settings.get_database_url()
        self.engine = create_engine(
            database_url,
            pool_size=settings.get_database_pool_size(),
            max_overflow=settings.get_database_max_overflow(),
            echo=settings.get_database_echo()
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self._initialized = True
    
    def get_session(self) -> Session:
        """Get database session."""
        if not self._initialized:
            self.initialize()
        return self.SessionLocal()
    
    def create_tables(self):
        """Create all tables."""
        if not self._initialized:
            self.initialize()
        from langflix.db.models import Base
        Base.metadata.create_all(bind=self.engine)
    
    def close(self):
        """Close database connections."""
        if self.engine:
            self.engine.dispose()
        self._initialized = False


# Global database manager
db_manager = DatabaseManager()


def get_db_session() -> Session:
    """Get database session for dependency injection."""
    return db_manager.get_session()
