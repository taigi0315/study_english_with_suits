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

## 5단계: 지원 디렉토리 생성

```bash
mkdir -p /mnt/Pool_2/Projects/langflix/{output,logs,cache,assets,db-backups}
chown -R 1000:1000 /mnt/Pool_2/Projects/langflix
chmod -R 755 /mnt/Pool_2/Projects/langflix
```

UID/GID `1000:1000`은 다수 컨테이너에서 기본으로 사용하는 비특권 사용자입니다. 이미지에 따라 다른 UID를 사용한다면 값도 함께 조정하세요.

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
GOOGLE_API_KEY_1=
LEMONFOX_API_KEY=

# 네트워크 설정
API_PORT=8000
POSTGRES_PORT=5432
REDIS_PORT=6379

# 로그 레벨
LOG_LEVEL=INFO
EOF
```

실서비스 배포 전 비밀번호 및 API 키를 실제 값으로 교체하고, `.env` 파일은 소스 관리에서 제외하세요.

> **참고:** 실제 미디어 경로가 `/mnt/Media/Shows` 처럼 다르면 `TRUENAS_MEDIA_PATH=/mnt/Media` 로 지정하거나, Compose 볼륨을 직접 `- /mnt/Media/Shows:/media/shows:ro` 형태로 수정하세요. 대소문자까지 경로와 일치해야 합니다.

### YouTube OAuth 자격 증명 준비

1. Google Cloud Console에서 OAuth 자격 증명을 다운로드하여 `youtube_credentials.json` 으로 저장합니다.
2. 빈 `youtube_token.json` 파일을 생성합니다(애플리케이션이 토큰을 자동 저장).
3. 두 파일을 TrueNAS의 `${TRUENAS_DATA_PATH}/assets/` 경로로 복사합니다.
   ```bash
   scp youtube_credentials.json youtube_token.json \
       truenas_admin@truenas-ip:/mnt/Pool_2/Projects/langflix/assets/
   ```
4. Docker 컨테이너가 접근할 수 있도록 권한을 조정합니다(UID/GID 1000).
   ```bash
   sudo chown 1000:1000 /mnt/Pool_2/Projects/langflix/assets/youtube_token.json
   sudo chmod 600 /mnt/Pool_2/Projects/langflix/assets/youtube_token.json
   sudo chmod 640 /mnt/Pool_2/Projects/langflix/assets/youtube_credentials.json
   ```
5. Compose 파일에서 해당 파일을 자동으로 마운트합니다(다음 단계 참고).

---

## 7단계: Docker Compose 파일 확인

`deploy/docker-compose.truenas.yml`을 열어 볼륨 경로가 데이터세트를 가리키는지 점검합니다.

```yaml
services:
  api:
    volumes:
      - ${TRUENAS_MEDIA_PATH}:/media/shows:ro
      - ${TRUENAS_DATA_PATH}/output:/data/output:rw
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
      - ${TRUENAS_DATA_PATH}/assets:/data/assets:ro
      - ${TRUENAS_DATA_PATH}/logs:/data/logs:rw
      - ${TRUENAS_DATA_PATH}/cache:/app/cache:rw
      - ${TRUENAS_DATA_PATH}/assets/youtube_credentials.json:/app/youtube_credentials.json:ro
      - ${TRUENAS_DATA_PATH}/assets/youtube_token.json:/app/youtube_token.json:rw
```

데이터 구조가 다르다면 경로를 상황에 맞게 수정하세요.

---

## 8A단계: Docker Compose CLI로 배포(셸 방식)

```bash
cd /mnt/Pool_2/Projects/langflix/deploy

# 이미지 다운로드 혹은 빌드
docker compose -f docker-compose.truenas.yml pull
# 또는
sudo docker compose -f docker-compose.truenas.yml build

# 스택 실행
sudo docker compose -f docker-compose.truenas.yml up -d

# 상태 확인
sudo docker compose -f docker-compose.truenas.yml ps
```

> TrueNAS SCALE에서는 Docker 소켓이 root 소유이므로 `truenas_admin` 계정으로 실행할 때는 `sudo`를 함께 사용하세요. `apps` 사용자로 전환하면 `sudo` 없이 실행할 수 있습니다.

`apps` 사용자로 실행하려면:

```bash
sudo -iu apps
cd /mnt/Pool_2/Projects/langflix/deploy
docker compose -f docker-compose.truenas.yml up -d
```

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

### 컨테이너가 시작되지 않음
- `docker compose -f docker-compose.truenas.yml logs`로 에러 확인
- 데이터세트 경로 및 권한 확인 (`ls -lah /mnt/Pool_2/Projects/langflix`)
- UI 컨테이너만 실패한다면 `${TRUENAS_DATA_PATH}/assets` 존재 여부와 `LANGFLIX_API_BASE_URL`이 `langflix-api`로 해석되는지 확인

### PostgreSQL/Redis 연결 오류
- `.env` 값이 올바른지 검증
- 컨테이너 내부 테스트:
  ```bash
  docker exec langflix-postgres pg_isready -U langflix
  docker exec langflix-redis redis-cli -a "$REDIS_PASSWORD" ping
  ```

### 미디어 경로 접근 불가
- `.env`의 `TRUENAS_MEDIA_PATH` 확인
- 데이터세트가 컨테이너에서 읽기 가능하도록 권한 조정
- `docker exec langflix-api ls /media`로 마운트 확인

### UI 로그에 PostgreSQL 연결 실패 메시지가 나오는 경우
- 기본값(`DATABASE_ENABLED=false`)에서는 PostgreSQL 서비스를 사용하지 않으므로 연결 거부 메시지가 나타날 수 있습니다.
- 데이터베이스 기반 기능(쿼터 추적, 스케줄러 등)이 필요하다면 `.env`에서 `DATABASE_ENABLED=true` 로 설정하고 다음 명령으로 데이터베이스 프로필을 실행하세요.
  ```bash
  sudo docker compose -f docker-compose.truenas.yml --profile database up -d
  ```
- 데이터베이스 기능이 필요 없다면 해당 경고는 무시해도 됩니다.
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

