# YouTube Module Documentation (ENG)

**Last Updated:** 2025-01-30

## Overview

The `langflix/youtube/` module provides comprehensive YouTube automation functionality for managing, uploading, and scheduling educational videos. It includes video file management, metadata generation, upload handling with OAuth authentication, scheduling with quota management, and a web-based UI for video management.

## Folder Structure

- `video_manager.py`: Video file scanning, metadata extraction, and file management
- `uploader.py`: YouTube API authentication and video upload functionality
- `metadata_generator.py`: YouTube metadata (title, description, tags) generation
- `schedule_manager.py`: Upload scheduling with daily limits and quota management
- `web_ui.py`: Flask-based web interface for video management dashboard

## Key Components

### VideoFileManager (`video_manager.py`)

Manages generated video files for YouTube upload.

**Features:**
- Scans output directory for video files
- Extracts metadata using ffprobe (duration, resolution, format)
- Parses video paths to determine type, episode, expression
- Integrates with Redis for caching video metadata
- Checks database for upload status
- Filters videos by type, episode, upload readiness

**Key Methods:**
- `scan_all_videos(force_refresh=False)`: Scan all video files and extract metadata
- `get_uploadable_videos(videos)`: Filter videos ready for upload (final and short types)
- `get_videos_by_type(videos, video_type)`: Filter by video type
- `get_videos_by_episode(videos, episode)`: Filter by episode
- `get_upload_ready_videos(videos)`: Get videos ready for upload
- `get_statistics(videos)`: Get video statistics

**VideoMetadata Dataclass:**
```python
@dataclass
class VideoMetadata:
    path: str
    filename: str
    size_mb: float
    duration_seconds: float
    resolution: str
    format: str
    created_at: datetime
    episode: str
    expression: str
    video_type: str  # 'educational', 'short', 'final', 'slide', 'context'
    language: str
    ready_for_upload: bool = False
    uploaded_to_youtube: bool = False
    youtube_video_id: Optional[str] = None
```

**Caching:**
- Uses Redis for video metadata caching (5-minute TTL)
- Cache invalidation on video processing completion
- Fallback to filesystem scan if cache unavailable

### YouTubeUploader (`uploader.py`)

Handles YouTube API authentication and video uploads.

**Features:**
- OAuth 2.0 authentication with Google
- Token management and refresh
- Video upload with progress tracking
- Metadata upload (title, description, tags, privacy, category)
- Scheduled publishing support
- Error handling and retry logic

**Key Methods:**
- `authenticate()`: Authenticate with YouTube API
- `upload_video(video_path, metadata, scheduled_time=None)`: Upload video with metadata
- `refresh_token()`: Refresh OAuth token if expired
- `get_authenticated_service()`: Get authenticated YouTube API service

**OAuth State Storage:**
- Supports Redis for OAuth state storage (for web-based auth flows)
- Falls back to in-memory storage if Redis unavailable
- Prevents CSRF attacks in OAuth flow

**YouTubeUploadResult Dataclass:**
```python
@dataclass
class YouTubeUploadResult:
    success: bool
    video_id: Optional[str] = None
    video_url: Optional[str] = None
    error_message: Optional[str] = None
    upload_time: Optional[datetime] = None
```

**YouTubeVideoMetadata Dataclass:**
```python
@dataclass
class YouTubeVideoMetadata:
    title: str
    description: str
    tags: List[str]
    category: str
    privacy: str  # private, public, unlisted
    thumbnail_path: Optional[str] = None
```

### YouTubeMetadataGenerator (`metadata_generator.py`)

Generates YouTube metadata for educational videos.

**Features:**
- Template-based metadata generation
- Support for different video types (educational, short, final)
- Dynamic content substitution (expression, translation, episode)
- SEO-optimized titles and descriptions
- Category mapping for YouTube categories

**Key Methods:**
- `generate_metadata(video_type, expression, translation, episode, language)`: Generate complete metadata
- `generate_title(video_type, expression, episode)`: Generate title
- `generate_description(video_type, expression, translation, episode, language)`: Generate description
- `generate_tags(video_type, expression, episode)`: Generate tags

**Templates:**
- Pre-configured templates for educational, short, and final video types
- Customizable templates via configuration
- Supports multiple languages

### YouTubeScheduleManager (`schedule_manager.py`)

Manages YouTube upload scheduling with daily limits and quota management.

