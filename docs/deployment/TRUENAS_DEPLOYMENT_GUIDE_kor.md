# TrueNAS SCALE 배포 가이드 (한국어)

## 개요

이 문서는 Linux 기반 커뮤니티 에디션인 **TrueNAS SCALE** 환경에서 LangFlix 애플리케이션을 배포하는 절차를 설명합니다. TrueNAS SCALE은 Kubernetes와 Docker 도구를 기본 제공하므로, 별도의 가상 머신 없이도 LangFlix 스택을 직접 실행할 수 있습니다. 본 문서는 두 가지 지원 방법을 안내합니다.

1. **Docker Compose CLI (권장)**: SCALE 셸에서 `docker compose` 명령으로 관리
2. **Apps → Docker Compose App (GUI)**: 웹 UI의 Apps 기능으로 Compose 파일 불러오기

운영 방식에 맞는 방법을 선택하면 됩니다. 두 방법 모두 TrueNAS 데이터세트를 마운트하여 미디어, 출력, 로그, 백업 데이터를 관리합니다. 예시 경로는 다음과 같이 `/mnt/Pool_2/Projects/langflix`에 프로젝트가 위치한다고 가정합니다.

```bash
truenas_admin@truenas[/mnt/Pool_2/Projects/langflix]$ pwd
/mnt/Pool_2/Projects/langflix
```

환경이 다르면 경로만 변경해 적용하세요.

---

## 사전 준비사항

### 플랫폼
- TrueNAS SCALE 23.10(Cobia) 이상
- TrueNAS SCALE 웹 UI 관리자 권한
- Apps 서비스 활성화(k3s + Docker)

### 스토리지
- 미디어 라이브러리(읽기 전용) 데이터세트
- LangFlix 애플리케이션 데이터(읽기/쓰기)용 데이터세트
- 필요 시 로그/백업 데이터세트를 별도로 생성하거나 애플리케이션 데이터세트 하위 디렉터리로 구성

### 인증 정보
- PostgreSQL 비밀번호
- Redis 비밀번호
- Gemini API 키(선택적 외부 API 키 포함)

### 네트워크
- TrueNAS SCALE 호스트에 고정 IP 또는 DHCP 예약
- API 접근 포트(`8000` 기본값)를 LAN 방화벽에서 허용
- 외부 노출 시 리버스 프록시(선택)

---

## 1단계: TrueNAS SCALE에서 데이터세트 준비

1. **데이터세트 생성 확인**
   - 웹 UI → **Storage** → **Pools**
   - 예시 구조:
     - `mnt/Pool_2/Media` (기존 미디어 파일 저장소, 읽기 전용)
     - `mnt/Pool_2/Projects/langflix` (LangFlix 코드 및 애플리케이션 데이터)
2. **권한 설정**
   - 기본 소유자(`root:root`) 그대로 두고 컨테이너 내부에서 UID/GID 1000으로 접근하도록 구성합니다.
3. **절대 경로 기록**
   - `.env` 파일 및 Compose 볼륨 설정에 사용할 실제 경로를 메모합니다.

---

## 2단계: SCALE 셸 접속

- 웹 UI → **System Settings** → **Shell**
- 또는 SSH: `ssh root@truenas-ip`

> **팁:** Cobia 버전부터는 `apps` 전용 계정이 도입되었습니다. 보안 정책에 따라 `sudo -iu apps`로 전환해 Compose를 실행할 수 있습니다. 본 가이드는 단순화를 위해 `root` 기준으로 설명합니다.

---

## 3단계: Docker Compose CLI 확인

TrueNAS SCALE에는 Docker와 Compose 플러그인이 기본 포함되어 있지만, 다음 명령으로 상태를 확인하세요.

```bash
docker version
docker compose version
```

Compose 플러그인이 없다면 다시 설치합니다.

```bash
apt update
apt install -y docker-compose-plugin
```

SCALE에서는 꼭 필요한 패키지만 설치하고 `dist-upgrade` 등 대규모 업데이트는 피하세요.

---

## 4단계: LangFlix 리포지토리 클론

애플리케이션 데이터세트 내부에 코드를 배치합니다.

```bash
cd /mnt/Pool_2/Projects
git clone https://github.com/your-username/study_english_with_sutis.git langflix
cd langflix
```

필요 시 포크한 리포지토리를 사용하거나 특정 커밋으로 고정할 수 있습니다.

---

### 선택: 최소 배포 번들 생성

개발 PC에서 미리 간소화된 번들을 만들어 TrueNAS로 복사하고 싶다면 다음 명령을 실행하세요.

