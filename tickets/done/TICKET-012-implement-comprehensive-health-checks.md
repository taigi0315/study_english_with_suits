# [TICKET-012] Implement Comprehensive Health Checks for All System Components

## Priority
- [ ] Critical (System stability, security, data loss risk)
- [ ] High (Performance issues, significant tech debt)
- [x] Medium (Code quality, maintainability improvements)
- [ ] Low (Nice-to-have refactorings)

## Type
- [ ] Refactoring
- [ ] Performance Optimization
- [ ] Test Coverage
- [ ] Bug Fix
- [ ] Security Issue
- [ ] Technical Debt
- [x] Code Duplication

## Impact Assessment
**Business Impact:**
- 프로덕션 모니터링 및 알림 시스템 구축의 기반
- 시스템 장애 조기 발견 및 대응 가능
- 운영팀의 시스템 상태 파악 용이

**Technical Impact:**
- 영향받는 모듈: `langflix/api/routes/health.py`, `langflix/monitoring/`
- 예상 변경 파일: 3-5개
- Breaking changes: 없음 (기존 엔드포인트 확장)

**Effort Estimate:**
- Small (< 1 day)

## Problem Description

### Current State
**Location:** `langflix/api/routes/health.py:20-33`

현재 health check endpoint가 플레이스홀더 구현으로 되어 있습니다:

```python
@router.get("/health/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """Detailed health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "LangFlix API",
        "version": "1.0.0",
        "components": {
            "database": "connected",  # TODO: Implement actual health checks
            "storage": "available",
            "tts": "ready"
        }
    }
```

**문제점:**
1. 실제 시스템 상태를 확인하지 않고 항상 "healthy" 반환
2. 데이터베이스 연결 상태 확인 미구현 (TODO 주석)
3. 스토리지 백엔드 상태 확인 미구현
4. TTS 서비스 상태 확인 미구현
5. 외부 의존성(Redis, LLM API 등) 상태 확인 없음
6. 프로덕션 모니터링 시스템과 통합 불가

### Root Cause Analysis
- 초기 API 스캐폴딩 시 빠른 구현을 위해 플레이스홀더로 구현
- 실제 health check 로직 구현 우선순위가 낮았음
- 모니터링 시스템과의 통합 필요성 인식 부족

### Evidence
- `langflix/api/routes/health.py:29`: TODO 주석으로 표시됨
- `langflix/api/routes/health.py:36-49`: Redis health check만 구현됨
- `langflix/monitoring/health_checker.py`: Health checker 모듈이 존재하지만 활용되지 않음
- 프로덕션 배포 시 실제 시스템 상태 확인 불가

## Proposed Solution

### Approach
1. **데이터베이스 Health Check**: 실제 연결 테스트 및 쿼리 실행
2. **스토리지 Health Check**: 스토리지 백엔드 읽기/쓰기 테스트
3. **TTS Service Health Check**: TTS 서비스 연결 및 응답 테스트
4. **Redis Health Check**: 기존 구현 활용 및 개선
5. **LLM API Health Check**: LLM API 연결 상태 확인 (선택적)
6. **통합 Health Status**: 모든 컴포넌트 상태를 종합하여 전체 상태 결정

### Implementation Details

