# LangFlix API 모듈 문서 (KOR)

최종 업데이트: 2025-11-13

## 개요
`langflix/api` 패키지는 LangFlix의 FastAPI 기반 HTTP 인터페이스를 제공합니다. 헬스 체크, 영상 처리 잡 관리, 파일 목록 제공 기능을 포함하며, 미들웨어/예외 처리/정적 경로 마운트 및 Redis 잡 저장소와의 연계를 담당합니다.

## 폴더 구조
- `main.py`: FastAPI 앱 팩토리, 라우터 등록, lifespan 관리, 미들웨어, 정적 경로 마운트.
- `dependencies.py`: DI 프로바이더 자리(데이터베이스 세션, 스토리지 백엔드).
- `exceptions.py`: API 전용 예외 타입과 통합 예외 핸들러.
- `middleware.py`: 요청 로깅 미들웨어(`X-Process-Time` 헤더 포함).
- `models/`
  - `common.py`: 공용 응답 모델(헬스/에러).
  - `requests.py`: 요청 DTO(잡 생성, 파일 업로드 메타데이터).
  - `responses.py`: 응답 DTO(잡 상태, 표현식 목록).
- `routes/`
  - `health.py`: 서비스/Redis 헬스 엔드포인트 및 정리.
  - `files.py`: 스토리지 연동 파일 인벤토리, 메타데이터 조회, 보호 삭제 로직.
  - `jobs.py`: 잡 생성, 상태/표현식 조회, 잡 목록 API.
  - `batch.py`: 배치 비디오 처리 엔드포인트 (배치 생성, 배치 상태 조회).
- `tasks/processing.py`: (존재하나 여기서는 직접 사용되지 않음; 실제 처리는 `routes/jobs.py` 내 백그라운드 태스크에서 수행).

## 애플리케이션 라이프사이클 및 설정
- `main.py`의 `create_app()`:
  - CORS 전체 허용(운영 환경에서 제한 필요).
  - `LoggingMiddleware` 적용 및 `X-Process-Time` 헤더 추가.
  - 로컬 `output/` 존재 시 `/output` 정적 마운트.
  - 라우터: `health`, `jobs`(프리픽스 `/api/v1`), `files`(프리픽스 `/api/v1`), `batch`(프리픽스 `/api/v1`).
  - 예외 핸들러 등록: `APIException`, `HTTPException`.
- Lifespan 시작:
  - 데이터베이스가 활성화된 경우 연결 풀 초기화(`settings.get_database_enabled()`)
  - Redis 잡 저장소 정리 및 상태 확인(`langflix.core.redis_client.get_redis_job_manager()`)
  - 순차 배치 작업 처리를 위한 `QueueProcessor` 백그라운드 작업 시작
- Lifespan 종료:
  - `QueueProcessor` 우아하게 중지 (처리 중인 작업이 있으면 재큐잉)
  - 데이터베이스가 활성화된 경우 연결 정리
- Flask Web UI와 FastAPI 백엔드 사이의 API 엔드포인트는 `LANGFLIX_API_BASE_URL` 환경 변수로 지정합니다.
  - 값이 설정되어 있으면 (마지막 슬래시 제거 후) 그대로 사용합니다.
  - 값이 없으면 로컬 개발 환경에서는 자동으로 `http://localhost:8000`을 선택합니다.
  - Docker/컨테이너 환경(`LANGFLIX_RUNNING_IN_DOCKER=1` 또는 자동 감지)에서는 기본적으로 `http://langflix-api:8000`을 사용합니다.
  - 이중 기본값을 통해 추가 설정 없이 로컬과 Docker Compose 배포 모두에서 동일한 UI를 사용할 수 있습니다.

## 의존성 주입

### 데이터베이스 의존성 (`get_db()`)
- FastAPI 의존성 주입을 통해 SQLAlchemy 데이터베이스 세션 제공
- `langflix.db.session`의 `DatabaseManager`를 사용하여 연결 풀 관리
- 자동 세션 생명주기 처리:
  - 엔드포인트 핸들러에 데이터베이스 세션 yield
  - 성공 시 자동 commit
  - 예외 발생 시 rollback
  - `finally` 블록에서 세션 종료
- 데이터베이스가 비활성화된 경우(file-only 모드) `None` 반환 - `settings.get_database_enabled()`로 확인
- 데이터베이스 초기화는 애플리케이션 lifespan에서 수행됨 (아래 참조)

**사용 예:**
```python
from fastapi import Depends
from langflix.api.dependencies import get_db
from sqlalchemy.orm import Session

@router.get("/endpoint")
async def my_endpoint(db: Session = Depends(get_db)):
    if db is None:
        # 데이터베이스 비활성화, 적절히 처리
        return {"message": "Database not available"}
    # db 세션 사용...
```