```bash
make deploy-zip                 # dist/langflix_deploy_<timestamp>.zip 생성
make deploy-zip OUTPUT=/tmp/langflix.zip INCLUDE_DOCS=1
make deploy-zip INCLUDE_MEDIA=1
```

이 ZIP에는 애플리케이션 코드, Docker/Compose 리소스, 설정 템플릿, 필수 에셋만 포함되며 가상환경, 테스트, 캐시 등 개발용 파일은 제외됩니다. 대용량 `assets/media` 라이브러리는 기본적으로 제외되며, 번들에 포함해야 할 때만 `INCLUDE_MEDIA=1` 옵션을 사용하세요.

---

## 5단계: 지원 디렉토리 생성 및 권한 설정

Docker Compose가 볼륨 마운트를 위해 필요한 디렉토리를 미리 생성하고 **반드시 올바른 권한을 설정**해야 합니다. 이 단계를 건너뛰면 컨테이너가 시작되지 않거나 파일 접근 오류가 발생합니다.

### 5-1. 디렉토리 생성

```bash
cd /mnt/Pool_2/Projects/langflix

# 필요한 디렉토리 생성
sudo mkdir -p output logs cache assets db-backups
```

### 5-2. 디렉토리 권한 설정 (중요!)

Docker 컨테이너 내부에서 사용하는 사용자는 UID/GID `1000:1000`입니다. 호스트의 파일과 디렉토리를 이 사용자가 접근할 수 있도록 권한을 설정해야 합니다.

```bash
# Docker 컨테이너 사용자(UID/GID 1000)가 접근할 수 있도록 권한 설정
sudo chown -R 1000:1000 output logs cache assets db-backups
sudo chmod -R 755 output logs cache assets db-backups
```

**권한 확인:**
```bash
ls -la /mnt/Pool_2/Projects/langflix/
# 출력 예시:
# drwxr-xr-x 1 1000 1000 output
# drwxr-xr-x 1 1000 1000 logs
# drwxr-xr-x 1 1000 1000 cache
# drwxr-xr-x 1 1000 1000 assets
# drwxr-xr-x 1 1000 1000 db-backups
```

### 5-3. TrueNAS ACL 문제 해결

TrueNAS의 ACL(접근 제어 목록) 때문에 `chmod`/`chown`이 작동하지 않을 수 있습니다. 다음 방법을 시도하세요:

**방법 1: TrueNAS 웹 UI 사용 (권장)**
1. 웹 UI → **Storage** → **Pools**
2. 데이터세트 선택 (예: `Pool_2/Projects/langflix`)
3. **Permissions** 클릭
4. 각 디렉토리(`output`, `logs`, `cache`, `assets`, `db-backups`)에 대해:
   - **User**: `1000` 또는 `apps` 선택
   - **Group**: `1000` 선택
   - **Mode**: `755` 설정
   - **Apply** 클릭

**방법 2: midclt 명령어 사용**
```bash
# TrueNAS API를 통한 권한 설정
sudo midclt call filesystem.setperm path=/mnt/Pool_2/Projects/langflix/output mode=755 user=1000 group=1000
sudo midclt call filesystem.setperm path=/mnt/Pool_2/Projects/langflix/logs mode=755 user=1000 group=1000
sudo midclt call filesystem.setperm path=/mnt/Pool_2/Projects/langflix/cache mode=755 user=1000 group=1000
sudo midclt call filesystem.setperm path=/mnt/Pool_2/Projects/langflix/assets mode=755 user=1000 group=1000
sudo midclt call filesystem.setperm path=/mnt/Pool_2/Projects/langflix/db-backups mode=755 user=1000 group=1000
```

> **참고:** `midclt` 명령어가 작동하지 않는 경우, TrueNAS 웹 UI를 사용하거나 시스템 관리자에게 문의하세요.

### 5-4. 미디어 경로 권한 설정

미디어 파일이 있는 경로도 컨테이너가 읽을 수 있도록 권한을 설정해야 합니다:

```bash
# 미디어 경로 확인 (예: /mnt/Pool_2/Media/Shows/Suits)
MEDIA_PATH="/mnt/Pool_2/Media/Shows/Suits"  # 실제 경로로 변경

# 읽기 권한 설정 (컨테이너는 읽기만 필요)
sudo chown -R 1000:1000 "$MEDIA_PATH"
sudo chmod -R 755 "$MEDIA_PATH"

# 권한 확인
ls -la "$MEDIA_PATH" | head -5
```

