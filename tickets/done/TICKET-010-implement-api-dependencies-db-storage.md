# [TICKET-010] Implement API Dependencies for Database and Storage

## Priority
- [ ] Critical (System stability, security, data loss risk)
- [x] High (Performance issues, significant tech debt)
- [ ] Medium (Code quality, maintainability improvements)
- [ ] Low (Nice-to-have refactorings)

## Type
- [x] Refactoring
- [ ] Performance Optimization
- [ ] Test Coverage
- [ ] Bug Fix
- [ ] Security Issue
- [x] Technical Debt
- [ ] Code Duplication

## Impact Assessment
**Business Impact:**
- API 엔드포인트가 데이터베이스와 스토리지 백엔드를 사용할 수 없음
- FastAPI 의존성 주입 패턴이 완전히 구현되지 않아 향후 기능 확장 제약
- 프로덕션 배포 시 필수 기능 부재

**Technical Impact:**
- 영향받는 모듈: `langflix/api/dependencies.py`, `langflix/api/routes/`, `langflix/api/main.py`
- 예상 변경 파일: 5-7개
- Breaking changes: 없음 (현재 None 반환하므로 구현하면 기능 활성화)

**Effort Estimate:**
- Medium (1-3 days)

## Problem Description

### Current State
**Location:** `langflix/api/dependencies.py:10-20`

현재 API 의존성 주입 함수들이 플레이스홀더로만 구현되어 있습니다:

```python
def get_db() -> Generator[Session, None, None]:
    """Get database session."""
    # TODO: Implement actual database session
    # For now, return None
    yield None

def get_storage():
    """Get storage backend."""
    # TODO: Implement actual storage backend
    # For now, return None
    return None
```

**문제점:**
1. FastAPI의 `Depends()`를 사용하는 모든 엔드포인트에서 실제 데이터베이스/스토리지 기능 사용 불가
2. 문서화된 API 엔드포인트(`docs/api/README_eng.md:33-34`)에서도 TODO로 표시됨
3. `langflix/db/session.py`의 `get_db_session()`와 `langflix/storage/factory.py`의 `create_storage_backend()`가 이미 존재하지만 API에서 사용되지 않음
4. Health check endpoint(`langflix/api/routes/health.py:29`)에서도 데이터베이스 상태 확인 불가

### Root Cause Analysis
- 초기 API 스캐폴딩 시 빠른 구현을 위해 플레이스홀더로 구현
- 데이터베이스와 스토리지 백엔드가 구현되었지만 API 통합이 누락됨
- 의존성 주입 패턴의 일관성 부족

### Evidence
- `langflix/api/dependencies.py:10-20`: 플레이스홀더 구현
- `docs/api/README_eng.md:33-34`: TODO 주석으로 문서화됨
- `langflix/db/session.py:59-61`: `get_db_session()` 함수 존재
- `langflix/storage/factory.py`: `create_storage_backend()` 함수 존재
- `langflix/api/routes/health.py:29`: 데이터베이스 health check 미구현
- FastAPI 라우트에서 `Depends(get_db)` 또는 `Depends(get_storage)` 사용 시도 시 None 반환

## Proposed Solution

### Approach
1. **데이터베이스 의존성 구현**: `get_db_session()`을 사용하여 FastAPI 의존성 주입 패턴으로 래핑
2. **스토리지 의존성 구현**: `create_storage_backend()`를 사용하여 FastAPI 의존성 주입 패턴으로 래핑
3. **컨텍스트 관리**: FastAPI의 lifespan과 연계하여 세션/리소스 정리 보장
4. **Health check 통합**: Health check endpoint에서 실제 데이터베이스 연결 상태 확인

### Implementation Details

#### Step 1: Implement Database Dependency
```python
# langflix/api/dependencies.py
from typing import Generator
from sqlalchemy.orm import Session
from contextlib import contextmanager
from langflix.db.session import DatabaseManager
from langflix import settings

# Global database manager instance
db_manager = DatabaseManager()

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database session.
    
    Yields:
        Session: Database session
    """
    if not settings.get_database_enabled():
        # Return None if database is disabled (file-only mode)
        yield None
        return
    
    # Initialize database if not already initialized
    if not db_manager._initialized:
        db_manager.initialize()
    
    # Get session
    db = db_manager.get_session()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
```

