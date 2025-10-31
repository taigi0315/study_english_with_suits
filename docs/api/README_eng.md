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
- Lifespan startup performs Redis job store cleanup and health check via `langflix.core.redis_client.get_redis_job_manager()`.

## Dependency Injection (Placeholders)
- `get_db()` yields a `Session` but currently returns `None` (TODO).
- `get_storage()` returns `None` (TODO).

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
- `/health/detailed` (GET): Includes version and component placeholders.
- `/health/redis` (GET): Redis health via job manager.
- `/health/redis/cleanup` (POST): Cleanup expired/stale jobs.
- `/api/v1/files` (GET): List files under `output/` recursively.
- `/api/v1/files/{file_id}` (GET): Stub for file details (TODO).
- `/api/v1/files/{file_id}` (DELETE): Stub for deletion (TODO).
- `/api/v1/jobs` (POST): Create a new job with `UploadFile` video+subtitle and form fields; starts background processing.
- `/api/v1/jobs/{job_id}` (GET): Fetch current job state from Redis.
- `/api/v1/jobs/{job_id}/expressions` (GET): Returns expressions from Redis (same source as job status).
- `/api/v1/jobs` (GET): List all jobs from Redis.

## Job Processing (Background Task)

### Unified Pipeline Service

The API uses `VideoPipelineService` (`langflix/services/video_pipeline_service.py`) which provides a unified interface for both API and CLI processing. This eliminates code duplication and ensures consistent behavior.

**Key Features:**
- Single source of truth for video processing pipeline
- Progress callback support for real-time job status updates
- Consistent result format across API and CLI

**Implementation:**
- Defined in `routes/jobs.py` as `process_video_task(...)` (simplified from 450+ lines to ~110 lines)
- Uses `VideoPipelineService.process_video()` which wraps `LangFlixPipeline`
- Uses `TempFileManager` for temporary file handling (see `langflix/utils/temp_file_manager.py`)
  - Temporary files are automatically cleaned up when context exits, even on exceptions
  - No hardcoded `/tmp` paths - uses system temp directory via `tempfile` module
  - Context managers ensure cleanup even if processing fails
- Updates Redis job status/results via callback; invalidates video cache

**Progress Tracking:**
- Progress callbacks automatically update Redis job status
- Progress milestones: 10% (init), 20% (saving files), 30% (parsing), 50% (processing), 70% (educational videos), 80% (short videos), 100% (complete)

## Error Handling and Logging
- Centralized exception handler returns consistent JSON payloads.
- Extensive `logger.info/warning/error` statements track pipeline steps and failures.

## Security and Operational Notes
- CORS is wide-open (`*`) by default; restrict per environment.
- File operations target local filesystem; ensure appropriate container paths/permissions in production.
- Validate upload sizes/types further if needed.
- Redis availability is assumed; startup logs on failure but app remains up—consider fail-fast or degraded mode indicator.

## Extensibility
- Implement `dependencies.get_db/get_storage` to integrate DB/storage.
- Replace stubbed file detail/delete with actual storage-backed operations.
- ✅ `/jobs/{id}/expressions` aligned with Redis (source of truth) - `jobs_db` dependency removed (TICKET-003).

## Usage Example
```bash
uvicorn langflix.api.main:app --reload
# Visit /docs for Swagger UI
```
