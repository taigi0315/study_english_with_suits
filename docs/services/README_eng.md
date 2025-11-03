# Services Module Documentation

## Overview

The `langflix/services/` module contains service-layer classes that provide unified interfaces for business logic, consolidating code that was previously duplicated between API and CLI implementations.

**Last Updated:** 2025-11-02  
**Related Tickets:** TICKET-001-extract-pipeline-logic, TICKET-014-batch-video-processing-queue

## Purpose

This module provides:
- **Unified interfaces** for business logic that can be used by both API and CLI
- **Code consolidation** to eliminate duplication
- **Progress tracking** for long-running operations
- **Standardized result formats** across different entry points

## Key Components

### VideoPipelineService

Unified video processing pipeline service that wraps `LangFlixPipeline` for use by both API endpoints and CLI commands.

**Location:** `langflix/services/video_pipeline_service.py`

**Purpose:**
- Eliminates 450+ lines of duplicate code between API and CLI
- Provides single source of truth for video processing logic
- Enables progress tracking for API job updates

#### Key Features

**1. Unified Interface**
```python
from langflix.services.video_pipeline_service import VideoPipelineService

service = VideoPipelineService(language_code="ko", output_dir="output")
result = service.process_video(
    video_path="path/to/video.mkv",
    subtitle_path="path/to/subtitle.srt",
    show_name="Suits",
    episode_name="S01E01",
    max_expressions=10,
    language_level="intermediate",
    progress_callback=my_callback
)
```

**2. Progress Callback Support**
- Optional `progress_callback` parameter: `(progress: int, message: str) -> None`
- Progress milestones automatically reported:
  - 10%: Initializing
  - 20%: Running pipeline
  - 90%: Collecting results
  - 100%: Completed

**3. Standardized Result Format**
```python
{
    "expressions": List[dict],           # Processed expressions
    "educational_videos": List[str],     # Paths to educational videos
    "short_videos": List[str],           # Paths to short videos
    "final_video": str,                  # Path to final concatenated video
    "output_directory": str,             # Output directory path
    "summary": dict                      # Pipeline summary
}
```

#### Usage in API

```python
# In langflix/api/routes/jobs.py
from langflix.services.video_pipeline_service import VideoPipelineService

async def process_video_task(job_id: str, ...):
    service = VideoPipelineService(
        language_code=language_code,
        output_dir=output_dir
    )
    
    # Progress callback updates Redis
    def update_progress(progress: int, message: str):
        redis_manager.update_job(job_id, {
            "progress": progress,
            "current_step": message
        })
    
    result = service.process_video(
        video_path=temp_video_path,
        subtitle_path=temp_subtitle_path,
        show_name=show_name,
        episode_name=episode_name,
        progress_callback=update_progress,
        ...
    )
```

#### Usage in CLI

```python
# CLI can also use the service for consistency
from langflix.services.video_pipeline_service import VideoPipelineService

service = VideoPipelineService(language_code="ko")
result = service.process_video(...)

# Or continue using LangFlixPipeline directly (both work)
```

### BatchQueueService

Manages batch video processing with a Redis-based FIFO queue system for sequential job execution.

**Location:** `langflix/services/batch_queue_service.py`

**Purpose:**
- Create batches of video processing jobs
- Queue jobs for sequential processing
- Track batch and individual job status
- Calculate batch status from job statuses

#### Key Features

**1. Batch Creation**
```python
from langflix.services.batch_queue_service import BatchQueueService

service = BatchQueueService()
result = service.create_batch(
    videos=[
        {
            'video_path': '/path/to/video1.mp4',
            'subtitle_path': '/path/to/subtitle1.srt',
            'episode_name': 'Episode 1',
            'show_name': 'Suits'
        },
        # ... more videos
    ],
    config={
        'language_code': 'ko',
        'language_level': 'intermediate',
        'max_expressions': 50,
        'test_mode': False,
        'no_shorts': False,
        'output_dir': 'output'
    }
)
# Returns: {'batch_id': 'uuid', 'total_jobs': 2, 'jobs': [...], 'status': 'PENDING'}
```

**2. Batch Status Tracking**
```python
batch_status = service.get_batch_status(batch_id)
# Returns batch info with:
# - Overall status (PENDING, PROCESSING, COMPLETED, FAILED, PARTIALLY_FAILED)
# - Individual job statuses
# - Progress metrics (completed_jobs, failed_jobs, total_jobs)
```

**3. Status Calculation**
- `PENDING`: All jobs are QUEUED (not yet started)
- `PROCESSING`: At least one job is QUEUED or PROCESSING
- `COMPLETED`: All jobs completed successfully
- `FAILED`: All jobs failed
- `PARTIALLY_FAILED`: Mix of completed and failed jobs

**4. Batch Size Limits**
- Maximum batch size: 50 videos per batch (configurable via `MAX_BATCH_SIZE`)
- Validation ensures batch size doesn't exceed limit

#### Usage in API

```python
# In langflix/api/routes/batch.py
from langflix.services.batch_queue_service import BatchQueueService

@router.post("/batch")
async def create_batch(request: BatchCreateRequest):
    service = BatchQueueService()
    
    # Validate batch size
    if len(request.videos) > service.MAX_BATCH_SIZE:
        raise HTTPException(status_code=400, detail="Batch size exceeded")
    
    result = service.create_batch(
        videos=[video.dict() for video in request.videos],
        config=request.dict(exclude={'videos'})
    )
    return result
```

### QueueProcessor

Sequentially processes jobs from the Redis queue using a background worker pattern integrated with FastAPI lifespan.

**Location:** `langflix/services/queue_processor.py`

