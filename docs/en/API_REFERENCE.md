# LangFlix API Reference

**Version:** 2.0  
**Last Updated:** October 21, 2025

## Overview

The LangFlix API provides RESTful endpoints for video processing, job management, and result retrieval. The API is built with FastAPI and provides automatic OpenAPI documentation.

**✅ Phase 1 Complete**: All video processing features are now available via API endpoints.

## Base URL

```
http://localhost:8000
```

## Authentication

Currently, the API does not require authentication. Authentication will be added in Phase 2.

## Interactive Documentation

Visit `http://localhost:8000/docs` for interactive API documentation with Swagger UI.

## API Endpoints

### Health Check

#### GET /health

Check the health status of the API service.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-21T10:00:00Z",
  "service": "LangFlix API",
  "version": "1.0.0"
}
```

#### GET /health/detailed

Get detailed health status including component status.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2025-10-21T10:00:00Z",
  "components": {
    "database": "healthy",
    "storage": "healthy",
    "llm": "healthy"
  }
}
```

### Job Management

#### POST /api/v1/jobs

Create a new video processing job.

**Request:**
- Content-Type: `multipart/form-data`
- Parameters:
  - `video_file`: Video file (MP4, MKV, AVI)
  - `subtitle_file`: Subtitle file (SRT, VTT)
  - `language_code`: Language code (e.g., "en", "ko")
  - `show_name`: Name of the TV show
  - `episode_name`: Name of the episode
  - `max_expressions`: Maximum number of expressions (default: 10)
  - `language_level`: Proficiency level (beginner, intermediate, advanced, mixed)
  - `test_mode`: Enable test mode (default: false)
  - `no_shorts`: Skip short video generation (default: false)

**Response:**
```json
{
  "job_id": "uuid",
  "status": "PENDING",
  "progress": 0,
  "created_at": "2025-10-21T10:00:00Z"
}
```

#### GET /api/v1/jobs/{job_id}

Get the status of a processing job.

**Response:**
```json
{
  "job_id": "uuid",
  "status": "PROCESSING",
  "progress": 75,
  "created_at": "2025-10-21T10:00:00Z",
  "started_at": "2025-10-21T10:01:00Z",
  "completed_at": null,
  "error_message": null
}
```

**Status Values:**
- `PENDING`: Job created, not started
- `PROCESSING`: Currently processing
- `COMPLETED`: Successfully finished
- `FAILED`: Encountered error

#### GET /api/v1/jobs/{job_id}/expressions

Get expressions for a completed job.

**Response:**
```json
{
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

#### GET /api/v1/jobs

List jobs with optional filtering.

**Query Parameters:**
- `status`: Filter by job status
- `limit`: Maximum number of jobs (default: 50)
- `offset`: Number of jobs to skip (default: 0)

**Response:**
```json
[
  {
    "job_id": "uuid",
    "status": "COMPLETED",
    "progress": 100,
    "created_at": "2025-10-21T10:00:00Z",
    "started_at": "2025-10-21T10:01:00Z",
    "completed_at": "2025-10-21T10:05:00Z",
    "error_message": null
  }
]
```

### File Management

#### GET /api/v1/files/{file_id}

Download a file by ID.

**Response:**
- File content (binary)

#### GET /api/v1/files

List files with optional filtering.

**Query Parameters:**
- `job_id`: Filter by job ID
- `file_type`: Filter by file type

**Response:**
```json
{
  "files": [
    {
      "file_id": "uuid",
      "job_id": "uuid",
      "file_type": "video",
      "filename": "context_video.mkv",
      "size": 1024000,
      "created_at": "2025-10-21T10:00:00Z"
    }
  ]
}
```

#### DELETE /api/v1/files/{file_id}

Delete a file by ID.

**Response:**
```json
{
  "message": "File deleted successfully"
}
```

## Error Handling

The API uses standard HTTP status codes and returns error information in a consistent format.

### Error Response Format

```json
{
  "error": "ErrorType",
  "message": "Human-readable error message",
  "details": {
    "additional": "error details"
  }
}
```

### Common Error Codes

- `400 Bad Request`: Invalid request parameters
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Processing error
- `500 Internal Server Error`: Server error

## API Documentation

Interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Examples

### Creating a Job

```bash
curl -X POST "http://localhost:8000/api/v1/jobs" \
  -F "video_file=@video.mp4" \
  -F "subtitle_file=@subtitles.srt" \
  -F "language_code=en" \
  -F "show_name=Suits" \
  -F "episode_name=S01E01"
```

### Checking Job Status

```bash
curl -X GET "http://localhost:8000/api/v1/jobs/{job_id}"
```

### Getting Job Results

```bash
curl -X GET "http://localhost:8000/api/v1/jobs/{job_id}/expressions"
```

## Rate Limiting

Currently, there are no rate limits. Rate limiting will be implemented in Phase 2.

## Versioning

The API uses URL versioning. The current version is v1.

## Support

For API support and questions, please refer to the main documentation or create an issue in the repository.
