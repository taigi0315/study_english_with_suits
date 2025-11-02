# Dockge를 사용한 LangFlix 설정 가이드

## 개요

TrueNAS의 Dockge를 사용하여 LangFlix를 Docker로 실행하는 방법입니다.

## 전제 조건

1. TrueNAS에 Dockge가 설치되어 있어야 합니다
2. 미디어 파일 경로 확인 (`192.168.86.43/media/shows`가 TrueNAS에서 어떻게 마운트되어 있는지)
3. Docker 이미지 빌드 또는 레지스트리에서 가져오기

## 단계별 설정

### 1단계: 미디어 경로 확인

TrueNAS 셸에서 미디어 경로를 확인합니다:

```bash
# TrueNAS 셸 접속 후
ls -la /mnt/

# 미디어 경로 찾기 (예시)
# /mnt/pool/media/shows 또는
# /mnt/tank/media/shows 또는
# /mnt/media-server
```

### 2단계: 프로젝트 준비

**옵션 A: Git에서 클론 (권장)**
```bash
cd /mnt/pool/apps/  # 또는 원하는 경로
git clone <your-repo-url> langflix
cd langflix
```

**옵션 B: 파일 직접 업로드**
- TrueNAS 웹 UI에서 파일 업로드
- 또는 SMB/NFS 공유를 통해 업로드

### 3단계: Docker 이미지 빌드 (선택사항)

Dockge에서 빌드를 사용하지 않으려면, 미리 이미지를 빌드합니다:

```bash
cd /path/to/langflix
docker build -f Dockerfile.dev -t langflix:latest .
```

### 4단계: Dockge에서 Stack 생성

1. **Dockge 웹 UI 접속**
   - 브라우저에서 `http://192.168.86.43:31014` 접속

2. **새 Stack 생성**
   - 왼쪽 사이드바에서 "+ Compose" 클릭
   - 또는 기존 Stack 선택

3. **Stack 이름 입력**
   - Stack Name: `langflix` (소문자만)

4. **YAML 에디터에 다음 내용 입력**

```yaml
services:
  langflix:
    # 이미지 사용 (미리 빌드한 경우)
    image: langflix:latest
    
    # 또는 빌드 사용 (Dockge가 지원하는 경우)
    # build:
    #   context: /mnt/pool/apps/langflix
    #   dockerfile: Dockerfile.dev
    
    container_name: langflix-app
    restart: unless-stopped
    
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - LANGFLIX_LOG_LEVEL=INFO
      - LANGFLIX_STORAGE_LOCAL_BASE_PATH=/media/shows
    
    volumes:
      # TrueNAS의 실제 미디어 경로로 변경 필요
      - /mnt/pool/media/shows:/media/shows:ro
      
      # 설정 파일
      - /mnt/pool/apps/langflix/config.yaml:/app/config.yaml:ro
      
      # 출력 디렉토리
      - /mnt/pool/apps/langflix/output:/data/output
    
    ports:
      - "8000:8000"
      - "5000:5000"
    
    deploy:
      resources:
        limits:
          memory: 8G
          cpus: '4'
    
    healthcheck:
      test: ["CMD", "python", "-c", "import langflix; print('OK')"]
      interval: 30s
      timeout: 10s
      retries: 3
```

5. **환경 변수 설정 (.env 섹션)**

Dockge의 ".env" 섹션에 추가:

```bash
# Gemini API Key (필수)
GEMINI_API_KEY=your_gemini_api_key_here
```

### 5단계: 경로 확인 및 수정

**중요**: 다음 경로들을 TrueNAS의 실제 경로로 변경해야 합니다:

1. **미디어 경로**: 
   ```yaml
   volumes:
     - /mnt/pool/media/shows:/media/shows:ro
   ```
   → `192.168.86.43/media/shows`가 TrueNAS에서 실제로 어디에 마운트되어 있는지 확인

2. **설정 파일 경로**:
   ```yaml
   - /mnt/pool/apps/langflix/config.yaml:/app/config.yaml:ro
   ```
   → 프로젝트의 실제 경로로 변경

