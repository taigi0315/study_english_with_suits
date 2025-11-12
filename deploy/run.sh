#!/bin/bash

# LangFlix TrueNAS Deployment - Start Script
# Usage: ./run.sh

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

# YouTube 자격 증명 파일 확인
echo ""
echo -e "${BLUE}🔐 YouTube 자격 증명 파일 확인 중...${NC}"
if [ -f "$TRUENAS_DATA_PATH/assets/youtube_credentials.json" ]; then
    echo -e "${GREEN}✅ youtube_credentials.json 발견${NC}"
else
    echo -e "${YELLOW}⚠️  youtube_credentials.json 없음${NC}"
    echo "   YouTube 기능을 사용하려면 이 파일이 필요합니다"
fi

if [ -f "$TRUENAS_DATA_PATH/assets/youtube_token.json" ]; then
    echo -e "${GREEN}✅ youtube_token.json 발견${NC}"
else
    echo -e "${YELLOW}⚠️  youtube_token.json 없음 (첫 로그인 시 자동 생성됨)${NC}"
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

# Docker Compose 시작
echo ""
echo -e "${GREEN}Docker Compose 시작 중...${NC}"
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

