# LangFlix API Module Documentation (ENG)

Last updated: 2025-11-13

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
  - `files.py`: Storage-backed file inventory, metadata lookup, protected deletion.
  - `jobs.py`: Endpoints to create jobs, query job status/expressions, list jobs.
  - `batch.py`: Endpoints for batch video processing (create batch, get batch status).
  - `tasks/processing.py`: (present but not used directly here; job processing is defined in `routes/jobs.py`).

## Application Lifecycle and Configuration
- `create_app()` in `main.py` initializes FastAPI with:
  - CORS allowing all origins (adjust for production).
  - `LoggingMiddleware` for request/response logs and `X-Process-Time` header.
  - Static mount `/output` when local `output/` exists.
  - Routers: `health`, `jobs` (prefixed `/api/v1`), `files` (prefixed `/api/v1`), `batch` (prefixed `/api/v1`).
  - Exception handlers for `APIException` and `HTTPException`.
- Lifespan startup:
  - Initializes database connection pool if enabled (`settings.get_database_enabled()`)
  - Performs Redis job store cleanup and health check via `langflix.core.redis_client.get_redis_job_manager()`
  - Starts `QueueProcessor` background task for sequential batch job processing
- Lifespan shutdown:
  - Stops `QueueProcessor` gracefully (requeues current job if processing)
  - Closes database connections gracefully if database was enabled
- `LANGFLIX_API_BASE_URL` environment variable controls how the Flask web UI talks to the FastAPI backend.
  - If set, the value (minus trailing slash) is used verbatim.
  - If not set, the UI automatically selects `http://localhost:8000` for local development.
  - Inside Docker/Container environments (`LANGFLIX_RUNNING_IN_DOCKER=1` or automatic detection), it defaults to `http://langflix-api:8000`.
  - This dual fallback lets the same build work in both local and Compose-based deployments without manual tweaks.

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
- `/health` (GET): Basic health check endpoint. Returns service status and timestamp.
- `/health/detailed` (GET): Comprehensive health check with actual component status verification:
  - Uses `SystemHealthChecker` from `langflix.monitoring.health_checker` to check all system components
  - Database: Checks connectivity with `SELECT 1` query using `db_manager.session()` context manager
    - Returns `{"status": "healthy", "message": "..."}` or `{"status": "disabled", "message": "..."}` or `{"status": "unhealthy", "message": "..."}`
  - Storage: Checks backend availability by attempting to list files (lightweight operation)
    - Returns `{"status": "healthy", "message": "..."}` or `{"status": "unhealthy", "message": "..."}`
  - Redis: Checks Redis connectivity via job manager
    - Returns full health dict from `RedisJobManager.health_check()`
  - TTS: Checks TTS service configuration (API key presence for Gemini or LemonFox)
    - Returns `{"status": "healthy", "message": "..."}` or `{"status": "unhealthy", "message": "..."}` or `{"status": "unknown", "message": "..."}`
  - Overall status: Determined from component statuses (`healthy`, `degraded`, or `unhealthy`)
- `/health/database` (GET): Individual database health check endpoint.
- `/health/storage` (GET): Individual storage health check endpoint.
- `/health/tts` (GET): Individual TTS service health check endpoint.
- `/health/redis` (GET): Redis health via job manager.
- `/health/redis/cleanup` (POST): Cleanup expired/stale jobs.
- `/api/v1/files` (GET): Enumerate files via the configured storage backend (Local or GCS), returning metadata (`size`, `mime`, timestamps, public URL).
- `/api/v1/files/{file_id}` (GET): Fetch normalized metadata for a specific file; rejects traversal attempts and directory requests.
- `/api/v1/files/{file_id}` (DELETE): Remove a file through the storage backend while protecting sensitive assets (`config.yaml`, `.env`, `*.log`, etc.).
- `/api/v1/jobs` (POST): Create a new job with `UploadFile` video+subtitle and form fields; starts background processing.
- `/api/v1/jobs/{job_id}` (GET): Fetch current job state from Redis.
- `/api/v1/jobs/{job_id}/expressions` (GET): Returns expressions from Redis (same source as job status).
  - **TICKET-003 Fix:** Fixed undefined `jobs_db` variable - now correctly uses Redis via `get_redis_job_manager()`
