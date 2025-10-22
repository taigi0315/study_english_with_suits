# LangFlix 배포 가이드

**버전:** 1.0  
**최종 업데이트:** 2025년 10월 19일

이 가이드는 확장 가능하고 신뢰할 수 있는 비디오 처리 작업을 위한 LangFlix의 프로덕션 배포를 다룹니다.

---

## 목차

1. [사전 요구사항](#사전-요구사항)
2. [로컬 배포](#로컬-배포)
3. [Docker 배포](#docker-배포)
4. [클라우드 배포](#클라우드-배포)
5. [환경 설정](#환경-설정)
6. [모니터링 및 로깅](#모니터링-및-로깅)
7. [확장 고려사항](#확장-고려사항)
8. [보안 모범 사례](#보안-모범-사례)
9. [문제 해결](#문제-해결)

---

## 사전 요구사항

### 시스템 요구사항

**최소:**
- CPU: 4코어, 2.4 GHz
- RAM: 8 GB
- 저장공간: 50 GB SSD
- OS: Linux (Ubuntu 20.04+), macOS, Windows 10+

**권장:**
- CPU: 8+ 코어, 3.0+ GHz
- RAM: 16+ GB
- 저장공간: 500 GB+ SSD
- 네트워크: 100+ Mbps

### 종속성

- Python 3.9+
- ffmpeg 4.4+
- Google Gemini API 접근 권한
- Docker (컨테이너화된 배포용)

---

## 로컬 배포

### 1. 시스템 설정

**Ubuntu/Debian:**
```bash
# 시스템 업데이트
sudo apt update && sudo apt upgrade -y

# 시스템 종속성 설치
sudo apt install -y python3.9 python3.9-pip python3.9-venv ffmpeg git

# Node.js 설치 (웹 인터페이스 컴포넌트용)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
```

**macOS:**
```bash
# Homebrew가 없는 경우 설치
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 종속성 설치
brew install python@3.9 ffmpeg git node
```

**Windows:**
```powershell
# Chocolatey 설치
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# 종속성 설치
choco install python39 ffmpeg git nodejs -y
```

### 2. 애플리케이션 설정

```bash
# 저장소 클론
git clone https://github.com/taigi0315/study_english_with_suits.git
cd study_english_with_suits

# 가상 환경 생성
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 종속성 설치
pip install --upgrade pip
pip install -r requirements.txt

# 설치 확인
python -c "import langflix; print('LangFlix 설치 성공')"
```

### 3. 설정

```bash
# 설정 파일 복사
cp env.example .env
cp config.example.yaml config.yaml

# 환경 변수 편집
nano .env
```

**필수 `.env` 변수:**
```env
# 필수
GEMINI_API_KEY=your_actual_api_key_here

# 선택적 프로덕션 설정
LANGFLIX_LOG_LEVEL=INFO
LANGFLIX_MAX_CONCURRENT_JOBS=4
LANGFLIX_OUTPUT_DIR=/data/langflix/output
```

**프로덕션 `config.yaml`:**
```yaml
llm:
  max_input_length: 1680
  max_retries: 5
  retry_backoff_seconds: 3

video:
  codec: "libx264"
  preset: "medium"  # 프로덕션용 더 나은 품질
  crf: 20          # 더 높은 품질
  resolution: "1920x1080"

processing:
  min_expressions_per_chunk: 2
  max_expressions_per_chunk: 4  # 프로덕션에서 청크당 더 많은 표현
```

### 4. 서비스 설정 (Linux)

**systemd 서비스 생성:**

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

**서비스 활성화 및 시작:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable langflix.service
```

---

## Docker 배포

### 1. Dockerfile

프로젝트 루트에 `Dockerfile` 생성:

```dockerfile
FROM python:3.9-slim

# 시스템 종속성 설치
RUN apt-get update && apt-get install -y \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# 작업 디렉토리 설정
WORKDIR /app

# 요구사항 복사 및 Python 종속성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 비루트 사용자 생성
RUN useradd -m -s /bin/bash langflix && \
    chown -R langflix:langflix /app
USER langflix

# 헬스 체크
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import langflix" || exit 1

# 기본 명령
CMD ["python", "-m", "langflix.main", "--help"]
```

### 2. Docker Compose

`docker-compose.yml` 생성:

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
      - "8080:8080"  # 웹 인터페이스 추가 시
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

### 3. 빌드 및 실행

```bash
# 이미지 빌드
docker build -t langflix:latest .

# docker-compose로 실행
docker-compose up -d

# 또는 직접 실행
docker run -d \
  --name langflix \
  -e GEMINI_API_KEY=your_key_here \
  -v $(pwd)/assets:/app/assets:ro \
  -v $(pwd)/output:/app/output \
  langflix:latest
```

---

## 클라우드 배포

### AWS 배포

#### 1. EC2 인스턴스 설정

**권장 인스턴스 유형:**
- 개발: `t3.large` (2 vCPU, 8 GB RAM)
- 프로덕션: `c5.2xlarge` (8 vCPU, 16 GB RAM) 이상
- 고처리량: `c5.4xlarge` (16 vCPU, 32 GB RAM)

**런치 스크립트:**
```bash
#!/bin/bash
# 시스템 업데이트
sudo yum update -y

# 종속성 설치
sudo yum install -y python39 python39-pip git wget
sudo amazon-linux-extras install ffmpeg

# 애플리케이션 디렉토리 설정
sudo mkdir -p /opt/langflix
sudo chown ec2-user:ec2-user /opt/langflix
cd /opt/langflix

# 클론 및 설정 (실제 저장소 URL 추가)
git clone https://github.com/your-org/langflix.git .
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# systemd 서비스 설정 (위와 동일)
```

#### 2. S3 통합

**AWS CLI 설치 및 설정:**
```bash
pip install awscli
aws configure
```

**`config.yaml`에 추가:**
```yaml
storage:
  type: "s3"
  bucket: "your-langflix-bucket"
  region: "us-west-2"
  input_prefix: "input/"
  output_prefix: "output/"
```

**환경 변수:**
```env
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_DEFAULT_REGION=us-west-2
```

### Google Cloud Platform

#### 1. Compute Engine 설정

**GPU 지원으로 인스턴스 생성 (선택사항):**
```bash
gcloud compute instances create langflix-server \
    --zone=us-central1-a \
    --machine-type=n1-standard-8 \
    --accelerator=type=nvidia-tesla-t4,count=1 \
    --image-family=cos-stable \
    --image-project=cos-cloud \
    --boot-disk-size=100GB
```

#### 2. Cloud Storage 통합

```bash
# Google Cloud SDK 설치
pip install google-cloud-storage

# 인증
gcloud auth application-default login
```

### Azure 배포

#### 1. VM 설정

```bash
# 리소스 그룹 생성
az group create --name langflix-rg --location eastus

# VM 생성
az vm create \
  --resource-group langflix-rg \
  --name langflix-vm \
  --image UbuntuLTS \
  --size Standard_D4s_v3 \
  --admin-username azureuser \
  --generate-ssh-keys
```

---

## 환경 설정

### 프로덕션 설정

**프로덕션 `.env`:**
```env
# 핵심 API
GEMINI_API_KEY=your_production_api_key

# 로깅
LANGFLIX_LOG_LEVEL=INFO
LANGFLIX_LOG_FILE=/var/log/langflix/app.log

# 성능
LANGFLIX_MAX_CONCURRENT_JOBS=8
LANGFLIX_CHUNK_SIZE=1400

# 저장소
LANGFLIX_OUTPUT_DIR=/data/langflix/output
LANGFLIX_TEMP_DIR=/tmp/langflix

# 모니터링
LANGFLIX_ENABLE_METRICS=true
LANGFLIX_METRICS_PORT=9090
```

**프로덕션 `config.yaml`:**
```yaml
# 프로덕션용 최적화
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

### 다중 환경 설정

**개발:**
```bash
cp config.example.yaml config.dev.yaml
export LANGFLIX_CONFIG_FILE=config.dev.yaml
```

**스테이징:**
```bash
cp config.example.yaml config.staging.yaml
export LANGFLIX_CONFIG_FILE=config.staging.yaml
```

**프로덕션:**
```bash
cp config.example.yaml config.prod.yaml
export LANGFLIX_CONFIG_FILE=config.prod.yaml
```

---

## 모니터링 및 로깅

### 로깅 설정

**구조화된 로깅 설정:**
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

**로그 회전:**
```yaml
# systemd 서비스 또는 logrotate 설정
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

### 모니터링 설정

#### Prometheus 메트릭

`monitoring.py` 생성:
```python
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import time

# 메트릭
EXPRESSIONS_PROCESSED = Counter('langflix_expressions_processed_total', '처리된 총 표현 수')
PROCESSING_DURATION = Histogram('langflix_processing_duration_seconds', '처리 지속시간')
ACTIVE_JOBS = Gauge('langflix_active_jobs', '현재 활성 처리 작업 수')
API_ERRORS = Counter('langflix_api_errors_total', '총 API 오류 수', ['error_type'])

def start_metrics_server(port=9090):
    start_http_server(port)
```

#### 헬스 체크

```python
from flask import Flask, jsonify
import os

app = Flask(__name__)

@app.route('/health')
def health_check():
    checks = {
        'api_key': bool(os.getenv('GEMINI_API_KEY')),
        'ffmpeg': subprocess.run(['ffmpeg', '-version'], capture_output=True).returncode == 0,
        'disk_space': shutil.disk_usage('/').free > 10 * 1024**3  # 10GB 여유공간
    }
    
    healthy = all(checks.values())
    status_code = 200 if healthy else 503
    
    return jsonify({'status': 'healthy' if healthy else 'unhealthy', 'checks': checks}), status_code

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
```

---

## 확장 고려사항

### 수평 확장

#### 큐 기반 아키텍처

**Redis와 함께 Celery 사용:**

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

**Celery 설정:**
```python
# celeryconfig.py
broker_url = 'redis://localhost:6379/0'
result_backend = 'redis://localhost:6379/0'
task_serializer = 'json'
result_serializer = 'json'
accept_content = ['json']
timezone = 'UTC'
enable_utc = True

# 워커 설정
worker_concurrency = 4
worker_prefetch_multiplier = 1
```

#### 로드 밸런서 설정

**Nginx 설정:**
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

### 리소스 관리

#### 메모리 최적화

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
        # 임시 비디오 파일 정리
        pass
```

#### 배치 처리

```python
def batch_process_episodes(episode_list, batch_size=5):
    """리소스 관리를 위해 에피소드를 배치로 처리합니다."""
    for i in range(0, len(episode_list), batch_size):
        batch = episode_list[i:i + batch_size]
        
        # 배치 처리
        for episode in batch:
            processor.process_episode(episode)
            
        # 배치 간 정리
        gc.collect()
        time.sleep(2)  # 배치 간 짧은 일시정지
```

---

## 보안 모범 사례

### API 키 관리

**시크릿 관리 사용:**
```bash
# AWS Secrets Manager
aws secretsmanager create-secret --name langflix/api-key --secret-string "your_api_key"

# Kubernetes 시크릿
kubectl create secret generic langflix-secrets --from-literal=gemini-api-key=your_key
```

**환경 격리:**
```bash
# API 키를 절대 커밋하지 않음
echo "*.env" >> .gitignore
echo "config.local.yaml" >> .gitignore
```

### 네트워크 보안

**방화벽 규칙:**
```bash
# UFW (Ubuntu)
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# 로드 밸런서를 제외하고 LangFlix 포트에 대한 직접 접근 차단
sudo ufw deny 8080
```

### 파일 시스템 보안

**적절한 권한:**
```bash
# 전용 사용자 생성
sudo useradd -r -s /bin/false langflix

# 적절한 소유권 설정
sudo chown -R langflix:langflix /opt/langflix
sudo chmod -R 755 /opt/langflix
sudo chmod 600 /opt/langflix/.env
```

---

## 문제 해결

### 일반적인 배포 문제

#### 1. FFmpeg를 찾을 수 없음

**오류:** `FileNotFoundError: [Errno 2] No such file or directory: 'ffmpeg'`

**해결책:**
```bash
# 설치 확인
which ffmpeg
ffmpeg -version

# 필요시 PATH 수정
export PATH=$PATH:/usr/local/bin

# Docker: PATH에 ffmpeg가 있는지 확인
ENV PATH="/usr/local/bin:$PATH"
```

#### 2. 권한 문제

**오류:** `PermissionError: [Errno 13] Permission denied`

**해결책:**
```bash
# 소유권 확인
ls -la /opt/langflix

# 소유권 수정
sudo chown -R $USER:$USER /opt/langflix
chmod 755 /opt/langflix
chmod 644 /opt/langflix/config.yaml
```

#### 3. 메모리 문제

**오류:** `MemoryError` 또는 `Killed`

**해결책:**
```bash
# 메모리 사용량 확인
free -h
top -p $(pgrep -f langflix)

# 설정에서 배치 크기 감소
# 스왑 공간 추가
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### 성능 최적화

#### 1. 느린 처리

```bash
# CPU 사용량 프로파일링
python -m cProfile -s cumulative -m langflix.main --subtitle test.srt

# I/O 병목 확인
iotop -a
iostat -x 1
```

#### 2. API 속도 제한

```yaml
# config.yaml에서 지연 증가
llm:
  max_retries: 5
  retry_backoff_seconds: 5  # 2에서 증가
```

### 모니터링 및 알림

**알림 설정 대상:**
- 높은 오류율 (>5%)
- 긴 처리 시간 (에피소드당 >30분)
- 낮은 디스크 공간 (<10GB 여유)
- 높은 메모리 사용량 (>90%)
- API 할당량 고갈

**모니터링 스크립트 예제:**
```bash
#!/bin/bash
# health_check.sh

# 디스크 공간 확인
DISK_USAGE=$(df / | awk 'NR==2 {print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 90 ]; then
    echo "경고: 디스크 사용량이 ${DISK_USAGE}%입니다"
    exit 1
fi

# 메모리 확인
MEM_USAGE=$(free | awk 'NR==2{printf "%.0f", $3*100/$2 }')
if [ $MEM_USAGE -gt 90 ]; then
    echo "경고: 메모리 사용량이 ${MEM_USAGE}%입니다"
    exit 1
fi

echo "시스템 정상"
exit 0
```

---

**이 배포 가이드의 영어 버전은 [DEPLOYMENT.md](DEPLOYMENT.md)를 참조하세요**

**관련 문서:**
- [사용자 매뉴얼](USER_MANUAL_KOR.md) - 완전한 사용 가이드
- [API 참조](API_REFERENCE_KOR.md) - 프로그래밍 방식 사용법
- [성능 가이드](PERFORMANCE_KOR.md) - 최적화 팁
