# [TICKET-003] Fix Undefined Variable Bug in get_job_expressions Endpoint

## Priority
- [x] Critical (System stability, security, data loss risk)
- [ ] High (Performance issues, significant tech debt)
- [ ] Medium (Code quality, maintainability improvements)
- [ ] Low (Nice-to-have ref정actorings)

## Type
- [ ] Refactoring
- [ ] Performance Optimization
- [ ] Test Coverage
- [x] Bug Fix
- [ ] Security Issue
- [ ] Technical Debt
- [ ] Code Duplication

## Impact Assessment
**Business Impact:**
- `get_job_expressions` API 엔드포인트가 실제로 작동하지 않음
- 사용자가 작업의 표현식 결과를 가져올 수 없음
- 프로덕션에서 런타임 에러 발생 가능 (NameError)

**Technical Impact:**
- 영향받는 모듈: `langflix/api/routes/jobs.py`
- 예상 변경 파일: 1개
- 간단한 버그 수정이지만 즉시 수정 필요

**Effort Estimate:**
- Small (< 1 day)

## Problem Description

### Current State
**Location:** `langflix/api/routes/jobs.py:578-602`

`get_job_expressions` 엔드포인트에서 정의되지 않은 변수 `jobs_db`를 참조하고 있습니다:

```python
@router.get("/jobs/{job_id}/expressions")
async def get_job_expressions(job_id: str) -> Dict[str, Any]:
    """Get expressions extracted from the job."""
    
    if job_id not in jobs_db:  # ❌ NameError: name 'jobs_db' is not defined
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs_db[job_id]  # ❌ NameError: name 'jobs_db' is not defined
    
    # Return ACTUAL expressions from processing
    if job["status"] != "COMPLETED":
        return {
            "job_id": job_id,
            "status": job["status"],
            "message": "Processing not completed yet",
            "expressions": []
        }
    
    return {
        "job_id": job_id,
        "status": job["status"],
        "expressions": job.get("expressions", []),
        "total_expressions": len(job.get("expressions", [])),
        "completed_at": job.get("completed_at")
    }
```

### Root Cause Analysis
- 다른 엔드포인트들은 Redis를 사용하는데 이 엔드포인트만 구식 `jobs_db` 딕셔너리를 참조
- 아마도 마이그레이션 중에 업데이트되지 않은 코드
- `get_job_status`는 올바르게 Redis를 사용하고 있음 (line 565-576)

### Evidence
- `langflix/api/routes/jobs.py:582-583`: `jobs_db` 변수 사용 (정의되지 않음)
- `langflix/api/routes/jobs.py:565-576`: `get_job_status`는 올바르게 Redis 사용
- `langflix/api/routes/jobs.py:604-612`: `list_jobs`도 올바르게 Redis 사용
- 코드베이스 전체에서 `jobs_db` 검색 시 이 위치에서만 사용됨

## Proposed Solution

### Approach
`get_job_expressions` 엔드포인트를 다른 엔드포인트들과 일관되게 Redis를 사용하도록 수정

### Implementation Details

```python
@router.get("/jobs/{job_id}/expressions")
async def get_job_expressions(job_id: str) -> Dict[str, Any]:
    """Get expressions extracted from the job."""
    
    redis_manager = get_redis_job_manager()
    job = redis_manager.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Return ACTUAL expressions from processing
    if job.get("status") != "COMPLETED":
        return {
            "job_id": job_id,
            "status": job.get("status", "UNKNOWN"),
            "message": "Processing not completed yet",
            "expressions": []
        }
    
    return {
        "job_id": job_id,
        "status": job.get("status", "UNKNOWN"),
        "expressions": job.get("expressions", []),
        "total_expressions": len(job.get("expressions", [])),
        "completed_at": job.get("completed_at")
    }
```

### Alternative Approaches Considered
- **Option 1: 현재 선택된 접근 (Redis 사용)**
  - 장점: 다른 엔드포인트와 일관성, 현재 아키텍처와 일치
  - 단점: 없음
  - 선택 이유: 가장 간단하고 올바른 수정

