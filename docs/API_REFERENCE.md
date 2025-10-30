# LangFlix API Reference

## API Mode Setup (15 minutes)

### Database Setup

```bash
# Install PostgreSQL (if not already)
brew install postgresql  # macOS
sudo apt install postgresql  # Ubuntu

# Create database
createdb langflix

# Run migrations
alembic upgrade head
```

### Start API Server

```bash
# Development mode
uvicorn langflix.api.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn langflix.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Test API

```bash
# Health check
curl http://localhost:8000/health

# View API docs
open http://localhost:8000/docs
```

---

## API Endpoints

## Media Pipeline Notes (Unreleased)
- Video: keep original codec/resolution when possible; re-encode only when filters are applied
- Audio: normalized to stereo (ac=2), 48kHz (ar=48000) at concat/stack boundaries
- Explicit stream mapping is used to prevent audio loss
- Related modules: `langflix/media/ffmpeg_utils.py`, `langflix/audio/timeline.py`, `langflix/subtitles/overlay.py`, `langflix/slides/generator.py`

### Health Check

```bash
GET /health
```

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "version": "1.0.0"
}
```

### Submit Processing Job

```bash
POST /api/v1/jobs
```

**Request**:
```bash
curl -X POST "http://localhost:8000/api/v1/jobs" \
  -F "video_file=@video.mp4" \
  -F "subtitle_file=@subtitle.srt" \
  -F "language_code=en" \
  -F "show_name=Suits" \
  -F "episode_name=S01E01" \
  -F "language_level=intermediate" \
  -F "test_mode=false" \
  -F "no_shorts=false"
```

**Response**:
```json
{
  "job_id": "uuid",
  "status": "PENDING",
  "created_at": "2024-01-01T12:00:00Z"
}
```

### Check Job Status

```bash
GET /api/v1/jobs/{job_id}
```

**Response**:
```json
{
  "job_id": "uuid",
  "status": "PROCESSING",
  "progress": 45,
  "created_at": "2024-01-01T12:00:00Z",
  "started_at": "2024-01-01T12:01:00Z",
  "estimated_completion": "2024-01-01T12:15:00Z"
}
```

### Get Job Results

```bash
GET /api/v1/jobs/{job_id}/expressions
```

**Response**:
```json
{
  "job_id": "uuid",
  "expressions": [
    {
      "id": "expr_1",
      "expression": "How are you doing?",
      "translation": "어떻게 지내고 있어요?",
      "context": "Full dialogue context...",
      "difficulty": 3,
      "category": "greeting"
    }
  ],
  "total_count": 10
}
```

### Download Generated Files

```bash
GET /api/v1/jobs/{job_id}/files/{file_type}
```

**File Types**:
- `context_videos`: Individual expression clips
- `educational_videos`: Combined educational videos
- `short_videos`: Short format videos
- `metadata`: JSON metadata files

---

## YouTube Integration API

### YouTube Authentication

```bash
POST /api/youtube/login
```

**Response**:
```json
{
  "status": "success",
  "auth_url": "https://accounts.google.com/oauth/authorize?..."
}
```

### Get Next Available Upload Time

```bash
GET /api/schedule/next-available?video_type=final
```

**Response**:
```json
{
  "next_available": "2024-01-02T10:00:00Z",
  "video_type": "final",
  "estimated_duration": 300
}
```

### Schedule Upload

```bash
POST /api/upload/schedule
```

**Request**:
```json
{
  "video_path": "/path/to/video.mp4",
  "video_type": "final",
  "scheduled_time": "2024-01-02T10:00:00Z",
  "title": "Suits S01E01 - English Expressions",
  "description": "Learn English expressions from Suits episode 1",
  "tags": ["english", "learning", "suits"]
}
```

**Response**:
```json
{
  "upload_id": "upload_uuid",
  "status": "SCHEDULED",
  "scheduled_time": "2024-01-02T10:00:00Z"
}
```

### Check Upload Status

```bash
GET /api/upload/{upload_id}/status
```

**Response**:
```json
{
  "upload_id": "upload_uuid",
  "status": "COMPLETED",
  "youtube_video_id": "dQw4w9WgXcQ",
  "uploaded_at": "2024-01-02T10:05:00Z"
}
```

---

## Media Management API

### Scan Media Files

```bash
POST /api/media/scan
```

**Request**:
```json
{
  "directory": "/path/to/media",
  "recursive": true,
  "file_types": ["mp4", "mkv", "avi"]
}
```

**Response**:
```json
{
  "scan_id": "scan_uuid",
  "status": "COMPLETED",
  "files_found": 25,
  "processed": 25,
  "errors": 0
}
```

### Get Media Library

```bash
GET /api/media/library
```

**Response**:
```json
{
  "media_files": [
    {
      "id": "media_1",
      "filename": "Suits.S01E01.mkv",
      "path": "/path/to/Suits.S01E01.mkv",
      "size": 1024000000,
      "duration": 2700,
      "created_at": "2024-01-01T12:00:00Z"
    }
  ],
  "total_count": 25
}
```

### Get Available Subtitles

```bash
GET /api/media/{media_id}/subtitles
```

**Response**:
```json
{
  "subtitles": [
    {
      "id": "sub_1",
      "filename": "Suits.S01E01.srt",
      "path": "/path/to/Suits.S01E01.srt",
      "language": "en",
      "encoding": "utf-8"
    }
  ]
}
```