**컨테이너 내부에서 접근 테스트:**
```bash
# 컨테이너 시작 후 테스트
sudo docker exec langflix-api ls -lah /media/shows
# Permission denied 오류가 발생하면 미디어 경로 권한을 다시 확인하세요
```

### 5-5. YouTube 자격 증명 파일 권한 설정

YouTube 기능을 사용하려면 자격 증명 파일의 권한도 올바르게 설정해야 합니다. **`run.sh` 스크립트가 자동으로 처리합니다**, 필요시 수동으로도 설정할 수 있습니다:

**자동 설정 (권장):**
`run.sh` 스크립트는 배포를 시작할 때 YouTube 자격 증명 파일의 권한을 자동으로 설정합니다:
- `youtube_credentials.json`: 644 (읽기 전용)
- `youtube_token.json`: 600 (읽기/쓰기, 보안)

**수동 설정 (필요한 경우):**
```bash
# 파일이 존재하는지 확인
ls -la assets/youtube_credentials.json assets/youtube_token.json

# 파일 권한 설정
sudo chown 1000:1000 assets/youtube_credentials.json
sudo chown 1000:1000 assets/youtube_token.json

# youtube_credentials.json: 읽기 전용 (644)
sudo chmod 644 assets/youtube_credentials.json

# youtube_token.json: 읽기/쓰기 (600, 더 안전)
sudo chmod 600 assets/youtube_token.json

# 권한 확인
ls -la assets/youtube_*.json
# 출력 예시:
# -rw-r--r-- 1 1000 1000 youtube_credentials.json
# -rw------- 1 1000 1000 youtube_token.json
```

**컨테이너 내부에서 파일 접근 테스트:**
```bash
# 컨테이너 시작 후 테스트
sudo docker exec langflix-ui cat /app/youtube_credentials.json | head -5
# Permission denied 오류가 발생하면 파일 권한을 다시 확인하세요
```

> **중요:** UID/GID `1000:1000`은 다수 컨테이너에서 기본으로 사용하는 비특권 사용자입니다. 이미지에 따라 다른 UID를 사용한다면 값도 함께 조정하세요.

---

## 6단계: 환경 변수 파일 작성

`deploy/.env` 파일을 생성합니다.

```bash
cd /mnt/Pool_2/Projects/langflix/deploy
cat <<'EOF' > .env
# TrueNAS SCALE 데이터세트 경로
TRUENAS_MEDIA_PATH=/mnt/Pool_2/Media  # 실제 미디어 데이터세트 루트로 조정
TRUENAS_DATA_PATH=/mnt/Pool_2/Projects/langflix

# 데이터베이스 설정
POSTGRES_USER=langflix
POSTGRES_PASSWORD=change_me_securely
POSTGRES_DB=langflix

# Redis 설정
REDIS_PASSWORD=change_me_securely
LANGFLIX_REDIS_URL=redis://:${REDIS_PASSWORD}@langflix-redis:6379/0

# UI 설정
LANGFLIX_UI_PORT=5000
LANGFLIX_OUTPUT_DIR=/data/output
LANGFLIX_MEDIA_DIR=/media/shows
LANGFLIX_API_BASE_URL=http://langflix-api:8000

# 백엔드 서버 설정
UVICORN_HOST=0.0.0.0
UVICORN_PORT=8000
UVICORN_RELOAD=false

# API 키
GEMINI_API_KEY=your_gemini_api_key_here

# 네트워크 설정
API_PORT=8000
POSTGRES_PORT=5432
REDIS_PORT=6379

# 로그 레벨
LOG_LEVEL=INFO
EOF
```

실서비스 배포 전 비밀번호 및 API 키를 실제 값으로 교체하고, `.env` 파일은 소스 관리에서 제외하세요.

> **참고:** Docker Compose 파일에서 `.env` 파일은 마운트되지 않습니다. 모든 환경 변수는 `environment` 섹션을 통해 직접 전달되므로, TrueNAS ACL 권한 문제를 피할 수 있습니다. `.env` 파일은 Docker Compose가 변수를 읽어서 `environment` 섹션에 전달하는 용도로만 사용됩니다.

> **참고:** 실제 미디어 경로가 `/mnt/Media/Shows` 처럼 다르면 `TRUENAS_MEDIA_PATH=/mnt/Media` 로 지정하거나, Compose 볼륨을 직접 `- /mnt/Media/Shows:/media/shows:ro` 형태로 수정하세요. 대소문자까지 경로와 일치해야 합니다.

### YouTube OAuth 자격 증명 준비

