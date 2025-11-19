# LangFlix Setup Guide

## 프로젝트 개요 (Project Overview)

LangFlix는 TV 쇼의 자막을 분석하여 영어 표현 학습용 비디오를 자동 생성하는 도구입니다.

## 빠른 시작 (Quick Start)

### 🐳 Docker로 간단 실행 (권장)

```bash
# 1. 환경 변수 설정
cp env.example .env
# .env 파일을 편집하여 GEMINI_API_KEY 설정

# 2. Docker Compose로 모든 서비스 실행
docker-compose -f docker-compose.dev.yml up -d

# 3. API 서버 확인 (선택사항)
curl http://localhost:8000/health
```

### 🚀 로컬 개발 환경

```bash
# 1. 가상환경 설정
python -m venv venv
source venv/bin/activate  # macOS/Linux
# 또는
venv\Scripts\activate     # Windows

# 2. 의존성 설치
pip install -r requirements.txt

# 3. 환경 변수 설정
cp env.example .env
# .env 파일을 편집하여 GEMINI_API_KEY 설정

# 4. 설정 파일 복사
cp config.example.yaml config.yaml

# 5. 데이터베이스 설정 (선택사항)
# PostgreSQL과 Redis가 필요합니다
```

## 설치 방법 (Installation)

### 1. 가상환경 설정
```bash
# 가상환경 생성 (이미 생성되어 있다면 생략)
python -m venv venv

# 가상환경 활성화
source venv/bin/activate  # macOS/Linux
# 또는
venv\Scripts\activate     # Windows
```

### 2. ffmpeg 설치 (비디오 처리용)
```bash
# macOS (Homebrew 사용)
brew install ffmpeg

# Ubuntu/Debian
sudo apt update
sudo apt install ffmpeg

# Windows (Chocolatey 사용)
choco install ffmpeg

# 또는 Windows에서 직접 다운로드
# https://ffmpeg.org/download.html
```

### 3. 의존성 설치
```bash
pip install -r requirements.txt
```

### 4. 환경 변수 설정
```bash
# .env 파일 생성
cp env.example .env

# .env 파일을 편집하여 API 키 설정
# GEMINI_API_KEY=your_actual_api_key_here
```

### 5. YAML 설정 파일 구성
```bash
# 예제 설정 파일 복사
cp config.example.yaml config.yaml

# 필요한 경우 config.yaml 편집하여 다음 설정 조정:
# - 대상 언어 (target_language)
# - 비디오 품질 설정 (video codec, resolution, crf)
# - 폰트 크기 (font sizes)
# - LLM 매개변수 (temperature, max_input_length)
# - 표현 제한 (min/max expressions per chunk)
```

