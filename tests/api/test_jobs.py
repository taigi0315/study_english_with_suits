"""
Tests for job management endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
from langflix.api.main import app

client = TestClient(app)

@patch('langflix.api.routes.jobs.get_redis_job_manager')
def test_create_job_mock(mock_get_manager):
    """Test job creation endpoint with mock data."""
    mock_manager = MagicMock()
    mock_get_manager.return_value = mock_manager
    mock_manager.create_job.return_value = True
    
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
    assert "message" in result
    assert result["message"] == "Job created successfully"
    assert "video_size_mb" in result
    assert "subtitle_size_kb" in result
    # Verify Redis create_job was called
    mock_manager.create_job.assert_called_once()

@patch('langflix.api.routes.jobs.get_redis_job_manager')
def test_get_job_status(mock_get_manager):
    """Test job status retrieval."""
    mock_manager = MagicMock()
    mock_get_manager.return_value = mock_manager
    
    job_id = "test-job-id"
    mock_job = {
        "job_id": job_id,
        "status": "PROCESSING",
        "progress": 50,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "current_step": "Processing video..."
    }
    mock_manager.get_job.return_value = mock_job
    
    response = client.get(f"/api/v1/jobs/{job_id}")
    assert response.status_code == 200
    
    result = response.json()
    assert result["job_id"] == job_id
    assert result["status"] == "PROCESSING"
    assert "progress" in result
    assert result["progress"] == 50
    assert "created_at" in result
    mock_manager.get_job.assert_called_once_with(job_id)

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

@patch('langflix.api.routes.jobs.get_redis_job_manager')
def test_list_jobs(mock_get_manager):
    """Test job listing endpoint."""
    mock_manager = MagicMock()
    mock_get_manager.return_value = mock_manager
    
    # Mock jobs
    mock_jobs = {
        "job1": {
            "job_id": "job1",
            "status": "COMPLETED",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        "job2": {
            "job_id": "job2",
            "status": "PENDING",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    }
    mock_manager.get_all_jobs.return_value = mock_jobs
    
    response = client.get("/api/v1/jobs")
    assert response.status_code == 200
    
    result = response.json()
    assert isinstance(result, dict)
    assert "jobs" in result
    assert "total" in result
    assert isinstance(result["jobs"], list)
    assert result["total"] == 2
    assert len(result["jobs"]) == 2
    mock_manager.get_all_jobs.assert_called_once()

@patch('langflix.api.routes.jobs.get_redis_job_manager')
def test_list_jobs_with_filters(mock_get_manager):
    """Test job listing endpoint (filters are currently ignored, but endpoint works)."""
    mock_manager = MagicMock()
    mock_get_manager.return_value = mock_manager
    
    # Mock jobs - note: filters are not currently implemented, so all jobs are returned
    mock_jobs = {
        "job1": {
            "job_id": "job1",
            "status": "COMPLETED",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    }
    mock_manager.get_all_jobs.return_value = mock_jobs
    
    response = client.get("/api/v1/jobs?status=PENDING&limit=10&offset=0")
    assert response.status_code == 200
    
    result = response.json()
    assert isinstance(result, dict)
    assert "jobs" in result
    assert "total" in result
    assert isinstance(result["jobs"], list)
    # Note: Filters are not implemented yet, so all jobs are returned
    mock_manager.get_all_jobs.assert_called_once()
