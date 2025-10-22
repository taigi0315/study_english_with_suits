# LangFlix Deployment Guide

**Version:** 2.0  
**Last Updated:** October 21, 2025

This guide covers production deployment of LangFlix API service for scalable, reliable video processing operations.

**✅ Phase 1 Complete**: API-based deployment is now fully operational.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Local Deployment](#local-deployment)
3. [Docker Deployment](#docker-deployment)
4. [Cloud Deployment](#cloud-deployment)
5. [Environment Configuration](#environment-configuration)
6. [Monitoring and Logging](#monitoring-and-logging)
7. [Scaling Considerations](#scaling-considerations)
8. [Security Best Practices](#security-best-practices)
9. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### System Requirements

**Minimum:**
- CPU: 4 cores, 2.4 GHz
- RAM: 8 GB
- Storage: 50 GB SSD
- OS: Linux (Ubuntu 20.04+), macOS, Windows 10+

**Recommended:**
- CPU: 8+ cores, 3.0+ GHz
- RAM: 16+ GB
- Storage: 500 GB+ SSD
- Network: 100+ Mbps

### Dependencies

- Python 3.9+
- ffmpeg 4.4+
- Google Gemini API access
- Docker (for containerized deployment)

---

## Local Deployment

### 1. Quick Start (API Service)

```bash
# Clone repository
git clone <repository-url>
cd langflix

# Setup environment
make setup

# Start API server
make api

# Test API
curl http://127.0.0.1:8000/health
```

### 2. System Setup

**Ubuntu/Debian:**
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install system dependencies
sudo apt install -y python3.9 python3.9-pip python3.9-venv ffmpeg git

# Install Node.js (for any web interface components)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
```

**macOS:**
```bash
# Install Homebrew if not present
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install python@3.9 ffmpeg git node
```

**Windows:**
```powershell
# Install Chocolatey
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Install dependencies
choco install python39 ffmpeg git nodejs -y
```

### 2. Application Setup

```bash
# Clone repository
git clone https://github.com/taigi0315/study_english_with_suits.git
cd study_english_with_suits

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Verify installation
python -c "import langflix; print('LangFlix installed successfully')"
```

### 3. Configuration

```bash
# Copy configuration files
cp env.example .env
cp config.example.yaml config.yaml

# Edit environment variables
nano .env
```

**Essential `.env` variables:**
```env
# Required
GEMINI_API_KEY=your_actual_api_key_here

# Optional production settings
LANGFLIX_LOG_LEVEL=INFO
LANGFLIX_MAX_CONCURRENT_JOBS=4
LANGFLIX_OUTPUT_DIR=/data/langflix/output
```

**Production `config.yaml`:**
```yaml
llm:
  max_input_length: 1680
  max_retries: 5
  retry_backoff_seconds: 3

video:
  codec: "libx264"
  preset: "medium"  # Better quality for production
  crf: 20          # Higher quality
  resolution: "1920x1080"

processing:
  min_expressions_per_chunk: 2
  max_expressions_per_chunk: 4  # More expressions per chunk in production
```

### 4. Service Setup (Linux)

**Create systemd service:**

```bash
sudo nano /etc/systemd/system/langflix.service
```

```ini
[Unit]
Description=LangFlix Video Processing Service
After=network.target

[Service]
Type=simple
User=langflix
Group=langflix
WorkingDirectory=/opt/langflix
Environment=PATH=/opt/langflix/venv/bin
ExecStart=/opt/langflix/venv/bin/python -m langflix.main --subtitle %i
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable and start service:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable langflix.service
```

---

## Docker Deployment

### 1. Dockerfile

Create `Dockerfile` in project root:

```dockerfile
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -s /bin/bash langflix && \
    chown -R langflix:langflix /app
USER langflix

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import langflix" || exit 1

# Default command
CMD ["python", "-m", "langflix.main", "--help"]
```

### 2. Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  langflix:
    build: .
    container_name: langflix-app
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - LANGFLIX_LOG_LEVEL=INFO
    volumes:
      - ./assets:/app/assets:ro
      - ./config.yaml:/app/config.yaml:ro
      - langflix-output:/app/output
      - langflix-logs:/app/logs
    ports:
      - "8080:8080"  # If web interface added
    restart: unless-stopped
    deploy:
      resources:
        limits:
          memory: 8G
          cpus: '4'

volumes:
  langflix-output:
  langflix-logs:
```

### 3. Build and Run

```bash
# Build image
docker build -t langflix:latest .

# Run with docker-compose
docker-compose up -d

# Or run directly
docker run -d \
  --name langflix \
  -e GEMINI_API_KEY=your_key_here \
  -v $(pwd)/assets:/app/assets:ro \
  -v $(pwd)/output:/app/output \
  langflix:latest
```

---

## Cloud Deployment

### AWS Deployment

#### 1. EC2 Instance Setup

**Recommended Instance Types:**
- Development: `t3.large` (2 vCPU, 8 GB RAM)
- Production: `c5.2xlarge` (8 vCPU, 16 GB RAM) or higher
- High-throughput: `c5.4xlarge` (16 vCPU, 32 GB RAM)

**Launch Script:**
```bash
#!/bin/bash
# Update system
sudo yum update -y

# Install dependencies
sudo yum install -y python39 python39-pip git wget
sudo amazon-linux-extras install ffmpeg

# Setup application directory
sudo mkdir -p /opt/langflix
sudo chown ec2-user:ec2-user /opt/langflix
cd /opt/langflix

# Clone and setup (add your actual repo URL)
git clone https://github.com/your-org/langflix.git .
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Setup systemd service (as above)
```

#### 2. S3 Integration

**Install AWS CLI and configure:**
```bash
pip install awscli
aws configure
```

**Add to `config.yaml`:**
```yaml
storage:
  type: "s3"
  bucket: "your-langflix-bucket"
  region: "us-west-2"
  input_prefix: "input/"
  output_prefix: "output/"
```

**Environment variables:**
```env
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-west-2
```

### Google Cloud Platform

#### 1. Compute Engine Setup

**Create instance with GPU support (optional):**
```bash
gcloud compute instances create langflix-server \
    --zone=us-central1-a \
    --machine-type=n1-standard-8 \
    --accelerator=type=nvidia-tesla-t4,count=1 \
    --image-family=cos-stable \
    --image-project=cos-cloud \
    --boot-disk-size=100GB
```

#### 2. Cloud Storage Integration

```bash
# Install Google Cloud SDK
pip install google-cloud-storage

# Authenticate
gcloud auth application-default login
```

### Azure Deployment

#### 1. VM Setup

```bash
# Create resource group
az group create --name langflix-rg --location eastus

# Create VM
az vm create \
  --resource-group langflix-rg \
  --name langflix-vm \
  --image UbuntuLTS \
  --size Standard_D4s_v3 \
  --admin-username azureuser \
  --generate-ssh-keys
```

---

## Environment Configuration

### Production Configuration

**Production `.env`:**
```env
# Core API
GEMINI_API_KEY=your_production_api_key

# Logging
LANGFLIX_LOG_LEVEL=INFO
LANGFLIX_LOG_FILE=/var/log/langflix/app.log

# Performance
LANGFLIX_MAX_CONCURRENT_JOBS=8
LANGFLIX_CHUNK_SIZE=1400

# Storage
LANGFLIX_OUTPUT_DIR=/data/langflix/output
LANGFLIX_TEMP_DIR=/tmp/langflix

# Monitoring
LANGFLIX_ENABLE_METRICS=true
LANGFLIX_METRICS_PORT=9090
```

**Production `config.yaml`:**
```yaml
# Optimized for production
llm:
  max_input_length: 1680
  max_retries: 5
  retry_backoff_seconds: 3
  timeout: 120

video:
  codec: "libx264"
  preset: "medium"
  crf: 20
  resolution: "1920x1080"
  thread_count: 4

processing:
  min_expressions_per_chunk: 2
  max_expressions_per_chunk: 4
  batch_size: 10

storage:
  retention_days: 30
  cleanup_temp_files: true
```

### Multi-Environment Setup

**Development:**
```bash
cp config.example.yaml config.dev.yaml
export LANGFLIX_CONFIG_FILE=config.dev.yaml
```

**Staging:**
```bash
cp config.example.yaml config.staging.yaml
export LANGFLIX_CONFIG_FILE=config.staging.yaml
```

**Production:**
```bash
cp config.example.yaml config.prod.yaml
export LANGFLIX_CONFIG_FILE=config.prod.yaml
```

---

## Monitoring and Logging

### Logging Configuration

**Structured logging setup:**
```python
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        if hasattr(record, 'user_id'):
            log_entry['user_id'] = record.user_id
            
        if hasattr(record, 'job_id'):
            log_entry['job_id'] = record.job_id
            
        return json.dumps(log_entry)
```

**Log rotation:**
```yaml
# In systemd service or logrotate config
logrotate:
  - /var/log/langflix/*.log {
      daily
      rotate 30
      compress
      delaycompress
      missingok
      notifempty
      create 644 langflix langflix
    }
```

### Monitoring Setup

#### Prometheus Metrics

Create `monitoring.py`:
```python
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import time

# Metrics
EXPRESSIONS_PROCESSED = Counter('langflix_expressions_processed_total', 'Total expressions processed')
PROCESSING_DURATION = Histogram('langflix_processing_duration_seconds', 'Processing duration')
ACTIVE_JOBS = Gauge('langflix_active_jobs', 'Currently active processing jobs')
API_ERRORS = Counter('langflix_api_errors_total', 'Total API errors', ['error_type'])

def start_metrics_server(port=9090):
    start_http_server(port)
```

#### Health Checks

```python
from flask import Flask, jsonify
import os

app = Flask(__name__)

@app.route('/health')
def health_check():
    checks = {
        'api_key': bool(os.getenv('GEMINI_API_KEY')),
        'ffmpeg': subprocess.run(['ffmpeg', '-version'], capture_output=True).returncode == 0,
        'disk_space': shutil.disk_usage('/').free > 10 * 1024**3  # 10GB free
    }
    
    healthy = all(checks.values())
    status_code = 200 if healthy else 503
    
    return jsonify({'status': 'healthy' if healthy else 'unhealthy', 'checks': checks}), status_code

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
```

---

## Scaling Considerations

### Horizontal Scaling

#### Queue-Based Architecture

**Using Celery with Redis:**

```python
# celery_app.py
from celery import Celery

celery_app = Celery('langflix')
celery_app.config_from_object('celeryconfig')

@celery_app.task
def process_episode_task(subtitle_path, video_dir, output_dir):
    pipeline = LangFlixPipeline(subtitle_path, video_dir, output_dir)
    return pipeline.run()
```

**Celery configuration:**
```python
# celeryconfig.py
broker_url = 'redis://localhost:6379/0'
result_backend = 'redis://localhost:6379/0'
task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
timezone = 'UTC'
enable_utc = True

# Worker configuration
worker_concurrency = 4
worker_prefetch_multiplier = 1
```

#### Load Balancer Setup

**Nginx configuration:**
```nginx
upstream langflix_backend {
    server 127.0.0.1:8080;
    server 127.0.0.1:8081;
    server 127.0.0.1:8082;
}

server {
    listen 80;
    server_name langflix.example.com;
    
    location / {
        proxy_pass http://langflix_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /health {
        access_log off;
        proxy_pass http://langflix_backend;
    }
}
```

### Resource Management

#### Memory Optimization

```python
import gc
import psutil

class ResourceManager:
    def __init__(self, max_memory_gb=8):
        self.max_memory_bytes = max_memory_gb * 1024**3
        
    def check_memory(self):
        memory = psutil.virtual_memory()
        if memory.used > self.max_memory_bytes:
            gc.collect()
            return False
        return True
    
    def cleanup_temp_files(self):
        # Cleanup temporary video files
        pass
```

#### Batch Processing

```python
def batch_process_episodes(episode_list, batch_size=5):
    """Process episodes in batches to manage resources."""
    for i in range(0, len(episode_list), batch_size):
        batch = episode_list[i:i + batch_size]
        
        # Process batch
        for episode in batch:
            processor.process_episode(episode)
            
        # Cleanup between batches
        gc.collect()
        time.sleep(2)  # Brief pause between batches
```

---

## Security Best Practices

### API Key Management

**Use secret management:**
```bash
# AWS Secrets Manager
aws secretsmanager create-secret --name langflix/api-key --secret-string "your_api_key"

# Kubernetes secrets
kubectl create secret generic langflix-secrets --from-literal=gemini-api-key=your_key
```

**Environment isolation:**
```bash
# Never commit API keys
echo "*.env" >> .gitignore
echo "config.local.yaml" >> .gitignore
```

### Network Security

**Firewall rules:**
```bash
# UFW (Ubuntu)
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# Block direct access to LangFlix ports except for load balancer
sudo ufw deny 8080
```

### File System Security

**Proper permissions:**
```bash
# Create dedicated user
sudo useradd -r -s /bin/false langflix

# Set proper ownership
sudo chown -R langflix:langflix /opt/langflix
sudo chmod -R 755 /opt/langflix
sudo chmod 600 /opt/langflix/.env
```

---

## Troubleshooting

### Common Deployment Issues

#### 1. FFmpeg Not Found

**Error:** `FileNotFoundError: [Errno 2] No such file or directory: 'ffmpeg'`

**Solution:**
```bash
# Verify installation
which ffmpeg
ffmpeg -version

# Fix PATH if needed
export PATH=$PATH:/usr/local/bin

# Docker: Ensure ffmpeg is in PATH
ENV PATH="/usr/local/bin:$PATH"
```

#### 2. Permission Issues

**Error:** `PermissionError: [Errno 13] Permission denied`

**Solution:**
```bash
# Check ownership
ls -la /opt/langflix

# Fix ownership
sudo chown -R $USER:$USER /opt/langflix
chmod 755 /opt/langflix
chmod 644 /opt/langflix/config.yaml
```

#### 3. Memory Issues

**Error:** `MemoryError` or `Killed`

**Solution:**
```bash
# Check memory usage
free -h
top -p $(pgrep -f langflix)

# Reduce batch size in config
# Add swap space
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### Performance Optimization

#### 1. Slow Processing

```bash
# Profile CPU usage
python -m cProfile -s cumulative -m langflix.main --subtitle test.srt

# Check I/O bottlenecks
iotop -a
iostat -x 1
```

#### 2. API Rate Limiting

```yaml
# Increase delays in config.yaml
llm:
  max_retries: 5
  retry_backoff_seconds: 5  # Increase from 2
```

### Monitoring and Alerting

**Set up alerts for:**
- High error rates (>5%)
- Long processing times (>30 minutes per episode)
- Low disk space (<10GB free)
- High memory usage (>90%)
- API quota exhaustion

**Example monitoring script:**
```bash
#!/bin/bash
# health_check.sh

# Check disk space
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 90 ]; then
    echo "ALERT: Disk usage at ${DISK_USAGE}%"
    exit 1
fi

# Check memory
MEM_USAGE=$(free | awk 'NR==2{printf "%.0f", $3*100/$2 }')
if [ $MEM_USAGE -gt 90 ]; then
    echo "ALERT: Memory usage at ${MEM_USAGE}%"
    exit 1
fi

echo "System healthy"
exit 0
```

---

**For Korean version of this deployment guide, see [DEPLOYMENT_KOR.md](DEPLOYMENT_KOR.md)**

**Related Documentation:**
- [User Manual](USER_MANUAL.md) - Complete usage guide
- [API Reference](API_REFERENCE.md) - Programmatic usage
- [Performance Guide](PERFORMANCE.md) - Optimization tips
