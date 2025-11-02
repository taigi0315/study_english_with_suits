"""
Tests for health check endpoints.
"""

import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import text
from langflix.api.main import app

client = TestClient(app)

def test_health_check():
    """Test basic health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert data["service"] == "LangFlix API"

def test_detailed_health_check_with_database_disabled():
    """Test detailed health check when database is disabled."""
    mock_storage = Mock()
    mock_storage.list_files.return_value = []
    
    with patch('langflix.api.dependencies.settings.get_database_enabled', return_value=False):
        with patch('langflix.api.dependencies.create_storage_backend', return_value=mock_storage):
            response = client.get("/health/detailed")
            assert response.status_code == 200
            
            data = response.json()
            assert data["status"] == "healthy"
            assert "timestamp" in data
            assert "components" in data
            assert data["components"]["database"] == "disabled"
            assert data["components"]["storage"] == "available"
            # "tts" field is in the main response (not in components)
            assert data["tts"] == "ready"

def test_detailed_health_check_with_database_enabled():
    """Test detailed health check when database is enabled."""
    mock_session = Mock(spec=Session)
    mock_session.execute.return_value = None
    
    mock_storage = Mock()
    mock_storage.list_files.return_value = []
    
    # Mock database manager
    with patch('langflix.api.dependencies.settings.get_database_enabled', return_value=True):
        with patch('langflix.api.dependencies.db_manager._initialized', True):
            with patch('langflix.api.dependencies.db_manager.get_session', return_value=mock_session):
                with patch('langflix.api.dependencies.create_storage_backend', return_value=mock_storage):
                    response = client.get("/health/detailed")
                    assert response.status_code == 200
                    
                    data = response.json()
                    assert data["status"] == "healthy"
                    assert "components" in data
                    assert data["components"]["database"] == "connected"
                    assert data["components"]["storage"] == "available"
                    
                    # Verify database check was performed
                    mock_session.execute.assert_called_once()

def test_detailed_health_check_database_error():
    """Test detailed health check when database has error."""
    mock_session = Mock(spec=Session)
    mock_session.execute.side_effect = Exception("Connection error")
    
    mock_storage = Mock()
    mock_storage.list_files.return_value = []
    
    with patch('langflix.api.dependencies.settings.get_database_enabled', return_value=True):
        with patch('langflix.api.dependencies.db_manager._initialized', True):
            with patch('langflix.api.dependencies.db_manager.get_session', return_value=mock_session):
                with patch('langflix.api.dependencies.create_storage_backend', return_value=mock_storage):
                    response = client.get("/health/detailed")
                    assert response.status_code == 200
                    
                    data = response.json()
                    assert data["status"] == "healthy"
                    assert "components" in data
                    assert "error" in data["components"]["database"]

def test_detailed_health_check_storage_error():
    """Test detailed health check when storage has error."""
    mock_session = Mock(spec=Session)
    mock_session.execute.return_value = None
    
    mock_storage = Mock()
    mock_storage.list_files.side_effect = Exception("Storage error")
    
    with patch('langflix.api.dependencies.settings.get_database_enabled', return_value=True):
        with patch('langflix.api.dependencies.db_manager._initialized', True):
            with patch('langflix.api.dependencies.db_manager.get_session', return_value=mock_session):
                with patch('langflix.api.dependencies.create_storage_backend', return_value=mock_storage):
                    response = client.get("/health/detailed")
                    assert response.status_code == 200
                    
                    data = response.json()
                    assert data["status"] == "healthy"
                    assert "components" in data
                    assert "error" in data["components"]["storage"]
