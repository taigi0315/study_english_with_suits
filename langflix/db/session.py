"""
Database session management for LangFlix.

This module provides database connection management and session handling.
"""

from contextlib import contextmanager
from typing import Generator

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
        
        # Check if database is enabled
        if not settings.get_database_enabled():
            # If disabled, we don't initialize the engine
            # Any attempt to use the session will raise an error, which is expected
            # if the caller didn't check get_database_enabled() first.
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
    
    @contextmanager
    def session(self) -> Generator[Session, None, None]:
        """
        Context manager for database session.
        
        Automatically handles commit, rollback, and close.
        
        Usage:
            with db_manager.session() as db:
                # ... database operations ...
                # Commit happens automatically on success
        
        Yields:
            Session: Database session
        """
        if not self._initialized:
            self.initialize()
        
        db = self.SessionLocal()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
    
    def get_session(self) -> Session:
        """
        Get database session (legacy method, use session() context manager instead).
        
        Note: When using get_session(), you must manually call:
        - db.commit() on success
        - db.rollback() on exception
        - db.close() in finally block
        """
        if not self._initialized:
            self.initialize()
        return self.SessionLocal()
    
    def create_tables(self):
        """Create all tables."""
        if not self._initialized:
            self.initialize()
        from langflix.db.models import Base
        Base.metadata.create_all(bind=self.engine)
    
    def check_connection(self) -> bool:
        """
        Check if database connection is available.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
        if not self._initialized:
            try:
                self.initialize()
            except Exception:
                return False
                
        if not self.engine:
            return False
            
        try:
            with self.engine.connect() as connection:
                from sqlalchemy import text
                connection.execute(text("SELECT 1"))
            return True
        except Exception:
            return False

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