---

## Job Queue Management

### Get All Jobs

```bash
GET /api/v1/jobs
```

**Query Parameters**:
- `status`: Filter by status (PENDING, PROCESSING, COMPLETED, FAILED)
- `limit`: Number of jobs to return (default: 50)
- `offset`: Number of jobs to skip (default: 0)

**Response**:
```json
{
  "jobs": [
    {
      "job_id": "uuid",
      "status": "COMPLETED",
      "created_at": "2024-01-01T12:00:00Z",
      "completed_at": "2024-01-01T12:15:00Z"
    }
  ],
  "total_count": 100,
  "limit": 50,
  "offset": 0
}
```

### Cancel Job

```bash
DELETE /api/v1/jobs/{job_id}
```

**Response**:
```json
{
  "job_id": "uuid",
  "status": "CANCELLED",
  "cancelled_at": "2024-01-01T12:10:00Z"
}
```

### Retry Failed Job

```bash
POST /api/v1/jobs/{job_id}/retry
```

**Response**:
```json
{
  "job_id": "uuid",
  "status": "PENDING",
  "retry_count": 2,
  "scheduled_at": "2024-01-01T12:10:00Z"
}
```

---

## Quota Management

### Check Quota Status

```bash
GET /api/quota/status
```

**Response**:
```json
{
  "youtube": {
    "daily_limits": {
      "final": 2,
      "short": 5
    },
    "used_today": {
      "final": 1,
      "short": 2
    },
    "remaining": {
      "final": 1,
      "short": 3
    },
    "reset_time": "2024-01-02T00:00:00Z"
  }
}
```

### Get Quota Usage History

```bash
GET /api/quota/history
```

**Query Parameters**:
- `days`: Number of days to retrieve (default: 7)
- `video_type`: Filter by video type (final, short)

**Response**:
```json
{
  "usage_history": [
    {
      "date": "2024-01-01",
      "final_videos": 1,
      "short_videos": 2,
      "total_quota_used": 3
    }
  ]
}
```

---

## Error Handling

### Error Response Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid file format",
    "details": {
      "field": "subtitle_file",
      "expected": "srt",
      "received": "txt"
    }
  },
  "timestamp": "2024-01-01T12:00:00Z"
}
```

### Common Error Codes

| Code | Description | HTTP Status |
|------|-------------|-------------|
| `VALIDATION_ERROR` | Invalid request parameters | 400 |
| `FILE_NOT_FOUND` | Requested file not found | 404 |
| `JOB_NOT_FOUND` | Job ID not found | 404 |
| `QUOTA_EXCEEDED` | Daily quota exceeded | 429 |
| `PROCESSING_ERROR` | Internal processing error | 500 |
| `AUTHENTICATION_ERROR` | Authentication failed | 401 |
| `PERMISSION_ERROR` | Insufficient permissions | 403 |

---

## Authentication

### API Key Authentication

```bash
# Add API key to request headers
curl -H "X-API-Key: your_api_key" \
  http://localhost:8000/api/v1/jobs
```

### OAuth2 Authentication (for YouTube)

```bash
# Include access token in headers
curl -H "Authorization: Bearer your_access_token" \
  http://localhost:8000/api/youtube/status
```

---

## Rate Limiting

### Rate Limits

- **General API**: 100 requests per minute
- **File Upload**: 10 requests per minute
- **YouTube API**: Respects Google's rate limits

### Rate Limit Headers

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

---

## WebSocket Events

### Real-time Job Updates

```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:8000/ws/jobs');

// Listen for job updates
ws.onmessage = function(event) {
  const data = JSON.parse(event.data);
  console.log('Job update:', data);
};
```

### Event Types

```json
{
  "type": "job_status_update",
  "job_id": "uuid",
  "status": "PROCESSING",
  "progress": 45,
  "timestamp": "2024-01-01T12:05:00Z"
}
```

---

## SDK Examples

### Python SDK

```python
import requests

# Submit job
response = requests.post(
    'http://localhost:8000/api/v1/jobs',
    files={
        'video_file': open('video.mp4', 'rb'),
        'subtitle_file': open('subtitle.srt', 'rb')
    },
    data={
        'language_code': 'en',
        'show_name': 'Suits',
        'episode_name': 'S01E01'
    }
)

job_id = response.json()['job_id']

# Check status
status_response = requests.get(f'http://localhost:8000/api/v1/jobs/{job_id}')
print(status_response.json())
```

### JavaScript SDK

```javascript
// Submit job
const formData = new FormData();
formData.append('video_file', videoFile);
formData.append('subtitle_file', subtitleFile);
formData.append('language_code', 'en');

const response = await fetch('/api/v1/jobs', {
  method: 'POST',
  body: formData
});

const { job_id } = await response.json();

// Check status
const statusResponse = await fetch(`/api/v1/jobs/${job_id}`);
const status = await statusResponse.json();
console.log(status);
```

---

## Testing

### Test API Endpoints

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test job submission
curl -X POST http://localhost:8000/api/v1/jobs \
  -F "video_file=@test.mp4" \
  -F "subtitle_file=@test.srt"

# Test job status
curl http://localhost:8000/api/v1/jobs/{job_id}
```

### API Documentation

Visit `http://localhost:8000/docs` for interactive API documentation with:
- Endpoint descriptions
- Request/response schemas
- Try-it-out functionality
- Authentication examples
