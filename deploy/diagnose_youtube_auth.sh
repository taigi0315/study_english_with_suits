#!/bin/bash

# YouTube 인증 문제 진단 스크립트
# Usage: ./diagnose_youtube_auth.sh

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/.env" 2>/dev/null || true
TRUENAS_DATA_PATH="${TRUENAS_DATA_PATH:-/mnt/Pool_2/Projects/langflix}"

echo -e "${BLUE}════════════════════════════════════════════════${NC}"
echo -e "${BLUE}🔍 YouTube 인증 문제 진단${NC}"
echo -e "${BLUE}════════════════════════════════════════════════${NC}"
echo ""

# 1. 호스트에서 파일 확인
echo -e "${BLUE}1. 호스트 파일 확인${NC}"
CREDENTIALS_FILE="$TRUENAS_DATA_PATH/auth/youtube_credentials.json"
echo "   경로: $CREDENTIALS_FILE"

if [ -f "$CREDENTIALS_FILE" ]; then
    echo -e "   ${GREEN}✅ 파일 존재${NC}"
    FILE_SIZE=$(stat -f%z "$CREDENTIALS_FILE" 2>/dev/null || stat -c%s "$CREDENTIALS_FILE" 2>/dev/null || echo "0")
    echo "   파일 크기: $FILE_SIZE bytes"
    
    if [ "$FILE_SIZE" -eq 0 ]; then
        echo -e "   ${RED}❌ 파일이 비어있음!${NC}"
    else
        echo -e "   ${GREEN}✅ 파일 크기 정상${NC}"
        # JSON 유효성 확인
        if python3 -m json.tool "$CREDENTIALS_FILE" > /dev/null 2>&1; then
            echo -e "   ${GREEN}✅ JSON 형식 유효${NC}"
        else
            echo -e "   ${RED}❌ JSON 형식 오류${NC}"
        fi
    fi
    
    # 파일 권한 확인
    PERMS=$(ls -l "$CREDENTIALS_FILE" 2>/dev/null | awk '{print $1, $3, $4}')
    echo "   권한: $PERMS"
else
    echo -e "   ${RED}❌ 파일 없음${NC}"
    exit 1
fi

echo ""

# 2. Docker 컨테이너 상태 확인
echo -e "${BLUE}2. Docker 컨테이너 상태${NC}"
if sudo docker ps | grep -q "langflix-ui"; then
    echo -e "   ${GREEN}✅ langflix-ui 컨테이너 실행 중${NC}"
else
    echo -e "   ${RED}❌ langflix-ui 컨테이너가 실행 중이 아님${NC}"
    exit 1
fi

if sudo docker ps | grep -q "langflix-api"; then
    echo -e "   ${GREEN}✅ langflix-api 컨테이너 실행 중${NC}"
else
    echo -e "   ${YELLOW}⚠️  langflix-api 컨테이너가 실행 중이 아님${NC}"
fi

echo ""

# 3. 컨테이너 내부 파일 확인
echo -e "${BLUE}3. 컨테이너 내부 파일 확인 (langflix-ui)${NC}"
CONTAINER_PATH="/app/auth/youtube_credentials.json"

# 파일 존재 확인
if sudo docker exec langflix-ui test -f "$CONTAINER_PATH" 2>/dev/null; then
    echo -e "   ${GREEN}✅ 파일 존재: $CONTAINER_PATH${NC}"
    
    # 파일 크기 확인
    CONTAINER_SIZE=$(sudo docker exec langflix-ui stat -c%s "$CONTAINER_PATH" 2>/dev/null || echo "0")
    echo "   컨테이너 내 파일 크기: $CONTAINER_SIZE bytes"
    
    if [ "$CONTAINER_SIZE" -eq 0 ]; then
        echo -e "   ${RED}❌ 컨테이너 내 파일이 비어있음!${NC}"
    else
        echo -e "   ${GREEN}✅ 컨테이너 내 파일 크기 정상${NC}"
    fi
    
    # 파일 읽기 가능 여부
    if sudo docker exec langflix-ui test -r "$CONTAINER_PATH" 2>/dev/null; then
        echo -e "   ${GREEN}✅ 파일 읽기 가능${NC}"
    else
        echo -e "   ${RED}❌ 파일 읽기 불가${NC}"
    fi
    
    # 파일 내용 확인 (처음 5줄)
    echo ""
    echo "   파일 내용 (처음 5줄):"
    sudo docker exec langflix-ui head -5 "$CONTAINER_PATH" 2>/dev/null || echo "   읽기 실패"
    
    # JSON 유효성 확인
    if sudo docker exec langflix-ui python3 -m json.tool "$CONTAINER_PATH" > /dev/null 2>&1; then
        echo -e "   ${GREEN}✅ JSON 형식 유효${NC}"
    else
        echo -e "   ${RED}❌ JSON 형식 오류${NC}"
        echo "   오류 상세:"
        sudo docker exec langflix-ui python3 -m json.tool "$CONTAINER_PATH" 2>&1 | head -10 || true
    fi
