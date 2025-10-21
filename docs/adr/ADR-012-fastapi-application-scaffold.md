# ADR-012: FastAPI Application Scaffold

**Date:** 2025-10-21  
**Status:** Draft  
**Deciders:** Development Team  
**Related ADRs:** ADR-009 (Service Architecture Foundation), ADR-011 (Storage Abstraction Layer)

## Context

LangFlix needs a web API to complement the existing CLI functionality, enabling cloud-based video processing and multi-user access. The API should provide asynchronous processing capabilities while maintaining the same core functionality as the CLI.

## Decision

We will create a FastAPI application scaffold that provides RESTful API endpoints for video processing, job management, and result retrieval. The API will use the same core LangFlixPipeline logic as the CLI but with cloud storage and database integration.

## Implementation Plan

### FastAPI Application Structure

#### File Structure
```
langflix/
├── api/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point
│   ├── dependencies.py      # Dependency injection
│   ├── middleware.py        # Custom middleware
│   ├── exceptions.py        # API exception handlers
│   ├── models/
│   │   ├── __init__.py
│   │   ├── requests.py      # Request models
│   │   ├── responses.py     # Response models
│   │   └── common.py        # Common models
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── health.py        # Health check endpoints
│   │   ├── jobs.py          # Job management endpoints
│   │   └── files.py         # File upload/download endpoints
│   └── tasks/
│       ├── __init__.py
│       └── processing.py    # Background task processing
```

### API Endpoints Design

#### Core Endpoints

**Health Check**
```python
GET /health
Response: {"status": "healthy", "timestamp": "2025-10-21T10:00:00Z"}
```

**Job Management**
```python
POST /api/v1/jobs
Request: {
    "video_file": UploadFile,
    "subtitle_file": UploadFile,
    "language_code": "en",
    "show_name": "Suits",
    "episode_name": "S01E01",
    "max_expressions": 10,
    "language_level": "intermediate"
}
Response: {
    "job_id": "uuid",
    "status": "PENDING",
    "created_at": "2025-10-21T10:00:00Z"
}

GET /api/v1/jobs/{job_id}
Response: {
    "job_id": "uuid",
    "status": "PROCESSING|COMPLETED|FAILED",
    "progress": 75,
    "created_at": "2025-10-21T10:00:00Z",
    "started_at": "2025-10-21T10:01:00Z",
    "completed_at": "2025-10-21T10:05:00Z",
    "error_message": null
}

GET /api/v1/jobs/{job_id}/expressions
Response: {
    "job_id": "uuid",
    "expressions": [
        {
            "id": "uuid",
            "expression": "get the ball rolling",
            "translation": "일을 시작하다",
            "dialogue": "Let's get the ball rolling on this project",
            "dialogue_translation": "이 프로젝트를 시작해보자",
            "similar_expressions": ["start working", "begin"],
            "context_start_time": "00:01:23,456",
            "context_end_time": "00:01:25,789",
            "scene_type": "dialogue"
        }
    ],
    "total": 1
}
```

### Request/Response Models

#### Request Models

**`langflix/api/models/requests.py`**
```python
from pydantic import BaseModel, Field
from typing import Optional, Literal
from fastapi import UploadFile

class JobCreateRequest(BaseModel):
    """Request model for creating a new processing job."""
    language_code: str = Field(..., description="Language code (e.g., 'en', 'ko')")
    show_name: str = Field(..., description="Name of the TV show")
    episode_name: str = Field(..., description="Name of the episode")
    max_expressions: Optional[int] = Field(10, description="Maximum number of expressions to extract")
    language_level: Optional[Literal["beginner", "intermediate", "advanced", "mixed"]] = Field(
        "intermediate", description="Target language proficiency level"
    )
    test_mode: bool = Field(False, description="Enable test mode (process only first chunk)")
    no_shorts: bool = Field(False, description="Skip short video generation")

class FileUploadRequest(BaseModel):
    """Request model for file uploads."""
    video_file: UploadFile
    subtitle_file: UploadFile
    job_config: JobCreateRequest
```

