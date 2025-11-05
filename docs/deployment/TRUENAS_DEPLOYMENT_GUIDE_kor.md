# TrueNAS 배포 가이드 (한국어)

## 개요

이 가이드는 LangFlix 애플리케이션을 TrueNAS 서버에 배포하는 방법을 설명합니다.

**현재 상황:**
- macOS에서 PostgreSQL, Redis, 애플리케이션이 Docker로 실행 중
- TrueNAS 서버에 미디어 파일 저장됨
- TrueNAS에서 모든 서비스를 실행하고 미디어 파일에 접근해야 함

**배포 대상:**
- TrueNAS Scale (Linux 기반, Docker 지원) - **권장**
- TrueNAS Core (FreeBSD 기반) - VM 또는 Docker Desktop 필요

---

## 사전 요구사항

### 1. TrueNAS 버전 확인

**TrueNAS Scale (권장):**
- Linux 기반으로 Docker를 직접 지원
- Docker Compose 사용 가능
- 가장 쉬운 배포 방법

**TrueNAS Core:**
- FreeBSD 기반으로 Docker를 직접 지원하지 않음
- Docker Desktop을 VM으로 실행하거나
- 별도의 Linux VM 생성 필요

### 2. 필요한 것들

- TrueNAS 서버에 SSH 접근 권한
- Docker 및 Docker Compose 설치 (TrueNAS Scale의 경우 Apps에서 설치)
- TrueNAS의 미디어 파일 경로 확인
- GitHub 저장소 접근 또는 프로젝트 파일 업로드

---

## 1단계: TrueNAS 환경 준비

### TrueNAS Scale에서 Docker 설정

1. **TrueNAS 웹 UI 접속**
   - 브라우저에서 TrueNAS IP 주소 접속 (예: `http://192.168.1.100`)

2. **Apps 설치 (Docker 포함)**
   - 좌측 메뉴에서 **Apps** 클릭
   - **Available Applications** 에서 **Docker** 또는 **Docker Compose** 검색
   - 설치 (TrueNAS Scale은 Kubernetes 기반이므로 Apps가 자동으로 Docker를 제공)

3. **셸(Shell) 접근**
   - 좌측 메뉴에서 **System Settings** → **Shell** 클릭
   - 또는 SSH로 접속: `ssh admin@truenas-ip`

### TrueNAS 경로 확인

TrueNAS에서 미디어 파일 경로를 확인합니다:

```bash
# TrueNAS 셸에서 실행
ls -la /mnt/

# 일반적인 패턴:
# /mnt/pool/media/shows
# /mnt/tank/media/shows
# /mnt/storage/media/shows
```

**중요:** 이 경로를 기록해두세요. 나중에 docker-compose.yml에서 사용합니다.

---

## 2단계: 프로젝트 파일 준비

### 옵션 A: Git에서 클론 (권장)

```bash
# TrueNAS 셸에서 실행
cd /mnt/pool/apps/  # 또는 원하는 경로
git clone https://github.com/your-username/study_english_with_sutis.git langflix
cd langflix
```

### 옵션 B: 파일 직접 업로드

1. SMB/NFS 공유를 통해 파일 업로드
2. 또는 `scp` 사용:
   ```bash
   # 로컬 Mac에서 실행
   scp -r /path/to/project admin@truenas-ip:/mnt/pool/apps/langflix
   ```

---

## 3단계: 환경 변수 설정

`deploy/` 디렉토리에 `.env` 파일을 생성합니다:

```bash
cd /mnt/pool/apps/langflix/deploy
nano .env
```

다음 내용을 입력하세요:

```bash
# TrueNAS 경로 설정 (실제 경로로 변경 필요)
# 미디어 파일이 저장된 경로
TRUENAS_MEDIA_PATH=/mnt/pool/media

# 애플리케이션 데이터 저장 경로
TRUENAS_DATA_PATH=/mnt/pool/apps/langflix

# 데이터베이스 비밀번호
POSTGRES_PASSWORD=your_secure_password_here

# Redis 비밀번호
REDIS_PASSWORD=your_redis_password_here

# API 키 (필수)
GEMINI_API_KEY=your_gemini_api_key_here

# 선택적 API 키
GOOGLE_API_KEY_1=
LEMONFOX_API_KEY=

# 포트 설정 (선택사항)
API_PORT=8000
POSTGRES_PORT=5432
REDIS_PORT=6379

# 로그 레벨
LOG_LEVEL=INFO
```

**중요:** 
- `TRUENAS_MEDIA_PATH`는 실제 TrueNAS 미디어 경로로 변경
- `TRUENAS_DATA_PATH`는 애플리케이션 데이터를 저장할 경로
- 비밀번호는 안전한 것으로 변경

