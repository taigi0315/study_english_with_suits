# [TICKET-005] Integrate Error Handler Module into Actual Codebase

## Priority
- [ ] Critical (System stability, security, data loss risk)
- [ ] High (Performance issues, significant tech debt)
- [x] Medium (Code quality, maintainability improvements)
- [ ] Low (Nice-to-have refactorings)

## Type
- [x] Refactoring
- [ ] Performance Optimization
- [ ] Test Coverage
- [ ] Bug Fix
- [ ] Security Issue
- [x] Technical Debt

## Impact Assessment
**Business Impact:**
- 에러 핸들링이 일관되지 않아 디버깅이 어려움
- 예외 발생 시 적절한 복구 메커니즘이 없음
- 사용자에게 친화적인 에러 메시지 부족

**Technical Impact:**
- 영향받는 모듈: 전체 코드베이스 (주로 `langflix/core/`, `langflix/api/`, `langflix/services/`)
- 예상 변경 파일: 10-15개
- 기존 error_handler.py는 구현되어 있으나 사용되지 않음

**Effort Estimate:**
- Medium (1-3 days)

## Problem Description

### Current State
**Location:** `langflix/core/error_handler.py`

고도로 정교한 에러 핸들링 시스템이 구현되어 있으나, 실제 코드베이스에서 거의 사용되지 않습니다:

```python
# langflix/core/error_handler.py exists with:
# - ErrorHandler class
# - RetryConfig
# - ErrorContext
# - ErrorReport
# - Decorators (@handle_error_decorator, @retry_on_error)
# - Fallback strategies
```

하지만 실제 사용 예시를 찾을 수 없습니다. 대신 코드베이스 전반에 걸쳐 기본적인 try-except 블록이 사용됩니다:

**예시 1: langflix/api/routes/jobs.py:460-477**
```python
except Exception as e:
    logger.error(f"Error processing job {job_id}: {e}")
    
    # Clean up temporary files
    try:
        if 'temp_video_path' in locals():
            os.unlink(temp_video_path)
        if 'temp_subtitle_path' in locals():
            os.unlink(temp_subtitle_path)
    except:
        pass
    
    # Update job with error
    redis_manager.update_job(job_id, {
        "status": "FAILED",
        "error": str(e),
        "failed_at": datetime.now(timezone.utc).isoformat()
    })
```

**예시 2: langflix/main.py:318-320**
```python
except Exception as e:
    logger.error(f"❌ Pipeline failed: {e}")
    raise
```

**예시 3: langflix/core/expression_analyzer.py:408-483**
```python
def _generate_content_with_retry(model, prompt: str, max_retries: int = 3, ...):
    # Custom retry logic instead of using error_handler
    for attempt in range(max_retries):
        try:
            # ... API call ...
        except Exception as e:
            # Custom error handling
```

### Root Cause Analysis
- `error_handler.py`가 나중에 추가되었지만 기존 코드에 통합되지 않음
- 기존 코드가 이미 작동하고 있어서 변경 우선순위가 낮았음
- 점진적 통합 계획이 없었음

### Evidence
- `langflix/core/error_handler.py`: 완전히 구현된 모듈 (483줄)
- grep 검색 결과: 실제 사용처 없음
- 코드베이스 전반에 기본 try-except 사용
- `_generate_content_with_retry`: 커스텀 retry 로직 (error_handler 미사용)

## Proposed Solution

### Approach
1. **점진적 통합**: 핵심 워크플로우부터 시작하여 단계적으로 통합
2. **데코레이터 활용**: 기존 함수를 최소한으로 변경하면서 에러 핸들링 추가
3. **커스텀 retry 로직 교체**: `expression_analyzer.py`의 커스텀 retry를 error_handler 사용으로 교체

### Implementation Details

#### Step 1: Expression Analyzer에 통합
`langflix/core/expression_analyzer.py` 수정:

```python
from langflix.core.error_handler import (
    handle_error_decorator,
    ErrorContext,
    ErrorCategory,
    ErrorSeverity,
    retry_on_error
)

# Replace custom _generate_content_with_retry
@retry_on_error(max_attempts=3, delay=2.0, exceptions=(Exception,))
def _generate_content_with_retry(model, prompt: str, ...):
    """Generate content with automatic retry using error_handler."""
    context = ErrorContext(
        category=ErrorCategory.API,
        severity=ErrorSeverity.MEDIUM,
        operation="generate_content",
        module="expression_analyzer"
    )
    
    try:
        # Original API call logic
        response = model.generate_content(prompt, ...)
        return response
    except Exception as e:
        from langflix.core.error_handler import handle_error
        handle_error(e, context, retry=True, fallback=False)
        raise

# Wrap analyze_chunk function
@handle_error_decorator(
    ErrorContext(
        category=ErrorCategory.PROCESSING,
        severity=ErrorSeverity.HIGH,
        operation="analyze_chunk",
        module="expression_analyzer"
    ),
    retry=True,
    fallback=True
)
def analyze_chunk(subtitle_chunk: List[dict], ...):
    # Existing logic with improved error handling
    pass
```