### 스토리지 의존성 (`get_storage()`)
- FastAPI 의존성 주입을 통해 스토리지 백엔드 인스턴스 제공
- `langflix.storage.factory`의 `create_storage_backend()` 팩토리 사용
- 설정에 따라 구성된 스토리지 백엔드(Local 또는 GCS) 반환
- 요청마다 새로운 인스턴스 생성(경량 작업)

**사용 예:**
```python
from fastapi import Depends
from langflix.api.dependencies import get_storage
from langflix.storage.base import StorageBackend

@router.get("/endpoint")
async def my_endpoint(storage: StorageBackend = Depends(get_storage)):
    files = storage.list_files("/path")
    # 스토리지 백엔드 사용...
```

## 예외 처리

### 에러 핸들러 통합 (TICKET-005)

API는 이제 구조화된 에러 리포팅을 위해 중앙화된 에러 핸들러(`langflix/core/error_handler.py`)를 사용합니다:

**주요 기능:**
- **구조화된 에러 리포트**: 모든 에러는 컨텍스트(operation, component, metadata)와 함께 캡처됨
- **에러 카테고리**: 에러는 자동으로 분류됨 (NETWORK, PROCESSING, VALIDATION, RESOURCE, SYSTEM)
- **에러 심각도**: 에러는 심각도에 따라 분류됨 (LOW, MEDIUM, HIGH, CRITICAL)
- **에러 추적**: 에러 리포트가 저장되며 통계 조회 가능

**통합 포인트:**
- `routes/jobs.py`의 `process_video_task()`는 작업 컨텍스트와 함께 에러를 리포팅
- 에러 컨텍스트에 포함: `job_id`, `video_filename`, `subtitle_filename`
- 에러는 Redis 작업 상태 업데이트 전에 에러 핸들러를 통해 로깅됨

**사용 예시:**
```python
from langflix.core.error_handler import handle_error, ErrorContext

try:
    # 처리 로직
    pass
except Exception as e:
    error_context = ErrorContext(
        operation="process_video_task",
        component="api.routes.jobs",
        additional_data={"job_id": job_id}
    )
    handle_error(e, error_context, retry=False, fallback=False)
    # 에러 처리 계속...
```

**장점:**
- 모든 모듈에서 일관된 에러 리포팅
- 구조화된 에러 정보로 더 나은 디버깅
- 에러 모니터링 및 알림을 위한 기반 (향후 개선)

- 기본 예외 `APIException` 및 특수화: `ValidationError`, `NotFoundError`, `ProcessingError`, `StorageError`.
- `api_exception_handler`는 `APIException`, `HTTPException` 모두를 구조화된 JSON 에러로 변환(`models.common.ErrorResponse` 참고).

## 미들웨어
- `LoggingMiddleware`는 메서드/URL/상태코드/소요시간을 로깅하고, `X-Process-Time` 헤더를 추가합니다.

## 데이터 모델
- 요청:
  - `JobCreateRequest`: 언어, 시리즈/에피소드, `max_expressions`, `language_level`, `test_mode`, `no_shorts`.
  - `FileUploadRequest`: 파일명, 콘텐츠 타입, 크기.
- 응답:
  - `JobStatusResponse`: id, 상태, 타임스탬프, 진행률, 에러.
  - `ExpressionResponse`: 표현식, 번역, 컨텍스트, 유사 표현식.
  - `JobExpressionsResponse`: 잡 id, 상태, 표현식 목록.
  - `HealthResponse`, `DetailedHealthResponse`, `ErrorResponse`(from `common.py`).

## 엔드포인트
- `/` (GET): API 루트 메타.
- `/local/status` (GET): 로컬 개발 정보.
- `/health` (GET): 기본 헬스 체크 엔드포인트. 서비스 상태와 타임스탬프를 반환합니다.
- `/health/detailed` (GET): 모든 시스템 컴포넌트의 실제 상태 확인:
  - `langflix.monitoring.health_checker`의 `SystemHealthChecker`를 사용하여 모든 시스템 컴포넌트 상태를 확인합니다
  - Database: `db_manager.session()` context manager를 사용하여 `SELECT 1` 쿼리로 연결 확인
    - `{"status": "healthy", "message": "..."}` 또는 `{"status": "disabled", "message": "..."}` 또는 `{"status": "unhealthy", "message": "..."}` 반환
  - Storage: 파일 목록 조회 시도(가벼운 작업)로 백엔드 가용성 확인
    - `{"status": "healthy", "message": "..."}` 또는 `{"status": "unhealthy", "message": "..."}` 반환
  - Redis: 잡 매니저를 통한 Redis 연결 확인
    - `RedisJobManager.health_check()`의 전체 헬스 딕셔너리 반환
  - TTS: TTS 서비스 설정 확인(Gemini 또는 LemonFox의 API 키 존재 여부)
    - `{"status": "healthy", "message": "..."}` 또는 `{"status": "unhealthy", "message": "..."}` 또는 `{"status": "unknown", "message": "..."}` 반환
  - 전체 상태: 컴포넌트 상태로부터 결정됨 (`healthy`, `degraded`, 또는 `unhealthy`)
