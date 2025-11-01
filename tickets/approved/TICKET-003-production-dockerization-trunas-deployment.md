# [TICKET-003] Production Dockerization & TrueNAS Deployment Pipeline

## Priority
- [ ] Critical (System stability, security, data loss risk)
- [x] High (Performance issues, significant tech debt)
- [ ] Medium (Code quality, maintainability improvements)
- [ ] Low (Nice-to-have refactorings)

## Type
- [ ] Refactoring
- [ ] Performance Optimization
- [ ] Test Coverage
- [ ] Bug Fix
- [ ] Security Issue
- [ ] Technical Debt
- [x] Infrastructure & DevOps

## Impact Assessment
**Business Impact:**
- 일관된 배포 환경 필요
- TrueNAS 배포 표준화
- 운영 안정성 향상
- CI/CD 파이프라인으로 개발 효율 증대

**Technical Impact:**
- 영향받는 모듈: 전체 인프라
- 예상 변경 파일: 15-20개
- 빌드, 테스트, 배포 파이프라인 구축

**Effort Estimate:**
- Large (> 3 days)

## Problem Description

### Current State
**Location:** `deploy/` directory and Dockerfile files

프로덕션 배포가 불완전합니다:

1. **EC2 전용 Docker Compose**
   - `deploy/docker-compose.ec2.yml` - EC2 용도, TrueNAS 미고려
   - 개발용만 `docker-compose.dev.yml` 존재
   - `Dockerfile.ec2` - 기본 설정
   - `Dockerfile.dev` - 개발용

2. **CI/CD 부재**
   - GitHub Actions 없음
   - 자동화 빌드/테스트/배포 없음
   - 릴리스 절차 수동

3. **로컬 배포 프로세스 불충분**
   - `deploy/ec2-setup.sh` - EC2용 스크립트
   - TrueNAS 매뉴얼 없음
   - 헬스 체크 부족
   - 모니터링 미구현
   - 로그 관리 표준 없음

4. **보안 취약**
   - root 권한 사용
   - 비밀 관리 방식 약함
   - 이미지 스캔 부재
   - 네트워크 보안 미검토

### Root Cause Analysis
- 초기 개발이며 운영화 미구현
- 환경별 구성 누락
- CI/CD 우선순위 낮음

### Evidence
- `deploy/Dockerfile.ec2`: 프로덕션용이지만 TrueNAS 미고려
- `deploy/docker-compose.ec2.yml`: 하드코딩 및 설정 부족
- `.github/`: CI/CD 구성 파일 없음
- 테스트는 `run_tests.py`로 수동

## Proposed Solution

### Approach
1. 멀티스테이지 Docker 이미지
2. 환경별 Docker Compose
3. GitHub Actions CI/CD
4. 보안 강화(비루트 사용자, 비밀 관리, 이미지 스캔)
5. 헬스체크/모니터링
6. TrueNAS 배포 가이드

### Implementation Details

#### Step 1: Production Dockerfile 작성
`Dockerfile` 생성 (Multi-stage):

```dockerfile
# ============================================================================
# LangFlix Production Dockerfile (Multi-stage Build)
# ============================================================================

# ----------------------------------------------------------------------------
# Stage 1: Builder - Install dependencies and build application
# ----------------------------------------------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /app

# Install system dependencies for building
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies to a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r requirements.txt

# ----------------------------------------------------------------------------
# Stage 2: Runtime - Lightweight production image
# ----------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash langflix && \
    mkdir -p /app /data/output /data/logs /data/assets && \
    chown -R langflix:langflix /app /data

WORKDIR /app
USER langflix

# Copy application code
COPY --chown=langflix:langflix . .

# Expose ports
EXPOSE 8000 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["python", "-m", "langflix.api.main"]

# ----------------------------------------------------------------------------
# Stage 3: CLI - For command-line usage
# ----------------------------------------------------------------------------
FROM runtime AS cli
CMD ["python", "-m", "langflix.main", "--help"]

# ----------------------------------------------------------------------------
# Stage 4: API - For API server
# ----------------------------------------------------------------------------
FROM runtime AS api
CMD ["python", "-m", "langflix.api.main"]

# ----------------------------------------------------------------------------
# Stage 5: Celery Worker - For background tasks
# ----------------------------------------------------------------------------
FROM runtime AS celery-worker
CMD ["celery", "-A", "langflix.tasks.celery_app", "worker", "--loglevel=info"]
```

