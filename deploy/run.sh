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

# assets 디렉토리 확인 및 생성
ASSETS_DIR="$TRUENAS_DATA_PATH/assets"
if [ ! -d "$ASSETS_DIR" ]; then
    echo -e "${YELLOW}⚠️  assets 디렉토리 없음, 생성 중...${NC}"
    sudo mkdir -p "$ASSETS_DIR"
    sudo chown -R 1000:1000 "$ASSETS_DIR" 2>/dev/null || true
    sudo chmod -R 755 "$ASSETS_DIR" 2>/dev/null || true
fi

# youtube_credentials.json 처리
CREDENTIALS_FILE="$ASSETS_DIR/youtube_credentials.json"
if [ -f "$CREDENTIALS_FILE" ]; then
    echo -e "${GREEN}✅ youtube_credentials.json 발견${NC}"
    # 소유권 설정 (UID/GID 1000 = Docker 컨테이너 사용자)
    if sudo chown 1000:1000 "$CREDENTIALS_FILE" 2>/dev/null; then
        echo "   소유권 설정 완료 (1000:1000)"
    else
        echo -e "${YELLOW}⚠️  소유권 설정 실패 (권한이 부족할 수 있음)${NC}"
    fi
    # 권한 설정 (644 = read-only, 컨테이너에서 읽기만 필요)
    if sudo chmod 644 "$CREDENTIALS_FILE" 2>/dev/null; then
        echo "   권한 설정 완료 (644)"
    else
        echo -e "${YELLOW}⚠️  권한 설정 실패${NC}"
    fi
    # 권한 확인
    PERMS=$(ls -l "$CREDENTIALS_FILE" 2>/dev/null | awk '{print $1, $3, $4}')
    echo "   현재 상태: $PERMS"
else
    echo -e "${YELLOW}⚠️  youtube_credentials.json 없음${NC}"
    echo "   Docker 마운트를 위해 빈 파일 생성 중..."
    # Docker Compose가 파일을 마운트하려고 하므로 빈 파일을 미리 생성
    if sudo touch "$CREDENTIALS_FILE" 2>/dev/null; then
        sudo chown 1000:1000 "$CREDENTIALS_FILE" 2>/dev/null || true
        sudo chmod 644 "$CREDENTIALS_FILE" 2>/dev/null || true
        echo "   빈 파일 생성 및 권한 설정 완료: 644"
        echo -e "${YELLOW}   ⚠️  YouTube 기능을 사용하려면 이 파일에 실제 자격 증명을 추가해야 합니다${NC}"
        echo "   참고: docs/youtube/YOUTUBE_SETUP_GUIDE_eng.md"
    else
        echo -e "${YELLOW}⚠️  파일 생성 실패 (권한이 부족할 수 있음)${NC}"
    fi
fi

# youtube_token.json 처리
TOKEN_FILE="$ASSETS_DIR/youtube_token.json"
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
    # 빈 파일을 미리 생성하여 권한 문제를 방지
    if sudo touch "$TOKEN_FILE" 2>/dev/null; then
        echo "   빈 파일 생성 완료"
        sudo chown 1000:1000 "$TOKEN_FILE" 2>/dev/null || true
        sudo chmod 600 "$TOKEN_FILE" 2>/dev/null || true
        echo "   권한 설정 완료 (1000:1000, 600)"
    else
        echo -e "${YELLOW}⚠️  파일 생성 실패 (권한이 부족할 수 있음)${NC}"
    fi
fi

# assets 디렉토리 내 모든 YouTube 관련 파일의 권한 확인 및 수정
echo ""
echo -e "${BLUE}📋 assets 디렉토리 내 YouTube 관련 파일 권한 확인 중...${NC}"
for file in "$ASSETS_DIR"/youtube_*.json; do
    if [ -f "$file" ]; then
        filename=$(basename "$file")
        # 파일명에 따라 적절한 권한 설정
        if [[ "$filename" == "youtube_credentials.json" ]]; then
            sudo chown 1000:1000 "$file" 2>/dev/null || true
            sudo chmod 644 "$file" 2>/dev/null || true
            echo "   ✅ $filename: 644"
        elif [[ "$filename" == "youtube_token.json" ]]; then
            sudo chown 1000:1000 "$file" 2>/dev/null || true
            sudo chmod 600 "$file" 2>/dev/null || true
            echo "   ✅ $filename: 600"
        else
            # 기타 YouTube 관련 파일은 기본 권한
            sudo chown 1000:1000 "$file" 2>/dev/null || true
            sudo chmod 600 "$file" 2>/dev/null || true
            echo "   ✅ $filename: 600 (default)"
        fi
    fi
done

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
    echo "다음 중 선택하세요:"
    echo "  1) 재시작 (기존 컨테이너 중지 후 시작)"
    echo "  2) 건너뛰기 (현재 상태 유지)"
    echo "  3) 취소"
    read -p "선택 (1/2/3): " choice

    case $choice in
        1)
            echo ""
            echo -e "${YELLOW}기존 컨테이너 중지 중...${NC}"
            sudo docker compose -f "$COMPOSE_FILE" down
            ;;
        2)
            echo ""
            echo -e "${GREEN}현재 상태 유지${NC}"
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
    # 컨테이너 내부에서 파일 접근 테스트
    if sudo docker exec langflix-ui test -r /app/auth/youtube_credentials.json 2>/dev/null; then
        echo -e "${GREEN}✅ youtube_credentials.json 접근 가능${NC}"
    else
        echo -e "${YELLOW}⚠️  youtube_credentials.json 접근 불가${NC}"
        echo "   파일이 없거나 권한 문제가 있을 수 있습니다"
        echo "   해결 방법:"
        echo "   1. 파일이 존재하는지 확인: ls -la $CREDENTIALS_FILE"
        echo "   2. 소유권 확인: sudo chown 1000:1000 $CREDENTIALS_FILE"
        echo "   3. 권한 확인: sudo chmod 644 $CREDENTIALS_FILE"
    fi

    if sudo docker exec langflix-ui test -r /app/auth/youtube_token.json 2>/dev/null; then
        echo -e "${GREEN}✅ youtube_token.json 접근 가능${NC}"
    else
        echo -e "${YELLOW}⚠️  youtube_token.json 접근 불가 (첫 로그인 시 생성됨)${NC}"
    fi

    # 파일 목록 확인
    echo ""
    echo "   컨테이너 내부 파일 목록:"
    sudo docker exec langflix-ui ls -la /app/auth/youtube_*.json 2>/dev/null || echo "   파일 없음"
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

