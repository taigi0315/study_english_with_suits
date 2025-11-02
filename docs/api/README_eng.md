# LangFlix API Module Documentation (ENG)

Last updated: 2025-10-30

## Overview
The `langflix/api` package provides the FastAPI-based HTTP interface for LangFlix. It exposes health endpoints, job management for video processing, and file listing utilities. It wires middleware, exception handling, and static mounts, and integrates with Redis-backed job storage.

## Folder Structure
- `main.py`: FastAPI app factory, router registration, lifespan management, middleware, static mounts.
- `dependencies.py`: Placeholders for DI providers (DB session, storage backend).
- `exceptions.py`: API-specific exception types and a unified exception handler.
- `middleware.py`: Request logging middleware with processing time header.
- `models/`
  - `common.py`: Common response models (health, error).
  - `requests.py`: Request DTOs (job creation, file upload metadata).
  - `responses.py`: Response DTOs (job status, expressions).
- `routes/`
  - `health.py`: Service/Redis health endpoints and cleanup.
  - `files.py`: Output file listing and stubs for detail/delete.
  - `jobs.py`: Endpoints to create jobs, query job status/expressions, list jobs.
- `tasks/processing.py`: (present but not used directly here; job processing is defined in `routes/jobs.py`).

## Application Lifecycle and Configuration
- `create_app()` in `main.py` initializes FastAPI with:
  - CORS allowing all origins (adjust for production).
  - `LoggingMiddleware` for request/response logs and `X-Process-Time` header.
  - Static mount `/output` when local `output/` exists.
  - Routers: `health`, `jobs` (prefixed `/api/v1`), `files` (prefixed `/api/v1`).
  - Exception handlers for `APIException` and `HTTPException`.
- Lifespan startup:
  - Initializes database connection pool if enabled (`settings.get_database_enabled()`)
  - Performs Redis job store cleanup and health check via `langflix.core.redis_client.get_redis_job_manager()`
- Lifespan shutdown:
  - Closes database connections gracefully if database was enabled

## Dependency Injection

### Database Dependency (`get_db()`)
- Provides SQLAlchemy database sessions via FastAPI dependency injection
- Uses `DatabaseManager` from `langflix.db.session` for connection pooling
- Automatically handles session lifecycle:
  - Yields database session to endpoint handler
  - Commits on successful completion
  - Rolls back on exceptions
  - Closes session in `finally` block
- Returns `None` if database is disabled (file-only mode) - checked via `settings.get_database_enabled()`
- Database initialization happens in application lifespan (see below)

**Usage:**
```python
from fastapi import Depends
from langflix.api.dependencies import get_db
from sqlalchemy.orm import Session

@router.get("/endpoint")
async def my_endpoint(db: Session = Depends(get_db)):
    if db is None:
        # Database disabled, handle accordingly
        return {"message": "Database not available"}
    # Use db session...
```

### Storage Dependency (`get_storage()`)
- Provides storage backend instances via FastAPI dependency injection
- Uses `create_storage_backend()` factory from `langflix.storage.factory`
- Returns configured storage backend (Local or GCS) based on settings
- Creates a new instance per request (lightweight operation)

**Usage:**
```python
from fastapi import Depends
from langflix.api.dependencies import get_storage
from langflix.storage.base import StorageBackend

@router.get("/endpoint")
async def my_endpoint(storage: StorageBackend = Depends(get_storage)):
    files = storage.list_files("/path")
    # Use storage backend...
```

## Exceptions
- `APIException` base and specializations: `ValidationError`, `NotFoundError`, `ProcessingError`, `StorageError`.
- `api_exception_handler` converts both `APIException` and `HTTPException` into structured JSON error responses (see `models.common.ErrorResponse`).

## Middleware
- `LoggingMiddleware` logs method, URL, status code, and elapsed time; injects `X-Process-Time` response header.

## Data Models
- Requests:
  - `JobCreateRequest`: language, show/episode, `max_expressions`, `language_level`, `test_mode`, `no_shorts`.
  - `FileUploadRequest`: filename, content_type, size.
- Responses:
  - `JobStatusResponse`: id, status, timestamps, progress, error.
  - `ExpressionResponse`: expression, translation, context, similar expressions.
  - `JobExpressionsResponse`: job id, status, expressions.
  - `HealthResponse`, `DetailedHealthResponse`, `ErrorResponse` (from `common.py`).

## Endpoints
- `/` (GET): API root meta.
- `/local/status` (GET): Local dev info.
- `/health` (GET): Basic health.
- `/health/detailed` (GET): Includes version and actual component health checks:
  - Database: Checks connectivity with `SELECT 1` query (returns "connected", "disabled", or error message)
  - Storage: Checks availability by attempting to list files (returns "available" or error message)
  - TTS: Always returns "ready"
