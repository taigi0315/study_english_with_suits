# LangFlix 런북

**버전:** 2.0  
**최종 업데이트:** 2025년 1월 28일

이 런북은 CLI와 API 모드 모두에서 LangFlix를 운영하는 포괄적인 운영 가이드를 제공하며, WhisperX 통합 및 교육용 슬라이드 생성이 포함된 새로운 표현식 기반 학습 기능을 포함합니다.

---

## 목차

1. [개요](#개요)
2. [빠른 시작](#빠른-시작)
3. [CLI 모드](#cli-모드)
4. [API 모드](#api-모드)
5. [설정](#설정)
6. [스토리지 백엔드](#스토리지-백엔드)
7. [데이터베이스 통합](#데이터베이스-통합)
8. [모니터링 및 상태 확인](#모니터링-및-상태-확인)
9. [문제 해결](#문제-해결)
10. [배포](#배포)

---

## 개요

LangFlix는 두 가지 운영 모드를 지원합니다:

### CLI 모드 (개발/로컬)
- **목적**: 로컬 개발, 테스트, 단일 사용자 처리
- **스토리지**: 로컬 파일시스템 (`output/` 디렉토리)
- **데이터베이스**: 선택사항 (메타데이터 저장)
- **사용법**: 직접 비디오 처리를 위한 명령줄 인터페이스

### API 모드 (프로덕션/클라우드)
- **목적**: 웹 서비스, 다중 사용자 액세스, 확장 가능한 처리
- **스토리지**: Google Cloud Storage (설정 가능)
- **데이터베이스**: 필수 (작업 추적, 메타데이터)
- **사용법**: 비동기 비디오 처리를 위한 RESTful API

---

## 빠른 시작

### CLI 모드
```bash
# 의존성 설치
pip install -r requirements.txt

# 환경 설정
cp env.example .env
# .env 파일을 편집하여 API 키 추가

# CLI 실행
python -m langflix.main --video-dir /path/to/video --subtitle /path/to/subtitle.srt
```

### API 모드
```bash
# 의존성 설치
pip install -r requirements.txt

# 데이터베이스 및 스토리지 설정
# langflix/config/default.yaml 편집

# API 서버 시작
uvicorn langflix.api.main:app --host 0.0.0.0 --port 8000
```

---

## CLI 모드

### 기본 사용법

```bash
# 기본 처리
python -m langflix.main \
  --video-dir /path/to/video/directory \
  --subtitle /path/to/subtitle.srt \
  --language en

# 테스트 모드 (빠른 처리)
python -m langflix.main \
  --video-dir /path/to/video/directory \
  --subtitle /path/to/subtitle.srt \
  --language en \
  --test

# 숏 비디오 생성 건너뛰기
python -m langflix.main \
  --video-dir /path/to/video/directory \
  --subtitle /path/to/subtitle.srt \
  --language en \
  --no-shorts
```

### CLI 설정

**환경 변수:**
```bash
# 필수
GEMINI_API_KEY=your_gemini_api_key_here

# 선택사항
LANGFLIX_CONFIG_PATH=/path/to/custom/config.yaml
```

**설정 파일 (`langflix/config/default.yaml`):**
```yaml
# 애플리케이션 설정
app:
  show_name: "Suits"
  template_file: "expression_analysis_prompt.txt"

# 데이터베이스 (CLI용 선택사항)
database:
  enabled: false  # 데이터베이스 통합을 활성화하려면 true로 설정
  url: "postgresql://user:password@localhost:5432/langflix"

# 스토리지 (CLI는 기본적으로 로컬 사용)
storage:
  backend: "local"
  local:
    base_path: "output"
```

### CLI 출력 구조

```
output/
├── Suits/
│   └── S01E01_720p.HDTV.x264/
│       ├── metadata/
│       │   └── expressions.json
│       ├── shared/
│       │   ├── context_videos/
│       │   ├── context_slide_combined/
│       │   └── short_videos/
│       └── translations/
│           └── ko/
│               ├── subtitles/
│               ├── slides/
│               └── audio/
```

---

## API 모드

### API 서버 시작

```bash
# 개발 모드
uvicorn langflix.api.main:app --reload --host 0.0.0.0 --port 8000

# 프로덕션 모드
uvicorn langflix.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### API 엔드포인트

#### 상태 확인
```bash
# 기본 상태 확인
curl http://localhost:8000/health

# 상세 상태 확인
curl http://localhost:8000/health/detailed
```

#### 작업 관리
```bash
# 처리 작업 생성
curl -X POST "http://localhost:8000/api/v1/jobs" \
  -F "video_file=@video.mp4" \
  -F "subtitle_file=@subtitles.srt" \
  -F "language_code=en" \
  -F "show_name=Suits" \
  -F "episode_name=S01E01"

# 작업 상태 확인
curl http://localhost:8000/api/v1/jobs/{job_id}

# 작업 결과 가져오기
curl http://localhost:8000/api/v1/jobs/{job_id}/expressions

# 모든 작업 목록
curl http://localhost:8000/api/v1/jobs
```

### API 설정

**필수 환경 변수:**
```bash
# API 키
GEMINI_API_KEY=your_gemini_api_key_here

# 데이터베이스 (API용 필수)
DATABASE_URL=postgresql://user:password@localhost:5432/langflix

# 스토리지 (프로덕션용 GCS)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json
```

**API 설정 (`langflix/config/default.yaml`):**
```yaml
# 데이터베이스 (API용 필수)
database:
  enabled: true
  url: "postgresql://user:password@localhost:5432/langflix"

# 스토리지 (API용 GCS)
storage:
  backend: "gcs"
  gcs:
    bucket_name: "langflix-storage"
    credentials_path: "/path/to/service-account.json"

# API 설정
api:
  host: "0.0.0.0"
  port: 8000
  workers: 4
  cors_origins: ["*"]
```

---

## 스토리지 백엔드

### LocalStorage (CLI 기본값)
- **목적**: 로컬 개발, CLI 사용
- **설정**: `storage.backend: "local"`
- **파일**: `output/` 디렉토리에 저장
- **URL**: 로컬 파일 경로

### GoogleCloudStorage (API 기본값)
- **목적**: 프로덕션, 클라우드 스토리지
- **설정**: `storage.backend: "gcs"`
- **파일**: GCS 버킷에 저장
- **URL**: 공개 GCS URL

**GCS 설정:**
```bash
# GCS 버킷 생성
gsutil mb gs://your-langflix-bucket

# 서비스 계정 설정
# 1. Google Cloud Console에서 서비스 계정 생성
# 2. JSON 키 파일 다운로드
# 3. GOOGLE_APPLICATION_CREDENTIALS 환경 변수 설정
```

---

## 데이터베이스 통합

### 데이터베이스 설정

**PostgreSQL 설치:**
```bash
# macOS
brew install postgresql
brew services start postgresql

# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql
```

**데이터베이스 생성:**
```sql
CREATE DATABASE langflix;
CREATE USER langflix_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE langflix TO langflix_user;
```

**마이그레이션:**
```bash
# 데이터베이스 마이그레이션 실행
alembic upgrade head
```

### 데이터베이스 모델

**Media 테이블:**
- `id`: 고유 식별자
- `show_name`: TV 쇼 이름
- `episode_name`: 에피소드 식별자
- `language_code`: 언어 코드 (en, ko 등)
- `subtitle_file_path`: 자막 파일 경로
- `video_file_path`: 비디오 파일 경로
- `created_at`: 생성 타임스탬프

**Expression 테이블:**
- `id`: 고유 식별자
- `media_id`: Media 외래 키
- `expression`: 영어 표현
- `translation`: 번역 텍스트
- `dialogue`: 전체 대화 컨텍스트
- `similar_expressions`: 유사 표현의 JSON 배열
- `context_start_time`: 시작 시간 (초)
- `context_end_time`: 종료 시간 (초)

**ProcessingJob 테이블:**
- `id`: 고유 식별자
- `media_id`: Media 외래 키
- `status`: PENDING, PROCESSING, COMPLETED, FAILED
- `job_type`: 처리 작업 유형
- `started_at`: 처리 시작 시간
- `completed_at`: 처리 완료 시간
- `error_message`: 실패 시 오류 세부사항

---

## 모니터링 및 상태 확인

### CLI 모니터링

**로그 파일:**
```bash
# 처리 로그 확인
tail -f langflix.log

# 오류 확인
grep ERROR langflix.log
```

**출력 검증:**
```bash
# 파일 생성 확인
ls -la output/ShowName/EpisodeName/

# 비디오 파일 검증
ffprobe output/ShowName/EpisodeName/shared/context_videos/*.mkv
```

### API 모니터링

**상태 엔드포인트:**
```bash
# 기본 상태
curl http://localhost:8000/health

# 상세 상태 (데이터베이스, 스토리지, LLM 확인)
curl http://localhost:8000/health/detailed
```

**API 문서:**
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

**로깅:**
```bash
# API 로그
tail -f logs/api.log

# 데이터베이스 로그
tail -f logs/database.log
```

---

## 문제 해결

### 일반적인 CLI 문제

**문제**: `ModuleNotFoundError: No module named 'langflix'`
```bash
# 해결책: 개발 모드로 설치
pip install -e .
```

**문제**: `ffmpeg not found`
```bash
# 해결책: ffmpeg 설치
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg
```

**문제**: `GEMINI_API_KEY not found`
```bash
# 해결책: 환경 변수 설정
export GEMINI_API_KEY=your_api_key_here
# 또는 .env 파일에 추가
```

### 일반적인 API 문제

**문제**: `Database connection failed`
```bash
# 해결책: 데이터베이스 설정 확인
# 1. PostgreSQL이 실행 중인지 확인
# 2. 설정의 연결 문자열 확인
# 3. 마이그레이션 실행: alembic upgrade head
```

**문제**: `Storage backend error`
```bash
# 해결책: 스토리지 설정 확인
# 1. GCS 자격 증명 확인
# 2. 버킷 권한 확인
# 3. 먼저 LocalStorage로 테스트
```

**문제**: `Job stuck in PROCESSING status`
```bash
# 해결책: 백그라운드 작업 로그 확인
# 1. API 로그에서 오류 확인
# 2. 데이터베이스 연결 확인
# 3. 스토리지 백엔드 액세스 확인
```

### 성능 문제

**느린 처리:**
- 빠른 처리를 위해 `--test` 플래그 사용
- 사용 가능한 디스크 공간 확인
- API 키 할당량 제한 확인

**메모리 문제:**
- 더 짧은 비디오 세그먼트 처리
- 시스템 메모리 증가
- 개발용 테스트 모드 사용

---

## 배포

### CLI 배포

**로컬 개발:**
```bash
# 저장소 클론
git clone https://github.com/your-repo/langflix.git
cd langflix

# 의존성 설치
pip install -r requirements.txt

# 환경 설정
cp env.example .env
# API 키로 .env 편집

# 처리 실행
python -m langflix.main --help
```

### API 배포

**Docker 배포:**
```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "langflix.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**환경 변수:**
```bash
# 필수
GEMINI_API_KEY=your_api_key
DATABASE_URL=postgresql://user:password@db:5432/langflix
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json

# 선택사항
LANGFLIX_CONFIG_PATH=/app/config/production.yaml
```

**프로덕션 설정:**
```yaml
# production.yaml
database:
  enabled: true
  url: "${DATABASE_URL}"
  pool_size: 10
  max_overflow: 20

storage:
  backend: "gcs"
  gcs:
    bucket_name: "langflix-production"
    credentials_path: "${GOOGLE_APPLICATION_CREDENTIALS}"

api:
  host: "0.0.0.0"
  port: 8000
  workers: 4
  cors_origins: ["https://yourdomain.com"]
```

---

## 보안 고려사항

### API 보안
- **인증**: Phase 2에서 구현
- **속도 제한**: Phase 2에서 추가
- **입력 검증**: 이미 구현됨
- **CORS**: 프로덕션 도메인에 대해 설정

### 데이터 보안
- **API 키**: 환경 변수에 저장
- **데이터베이스**: 연결 풀링 사용
- **스토리지**: 서비스 계정 인증 사용
- **로그**: 민감한 데이터 로깅 방지

---

## 지원

### 문서
- **사용자 매뉴얼**: `docs/ko/USER_MANUAL_KOR.md`
- **API 참조**: `docs/ko/API_REFERENCE_KOR.md`
- **문제 해결**: `docs/ko/TROUBLESHOOTING_KOR.md`

### 도움 받기
- **이슈**: GitHub 이슈 생성
- **로그**: 관련 로그 파일 포함
- **설정**: 정리된 설정 파일 공유

---

## 버전 히스토리

- **v1.0**: CLI 및 API 지원이 포함된 초기 릴리스
- **v1.1**: 숏 비디오 생성 추가
- **v1.2**: Gemini TTS 통합 추가
- **v1.3**: 스토리지 추상화 계층 추가
- **v1.4**: 데이터베이스 통합 추가
- **v1.5**: FastAPI 애플리케이션 스캐폴드 추가
