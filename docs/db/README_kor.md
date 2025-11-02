# Database 모듈 문서

## 개요

`langflix/db/` 모듈은 SQLAlchemy ORM을 사용하여 LangFlix를 위한 데이터베이스 통합을 제공합니다. 미디어 메타데이터, 표현식, 처리 작업, YouTube 업로드 스케줄을 저장하기 위해 PostgreSQL을 지원합니다.

**최종 업데이트:** 2025-01-30

## 목적

이 모듈의 주요 역할:
- 데이터베이스 모델 정의 (Media, Expression, ProcessingJob, YouTubeSchedule 등)
- 모든 데이터베이스 엔티티에 대한 CRUD 작업
- 데이터베이스 세션 관리 및 연결 풀링
- Alembic을 사용한 데이터베이스 마이그레이션

## 주요 구성 요소

### 데이터베이스 모델

**위치:** `langflix/db/models.py`

LangFlix 데이터베이스 스키마를 위한 SQLAlchemy 모델:

#### Media 모델
에피소드/쇼 메타데이터 저장:
- `id`: UUID 기본 키
- `show_name`: TV 쇼 이름
- `episode_name`: 에피소드 식별자
- `language_code`: 언어 코드 (예: 'ko', 'en')
- `subtitle_file_path`: 스토리지 백엔드 참조
- `video_file_path`: 스토리지 백엔드 참조
- 관계: `expressions`, `processing_jobs`

#### Expression 모델
개별 표현식 및 분석 저장:
- `id`: UUID 기본 키
- `media_id`: Media 외래 키
- `expression`: 영어 표현식 텍스트
- `expression_translation`: 번역
- `expression_dialogue`: 전체 대화 컨텍스트
- `expression_dialogue_translation`: 대화 번역
- `similar_expressions`: 유사 표현식의 JSON 배열
- `context_start_time`, `context_end_time`: 비디오 타임스탬프
- `scene_type`: 장면 유형 (대화, 액션 등)
- `context_video_path`, `slide_video_path`: 스토리지 참조
- `difficulty`: 1-10 난이도 레벨
- `category`: 표현식 카테고리 (관용구, 속어, 공식적 등)
- `educational_value`: 교육적 가치 설명
- `score`: 선택을 위한 순위 점수

#### ProcessingJob 모델
비동기 처리 작업 추적:
- `id`: UUID 기본 키
- `media_id`: Media 외래 키
- `status`: 작업 상태 (PENDING, PROCESSING, COMPLETED, FAILED)
- `progress`: 진행률 백분율 (0-100)
- `error_message`: 실패 시 오류 세부 정보
- `started_at`, `completed_at`: 타임스탬프

#### YouTubeSchedule 모델
YouTube 업로드 스케줄 추적:
- `id`: UUID 기본 키
- `video_path`: 비디오 파일 경로
- `video_type`: 'final' 또는 'short'
- `scheduled_publish_time`: 예약된 게시 날짜시간
- `upload_status`: 'scheduled', 'uploading', 'completed', 'failed'
- `youtube_video_id`: 업로드 후 YouTube 비디오 ID
- `account_id`: YouTubeAccount 외래 키

#### YouTubeAccount 모델
YouTube 계정 정보 추적:
- `id`: UUID 기본 키
- `channel_id`: YouTube 채널 ID
- `channel_title`: 채널 이름
- `email`: 계정 이메일
- `is_active`: 활성 상태
- `token_file_path`: OAuth 토큰 파일 경로

#### YouTubeQuotaUsage 모델
일일 YouTube API 할당량 사용 추적:
- `id`: UUID 기본 키
- `date`: 할당량 추적 날짜
- `quota_used`: 사용된 할당량 단위
- `quota_limit`: 일일 할당량 제한 (기본값: 10000)
- `upload_count`: 업로드 횟수
- `final_videos_uploaded`: 최종 비디오 수
- `short_videos_uploaded`: 숏 비디오 수

### CRUD 작업

**위치:** `langflix/db/crud.py`

데이터베이스 작업을 위한 CRUD 클래스 제공:

#### MediaCRUD
```python
MediaCRUD.create(db, show_name, episode_name, language_code, ...)
MediaCRUD.get_by_id(db, media_id)
MediaCRUD.get_by_show_episode(db, show_name, episode_name)
MediaCRUD.update_file_paths(db, media_id, subtitle_path, video_path)
MediaCRUD.list_all(db, skip, limit)
```

#### ExpressionCRUD
```python
ExpressionCRUD.create_from_analysis(db, media_id, analysis_data)
ExpressionCRUD.create(db, media_id, expression, ...)
ExpressionCRUD.get_by_media(db, media_id)
ExpressionCRUD.get_by_id(db, expression_id)
ExpressionCRUD.search_by_text(db, search_text)
ExpressionCRUD.delete_by_media(db, media_id)
```

#### ProcessingJobCRUD
```python
ProcessingJobCRUD.create(db, media_id)
ProcessingJobCRUD.get_by_id(db, job_id)
ProcessingJobCRUD.get_by_media(db, media_id)
ProcessingJobCRUD.update_status(db, job_id, status, progress, error_message)
ProcessingJobCRUD.get_by_status(db, status)
ProcessingJobCRUD.get_active_jobs(db)
ProcessingJobCRUD.delete_by_media(db, media_id)
```

### 세션 관리

**위치:** `langflix/db/session.py`

데이터베이스 연결 관리 제공:

```python
class DatabaseManager:
    """데이터베이스 연결 관리자."""
    
    def initialize(self):
        """데이터베이스 연결 초기화."""
    
    def get_session(self) -> Session:
        """데이터베이스 세션 가져오기."""
    
    def create_tables(self):
        """모든 테이블 생성."""
```