1. Google Cloud Console에서 OAuth 자격 증명을 다운로드하여 `youtube_credentials.json` 으로 저장합니다.
   - 자세한 설정 방법은 [YouTube Setup Guide](../youtube/YOUTUBE_SETUP_GUIDE_kor.md)를 참고하세요.

2. 빈 `youtube_token.json` 파일을 생성합니다(애플리케이션이 토큰을 자동 저장).
   ```bash
   touch youtube_token.json
   ```

3. 두 파일을 TrueNAS의 `${TRUENAS_DATA_PATH}/assets/` 경로로 복사합니다.
   
   **로컬 컴퓨터에서 실행:**
   ```bash
   # SMB 마운트 사용 (macOS)
   mount_smbfs //truenas_admin@truenas-ip/Projects /tmp/truenas
   cp youtube_credentials.json youtube_token.json /tmp/truenas/langflix/assets/
   umount /tmp/truenas
   ```
   
   **또는 TrueNAS 웹 UI 사용:**
   - 웹 UI → **Storage** → **Pools** → `Pool_2/Projects/langflix/assets/`
   - 파일 업로드 기능 사용
   
   **또는 SSH/SCP 사용:**
   ```bash
   scp youtube_credentials.json youtube_token.json \
       truenas_admin@truenas-ip:/mnt/Pool_2/Projects/langflix/assets/
   ```

4. **Docker 컨테이너가 접근할 수 있도록 권한을 조정합니다(UID/GID 1000).**
   
   **TrueNAS에서 실행:**
   ```bash
   cd /mnt/Pool_2/Projects/langflix/assets
   
   # 파일 소유권 변경
   sudo chown 1000:1000 youtube_credentials.json youtube_token.json
   
   # 파일 권한 설정
   # youtube_credentials.json: 읽기 전용 (644)
   sudo chmod 644 youtube_credentials.json
   
   # youtube_token.json: 읽기/쓰기 (600, 더 안전)
   sudo chmod 600 youtube_token.json
   
   # 권한 확인
   ls -la youtube_*.json
   # 출력 예시:
   # -rw-r--r-- 1 1000 1000 youtube_credentials.json
   # -rw------- 1 1000 1000 youtube_token.json
   ```

5. **컨테이너 내부에서 파일 접근 테스트:**
   ```bash
   # 컨테이너 시작 후 테스트
   sudo docker exec langflix-ui cat /app/youtube_credentials.json | head -5
   sudo docker exec langflix-ui ls -la /app/youtube_*.json
   ```
   
   `Permission denied` 오류가 발생하면:
   - 파일 소유권이 `1000:1000`인지 확인
   - 파일 권한이 올바른지 확인 (`644` 또는 `600`)
   - TrueNAS ACL이 권한을 차단하지 않는지 확인

6. Compose 파일에서 해당 파일을 자동으로 마운트합니다(다음 단계 참고).

---

## 7단계: Docker Compose 파일 확인

`deploy/docker-compose.truenas.yml`을 열어 볼륨 경로가 데이터세트를 가리키는지 점검합니다.

```yaml
services:
  api:
    volumes:
      - ${TRUENAS_MEDIA_PATH}:/media/shows:ro
      - ${TRUENAS_DATA_PATH}/output:/data/output:rw
      - ${TRUENAS_DATA_PATH}/output:/app/output:rw
      - ${TRUENAS_DATA_PATH}/logs:/var/log/langflix:rw
      - ${TRUENAS_DATA_PATH}/cache:/data/cache:rw
  langflix-ui:
    environment:
      - LANGFLIX_API_BASE_URL=http://langflix-api:8000
      - LANGFLIX_OUTPUT_DIR=/data/output
      - LANGFLIX_MEDIA_DIR=/media/shows
    ports:
      - "${UI_PORT:-5000}:5000"
    volumes:
      - ${TRUENAS_MEDIA_PATH}:/media/shows:ro
      - ${TRUENAS_DATA_PATH}/output:/data/output:rw
      - ${TRUENAS_DATA_PATH}/output:/app/output:rw
      - ${TRUENAS_DATA_PATH}/assets:/data/assets:ro
      - ${TRUENAS_DATA_PATH}/logs:/data/logs:rw
      - ${TRUENAS_DATA_PATH}/cache:/app/cache:rw
      - ${TRUENAS_DATA_PATH}/assets/youtube_credentials.json:/app/youtube_credentials.json:ro
      - ${TRUENAS_DATA_PATH}/assets/youtube_token.json:/app/youtube_token.json:rw
```

