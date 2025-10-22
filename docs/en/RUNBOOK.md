# LangFlix Runbook

**Version:** 2.0  
**Last Updated:** October 21, 2025

This runbook provides comprehensive operational guidance for running LangFlix API service.

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [API Service](#api-service)
4. [Configuration](#configuration)
5. [Storage Backends](#storage-backends)
6. [Database Integration](#database-integration)
7. [Monitoring & Health Checks](#monitoring--health-checks)
8. [Troubleshooting](#troubleshooting)
9. [Deployment](#deployment)

---

## Overview

LangFlix is now a **FastAPI-based web service** that provides:

### API-First Architecture
- **Purpose**: Web service, multi-user access, scalable processing
- **Storage**: Local filesystem (default) or Google Cloud Storage (configurable)
- **Database**: Required (job tracking, metadata, user management)
- **Usage**: RESTful API for asynchronous video processing
- **Background Processing**: Long-running video processing tasks
- **Job Management**: Real-time progress tracking and status monitoring

### Key Features
- ✅ **RESTful API**: Complete video processing via HTTP endpoints
- ✅ **Background Tasks**: Asynchronous processing with job tracking
- ✅ **Modular Architecture**: Clean separation of concerns
- ✅ **Production Ready**: Tested with multiple episodes (S01E01-S01E06)
- ✅ **Scalable**: Designed for cloud deployment

---

## Quick Start

### 1. Setup
```bash
# Clone repository
git clone <repository-url>
cd langflix

# Setup environment
make setup

# Or manually:
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Start API Server
```bash
# Start API server
make api

# Or manually:
uvicorn langflix.api.main:app --host 127.0.0.1 --port 8000 --reload
```

### 3. Test API
```bash
# Health check
curl http://127.0.0.1:8000/health

# API documentation
open http://127.0.0.1:8000/docs
```

### 4. Process Video
```bash
# Upload video and subtitle for processing
curl -X POST "http://127.0.0.1:8000/api/v1/jobs" \
  -F "video_file=@path/to/video.mkv" \
  -F "subtitle_file=@path/to/subtitle.srt" \
  -F "language_code=ko" \
  -F "show_name=Suits" \
  -F "episode_name=S01E01" \
  -F "max_expressions=3" \
  -F "language_level=intermediate"
```

### 5. Check Job Status
```bash
# Get job status
curl "http://127.0.0.1:8000/api/v1/jobs/{job_id}"

# List all jobs
curl "http://127.0.0.1:8000/api/v1/jobs"
```

---

## API Service

### Endpoints

#### Health Check
```bash
GET /health
```
Returns service health status.

#### Create Job
```bash
POST /api/v1/jobs
```
Upload video and subtitle files for processing.

**Parameters:**
- `video_file`: Video file (MKV, MP4, AVI)
- `subtitle_file`: Subtitle file (SRT)
- `language_code`: Target language (ko, en, etc.)
- `show_name`: Series name
- `episode_name`: Episode identifier
- `max_expressions`: Maximum expressions to extract (default: 3)
- `language_level`: Difficulty level (beginner, intermediate, advanced)
- `test_mode`: Enable test mode (optional)
- `no_shorts`: Skip short video generation (optional)

#### Get Job Status
```bash
GET /api/v1/jobs/{job_id}
```
Returns job status and progress.

#### List Jobs
```bash
GET /api/v1/jobs
```
Returns list of all jobs.

### Job States
- `PENDING`: Job created, waiting to start
- `PROCESSING`: Currently processing
- `COMPLETED`: Successfully completed
- `FAILED`: Processing failed

### Output Structure
```
output/
└── {show_name}/
    └── {episode_name}/
        ├── context_videos/          # Context clips
        ├── slides/                  # Educational slides
        ├── tts_audio/              # TTS audio files
        ├── final_videos/           # Final educational video
        ├── short_videos/           # Short-form videos
        ├── context_slide_combined/  # Individual short videos
        └── subtitles/              # Subtitle files
```

---

## Configuration

### Environment Variables
```bash
# Copy example environment file
cp env.example .env

# Edit .env file
GEMINI_API_KEY=your_gemini_api_key
DATABASE_URL=sqlite:///./langflix.db
STORAGE_TYPE=local  # or gcs
```

### Configuration File
Edit `langflix/config/default.yaml`:

```yaml
# API Configuration
api:
  host: "127.0.0.1"
  port: 8000
  debug: false

# Database Configuration
database:
  url: "sqlite:///./langflix.db"
  echo: false

# Storage Configuration
storage:
  type: "local"  # or "gcs"
  local:
    base_path: "./output"
  gcs:
    bucket_name: "your-bucket"
    project_id: "your-project"

# TTS Configuration
tts:
  provider: "gemini"  # or "google", "lemonfox"
  gemini:
    api_key: "${GEMINI_API_KEY}"
```

---

## Storage Backends

### Local Storage (Default)
```yaml
storage:
  type: "local"
  local:
    base_path: "./output"
```

### Google Cloud Storage
```yaml
storage:
  type: "gcs"
  gcs:
    bucket_name: "your-langflix-bucket"
    project_id: "your-gcp-project"
    credentials_path: "/path/to/service-account.json"
```

---

## Database Integration

### SQLite (Development)
```bash
# Default SQLite database
DATABASE_URL=sqlite:///./langflix.db
```

### PostgreSQL (Production)
```bash
# PostgreSQL database
DATABASE_URL=postgresql://user:password@localhost/langflix
```

### Database Migrations
```bash
# Run migrations
make db-migrate

# Reset database
make db-reset
```

---

## Monitoring & Health Checks

### Health Endpoint
```bash
curl http://127.0.0.1:8000/health
```

### Job Monitoring
```bash
# Check job status
curl "http://127.0.0.1:8000/api/v1/jobs/{job_id}"

# Monitor all jobs
curl "http://127.0.0.1:8000/api/v1/jobs"
```

### Logs
```bash
# View API logs
tail -f logs/api.log

# View processing logs
tail -f logs/processing.log
```

---

## Troubleshooting

### Common Issues

#### 1. Port Already in Use
```bash
# Error: [Errno 48] Address already in use
# Solution: Kill existing process or use different port
lsof -ti:8000 | xargs kill -9
# Or use different port:
uvicorn langflix.api.main:app --host 127.0.0.1 --port 8001
```

#### 2. Database Connection Issues
```bash
# Check database connection
python -c "from langflix.db.session import engine; print('Database connected')"

# Reset database
make db-reset
```

#### 3. Storage Issues
```bash
# Check storage configuration
python -c "from langflix.storage.factory import get_storage; print('Storage configured')"

# Test storage access
python -c "from langflix.storage.local import LocalStorage; storage = LocalStorage(); print('Storage working')"
```

#### 4. API Key Issues
```bash
# Check API key configuration
python -c "from langflix.core.expression_analyzer import analyze_chunk; print('API key configured')"
```

### Debug Mode
```bash
# Start with debug logging
make dev

# Or manually:
uvicorn langflix.api.main:app --host 127.0.0.1 --port 8000 --reload --log-level debug
```

---

## Deployment

### Development
```bash
# Local development
make dev
```

### Production
```bash
# Production deployment
uvicorn langflix.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Docker
```bash
# Build Docker image
docker build -t langflix-api .

# Run container
docker run -p 8000:8000 -e GEMINI_API_KEY=your_key langflix-api
```

### Cloud Deployment
See `docs/en/DEPLOYMENT.md` for detailed cloud deployment instructions.

---

## Makefile Commands

```bash
make setup     # Setup virtual environment and install dependencies
make api       # Start API server
make dev       # Start API server in development mode
make test      # Run all tests
make test-unit # Run unit tests only
make test-functional # Run functional tests only
make test-api  # Run API tests only
make db-migrate # Run database migrations
make db-reset  # Reset database
make clean     # Clean up generated files
make help      # Show help message
```

---

## Support

For additional support:
- Check the troubleshooting section above
- Review logs in the `logs/` directory
- Check API documentation at `http://127.0.0.1:8000/docs`
- Review the API Reference in `docs/en/API_REFERENCE.md`