- `/health/redis` (GET): Redis health via job manager.
- `/health/redis/cleanup` (POST): Cleanup expired/stale jobs.
- `/api/v1/files` (GET): List files under `output/` recursively.
- `/api/v1/files/{file_id}` (GET): Stub for file details (TODO).
- `/api/v1/files/{file_id}` (DELETE): Stub for deletion (TODO).
- `/api/v1/jobs` (POST): Create a new job with `UploadFile` video+subtitle and form fields; starts background processing.
- `/api/v1/jobs/{job_id}` (GET): Fetch current job state from Redis.
- `/api/v1/jobs/{job_id}/expressions` (GET): Returns expressions from Redis (same source as job status).
  - **TICKET-003 Fix:** Fixed undefined `jobs_db` variable - now correctly uses Redis via `get_redis_job_manager()`
- `/api/v1/jobs` (GET): List all jobs from Redis.

## Job Processing (Background Task)

### Unified Pipeline Service (TICKET-001)

The API uses `VideoPipelineService` (`langflix/services/video_pipeline_service.py`) which provides a unified interface for both API and CLI processing. This eliminates code duplication and ensures consistent behavior.

**Key Features:**
- Single source of truth for video processing pipeline
- Progress callback support for real-time job status updates
- Consistent result format across API and CLI

**Implementation:**
- Defined in `routes/jobs.py` as `process_video_task(...)` (simplified from 450+ lines to ~110 lines)
- Uses `VideoPipelineService.process_video()` which wraps `LangFlixPipeline`
- **Temporary File Management (TICKET-002):**
  - Uses `TempFileManager` for temporary file handling (see `langflix/utils/temp_file_manager.py`)
  - Temporary files are automatically cleaned up when context exits, even on exceptions
  - No hardcoded `/tmp` paths - uses system temp directory via `tempfile` module
  - Context managers ensure cleanup even if processing fails
  - Global singleton instance manages all temporary files across the application
- Updates Redis job status/results via callback; invalidates video cache

**Progress Tracking:**
- Progress callbacks automatically update Redis job status
- Progress milestones: 10% (init), 20% (saving files), 30% (parsing), 50% (processing), 70% (educational videos), 80% (short videos), 100% (complete)

**Related Documentation:**
- [Services Module Documentation](../services/README_eng.md) - VideoPipelineService details
- [Utils Module Documentation](../utils/temp_file_manager_eng.md) - TempFileManager usage

## Error Handling and Logging

### Error Handler Integration (TICKET-005)

The API now uses the centralized error handler (`langflix/core/error_handler.py`) for structured error reporting:

**Key Features:**
- **Structured Error Reports**: All errors are captured with context (operation, component, metadata)
- **Error Categories**: Errors are automatically categorized (NETWORK, PROCESSING, VALIDATION, RESOURCE, SYSTEM)
- **Error Severity**: Errors are classified by severity (LOW, MEDIUM, HIGH, CRITICAL)
- **Error Tracking**: Error reports are stored and can be queried for statistics

**Integration Points:**
- `process_video_task()` in `routes/jobs.py` reports errors with job context
- Error context includes: `job_id`, `video_filename`, `subtitle_filename`
- Errors are logged via the error handler before updating Redis job status

**Usage Example:**
```python
from langflix.core.error_handler import handle_error, ErrorContext

try:
    # Processing logic
    pass
except Exception as e:
    error_context = ErrorContext(
        operation="process_video_task",
        component="api.routes.jobs",
        additional_data={"job_id": job_id}
    )
    handle_error(e, error_context, retry=False, fallback=False)
    # Continue with error handling...
```

**Benefits:**
- Consistent error reporting across all modules
- Better debugging with structured error information
- Foundation for error monitoring and alerting (future enhancement)

- Centralized exception handler returns consistent JSON payloads.
- Extensive `logger.info/warning/error` statements track pipeline steps and failures.

## Security and Operational Notes
- CORS is wide-open (`*`) by default; restrict per environment.
- File operations target local filesystem; ensure appropriate container paths/permissions in production.
- Validate upload sizes/types further if needed.
- Redis availability is assumed; startup logs on failure but app remains up—consider fail-fast or degraded mode indicator.

## Extensibility
- ✅ `dependencies.get_db/get_storage` implemented - Database and storage integration complete (TICKET-010)
- Replace stubbed file detail/delete with actual storage-backed operations.
- ✅ `/jobs/{id}/expressions` aligned with Redis (source of truth) - `jobs_db` dependency removed (TICKET-003).

## Usage Example
```bash
uvicorn langflix.api.main:app --reload
# Visit /docs for Swagger UI
```