**전역 함수:**
- `get_db_session()`: 의존성 주입을 위한 데이터베이스 세션 가져오기

## 데이터베이스 스키마

### 관계

```
Media (1) ──< (N) Expression
Media (1) ──< (N) ProcessingJob
YouTubeAccount (1) ──< (N) YouTubeSchedule
```

### 제약 조건

- `ProcessingJob.progress`: CHECK 제약 조건 (0 <= progress <= 100)
- `YouTubeSchedule.video_type`: CHECK 제약 조건 (IN ('final', 'short'))
- `YouTubeSchedule.upload_status`: CHECK 제약 조건 (IN ('scheduled', 'uploading', 'completed', 'failed'))
- 외래 키는 CASCADE 삭제 사용

## 구현 세부사항

### 연결 구성

데이터베이스 연결은 `langflix.settings`를 통해 구성됩니다:

```python
database_url = settings.get_database_url()
pool_size = settings.get_database_pool_size()
max_overflow = settings.get_database_max_overflow()
```

### 세션 생명주기

1. **초기화**: DatabaseManager가 엔진 및 세션 팩토리 초기화
2. **세션 가져오기**: `get_db_session()` 호출하여 세션 가져오기
3. **세션 사용**: CRUD 작업 수행
4. **닫기**: 세션이 자동으로 닫힘 (컨텍스트 매니저)

### 마이그레이션 시스템

데이터베이스 마이그레이션은 Alembic을 사용:

- 마이그레이션 파일: `langflix/db/migrations/versions/`
- 마이그레이션 명령: `alembic upgrade head`, `alembic revision --autogenerate`

## 의존성

- `sqlalchemy`: ORM 프레임워크
- `alembic`: 데이터베이스 마이그레이션 도구
- `psycopg2` 또는 `asyncpg`: PostgreSQL 드라이버
- `langflix.settings`: 데이터베이스 구성

## 일반적인 작업

### Media 레코드 생성

#### 권장: Context Manager 사용

```python
from langflix.db.crud import MediaCRUD
from langflix.db.session import db_manager

# 권장 방법: 자동 commit/rollback/close
with db_manager.session() as db:
    media = MediaCRUD.create(
        db,
        show_name="Suits",
        episode_name="S01E01",
        language_code="ko",
        subtitle_file_path="subtitles/s01e01.srt",
        video_file_path="media/s01e01.mp4"
    )
    # 성공 시 자동으로 commit
    # 예외 발생 시 자동으로 rollback
    # finally 블록에서 자동으로 close
```

#### 레거시: 수동 세션 관리

```python
# 여전히 지원되지만 권장하지 않음
from langflix.db.session import get_db_session

db = get_db_session()
try:
    media = MediaCRUD.create(
        db,
        show_name="Suits",
        episode_name="S01E01",
        language_code="ko",
        subtitle_file_path="subtitles/s01e01.srt",
        video_file_path="media/s01e01.mp4"
    )
    db.commit()
except Exception:
    db.rollback()
finally:
    db.close()
```

### 분석에서 Expression 생성

```python
from langflix.db.crud import ExpressionCRUD

expression = ExpressionCRUD.create_from_analysis(
    db,
    media_id=str(media.id),
    analysis_data=expression_analysis
)
```

### 작업 상태 업데이트

```python
from langflix.db.crud import ProcessingJobCRUD

ProcessingJobCRUD.update_status(
    db,
    job_id=str(job.id),
    status="PROCESSING",
    progress=50
)
```

### Media별 Expression 쿼리

```python
expressions = ExpressionCRUD.get_by_media(db, media_id)
for expr in expressions:
    print(f"{expr.expression}: {expr.expression_translation}")
```

### Expression 검색

```python
results = ExpressionCRUD.search_by_text(db, "get away with")
for expr in results:
    print(f"Found: {expr.expression}")
```

## 데이터베이스 구성

### 환경 변수

- `DATABASE_URL`: PostgreSQL 연결 문자열
  - 예시: `postgresql://user:pass@localhost/langflix`
- `DATABASE_POOL_SIZE`: 연결 풀 크기 (기본값: 10)
- `DATABASE_MAX_OVERFLOW`: 최대 오버플로우 연결 (기본값: 20)

### 선택적 데이터베이스

데이터베이스는 선택사항입니다 - LangFlix는 파일 전용 모드로 실행할 수 있습니다. 데이터베이스가 구성되면:
- 메타데이터가 데이터베이스에 저장됨
- 파일 경로는 스토리지 백엔드를 참조함
- 처리 작업이 추적됨

## 주의사항

1. **UUID 타입**: 모든 ID는 UUID 타입 사용 - 필요시 문자열로 변환
2. **세션 관리**: 항상 세션을 닫거나 컨텍스트 매니저 사용
3. **트랜잭션**: 변경 후 `db.commit()` 사용, 오류 시 `db.rollback()` 사용
4. **스토리지 참조**: 파일 경로는 참조이며 절대 경로가 아님
5. **CASCADE 삭제**: Media 삭제 시 관련 Expressions 및 Jobs 삭제
6. **JSONB 필드**: `similar_expressions`는 PostgreSQL 배열 지원을 위해 JSONB 사용
7. **타임존**: 모든 타임스탬프는 타임존 인식 datetime 사용

## 관련 모듈

- `langflix/storage/`: 파일 참조를 위한 스토리지 백엔드
- `langflix/api/`: API 엔드포인트가 작업 추적을 위해 데이터베이스 사용
- `langflix/services/`: 서비스가 메타데이터 저장을 위해 데이터베이스 사용