3. **출력 디렉토리**:
   ```yaml
   - /mnt/pool/apps/langflix/output:/data/output
   ```
   → 생성된 파일을 저장할 경로

### 6단계: 배포

1. Dockge에서 **"Deploy"** 버튼 클릭
2. 로그 확인 (Console 탭)
3. 상태 확인: `active`로 표시되는지 확인

### 7단계: 접속 확인

```bash
# API 문서
http://192.168.86.43:8000/docs

# API 상태 확인
http://192.168.86.43:8000/

# 프론트엔드 (사용하는 경우)
http://192.168.86.43:5000
```

## TrueNAS 경로 찾기

### 방법 1: 웹 UI에서 확인
1. TrueNAS 웹 UI 접속
2. Storage → Pools 메뉴
3. Pool 이름 확인 (예: `pool`, `tank`, `storage` 등)

### 방법 2: 셸에서 확인
```bash
# TrueNAS 셸에서
df -h | grep media

# 또는
mount | grep media

# 모든 마운트 포인트 확인
ls -la /mnt/
```

### 방법 3: SMB/NFS 공유 경로 확인
- TrueNAS의 Shares → SMB 또는 NFS에서 공유 경로 확인
- 실제 파일 시스템 경로는 보통 `/mnt/<pool>/<dataset>/...` 형식

## 일반적인 TrueNAS 경로 패턴

```yaml
volumes:
  # 패턴 1: 기본 pool
  - /mnt/pool/media/shows:/media/shows:ro
  
  # 패턴 2: tank pool
  - /mnt/tank/media/shows:/media/shows:ro
  
  # 패턴 3: storage pool
  - /mnt/storage/media/shows:/media/shows:ro
  
  # 패턴 4: ix-apps dataset (TrueNAS Scale)
  - /mnt/pool/ix-apps/docker-data:/media/shows:ro
```

## 문제 해결

### 컨테이너가 시작되지 않음

**확인 사항:**
```bash
# Dockge Console에서 로그 확인
# 또는 TrueNAS 셸에서
docker logs langflix-app
```

**일반적인 문제:**
1. 경로가 존재하지 않음 → 디렉토리 생성 또는 경로 수정
2. 권한 문제 → 권한 확인 및 수정
3. 이미지가 없음 → 이미지 빌드 또는 pull

### 미디어 파일을 찾을 수 없음

**확인:**
```bash
# 컨테이너 내부에서 확인
docker exec langflix-app ls -la /media/shows

# 호스트에서 확인
ls -la /mnt/pool/media/shows
```

**해결:**
- 볼륨 마운트 경로가 올바른지 확인
- 읽기 권한 확인
- 미디어 서버 경로가 실제로 TrueNAS에 마운트되어 있는지 확인

### 환경 변수가 적용되지 않음

**.env 파일 사용:**
```bash
# Dockge의 .env 섹션에
GEMINI_API_KEY=your_key_here
```

**또는 환경 변수 직접 입력:**
```yaml
environment:
  - GEMINI_API_KEY=your_key_here
```

## 최적화 팁

1. **읽기 전용 마운트**: 미디어 파일은 `:ro` 플래그 사용
2. **리소스 제한**: TrueNAS 리소스에 맞게 조정
3. **로그 관리**: 로그 디렉토리 마운트하여 로그 파일 관리
4. **네트워크 설정**: Dockge의 External Networks를 사용하여 다른 앱과 통신

## 다음 단계

1. API 문서 확인: `http://192.168.86.43:8000/docs`
2. 미디어 파일 처리 테스트
3. 모니터링 설정
4. 자동화 스크립트 작성

## 참고

- 전체 Docker Compose 예제: `deploy/docker-compose.dockge.yml`
- 네트워크 미디어 설정: `docs/deployment/DOCKER_NETWORK_MEDIA_kor.md`
- API 문서: `docs/api/README_kor.md`

