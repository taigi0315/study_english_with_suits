# Database Module Documentation

## Overview

The `langflix/db/` module provides database integration for LangFlix using SQLAlchemy ORM. It supports PostgreSQL for storing media metadata, expressions, processing jobs, and YouTube upload schedules.

**Last Updated:** 2025-01-30

## Purpose

This module is responsible for:
- Database model definitions (Media, Expression, ProcessingJob, YouTubeSchedule, etc.)
- CRUD operations for all database entities
- Database session management and connection pooling
- Database migrations using Alembic

## Key Components

### Database Models

**Location:** `langflix/db/models.py`

SQLAlchemy models for the LangFlix database schema:

#### Media Model
Stores episode/show metadata:
- `id`: UUID primary key
- `show_name`: Name of the TV show
- `episode_name`: Episode identifier
- `language_code`: Language code (e.g., 'ko', 'en')
- `subtitle_file_path`: Reference to storage backend
- `video_file_path`: Reference to storage backend
- Relationships: `expressions`, `processing_jobs`

#### Expression Model
Stores individual expressions and their analysis:
- `id`: UUID primary key
- `media_id`: Foreign key to Media
- `expression`: The English expression text
- `expression_translation`: Translation
- `expression_dialogue`: Full dialogue context
- `expression_dialogue_translation`: Dialogue translation
- `similar_expressions`: JSON array of similar expressions
- `context_start_time`, `context_end_time`: Video timestamps
- `scene_type`: Type of scene (dialogue, action, etc.)
- `context_video_path`, `slide_video_path`: Storage references
- `difficulty`: 1-10 difficulty level
- `category`: Expression category (idiom, slang, formal, etc.)
- `educational_value`: Educational value explanation
- `score`: Ranking score for selection

#### ProcessingJob Model
Tracks asynchronous processing jobs:
- `id`: UUID primary key
- `media_id`: Foreign key to Media
- `status`: Job status (PENDING, PROCESSING, COMPLETED, FAILED)
- `progress`: Progress percentage (0-100)
- `error_message`: Error details if failed
- `started_at`, `completed_at`: Timestamps

#### YouTubeSchedule Model
Tracks YouTube upload schedules:
- `id`: UUID primary key
- `video_path`: Path to video file
- `video_type`: 'final' or 'short'
- `scheduled_publish_time`: Scheduled publication datetime
- `upload_status`: 'scheduled', 'uploading', 'completed', 'failed'
- `youtube_video_id`: YouTube video ID after upload
- `account_id`: Foreign key to YouTubeAccount

#### YouTubeAccount Model
Tracks YouTube account information:
- `id`: UUID primary key
- `channel_id`: YouTube channel ID
- `channel_title`: Channel name
- `email`: Account email
- `is_active`: Active status
- `token_file_path`: Path to OAuth token file

#### YouTubeQuotaUsage Model
Tracks daily YouTube API quota usage:
- `id`: UUID primary key
- `date`: Date for quota tracking
- `quota_used`: Quota units used
- `quota_limit`: Daily quota limit (default: 10000)
- `upload_count`: Number of uploads
- `final_videos_uploaded`: Count of final videos
- `short_videos_uploaded`: Count of short videos

### CRUD Operations

**Location:** `langflix/db/crud.py`

Provides CRUD classes for database operations:

#### MediaCRUD
```python
MediaCRUD.create(db, show_name, episode_name, language_code, ...)
MediaCRUD.get_by_id(db, media_id)
MediaCRUD.get_by_show_episode(db, show_name, episode_name)
MediaCRUD.update_file_paths(db, media_id, subtitle_path, video_path)
MediaCRUD.list_all(db, skip, limit)
```

#### ExpressionCRUD
```python
ExpressionCRUD.create_from_analysis(db, media_id, analysis_data)
ExpressionCRUD.create(db, media_id, expression, ...)
ExpressionCRUD.get_by_media(db, media_id)
ExpressionCRUD.get_by_id(db, expression_id)
ExpressionCRUD.search_by_text(db, search_text)
ExpressionCRUD.delete_by_media(db, media_id)
```

#### ProcessingJobCRUD
```python
ProcessingJobCRUD.create(db, media_id)
ProcessingJobCRUD.get_by_id(db, job_id)
ProcessingJobCRUD.get_by_media(db, media_id)
ProcessingJobCRUD.update_status(db, job_id, status, progress, error_message)
ProcessingJobCRUD.get_by_status(db, status)
ProcessingJobCRUD.get_active_jobs(db)
ProcessingJobCRUD.delete_by_media(db, media_id)
```

### Session Management

**Location:** `langflix/db/session.py`

Provides database connection management:

```python
class DatabaseManager:
    """Database connection manager."""
    
    def initialize(self):
        """Initialize database connection."""
    
    def get_session(self) -> Session:
        """Get database session."""
    
    def create_tables(self):
        """Create all tables."""
```

**Global Functions:**
- `get_db_session()`: Get database session for dependency injection

## Database Schema

### Relationships

```
Media (1) ──< (N) Expression
Media (1) ──< (N) ProcessingJob
YouTubeAccount (1) ──< (N) YouTubeSchedule
```

### Constraints

- `ProcessingJob.progress`: CHECK constraint (0 <= progress <= 100)
- `YouTubeSchedule.video_type`: CHECK constraint (IN ('final', 'short'))
- `YouTubeSchedule.upload_status`: CHECK constraint (IN ('scheduled', 'uploading', 'completed', 'failed'))
- Foreign keys use CASCADE delete

## Implementation Details

### Connection Configuration

Database connection is configured via `langflix.settings`:

```python
database_url = settings.get_database_url()
pool_size = settings.get_database_pool_size()
max_overflow = settings.get_database_max_overflow()
```

### Session Lifecycle

1. **Initialize**: DatabaseManager initializes engine and session factory
2. **Get Session**: Call `get_db_session()` to get session
3. **Use Session**: Perform CRUD operations
4. **Close**: Session is closed automatically (context manager)

### Migration System

Database migrations use Alembic:

- Migration files: `langflix/db/migrations/versions/`
- Migration commands: `alembic upgrade head`, `alembic revision --autogenerate`

## Dependencies

- `sqlalchemy`: ORM framework
- `alembic`: Database migration tool
- `psycopg2` or `asyncpg`: PostgreSQL driver
- `langflix.settings`: Database configuration

## Common Tasks

### Create Media Record

#### Recommended: Using Context Manager

```python
from langflix.db.crud import MediaCRUD
from langflix.db.session import db_manager

# Recommended approach: automatic commit/rollback/close
with db_manager.session() as db:
    media = MediaCRUD.create(
        db,
        show_name="Suits",
        episode_name="S01E01",
        language_code="ko",
        subtitle_file_path="subtitles/s01e01.srt",
        video_file_path="media/s01e01.mp4"
    )
    # Commit happens automatically on success
    # Rollback happens automatically on exception
    # Close happens automatically in finally block
```

#### Legacy: Manual Session Management

```python
# Still supported but not recommended
from langflix.db.session import get_db_session

db = get_db_session()
try:
    media = MediaCRUD.create(
        db,
        show_name="Suits",
        episode_name="S01E01",
        language_code="ko",
        subtitle_file_path="subtitles/s01e01.srt",
        video_file_path="media/s01e01.mp4"
    )
    db.commit()
except Exception:
    db.rollback()
finally:
    db.close()
```

### Create Expression from Analysis

```python
from langflix.db.crud import ExpressionCRUD

expression = ExpressionCRUD.create_from_analysis(
    db,
    media_id=str(media.id),
    analysis_data=expression_analysis
)
```

### Update Job Status

```python
from langflix.db.crud import ProcessingJobCRUD

ProcessingJobCRUD.update_status(
    db,
    job_id=str(job.id),
    status="PROCESSING",
    progress=50
)
```

### Query Expressions by Media

```python
expressions = ExpressionCRUD.get_by_media(db, media_id)
for expr in expressions:
    print(f"{expr.expression}: {expr.expression_translation}")
```

### Search Expressions

```python
results = ExpressionCRUD.search_by_text(db, "get away with")
for expr in results:
    print(f"Found: {expr.expression}")
```

## Database Configuration

### Environment Variables

- `DATABASE_URL`: PostgreSQL connection string
  - Example: `postgresql://user:pass@localhost/langflix`
- `DATABASE_POOL_SIZE`: Connection pool size (default: 10)
- `DATABASE_MAX_OVERFLOW`: Max overflow connections (default: 20)

### Optional Database

The database is optional - LangFlix can run in file-only mode. When database is configured:
- Metadata is stored in database
- File paths reference storage backend
- Processing jobs are tracked

## Gotchas and Notes

1. **UUID Types**: All IDs use UUID type - convert to string when needed
2. **Session Management**: Always close sessions or use context managers
3. **Transactions**: Use `db.commit()` after mutations, `db.rollback()` on errors
4. **Storage References**: File paths are references, not absolute paths
5. **Cascade Deletes**: Deleting Media deletes related Expressions and Jobs
6. **JSONB Fields**: `similar_expressions` uses JSONB for PostgreSQL array support
7. **Timezone**: All timestamps use timezone-aware datetime

## Related Modules

- `langflix/storage/`: Storage backend for file references
- `langflix/api/`: API endpoints use database for job tracking
- `langflix/services/`: Services use database for metadata storage