#### Step 1: Create Health Check Service
```python
# langflix/monitoring/health_checker.py (기존 파일 확장)
from typing import Dict, Any, Optional
from sqlalchemy import text
from langflix import settings
from langflix.db.session import db_manager
from langflix.storage.factory import create_storage_backend

class SystemHealthChecker:
    """System health checker for all components."""
    
    def check_database(self) -> Dict[str, Any]:
        """Check database connectivity."""
        if not settings.get_database_enabled():
            return {"status": "disabled", "message": "Database disabled"}
        
        try:
            with db_manager.session() as db:
                # Simple query to test connection
                result = db.execute(text("SELECT 1")).scalar()
                if result == 1:
                    return {
                        "status": "healthy",
                        "message": "Database connection successful"
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "message": "Database query returned unexpected result"
                    }
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Database connection failed: {str(e)}"
            }
    
    def check_storage(self) -> Dict[str, Any]:
        """Check storage backend connectivity."""
        try:
            storage = create_storage_backend()
            # Try to list files (lightweight operation)
            storage.list_files("/", limit=1)
            return {
                "status": "healthy",
                "message": f"Storage backend ({type(storage).__name__}) accessible"
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Storage backend error: {str(e)}"
            }
    
    def check_redis(self) -> Dict[str, Any]:
        """Check Redis connectivity."""
        try:
            from langflix.core.redis_client import get_redis_job_manager
            redis_manager = get_redis_job_manager()
            health = redis_manager.health_check()
            return health
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"Redis connection failed: {str(e)}"
            }
    
    def check_tts(self) -> Dict[str, Any]:
        """Check TTS service connectivity."""
        try:
            # Check if TTS configuration is valid
            tts_provider = settings.get_tts_provider()
            if tts_provider == "gemini":
                # Check if API key is configured
                api_key = settings.get_gemini_api_key()
                if not api_key:
                    return {
                        "status": "unhealthy",
                        "message": "Gemini API key not configured"
                    }
                return {
                    "status": "healthy",
                    "message": "TTS service (Gemini) configured"
                }
            elif tts_provider == "lemonfox":
                api_key = settings.get_lemonfox_api_key()
                if not api_key:
                    return {
                        "status": "unhealthy",
                        "message": "LemonFox API key not configured"
                    }
                return {
                    "status": "healthy",
                    "message": "TTS service (LemonFox) configured"
                }
            else:
                return {
                    "status": "unknown",
                    "message": f"Unknown TTS provider: {tts_provider}"
                }
        except Exception as e:
            return {
                "status": "unhealthy",
                "message": f"TTS service check failed: {str(e)}"
            }
    
    def get_overall_health(self) -> Dict[str, Any]:
        """Get overall system health status."""
        components = {
            "database": self.check_database(),
            "storage": self.check_storage(),
            "redis": self.check_redis(),
            "tts": self.check_tts()
        }
        
        # Determine overall status
        statuses = [comp.get("status") for comp in components.values()]
        if "unhealthy" in statuses:
            overall_status = "unhealthy"
        elif "unknown" in statuses:
            overall_status = "degraded"
        else:
            overall_status = "healthy"
        
        return {
            "status": overall_status,
            "components": components,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
```

#### Step 2: Update Health Check Endpoint
```python
# langflix/api/routes/health.py
from langflix.monitoring.health_checker import SystemHealthChecker

@router.get("/health/detailed")
async def detailed_health_check() -> Dict[str, Any]:
    """Detailed health check endpoint with actual component checks."""
    checker = SystemHealthChecker()
    health = checker.get_overall_health()
    
    return {
        "status": health["status"],
        "timestamp": health["timestamp"],
        "service": "LangFlix API",
        "version": "1.0.0",
        "components": health["components"]
    }
```

#### Step 3: Add Individual Component Health Checks
```python
# langflix/api/routes/health.py
@router.get("/health/database")
async def database_health_check() -> Dict[str, Any]:
    """Database health check endpoint."""
    checker = SystemHealthChecker()
    return checker.check_database()

@router.get("/health/storage")
async def storage_health_check() -> Dict[str, Any]:
    """Storage health check endpoint."""
    checker = SystemHealthChecker()
    return checker.check_storage()

@router.get("/health/tts")
async def tts_health_check() -> Dict[str, Any]:
    """TTS service health check endpoint."""
    checker = SystemHealthChecker()
    return checker.check_tts()
```

### Alternative Approaches Considered
- **Option 1**: 각 컴포넌트별로 별도의 health check 모듈 생성 - Rejected (중앙화된 health checker가 더 관리하기 쉬움)
- **Option 2**: 외부 모니터링 라이브러리 사용 - Rejected (단순한 구현으로 충분, 외부 의존성 추가 불필요)
- **Option 3**: 선택한 접근법 - 기존 monitoring 모듈 확장, 간단한 연결 테스트 위주

### Benefits
- **실제 상태 확인**: 실제 시스템 컴포넌트 상태 확인
- **프로덕션 모니터링**: 모니터링 시스템과 통합 가능
- **조기 장애 발견**: 시스템 문제 조기 감지
- **디버깅 용이**: 각 컴포넌트별 상태 확인 가능
- **운영 안정성**: 프로덕션 환경에서 시스템 상태 파악 용이