데이터 구조가 다르다면 경로를 상황에 맞게 수정하세요.

---

## 8A단계: Docker Compose CLI로 배포(셸 방식)

### 방법 1: run.sh 스크립트 사용 (권장)

`deploy/run.sh` 스크립트를 사용하면 디렉토리 생성, 권한 설정, Docker Compose 시작을 자동으로 처리합니다.

```bash
cd /mnt/Pool_2/Projects/langflix/deploy

# 실행 권한 부여 (최초 1회)
chmod +x run.sh shutdown.sh

# 시작
./run.sh
```

스크립트는 다음을 자동으로 수행합니다:
- `.env` 파일 확인
- 필요한 디렉토리 생성 (`output`, `logs`, `cache`, `assets`, `db-backups`)
- 디렉토리 권한 설정 (UID/GID 1000:1000)
- YouTube 자격 증명 파일 확인
- Docker Compose 시작
- 컨테이너 상태 확인

### 방법 2: 수동 실행

**기본 방법 (권장):** `truenas_admin` 계정에서 `sudo` 사용

```bash
cd /mnt/Pool_2/Projects/langflix/deploy

# 이미지 다운로드 혹은 빌드
sudo docker compose -f docker-compose.truenas.yml pull
# 또는
sudo docker compose -f docker-compose.truenas.yml build

# 스택 실행
sudo docker compose -f docker-compose.truenas.yml up -d

# 상태 확인
sudo docker compose -f docker-compose.truenas.yml ps
```

> **참고:** TrueNAS SCALE에서는 Docker 소켓이 root 소유이므로 `truenas_admin` 계정으로 실행할 때는 `sudo`를 함께 사용해야 합니다. 일부 시스템에서는 `apps` 사용자가 비활성화되어 있을 수 있으므로, `sudo`를 사용하는 방법을 권장합니다.

**대안 (선택사항):** `apps` 사용자 사용 (시스템에서 활성화된 경우에만)

```bash
# apps 사용자로 전환 (시스템에서 활성화된 경우에만 작동)
sudo -iu apps
cd /mnt/Pool_2/Projects/langflix/deploy
docker compose -f docker-compose.truenas.yml up -d
```

> **주의:** `apps` 사용자가 "currently not available" 오류가 발생하면, 시스템 관리자가 해당 사용자를 활성화해야 합니다. 대부분의 경우 `sudo`를 사용하는 방법이 더 간단합니다.

---

## 8B단계: Apps → Docker Compose App으로 배포(GUI 방식)

1. 웹 UI → **Apps** → **Launch Docker Compose App**
2. **Application Name:** `langflix`
3. `docker-compose.truenas.yml` 내용을 붙여넣기
4. **Use Custom Environment File**을 켜고 `.env` 내용을 입력하거나 키/값으로 직접 지정
5. **Volumes** 섹션에서 경로 매핑 확인
6. **Install** 클릭 → `ix-applications` 데이터세트에 Compose 앱이 생성됩니다.

> GUI 방식은 Apps 대시보드에서 상태를 확인하고 관리하고 싶은 경우 유용합니다.

---

## 9단계: 서비스 검증

```bash
curl http://truenas-ip:8000/health
curl http://truenas-ip:8000/docs
curl http://truenas-ip:5000/
```

로그 확인:

```bash
docker compose -f docker-compose.truenas.yml logs -f api
docker compose -f docker-compose.truenas.yml logs -f langflix-ui
docker compose -f docker-compose.truenas.yml logs -f postgres
```

컨테이너 마운트 확인:

```bash
docker exec -it langflix-api ls -lah /media/shows
docker exec -it langflix-api ls -lah /data/output
docker exec -it langflix-ui ls -lah /data/output
```

---

## 10단계: 네트워크 및 보안

- SCALE 방화벽 또는 상위 라우터에서 `8000`(API), `5000`(UI) 포트 접근 허용
- 외부 서비스 노출 시 Traefik, Nginx Proxy Manager, Caddy 등 리버스 프록시 구성
- `.env` 파일과 비밀 값은 접근 권한을 제한
- PostgreSQL/Redis 비밀번호는 주기적으로 변경

---

## 11단계: 운영 및 유지보수

### LangFlix 업데이트

```bash
cd /mnt/Pool_2/Projects/langflix
git pull
cd deploy
docker compose -f docker-compose.truenas.yml pull
docker compose -f docker-compose.truenas.yml up -d
```

### 개발 사이클 / 환경 초기화

구성을 변경하거나 새로 빌드하기 전에 기존 컨테이너와 리소스를 정리하세요.