**Purpose:**
- Process queued jobs sequentially (FIFO)
- Ensure only one processor instance runs (Redis lock)
- Handle stuck jobs on startup
- Graceful shutdown with job requeuing

#### Key Features

**1. Background Processing**
- Runs as async background task in FastAPI lifespan
- Automatically starts on API startup
- Stops gracefully on API shutdown

**2. Processor Lock**
- Uses Redis lock (`jobs:processor_lock`) to ensure single instance
- Lock renewal every 30 minutes
- Prevents duplicate processing

**3. Stuck Job Recovery**
- On startup, identifies jobs stuck in PROCESSING state (>1 hour)
- Marks stuck jobs as FAILED automatically
- Clears stale processing markers

**4. Async Processing**
- Uses `run_in_executor()` to run blocking `process_video()` calls
- Prevents event loop blocking
- Allows concurrent API requests during processing

**5. Progress Updates**
- Updates job progress in Redis during processing
- Includes `updated_at` timestamp for tracking
- Continues processing even if progress updates fail

**6. Error Handling**
- Marks jobs as FAILED on processing errors
- Updates batch status if job is part of a batch
- Removes processing marker on completion/failure

#### Integration

```python
# In langflix/api/main.py
from langflix.services.queue_processor import QueueProcessor

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    queue_processor = QueueProcessor()
    queue_processor_task = asyncio.create_task(queue_processor.start())
    
    yield
    
    # Shutdown
    await queue_processor.stop()
    queue_processor_task.cancel()
```

#### Processing Flow

1. **Job Queued**: Job added to Redis list `jobs:queue`
2. **Job Claimed**: Processor atomically marks job as PROCESSING
3. **Job Processed**: Video processing runs in thread executor
4. **Progress Updated**: Progress callbacks update Redis job status
5. **Job Completed**: Job marked COMPLETED/FAILED, batch status updated
6. **Next Job**: Processor picks next job from queue

### PipelineRunner (Legacy)

**Location:** `langflix/services/pipeline_runner.py`

**Status:** Still in use (by `langflix/youtube/web_ui.py`), but consider migrating to `VideoPipelineService` in the future.

**Note:** Previously had bugs (undefined `selected_expressions` variable) that were fixed in TICKET-001.

## Architecture Pattern

### Service Layer Pattern

This module implements the Service Layer Pattern:

```
┌─────────────┐         ┌──────────────┐         ┌──────────────────┐
│   API       │────────▶│   Service    │────────▶│   Core Logic     │
│  (routes)   │         │   (services) │         │   (main.py)      │
└─────────────┘         └──────────────┘         └──────────────────┘
        │                        │                        │
        │                        │                        │
        ▼                        ▼                        ▼
┌─────────────┐         ┌──────────────┐         ┌──────────────────┐
│   CLI       │────────▶│   Service    │────────▶│   Core Logic     │
│  (main.py)  │         │   (services) │         │   (main.py)      │
└─────────────┘         └──────────────┘         └──────────────────┘
```

**Benefits:**
- Single source of truth for business logic
- No duplication between API and CLI
- Easy to add new entry points (e.g., WebSocket, GraphQL)
- Testable business logic independent of entry point

## Dependencies

### Internal Dependencies
- `langflix/main.py` - `LangFlixPipeline` (core pipeline logic)
- `langflix/utils/temp_file_manager.py` - TempFileManager for file cleanup (used internally by pipeline)
- `langflix/utils/filename_utils.py` - Filename sanitization (used internally)
- `langflix/core/redis_client.py` - `RedisJobManager` for batch and queue operations
- `langflix/services/video_pipeline_service.py` - Used by QueueProcessor for actual processing

### External Dependencies
- Standard library: `logging`, `pathlib`, `typing`, `datetime`

## Common Tasks

### Adding a New Service

1. Create new service class in `langflix/services/`
2. Follow same pattern as `VideoPipelineService`:
   - Initialize with required dependencies
   - Provide clear method interfaces
   - Support progress callbacks if applicable
   - Return standardized result formats
3. Export in `langflix/services/__init__.py`
4. Update this documentation

### Modifying VideoPipelineService

1. Ensure changes maintain backward compatibility
2. Update both API and CLI if interface changes
3. Add tests in `tests/unit/test_video_pipeline_service.py`
4. Update integration tests in `tests/integration/test_pipeline_service.py`

### Adding Progress Tracking

1. Add `progress_callback` parameter to service method
2. Call callback at key milestones
3. Document progress percentages in method docstring
4. Test callback invocation in unit tests

## Testing

### Unit Tests
- `tests/unit/test_video_pipeline_service.py` - Service unit tests
  - Initialization
  - Basic processing
  - Progress callbacks
  - Error handling
  - Result extraction
- `tests/unit/test_batch_queue_service.py` - BatchQueueService unit tests
  - Batch creation with various configurations
  - Batch status calculation (all status scenarios)
  - Edge cases (missing episode_name, empty paths, batch size limits)
  - Batch status updates
- `tests/unit/test_queue_processor.py` - QueueProcessor unit tests
  - Lock acquisition/release
  - Stuck job recovery
  - Executor-based processing (prevents event loop blocking)
  - Progress callback failure handling
  - File read failures
  - Graceful shutdown

### Integration Tests
- `tests/integration/test_pipeline_service.py` - End-to-end service tests
  - Service uses same pipeline as CLI
  - Progress callback integration
  - Result structure consistency

## Related Documentation

- [Core Module Documentation](../core/README_eng.md) - LangFlixPipeline details
- [API Module Documentation](../api/README_eng.md) - API usage of services
- [Troubleshooting Guide](../TROUBLESHOOTING_GUIDE.md)

