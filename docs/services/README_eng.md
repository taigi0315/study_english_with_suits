# Services Module Documentation

## Overview

The `langflix/services/` module contains service-layer classes that provide unified interfaces for business logic, consolidating code that was previously duplicated between API and CLI implementations.

**Last Updated:** 2025-01-30  
**Related Tickets:** TICKET-001-extract-pipeline-logic

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

### Integration Tests
- `tests/integration/test_pipeline_service.py` - End-to-end service tests
  - Service uses same pipeline as CLI
  - Progress callback integration
  - Result structure consistency

## Related Documentation

- [Core Module Documentation](../core/README_eng.md) - LangFlixPipeline details
- [API Module Documentation](../api/README_eng.md) - API usage of services
- [Troubleshooting Guide](../TROUBLESHOOTING_GUIDE.md)