else
    echo -e "   ${RED}❌ 파일 없음: $CONTAINER_PATH${NC}"
    echo ""
    echo "   컨테이너 내 /app/auth/ 디렉토리 내용:"
    sudo docker exec langflix-ui ls -la /app/auth/ 2>/dev/null || echo "   디렉토리 없음"
fi

echo ""

# 4. 환경 변수 확인
echo -e "${BLUE}4. 환경 변수 확인${NC}"
YOUTUBE_CREDS_ENV=$(sudo docker exec langflix-ui printenv YOUTUBE_CREDENTIALS_FILE 2>/dev/null || echo "설정 안 됨")
echo "   YOUTUBE_CREDENTIALS_FILE: $YOUTUBE_CREDS_ENV"

YOUTUBE_TOKEN_ENV=$(sudo docker exec langflix-ui printenv YOUTUBE_TOKEN_FILE 2>/dev/null || echo "설정 안 됨")
echo "   YOUTUBE_TOKEN_FILE: $YOUTUBE_TOKEN_ENV"

echo ""

# 5. Python 코드에서 경로 확인
echo -e "${BLUE}5. Python 코드에서 경로 확인${NC}"
echo "   Python에서 감지하는 경로:"
sudo docker exec langflix-ui python3 -c "
import os
is_docker = os.path.exists('/app') or os.getenv('DOCKER_ENV') == 'true'
if is_docker:
    creds_path = '/app/auth/youtube_credentials.json'
else:
    creds_path = 'auth/youtube_credentials.json'
print(f'   감지된 환경: Docker={is_docker}')
print(f'   사용할 경로: {creds_path}')
print(f'   파일 존재: {os.path.exists(creds_path)}')
if os.path.exists(creds_path):
    size = os.path.getsize(creds_path)
    print(f'   파일 크기: {size} bytes')
    print(f'   읽기 가능: {os.access(creds_path, os.R_OK)}')
" 2>/dev/null || echo "   Python 실행 실패"

echo ""

# 6. Docker Compose 마운트 확인
echo -e "${BLUE}6. Docker Compose 마운트 확인${NC}"
echo "   docker-compose.truenas.yml에서 설정된 마운트:"
grep -A 2 "youtube_credentials.json" "$SCRIPT_DIR/docker-compose.truenas.yml" | grep -v "^--" || echo "   마운트 설정 없음"

echo ""

# 7. 컨테이너 로그 확인 (최근 오류)
echo -e "${BLUE}7. 최근 컨테이너 로그 (YouTube 관련)${NC}"
echo "   langflix-ui 로그:"
sudo docker logs langflix-ui 2>&1 | grep -i "youtube\|credentials\|auth" | tail -10 || echo "   관련 로그 없음"

echo ""

# 8. 요약 및 권장 사항
echo -e "${BLUE}════════════════════════════════════════════════${NC}"
echo -e "${BLUE}📋 진단 요약${NC}"
echo -e "${BLUE}════════════════════════════════════════════════${NC}"

# 문제 체크
ISSUES=0

if [ ! -f "$CREDENTIALS_FILE" ]; then
    echo -e "${RED}❌ 호스트에 파일이 없음${NC}"
    ISSUES=$((ISSUES + 1))
fi

if [ -f "$CREDENTIALS_FILE" ] && [ "$FILE_SIZE" -eq 0 ]; then
    echo -e "${RED}❌ 호스트 파일이 비어있음${NC}"
    ISSUES=$((ISSUES + 1))
fi

if ! sudo docker exec langflix-ui test -f "$CONTAINER_PATH" 2>/dev/null; then
    echo -e "${RED}❌ 컨테이너 내 파일이 없음 (마운트 문제 가능)${NC}"
    ISSUES=$((ISSUES + 1))
fi

if [ "$ISSUES" -eq 0 ]; then
    echo -e "${GREEN}✅ 기본 검사 통과${NC}"
    echo ""
    echo "   다음 단계:"
    echo "   1. 웹 UI에서 YouTube 로그인 시도"
    echo "   2. 브라우저 개발자 도구에서 네트워크 오류 확인"
    echo "   3. 컨테이너 로그 확인: sudo docker logs langflix-ui -f"
else
    echo -e "${YELLOW}⚠️  $ISSUES 개의 문제 발견${NC}"
    echo ""
    echo "   해결 방법:"
    echo "   1. 파일이 없거나 비어있으면: 실제 OAuth2 자격 증명 파일 복사"
    echo "   2. 마운트 문제면: 컨테이너 재시작"
    echo "      sudo docker compose -f $SCRIPT_DIR/docker-compose.truenas.yml restart"
fi

echo ""