---

## 4단계: 디렉토리 구조 생성

TrueNAS에서 필요한 디렉토리를 생성합니다:

```bash
# 애플리케이션 데이터 디렉토리 생성
sudo mkdir -p /mnt/pool/apps/langflix/{output,logs,cache,assets,db-backups}

# 권한 설정 (Docker 사용자에게 쓰기 권한 부여)
sudo chown -R 1000:1000 /mnt/pool/apps/langflix
sudo chmod -R 755 /mnt/pool/apps/langflix

# 미디어 경로 확인 (읽기 권한만 필요)
ls -la /mnt/pool/media/shows
```

---

## 5단계: Docker Compose 파일 확인

`deploy/docker-compose.truenas.yml` 파일이 준비되어 있습니다.

주요 설정 확인:

```yaml
volumes:
  # 미디어 파일 (읽기 전용)
  - ${TRUENAS_MEDIA_PATH}/shows:/media/shows:ro
  
  # 출력 디렉토리 (쓰기 가능)
  - ${TRUENAS_DATA_PATH}/langflix/output:/data/output:rw
```

`.env` 파일의 경로가 올바른지 확인하세요.

---

## 6단계: Docker 이미지 빌드 및 실행

### TrueNAS Scale에서 실행

```bash
cd /mnt/pool/apps/langflix/deploy

# Docker Compose로 서비스 시작
docker-compose -f docker-compose.truenas.yml up -d

# 로그 확인
docker-compose -f docker-compose.truenas.yml logs -f

# 서비스 상태 확인
docker-compose -f docker-compose.truenas.yml ps
```

### Dockge를 사용하는 경우

1. **Dockge 웹 UI 접속**
   - 브라우저에서 `http://truenas-ip:31014` 접속

2. **새 Stack 생성**
   - "+ Compose" 클릭
   - Stack Name: `langflix`

3. **docker-compose.truenas.yml 내용 복사**
   - 파일 내용을 Dockge의 YAML 에디터에 붙여넣기

4. **환경 변수 설정**
   - ".env" 섹션에 환경 변수 입력

5. **Deploy 클릭**

---

## 7단계: 서비스 확인

### API 상태 확인

```bash
# API 헬스 체크
curl http://localhost:8000/health

# 또는 브라우저에서
http://truenas-ip:8000/health
```

### API 문서 확인

브라우저에서 접속:
```
http://truenas-ip:8000/docs
```

### 컨테이너 상태 확인

```bash
# 모든 컨테이너 상태
docker ps

# 특정 서비스 로그
docker logs langflix-api
docker logs langflix-celery-worker
docker logs langflix-postgres
docker logs langflix-redis
```

### 미디어 파일 접근 확인

```bash
# 컨테이너 내부에서 미디어 파일 확인
docker exec langflix-api ls -la /media/shows

# 출력 디렉토리 확인
docker exec langflix-api ls -la /data/output
```

---

## 8단계: 네트워크 접근 설정

### TrueNAS 방화벽 설정

TrueNAS 웹 UI에서:
1. **Network** → **Firewall** 메뉴
2. 필요한 포트 열기:
   - `8000` (API)
   - `5432` (PostgreSQL - 내부 네트워크만)
   - `6379` (Redis - 내부 네트워크만)

### 외부 접근 (선택사항)

외부에서 접근하려면:
1. 라우터에서 포트 포워딩 설정
2. 또는 리버스 프록시 설정 (Nginx, Traefik 등)

---

## 문제 해결

### 컨테이너가 시작되지 않음

**확인 사항:**
```bash
# 로그 확인
docker-compose -f docker-compose.truenas.yml logs

# 특정 서비스 로그
docker logs langflix-api
```

**일반적인 문제:**

1. **경로가 존재하지 않음**
   ```bash
   # 디렉토리 생성
   sudo mkdir -p /mnt/pool/apps/langflix/{output,logs,cache}
   ```

2. **권한 문제**
   ```bash
   # Docker 사용자에게 권한 부여
   sudo chown -R 1000:1000 /mnt/pool/apps/langflix
   sudo chmod -R 755 /mnt/pool/apps/langflix
   ```

3. **미디어 경로 접근 불가**
   ```bash
   # 미디어 경로 확인
   ls -la /mnt/pool/media/shows
   
   # 컨테이너에서 확인
   docker exec langflix-api ls -la /media/shows
   ```

### 데이터베이스 연결 실패