### Risks & Considerations
- **성능 영향**: Health check가 실제 시스템 부하에 영향을 주지 않도록 가벼운 테스트만 수행
- **에러 처리**: Health check 실패가 실제 서비스에 영향을 주지 않도록 격리
- **보안**: Health check 엔드포인트 접근 제어 고려 (프로덕션 환경)

## Testing Strategy
- **Unit Tests**:
  - 각 컴포넌트별 health check 테스트
  - 정상 상태 테스트
  - 에러 상태 테스트
  - 전체 상태 종합 테스트
- **Integration Tests**:
  - 실제 데이터베이스/스토리지/Redis에 대한 health check 테스트
  - Health check endpoint 테스트
- **Error Scenarios**:
  - 데이터베이스 연결 실패 시나리오
  - 스토리지 백엔드 오류 시나리오
  - Redis 연결 실패 시나리오

## Files Affected
- `langflix/monitoring/health_checker.py` - SystemHealthChecker 클래스 구현/확장
- `langflix/api/routes/health.py` - detailed_health_check() 업데이트, 개별 health check 엔드포인트 추가
- `tests/api/test_health.py` - Health check 테스트 업데이트/추가
- `tests/monitoring/test_health_checker.py` - 새로운 테스트 파일 생성
- `docs/api/README_eng.md` - Health check 엔드포인트 문서 업데이트
- `docs/api/README_kor.md` - Health check 엔드포인트 문서 업데이트

## Dependencies
- Depends on: TICKET-010 (API dependencies 구현 후 데이터베이스 health check 가능)
- Blocks: None
- Related to: 프로덕션 모니터링 시스템 통합

## References
- Related documentation: `docs/api/README_eng.md`, `docs/monitoring/README_eng.md`
- FastAPI health checks: https://fastapi.tiangolo.com/advanced/testing/#testing-websockets
- Kubernetes health checks: https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/

## Architect Review Questions
**For the architect to consider:**
1. Health check의 빈도와 성능 영향은 어떻게 관리할 것인가?
2. 프로덕션 환경에서 health check 엔드포인트에 대한 인증/접근 제어가 필요한가?
3. LLM API health check는 포함해야 하는가? (비용 이슈)
4. Health check 결과를 캐싱해야 하는가?

## Success Criteria
How do we know this is successfully implemented?
- [ ] 데이터베이스 health check가 실제 연결 상태 확인
- [ ] 스토리지 health check가 실제 백엔드 상태 확인
- [ ] TTS 서비스 health check가 설정 상태 확인
- [ ] Redis health check가 정상 동작 (기존 구현 활용)
- [ ] 전체 health check가 모든 컴포넌트 상태를 종합
- [ ] 모든 관련 테스트 통과
- [ ] 프로덕션 모니터링 시스템과 통합 가능
- [ ] Health check가 실제 서비스 부하에 영향을 주지 않음

---
## 🏛️ Architect Review & Approval

**Reviewed by:** Architect Agent
**Review Date:** 2025-01-30
**Decision:** ✅ APPROVED (Deferred to Phase 1)

**Strategic Rationale:**
- 프로덕션 모니터링 기반
- 신속한 장애 감지로 안정성 향상
- `langflix/monitoring/health_checker.py` 확장으로 통합 용이

**Implementation Phase:** Phase 1 - Sprint 1 (2주)
**Sequence Order:** #3 (TICKET-010, TICKET-011 완료 후)

**Architectural Guidance:**
- TICKET-010 완료 후 DB health check 가능
- TICKET-011 `db_manager.session()`으로 DB 체크 구현
- `SystemHealthChecker` 추가/확장
- 간단한 체크만 수행(부하 최소화)

**Dependencies:**
- **Must complete first:** TICKET-010
- **Should complete first:** TICKET-011
- **Blocks:** 없음
- **Related work:** TICKET-010, TICKET-011

**Risk Mitigation:**
- 체크 실패 격리
- 가벼운 `SELECT 1`만 사용
- TTS는 설정 확인만
- LLM API 체크 생략(비용)