**Features:**
- Daily upload limits (configurable: default 2 final, 5 shorts per day)
- Preferred posting times (e.g., 10:00, 14:00, 18:00)
- Quota tracking and management
- Quota warning threshold (default 80%)
- Database-backed scheduling with SQLAlchemy
- Race condition prevention with database-level locking

**Key Methods:**
- `get_next_available_slot(video_type, preferred_date=None)`: Calculate next available upload slot
- `check_daily_quota(date)`: Check daily quota status for a date
- `schedule_upload(video_path, video_type, scheduled_time)`: Schedule video for upload
- `get_quota_status(date)`: Get quota status for a date
- `check_quota_warning()`: Check if quota is approaching limit

**ScheduleConfig Dataclass:**
```python
@dataclass
class ScheduleConfig:
    daily_limits: Dict[str, int] = None  # {'final': 2, 'short': 5}
    preferred_times: List[str] = None    # ['10:00', '14:00', '18:00']
    quota_limit: int = 10000
    warning_threshold: float = 80.0      # Percentage (0-100)
```

**DailyQuotaStatus Dataclass:**
```python
@dataclass
class DailyQuotaStatus:
    date: date
    final_used: int
    final_remaining: int
    short_used: int
    short_remaining: int
    quota_used: int
    quota_remaining: int
    quota_percentage: float
```

**Database Integration:**
- Uses `db_manager.session()` context manager for database sessions
- Stores schedule in `YouTubeSchedule` table
- Tracks quota usage in `YouTubeQuotaUsage` table
- Database-level locking prevents race conditions (TICKET-021)

**Recent Fixes (TICKET-021):**
- Fixed race conditions in concurrent scheduling requests
- Added database-level locking for schedule creation
- Improved error handling for database connection failures
- Fixed quota warning threshold calculation (changed from ratio to percentage)

### VideoManagementUI (`web_ui.py`)

Flask-based web interface for video management dashboard.

**Features:**
- **File Explorer Interface**: Directory-based navigation (output/ → Series/ → Episode/ → shorts/ or long/)
- Video listing and filtering
- Upload management with progress tracking
- Schedule management interface
- Statistics dashboard
- OAuth authentication flow for YouTube
- Batch operations (multi-select upload)
- Real-time job status updates
- Breadcrumb navigation for directory traversal

**Key Routes:**
- `/`: Main dashboard with file explorer (HTML)
- `/api/videos`: Get all videos (JSON)
- `/api/videos/<video_type>`: Get videos by type
- `/api/videos/episode/<episode>`: Get videos by episode
- `/api/upload-ready`: Get videos ready for upload
- `/api/statistics`: Get video statistics
- `/api/explore`: Explore directory structure (new)
- `/api/explore/file-info`: Get detailed file information (new)
- `/api/upload`: Upload video to YouTube
- `/api/schedule`: Schedule video for upload
- `/api/schedule/<schedule_id>`: Get/update/delete schedule
- `/api/oauth/authorize`: Initiate OAuth flow
- `/api/oauth/callback`: Handle OAuth callback
- `/api/thumbnail/<video_path>`: Generate and serve video thumbnail (uses temporary files)

**UI Features:**
- **File Explorer View**: Navigate through output directory structure like a file manager
- **List View**: Compact list display showing video files with metadata
- **Breadcrumb Navigation**: Easy navigation between directory levels
- **Filtering**: Filter by video type (short-form, long-form), upload status
- **Search**: Search files by name
- **Batch Selection**: Select multiple videos for batch upload operations
- **File Filtering**: Automatically filters out system files (.DS_Store) and thumbnail files

**Integration Points:**
- Uses `VideoFileManager` for video scanning
- Uses `YouTubeUploader` for uploads
- Uses `YouTubeMetadataGenerator` for metadata
- Uses `YouTubeScheduleManager` for scheduling
- Uses `MediaScanner` for media file discovery
- Uses `JobQueue` for background processing
- Uses Redis for OAuth state storage

**Recent Enhancements (2025-01):**
- File explorer interface replacing flat video list
- Directory-based navigation for better organization
- Automatic filtering of system files (.DS_Store)
- Thumbnail generation using temporary files (no disk storage)
- Improved list view with full filename display
- Removed redundant metadata (episode name, file size) for cleaner UI

**Recent Enhancements (TICKET-021):**
- Multi-select checkbox for batch video management
- Improved error handling and user feedback
- Better UI/UX for schedule management
- Real-time quota status display