**확인:**
```bash
# PostgreSQL 컨테이너 상태
docker ps | grep postgres

# PostgreSQL 로그
docker logs langflix-postgres

# 연결 테스트
docker exec langflix-postgres pg_isready -U langflix
```

### Redis 연결 실패

**확인:**
```bash
# Redis 컨테이너 상태
docker ps | grep redis

# Redis 로그
docker logs langflix-redis

# 연결 테스트
docker exec langflix-redis redis-cli -a your_password ping
```

### 미디어 파일을 찾을 수 없음

**확인:**
```bash
# 호스트에서 미디어 경로 확인
ls -la /mnt/pool/media/shows

# 컨테이너에서 확인
docker exec langflix-api ls -la /media/shows

# 환경 변수 확인
docker exec langflix-api env | grep LANGFLIX_STORAGE
```

**해결:**
- `.env` 파일의 `TRUENAS_MEDIA_PATH` 확인
- `docker-compose.truenas.yml`의 볼륨 마운트 경로 확인
- 미디어 경로가 실제로 존재하는지 확인

---

## 업데이트 및 유지보수

### 애플리케이션 업데이트

```bash
cd /mnt/pool/apps/langflix/deploy

# Git에서 최신 코드 가져오기
cd ..
git pull
cd deploy

# 이미지 재빌드 및 재시작
docker-compose -f docker-compose.truenas.yml build
docker-compose -f docker-compose.truenas.yml up -d

# 또는 특정 서비스만 재시작
docker-compose -f docker-compose.truenas.yml restart langflix-api
```

### 데이터베이스 백업

```bash
# PostgreSQL 백업
docker exec langflix-postgres pg_dump -U langflix langflix > /mnt/pool/apps/langflix/db-backups/backup_$(date +%Y%m%d_%H%M%S).sql

# 자동 백업 스크립트 생성 (선택사항)
```

### 로그 확인

```bash
# 모든 서비스 로그
docker-compose -f docker-compose.truenas.yml logs -f

# 특정 서비스 로그
docker-compose -f docker-compose.truenas.yml logs -f langflix-api

# 로그 파일 확인 (TrueNAS 호스트)
tail -f /mnt/pool/apps/langflix/logs/langflix.log
```

---

## 리소스 관리

### 리소스 사용량 확인

```bash
# 컨테이너 리소스 사용량
docker stats

# 디스크 사용량
docker system df
```

### 리소스 제한 조정

TrueNAS의 리소스에 맞게 `docker-compose.truenas.yml`의 리소스 제한을 조정할 수 있습니다:

```yaml
deploy:
  resources:
    limits:
      cpus: '4'      # CPU 코어 수
      memory: 8G     # 메모리 제한
```

---

## 보안 고려사항

1. **비밀번호 변경**
   - `.env` 파일의 기본 비밀번호를 안전한 것으로 변경
   - PostgreSQL, Redis 비밀번호 강화

2. **네트워크 격리**
   - PostgreSQL, Redis는 내부 네트워크에서만 접근 가능하도록 설정
   - API만 외부에 노출

3. **파일 권한**
   - 미디어 파일은 읽기 전용으로 마운트 (`:ro`)
   - 출력 디렉토리는 필요한 사용자에게만 쓰기 권한

4. **정기 업데이트**
   - Docker 이미지 정기 업데이트
   - 보안 패치 적용

---

## 요약

**배포 절차 요약:**

1. ✅ TrueNAS 환경 준비 (Docker, 경로 확인)
2. ✅ 프로젝트 파일 준비 (Git 클론 또는 업로드)
3. ✅ 환경 변수 설정 (`.env` 파일 생성)
4. ✅ 디렉토리 구조 생성
5. ✅ Docker Compose 실행
6. ✅ 서비스 확인 및 테스트

**주요 경로:**
- 미디어 파일: `/mnt/pool/media/shows` (읽기 전용)
- 애플리케이션 데이터: `/mnt/pool/apps/langflix/` (쓰기 가능)
- 로그: `/mnt/pool/apps/langflix/logs/`
- 출력: `/mnt/pool/apps/langflix/output/`

**접근 URL:**
- API: `http://truenas-ip:8000`
- API 문서: `http://truenas-ip:8000/docs`
- 헬스 체크: `http://truenas-ip:8000/health`

---

## 추가 자료

- [Dockge 설정 가이드](DOCKGE_SETUP_kor.md)
- [Docker 네트워크 미디어 경로 설정](DOCKER_NETWORK_MEDIA_kor.md)
- [CI/CD SSH 설정](CI_CD_SSH_SETUP.md)
- [API 참조 문서](../API_REFERENCE.md)

---

**마지막 업데이트:** 2025-01-30

