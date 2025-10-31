"""
Tests for job management endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
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

@patch('langflix.api.routes.jobs.get_redis_job_manager')
def test_get_job_expressions_completed(mock_get_manager):
    """Test job expressions retrieval for completed job."""
    mock_manager = MagicMock()
    mock_get_manager.return_value = mock_manager
    
    job_id = "test-job-id"
    mock_job = {
        "job_id": job_id,
        "status": "COMPLETED",
        "expressions": [
            {"expression": "test expression", "translation": "테스트 표현"}
        ],
        "completed_at": datetime.now(timezone.utc).isoformat()
    }
    mock_manager.get_job.return_value = mock_job
    
    response = client.get(f"/api/v1/jobs/{job_id}/expressions")
    assert response.status_code == 200
    
    result = response.json()
    assert result["job_id"] == job_id
    assert result["status"] == "COMPLETED"
    assert "expressions" in result
    assert "total_expressions" in result
    assert isinstance(result["expressions"], list)
    assert len(result["expressions"]) == 1
    assert result["total_expressions"] == 1
    assert "completed_at" in result
    mock_manager.get_job.assert_called_once_with(job_id)

@patch('langflix.api.routes.jobs.get_redis_job_manager')
def test_get_job_expressions_not_completed(mock_get_manager):
    """Test job expressions retrieval for job that's not completed yet."""
    mock_manager = MagicMock()
    mock_get_manager.return_value = mock_manager
    
    job_id = "test-job-id"
    mock_job = {
        "job_id": job_id,
        "status": "PROCESSING",
        "progress": 50
    }
    mock_manager.get_job.return_value = mock_job
    
    response = client.get(f"/api/v1/jobs/{job_id}/expressions")
    assert response.status_code == 200
    
    result = response.json()
    assert result["job_id"] == job_id
    assert result["status"] == "PROCESSING"
    assert "expressions" in result
    assert result["expressions"] == []
    assert "message" in result
    assert "Processing not completed yet" in result["message"]
    mock_manager.get_job.assert_called_once_with(job_id)

@patch('langflix.api.routes.jobs.get_redis_job_manager')
def test_get_job_expressions_not_found(mock_get_manager):
    """Test job expressions retrieval when job doesn't exist."""
    mock_manager = MagicMock()
    mock_get_manager.return_value = mock_manager
    
    job_id = "non-existent-job-id"
    mock_manager.get_job.return_value = None
    
    response = client.get(f"/api/v1/jobs/{job_id}/expressions")
    assert response.status_code == 404
    
    result = response.json()
    # FastAPI HTTPException returns error in 'detail' field
    assert "detail" in result or "error" in result
    error_message = result.get("detail") or result.get("error", "")
    assert "Job not found" in error_message
    mock_manager.get_job.assert_called_once_with(job_id)

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