**방법 1: shutdown.sh 스크립트 사용 (권장)**

```bash
cd /mnt/Pool_2/Projects/langflix/deploy

# 컨테이너만 정지 (볼륨 유지)
./shutdown.sh

# 볼륨까지 삭제 (Redis 데이터 초기화)
./shutdown.sh --remove-volumes

# 이미지까지 제거 (강제 재빌드)
./shutdown.sh --remove-volumes --remove-images
```

**방법 2: 수동 실행**

```bash
cd /mnt/Pool_2/Projects/langflix/deploy

# 컨테이너만 정지(볼륨 유지)
sudo docker compose -f docker-compose.truenas.yml down

# 선택: 볼륨까지 삭제(예: Redis 데이터 초기화)
sudo docker compose -f docker-compose.truenas.yml down -v

# 선택: 빌드 이미지를 제거해 강제 재빌드
sudo docker compose -f docker-compose.truenas.yml down --rmi local
sudo docker system prune -f
```

### 백업

```bash
docker exec langflix-postgres pg_dump -U langflix langflix \
  > /mnt/Pool_2/Projects/langflix/db-backups/backup_$(date +%Y%m%d_%H%M%S).sql
```

TrueNAS의 스냅샷 및 복제 기능으로 데이터세트를 주기적으로 백업하세요.

### 모니터링

```bash
docker compose -f docker-compose.truenas.yml logs -f
docker stats
```

장기 모니터링이 필요하면 Prometheus/Grafana 연계를 고려합니다.

---

## 문제 해결

### 디렉토리 생성 권한 오류 (`chmod: operation not permitted`)

**증상:**
```
Error response from daemon: error while creating mount source path '/mnt/Pool_2/Projects/langflix/output': chmod /mnt/Pool_2/Projects/langflix/output: operation not permitted
```

**원인:**
- Docker Compose가 볼륨 마운트를 위해 디렉토리를 자동 생성하려고 시도하지만, TrueNAS ACL 때문에 권한 설정이 실패합니다.
- 디렉토리가 이미 존재하더라도 소유권이 올바르지 않으면 같은 오류가 발생할 수 있습니다.

**해결 방법:**

1. **필요한 디렉토리를 미리 생성하고 권한 설정:**
   ```bash
   cd /mnt/Pool_2/Projects/langflix
   
   # 디렉토리 생성
   sudo mkdir -p output logs cache assets db-backups
   
   # 소유권 변경 (중요!)
   sudo chown -R 1000:1000 output logs cache assets db-backups
   
   # 권한 설정
   sudo chmod -R 755 output logs cache assets db-backups
   
   # 권한 확인
   ls -la | grep -E "output|logs|cache|assets|db-backups"
   # 출력 예시:
   # drwxr-xr-x 1 1000 1000 output
   # drwxr-xr-x 1 1000 1000 logs
   # ...
   ```

2. **TrueNAS ACL 때문에 `chmod`/`chown`이 작동하지 않는 경우:**
   
   **방법 A: TrueNAS 웹 UI 사용 (권장)**
   - 웹 UI → **Storage** → **Pools** → 데이터세트 선택
   - **Permissions** 클릭
   - 각 디렉토리에 대해:
     - **User**: `1000` 또는 `apps` 선택
     - **Group**: `1000` 선택
     - **Mode**: `755` 설정
     - **Apply** 클릭
   
   **방법 B: midclt 명령어 사용**
   ```bash
   sudo midclt call filesystem.setperm path=/mnt/Pool_2/Projects/langflix/output mode=755 user=1000 group=1000
   sudo midclt call filesystem.setperm path=/mnt/Pool_2/Projects/langflix/logs mode=755 user=1000 group=1000
   sudo midclt call filesystem.setperm path=/mnt/Pool_2/Projects/langflix/cache mode=755 user=1000 group=1000
   sudo midclt call filesystem.setperm path=/mnt/Pool_2/Projects/langflix/assets mode=755 user=1000 group=1000
   sudo midclt call filesystem.setperm path=/mnt/Pool_2/Projects/langflix/db-backups mode=755 user=1000 group=1000
   ```
   
   > **참고:** `midclt` 명령어가 작동하지 않는 경우, TrueNAS 웹 UI를 사용하거나 시스템 관리자에게 문의하세요.

3. **5단계를 다시 실행한 후 Docker Compose 재시작:**
   ```bash
   cd /mnt/Pool_2/Projects/langflix/deploy
   sudo docker compose -f docker-compose.truenas.yml down
   sudo docker compose -f docker-compose.truenas.yml up -d
   ```