#### Step 2: TrueNAS Docker Compose
`deploy/docker-compose.truenas.yml` 생성:

```yaml
version: '3.8'

services:
  # LangFlix API Server
  langflix-api:
    build:
      context: ..
      dockerfile: Dockerfile
      target: api
    container_name: langflix-api
    restart: unless-stopped
    
    # Environment variables
    environment:
      # API Settings
      - LANGFLIX_HOST=0.0.0.0
      - LANGFLIX_PORT=8000
      - LANGFLIX_WORKERS=4
      
      # Database
      - DATABASE_URL=postgresql://langflix:${POSTGRES_PASSWORD}@postgres:5432/langflix
      - LANGFLIX_DATABASE_ENABLED=true
      
      # Redis
      - REDIS_URL=redis://redis:6379/0
      
      # APIs
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - GOOGLE_API_KEY_1=${GOOGLE_API_KEY_1}
      - LEMONFOX_API_KEY=${LEMONFOX_API_KEY}
      
      # Paths
      - LANGFLIX_OUTPUT_DIR=/data/output
      - LANGFLIX_ASSETS_DIR=/data/assets
      - LANGFLIX_LOG_DIR=/data/logs
      
      # Logging
      - LANGFLIX_LOG_LEVEL=${LOG_LEVEL:-INFO}
      
    # Ports
    ports:
      - "${API_PORT:-8000}:8000"
    
    # Volumes (TrueNAS mount points)
    volumes:
      # Persistent data
      - ${TRUENAS_DATA_MOUNT}/langflix/output:/data/output:rw
      - ${TRUENAS_DATA_MOUNT}/langflix/assets:/data/assets:ro
      - ${TRUENAS_DATA_MOUNT}/langflix/logs:/data/logs:rw
      - ${TRUENAS_DATA_MOUNT}/langflix/cache:/app/cache:rw
      
      # Configuration (read-only)
      - ../config.yaml:/app/config.yaml:ro
      - ../.env:/app/.env:ro
    
    # Dependencies
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    
    # Resource limits
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
        reservations:
          cpus: '2'
          memory: 4G
    
    # Health check
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      start_period: 60s
      retries: 3

  # LangFlix Frontend Server  
  langflix-frontend:
    build:
      context: ..
      dockerfile: Dockerfile
      target: cli
    container_name: langflix-frontend
    restart: unless-stopped
    
    environment:
      - FLASK_ENV=production
      - FLASK_PORT=5000
    
    ports:
      - "${FRONTEND_PORT:-5000}:5000"
    
    volumes:
      - ${TRUENAS_DATA_MOUNT}/langflix/output:/data/output:ro
      - ../config.yaml:/app/config.yaml:ro
    
    depends_on:
      - langflix-api
    
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G

  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    container_name: langflix-postgres
    restart: unless-stopped
    
    environment:
      - POSTGRES_USER=langflix
      - POSTGRES_DB=langflix
      - POSTGRES_PASSWORD_FILE=/run/secrets/postgres_password
      - PGDATA=/var/lib/postgresql/data/pgdata
    
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ${TRUENAS_DATA_MOUNT}/langflix/db-backups:/backups:rw
    
    secrets:
      - postgres_password
    
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U langflix -d langflix"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis Cache
  redis:
    image: redis:7-alpine
    container_name: langflix-redis
    restart: unless-stopped
    
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    
    volumes:
      - redis_data:/data
    
    healthcheck:
      test: ["CMD", "redis-cli", "--raw", "incr", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Celery Worker (Background Processing)
  celery-worker:
    build:
      context: ..
      dockerfile: Dockerfile
      target: celery-worker
    container_name: langflix-celery-worker
    restart: unless-stopped
    
    environment:
      - DATABASE_URL=postgresql://langflix:${POSTGRES_PASSWORD}@postgres:5432/langflix
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - LANGFLIX_OUTPUT_DIR=/data/output
      - CELERY_BROKER_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - CELERY_RESULT_BACKEND=redis://:${REDIS_PASSWORD}@redis:6379/0
    
    volumes:
      - ${TRUENAS_DATA_MOUNT}/langflix/output:/data/output:rw
      - ${TRUENAS_DATA_MOUNT}/langflix/assets:/data/assets:ro
      - ../config.yaml:/app/config.yaml:ro
    
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      langflix-api:
        condition: service_healthy
    
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
    
    # Scale workers
    # docker-compose up --scale celery-worker=3

  # Celery Beat (Scheduled Tasks)
  celery-beat:
    build:
      context: ..
      dockerfile: Dockerfile
      target: celery-worker
    container_name: langflix-celery-beat
    restart: unless-stopped
    
    command: celery -A langflix.tasks.celery_app beat --loglevel=info
    
    environment:
      - DATABASE_URL=postgresql://langflix:${POSTGRES_PASSWORD}@postgres:5432/langflix
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - CELERY_BROKER_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - CELERY_RESULT_BACKEND=redis://:${REDIS_PASSWORD}@redis:6379/0
    
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  # Flower (Celery Monitoring)
  flower:
    build:
      context: ..
      dockerfile: Dockerfile
      target: celery-worker
    container_name: langflix-flower
    restart: unless-stopped
    
    command: celery -A langflix.tasks.celery_app flower --port=5555
    
    environment:
      - CELERY_BROKER_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - CELERY_RESULT_BACKEND=redis://:${REDIS_PASSWORD}@redis:6379/0
    
    ports:
      - "${FLOWER_PORT:-5555}:5555"
    
    depends_on:
      - redis

# Named volumes for container-managed data
volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local

# Docker secrets for sensitive data
secrets:
  postgres_password:
    external: true
  gemini_api_key:
    external: true
```

