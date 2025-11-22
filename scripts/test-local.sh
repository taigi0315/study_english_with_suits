#!/bin/bash

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 LangFlix 로컬 테스트 환경 시작${NC}"
echo ""

# 포트 확인 함수
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1 ; then
        echo -e "${RED}❌ 포트 $port 가 이미 사용 중입니다${NC}"
        echo "   실행 중인 프로세스:"
        lsof -Pi :$port -sTCP:LISTEN
        return 1
    else
        echo -e "${GREEN}✅ 포트 $port 사용 가능${NC}"
        return 0
    fi
}

# 포트 확인
echo "포트 확인 중..."
if ! check_port 8000; then
    echo -e "${YELLOW}💡 포트 8000을 사용하는 프로세스를 종료하거나 다른 포트를 사용하세요${NC}"
    exit 1
fi

if ! check_port 5000; then
    echo -e "${YELLOW}💡 macOS의 경우: System Preferences -> General -> AirDrop & Handoff -> AirPlay Receiver 비활성화${NC}"
    echo -e "${YELLOW}   또는 다른 포트 사용: export LANGFLIX_UI_PORT=5001${NC}"
    exit 1
fi

# 필요한 디렉토리 생성
echo ""
echo "필요한 디렉토리 생성 중..."
mkdir -p output logs cache assets/media
echo -e "${GREEN}✅ 디렉토리 생성 완료${NC}"

# 환경 변수 설정
export LANGFLIX_API_BASE_URL=http://localhost:8000
export REDIS_URL=redis://localhost:6379/0
export LANGFLIX_OUTPUT_DIR=./output
export LANGFLIX_MEDIA_DIR=./assets/media
export YOUTUBE_CREDENTIALS_FILE=./auth/youtube_credentials.json
export YOUTUBE_TOKEN_FILE=./auth/youtube_token.json
export LANGFLIX_UI_PORT=5000
export LANGFLIX_UI_OPEN_BROWSER=false

# YouTube 자격 증명 파일 확인
if [ ! -f "./auth/youtube_credentials.json" ]; then
    echo -e "${YELLOW}⚠️  경고: ./auth/youtube_credentials.json 파일이 없습니다${NC}"
    echo "   YouTube 기능을 테스트하려면 이 파일이 필요합니다"
fi

echo ""
echo -e "${GREEN}환경 변수 설정 완료${NC}"
echo ""

# 종료 함수
cleanup() {
    echo ""
    echo -e "${YELLOW}종료 중...${NC}"
    if [ ! -z "$API_PID" ]; then
        kill $API_PID 2>/dev/null
        echo "API 서버 종료됨"
    fi
    if [ ! -z "$UI_PID" ]; then
        kill $UI_PID 2>/dev/null
        echo "UI 서버 종료됨"
    fi
    exit 0
}

# 종료 시그널 처리
trap cleanup SIGINT SIGTERM

# API 서버 백그라운드 실행
echo -e "${GREEN}📡 API 서버 시작 중...${NC}"
python -m langflix.api.main > /tmp/langflix-api.log 2>&1 &
API_PID=$!

# API 서버 시작 대기
echo "API 서버 시작 대기 중..."
sleep 5

# API 서버 상태 확인
if ! kill -0 $API_PID 2>/dev/null; then
    echo -e "${RED}❌ API 서버 시작 실패${NC}"
    echo "로그 확인:"
    tail -20 /tmp/langflix-api.log
    exit 1
fi

# Health check
if curl -s http://localhost:8000/health > /dev/null; then
    echo -e "${GREEN}✅ API 서버 정상 작동 중 (PID: $API_PID)${NC}"
else
    echo -e "${YELLOW}⚠️  API 서버가 시작되었지만 health check 실패${NC}"
    echo "로그 확인:"
    tail -10 /tmp/langflix-api.log
fi

# UI 서버 실행
echo ""
echo -e "${GREEN}🌐 UI 서버 시작 중...${NC}"
python -m langflix.youtube.web_ui > /tmp/langflix-ui.log 2>&1 &
UI_PID=$!

# UI 서버 시작 대기
sleep 3

# UI 서버 상태 확인
if ! kill -0 $UI_PID 2>/dev/null; then
    echo -e "${RED}❌ UI 서버 시작 실패${NC}"
    echo "로그 확인:"
    tail -20 /tmp/langflix-ui.log
    cleanup
    exit 1
fi

echo ""
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ LangFlix 테스트 환경이 실행 중입니다${NC}"
echo -e "${GREEN}════════════════════════════════════════${NC}"
echo ""
echo "📊 서버 정보:"
echo "   - API 서버 PID: $API_PID"
echo "   - UI 서버 PID: $UI_PID"
echo ""
echo "🌐 접속 URL:"
echo "   - Frontend UI: http://localhost:5000"
echo "   - Backend API: http://localhost:8000"
echo "   - API Docs: http://localhost:8000/docs"
echo ""
echo "📝 로그 확인:"
echo "   - API 로그: tail -f /tmp/langflix-api.log"
echo "   - UI 로그: tail -f /tmp/langflix-ui.log"
echo ""
echo -e "${YELLOW}종료하려면 Ctrl+C를 누르세요${NC}"
echo ""

# 프로세스 대기
wait