4. **run.sh 스크립트 사용:**
   - `run.sh` 스크립트는 디렉토리 생성과 권한 설정을 자동으로 처리합니다.
   ```bash
   cd /mnt/Pool_2/Projects/langflix/deploy
   ./run.sh
   ```

### .env 파일 권한 오류 (`Permission denied: '/app/.env'`)

**증상:**
```
Error: [Errno 13] Permission denied: '/app/.env'
```

**해결 방법:**

> **참고:** 최신 버전의 `docker-compose.truenas.yml`에서는 `.env` 파일이 컨테이너에 마운트되지 않습니다. 모든 환경 변수는 `environment` 섹션을 통해 직접 전달되므로 이 오류는 발생하지 않습니다.

만약 이 오류가 발생한다면:

1. **최신 `docker-compose.truenas.yml` 파일 사용 확인:**
   - `.env` 파일 마운트 라인이 제거되었는지 확인 (`- ../.env:/app/.env:ro` 라인이 없어야 함)
   - 최신 코드를 TrueNAS에 복사했는지 확인

2. **컨테이너 재시작:**
   ```bash
   sudo docker compose -f docker-compose.truenas.yml down
   sudo docker compose -f docker-compose.truenas.yml up -d
   ```

### 컨테이너가 시작되지 않음
- `sudo docker compose -f docker-compose.truenas.yml logs`로 에러 확인
- 데이터세트 경로 및 권한 확인 (`ls -lah /mnt/Pool_2/Projects/langflix`)
- UI 컨테이너만 실패한다면 `${TRUENAS_DATA_PATH}/assets` 존재 여부와 `LANGFLIX_API_BASE_URL`이 `langflix-api`로 해석되는지 확인

### PostgreSQL/Redis 연결 오류
- `.env` 값이 올바른지 검증
- 컨테이너 내부 테스트:
  ```bash
  docker exec langflix-postgres pg_isready -U langflix
  docker exec langflix-redis redis-cli -a "$REDIS_PASSWORD" ping
  ```

### 미디어 경로 접근 불가 (`Permission denied`)

**증상:**
```bash
sudo docker exec langflix-api ls -lah /media/shows
# ls: cannot open directory '/media/shows': Permission denied
```

**해결 방법:**

1. **미디어 경로 권한 확인 및 설정:**
   ```bash
   # 실제 미디어 경로 확인 (예: /mnt/Pool_2/Media/Shows/Suits)
   MEDIA_PATH="/mnt/Pool_2/Media/Shows/Suits"  # 실제 경로로 변경
   
   # 권한 설정
   sudo chown -R 1000:1000 "$MEDIA_PATH"
   sudo chmod -R 755 "$MEDIA_PATH"
   
   # 권한 확인
   ls -la "$MEDIA_PATH" | head -5
   ```

2. **컨테이너 내부에서 접근 테스트:**
   ```bash
   sudo docker exec langflix-api ls -lah /media/shows
   # 파일 목록이 보이면 성공
   ```

3. **TrueNAS ACL 문제인 경우:**
   - 웹 UI → **Storage** → 데이터세트 선택 → **Permissions**
   - 미디어 경로에 대해 User `1000`, Group `1000`, Mode `755` 설정
   - 또는 `midclt` 명령어 사용:
     ```bash
     sudo midclt call filesystem.setperm path=/mnt/Pool_2/Media/Shows/Suits mode=755 user=1000 group=1000
     ```

4. **`.env`의 `TRUENAS_MEDIA_PATH` 확인:**
   - 실제 미디어 파일이 있는 경로의 부모 디렉토리를 지정
   - 예: `/mnt/Pool_2/Media` (실제 파일은 `/mnt/Pool_2/Media/Shows/Suits`에 있음)

### UI 로그에 PostgreSQL 연결 실패 메시지가 나오는 경우
- 기본값(`DATABASE_ENABLED=false`)에서는 PostgreSQL 서비스를 사용하지 않으므로 연결 거부 메시지가 나타날 수 있습니다.
- 데이터베이스 기반 기능(쿼터 추적, 스케줄러 등)이 필요하다면 `.env`에서 `DATABASE_ENABLED=true` 로 설정하고 다음 명령으로 데이터베이스 프로필을 실행하세요.
  ```bash
  sudo docker compose -f docker-compose.truenas.yml --profile database up -d
  ```
- 데이터베이스 기능이 필요 없다면 해당 경고는 무시해도 됩니다.

