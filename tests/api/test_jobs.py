"""
Tests for job management endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from langflix.api.main import app

client = TestClient(app)

def test_create_job_mock():
    """Test job creation endpoint with mock data."""
    # Mock file upload data
    files = {
        "video_file": ("test.mp4", b"mock video content", "video/mp4"),
        "subtitle_file": ("test.srt", b"mock subtitle content", "text/plain")
    }
    data = {
        "language_code": "en",
        "show_name": "Suits",
        "episode_name": "S01E01",
        "max_expressions": 10,
        "language_level": "intermediate"
    }
    
    response = client.post("/api/v1/jobs", files=files, data=data)
    assert response.status_code == 200
    
    result = response.json()
    assert "job_id" in result
    assert result["status"] == "PENDING"
    assert result["progress"] == 0
    assert "created_at" in result

def test_get_job_status():
    """Test job status retrieval."""
    job_id = "test-job-id"
    response = client.get(f"/api/v1/jobs/{job_id}")
    assert response.status_code == 200
    
    result = response.json()
    assert result["job_id"] == job_id
    assert result["status"] in ["PENDING", "PROCESSING", "COMPLETED", "FAILED"]
    assert "progress" in result
    assert "created_at" in result

def test_get_job_expressions():
    """Test job expressions retrieval."""
    job_id = "test-job-id"
    response = client.get(f"/api/v1/jobs/{job_id}/expressions")
    assert response.status_code == 200
    
    result = response.json()
    assert result["job_id"] == job_id
    assert "expressions" in result
    assert "total" in result
    assert isinstance(result["expressions"], list)

def test_list_jobs():
    """Test job listing endpoint."""
    response = client.get("/api/v1/jobs")
    assert response.status_code == 200
    
    result = response.json()
    assert isinstance(result, list)

def test_list_jobs_with_filters():
    """Test job listing with filters."""
    response = client.get("/api/v1/jobs?status=PENDING&limit=10&offset=0")
    assert response.status_code == 200
    
    result = response.json()
    assert isinstance(result, list)