#### Step 2: API Routes에 통합
`langflix/api/routes/jobs.py` 수정:

```python
from langflix.core.error_handler import (
    handle_error_decorator,
    ErrorContext,
    ErrorCategory,
    ErrorSeverity
)

@handle_error_decorator(
    ErrorContext(
        category=ErrorCategory.SYSTEM,
        severity=ErrorSeverity.HIGH,
        operation="process_video_task",
        module="api.routes.jobs"
    ),
    retry=False,  # Job processing should not retry automatically
    fallback=False
)
async def process_video_task(...):
    """Process video in background task with error handling."""
    
    # Replace manual error handling with decorator
    # The decorator will automatically:
    # - Log errors with context
    # - Create error reports
    # - Update job status on failure
    
    try:
        # ... processing logic ...
    except Exception as e:
        # Error handler decorator will catch and handle
        raise  # Re-raise after logging/reporting
```

#### Step 3: Video Editor에 통합
`langflix/core/video_editor.py`의 주요 메서드에 통합:

```python
from langflix.core.error_handler import (
    handle_error_decorator,
    ErrorContext,
    ErrorCategory,
    ErrorSeverity,
    retry_on_error
)

@handle_error_decorator(
    ErrorContext(
        category=ErrorCategory.PROCESSING,
        severity=ErrorSeverity.HIGH,
        operation="create_educational_sequence",
        module="core.video_editor"
    ),
    retry=False,
    fallback=False
)
def create_educational_sequence(self, ...):
    # Existing logic with error handling
    pass

@retry_on_error(max_attempts=2, delay=1.0)
def _create_timeline_from_tts(self, ...):
    # FFmpeg operations can benefit from retry
    pass
```

#### Step 4: 에러 리포트 수집 및 모니터링
`langflix/api/main.py`에 에러 리포트 엔드포인트 추가 (선택적):

```python
from langflix.core.error_handler import get_error_handler

@router.get("/api/v1/errors/stats")
async def get_error_stats():
    """Get error statistics (for monitoring)."""
    handler = get_error_handler()
    stats = handler.get_error_statistics(hours=24)
    return stats
```

### Alternative Approaches Considered

**Option 1: error_handler.py 제거**
- 장점: 사용되지 않는 코드 제거
- 단점: 향후 개선 기회 상실, 이미 구현된 가치 있는 기능 버림
- 선택하지 않은 이유: 구현된 기능의 가치가 높음

**Option 2: 선택된 접근 (점진적 통합)**
- 장점: 기존 기능 유지, 점진적 개선, 위험 최소화
- 단점: 시간 투자 필요
- 선택 이유: 최선의 장기적 솔루션

### Benefits
- **일관된 에러 핸들링**: 모든 모듈에서 동일한 방식으로 에러 처리
- **자동 재시도**: 네트워크 에러 등에 대한 자동 재시도 메커니즘
- **에러 리포트**: 디버깅을 위한 구조화된 에러 정보
- **복구 메커니즘**: Fallback 전략으로 부분 실패 처리
- **모니터링**: 에러 통계 수집 가능

### Risks & Considerations
- **Breaking Changes**: 기존 에러 처리 동작이 변경될 수 있음
- **성능**: 데코레이터 오버헤드 (미미하지만 측정 필요)
- **점진적 마이그레이션**: 한 번에 모든 곳에 적용하지 않고 단계적으로

## Testing Strategy

### Unit Tests
- 에러 핸들러 데코레이터가 올바르게 작동하는지 테스트
- 재시도 로직이 올바르게 작동하는지 테스트
- Fallback 전략이 실행되는지 테스트

### Integration Tests
- 실제 워크플로우에서 에러 발생 시 올바르게 처리되는지 검증
- 에러 리포트가 생성되는지 검증

### Regression Tests
- 기존 기능이 동일하게 작동하는지 검증
- 에러 발생 시에도 적절한 응답이 반환되는지 검증

## Files Affected

**수정:**
- `langflix/core/expression_analyzer.py` - error_handler 데코레이터 추가
- `langflix/api/routes/jobs.py` - error_handler 데코레이터 추가
- `langflix/core/video_editor.py` - error_handler 데코레이터 추가
- `langflix/core/video_processor.py` - error_handler 통합 (필요시)
- `langflix/main.py` - LangFlixPipeline에 error_handler 통합
- 기타 주요 처리 함수들