### YouTube 자격 증명 파일 접근 오류 (`Permission denied` 또는 `OAuth URL failed to generate`)

**증상:**
```bash
sudo docker exec langflix-ui cat /app/youtube_credentials.json | head -5
# cat: /app/youtube_credentials.json: Permission denied

# 또는 UI에서:
# Error: \app\youtube_credental.json Oauth URL failed to generate
```

**해결 방법:**

> **참고:** `run.sh` 스크립트가 파일 권한을 자동으로 처리합니다. `run.sh`를 사용하는 경우, 자동으로 올바른 권한이 설정됩니다. 아래의 수동 단계는 `run.sh`를 사용하지 않거나 자동 권한 설정이 실패한 경우에만 필요합니다.

**자동 수정 (권장):**

`deploy/run.sh` 스크립트가 자동으로:
1. YouTube 자격 증명 파일 확인
2. 소유권을 `1000:1000`으로 설정 (Docker 컨테이너 사용자)
3. 권한 설정: `youtube_credentials.json`은 `644`, `youtube_token.json`은 `600`
4. `youtube_token.json`이 없으면 빈 파일 생성
5. 시작 후 컨테이너 내부에서 파일 접근 검증

다음 명령어만 실행하세요:
```bash
cd /mnt/Pool_2/Projects/langflix/deploy
./run.sh
```

**수동 수정 (자동 수정이 작동하지 않는 경우):**

1. **파일 소유권 확인:**
   ```bash
   ls -la /mnt/Pool_2/Projects/langflix/assets/youtube_*.json
   # 출력 예시:
   # -rwxrwx--- 1 changik root youtube_credentials.json  # 잘못된 소유권
   # -rw-r--r-- 1 1000 1000 youtube_credentials.json    # 올바른 소유권
   ```

2. **파일 소유권 및 권한 설정:**
   ```bash
   cd /mnt/Pool_2/Projects/langflix/assets
   
   # 소유권 변경
   sudo chown 1000:1000 youtube_credentials.json youtube_token.json
   
   # 권한 설정
   sudo chmod 644 youtube_credentials.json  # 읽기 전용
   sudo chmod 600 youtube_token.json        # 읽기/쓰기 (더 안전)
   
   # 확인
   ls -la youtube_*.json
   # 출력 예시:
   # -rw-r--r-- 1 1000 1000 youtube_credentials.json
   # -rw------- 1 1000 1000 youtube_token.json
   ```

3. **컨테이너 내부에서 접근 테스트:**
   ```bash
   # 컨테이너 재시작
   sudo docker compose -f docker-compose.truenas.yml restart langflix-ui
   
   # 파일 접근 테스트
   sudo docker exec langflix-ui cat /app/youtube_credentials.json | head -5
   sudo docker exec langflix-ui ls -la /app/youtube_*.json
   ```

4. **TrueNAS ACL 문제인 경우:**
   - 웹 UI → **Storage** → 데이터세트 선택 → **Permissions**
   - `assets/youtube_credentials.json` 파일에 대해 User `1000`, Group `1000`, Mode `644` 설정
   - `assets/youtube_token.json` 파일에 대해 User `1000`, Group `1000`, Mode `600` 설정
### 리소스 부족
- 호스트의 CPU/RAM 증설 또는 데이터세트 쿼터 조정
- Compose `deploy.resources` 섹션으로 리소스 제한/예약 설정

---

## 요약

1. TrueNAS SCALE에서 미디어 및 애플리케이션 데이터세트 준비
2. LangFlix 리포지토리 클론 후 `.env`와 볼륨 경로 설정
3. Docker Compose CLI 또는 Apps GUI로 스택 배포
4. 서비스 상태를 검증하고 접근 제어 구성
5. Git 업데이트와 Docker 이미지 갱신, 데이터세트 스냅샷으로 유지보수

TrueNAS SCALE은 ZFS 기반 스토리지의 안정성을 유지하면서 컨테이너 워크로드를 효율적으로 운영할 수 있는 플랫폼입니다.

**접속 URL**
- API: `http://truenas-ip:8000`
- API 문서: `http://truenas-ip:8000/docs`
- LangFlix UI 대시보드: `http://truenas-ip:5000`

---

## 추가 자료

- TrueNAS SCALE 공식 문서: <https://www.truenas.com/docs/scale/>
- Docker Compose App 가이드: <https://www.truenas.com/docs/scale/scaletutorials/dockercompose/>
- LangFlix 프로젝트 문서: `docs/project.md`

---

**마지막 업데이트:** 2025-11-10