#### Response Models

**`langflix/api/models/responses.py`**
```python
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import datetime

class JobStatusResponse(BaseModel):
    """Response model for job status."""
    job_id: str = Field(..., description="Unique job identifier")
    status: Literal["PENDING", "PROCESSING", "COMPLETED", "FAILED"] = Field(
        ..., description="Current job status"
    )
    progress: int = Field(..., description="Progress percentage (0-100)")
    created_at: datetime = Field(..., description="Job creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Processing start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Processing completion timestamp")
    error_message: Optional[str] = Field(None, description="Error message if failed")

class ExpressionResponse(BaseModel):
    """Response model for individual expressions."""
    id: str = Field(..., description="Expression identifier")
    expression: str = Field(..., description="The expression text")
    translation: str = Field(..., description="Translation of the expression")
    dialogue: str = Field(..., description="Full dialogue containing the expression")
    dialogue_translation: str = Field(..., description="Translation of the dialogue")
    similar_expressions: List[str] = Field(..., description="List of similar expressions")
    context_start_time: str = Field(..., description="Start time in subtitle format")
    context_end_time: str = Field(..., description="End time in subtitle format")
    scene_type: str = Field(..., description="Type of scene (e.g., 'dialogue', 'action')")

class JobExpressionsResponse(BaseModel):
    """Response model for job expressions."""
    job_id: str = Field(..., description="Job identifier")
    expressions: List[ExpressionResponse] = Field(..., description="List of expressions")
    total: int = Field(..., description="Total number of expressions")

class ErrorResponse(BaseModel):
    """Response model for errors."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[dict] = Field(None, description="Additional error details")
```

### FastAPI Application Setup

#### Main Application

**`langflix/api/main.py`**
```python
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from .routes import health, jobs, files
from .exceptions import APIException, api_exception_handler
from .middleware import LoggingMiddleware

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="LangFlix API",
        description="Language learning video processing API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add custom middleware
    app.add_middleware(LoggingMiddleware)
    
    # Include routers
    app.include_router(health.router, tags=["health"])
    app.include_router(jobs.router, prefix="/api/v1", tags=["jobs"])
    app.include_router(files.router, prefix="/api/v1", tags=["files"])
    
    # Add exception handlers
    app.add_exception_handler(APIException, api_exception_handler)
    app.add_exception_handler(HTTPException, api_exception_handler)
    
    return app

# Create app instance
app = create_app()

@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info("LangFlix API starting up...")
    # Initialize database connection
    # Initialize storage backends
    logger.info("LangFlix API started successfully")

@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info("LangFlix API shutting down...")
    # Cleanup resources
    logger.info("LangFlix API shutdown complete")
```

#### Health Check Routes

**`langflix/api/routes/health.py`**
```python
from fastapi import APIRouter, Depends
from datetime import datetime
from ..models.responses import JobStatusResponse

router = APIRouter()

@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "LangFlix API",
        "version": "1.0.0"
    }

@router.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with component status."""
    # Check database connection
    # Check storage backends
    # Check external services
    
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "components": {
            "database": "healthy",
            "storage": "healthy",
            "llm": "healthy"
        }
    }
```

#### Job Management Routes