#### Step 3: Docker secrets 관리
`.docker/secrets/` 디렉토리 생성 및 가이드:

```bash
# .docker/secrets/README.md
# Create Docker secrets before starting services:

docker secret create postgres_password /path/to/secrets/postgres_password.txt
docker secret create redis_password /path/to/secrets/redis_password.txt
docker secret create gemini_api_key /path/to/secrets/gemini_api_key.txt

# Or use environment file
docker secret create --from-env-file langflix_env .env
```

#### Step 4: GitHub Actions CI/CD
`.github/workflows/` 디렉토리 생성:

```yaml
# .github/workflows/ci.yml
name: CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

env:
  PYTHON_VERSION: '3.11'
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}

jobs:
  lint:
    name: Code Linting
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install flake8 black isort mypy
          pip install -r requirements.txt
      
      - name: Lint with flake8
        run: flake8 langflix/ tests/ --count --select=E9,F63,F7,F82 --show-source --statistics
      
      - name: Check formatting with black
        run: black --check langflix/ tests/
      
      - name: Check import sorting
        run: isort --check-only langflix/ tests/
      
      - name: Type check with mypy
        run: mypy langflix/ --ignore-missing-imports

  test:
    name: Run Tests
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_langflix
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
      
      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379
    
    strategy:
      matrix:
        test-type: [unit, integration, functional]
      fail-fast: false
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
      
      - name: Install system dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y ffmpeg
      
      - name: Cache pip packages
        uses: actions/cache@v3
        with:
          path: ~/.cache/pip
          key: ${{ runner.os }}-pip-${{ hashFiles('requirements.txt') }}
          restore-keys: |
            ${{ runner.os }}-pip-
      
      - name: Install Python dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-cov pytest-asyncio
      
      - name: Run tests
        env:
          GEMINI_API_KEY: ${{ secrets.GEMINI_API_KEY }}
          DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_langflix
          REDIS_URL: redis://localhost:6379/0
        run: |
          pytest tests/${{ matrix.test-type }}/ -v --cov=langflix --cov-report=xml --cov-report=term
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          flags: ${{ matrix.test-type }}
          name: ${{ matrix.test-type }}-coverage

  build-and-push:
    name: Build and Push Docker Images
    needs: [lint, test]
    runs-on: ubuntu-latest
    if: github.event_name == 'push'
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3
      
      - name: Log in to Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=ref,event=pr
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=sha,prefix={{branch}}-
      
      - name: Build and push API image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: Dockerfile
          target: api
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
      
      - name: Build and push Frontend image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: Dockerfile
          target: cli
          push: true
          tags: ${{ steps.meta.outputs.tags }}-frontend
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
      
      - name: Build and push Worker image
        uses: docker/build-push-action@v5
        with:
          context: .
          file: Dockerfile
          target: celery-worker
          push: true
          tags: ${{ steps.meta.outputs.tags }}-worker
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  security-scan:
    name: Security Scan
    needs: build-and-push
    runs-on: ubuntu-latest
    if: github.event_name == 'push'
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:main-api
          format: 'sarif'
          output: 'trivy-results.sarif'
      
      - name: Upload Trivy results
        uses: github/codeql-action/upload-sarif@v2
        if: always()
        with:
          sarif_file: 'trivy-results.sarif'

  deploy:
    name: Deploy to TrueNAS
    needs: [build-and-push, security-scan]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main' && github.event_name == 'push'
    environment: production
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Deploy to TrueNAS
        uses: appleboy/ssh-action@master
        with:
          host: ${{ secrets.TRUNAS_HOST }}
          username: ${{ secrets.TRUNAS_USER }}
          key: ${{ secrets.TRUNAS_SSH_KEY }}
          script: |
            cd /mnt/pool/langflix/docker
            docker-compose pull
            docker-compose up -d
            docker system prune -af --volumes
            
  notify:
    name: Deployment Notification
    needs: [deploy]
    runs-on: ubuntu-latest
    if: always()
    
    steps:
      - name: Notify on success
        if: needs.deploy.result == 'success'
        run: |
          echo "✅ Deployment successful!"
      
      - name: Notify on failure
        if: needs.deploy.result == 'failure'
        run: |
          echo "❌ Deployment failed!"
```

