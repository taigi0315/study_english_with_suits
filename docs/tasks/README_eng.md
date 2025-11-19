# Tasks Module

## Overview

The `langflix/tasks/` module provides background task processing using Celery. It enables asynchronous processing of video content, educational slide generation, and file cleanup operations.

**Purpose:**
- Asynchronous video processing for long-running operations
- Background task execution with progress tracking
- Task queue management using Redis
- Scheduled cleanup operations

**When to use:**
- When processing videos asynchronously via API
- When running scheduled maintenance tasks
- When implementing background job processing

## File Inventory

### `celery_app.py`
Celery application configuration and initialization.

**Key Components:**
- `celery_app` - Main Celery application instance
- Redis broker and result backend configuration
- Task serialization settings
- Time limits and worker configuration

### `tasks.py`
Background task definitions.

**Key Tasks:**
- `process_video_content()` - Process video content for expression-based learning
- `generate_educational_slides()` - Generate educational slides from content data
- `cleanup_old_files()` - Clean up old temporary files

## Key Components

### Celery Application Configuration

```python
celery_app = Celery('langflix')

celery_app.conf.update(
    broker_url='redis://localhost:6379/0',
    result_backend='redis://localhost:6379/0',
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)
```

**Configuration Details:**
- **Broker**: Redis at `localhost:6379/0`
- **Result Backend**: Redis for task results
- **Serialization**: JSON format
- **Time Limits**: 30 minutes hard limit, 25 minutes soft limit
- **Worker Settings**: Prefetch multiplier 1, late acknowledgment

### Video Processing Task

```python
@celery_app.task(bind=True)
def process_video_content(self, video_path: str, output_dir: str):
    """
    Process video content for expression-based learning.
    
    Args:
        video_path: Path to the input video file
        output_dir: Directory to save processed content
        
    Returns:
        dict: Processing results with status and message
    """
```

**Features:**
- Progress tracking via `update_state()`
- State updates: PROGRESS, SUCCESS, FAILURE
- Error handling with exception logging
- Task metadata for progress reporting

**Usage:**
```python
from langflix.tasks.tasks import process_video_content

# Queue task
result = process_video_content.delay(
    video_path="input.mkv",
    output_dir="output/"
)

# Check status
print(result.state)  # PENDING, PROGRESS, SUCCESS, FAILURE

# Get result
if result.ready():
    print(result.result)
```

### Educational Slide Generation Task

```python
@celery_app.task(bind=True)
def generate_educational_slides(self, content_data: dict):
    """
    Generate educational slides from content data.
    
    Args:
        content_data: Dictionary containing content information
        
    Returns:
        dict: Generation results with status and message
    """
```

**Content Data Structure:**
```python
content_data = {
    'title': 'Expression Title',
    'expression': 'break the ice',
    'translation': '분위기를 깨다',
    # ... other expression data
}
```

### File Cleanup Task

```python
@celery_app.task
def cleanup_old_files(days: int = 7):
    """
    Clean up old temporary files.
    
    Args:
        days: Number of days to keep files (default: 7)
        
    Returns:
        dict: Cleanup results with status and message
    """
```

**Usage:**
```python
from langflix.tasks.tasks import cleanup_old_files

# Clean up files older than 7 days
result = cleanup_old_files.delay(days=7)

# Or schedule periodic cleanup
from celery.schedules import crontab
celery_app.conf.beat_schedule = {
    'cleanup-old-files': {
        'task': 'langflix.tasks.tasks.cleanup_old_files',
        'schedule': crontab(hour=2, minute=0),  # Daily at 2 AM
        'args': (7,)
    },
}
```

## Implementation Details

### Task State Management

Tasks use Celery's state management for progress tracking:

```python
# Update progress
self.update_state(
    state='PROGRESS',
    meta={
        'current': 50,
        'total': 100,
        'status': 'Processing step 5/10...'
    }
)

# Mark as failed
self.update_state(
    state='FAILURE',
    meta={'error': str(exc)}
)
```

### Error Handling

Tasks implement comprehensive error handling:

```python
try:
    # Task logic
    result = process_video(...)
    return result
except Exception as exc:
    logger.error(f"Task failed: {exc}")
    self.update_state(
        state='FAILURE',
        meta={'error': str(exc)}
    )
    raise
```

### Task Binding

Tasks use `bind=True` to access task instance methods:

```python
@celery_app.task(bind=True)
def my_task(self, ...):
    # self.update_state() available
    # self.request.id for task ID
    # self.retry() for retries
```

## Dependencies

**External Libraries:**
- `celery` - Distributed task queue
- `redis` - Message broker and result backend

**Internal Dependencies:**
- `langflix.settings` - Configuration access
- `langflix.services` - Business logic services

**Infrastructure:**
- Redis server (required for broker and result backend)
- Celery worker processes

## Common Tasks

### Starting Celery Worker

```bash
# Start worker
celery -A langflix.tasks.celery_app worker --loglevel=info

# Start with concurrency
celery -A langflix.tasks.celery_app worker --loglevel=info --concurrency=4

# Start beat scheduler for periodic tasks
celery -A langflix.tasks.celery_app beat --loglevel=info
```

### Monitoring Tasks

```python
from langflix.tasks.celery_app import celery_app

# Inspect active tasks
inspector = celery_app.control.inspect()
active = inspector.active()
registered = inspector.registered()
scheduled = inspector.scheduled()

# Get task result
from celery.result import AsyncResult
result = AsyncResult(task_id, app=celery_app)
print(result.state, result.result)
```

### Task Retry Logic

```python
@celery_app.task(bind=True, autoretry_for=(Exception,), max_retries=3)
def process_video_content(self, video_path: str, output_dir: str):
    try:
        # Task logic
        pass
    except Exception as exc:
        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
```

## Gotchas and Notes

### Important Considerations

1. **Redis Connection:**
   - Ensure Redis is running before starting workers
   - Default connection: `localhost:6379/0`
   - Configure Redis URL via environment variable if needed

2. **Task Time Limits:**
   - Hard limit: 30 minutes (task killed if exceeded)
   - Soft limit: 25 minutes (SoftTimeLimitExceeded exception)
   - Adjust based on video processing requirements

3. **Worker Prefetch:**
   - `prefetch_multiplier=1` ensures fair task distribution
   - Prevents one worker from hoarding tasks
   - Important for long-running tasks

4. **Task Serialization:**
   - Uses JSON serialization (not pickle)
   - Complex objects must be serializable to JSON
   - Consider using task IDs instead of passing large objects

5. **Late Acknowledgment:**
   - `task_acks_late=True` acknowledges tasks after completion
   - Prevents task loss if worker crashes during execution
   - Requires proper error handling

### Performance Tips

- Use appropriate worker concurrency based on CPU cores
- Monitor Redis memory usage for large result payloads
- Use result backends with expiration for temporary results
- Consider using result backend with database for persistence

### Error Handling

- Always handle exceptions in tasks
- Use `update_state()` to report errors
- Implement retry logic for transient failures
- Log errors for debugging

### Current Implementation Status

**Note:** The current task implementations (`process_video_content`, `generate_educational_slides`, `cleanup_old_files`) contain TODO comments indicating they are placeholders. Full implementation should:

1. Integrate with `VideoPipelineService` for video processing
2. Use `SlideGenerator` for slide creation
3. Implement actual file cleanup logic
4. Add proper progress reporting
5. Handle edge cases and errors

## Related Documentation

- [Services Module](../services/README_eng.md) - Business logic services
- [API Module](../api/README_eng.md) - API endpoints that use tasks
- [Core Module](../core/README_eng.md) - Core processing logic