**Alternative Approaches Considered:**
- 분리 모듈: 중앙화가 관리 간단
- 외부 라이브러리: 구현으로 충분
- **Selected approach:** `health_checker.py` 확장

**Implementation Notes:**
- `health_checker.py`에 `SystemHealthChecker` 추가
- `db_manager.session()` 활용
- 간단한 `storage.list_files()`로 체크
- TTS는 설정 확인만, 실제 호출 안 함

**Estimated Timeline:** 반일 미만
**Recommended Owner:** 중급+

---
## ✅ Implementation Complete

**Implemented by:** Implementation Agent
**Implementation Date:** 2025-01-30
**Branch:** feature/TICKET-012-comprehensive-health-checks

### What Was Implemented
Comprehensive health check system for all system components (database, storage, TTS, Redis) with individual component endpoints and overall health status aggregation.

### Files Modified
- `langflix/monitoring/health_checker.py` - Added `SystemHealthChecker` class with methods for checking database, storage, TTS, and Redis health
- `langflix/api/routes/health.py` - Updated `/health/detailed` endpoint to use `SystemHealthChecker`, added individual component endpoints (`/health/database`, `/health/storage`, `/health/tts`), updated Redis endpoint to use `SystemHealthChecker`
- `tests/api/test_health.py` - Updated existing tests to work with new `SystemHealthChecker` implementation, added tests for new individual component endpoints
- `docs/api/README_eng.md` - Updated health check endpoints documentation with detailed descriptions
- `docs/api/README_kor.md` - Updated health check endpoints documentation in Korean

### Files Created
- `tests/monitoring/test_health_checker.py` - Comprehensive test suite for `SystemHealthChecker` class (15 test cases)

### Tests Added
**Unit Tests:**
- `tests/monitoring/test_health_checker.py` - 15 test cases covering:
  - Database health check (disabled, healthy, unhealthy scenarios)
  - Storage health check (healthy, unhealthy scenarios)
  - Redis health check (healthy, unhealthy scenarios)
  - TTS health check (Gemini healthy/unhealthy, LemonFox healthy/unhealthy, unknown provider)
  - Overall health status aggregation (all healthy, one unhealthy, degraded scenarios)

**API Tests:**
- Updated 8 existing tests in `tests/api/test_health.py`:
  - All tests updated to work with new `SystemHealthChecker`
  - Added 3 new tests for individual component endpoints (`/health/database`, `/health/storage`, `/health/tts`)

**Test Coverage:**
- SystemHealthChecker: 15/15 tests passing
- API health endpoints: 8/8 tests passing
- All tests use proper mocking to avoid external dependencies

### Documentation Updated
- [✓] Code comments added/updated in `SystemHealthChecker` class
- [✓] `docs/api/README_eng.md` updated with comprehensive health check endpoint documentation
- [✓] `docs/api/README_kor.md` updated with Korean documentation
- [✓] All health check endpoints documented with request/response examples

### Verification Performed
- [✓] All SystemHealthChecker unit tests pass (15/15)
- [✓] All API health endpoint tests pass (8/8)
- [✓] Manual testing completed (verified endpoints return correct structure)
- [✓] Edge cases verified (database disabled, storage errors, missing API keys)
- [✓] Code review self-completed
- [✓] No lint errors

### Deviations from Original Plan
No significant deviations. Implementation followed the ticket specification closely:
- Used `SystemHealthChecker` class as proposed
- Implemented all component checks (database, storage, TTS, Redis)
- Added individual component endpoints as specified
- Used `db_manager.session()` context manager as recommended by architect

### Breaking Changes
None. All changes are backward compatible:
- `/health/detailed` endpoint still works but now returns more detailed component status
- Existing `/health/redis` endpoint behavior preserved (now uses `SystemHealthChecker` internally)
- Response format enhanced but maintains compatibility

### Known Limitations
- TTS health check only verifies API key configuration, not actual service connectivity (to avoid API costs)
- LLM API health check not included (as per architect guidance to avoid costs)

### Additional Notes
- Health checks are lightweight to minimize performance impact
- All checks use proper error handling and isolation (one component failure doesn't affect others)
- `psutil` dependency is optional (handled gracefully if not installed, though it's required for other parts of the system)
- Database check uses context manager for proper resource management

