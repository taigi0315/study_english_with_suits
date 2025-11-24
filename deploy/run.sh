#!/bin/bash

# LangFlix TrueNAS Deployment - Start Script
# Usage: ./run.sh [--build|-b]
#   --build, -b: Force rebuild Docker images (useful after code changes)

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.truenas.yml"

echo -e "${BLUE}════════════════════════════════════════════════${NC}"
echo -e "${BLUE}🚀 LangFlix TrueNAS Deployment - Start${NC}"
echo -e "${BLUE}════════════════════════════════════════════════${NC}"
echo ""

# .env 파일 확인
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    echo -e "${RED}❌ 오류: .env 파일을 찾을 수 없습니다${NC}"
    echo "   경로: $SCRIPT_DIR/.env"
    echo ""
    echo "   다음 명령어로 .env 파일을 생성하세요:"
    echo "   cd $SCRIPT_DIR"
    echo "   # .env 파일 내용 참고: docs/deployment/TRUENAS_DEPLOYMENT_GUIDE_kor.md"
    exit 1
fi

echo -e "${GREEN}✅ .env 파일 확인 완료${NC}"

# .env 파일에서 경로 읽기
source "$SCRIPT_DIR/.env"
TRUENAS_DATA_PATH="${TRUENAS_DATA_PATH:-/mnt/Pool_2/Projects/langflix}"
TRUENAS_MEDIA_PATH="${TRUENAS_MEDIA_PATH:-/mnt/Pool_2/Media}"

echo ""
echo -e "${BLUE}📁 경로 확인:${NC}"
echo "   TRUENAS_DATA_PATH: $TRUENAS_DATA_PATH"
echo "   TRUENAS_MEDIA_PATH: $TRUENAS_MEDIA_PATH"

# 필요한 디렉토리 확인 및 생성
echo ""
echo -e "${BLUE}📂 디렉토리 확인 중...${NC}"
REQUIRED_DIRS=("output" "logs" "cache" "assets" "db-backups")
MISSING_DIRS=()

for dir in "${REQUIRED_DIRS[@]}"; do
    dir_path="$TRUENAS_DATA_PATH/$dir"
    if [ ! -d "$dir_path" ]; then
        echo -e "${YELLOW}⚠️  디렉토리 없음: $dir_path${NC}"
        MISSING_DIRS+=("$dir_path")
    else
        echo -e "${GREEN}✅ $dir${NC}"
    fi
done

