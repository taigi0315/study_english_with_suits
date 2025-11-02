# Docker 네트워크 미디어 경로 설정

## 개요

이 가이드는 LangFlix Docker 컨테이너가 네트워크 서버에 저장된 미디어 파일(`192.168.86.43/media/shows/suits` 등)에 접근하도록 설정하는 방법을 설명합니다.

## 사전 요구사항

- Docker 호스트에서 접근 가능한 네트워크 서버
- 네트워크 공유 설정 완료 (NFS, CIFS/SMB, 또는 이미 마운트됨)
- Docker 및 docker-compose 설치

## 접근 방법 옵션

### 옵션 1: 호스트에서 네트워크 경로 마운트 (권장)

Docker 호스트에 먼저 네트워크 공유를 마운트한 다음, 컨테이너에 마운트합니다.

#### 1단계: 호스트에 네트워크 공유 마운트

**NFS 사용 시:**
```bash
# NFS 클라이언트 설치 (아직 설치되지 않은 경우)
sudo apt-get install nfs-common  # Ubuntu/Debian
# 또는
sudo yum install nfs-utils       # CentOS/RHEL

# 마운트 포인트 생성
sudo mkdir -p /mnt/media-server

# NFS 공유 마운트
sudo mount -t nfs 192.168.86.43:/media/shows /mnt/media-server

# 영구적으로 설정 (/etc/fstab에 추가)
echo "192.168.86.43:/media/shows /mnt/media-server nfs defaults 0 0" | sudo tee -a /etc/fstab
```

**CIFS/SMB 사용 시 (Windows 공유):**
```bash
# CIFS 유틸리티 설치
sudo apt-get install cifs-utils  # Ubuntu/Debian
# 또는
sudo yum install cifs-utils      # CentOS/RHEL

# 마운트 포인트 생성
sudo mkdir -p /mnt/media-server

# CIFS 공유 마운트 (자격 증명 포함)
sudo mount -t cifs //192.168.86.43/media /mnt/media-server \
    -o username=your_user,password=your_password,uid=$(id -u),gid=$(id -g)

# 영구적으로 설정 (/etc/fstab에 추가)
# 자격 증명 파일 생성
sudo bash -c 'cat > /etc/cifs-credentials << EOF
username=your_user
password=your_password
EOF'
sudo chmod 600 /etc/cifs-credentials

# /etc/fstab에 추가
echo "//192.168.86.43/media /mnt/media-server cifs credentials=/etc/cifs-credentials,uid=$(id -u),gid=$(id -g) 0 0" | sudo tee -a /etc/fstab
```

#### 2단계: Docker Compose 설정

`deploy/docker-compose.media-server.yml` 업데이트:

```yaml
services:
  langflix-media:
    volumes:
      # 호스트에 마운트된 네트워크 경로 마운트
      - /mnt/media-server:/media/shows:ro  # 안전을 위해 읽기 전용
```

#### 3단계: 애플리케이션 설정

환경 변수로 스토리지 경로 설정:

```bash
# docker-compose.yml 또는 .env 파일에
LANGFLIX_STORAGE_LOCAL_BASE_PATH=/media/shows
```

또는 `config.yaml` 업데이트:

```yaml
storage:
  backend: "local"
  local:
    base_path: "/media/shows"
```

### 옵션 2: 환경 변수 설정

Dockerfile을 수정하지 않고 환경 변수로 미디어 경로를 설정합니다.

#### Docker Compose 예제

```yaml
services:
  langflix-media:
    environment:
      - LANGFLIX_STORAGE_LOCAL_BASE_PATH=/media/shows
    volumes:
      - /mnt/media-server:/media/shows:ro
```

#### Docker Run 사용

```bash
docker run -d \
  -e LANGFLIX_STORAGE_LOCAL_BASE_PATH=/media/shows \
  -v /mnt/media-server:/media/shows:ro \
  langflix:latest
```

### 옵션 3: 빌드 인자 사용 (덜 유연함)

빌드 시점에 경로가 필요하면 Dockerfile ARG 사용:

```dockerfile
ARG MEDIA_PATH=/media/shows

RUN mkdir -p ${MEDIA_PATH}
ENV LANGFLIX_STORAGE_LOCAL_BASE_PATH=${MEDIA_PATH}
```

빌드:
```bash
docker build --build-arg MEDIA_PATH=/media/shows -t langflix:latest .
```

## 설정 우선순위