### 6. Gemini API 키 발급
1. [Google AI Studio](https://aistudio.google.com/) 방문
2. Google 계정으로 로그인
3. API 키 생성
4. `.env` 파일에 `GEMINI_API_KEY` 설정

## 테스트 실행 (Running Tests)

```bash
# 전체 테스트 실행
python run_tests.py

# 비디오 처리 테스트
python tests/functional/test_video_clip_extraction.py

# 자막 처리 테스트
python tests/functional/test_subtitle_processing.py

# 단위 테스트 실행
python -m pytest tests/unit/

# 특정 테스트 파일 실행
python -m pytest tests/test_expression_analyzer.py -v
```

## 실행 방법 (Running the Project)

### 🎬 메인 파이프라인 실행

```bash
# 기본 실행 (자막 파일과 비디오 디렉토리 지정)
python -m langflix.main --subtitle "assets/media/Suits/Suits.S01E01.720p.HDTV.x264.srt" --video-dir "assets/media"

# 드라이 런 (JSON만 생성, 비디오 처리 없음)
python -m langflix.main --subtitle "path/to/subtitle.srt" --dry-run

# 테스트 모드 (첫 번째 청크만 처리)
python -m langflix.main --subtitle "path/to/subtitle.srt" --test-mode

# 최대 표현 수 제한
python -m langflix.main --subtitle "path/to/subtitle.srt" --max-expressions 5

# 언어 레벨 지정
python -m langflix.main --subtitle "path/to/subtitle.srt" --language-level intermediate

# 한국어 출력
python -m langflix.main --subtitle "path/to/subtitle.srt" --language-code ko
```

### 🌐 API 서버 실행

```bash
# FastAPI 서버 시작
python -m langflix.api.main

# 또는 uvicorn 직접 실행
uvicorn langflix.api.main:app --host 0.0.0.0 --port 8000 --reload

# API 문서 확인
# 브라우저에서 http://localhost:8000/docs 접속
```

### 🐳 Docker로 API 서버 실행

```bash
# Docker Compose로 모든 서비스 실행
docker-compose -f docker-compose.dev.yml up -d

# 로그 확인
docker-compose -f docker-compose.dev.yml logs -f

# 서비스 중지
docker-compose -f docker-compose.dev.yml down
```

### 📊 데이터베이스 관리

```bash
# 데이터베이스 마이그레이션
alembic upgrade head

# 새로운 마이그레이션 생성
alembic revision --autogenerate -m "Description of changes"

# 데이터베이스 초기화 (개발용)
alembic downgrade base && alembic upgrade head
```

## 사용 방법 (Usage)

### 1. 미디어 파일 준비

#### **권장 폴더 구조 (New Structure)**
```
assets/
├── media/
│   └── Suits/                    # 시리즈별 폴더
│       ├── Suits.S01E01.720p.HDTV.x264.mkv
│       ├── Suits.S01E01.720p.HDTV.x264.srt
│       ├── Suits.S01E02.720p.HDTV.x264.mkv
│       ├── Suits.S01E02.720p.HDTV.x264.srt
│       └── ...
└── subtitles/                    # 대안 자막 위치
    └── Suits - season 1.en/
        ├── Suits - 1x01 - Pilot.720p.WEB-DL.en.srt
        └── ...
```

#### **파일 요구사항**
- **자막 파일**: `.srt` 형식의 자막 파일 필요
- **비디오 파일**: `.mp4`, `.mkv`, `.avi` 등 지원 형식
- **파일명 매칭**: 자막 파일과 비디오 파일의 이름이 일치해야 함
- **폴더 구조**: 시리즈별로 정리된 폴더 구조 권장

### 2. 기본 실행 예제

```bash
# 새로운 구조 (권장)
python -m langflix.main --subtitle "assets/media/Suits/Suits.S01E01.720p.HDTV.x264.srt" --video-dir "assets/media"

# 기존 구조도 지원
python -m langflix.main --subtitle "assets/subtitles/Suits - season 1.en/Suits - 1x01 - Pilot.720p.WEB-DL.en.srt"

# 출력 디렉토리 지정
python -m langflix.main --subtitle "path/to/subtitle.srt" --output-dir "my_results"

# 상세 로그 출력
python -m langflix.main --subtitle "path/to/subtitle.srt" --verbose
```

### 3. 고급 옵션

```bash
# 드라이 런 (JSON만 생성, 비디오 처리 없음)
python -m langflix.main --subtitle path/to/subtitle.srt --dry-run

# LLM 응답 저장 (디버깅용)
python -m langflix.main --subtitle path/to/subtitle.srt --save-llm-output

# 짧은 형식 비디오 생성 건너뛰기
python -m langflix.main --subtitle path/to/subtitle.srt --no-shorts
```

## 개발 상태 (Development Status)

- ✅ **Phase 1**: 핵심 로직 및 콘텐츠 생성
  - ✅ 자막 파서 구현
  - ✅ 표현 분석기 구현 (Gemini API 연동)
  - ✅ 프롬프트 엔지니어링
  - ✅ 에러 처리 및 로깅

- ✅ **Phase 2**: 비디오 처리 및 조립 (완료)
  - ✅ 비디오 파일 매핑 및 검증
  - ✅ 프레임 정확한 비디오 클립 추출 (0.1초 정확도)
  - ✅ 이중 언어 자막 생성
  - ✅ 완전한 파이프라인 테스트

- 📋 **Phase 3**: 개선 및 사용성 (계획)
  - CLI 개선
  - 로깅 및 오류 보고
  - 문서화

## 문제 해결 (Troubleshooting)

### 기본 문제 해결

자세한 문제 해결 가이드는 다음 문서를 참조하세요:
- [TROUBLESHOOTING_KOR.md](docs/TROUBLESHOOTING_KOR.md) - 한국어 문제 해결 가이드
- [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) - English troubleshooting guide

### 자주 발생하는 문제

**API 키 오류**
```
Error: GEMINI_API_KEY not found
```
→ `.env` 파일에 올바른 API 키가 설정되어 있는지 확인

**JSON 파싱 오류**
```
Error parsing JSON from LLM response
```
→ Gemini API 응답이 올바른 JSON 형식이 아닐 수 있음. 로그를 확인하여 원본 응답 확인

**의존성 오류**
```
Import "google.generativeai" could not be resolved
```
→ `pip install -r requirements.txt` 실행하여 의존성 재설치

**비디오 파일을 찾을 수 없음**
```
Error: Could not find video file for subtitle
```
→ 비디오 및 자막 파일명이 일치하는지 확인, `--video-dir` 옵션 사용

**Docker 관련 문제**
```bash
# Docker 컨테이너 상태 확인
docker-compose -f docker-compose.dev.yml ps

# Docker 로그 확인
docker-compose -f docker-compose.dev.yml logs

# Docker 컨테이너 재시작
docker-compose -f docker-compose.dev.yml restart
```

**데이터베이스 연결 문제**
```bash
# 데이터베이스 연결 테스트
python -c "from langflix.db.session import engine; print(engine.connect())"

# 데이터베이스 마이그레이션 재실행
alembic upgrade head
```

더 많은 문제와 해결책은 [문제 해결 가이드](docs/TROUBLESHOOTING_KOR.md)를 참조하세요.

## 유용한 명령어 모음

### 🛠️ 개발 도구

```bash
# 코드 포맷팅
black langflix/
isort langflix/

# 린팅
flake8 langflix/
pylint langflix/

# 타입 체킹
mypy langflix/

# 테스트 실행
pytest tests/ -v
python run_tests.py
```

### 📁 파일 관리

```bash
# 출력 파일 정리
rm -rf output/
rm -rf cache/

# 로그 파일 확인
tail -f langflix.log

# 임시 파일 정리
find . -name "*.tmp" -delete
find . -name "__pycache__" -type d -exec rm -rf {} +
```

### 🔍 디버깅

```bash
# 상세 로그로 실행
python -m langflix.main --subtitle "path/to/subtitle.srt" --verbose --save-llm-output

# 테스트 모드로 빠른 실행
python -m langflix.main --subtitle "path/to/subtitle.srt" --test-mode --max-expressions 3

# 드라이 런으로 분석만 확인
python -m langflix.main --subtitle "path/to/subtitle.srt" --dry-run
```