- `/health/database` (GET): 개별 데이터베이스 헬스 체크 엔드포인트.
- `/health/storage` (GET): 개별 스토리지 헬스 체크 엔드포인트.
- `/health/tts` (GET): 개별 TTS 서비스 헬스 체크 엔드포인트.
- `/health/redis` (GET): 잡 매니저를 통한 Redis 헬스 체크.
- `/health/redis/cleanup` (POST): 만료/정체 잡 정리.
- `/api/v1/files` (GET): 설정된 스토리지(Local/GCS)에 저장된 파일을 열람하고 메타데이터(`size`, `mime`, 타임스탬프, URL)를 반환.
- `/api/v1/files/{file_id}` (GET): 특정 파일 메타데이터 조회; 경로 정규화/역참조 차단/디렉터리 요청 거부 포함.
- `/api/v1/files/{file_id}` (DELETE): 스토리지 백엔드를 통해 파일 삭제. 민감 자산(`config.yaml`, `.env`, `*.log` 등)은 보호되어 403 반환.
- `/api/v1/jobs` (POST): 영상+자막 업로드와 폼 필드로 새 잡 생성, 백그라운드 처리 시작.
- `/api/v1/jobs/{job_id}` (GET): Redis에서 현재 잡 상태 조회.
- `/api/v1/jobs/{job_id}/expressions` (GET): Redis에서 표현식 반환(작업 상태와 동일한 소스).
  - **TICKET-003 수정:** 정의되지 않은 `jobs_db` 변수 수정 - 이제 `get_redis_job_manager()`를 통해 Redis를 올바르게 사용함
- `/api/v1/jobs` (GET): 모든 잡 나열(출처: Redis).
- `/api/v1/batch` (POST): 배치 비디오 처리 작업 생성 (TICKET-014).
  - 요청 본문: `{"videos": [...], "language_code": "ko", "language_level": "intermediate", ...}`
  - 반환: `{"batch_id": "uuid", "total_jobs": N, "jobs": [...], "status": "PENDING"}`
  - 작업은 `QueueProcessor`에 의해 순차 처리를 위해 큐에 추가됨
  - 최대 배치 크기: 50개 비디오 (강제 적용)
- `/api/v1/batch/{batch_id}` (GET): 개별 작업 진행 상황과 함께 배치 상태 조회 (TICKET-014).
  - 반환: 전체 상태, 개별 작업 상태, 진행 메트릭이 포함된 배치 정보
  - 상태 값: `PENDING`, `PROCESSING`, `COMPLETED`, `FAILED`, `PARTIALLY_FAILED`
  - 작업 상태를 기반으로 배치 상태를 자동으로 재계산하고 업데이트

## 잡 처리(백그라운드 태스크)

### 통합 파이프라인 서비스 (TICKET-001)

API는 API와 CLI 처리 모두에 대한 통합 인터페이스를 제공하는 `VideoPipelineService` (`langflix/services/video_pipeline_service.py`)를 사용합니다. 이를 통해 코드 중복을 제거하고 일관된 동작을 보장합니다.

**주요 기능:**
- 비디오 처리 파이프라인에 대한 단일 진실 공급원
- 실시간 작업 상태 업데이트를 위한 진행 상황 콜백 지원
- API와 CLI 간 일관된 결과 형식

**구현:**
- `routes/jobs.py`에서 `process_video_task(...)`로 정의 (450+ 줄에서 ~110 줄로 간소화)
- `LangFlixPipeline`을 래핑하는 `VideoPipelineService.process_video()` 사용
- **임시 파일 관리 (TICKET-002):**
  - 임시 파일 처리를 위해 `TempFileManager` 사용 (참조: `langflix/utils/temp_file_manager.py`)
  - 컨텍스트가 종료되면 예외 발생 시에도 임시 파일이 자동으로 정리됨
  - 하드코딩된 `/tmp` 경로 없음 - `tempfile` 모듈을 통해 시스템 temp 디렉토리 사용
  - 컨텍스트 관리자가 처리 실패 시에도 정리 보장
  - 전역 싱글톤 인스턴스가 애플리케이션 전체에서 모든 임시 파일 관리
- 콜백을 통해 Redis 작업 상태/결과 업데이트; 비디오 캐시 무효화