#### Step 5: Docker Compose Override 전략
환경별 override 구성:

```yaml
# docker-compose.override.yml.example (for local development)
# This file should be copied to docker-compose.override.yml
version: '3.8'

services:
  langflix-api:
    volumes:
      - .:/app  # Mount code for live reload
    environment:
      - LANGFLIX_LOG_LEVEL=DEBUG
      - FLASK_ENV=development
    ports:
      - "8000:8000"
      - "5555:5555"  # Flower monitoring
```

#### Step 6: TrueNAS Deployment Guide
`docs/DEPLOYMENT_TRUENAS.md` 문서 작성:

```markdown
# TrueNAS Deployment Guide

## Prerequisites
- TrueNAS Scale or Core with Docker support
- SSH access to TrueNAS host
- Domain name (optional, for reverse proxy)

## Step 1: Prepare TrueNAS

### Create Dataset
1. Open TrueNAS Web UI
2. Storage → Pools → Add Dataset
3. Create dataset: `langflix`
4. Set up SMB share for easy file management

### Configure Network
1. Services → SSH → Enable
2. Configure static IP if needed
3. Open firewall ports: 8000 (API), 5000 (Frontend), 5432 (Postgres, optional)

## Step 2: Deploy Application

### Clone Repository
```bash
ssh admin@truenas
cd /mnt/pool/apps
git clone https://github.com/your-org/langflix.git
cd langflix
```

### Configure Environment
```bash
cp .env.example .env
nano .env  # Edit with your API keys
```

### Create Docker Secrets
```bash
docker secret create postgres_password /path/to/secrets/postgres.txt
docker secret create redis_password /path/to/secrets/redis.txt
```

### Start Services
```bash
cd deploy
docker-compose -f docker-compose.truenas.yml up -d
```

## Step 3: Post-Deployment

### Run Migrations
```bash
docker exec -it langflix-api alembic upgrade head
```

### Verify Services
```bash
docker ps
curl http://localhost:8000/health
```

### View Logs
```bash
docker-compose -f docker-compose.truenas.yml logs -f
```

## Step 4: Monitoring

### Flower Dashboard
Access: http://truenas-ip:5555

### Health Checks
```bash
docker exec langflix-api python -c "from langflix.monitoring import check_all; check_all()"
```

## Troubleshooting

### Check Resource Usage
```bash
docker stats
```

### Restart Failed Services
```bash
docker-compose -f docker-compose.truenas.yml restart
```

### View Service Logs
```bash
docker-compose -f docker-compose.truenas.yml logs langflix-api
```
```

#### Step 7: .dockerignore 추가
`.dockerignore` 생성:

