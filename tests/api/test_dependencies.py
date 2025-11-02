"""
Tests for API dependencies (get_db, get_storage).
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session
from langflix.api.dependencies import get_db, get_storage, db_manager
from langflix.storage.base import StorageBackend


class TestGetDB:
    """Tests for get_db dependency."""
    
    def test_get_db_when_database_disabled(self):
        """Test get_db returns None when database is disabled."""
        with patch('langflix.api.dependencies.settings.get_database_enabled', return_value=False):
            gen = get_db()
            result = next(gen)
            assert result is None
    
    def test_get_db_when_database_enabled(self):
        """Test get_db yields session when database is enabled."""
        mock_session = Mock(spec=Session)
        
        with patch('langflix.api.dependencies.settings.get_database_enabled', return_value=True):
            with patch.object(db_manager, '_initialized', True):
                with patch.object(db_manager, 'get_session', return_value=mock_session):
                    gen = get_db()
                    session = next(gen)
                    assert session == mock_session
                    
                    # Simulate successful completion
                    try:
                        next(gen)
                    except StopIteration:
                        pass
                    
                    # Verify commit was called
                    mock_session.commit.assert_called_once()
                    mock_session.close.assert_called_once()
    
    def test_get_db_rollback_on_exception(self):
        """Test get_db rolls back on exception."""
        mock_session = Mock(spec=Session)
        mock_session.commit.side_effect = Exception("Test error")
        
        with patch('langflix.api.dependencies.settings.get_database_enabled', return_value=True):
            with patch.object(db_manager, '_initialized', True):
                with patch.object(db_manager, 'get_session', return_value=mock_session):
                    gen = get_db()
                    session = next(gen)
                    
                    # Simulate exception during processing
                    try:
                        next(gen)
                    except StopIteration:
                        pass
                    except Exception:
                        # Exception should be raised
                        pass
                    
                    # Verify rollback was called
                    mock_session.rollback.assert_called_once()
                    mock_session.close.assert_called_once()
    
    def test_get_db_initializes_if_not_initialized(self):
        """Test get_db initializes database manager if not initialized."""
        mock_session = Mock(spec=Session)
        
        with patch('langflix.api.dependencies.settings.get_database_enabled', return_value=True):
            with patch.object(db_manager, '_initialized', False):
                with patch.object(db_manager, 'initialize') as mock_init:
                    with patch.object(db_manager, 'get_session', return_value=mock_session):
                        gen = get_db()
                        next(gen)
                        mock_init.assert_called_once()
                        
                        # Cleanup
                        try:
                            next(gen)
                        except StopIteration:
                            pass


class TestGetStorage:
    """Tests for get_storage dependency."""
    
    def test_get_storage_returns_storage_backend(self):
        """Test get_storage returns storage backend instance."""
        mock_storage = Mock(spec=StorageBackend)
        
        with patch('langflix.api.dependencies.create_storage_backend', return_value=mock_storage):
            result = get_storage()
            assert result == mock_storage
    
    def test_get_storage_calls_factory(self):
        """Test get_storage calls create_storage_backend factory."""
        with patch('langflix.api.dependencies.create_storage_backend') as mock_factory:
            mock_factory.return_value = Mock(spec=StorageBackend)
            get_storage()
            mock_factory.assert_called_once()

