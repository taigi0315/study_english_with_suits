# LangFlix API 모듈 문서 (KOR)

최종 업데이트: 2025-10-30

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
  - `files.py`: `output/` 파일 목록 및 상세/삭제 스텁.
  - `jobs.py`: 잡 생성, 상태/표현식 조회, 잡 목록 API.
- `tasks/processing.py`: (존재하나 여기서는 직접 사용되지 않음; 실제 처리는 `routes/jobs.py` 내 백그라운드 태스크에서 수행).

## 애플리케이션 라이프사이클 및 설정
- `main.py`의 `create_app()`:
  - CORS 전체 허용(운영 환경에서 제한 필요).
  - `LoggingMiddleware` 적용 및 `X-Process-Time` 헤더 추가.
  - 로컬 `output/` 존재 시 `/output` 정적 마운트.
  - 라우터: `health`, `jobs`(프리픽스 `/api/v1`), `files`(프리픽스 `/api/v1`).
  - 예외 핸들러 등록: `APIException`, `HTTPException`.
- Lifespan 시작 시 Redis 잡 저장소 정리 및 상태 확인(`langflix.core.redis_client.get_redis_job_manager()`).

## 의존성 주입(플레이스홀더)
- `get_db()`는 `Session`을 yield하지만 현재는 `None` 반환(TODO).
- `get_storage()`는 현재 `None` 반환(TODO).

## 예외 처리
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
- `/health` (GET): 기본 헬스 체크.
- `/health/detailed` (GET): 버전/컴포넌트 포함 상세 헬스.
- `/health/redis` (GET): Redis 헬스.
- `/health/redis/cleanup` (POST): 만료/정체 잡 정리.
- `/api/v1/files` (GET): `output/` 재귀 파일 목록.
- `/api/v1/files/{file_id}` (GET): 파일 상세 스텁(TODO).
- `/api/v1/files/{file_id}` (DELETE): 파일 삭제 스텁(TODO).
- `/api/v1/jobs` (POST): 영상+자막 업로드와 폼 필드로 새 잡 생성, 백그라운드 처리 시작.
- `/api/v1/jobs/{job_id}` (GET): Redis에서 현재 잡 상태 조회.
- `/api/v1/jobs/{job_id}/expressions` (GET): Redis에서 표현식 반환(작업 상태와 동일한 소스).
- `/api/v1/jobs` (GET): 모든 잡 나열(출처: Redis).

## 잡 처리(백그라운드 태스크)
`routes/jobs.py`의 `process_video_task(...)`:
- `TempFileManager`를 사용한 임시 파일 처리 (참조: `langflix/utils/temp_file_manager.py`)
  - 컨텍스트가 종료되면 예외 발생 시에도 임시 파일이 자동으로 정리됨
  - 하드코딩된 `/tmp` 경로 없음 - `tempfile` 모듈을 통해 시스템 temp 디렉토리 사용
  - 컨텍스트 관리자가 처리 실패 시에도 정리 보장
- `langflix.core` 모듈로 자막 파싱/청크/표현식 분석, 자막 생성, 클립 추출, 교육용/쇼츠 영상 생성 및 배치, 최종 `ffmpeg` 병합 수행.
- `services.output_manager.create_output_structure`로 출력 디렉터리 구조 생성.
- Redis 상태/결과 업데이트, 비디오 캐시 무효화.

## 에러 처리 및 로깅
- 통합 예외 핸들러로 일관된 JSON 페이로드 반환.
- 파이프라인 단계별 상세 로깅으로 추적 용이.

## 보안/운영 주의사항
- CORS 기본 `*` 허용 → 환경별 제한 필요.
- 로컬 파일 시스템 사용 → 컨테이너/서버 권한 및 경로 확인 필요.
- 업로드 크기/타입 검증 강화 권장.
- Redis 비가용 시 앱은 기동되나 경고만 로그 → 장애 전파/격하 모드 정책 검토 권장.

## 확장 포인트
- `dependencies.get_db/get_storage` 구현으로 DB/스토리지 연계.
- 파일 상세/삭제 스텁을 실제 스토리지 연동으로 대체.
- ✅ `/jobs/{id}/expressions`를 Redis 기반 단일 소스 진실로 통합 완료 - `jobs_db` 의존 제거됨 (TICKET-003).

## 사용 예시
```bash
uvicorn langflix.api.main:app --reload
# /docs 에서 Swagger UI 확인
```