```
# Git
.git
.gitignore
.github

# Python
__pycache__
*.pyc
*.pyo
*.pyd
.Python
*.so
*.egg
*.egg-info
dist
build

# Virtual Environment
venv/
.venv/
env/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Testing
.pytest_cache/
.coverage
htmlcov/
.tox/
.mypy_cache/

# Large files
assets/media/*
output/*
cache/*
*.mkv
*.mp4
*.mp3
*.wav

# Logs
*.log
logs/

# Environment
.env
.env.*
config.yaml

# Documentation
docs/
*.md
!README.md

# CI/CD
.github/

# OS
.DS_Store
Thumbs.db
```

#### Step 8: Health Check 엔드포인트 개선
`langflix/api/routes/health.py`:

```python
from fastapi import APIRouter, Depends
from datetime import datetime
from typing import Dict, Any

router = APIRouter()

@router.get("/health")
async def health_check():
    """Basic health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }

@router.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check with component status"""
    
    components = {
        "database": await check_database(),
        "redis": await check_redis(),
        "storage": await check_storage(),
        "api_keys": await check_api_keys()
    }
    
    overall_healthy = all(
        comp.get("status") == "healthy" 
        for comp in components.values()
    )
    
    return {
        "status": "healthy" if overall_healthy else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "components": components
    }

async def check_database() -> Dict[str, Any]:
    """Check database connectivity"""
    try:
        from langflix.db import db_manager
        db = db_manager.get_session()
        db.execute("SELECT 1")
        db.close()
        return {"status": "healthy", "latency_ms": 0}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

async def check_redis() -> Dict[str, Any]:
    """Check Redis connectivity"""
    try:
        from langflix.core.redis_client import get_redis_job_manager
        manager = get_redis_job_manager()
        health = manager.health_check()
        return health
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

async def check_storage() -> Dict[str, Any]:
    """Check storage backends"""
    # Implementation
    return {"status": "healthy"}

async def check_api_keys() -> Dict[str, Any]:
    """Verify API keys are configured"""
    import os
    keys = {
        "gemini": bool(os.getenv("GEMINI_API_KEY")),
        "google_tts": bool(os.getenv("GOOGLE_API_KEY_1")),
        "lemonfox": bool(os.getenv("LEMONFOX_API_KEY"))
    }
    
    configured = sum(keys.values())
    total = len(keys)
    
    return {
        "status": "healthy" if configured > 0 else "unhealthy",
        "configured": configured,
        "total": total,
        "details": keys
    }
```

#### Step 9: Makefile 업데이트
`Makefile`에 Docker 명령 추가:

```makefile
# Docker commands
docker-build:
	@echo "🔨 Building LangFlix Docker images..."
	docker-compose -f deploy/docker-compose.truenas.yml build

docker-up:
	@echo "🐳 Starting LangFlix with Docker Compose..."
	docker-compose -f deploy/docker-compose.truenas.yml up -d

docker-down:
	@echo "🛑 Stopping LangFlix services..."
	docker-compose -f deploy/docker-compose.truenas.yml down

docker-restart:
	@echo "🔄 Restarting LangFlix services..."
	docker-compose -f deploy/docker-compose.truenas.yml restart

docker-logs:
	@echo "📋 Viewing LangFlix logs..."
	docker-compose -f deploy/docker-compose.truenas.yml logs -f

docker-shell-api:
	@echo "🐚 Opening shell in API container..."
	docker exec -it langflix-api bash

docker-test:
	@echo "🧪 Running tests in Docker..."
	docker-compose -f deploy/docker-compose.truenas.yml run --rm langflix-api pytest

docker-clean:
	@echo "🧹 Cleaning up Docker resources..."
	docker system prune -af --volumes
	docker-compose -f deploy/docker-compose.truenas.yml down --volumes
```

### Alternative Approaches Considered

**Option 1: 단일 Docker Compose**
- 장점: 단순함
- 단점: 환경 분리 부족
- 선택하지 않은 이유: 환경별 설정 필요

**Option 2: Kubernetes**
- 장점: 확장성
- 단점: 복잡도 증가, TrueNAS와 부합하지 않음
- 선택하지 않은 이유: 과도한 엔지니어링

**Option 3: 선택된 접근 (Docker Compose + Multi-stage)**
- 장점: 적절한 복잡도, 환경 분리, TrueNAS 호환, CI/CD 쉬움, 보안 강화
- 단점: 초기 설정 비용
- 선택 이유: 균형 지점

