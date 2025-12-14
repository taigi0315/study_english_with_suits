# Deployment Guide

## Overview

LangFlix can be deployed using Docker on any Linux server or TrueNAS.

---

## Docker Deployment

### Prerequisites
- Docker and Docker Compose
- API keys configured in `.env`

### Quick Deploy

```bash
# Build images
make docker-build

# Start services
make docker-up

# View logs
make docker-logs
```

### Services

| Service | Port | Description |
|---------|------|-------------|
| API | 8000 | FastAPI backend |
| Frontend | 5000 | Flask web UI |
| Redis | 6379 | Job queue |
| PostgreSQL | 5432 | Database (optional) |

---

## TrueNAS Deployment

### Setup Steps

1. **Build for TrueNAS:**
```bash
make docker-build-truenas
```

2. **Start services:**
```bash
make docker-up-truenas
```

3. **View logs:**
```bash
make docker-logs-truenas
```

### SSH Access for CI/CD

See [CI_CD_SSH_SETUP.md](CI_CD_SSH_SETUP.md) for GitHub Actions SSH setup.

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | Google Gemini API key |
| `REDIS_URL` | No | Redis connection string |
| `DATABASE_URL` | No | PostgreSQL connection |
| `DATABASE_ENABLED` | No | Enable DB (default: false) |

---

## Deployment Bundle

Create a minimal deployment package:

```bash
# Basic bundle
make deploy-zip

# With documentation
make deploy-zip INCLUDE_DOCS=1

# With media files
make deploy-zip INCLUDE_MEDIA=1
```

---

## Health Checks

```bash
# API health
curl http://localhost:8000/health

# Service status
make status
```

---

## Production Checklist

- [ ] Set `GEMINI_API_KEY` in production `.env`
- [ ] Configure Redis for job queue
- [ ] Set up log rotation
- [ ] Configure backups for output directory
- [ ] Set appropriate resource limits in Docker