**진행 상황 추적:**
- 진행 상황 콜백이 자동으로 Redis 작업 상태 업데이트
- 진행 마일스톤: 10% (초기화), 20% (파일 저장), 30% (파싱), 50% (처리), 70% (교육용 비디오), 80% (짧은 비디오), 100% (완료)

**관련 문서:**
- [Services 모듈 문서](../services/README_kor.md) - VideoPipelineService 세부사항
- [Utils 모듈 문서](../utils/temp_file_manager_kor.md) - TempFileManager 사용법

## 에러 처리 및 로깅
- 통합 예외 핸들러로 일관된 JSON 페이로드 반환.
- 파이프라인 단계별 상세 로깅으로 추적 용이.

## 보안/운영 주의사항
- CORS 기본 `*` 허용 → 환경별 제한 필요.
- 로컬 파일 시스템 사용 → 컨테이너/서버 권한 및 경로 확인 필요.
- 업로드 크기/타입 검증 강화 권장.
- Redis 비가용 시 앱은 기동되나 경고만 로그 → 장애 전파/격하 모드 정책 검토 권장.

## 파일 관리 엔드포인트

### 스토리지 기반 설계
- FastAPI 의존성 `Depends(get_storage)`로 모든 요청에서 `StorageBackend` 인스턴스를 획득하여 LocalStorage와 GCS 간 동작을 통일.
- `PurePosixPath`를 활용해 경로를 정규화하고, 역참조(`..`) 및 절대 경로를 차단하며 구분자를 통일.
- 메타데이터 헬퍼가 크기, MIME, 생성/수정 시각, 공유 가능한 URL을 제공합니다. LocalStorage는 파일 시스템 stat을 사용하고, GCS는 blob 메타데이터를 즉시 갱신합니다.

### 파일 목록
- `GET /api/v1/files`는 `storage.list_files("")` 결과를 순회하며 정규화/메타데이터 수집 후 디렉터리를 필터링합니다.
- 응답 예시:
  ```json
  {
    "files": [
      {
        "file_id": "short_form_videos/expressions/expression_hi.mkv",
        "name": "expression_hi.mkv",
        "path": "short_form_videos/expressions/expression_hi.mkv",
        "url": "...",
        "size": 1234567,
        "type": "video/x-matroska",
        "modified": 1731492801.123,
        "created": 1731492000.456,
        "is_directory": false
      }
    ],
    "total": 1
  }
  ```
  - `modified`/`created`는 기존 UI 호환성을 유지하기 위해 UNIX 타임스탬프(초)로 제공됩니다.
  - `url`은 LocalStorage는 절대 경로, GCS는 public URL을 반환합니다.

### 파일 상세
- `GET /api/v1/files/{file_id:path}`는 경로를 정규화하고 `storage.file_exists`로 존재 여부를 확인한 뒤 메타데이터를 반환합니다.
- 디렉터리 요청은 400, 존재하지 않는 파일은 404, 경로 역참조 시도는 400을 반환합니다.
- 모든 오류는 로깅 후 FastAPI `HTTPException`으로 감쌉니다.

### 파일 삭제
- `DELETE /api/v1/files/{file_id:path}` 흐름:
  1. 경로 정규화 및 존재 여부 확인.
  2. 메타데이터를 조회하여 디렉터리 삭제를 차단.
  3. `fnmatch` 기반 보호 패턴(`config.yaml`, `.env`, `*.log`, `langflix.log`, `requirements.txt`) 검사.
  4. `storage.delete_file` 실행 후 성공 여부 확인.
- 성공 시 `{ "message": "...", "file_id": "...", "deleted": true }` 응답.
- 보호 파일은 403, 디렉터리는 400, 존재하지 않는 파일은 404, 스토리지 오류는 500을 반환합니다.

### 테스트
- `tests/api/test_files_routes.py`에서 의존성 오버라이드를 이용해 pytest `tmp_path` 기반 LocalStorage를 주입.
- 목록/메타데이터/MIME 검증, 경로 검증, 삭제 성공/보호/디렉터리 차단 시나리오를 검증합니다.

## 확장 포인트
- ✅ `dependencies.get_db/get_storage` 구현 완료 - 데이터베이스 및 스토리지 통합 완료 (TICKET-010)
- ✅ 파일 상세/삭제 엔드포인트를 스토리지 연동 및 보안 검증 로직으로 교체 (TICKET-028).
- ✅ `/jobs/{id}/expressions`를 Redis 기반 단일 소스 진실로 통합 완료 - `jobs_db` 의존 제거됨 (TICKET-003).

## 사용 예시
```bash
uvicorn langflix.api.main:app --reload
# /docs 에서 Swagger UI 확인
```
