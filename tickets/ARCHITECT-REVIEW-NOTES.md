# Architect Review Notes - 2025-01-30

## System Understanding

### Architecture Overview
- **High-level Architecture**: LangFlix is a video processing pipeline that extracts educational content from TV shows
- **Key Components**: 
  - `langflix/core/` - Core video processing logic (VideoEditor, ExpressionAnalyzer, etc.)
  - `langflix/api/` - FastAPI HTTP interface for job management
  - `langflix/services/` - Business logic services
  - `langflix/media/` - FFmpeg utilities for video/audio processing
  - `langflix/db/` - Database integration (optional)
- **Critical Workflows**: 
  1. Video upload → Subtitle parsing → Expression analysis → Video generation → Output
  2. API job creation → Background processing → Status updates → Result retrieval

### Current State Assessment

**Strengths:**
- Well-modularized codebase with clear separation of concerns (core/api/services)
- Comprehensive documentation in `docs/` folder
- Good test structure (unit/integration/functional)
- Robust FFmpeg pipeline with demuxer-first approach (ADR-015)
- Error handler module exists but underutilized

**Known Issues:**
- Code duplication between CLI (`LangFlixPipeline`) and API (`process_video_task`)
- Inconsistent temporary file management across modules
- Unused/underutilized code (`error_handler.py`, `pipeline_runner.py`)
- Bug in `get_job_expressions` endpoint (undefined variable)
- Inconsistent filename sanitization logic

**Architectural Goals:**
- Consolidate video processing logic into unified service layer
- Standardize resource management (temp files, error handling)
- Remove code duplication and technical debt
- Improve maintainability and testability
- Align with service-oriented architecture pattern

### Technical Constraints
- **Performance**: Video processing is CPU-intensive, need efficient resource management
- **Scalability**: Current architecture supports single-node deployment
- **Integration dependencies**: 
  - Redis for job state management
  - Optional database integration
  - FFmpeg for video processing
  - External APIs for TTS/LLM

### Design Patterns Used
- **Service Layer Pattern**: Business logic in `services/` module
- **Pipeline Pattern**: Sequential processing in `LangFlixPipeline`
- **Repository Pattern**: Database abstraction in `db/` module
- **Strategy Pattern**: Different TTS providers, storage backends

### Technology Stack
- **Language**: Python 3.x
- **Framework**: FastAPI for HTTP API
- **Video Processing**: FFmpeg via `ffmpeg-python`
- **Storage**: File system, Redis for job state
- **Database**: SQLite (optional, via SQLAlchemy)

### Integration Points
- **External Services**: TTS APIs (Google, LemonFox), LLM APIs (Gemini)
- **File System**: Input media, output videos, temporary files
- **Redis**: Job status and progress tracking

---
## Ticket Review Process Starting Below

### New Ticket Review Session - 2025-01-30

**Tickets Reviewed:**
1. TICKET-001: Parallel LLM Processing - ✅ APPROVED (with critical fix)
2. TICKET-002: Multiple Expressions Per Context - ✅ APPROVED
3. TICKET-003: Production Dockerization - ✅ APPROVED (with scope adjustments)
4. TICKET-004: Consolidate Code Improvements - ❌ DELETED (placeholder, no content)

**Key Findings:**
- TICKET-001 has critical implementation bug (sequential loop defeats parallelization)
- TICKET-003 includes Celery but it's not actively used (make optional)
- All tickets approved with architectural enhancements

**Implementation Order:**
1. Phase 1: TICKET-001 (parallel processing) - Week 1-2
2. Phase 2: TICKET-002 (multi-expression) - Week 3-4
3. Phase 3: TICKET-003 (deployment) - Week 5-6+

---

### New Ticket Review Session - 2025-01-30 (Second)

**Tickets Reviewed:**
5. TICKET-010: API Dependencies for Database and Storage - ✅ APPROVED
6. TICKET-011: Database Session Context Manager - ✅ APPROVED
7. TICKET-012: Comprehensive Health Checks - ✅ APPROVED (Deferred to Phase 1)

**Key Findings:**
- TICKET-010: 필수 기술 부채 해소, FastAPI 의존성 주입 완성
- TICKET-011: 자동 리소스 관리 개선, 하위 호환성 유지
- TICKET-012: 모니터링 기반 구축, TICKET-010/011 종속성
- 모든 티켓 표준 패턴 적용, 구현 간단함

**Implementation Order:**
1. Phase 0: TICKET-011 (context manager) → TICKET-010 (API dependencies) - 즉시
2. Phase 1: TICKET-012 (health checks) - Sprint 1

**Dependencies:**
- TICKET-010: TICKET-011의 `session()` context manager 활용
- TICKET-012: TICKET-010 완료 후 DB health check 가능, TICKET-011의 `session()` 활용

**Technical Decisions:**
- Storage 백엔드는 가볍게 매 요청 생성
- Health check는 가벼운 쿼리만 사용
- TTS health check는 설정만 확인, 실제 호출 안 함
- LLM API health check는 비용 문제로 제외

---

### New Ticket Review Session - 2025-01-30 (Third)

**Tickets Reviewed:**
8. TICKET-013: Fix Multiple Expression Video Processing Bugs - ✅ APPROVED