**`langflix/api/routes/jobs.py`**
```python
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from typing import List
from uuid import UUID

from ..models.requests import JobCreateRequest, FileUploadRequest
from ..models.responses import JobStatusResponse, JobExpressionsResponse
from ..dependencies import get_db, get_storage
from ..tasks.processing import process_video_task

router = APIRouter()

@router.post("/jobs", response_model=JobStatusResponse)
async def create_job(
    request: FileUploadRequest,
    background_tasks: BackgroundTasks,
    db = Depends(get_db),
    storage = Depends(get_storage)
):
    """Create a new video processing job."""
    try:
        # Validate files
        if not request.video_file.filename.endswith(('.mp4', '.mkv', '.avi')):
            raise HTTPException(status_code=400, detail="Invalid video file format")
        
        if not request.subtitle_file.filename.endswith(('.srt', '.vtt')):
            raise HTTPException(status_code=400, detail="Invalid subtitle file format")
        
        # Create job record in database
        job = await create_job_record(db, request.job_config)
        
        # Start background processing
        background_tasks.add_task(
            process_video_task,
            job_id=str(job.id),
            video_file=request.video_file,
            subtitle_file=request.subtitle_file,
            config=request.job_config.dict()
        )
        
        return JobStatusResponse(
            job_id=str(job.id),
            status="PENDING",
            progress=0,
            created_at=job.created_at
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create job: {str(e)}")

@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: UUID, db = Depends(get_db)):
    """Get job status by ID."""
    job = await get_job_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return JobStatusResponse(
        job_id=str(job.id),
        status=job.status,
        progress=job.progress,
        created_at=job.created_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        error_message=job.error_message
    )

@router.get("/jobs/{job_id}/expressions", response_model=JobExpressionsResponse)
async def get_job_expressions(job_id: UUID, db = Depends(get_db)):
    """Get expressions for a completed job."""
    job = await get_job_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != "COMPLETED":
        raise HTTPException(status_code=400, detail="Job not completed yet")
    
    expressions = await get_expressions_by_job(db, job_id)
    
    return JobExpressionsResponse(
        job_id=str(job_id),
        expressions=expressions,
        total=len(expressions)
    )

@router.get("/jobs", response_model=List[JobStatusResponse])
async def list_jobs(
    status: str = None,
    limit: int = 50,
    offset: int = 0,
    db = Depends(get_db)
):
    """List jobs with optional filtering."""
    jobs = await list_jobs_from_db(db, status, limit, offset)
    return [
        JobStatusResponse(
            job_id=str(job.id),
            status=job.status,
            progress=job.progress,
            created_at=job.created_at,
            started_at=job.started_at,
            completed_at=job.completed_at,
            error_message=job.error_message
        )
        for job in jobs
    ]
```

### Error Handling

#### Custom Exceptions

**`langflix/api/exceptions.py`**
```python
from fastapi import HTTPException
from typing import Optional, Dict, Any

class APIException(Exception):
    """Base API exception."""
    def __init__(self, message: str, status_code: int = 500, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

class ValidationError(APIException):
    """Validation error."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 400, details)

class NotFoundError(APIException):
    """Resource not found error."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 404, details)

class ProcessingError(APIException):
    """Video processing error."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 422, details)

class StorageError(APIException):
    """Storage operation error."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, 500, details)
```

#### Exception Handlers

**`langflix/api/exceptions.py` (continued)**
```python
from fastapi import Request
from fastapi.responses import JSONResponse
from .models.responses import ErrorResponse

async def api_exception_handler(request: Request, exc: APIException):
    """Handle custom API exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.__class__.__name__,
            message=exc.message,
            details=exc.details
        ).dict()
    )

async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error="HTTPException",
            message=exc.detail,
            details={"status_code": exc.status_code}
        ).dict()
    )

async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="InternalServerError",
            message="An internal server error occurred",
            details={"exception": str(exc)}
        ).dict()
    )
```

### Dependencies

#### Dependency Injection

**`langflix/api/dependencies.py`**
```python
from fastapi import Depends
from sqlalchemy.orm import Session
from langflix.db import db_manager
from langflix.storage import create_storage_backend

def get_db() -> Session:
    """Get database session."""
    db = db_manager.get_session()
    try:
        yield db
    finally:
        db.close()

def get_storage():
    """Get storage backend."""
    return create_storage_backend()

def get_current_user():
    """Get current user (placeholder for Phase 2)."""
    # TODO: Implement authentication in Phase 2
    return {"user_id": "anonymous", "role": "user"}
```