- `/api/v1/jobs` (GET): List all jobs from Redis.
- `/api/v1/batch` (POST): Create a batch of video processing jobs (TICKET-014).
  - Request body: `{"videos": [...], "language_code": "ko", "language_level": "intermediate", ...}`
  - Returns: `{"batch_id": "uuid", "total_jobs": N, "jobs": [...], "status": "PENDING"}`
  - Jobs are queued for sequential processing by `QueueProcessor`
  - Maximum batch size: 50 videos (enforced)
- `/api/v1/batch/{batch_id}` (GET): Get batch status with individual job progress (TICKET-014).
  - Returns: Batch info with overall status, individual job statuses, progress metrics
  - Status values: `PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`, `PARTIALLY_FAILED`
  - Automatically recalculates and updates batch status based on job statuses

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

## File Management Endpoints

### Storage-backed design
- All file operations receive a `StorageBackend` via `Depends(get_storage)` ensuring parity between Local filesystem and Google Cloud Storage.
- Paths are normalized with `PurePosixPath`, block traversal (`..`) and absolute references, and unify separators.
- Metadata helpers supply size, MIME type, created/modified timestamps, and shareable URLs. Local backends read filesystem stats, while GCS reloads blob metadata on demand.

### Listing files
- `GET /api/v1/files` iterates `storage.list_files("")`, normalizes each entry, resolves metadata, and filters out directories.
- Response payload:
  ```json
  {
    "files": [
      {
        "file_id": "short_form_videos/expressions/expression_hi.mkv",
        "name": "expression_hi.mkv",
        "path": "short_form_videos/expressions/expression_hi.mkv",
        "url": "...",
        "size": 1234567,
        "type": "video/x-matroska",
        "modified": 1731492801.123,
        "created": 1731492000.456,
        "is_directory": false
      }
    ],
    "total": 1
  }
  ```
  - `modified`/`created` are UNIX timestamps (seconds) for consistency with prior UI expectations.
  - `url` is an absolute filesystem path for LocalStorage or public URL for GCS.

### File details
- `GET /api/v1/files/{file_id:path}` validates the identifier, checks existence via `storage.file_exists`, collects metadata, and rejects directory requests.
- Returns `404` for missing assets, `400` for directories, and `400` if traversal is detected.
- Errors are logged with context and wrapped into FastAPI `HTTPException` responses.

### File deletion
- `DELETE /api/v1/files/{file_id:path}` performs:
  1. Path normalization and existence check.
  2. Metadata lookup to block directory deletions.
  3. Protection filter (`config.yaml`, `.env`, `*.log`, `langflix.log`, `requirements.txt`) using `fnmatch`.
  4. `storage.delete_file` invocation with boolean success check.
- Returns `{ "message": "...", "file_id": "...", "deleted": true }` on success.
- Responds with `403` for protected files, `400` for directories, `404` for missing files, and `500` for storage-layer failures.

### Testing
- API coverage lives in `tests/api/test_files_routes.py`:
  - Dependency overrides inject `LocalStorage` backed by pytest `tmp_path`.
  - Verifies listing metadata, MIME detection, path validation, deletion flows, and protection rules.
  - Uses helper writers to construct isolated fixtures without polluting real output directories.

## Extensibility
- ✅ `dependencies.get_db/get_storage` implemented - Database and storage integration complete (TICKET-010)
- ✅ Storage-backed file detail/delete endpoints (TICKET-028) with security checks and metadata introspection.
- ✅ `/jobs/{id}/expressions` aligned with Redis (source of truth) - `jobs_db` dependency removed (TICKET-003).

## Usage Example
```bash
uvicorn langflix.api.main:app --reload
# Visit /docs for Swagger UI
```