# 없는 디렉토리 생성
if [ ${#MISSING_DIRS[@]} -gt 0 ]; then
    echo ""
    echo -e "${YELLOW}디렉토리 생성 중...${NC}"
    for dir_path in "${MISSING_DIRS[@]}"; do
        echo "   생성: $dir_path"
        sudo mkdir -p "$dir_path"
        sudo chown -R 1000:1000 "$dir_path" 2>/dev/null || true
        sudo chmod -R 755 "$dir_path" 2>/dev/null || true
    done
    echo -e "${GREEN}✅ 디렉토리 생성 완료${NC}"
fi

# YouTube 자격 증명 파일 확인 및 권한 설정
echo ""
echo -e "${BLUE}🔐 YouTube 자격 증명 파일 확인 및 권한 설정 중...${NC}"

# auth 디렉토리 확인 및 생성 (file reorganization 후)
AUTH_DIR="$TRUENAS_DATA_PATH/auth"
if [ ! -d "$AUTH_DIR" ]; then
    echo -e "${YELLOW}⚠️  auth 디렉토리 없음, 생성 중...${NC}"
    sudo mkdir -p "$AUTH_DIR"
    sudo chown -R 1000:1000 "$AUTH_DIR" 2>/dev/null || true
    sudo chmod -R 755 "$AUTH_DIR" 2>/dev/null || true
fi

# youtube_credentials.json 처리
CREDENTIALS_FILE="$AUTH_DIR/youtube_credentials.json"
if [ -f "$CREDENTIALS_FILE" ]; then
    echo -e "${GREEN}✅ youtube_credentials.json 발견${NC}"
    # 현재 파일 상태 확인
    CURRENT_OWNER=$(stat -c '%U:%G' "$CREDENTIALS_FILE" 2>/dev/null || stat -f '%Su:%Sg' "$CREDENTIALS_FILE" 2>/dev/null || echo "unknown")
    echo "   현재 소유자: $CURRENT_OWNER"
    
    # 소유권 설정 (UID/GID 1000 = Docker 컨테이너 사용자)
    # TrueNAS ZFS에서는 chown이 실패할 수 있으므로 여러 방법 시도
    if sudo chown 1000:1000 "$CREDENTIALS_FILE" 2>/dev/null; then
        echo "   소유권 설정 완료 (1000:1000)"
    else
        # ZFS ACL을 사용한 대안 시도
        echo -e "${YELLOW}⚠️  chown 실패, ZFS ACL 확인 중...${NC}"
        # 파일이 읽을 수 있는지 확인 (권한이 없어도 마운트는 가능)
        if [ -r "$CREDENTIALS_FILE" ]; then
            echo -e "${GREEN}   ✅ 파일 읽기 가능 (마운트는 정상 작동할 수 있음)${NC}"
        else
            echo -e "${YELLOW}   ⚠️  파일 읽기 불가 - ZFS 데이터셋 권한 확인 필요${NC}"
            echo "   해결 방법: TrueNAS 웹 UI에서 데이터셋 권한 설정 확인"
        fi
    fi
    # 권한 설정 (644 = read-only, 컨테이너에서 읽기만 필요)
    if sudo chmod 644 "$CREDENTIALS_FILE" 2>/dev/null; then
        echo "   권한 설정 완료 (644)"
    else
        echo -e "${YELLOW}⚠️  chmod 실패 (ZFS ACL 사용 중일 수 있음)${NC}"
    fi
    # 권한 확인
    PERMS=$(ls -l "$CREDENTIALS_FILE" 2>/dev/null | awk '{print $1, $3, $4}' || echo "권한 확인 불가")
    echo "   현재 상태: $PERMS"
else
    echo -e "${YELLOW}⚠️  youtube_credentials.json 없음${NC}"
    echo "   파일을 $AUTH_DIR/ 디렉토리에 복사/붙여넣기 해주세요"
    echo "   참고: docs/youtube/YOUTUBE_SETUP_GUIDE_eng.md"
    echo ""
    echo "   Docker Compose는 파일이 없어도 마운트를 시도하지만,"
    echo "   YouTube 기능을 사용하려면 실제 OAuth2 자격 증명 파일이 필요합니다."
fi

# youtube_token.json 처리
TOKEN_FILE="$AUTH_DIR/youtube_token.json"
if [ -f "$TOKEN_FILE" ]; then
    echo -e "${GREEN}✅ youtube_token.json 발견${NC}"
    # 소유권 설정
    if sudo chown 1000:1000 "$TOKEN_FILE" 2>/dev/null; then
        echo "   소유권 설정 완료 (1000:1000)"
    else
        echo -e "${YELLOW}⚠️  소유권 설정 실패${NC}"
    fi
    # 권한 설정 (600 = read/write, 더 안전)
    if sudo chmod 600 "$TOKEN_FILE" 2>/dev/null; then
        echo "   권한 설정 완료 (600)"
    else
        echo -e "${YELLOW}⚠️  권한 설정 실패${NC}"
    fi
    # 권한 확인
    PERMS=$(ls -l "$TOKEN_FILE" 2>/dev/null | awk '{print $1, $3, $4}')
    echo "   현재 상태: $PERMS"
else
    echo -e "${YELLOW}⚠️  youtube_token.json 없음 (첫 로그인 시 자동 생성됨)${NC}"
    echo "   첫 YouTube 로그인 시 자동으로 생성됩니다"
    echo "   디렉토리 권한 확인: $AUTH_DIR"
fi

# auth 디렉토리 내 모든 YouTube 관련 파일의 권한 확인 및 수정
echo ""
echo -e "${BLUE}📋 auth 디렉토리 내 YouTube 관련 파일 권한 확인 중...${NC}"
for file in "$AUTH_DIR"/youtube_*.json; do
    if [ -f "$file" ]; then
        filename=$(basename "$file")
        # 파일명에 따라 적절한 권한 설정
        if [[ "$filename" == "youtube_credentials.json" ]]; then
            sudo chown 1000:1000 "$file" 2>/dev/null || echo -e "${YELLOW}   ⚠️  $filename: 소유권 설정 실패 (ZFS ACL 확인 필요)${NC}"
            sudo chmod 644 "$file" 2>/dev/null || echo -e "${YELLOW}   ⚠️  $filename: 권한 설정 실패${NC}"
            # 읽기 가능 여부 확인
            if [ -r "$file" ]; then
                echo "   ✅ $filename: 읽기 가능"
            else
                echo -e "${YELLOW}   ⚠️  $filename: 읽기 불가 - 권한 문제${NC}"
            fi
        elif [[ "$filename" == "youtube_token.json" ]]; then
            sudo chown 1000:1000 "$file" 2>/dev/null || echo -e "${YELLOW}   ⚠️  $filename: 소유권 설정 실패${NC}"
            sudo chmod 600 "$file" 2>/dev/null || echo -e "${YELLOW}   ⚠️  $filename: 권한 설정 실패${NC}"
            if [ -r "$file" ]; then
                echo "   ✅ $filename: 읽기 가능"
            else
                echo -e "${YELLOW}   ⚠️  $filename: 읽기 불가${NC}"
            fi
        else
            # 기타 YouTube 관련 파일은 기본 권한
            sudo chown 1000:1000 "$file" 2>/dev/null || true
            sudo chmod 600 "$file" 2>/dev/null || true
            if [ -r "$file" ]; then
                echo "   ✅ $filename: 읽기 가능"
            else
                echo -e "${YELLOW}   ⚠️  $filename: 읽기 불가${NC}"
            fi
        fi
    fi
done

# TrueNAS ZFS 권한 문제 안내
echo ""
if [ -f "$CREDENTIALS_FILE" ] && [ ! -r "$CREDENTIALS_FILE" ]; then
    echo -e "${YELLOW}⚠️  TrueNAS ZFS 권한 문제 감지${NC}"
    echo "   해결 방법:"
    echo "   1. TrueNAS 웹 UI에서 데이터셋 권한 확인"
    echo "   2. 또는 다음 명령어로 ZFS ACL 확인:"
    echo "      zfs get aclmode $(zfs list -H -o name | grep -i langflix | head -1)"
    echo "   3. Docker 컨테이너는 파일이 마운트되면 접근 가능할 수 있습니다"
fi

# Docker Compose 파일 확인
if [ ! -f "$COMPOSE_FILE" ]; then
    echo -e "${RED}❌ 오류: docker-compose.truenas.yml 파일을 찾을 수 없습니다${NC}"
    echo "   경로: $COMPOSE_FILE"
    exit 1
fi

echo ""
echo -e "${BLUE}🐳 Docker Compose 시작 중...${NC}"
cd "$SCRIPT_DIR"

# 기존 컨테이너가 실행 중인지 확인
if sudo docker compose -f "$COMPOSE_FILE" ps | grep -q "Up"; then
    echo -e "${YELLOW}⚠️  일부 컨테이너가 이미 실행 중입니다${NC}"
    echo ""
    
    # 마운트 경로 확인 (이전 설정과 새 설정 불일치 체크)
    OLD_MOUNT_DETECTED=false
    if sudo docker inspect langflix-ui 2>/dev/null | grep -q "assets/youtube_token.json"; then
        OLD_MOUNT_DETECTED=true
        echo -e "${RED}⚠️  이전 마운트 설정 감지 (assets/ 디렉토리 사용 중)${NC}"
        echo "   컨테이너가 이전 설정으로 실행 중입니다."
        echo "   마운트 경로를 업데이트하려면 컨테이너를 재시작해야 합니다."
        echo ""
    fi
    
    echo "다음 중 선택하세요:"
    echo "  1) 재시작 (기존 컨테이너 중지 후 시작) - 마운트 설정 업데이트"
    if [ "$OLD_MOUNT_DETECTED" = true ]; then
        echo -e "     ${YELLOW}→ 권장: 마운트 경로를 auth/로 업데이트합니다${NC}"
    fi
    echo "  2) 건너뛰기 (현재 상태 유지)"
    echo "  3) 취소"
    read -p "선택 (1/2/3): " choice

    case $choice in
        1)
            echo ""
            echo -e "${YELLOW}기존 컨테이너 중지 중...${NC}"
            sudo docker compose -f "$COMPOSE_FILE" down
            echo -e "${GREEN}✅ 컨테이너 중지 완료${NC}"
            ;;
        2)
            echo ""
            echo -e "${GREEN}현재 상태 유지${NC}"
            if [ "$OLD_MOUNT_DETECTED" = true ]; then
                echo -e "${YELLOW}⚠️  경고: 이전 마운트 설정이 사용 중입니다${NC}"
                echo "   YouTube 인증이 작동하지 않을 수 있습니다."
            fi
            sudo docker compose -f "$COMPOSE_FILE" ps
            exit 0
            ;;
        3)
            echo "취소됨"
            exit 0
            ;;
        *)
            echo "잘못된 선택. 취소됨"
            exit 1
            ;;
    esac