### Benefits
- **버그 수정**: 런타임 에러 해결
- **일관성**: 다른 엔드포인트들과 동일한 저장소 사용
- **기능 복구**: 표현식 결과 조회 기능 정상 작동

### Risks & Considerations
- **Breaking Changes**: 없음 (기존에 작동하지 않았음)
- **데이터 호환성**: Redis의 job 데이터 구조가 기대하는 형식과 일치하는지 확인 필요

## Testing Strategy

### Unit Tests
- `get_job_expressions` 엔드포인트가 올바르게 작동하는지 테스트
- Job이 없을 때 404 에러 반환 테스트
- Job이 완료되지 않았을 때 적절한 응답 반환 테스트
- Job이 완료되었을 때 표현식 목록 반환 테스트

### Integration Tests
- 실제 Redis 연결을 통한 엔드포인트 테스트
- 전체 워크플로우에서 표현식 조회가 작동하는지 검증

## Files Affected

**수정:**
- `langflix/api/routes/jobs.py` - `get_job_expressions` 함수 수정 (약 10줄 변경)

**테스트 추가/수정:**
- `tests/api/test_jobs.py` - `get_job_expressions` 테스트 추가 (만약 없으면)

## Dependencies
- Depends on: None
- Blocks: None
- Related to: None

## References
- Related code: `langflix/api/routes/jobs.py:565-576` (올바른 구현 예시)

## Architect Review Questions
**For the architect to consider:**
1. 이 버그가 프로덕션에 배포되었는지 확인 필요
2. 다른 엔드포인트에도 유사한 문제가 있는지 전체 검토 필요

## Success Criteria
How do we know this is successfully implemented?
- [ ] `get_job_expressions` 엔드포인트가 런타임 에러 없이 작동
- [ ] 단위 테스트 통과
- [ ] 통합 테스트 통과
- [ ] API 문서에 반영 (필요시)

---
## 🏛️ Architect Review & Approval

**Reviewed by:** Architect Agent
**Review Date:** 2025-01-30
**Decision:** ✅ APPROVED

**Strategic Rationale:**
- Critical runtime bug that completely breaks the API endpoint
- Simple fix that aligns with existing architecture (Redis usage)
- No breaking changes - fixes non-functional endpoint
- Immediate deployment recommended

**Implementation Phase:** Phase 0 - Immediate (This Week)
**Sequence Order:** #1 in implementation queue

**Architectural Guidance:**
- Use the same Redis pattern as `get_job_status` and `list_jobs` endpoints
- Ensure job data structure in Redis matches expected format
- Verify Redis connection handling is consistent with other endpoints
- Test with actual Redis instance, not just mocks

**Dependencies:**
- **Must complete first:** None
- **Should complete first:** None
- **Blocks:** None
- **Related work:** None

**Risk Mitigation:**
- Risk: Redis data structure mismatch
  - Mitigation: Verify job data format in Redis matches expected structure
- Risk: Missing job data migration
  - Mitigation: Check if any existing jobs need data migration
- **Rollback strategy:** Simple revert - restore old code (though it was broken)

**Enhanced Success Criteria:**
Beyond original ticket criteria:
- [ ] Verify Redis job data structure contains `expressions` field when completed
- [ ] Test with job in various states (PENDING, PROCESSING, FAILED, COMPLETED)
- [ ] Ensure response format matches API documentation
- [ ] Check for similar bugs in other endpoints (full codebase scan)

**Alternative Approaches Considered:**
- Original proposal: Use Redis (same as other endpoints) ✅ Selected
- Alternative 1: Create new in-memory store - Rejected (inconsistent with architecture)
- **Selected approach:** Redis - aligns with existing architecture and single source of truth

**Implementation Notes:**
- Start by: Verifying Redis job data structure format
- Watch out for: Missing `expressions` field in Redis job data
- Coordinate with: None
- Reference: `langflix/api/routes/jobs.py:565-576` for correct pattern

**Estimated Timeline:** < 2 hours
**Recommended Owner:** Any developer (straightforward fix)