**테스트 추가:**
- `tests/unit/test_error_handler_integration.py` - 통합 테스트
- 기존 테스트 업데이트

## Dependencies
- Depends on: None
- Blocks: None
- Related to: TICKET-001 (파이프라인 리팩토링과 함께 작업 시 시너지)

## References
- Related code: `langflix/core/error_handler.py` (483줄의 구현)
- Design patterns: Decorator Pattern, Retry Pattern, Circuit Breaker Pattern

## Architect Review Questions
**For the architect to consider:**
1. 에러 리포트를 외부 모니터링 시스템(Sentry 등)에 전송하는 것이 필요한가?
2. 재시도 정책이 비즈니스 로직과 일치하는가?
3. 에러 통계 엔드포인트가 필요한가?

---
## 🏛️ Architect Review & Approval

**Reviewed by:** Architect Agent
**Review Date:** 2025-01-30
**Decision:** ✅ APPROVED

**Strategic Rationale:**
- Leverages existing investment - `error_handler.py` is fully implemented but unused
- Improves reliability - structured error handling and automatic retry
- Enhances debugging - error reports with context
- Long-term benefit - foundation for monitoring and alerting
- Gradual integration - low risk, can be done incrementally

**Implementation Phase:** Phase 2 - Sprint 2 (Weeks 3-4)
**Sequence Order:** #5 in implementation queue (after core refactoring complete)

**Architectural Guidance:**
- **Integration Strategy**: Gradual, incremental integration
  - Phase 1: Core workflows (expression analysis, video processing)
  - Phase 2: API endpoints (job processing, error responses)
  - Phase 3: Edge cases and cleanup
- **Retry Policy**: Different strategies for different operations
  - API calls (LLM, TTS): Retry with exponential backoff
  - File operations: Retry once, then fail fast
  - Video processing: No auto-retry (manual intervention needed)
- **Error Reporting**:
  - Initially: Log to file/console (current pattern)
  - Future: External monitoring (Sentry, DataDog) - design allows for this
  - Error statistics endpoint: Nice-to-have, not required initially
- **Decorator Pattern**: Use `@handle_error_decorator` and `@retry_on_error` for gradual migration
- **Backward Compatibility**: Ensure existing error handling behavior preserved (don't break current logging)

**Dependencies:**
- **Must complete first:** TICKET-001 (service layer refactoring - easier to integrate after consolidation)
- **Should complete first:** TICKET-003 (critical bug fix)
- **Blocks:** None
- **Related work:** TICKET-001 (can integrate in new service), TICKET-002 (temp file cleanup error handling)

**Risk Mitigation:**
- Risk: Breaking existing error handling behavior
  - Mitigation: Gradual integration - start with non-critical paths, verify behavior unchanged
- Risk: Retry loops causing resource exhaustion
  - Mitigation: Configurable retry limits, exponential backoff, circuit breaker pattern
- Risk: Performance overhead from decorators
  - Mitigation: Measure overhead (should be minimal), profile if needed
- **Rollback strategy:** Gradual - can revert individual integrations if issues arise

**Enhanced Success Criteria:**
Beyond original ticket criteria:
- [ ] Core workflows use error handler (expression analysis, video processing)
- [ ] Retry logic tested with various failure scenarios
- [ ] Error reports generated with useful context
- [ ] Existing error logging behavior preserved
- [ ] Performance impact measured and acceptable (< 5% overhead)
- [ ] Integration tests verify error handling works correctly

**Alternative Approaches Considered:**
- Original proposal: Gradual integration with decorators ✅ Selected
- Alternative 1: Remove `error_handler.py` - Rejected (waste of investment, loses functionality)
- Alternative 2: Full replacement immediately - Rejected (too risky, breaks existing behavior)
- **Selected approach:** Gradual integration - safest, allows learning and adjustment

**Implementation Notes:**
- Start by: Integrating in `expression_analyzer.py` (replaces custom retry logic)
- Watch out for: Retry policy conflicts with business logic (some operations shouldn't retry)
- Coordinate with: TICKET-001 team if working on service layer (integrate error handling in new service)
- Reference: `langflix/core/error_handler.py` for full API, existing retry in `expression_analyzer.py::_generate_content_with_retry`

**Estimated Timeline:** 2-3 days (with gradual integration and testing)
**Recommended Owner:** Senior engineer (requires understanding of error handling patterns)

## Success Criteria
How do we know this is successfully implemented?
- [ ] 핵심 워크플로우에 error_handler 통합됨
- [ ] 커스텀 retry 로직이 error_handler로 교체됨
- [ ] 에러 발생 시 구조화된 리포트가 생성됨
- [ ] 자동 재시도가 작동함 (테스트로 검증)
- [ ] 기존 기능 동작 유지
- [ ] 에러 통계 수집 가능 (선택적)

