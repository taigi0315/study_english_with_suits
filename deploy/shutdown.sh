#!/bin/bash

# LangFlix TrueNAS Deployment - Shutdown Script
# Usage: ./shutdown.sh [--remove-volumes] [--remove-images]

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$SCRIPT_DIR/docker-compose.truenas.yml"

echo -e "${BLUE}════════════════════════════════════════════════${NC}"
echo -e "${BLUE}🛑 LangFlix TrueNAS Deployment - Shutdown${NC}"
echo -e "${BLUE}════════════════════════════════════════════════${NC}"
echo ""

# 인자 파싱
REMOVE_VOLUMES=false
REMOVE_IMAGES=false

for arg in "$@"; do
    case $arg in
        --remove-volumes|-v)
            REMOVE_VOLUMES=true
            ;;
        --remove-images|-i)
            REMOVE_IMAGES=true
            ;;
        --help|-h)
            echo "사용법: $0 [옵션]"
            echo ""
            echo "옵션:"
            echo "  --remove-volumes, -v    볼륨도 함께 제거"
            echo "  --remove-images, -i     이미지도 함께 제거"
            echo "  --help, -h              이 도움말 표시"
            echo ""
            exit 0
            ;;
        *)
            echo -e "${RED}알 수 없는 옵션: $arg${NC}"
            echo "사용법: $0 --help"
            exit 1
            ;;
    esac
done

# Docker Compose 파일 확인
if [ ! -f "$COMPOSE_FILE" ]; then
    echo -e "${RED}❌ 오류: docker-compose.truenas.yml 파일을 찾을 수 없습니다${NC}"
    echo "   경로: $COMPOSE_FILE"
    exit 1
fi

cd "$SCRIPT_DIR"

# 현재 실행 중인 컨테이너 확인
RUNNING_CONTAINERS=$(sudo docker compose -f "$COMPOSE_FILE" ps --format json 2>/dev/null | grep -c '"State":"running"' || echo "0")

if [ "$RUNNING_CONTAINERS" -eq 0 ]; then
    echo -e "${YELLOW}⚠️  실행 중인 컨테이너가 없습니다${NC}"
    exit 0
fi

echo -e "${BLUE}📊 현재 실행 중인 컨테이너:${NC}"
sudo docker compose -f "$COMPOSE_FILE" ps

echo ""

# 확인 메시지
if [ "$REMOVE_VOLUMES" = true ]; then
    echo -e "${YELLOW}⚠️  경고: 볼륨도 함께 제거됩니다 (데이터 손실 가능)${NC}"
fi

if [ "$REMOVE_IMAGES" = true ]; then
    echo -e "${YELLOW}⚠️  경고: 이미지도 함께 제거됩니다${NC}"
fi

read -p "정말로 중지하시겠습니까? (y/N): " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "취소됨"
    exit 0
fi

# Docker Compose 중지
echo ""
echo -e "${BLUE}🛑 컨테이너 중지 중...${NC}"

if [ "$REMOVE_VOLUMES" = true ]; then
    sudo docker compose -f "$COMPOSE_FILE" down -v
    echo -e "${GREEN}✅ 컨테이너 및 볼륨 제거 완료${NC}"
else
    sudo docker compose -f "$COMPOSE_FILE" down
    echo -e "${GREEN}✅ 컨테이너 중지 완료${NC}"
fi

# 이미지 제거 (선택사항)
if [ "$REMOVE_IMAGES" = true ]; then
    echo ""
    echo -e "${BLUE}🗑️  이미지 제거 중...${NC}"
    sudo docker compose -f "$COMPOSE_FILE" down --rmi local
    echo -e "${GREEN}✅ 이미지 제거 완료${NC}"
fi

# 정리 (선택사항)
echo ""
read -p "사용하지 않는 Docker 리소스도 정리하시겠습니까? (y/N): " cleanup_confirm
if [[ "$cleanup_confirm" =~ ^[Yy]$ ]]; then
    echo -e "${BLUE}🧹 Docker 리소스 정리 중...${NC}"
    sudo docker system prune -f
    echo -e "${GREEN}✅ 정리 완료${NC}"
fi

echo ""
echo -e "${BLUE}════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ LangFlix 중지 완료${NC}"
echo -e "${BLUE}════════════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}📝 다시 시작하려면:${NC}"
echo "   ./run.sh"
echo ""