fi

# Docker Compose 시작 (이미지 재빌드 포함)
echo ""
echo -e "${GREEN}Docker Compose 시작 중...${NC}"

# 이미지 재빌드 여부 확인
REBUILD_IMAGES=false
if [ "$1" == "--build" ] || [ "$1" == "-b" ]; then
    REBUILD_IMAGES=true
elif [ -n "$FORCE_REBUILD" ] && [ "$FORCE_REBUILD" == "true" ]; then
    REBUILD_IMAGES=true
fi

if [ "$REBUILD_IMAGES" = true ]; then
    echo -e "${YELLOW}🔨 이미지 재빌드 중...${NC}"
    sudo docker compose -f "$COMPOSE_FILE" build --no-cache
    echo -e "${GREEN}✅ 이미지 재빌드 완료${NC}"
    echo ""
fi

# 이미지 빌드 (--build 옵션이 없을 때는 변경사항 확인 후 빌드)
if [ "$REBUILD_IMAGES" != true ]; then
    echo -e "${BLUE}📦 이미지 빌드 중 (변경사항 확인)...${NC}"
    # docker-compose build는 변경사항이 있으면 자동으로 빌드하고, 없으면 스킵합니다
    sudo docker compose -f "$COMPOSE_FILE" build
    echo -e "${GREEN}✅ 이미지 빌드 완료${NC}"