### Benefits
- 프로덕션 배포 일관성
- TrueNAS 호환성
- CI/CD 자동화
- 보안 강화
- 모니터링/로그 구조화
- 확장성 향상
- 재현 가능한 환경
- 개발/운영 분리

### Risks & Considerations
- Docker 학습 필요
- 설정 복잡도 증가
- 초기 비용 상승
- 마이그레이션 부담
- 의존성 관리 주의

## Testing Strategy

### Unit Tests
- Dockerfile 각 스테이지 검증
- 이미지 최소 사이즈 확인
- 보안 스캔 통과
- 헬스체크 동작 확인

### Integration Tests
- Compose 전체 스택 검증
- 의존성 시작 순서 검증
- 볼륨 마운트 확인
- 네트워크 정상 동작 확인

### CI Tests
- 모든 브랜치에서 자동 실행
- 릴리스 태그 시 자동 배포
- 보안 스캔 자동화
- 커버리지 기준 충족

### Deployment Tests
- TrueNAS 실제 배포 검증
- 롤백 절차 테스트
- 성능/메모리 테스트
- 재시작 동작 검증

## Files Affected

**새로 생성:**
- `Dockerfile` - Production multi-stage
- `deploy/docker-compose.truenas.yml` - TrueNAS Compose
- `.github/workflows/ci.yml` - CI/CD 파이프라인
- `.docker/secrets/README.md` - 비밀 관리 가이드
- `docs/DEPLOYMENT_TRUENAS.md` - TrueNAS 배포 가이드
- `.dockerignore` - 빌드 제외 파일

**수정:**
- `deploy/Dockerfile.ec2` - 멀티 스테이지로 리팩토링
- `deploy/docker-compose.ec2.yml` - 환경 변수 분리
- `langflix/api/routes/health.py` - 상세 헬스체크 추가
- `Makefile` - Docker 명령 추가
- `requirements.txt` - CI/CD/보안 의존성 추가

**테스트 추가:**
- `tests/docker/test_image_build.py`
- `tests/docker/test_compose_stack.py`
- `tests/integration/test_deployment.py`

## Dependencies
- Depends on: None
- Blocks: None
- Related to: ADR-017

## References
- Docker multi-stage: https://docs.docker.com/build/building/multi-stage/
- TrueNAS Docker: https://www.truenas.com/docs/
- GitHub Actions: https://docs.github.com/en/actions

## Architect Review Questions
1. Kubernetes 전환 시점은?
2. 인프라 IaC 적합성?
3. 모니터링 도구 선정?
4. 배포 전략?
5. 비용 최적화?

---
## 🏛️ Architect Review & Approval

**Reviewed by:** Architect Agent
**Review Date:** 2025-01-30
**Decision:** ✅ APPROVED (with scope adjustments)

**Strategic Rationale:**
- Essential for production deployment - enables consistent, reproducible environments
- TrueNAS deployment target aligns with existing infrastructure
- CI/CD automation improves development workflow
- Security hardening critical for production
- However: Large scope - consider phased approach

**Implementation Phase:** Phase 3 - Sprint 3+ (Weeks 5-6+)
**Sequence Order:** #3 in implementation queue (after core features stable)

**Architectural Guidance:**

**Critical Scope Adjustments:**

1. **Celery Dependency:**
   - Current codebase: Celery code exists (`langflix/tasks/celery_app.py`, `langflix/tasks/tasks.py`)
   - However: API uses FastAPI background tasks (`langflix/api/routes/jobs.py`) - Celery not actively used
   - Recommendation: **Make Celery optional** - include in Dockerfile but don't require it
   - Current implementation: FastAPI background tasks work for single-node deployment
   - Future: Celery needed for distributed workers (can enable later)

2. **Multi-stage Dockerfile Strategy:**
   - ✅ Approved: Multi-stage build reduces image size
   - Target stages: `builder`, `runtime`, `api` (CLI can be separate if needed)
   - Remove: `celery-worker` target (not implemented)

3. **Database Strategy:**
   - PostgreSQL: Good choice for production
   - However: Current codebase has optional DB support
   - Recommendation: Make PostgreSQL optional in compose (can run without DB)
   - Use existing Redis for job management (already implemented)