#### Step 2: Implement Storage Dependency
```python
# langflix/api/dependencies.py
from langflix.storage.factory import create_storage_backend
from langflix.storage.base import StorageBackend

def get_storage() -> StorageBackend:
    """
    FastAPI dependency for storage backend.
    
    Returns:
        StorageBackend: Storage backend instance (Local or GCS)
    """
    return create_storage_backend()
```

#### Step 3: Update Health Check Endpoint
```python
# langflix/api/routes/health.py
@router.get("/health/detailed")
async def detailed_health_check(
    db: Session = Depends(get_db),
    storage = Depends(get_storage)
) -> Dict[str, Any]:
    """Detailed health check endpoint."""
    components = {}
    
    # Check database
    if db is not None:
        try:
            db.execute(text("SELECT 1"))
            components["database"] = "connected"
        except Exception as e:
            components["database"] = f"error: {str(e)}"
    else:
        components["database"] = "disabled"
    
    # Check storage
    try:
        # Simple check - try to list root path
        storage.list_files("/", limit=1)
        components["storage"] = "available"
    except Exception as e:
        components["storage"] = f"error: {str(e)}"
    
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "LangFlix API",
        "version": "1.0.0",
        "components": components,
        "tts": "ready"
    }
```

#### Step 4: Update API Lifespan
```python
# langflix/api/main.py
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("LangFlix API starting up...")
    
    # Initialize database connection pool if enabled
    from langflix import settings
    if settings.get_database_enabled():
        from langflix.api.dependencies import db_manager
        db_manager.initialize()
        logger.info("Database connection pool initialized")
    
    # Cleanup Redis jobs on startup
    try:
        redis_manager = get_redis_job_manager()
        redis_manager.cleanup_expired_jobs()
        redis_manager.cleanup_stale_jobs()
        logger.info("Redis job cleanup completed")
    except Exception as e:
        logger.warning(f"Redis cleanup failed: {e}")
    
    yield
    
    logger.info("LangFlix API shutting down...")
    
    # Close database connections
    if settings.get_database_enabled():
        from langflix.api.dependencies import db_manager
        db_manager.close()
        logger.info("Database connections closed")
    
    logger.info("LangFlix API shutdown complete")
```

### Alternative Approaches Considered
- **Option 1**: 각 라우트에서 직접 `get_db_session()` 호출 - Rejected (의존성 주입 패턴과 불일치)
- **Option 2**: 별도의 초기화 함수로 분리 - Rejected (FastAPI의 의존성 주입 패턴 활용이 더 적절)
- **Option 3**: 선택한 접근법 - FastAPI의 표준 의존성 주입 패턴 사용, lifespan과 연계하여 리소스 관리

### Benefits
- **API 기능 활성화**: 데이터베이스와 스토리지 백엔드 사용 가능
- **표준 패턴 준수**: FastAPI의 권장 의존성 주입 패턴 사용
- **리소스 관리**: 자동 세션/커넥션 정리 보장
- **Health check 개선**: 실제 시스템 상태 확인 가능
- **확장성**: 향후 인증/권한 등 추가 의존성 쉽게 확장 가능

### Risks & Considerations
- **Breaking changes**: 없음 (현재 None 반환하므로 구현 시 기능 활성화)
- **데이터베이스 연결 풀**: 기존 `DatabaseManager`의 연결 풀 관리와 충돌 없음
- **스토리지 백엔드**: 기존 `create_storage_backend()` 팩토리 패턴 활용
- **에러 처리**: 세션 롤백 및 예외 처리 포함 필요

## Testing Strategy
- **Unit Tests**: 
  - `test_api_dependencies.py` 생성
  - `get_db()` 정상 동작 테스트 (yield, commit, rollback, close)
  - `get_storage()` 정상 동작 테스트
  - 데이터베이스 비활성화 시 None 반환 테스트
