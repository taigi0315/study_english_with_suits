"""
Tests for health check endpoints.
"""

import pytest
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
    assert data["version"] == "1.0.0"

def test_detailed_health_check():
    """Test detailed health check endpoint."""
    response = client.get("/health/detailed")
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "components" in data
    assert data["components"]["database"] == "healthy"
    assert data["components"]["storage"] == "healthy"
    assert data["components"]["llm"] == "healthy"