4. **Service Architecture:**
   - **Essential services**: API server, Redis, (optional) PostgreSQL
   - **Optional services**: Flower (Celery monitoring - remove), Celery workers (remove)
   - **Future services**: Can add later when needed

5. **Volume Management:**
   - TrueNAS mounts: ✅ Good approach
   - Ensure permissions: Non-root user can write to mounts
   - Consider: Separate volumes for output, logs, cache, assets

6. **Health Checks:**
   - ✅ Critical: Implement comprehensive health checks
   - API: `/health`, `/health/detailed`
   - Redis: Connection check
   - Storage: Write test
   - Database: Optional (if enabled)

7. **Security Considerations:**
   - ✅ Non-root user: Essential
   - ✅ Docker secrets: For sensitive data
   - Image scanning: Add to CI/CD
   - Network: Use internal networks, expose only necessary ports
   - Secrets management: Use Docker secrets or environment files (not hardcoded)

8. **CI/CD Strategy:**
   - ✅ GitHub Actions: Good choice
   - Phased approach:
     - Phase 1: Build and test only
     - Phase 2: Push to registry
     - Phase 3: Deploy to TrueNAS (manual trigger initially)

9. **Configuration Management:**
   - Environment variables: Use `.env` files
   - Config file mounting: Read-only mount
   - Secrets: Never in config files or images

**Dependencies:**
- **Must complete first:** Core features stable (TICKET-001, TICKET-002)
- **Should complete first:** None (can proceed independently)
- **Blocks:** None
- **Related work:** None

**Risk Mitigation:**
- Risk: Over-engineering with unused services (Celery)
  - Mitigation: Remove Celery components, use FastAPI background tasks
- Risk: Database dependency when optional
  - Mitigation: Make PostgreSQL optional, use environment flags
- Risk: Complex deployment process
  - Mitigation: Comprehensive documentation, phased rollout
- Risk: Security vulnerabilities
  - Mitigation: Image scanning, non-root user, secrets management
- **Rollback strategy:** Keep existing deployment method, Docker as additional option

**Enhanced Success Criteria:**
Beyond original ticket criteria:
- [ ] Multi-stage Dockerfile builds successfully (without Celery)
- [ ] Images are < 500MB (optimized)
- [ ] Non-root user working correctly
- [ ] Health checks implemented and passing
- [ ] TrueNAS deployment documented and tested
- [ ] CI/CD pipeline runs tests automatically
- [ ] Security scan passes (Trivy)
- [ ] Services start correctly (API + Redis, optional PostgreSQL)
- [ ] Volumes mounted with correct permissions
- [ ] Secrets not exposed in logs/images

**Alternative Approaches Considered:**
- Original proposal: Full stack with Celery - Modified (remove Celery, add later if needed)
- Alternative 1: Single-stage Dockerfile - Rejected (larger images, less secure)
- Alternative 2: Kubernetes - Deferred (overkill for current scale, can migrate later)
- **Selected approach:** Simplified Docker Compose (API + Redis + optional DB) - right-sized for current needs

**Implementation Notes:**
- Start by: Creating simplified Dockerfile (no Celery)
- Watch out for: Celery references in code (remove or make optional)
- Coordinate with: None
- Reference: `langflix/api/routes/jobs.py` for background task pattern, existing Redis usage

**Simplified Docker Compose Recommendation:**
```yaml
services:
  langflix-api:     # FastAPI server (main service)
  redis:            # Job state management
  postgres:         # Optional (if DB enabled)
```

**Phased Implementation:**
- **Phase 1**: Basic Dockerfile + compose (API + Redis)
- **Phase 2**: Add PostgreSQL (optional), health checks
- **Phase 3**: CI/CD pipeline
- **Phase 4**: TrueNAS deployment guide
- **Phase 5**: Advanced features (monitoring, scaling) - future

**Estimated Timeline:** 4-5 days (simplified version without Celery)
**Recommended Owner:** DevOps engineer or senior backend engineer with Docker experience

## Success Criteria
- 모든 스테이지 이미지 빌드 성공
- 멀티 스테이지로 이미지 크기 감소
- TrueNAS 배포 정상
- CI/CD 통과
- 보안 스캔 통과
- 헬스체크 100% 통과
- 문서화 완료