- **Integration Tests**:
  - Health check endpoint에서 실제 데이터베이스 연결 테스트
  - 실제 라우트에서 `Depends(get_db)` 사용 테스트
  - Lifespan에서 데이터베이스 초기화/정리 테스트
- **Error Scenarios**:
  - 데이터베이스 연결 실패 시 예외 처리 테스트
  - 스토리지 백엔드 초기화 실패 시 예외 처리 테스트

## Files Affected
- `langflix/api/dependencies.py` - get_db(), get_storage() 구현
- `langflix/api/routes/health.py` - detailed_health_check() 업데이트
- `langflix/api/main.py` - lifespan() 업데이트 (데이터베이스 초기화/정리)
- `tests/api/test_dependencies.py` - 새로운 테스트 파일 생성
- `tests/api/test_health.py` - health check 테스트 업데이트
- `docs/api/README_eng.md` - TODO 제거, 구현 내용 문서화
- `docs/api/README_kor.md` - TODO 제거, 구현 내용 문서화

## Dependencies
- Depends on: None
- Blocks: 향후 데이터베이스/스토리지 사용하는 API 엔드포인트 구현
- Related to: TICKET-011 (Health check 구현)

## References
- Related documentation: `docs/api/README_eng.md`, `docs/db/README_eng.md`, `docs/storage/README_eng.md`
- FastAPI dependency injection: https://fastapi.tiangolo.com/tutorial/dependencies/
- SQLAlchemy session management: `langflix/db/session.py`
- Storage factory: `langflix/storage/factory.py`

## Architect Review Questions
**For the architect to consider:**
1. 데이터베이스 연결 풀 관리 전략이 lifespan과 충돌하지 않는가?
2. 스토리지 백엔드 인스턴스는 매 요청마다 생성해도 되는가, 아니면 싱글톤으로 관리해야 하는가?
3. Health check에서 실제 쿼리를 실행하는 것이 프로덕션 부하에 영향을 미치지 않는가?
4. 에러 발생 시 API 응답 전략은 무엇인가? (예: 데이터베이스 연결 실패 시 503 vs 500)

## Success Criteria
How do we know this is successfully implemented?
- [ ] `get_db()`가 실제 데이터베이스 세션을 yield하고 자동으로 commit/rollback/close 처리
- [ ] `get_storage()`가 실제 스토리지 백엔드 인스턴스를 반환
- [ ] Health check endpoint에서 실제 데이터베이스/스토리지 상태 확인 가능
- [ ] 모든 관련 테스트 통과
- [ ] API 문서에서 TODO 제거됨
- [ ] 데이터베이스 비활성화 시 None 반환 (file-only mode 지원)
- [ ] 예외 발생 시 적절한 롤백 및 리소스 정리

---
## 🏛️ Architect Review & Approval

**Reviewed by:** Architect Agent
**Review Date:** 2025-01-30
**Decision:** ✅ APPROVED

**Strategic Rationale:**
- FastAPI 의존성 주입은 표준 패턴이라 통합 필요
- `langflix/db/session.py`, `langflix/storage/factory.py`는 이미 구현되어 통합만 남음
- 구현 시 DB/Storage를 사용하는 API 엔드포인트 확장 기반 제공

**Implementation Phase:** Phase 0 - Immediate
**Sequence Order:** #1 (TICKET-011, TICKET-012 사전 필요)

**Architectural Guidance:**
- `get_db()`는 FastAPI 연동 시 TICKET-011 `session()` context manager 활용
- Storage 백엔드는 경량이므로 매 요청 생성 허용
- Health check 쿼리는 간단하므로 부하 영향 미미
- 연결 실패/부재는 503(Service Unavailable)

**Dependencies:**
- **Must complete first:** 없음
- **Should complete first:** TICKET-011, TICKET-012(선택, `session()` 사용)
- **Blocks:** DB/Storage 사용 API 확장
- **Related work:** TICKET-011, TICKET-012

**Risk Mitigation:**
- 풀 관리는 단일 `DatabaseManager`로 중복 방지
- Health check는 간단한 `SELECT 1`만 사용
- DB 미설정 시 `None` 반환은 기존 동작 유지
- 요청 수준 에러는 FastAPI 기본 처리 활용