**Key Findings:**
- TICKET-008 이후 버그 3건: 타임스탬프 프리즈, 자막 오류, 임시 파일 누적
- 모두 TICKET-008 피쳐 완성에 필수
- 구현 간단, 영향 큼
- 타임스탬프: `avoid_negative_ts` 추가
- 자막: 그룹 단일 파일 사용(컨텍스트 공유)
- 임시 파일: 패턴 매칭 + `atexit` 정리

**Implementation Order:**
1. Phase 1: TICKET-013 (TICKET-008 직후)

**Dependencies:**
- TICKET-013: TICKET-008 완료 후 즉시

**Technical Decisions:**
- 그룹 ID로 자막 파일 고유성 보장
- 각 그룹 완료 후 임시 파일 즉시 정리(디버깅 유리)
- FFmpeg 옵션: `avoid_negative_ts`, 타임스탬프 검증

---

### New Ticket Review Session - 2025-01-30 (Fourth)

**Tickets Reviewed:**
9. TICKET-014: Implement Batch Video Processing Queue System - ✅ APPROVED

**Key Findings:**
- 배치 비디오 처리 큐 시스템 구현
- 사용자 경험 개선: 반복 작업 자동화
- Redis 기반 FIFO 큐, 순차 처리
- FastAPI lifespan background task
- 하위 호환성 유지 (단일 작업 처리 계속 작동)

**Implementation Order:**
1. Phase 2 (Sprint 2): TICKET-014 (TICKET-007, TICKET-008 완료 후)

**Dependencies:**
- TICKET-014: TICKET-007, TICKET-008 완료 후 구현
  - 병렬 처리 성능 혜택
  - 다중 표현식 기능 안정화 필요

**Technical Decisions:**
- 큐 프로세서: FastAPI lifespan background task (별도 데몬 불필요)
- 순차 처리: v1은 순차 (안전), 향후 병렬 처리 추가 가능
- 배치 크기 제한: 최대 50개 비디오
- 에러 처리: 실패한 작업은 FAILED로 표시하고 계속 진행
- 서버 재시작: QUEUED 작업 자동 재개, PROCESSING 작업 타임아웃
- Redis lock: 중복 프로세서 방지 (`SETNX jobs:processor_lock`)

---

### New Ticket Review Session - 2025-01-30 (Fifth)

**Tickets Reviewed:**
10. TICKET-028: Implement File Management API Endpoints - ✅ APPROVED

**Key Findings:**
- API 파일 관리 엔드포인트 완성 (GET details, DELETE)
- Storage backend abstraction 활용 (ADR-011)
- 보안: Path traversal 방지, protected files 패턴
- API 완성도 향상 및 사용자 경험 개선

**Implementation Order:**
1. Phase 2 - Sprint 2 (Weeks 3-4): TICKET-028

**Dependencies:**
- TICKET-028: Storage backend 이미 존재 (ADR-011)
- 독립적으로 구현 가능

**Technical Decisions:**
- File ID: Relative path 사용 (가장 간단, `list_files()`와 일치)
- Storage backend 메서드: `file_exists()`, `delete_file()`, `get_file_url()` 사용
- Path validation: `../` 및 absolute path 거부
- Protected files: 하드코딩된 패턴 (향후 설정으로 이동 고려)
- Performance: `list_files()`는 모든 파일 나열 (향후 pagination 고려)

**Code Corrections Made:**
- Storage backend 메서드 이름 수정 (`exists()` → `file_exists()`, `delete()` → `delete_file()`)
- `list_files()` 구현 수정 (빈 prefix로 모든 파일 나열, recursive 파라미터 없음)
- `delete_file()` 반환값 확인 추가

---

### New Ticket Review Session - 2025-01-21

**Tickets Reviewed:**
15. TICKET-060: Generate YouTube Metadata in Target Language for All Video Types - ✅ APPROVED

**Key Findings:**
- TICKET-056의 불완전한 구현을 완성하는 중요한 작업
- 타겟 언어 사용자 경험 개선 (한국어, 일본어, 중국어 등)
- YouTube SEO 개선 - 로컬라이즈된 메타데이터로 발견성 향상
- TICKET-059에 의존 (expression_translation 필드 필요)
- 모든 비디오 타입(short, long-form, final)에 일관된 타겟 언어 지원

**Implementation Order:**
1. Phase 1 - Sprint 1: TICKET-060 (TICKET-059 완료 후, Week 2)

**Dependencies:**
- TICKET-060: TICKET-059 완료 필수 (expression_translation 필드 필요)
- TICKET-060: TICKET-056의 자연스러운 확장

**Technical Decisions:**
- Expression text는 `expression_translation` 사용 (영어 원문 아님)
- 태그는 이중 언어(영어 + 타겟 언어) 고려 - 최대 발견성
- Long-form/Final 비디오 템플릿을 번역 사전에 추가
- 언어 감지는 `video_metadata.language` 필드 활용
- Fallback: 타겟 언어 번역이 없으면 영어로 graceful degradation

**Architectural Alignment:**
- 타겟 언어 사용자가 주요 대상 - 메타데이터는 그들의 언어로
- TICKET-056의 패턴 확장으로 일관성 유지
- Backward compatible - 기존 비디오에 영향 없음
- Low risk, high value - 즉각적인 사용자 경험 개선

