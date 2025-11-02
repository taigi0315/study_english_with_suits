"""
Unit tests for database session context manager.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from langflix.db.session import DatabaseManager


class TestDatabaseSessionContextManager:
    """Test database session context manager functionality."""
    
    @pytest.fixture
    def db_manager(self):
        """Create a DatabaseManager instance for testing."""
        manager = DatabaseManager()
        manager._initialized = True
        manager.SessionLocal = Mock()
        return manager
    
    def test_context_manager_commit_on_success(self, db_manager):
        """Test that context manager commits on successful exit."""
        mock_session = MagicMock()
        db_manager.SessionLocal.return_value = mock_session
        
        with db_manager.session() as db:
            assert db == mock_session
        
        # Verify commit was called
        mock_session.commit.assert_called_once()
        # Verify close was called
        mock_session.close.assert_called_once()
        # Verify rollback was not called
        mock_session.rollback.assert_not_called()
    
    def test_context_manager_rollback_on_exception(self, db_manager):
        """Test that context manager rolls back on exception."""
        mock_session = MagicMock()
        db_manager.SessionLocal.return_value = mock_session
        
        with pytest.raises(ValueError):
            with db_manager.session() as db:
                assert db == mock_session
                raise ValueError("Test exception")
        
        # Verify rollback was called
        mock_session.rollback.assert_called_once()
        # Verify close was called even on exception
        mock_session.close.assert_called_once()
        # Verify commit was not called
        mock_session.commit.assert_not_called()
    
    def test_context_manager_always_closes(self, db_manager):
        """Test that context manager always closes session, even on exception during commit."""
        mock_session = MagicMock()
        mock_session.commit.side_effect = Exception("Commit failed")
        db_manager.SessionLocal.return_value = mock_session
        
        with pytest.raises(Exception):
            with db_manager.session() as db:
                pass
        
        # Verify close was still called even if commit failed
        mock_session.close.assert_called_once()
    
    def test_context_manager_initializes_if_needed(self, db_manager):
        """Test that context manager initializes database if not already initialized."""
        db_manager._initialized = False
        db_manager.initialize = Mock()
        mock_session = MagicMock()
        db_manager.SessionLocal = Mock(return_value=mock_session)
        
        with db_manager.session() as db:
            pass
        
        # Verify initialize was called
        db_manager.initialize.assert_called_once()
        # Verify session was created
        db_manager.SessionLocal.assert_called_once()
    
    def test_get_session_still_available(self, db_manager):
        """Test that legacy get_session() method still works."""
        mock_session = MagicMock()
        db_manager.SessionLocal.return_value = mock_session
        
        db = db_manager.get_session()
        
        assert db == mock_session
        db_manager.SessionLocal.assert_called_once()

