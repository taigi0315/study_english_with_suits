# LangFlix Runbook

**Version:** 1.0  
**Last Updated:** October 21, 2025

This runbook provides comprehensive operational guidance for running LangFlix in both CLI and API modes.

---

## Table of Contents

1. [Overview](#overview)
2. [Quick Start](#quick-start)
3. [CLI Mode](#cli-mode)
4. [API Mode](#api-mode)
5. [Configuration](#configuration)
6. [Storage Backends](#storage-backends)
7. [Database Integration](#database-integration)
8. [Monitoring & Health Checks](#monitoring--health-checks)
9. [Troubleshooting](#troubleshooting)
10. [Deployment](#deployment)

---

## Overview

LangFlix supports two operational modes:

### CLI Mode (Development/Local)
- **Purpose**: Local development, testing, single-user processing
- **Storage**: Local filesystem (`output/` directory)
- **Database**: Optional (metadata storage)
- **Usage**: Command-line interface for direct video processing

### API Mode (Production/Cloud)
- **Purpose**: Web service, multi-user access, scalable processing
- **Storage**: Google Cloud Storage (configurable)
- **Database**: Required (job tracking, metadata)
- **Usage**: RESTful API for asynchronous video processing

---

## Quick Start

### CLI Mode
```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment
cp env.example .env
# Edit .env and add your API key

# Run CLI
python -m langflix.main --video-dir /path/to/video --subtitle /path/to/subtitle.srt
```

### API Mode
```bash
# Install dependencies
pip install -r requirements.txt

# Configure database and storage
# Edit langflix/config/default.yaml

# Start API server
uvicorn langflix.api.main:app --host 0.0.0.0 --port 8000
```

---

## CLI Mode

### Basic Usage

```bash
# Basic processing
python -m langflix.main \
  --video-dir /path/to/video/directory \
  --subtitle /path/to/subtitle.srt \
  --language en

# With test mode (faster processing)
python -m langflix.main \
  --video-dir /path/to/video/directory \
  --subtitle /path/to/subtitle.srt \
  --language en \
  --test

# Skip short video generation
python -m langflix.main \
  --video-dir /path/to/video/directory \
  --subtitle /path/to/subtitle.srt \
  --language en \
  --no-shorts
```

### CLI Configuration

**Environment Variables:**
```bash
# Required
GEMINI_API_KEY=your_gemini_api_key_here

# Optional
LANGFLIX_CONFIG_PATH=/path/to/custom/config.yaml
```

**Configuration File (`langflix/config/default.yaml`):**
```yaml
# Application settings
app:
  show_name: "Suits"
  template_file: "expression_analysis_prompt.txt"

# Database (optional for CLI)
database:
  enabled: false  # Set to true to enable database integration
  url: "postgresql://user:password@localhost:5432/langflix"

# Storage (CLI uses local by default)
storage:
  backend: "local"
  local:
    base_path: "output"
```

### CLI Output Structure

```
output/
├── Suits/
│   └── S01E01_720p.HDTV.x264/
│       ├── metadata/
│       │   └── expressions.json
│       ├── shared/
│       │   ├── context_videos/
│       │   ├── context_slide_combined/
│       │   └── short_videos/
│       └── translations/
│           └── ko/
│               ├── subtitles/
│               ├── slides/
│               └── audio/
```

---

## API Mode

### Starting the API Server

```bash
# Development mode
uvicorn langflix.api.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn langflix.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### API Endpoints

#### Health Check
```bash
# Basic health check
curl http://localhost:8000/health

# Detailed health check
curl http://localhost:8000/health/detailed
```

#### Job Management
```bash
# Create processing job
curl -X POST "http://localhost:8000/api/v1/jobs" \
  -F "video_file=@video.mp4" \
  -F "subtitle_file=@subtitles.srt" \
  -F "language_code=en" \
  -F "show_name=Suits" \
  -F "episode_name=S01E01"

# Check job status
curl http://localhost:8000/api/v1/jobs/{job_id}

# Get job results
curl http://localhost:8000/api/v1/jobs/{job_id}/expressions

# List all jobs
curl http://localhost:8000/api/v1/jobs
```

### API Configuration

**Required Environment Variables:**
```bash
# API Key
GEMINI_API_KEY=your_gemini_api_key_here

# Database (required for API)
DATABASE_URL=postgresql://user:password@localhost:5432/langflix

# Storage (GCS for production)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

**API Configuration (`langflix/config/default.yaml`):**
```yaml
# Database (required for API)
database:
  enabled: true
  url: "postgresql://user:password@localhost:5432/langflix"

# Storage (GCS for API)
storage:
  backend: "gcs"
  gcs:
    bucket_name: "langflix-storage"
    credentials_path: "/path/to/service-account.json"

# API settings
api:
  host: "0.0.0.0"
  port: 8000
  workers: 4
  cors_origins: ["*"]
```

---

## Storage Backends

### LocalStorage (CLI Default)
- **Purpose**: Local development, CLI usage
- **Configuration**: `storage.backend: "local"`
- **Files**: Stored in `output/` directory
- **URLs**: Local file paths

### GoogleCloudStorage (API Default)
- **Purpose**: Production, cloud storage
- **Configuration**: `storage.backend: "gcs"`
- **Files**: Stored in GCS bucket
- **URLs**: Public GCS URLs

**GCS Setup:**
```bash
# Create GCS bucket
gsutil mb gs://your-langflix-bucket

# Set up service account
# 1. Create service account in Google Cloud Console
# 2. Download JSON key file
# 3. Set GOOGLE_APPLICATION_CREDENTIALS environment variable
```

---

## Database Integration

### Database Setup

**PostgreSQL Installation:**
```bash
# macOS
brew install postgresql
brew services start postgresql

# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql
```

**Database Creation:**
```sql
CREATE DATABASE langflix;
CREATE USER langflix_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE langflix TO langflix_user;
```

**Migration:**
```bash
# Run database migrations
alembic upgrade head
```

### Database Models

**Media Table:**
- `id`: Unique identifier
- `show_name`: TV show name
- `episode_name`: Episode identifier
- `language_code`: Language code (en, ko, etc.)
- `subtitle_file_path`: Path to subtitle file
- `video_file_path`: Path to video file
- `created_at`: Creation timestamp

**Expression Table:**
- `id`: Unique identifier
- `media_id`: Foreign key to Media
- `expression`: The English expression
- `translation`: Translation text
- `dialogue`: Full dialogue context
- `similar_expressions`: JSON array of similar expressions
- `context_start_time`: Start time in seconds
- `context_end_time`: End time in seconds

**ProcessingJob Table:**
- `id`: Unique identifier
- `media_id`: Foreign key to Media
- `status`: PENDING, PROCESSING, COMPLETED, FAILED
- `job_type`: Type of processing job
- `started_at`: Processing start time
- `completed_at`: Processing completion time
- `error_message`: Error details if failed

---

## Monitoring & Health Checks

### CLI Monitoring

**Log Files:**
```bash
# Check processing logs
tail -f langflix.log

# Check for errors
grep ERROR langflix.log
```

**Output Verification:**
```bash
# Check if files were created
ls -la output/ShowName/EpisodeName/

# Verify video files
ffprobe output/ShowName/EpisodeName/shared/context_videos/*.mkv
```

### API Monitoring

**Health Endpoints:**
```bash
# Basic health
curl http://localhost:8000/health

# Detailed health (checks database, storage, LLM)
curl http://localhost:8000/health/detailed
```

**API Documentation:**
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

**Logging:**
```bash
# API logs
tail -f logs/api.log

# Database logs
tail -f logs/database.log
```

---

## Troubleshooting

### Common CLI Issues

**Problem**: `ModuleNotFoundError: No module named 'langflix'`
```bash
# Solution: Install in development mode
pip install -e .
```

**Problem**: `ffmpeg not found`
```bash
# Solution: Install ffmpeg
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg
```

**Problem**: `GEMINI_API_KEY not found`
```bash
# Solution: Set environment variable
export GEMINI_API_KEY=your_api_key_here
# Or add to .env file
```

### Common API Issues

**Problem**: `Database connection failed`
```bash
# Solution: Check database configuration
# 1. Verify PostgreSQL is running
# 2. Check connection string in config
# 3. Run migrations: alembic upgrade head
```

**Problem**: `Storage backend error`
```bash
# Solution: Check storage configuration
# 1. Verify GCS credentials
# 2. Check bucket permissions
# 3. Test with LocalStorage first
```

**Problem**: `Job stuck in PROCESSING status`
```bash
# Solution: Check background task logs
# 1. Check API logs for errors
# 2. Verify database connection
# 3. Check storage backend access
```

### Performance Issues

**Slow Processing:**
- Use `--test` flag for faster processing
- Check available disk space
- Verify API key quota limits

**Memory Issues:**
- Process shorter video segments
- Increase system memory
- Use test mode for development

---

## Deployment

### CLI Deployment

**Local Development:**
```bash
# Clone repository
git clone https://github.com/your-repo/langflix.git
cd langflix

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp env.example .env
# Edit .env with your API key

# Run processing
python -m langflix.main --help
```

### API Deployment

**Docker Deployment:**
```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "langflix.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Environment Variables:**
```bash
# Required
GEMINI_API_KEY=your_api_key
DATABASE_URL=postgresql://user:password@db:5432/langflix
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# Optional
LANGFLIX_CONFIG_PATH=/app/config/production.yaml
```

**Production Configuration:**
```yaml
# production.yaml
database:
  enabled: true
  url: "${DATABASE_URL}"
  pool_size: 10
  max_overflow: 20

storage:
  backend: "gcs"
  gcs:
    bucket_name: "langflix-production"
    credentials_path: "${GOOGLE_APPLICATION_CREDENTIALS}"

api:
  host: "0.0.0.0"
  port: 8000
  workers: 4
  cors_origins: ["https://yourdomain.com"]
```

---

## Security Considerations

### API Security
- **Authentication**: Implement in Phase 2
- **Rate Limiting**: Add in Phase 2
- **Input Validation**: Already implemented
- **CORS**: Configure for production domains

### Data Security
- **API Keys**: Store in environment variables
- **Database**: Use connection pooling
- **Storage**: Use service account authentication
- **Logs**: Avoid logging sensitive data

---

## Support

### Documentation
- **User Manual**: `docs/en/USER_MANUAL.md`
- **API Reference**: `docs/en/API_REFERENCE.md`
- **Troubleshooting**: `docs/en/TROUBLESHOOTING.md`

### Getting Help
- **Issues**: Create GitHub issue
- **Logs**: Include relevant log files
- **Configuration**: Share sanitized config files

---

## Version History

- **v1.0**: Initial release with CLI and API support
- **v1.1**: Added short video generation
- **v1.2**: Added Gemini TTS integration
- **v1.3**: Added storage abstraction layer
- **v1.4**: Added database integration
- **v1.5**: Added FastAPI application scaffold