### Middleware

#### Logging Middleware

**`langflix/api/middleware.py`**
```python
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time
import logging

logger = logging.getLogger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    """Logging middleware for API requests."""
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Log request
        logger.info(f"Request: {request.method} {request.url}")
        
        # Process request
        response = await call_next(request)
        
        # Log response
        process_time = time.time() - start_time
        logger.info(f"Response: {response.status_code} in {process_time:.3f}s")
        
        return response
```

### Configuration Updates

#### Requirements

**`requirements.txt` additions:**
```txt
# API dependencies
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
python-multipart>=0.0.6
```

#### API Configuration

**`langflix/config/default.yaml` additions:**
```yaml
# API Configuration
api:
  host: "0.0.0.0"
  port: 8000
  workers: 1
  reload: false  # Set to true for development
  log_level: "info"
  cors_origins: ["*"]  # Configure appropriately for production
```

### Testing Strategy

#### Unit Tests

**`tests/unit/test_api_models.py`**
```python
import pytest
from langflix.api.models.requests import JobCreateRequest
from langflix.api.models.responses import JobStatusResponse

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
    assert request.max_expressions == 10

def test_job_status_response():
    """Test JobStatusResponse model."""
    response = JobStatusResponse(
        job_id="test-uuid",
        status="PENDING",
        progress=0,
        created_at="2025-10-21T10:00:00Z"
    )
    assert response.status == "PENDING"
    assert response.progress == 0
```

#### Integration Tests

**`tests/integration/test_api_endpoints.py`**
```python
import pytest
from fastapi.testclient import TestClient
from langflix.api.main import app

client = TestClient(app)

def test_health_check():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_create_job():
    """Test job creation endpoint."""
    # Test with mock files
    files = {
        "video_file": ("test.mp4", b"mock video content", "video/mp4"),
        "subtitle_file": ("test.srt", b"mock subtitle content", "text/plain")
    }
    data = {
        "language_code": "en",
        "show_name": "Suits",
        "episode_name": "S01E01"
    }
    
    response = client.post("/api/v1/jobs", files=files, data=data)
    assert response.status_code == 200
    assert "job_id" in response.json()
```

## Success Criteria

### Phase 1c Complete When:
- [ ] FastAPI application running on port 8000
- [ ] Health check endpoint functional
- [ ] Job creation endpoint working (with mock processing)
- [ ] Job status endpoint returning real data
- [ ] API documentation accessible at `/docs`
- [ ] All request/response models validated
- [ ] Error handling working correctly
- [ ] All tests passing (CLI + API)

## Consequences

### Positive
- **RESTful API**: Standard HTTP interface for video processing
- **Async Processing**: Background task support for long-running operations
- **Documentation**: Auto-generated API docs with OpenAPI/Swagger
- **Scalability**: Foundation for multi-user web service
- **Integration**: Easy integration with frontend applications

### Negative
- **Complexity**: Additional API layer on top of CLI
- **Dependencies**: FastAPI and related packages
- **Maintenance**: API versioning and backward compatibility
- **Security**: Authentication and authorization (Phase 2)

### Risks and Mitigations

**Risk: API Performance Issues**
- Mitigation: Background processing, async operations, proper error handling

**Risk: API Security Vulnerabilities**
- Mitigation: Input validation, rate limiting (Phase 2), authentication (Phase 2)

**Risk: API Versioning Complexity**
- Mitigation: Clear versioning strategy, backward compatibility planning

## References

- [ADR-009: Service Architecture Foundation](ADR-009-service-architecture-foundation.md)
- [ADR-011: Storage Abstraction Layer](ADR-011-storage-abstraction-layer.md)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [OpenAPI Specification](https://swagger.io/specification/)

## Next Steps

1. Get this ADR approved
2. Set up FastAPI application structure
3. Implement request/response models
4. Create API endpoints
5. Add error handling and middleware
6. Set up API documentation
7. Add comprehensive tests