## Usage Examples

### Upload Video with Scheduling

```python
from langflix.youtube.uploader import YouTubeUploader, YouTubeUploadManager
from langflix.youtube.metadata_generator import YouTubeMetadataGenerator
from langflix.youtube.schedule_manager import YouTubeScheduleManager

# Initialize components
upload_manager = YouTubeUploadManager()
metadata_generator = YouTubeMetadataGenerator()
schedule_manager = YouTubeScheduleManager()

# Generate metadata
metadata = metadata_generator.generate_metadata(
    video_type="educational",
    expression="Break the ice",
    translation="분위기를 깨다",
    episode="S01E01",
    language="ko"
)

# Get next available slot
scheduled_time = schedule_manager.get_next_available_slot(
    video_type="final",
    preferred_date=date.today()
)

# Upload with scheduling
result = upload_manager.upload_video(
    video_path="output/educational_Break_the_ice.mkv",
    metadata=metadata,
    scheduled_time=scheduled_time
)
```

### Scan and Filter Videos

```python
from langflix.youtube.video_manager import VideoFileManager

# Initialize manager
manager = VideoFileManager(output_dir="output")

# Scan all videos
all_videos = manager.scan_all_videos()

# Filter by type
final_videos = manager.get_videos_by_type(all_videos, "final")
short_videos = manager.get_videos_by_type(all_videos, "short")

# Get upload-ready videos
ready_videos = manager.get_upload_ready_videos(all_videos)
```

### Check Quota Status

```python
from langflix.youtube.schedule_manager import YouTubeScheduleManager
from datetime import date

schedule_manager = YouTubeScheduleManager()

# Check quota for today
quota_status = schedule_manager.check_daily_quota(date.today())

print(f"Final videos: {quota_status.final_used}/{quota_status.final_remaining + quota_status.final_used}")
print(f"Short videos: {quota_status.short_used}/{quota_status.short_remaining + quota_status.short_used}")
print(f"Quota: {quota_status.quota_percentage:.1f}%")
```

## Dependencies

- **google-api-python-client**: YouTube API client
- **google-auth-httplib2**: HTTP transport for Google Auth
- **google-auth-oauthlib**: OAuth 2.0 flow for Google
- **flask**: Web framework for UI
- **sqlalchemy**: Database ORM for scheduling
- **ffprobe**: Video metadata extraction (external binary)

## Configuration

### OAuth Credentials

1. Create OAuth 2.0 credentials in Google Cloud Console
2. Download credentials as `youtube_credentials.json`
3. Place in project root or configure path

### Schedule Configuration

Configure in `ScheduleConfig`:
- `daily_limits`: Daily upload limits per video type
- `preferred_times`: Preferred posting times (HH:MM format)
- `quota_limit`: Daily quota limit (default: 10000)
- `warning_threshold`: Warning threshold percentage (default: 80%)

## Error Handling

All components include comprehensive error handling:
- Database connection errors are handled gracefully
- OAuth token refresh is automatic
- Upload failures are logged and reported
- Schedule conflicts are prevented with database locking

## Related Documentation

- [Database Module Documentation](../db/README_eng.md) - Database schema and models
- [Services Module Documentation](../services/README_eng.md) - Job queue and pipeline services
- [API Module Documentation](../api/README_eng.md) - FastAPI endpoints
- [Storage Module Documentation](../storage/README_eng.md) - Storage backend integration

## Testing

Tests are located in `tests/youtube/`:
- `test_video_manager.py`: Video file management tests
- `test_uploader.py`: Upload functionality tests
- `test_metadata_generator.py`: Metadata generation tests
- `test_schedule_manager.py`: Scheduling tests

## Recent Changes

### TICKET-021: Scheduler Race Conditions Fix
- Added database-level locking for schedule creation
- Fixed race conditions in concurrent scheduling requests
- Improved quota warning threshold calculation (percentage instead of ratio)
- Enhanced error handling for database connection failures

### TICKET-020: Scheduled Time Mismatch Fix
- Fixed timezone handling in UI and backend
- Ensured consistent time representation across components

### TICKET-019: Short-form Video Duration Limit
- Reduced short-form video duration limit
- Improved validation and error messages

### TICKET-018: Scheduled YouTube Upload Processor
- Implemented background processor for scheduled uploads
- Added automatic upload execution at scheduled times
- Improved job tracking and status updates

