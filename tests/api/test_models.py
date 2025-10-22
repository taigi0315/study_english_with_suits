"""
Tests for API models.
"""

import pytest
from datetime import datetime, timezone
from langflix.api.models.requests import JobCreateRequest
from langflix.api.models.responses import JobStatusResponse, ExpressionResponse, JobExpressionsResponse
from langflix.api.models.common import HealthResponse

def test_job_create_request():
    """Test JobCreateRequest model validation."""
    request = JobCreateRequest(
        language_code="en",
        show_name="Suits",
        episode_name="S01E01",
        max_expressions=10,
        language_level="intermediate"
    )
    assert request.language_code == "en"
    assert request.show_name == "Suits"
    assert request.episode_name == "S01E01"
    assert request.max_expressions == 10
    assert request.language_level == "intermediate"
    assert request.test_mode is False
    assert request.no_shorts is False

def test_job_create_request_defaults():
    """Test JobCreateRequest with default values."""
    request = JobCreateRequest(
        language_code="ko",
        show_name="Test Show",
        episode_name="S01E01"
    )
    assert request.language_code == "ko"
    assert request.max_expressions == 10
    assert request.language_level == "intermediate"
    assert request.test_mode is False
    assert request.no_shorts is False

def test_job_status_response():
    """Test JobStatusResponse model."""
    response = JobStatusResponse(
        job_id="test-uuid",
        status="PENDING",
        progress=0,
        created_at=datetime.now(timezone.utc)
    )
    assert response.job_id == "test-uuid"
    assert response.status == "PENDING"
    assert response.progress == 0
    assert response.started_at is None
    assert response.completed_at is None
    assert response.error_message is None

def test_expression_response():
    """Test ExpressionResponse model."""
    expression = ExpressionResponse(
        id="expr-1",
        expression="get the ball rolling",
        translation="일을 시작하다",
        dialogue="Let's get the ball rolling on this project",
        dialogue_translation="이 프로젝트를 시작해보자",
        similar_expressions=["start working", "begin"],
        context_start_time="00:01:23,456",
        context_end_time="00:01:25,789",
        scene_type="dialogue"
    )
    assert expression.id == "expr-1"
    assert expression.expression == "get the ball rolling"
    assert expression.translation == "일을 시작하다"
    assert len(expression.similar_expressions) == 2

def test_job_expressions_response():
    """Test JobExpressionsResponse model."""
    expressions = [
        ExpressionResponse(
            id="expr-1",
            expression="test expression",
            translation="테스트 표현",
            dialogue="test dialogue",
            dialogue_translation="테스트 대화",
            similar_expressions=["similar1"],
            context_start_time="00:01:00,000",
            context_end_time="00:01:05,000",
            scene_type="dialogue"
        )
    ]
    
    response = JobExpressionsResponse(
        job_id="job-1",
        expressions=expressions,
        total=1
    )
    assert response.job_id == "job-1"
    assert len(response.expressions) == 1
    assert response.total == 1

def test_health_response():
    """Test HealthResponse model."""
    response = HealthResponse(
        status="healthy",
        timestamp="2025-10-21T10:00:00Z",
        service="LangFlix API",
        version="1.0.0"
    )
    assert response.status == "healthy"
    assert response.timestamp == "2025-10-21T10:00:00Z"
    assert response.service == "LangFlix API"
    assert response.version == "1.0.0"