LangFlix 설정 우선순위 (높은 순서부터):
1. 환경 변수 (`LANGFLIX_STORAGE_LOCAL_BASE_PATH`)
2. `config.yaml` 파일 (`storage.local.base_path`)
3. 기본값

## 예제: 전체 설정

### 1. 호스트 설정 스크립트

`deploy/setup-media-mount.sh` 생성:

```bash
#!/bin/bash
# Docker를 위한 네트워크 미디어 마운트 설정

MEDIA_SERVER="192.168.86.43"
MEDIA_SHARE="/media/shows"
MOUNT_POINT="/mnt/media-server"

# 마운트 포인트 생성
sudo mkdir -p ${MOUNT_POINT}

# NFS 공유 마운트
sudo mount -t nfs ${MEDIA_SERVER}:${MEDIA_SHARE} ${MOUNT_POINT}

# 마운트 확인
if mountpoint -q ${MOUNT_POINT}; then
    echo "✓ ${MEDIA_SERVER}:${MEDIA_SHARE}를 ${MOUNT_POINT}에 성공적으로 마운트했습니다"
    ls -la ${MOUNT_POINT}
else
    echo "✗ 네트워크 공유 마운트 실패"
    exit 1
fi
```

### 2. Docker Compose 설정

`deploy/docker-compose.media-server.yml` 사용:

```yaml
version: '3.8'

services:
  langflix-media:
    build:
      context: ..
      dockerfile: deploy/Dockerfile.ec2.with-media
    environment:
      - LANGFLIX_STORAGE_LOCAL_BASE_PATH=/media/shows
    volumes:
      - /mnt/media-server:/media/shows:ro
      - ../config.yaml:/app/config.yaml:ro
      - ./output:/data/output
```

### 3. 설정 확인

```bash
# 컨테이너 시작
docker-compose -f deploy/docker-compose.media-server.yml up -d

# 미디어 경로 접근 확인
docker exec langflix-media-app ls -la /media/shows

# 설정 확인
docker exec langflix-media-app python -c "from langflix import settings; print(settings.get_storage_local_path())"
```

## 문제 해결

### 문제: 권한 거부됨

**증상:** 컨테이너가 마운트된 파일에 접근할 수 없음.

**해결책:**
```bash
# 마운트 권한 확인
ls -la /mnt/media-server

# 소유권 조정 또는 uid/gid와 함께 바인드 마운트 사용
docker run -v /mnt/media-server:/media/shows:ro \
  --user $(id -u):$(id -g) \
  langflix:latest
```

### 문제: 네트워크 공유에 접근할 수 없음

**증상:** 네트워크 공유를 마운트할 수 없음.

**해결책:**
1. 네트워크 연결 확인: `ping 192.168.86.43`
2. 방화벽 규칙 확인
3. 서버의 공유 권한 확인
4. Docker 전에 수동으로 마운트 테스트

### 문제: 성능 저하

**증상:** 네트워크 I/O가 느림.

**해결책:**
1. 가능하면 CIFS 대신 NFS 사용
2. NFS 타임아웃 값 증가
3. 자주 접근하는 파일 캐싱 고려
4. 처리용으로는 로컬 스토리지 사용, 결과만 다시 복사

## 보안 고려사항

1. **읽기 전용 마운트**: 미디어 볼륨에 `:ro` 플래그 사용 (실수로 인한 쓰기 방지)
2. **네트워크 보안**: 네트워크 공유가 신뢰할 수 있는 네트워크에 있거나 VPN 사용
3. **자격 증명**: SMB/CIFS 자격 증명을 안전하게 저장 (명령줄이 아닌 자격 증명 파일 사용)
4. **접근 제어**: 네트워크 공유 접근을 필요한 사용자로만 제한

## 모범 사례

1. **호스트에 먼저 마운트**: 더 안정적이고 디버깅이 쉬움
2. **환경 변수 사용**: 재빌드 없이 변경 가능
3. **미디어는 읽기 전용**: 미디어 파일은 일반적으로 읽기 전용이어야 함
4. **출력 분리**: 생성된 파일은 별도 볼륨에 보관
5. **디스크 공간 모니터링**: 네트워크 마운트가 로컬 캐시를 채울 수 있음

## 참고 자료

- Docker 볼륨: https://docs.docker.com/storage/volumes/
- NFS 마운트: https://linux.die.net/man/8/mount.nfs
- CIFS 마운트: https://linux.die.net/man/8/mount.cifs
- LangFlix Storage 문서: `docs/storage/README_kor.md`

