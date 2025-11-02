"""
Tests for health check endpoints.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
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
    mock_checker = Mock()
    mock_checker.get_overall_health.return_value = {
        "status": "healthy",
        "timestamp": "2025-01-30T00:00:00Z",
        "components": {
            "database": {"status": "disabled", "message": "Database disabled"},
            "storage": {"status": "healthy", "message": "OK"},
            "redis": {"status": "healthy"},
            "tts": {"status": "healthy", "message": "OK"}
        }
    }
    
    with patch('langflix.api.routes.health.SystemHealthChecker', return_value=mock_checker):
        response = client.get("/health/detailed")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "components" in data
        assert data["components"]["database"]["status"] == "disabled"
        assert data["components"]["storage"]["status"] == "healthy"

def test_detailed_health_check_with_database_enabled():
    """Test detailed health check when database is enabled."""
    mock_checker = Mock()
    mock_checker.get_overall_health.return_value = {
        "status": "healthy",
        "timestamp": "2025-01-30T00:00:00Z",
        "components": {
            "database": {"status": "healthy", "message": "Database connection successful"},
            "storage": {"status": "healthy", "message": "OK"},
            "redis": {"status": "healthy"},
            "tts": {"status": "healthy", "message": "OK"}
        }
    }
    
    with patch('langflix.api.routes.health.SystemHealthChecker', return_value=mock_checker):
        response = client.get("/health/detailed")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "components" in data
        assert data["components"]["database"]["status"] == "healthy"
        assert data["components"]["storage"]["status"] == "healthy"

def test_detailed_health_check_database_error():
    """Test detailed health check when database has error."""
    mock_checker = Mock()
    mock_checker.get_overall_health.return_value = {
        "status": "unhealthy",
        "timestamp": "2025-01-30T00:00:00Z",
        "components": {
            "database": {"status": "unhealthy", "message": "Database connection failed: Connection error"},
            "storage": {"status": "healthy", "message": "OK"},
            "redis": {"status": "healthy"},
            "tts": {"status": "healthy", "message": "OK"}
        }
    }
    
    with patch('langflix.api.routes.health.SystemHealthChecker', return_value=mock_checker):
        response = client.get("/health/detailed")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "unhealthy"
        assert "components" in data
        assert data["components"]["database"]["status"] == "unhealthy"
        assert "Connection error" in data["components"]["database"]["message"]

def test_detailed_health_check_storage_error():
    """Test detailed health check when storage has error."""
    mock_checker = Mock()
    mock_checker.get_overall_health.return_value = {
        "status": "unhealthy",
        "timestamp": "2025-01-30T00:00:00Z",
        "components": {
            "database": {"status": "healthy", "message": "OK"},
            "storage": {"status": "unhealthy", "message": "Storage backend error: Storage error"},
            "redis": {"status": "healthy"},
            "tts": {"status": "healthy", "message": "OK"}
        }
    }
    
    with patch('langflix.api.routes.health.SystemHealthChecker', return_value=mock_checker):
        response = client.get("/health/detailed")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "unhealthy"
        assert "components" in data
        assert data["components"]["storage"]["status"] == "unhealthy"
        assert "Storage error" in data["components"]["storage"]["message"]

def test_database_health_check_endpoint():
    """Test individual database health check endpoint."""
    mock_checker = Mock()
    mock_checker.check_database.return_value = {
        "status": "healthy",
        "message": "Database connection successful"
    }
    
    with patch('langflix.api.routes.health.SystemHealthChecker', return_value=mock_checker):
        response = client.get("/health/database")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "message" in data

def test_storage_health_check_endpoint():
    """Test individual storage health check endpoint."""
    mock_checker = Mock()
    mock_checker.check_storage.return_value = {
        "status": "healthy",
        "message": "Storage backend (LocalStorage) accessible"
    }
    
    with patch('langflix.api.routes.health.SystemHealthChecker', return_value=mock_checker):
        response = client.get("/health/storage")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "message" in data

def test_tts_health_check_endpoint():
    """Test individual TTS health check endpoint."""
    mock_checker = Mock()
    mock_checker.check_tts.return_value = {
        "status": "healthy",
        "message": "TTS service (Gemini) configured"
    }
    
    with patch('langflix.api.routes.health.SystemHealthChecker', return_value=mock_checker):
        response = client.get("/health/tts")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "healthy"
        assert "message" in data