fi

echo ""
echo -e "${GREEN}🚀 컨테이너 시작 중...${NC}"
sudo docker compose -f "$COMPOSE_FILE" up -d

# 잠시 대기
echo ""
echo -e "${BLUE}컨테이너 시작 대기 중...${NC}"
sleep 5

# 상태 확인
echo ""
echo -e "${BLUE}════════════════════════════════════════════════${NC}"
echo -e "${BLUE}📊 컨테이너 상태${NC}"
echo -e "${BLUE}════════════════════════════════════════════════${NC}"
sudo docker compose -f "$COMPOSE_FILE" ps

# Health check
echo ""
echo -e "${BLUE}🏥 Health Check${NC}"
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ API 서버 정상 작동${NC}"
else
    echo -e "${YELLOW}⚠️  API 서버 응답 없음 (아직 시작 중일 수 있음)${NC}"
fi

# YouTube 자격 증명 파일 접근 검증 (컨테이너 내부)
echo ""
echo -e "${BLUE}🔍 YouTube 자격 증명 파일 접근 검증 중...${NC}"
if sudo docker ps | grep -q "langflix-ui"; then
    # 마운트 경로 확인
    echo "   마운트 경로 확인 중..."
    MOUNT_INFO=$(sudo docker inspect langflix-ui 2>/dev/null | grep -A 3 "youtube_token.json" | grep "Source" | head -1)
    if echo "$MOUNT_INFO" | grep -q "auth/youtube_token.json"; then
        echo -e "${GREEN}   ✅ 올바른 마운트 경로 (auth/)${NC}"
    elif echo "$MOUNT_INFO" | grep -q "assets/youtube_token.json"; then
        echo -e "${RED}   ❌ 잘못된 마운트 경로 (assets/) - 컨테이너 재시작 필요${NC}"
        echo "      해결: ./run.sh 실행 시 옵션 1 선택"
    else
        echo -e "${YELLOW}   ⚠️  마운트 정보 확인 불가${NC}"
    fi
    
    # 컨테이너 내부에서 파일 접근 테스트
    if sudo docker exec langflix-ui test -r /app/auth/youtube_credentials.json 2>/dev/null; then
        echo -e "${GREEN}✅ youtube_credentials.json 접근 가능${NC}"
        
        # 파일 크기 확인
        CREDS_SIZE=$(sudo docker exec langflix-ui stat -c%s /app/auth/youtube_credentials.json 2>/dev/null || echo "0")
        if [ "$CREDS_SIZE" -eq 0 ]; then
            echo -e "${RED}   ❌ 파일이 비어있음!${NC}"
        else
            echo "   파일 크기: $CREDS_SIZE bytes"
        fi
    else
        echo -e "${YELLOW}⚠️  youtube_credentials.json 접근 불가${NC}"
        echo "   파일이 없거나 권한 문제가 있을 수 있습니다"
        echo "   해결 방법:"
        echo "   1. 파일이 존재하는지 확인: ls -la $CREDENTIALS_FILE"
        echo "   2. 소유권 확인: sudo chown 1000:1000 $CREDENTIALS_FILE"
        echo "   3. 권한 확인: sudo chmod 644 $CREDENTIALS_FILE"
        echo "   4. 파일을 $AUTH_DIR/ 디렉토리에 복사했는지 확인"
    fi

    if sudo docker exec langflix-ui test -r /app/auth/youtube_token.json 2>/dev/null; then
        echo -e "${GREEN}✅ youtube_token.json 접근 가능${NC}"
        
        # 파일 크기 확인
        TOKEN_SIZE=$(sudo docker exec langflix-ui stat -c%s /app/auth/youtube_token.json 2>/dev/null || echo "0")
        if [ "$TOKEN_SIZE" -eq 0 ]; then
            echo -e "${YELLOW}   ⚠️  파일이 비어있음 (첫 로그인 시 생성됨)${NC}"
        else
            echo "   파일 크기: $TOKEN_SIZE bytes"
            
            # JSON 유효성 간단 확인
            if sudo docker exec langflix-ui python3 -c "import json; json.load(open('/app/auth/youtube_token.json'))" 2>/dev/null; then
                echo -e "${GREEN}   ✅ JSON 형식 유효${NC}"
            else
                echo -e "${YELLOW}   ⚠️  JSON 형식 오류 가능 (자동으로 처리됨)${NC}"
            fi
        fi
    else
        echo -e "${YELLOW}⚠️  youtube_token.json 접근 불가 (첫 로그인 시 생성됨)${NC}"
    fi

    # 파일 목록 확인
    echo ""
    echo "   컨테이너 내부 파일 목록:"
    sudo docker exec langflix-ui ls -la /app/auth/youtube_*.json 2>/dev/null || echo "   파일 없음"
    
    # End-to-end 테스트 제안
    echo ""
    echo -e "${BLUE}📋 End-to-End 테스트 제안:${NC}"
    echo "   1. 웹 UI 접속: http://$(hostname -I | awk '{print $1}'):5000"
    echo "   2. YouTube 로그인 버튼 클릭"
    echo "   3. OAuth 인증 완료"
    echo "   4. 로그 확인: sudo docker logs langflix-ui -f"
else
    echo -e "${YELLOW}⚠️  langflix-ui 컨테이너가 실행 중이 아닙니다${NC}"
    echo "   컨테이너 시작 후 자동으로 검증됩니다"
fi

echo ""
echo -e "${BLUE}════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ LangFlix 시작 완료${NC}"
echo -e "${BLUE}════════════════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}🌐 접속 URL:${NC}"
echo "   - Frontend UI: http://$(hostname -I | awk '{print $1}'):5000"
echo "   - Backend API: http://$(hostname -I | awk '{print $1}'):8000"
echo "   - API Docs: http://$(hostname -I | awk '{print $1}'):8000/docs"
echo ""
echo -e "${BLUE}📝 유용한 명령어:${NC}"
echo "   로그 확인: sudo docker compose -f $COMPOSE_FILE logs -f"
echo "   상태 확인: sudo docker compose -f $COMPOSE_FILE ps"
echo "   중지: ./shutdown.sh"
echo ""
echo -e "${YELLOW}💡 팁:${NC}"
echo "   코드 변경 후 UI가 업데이트되지 않으면:"
echo "   ./run.sh --build    # 이미지 강제 재빌드"
echo ""