**Alternative Approaches Considered:**
- 라우트 직접 호출: 의존성 주입과 불일치
- 별도 초기화 함수: lifespan 통합이 낫음
- **Selected approach:** 표준 `Depends()` 사용

**Implementation Notes:**
- `langflix/api/dependencies.py`에 `get_db()`, `get_storage()` 구현
- `langflix/api/main.py`의 `lifespan()`에서 풀 초기화
- `get_db()`는 TICKET-011 `db_manager.session()` 적용
- `langflix/api/routes/health.py`에서 실제 상태 확인

**Estimated Timeline:** 1–2일
**Recommended Owner:** 중급+

---
## ✅ Implementation Complete

**Implemented by:** Implementation Engineer Agent
**Implementation Date:** 2025-01-30
**Branch:** feature/TICKET-010-implement-api-dependencies-db-storage

### What Was Implemented
- Implemented `get_db()` dependency function to provide SQLAlchemy database sessions via FastAPI dependency injection
- Implemented `get_storage()` dependency function to provide storage backend instances
- Updated health check endpoint to perform actual database and storage connectivity checks
- Updated application lifespan to initialize and cleanup database connections

### Files Modified
- `langflix/api/dependencies.py` - Implemented `get_db()` and `get_storage()` functions
- `langflix/api/routes/health.py` - Updated `detailed_health_check()` to use actual dependencies
- `langflix/api/main.py` - Updated `lifespan()` to initialize and cleanup database connections
- `tests/api/test_health.py` - Updated tests to mock dependencies correctly
- `docs/api/README_eng.md` - Updated documentation with implementation details and usage examples
- `docs/api/README_kor.md` - Updated Korean documentation with implementation details and usage examples

### Files Created
- `tests/api/test_dependencies.py` - Comprehensive unit tests for dependency functions

### Tests Added
**Unit Tests:**
- `tests/api/test_dependencies.py`:
  - `test_get_db_when_database_disabled` - Tests None return when DB disabled
  - `test_get_db_when_database_enabled` - Tests session yield and commit/close
  - `test_get_db_rollback_on_exception` - Tests rollback on exceptions
  - `test_get_db_initializes_if_not_initialized` - Tests auto-initialization
  - `test_get_storage_returns_storage_backend` - Tests storage backend return
  - `test_get_storage_calls_factory` - Tests factory function call

**Integration Tests:**
- `tests/api/test_health.py`:
  - `test_detailed_health_check_with_database_disabled` - Tests health check with DB disabled
  - `test_detailed_health_check_with_database_enabled` - Tests health check with DB enabled
  - `test_detailed_health_check_database_error` - Tests error handling for DB failures
  - `test_detailed_health_check_storage_error` - Tests error handling for storage failures

**Test Coverage:**
- All 11 tests passing
- Unit tests: 6 tests
- Integration tests: 5 tests (including existing basic health check)

### Documentation Updated
- [✓] Code comments added/updated in `dependencies.py` and `health.py`
- [✓] `docs/api/README_eng.md` updated with dependency injection documentation and usage examples
- [✓] `docs/api/README_kor.md` updated with Korean documentation
- [✓] Removed TODO comments from documentation
- [✓] Added usage examples for both `get_db()` and `get_storage()`

### Verification Performed
- [✓] All tests pass (11/11)
- [✓] Manual testing completed (verified health check endpoint behavior)
- [✓] Edge cases verified (database disabled, errors)
- [✓] Performance acceptable (lightweight operations)
- [✓] No lint errors
- [✓] Code self-reviewed

### Deviations from Original Plan
- None - Implementation followed the ticket's proposed solution exactly

### Breaking Changes
- None - Previous implementation returned `None`, now returns actual instances when configured

### Known Limitations
- None - All success criteria met

### Additional Notes
- Database session management uses existing `DatabaseManager` from `langflix.db.session`
- Storage backend uses existing `create_storage_backend()` factory from `langflix.storage.factory`
- Health check endpoint now provides actual component status instead of placeholder values
- All dependency functions properly handle the case when database is disabled (file-only mode)

---
