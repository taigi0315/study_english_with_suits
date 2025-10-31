# [TICKET-001] Extract Video Processing Pipeline Logic from API Task Function

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
- [x] Code Duplication

## Impact Assessment
**Business Impact:**
- 현재 `process_video_task` 함수가 450+ 줄로 매우 길어 유지보수가 어렵고 버그 발생 가능성이 높음
- 비디오 처리 로직이 API 라우트에 직접 구현되어 있어 CLI와 API 간 로직이 중복됨
- 새로운 기능 추가 시 여러 곳을 수정해야 함

**Technical Impact:**
- 영향받는 모듈: `langflix/api/routes/jobs.py`, `langflix/main.py`, `langflix/services/pipeline_runner.py`
- 예상 변경 파일: 4-6개
- 중복 로직 제거로 코드베이스 크기 약 30% 감소 예상

**Effort Estimate:**
- Medium (1-3 days)

## Problem Description

### Current State
**Location:** `langflix/api/routes/jobs.py:28-477`

`process_video_task` 함수가 450줄이 넘는 거대한 함수로, 전체 비디오 처리 파이프라인을 직접 구현하고 있습니다:

```python
async def process_video_task(
    job_id: str,
    video_content: bytes,
    subtitle_content: bytes,
    # ... parameters ...
):
    """Process video in background task with REAL LangFlix pipeline."""
    # 450+ lines of inline pipeline logic
    # - Parse subtitles
    # - Chunk subtitles  
    # - Analyze expressions
    # - Create output structure
    # - Process expressions
    # - Create educational videos
    # - Create short videos
    # - Concatenate final video
    # - Cleanup temp files
```

이 로직은 `langflix/main.py`의 `LangFlixPipeline` 클래스와 거의 동일하며, 다음과 같은 문제가 있습니다:

1. **코드 중복**: 동일한 로직이 API 라우트와 CLI 모두에 존재
2. **유지보수 어려움**: 버그 수정이나 기능 추가 시 여러 곳을 수정해야 함
3. **테스트 어려움**: 거대한 함수를 단위 테스트하기 어려움
4. **책임 분리 부족**: API 라우트가 비즈니스 로직까지 처리

### Root Cause Analysis
- 초기 개발 시 빠른 구현을 위해 API 엔드포인트에 로직을 직접 구현
- 기존 CLI 파이프라인(`LangFlixPipeline`)을 재사용하지 않고 새로 구현
- 점진적 리팩토링 없이 기능이 추가되면서 함수가 계속 커짐

### Evidence
- `langflix/api/routes/jobs.py:28-477`: 450+ 줄의 `process_video_task` 함수
- `langflix/main.py:177-757`: `LangFlixPipeline` 클래스에 유사한 로직 존재
- `langflix/services/pipeline_runner.py`: 또 다른 파이프라인 래퍼 존재하지만 사용되지 않음
- 중복된 로직:
  - Subtitle parsing: `jobs.py:86` vs `main.py:322`
  - Expression analysis: `jobs.py:105-130` vs `main.py:332-379`
  - Video processing: `jobs.py:194-261` vs `main.py:410-463`
  - Educational video creation: `jobs.py:262-298` vs `main.py:465-519`

## Proposed Solution

### Approach
1. **공통 서비스 클래스 생성**: `LangFlixPipeline`을 기반으로 API와 CLI 모두에서 사용 가능한 통합 파이프라인 서비스 생성
2. **API 작업 함수 리팩토링**: `process_video_task`는 작업 관리와 진행 상황 업데이트만 담당하고, 실제 처리는 서비스에 위임
3. **임시 파일 관리 개선**: 임시 파일 관리를 서비스 레벨에서 일관되게 처리

### Implementation Details

#### Step 1: 공통 파이프라인 서비스 생성
`langflix/services/video_pipeline_service.py` 생성:

```python
class VideoPipelineService:
    """Unified video processing pipeline service for both API and CLI."""
    
    def __init__(self, language_code: str, output_dir: str = "output"):
        self.language_code = language_code
        self.output_dir = output_dir
        self.pipeline = LangFlixPipeline(...)
    
    def process_video(
        self,
        video_path: str,
        subtitle_path: str,
        show_name: str,
        episode_name: str,
        max_expressions: int = 10,
        language_level: str = "intermediate",
        test_mode: bool = False,
        no_shorts: bool = False,
        progress_callback: Optional[Callable[[int, str], None]] = None
    ) -> Dict[str, Any]:
        """
        Process video with unified pipeline.
        
        Args:
            progress_callback: Optional callback(progress: int, message: str)
        """
        # Use existing LangFlixPipeline.run() method
        # Add progress callbacks to pipeline steps
        # Return standardized result format
        pass
```

#### Step 2: API 작업 함수 간소화
`langflix/api/routes/jobs.py`의 `process_video_task` 리팩토링:

```python
async def process_video_task(
    job_id: str,
    video_content: bytes,
    subtitle_content: bytes,
    # ... parameters ...
):
    """Process video in background task - simplified version."""
    
    redis_manager = get_redis_job_manager()
    
    try:
        # Update status
        redis_manager.update_job(job_id, {"status": "PROCESSING", "progress": 10})
        
        # Save uploaded files
        temp_video_path, temp_subtitle_path = _save_uploaded_files(
            job_id, video_content, subtitle_content
        )
        
        # Progress callback wrapper
        def update_progress(progress: int, message: str):
            redis_manager.update_job(job_id, {
                "progress": progress,
                "current_step": message
            })
        
        # Use unified pipeline service
        from langflix.services.video_pipeline_service import VideoPipelineService
        
        service = VideoPipelineService(language_code=language_code, output_dir="output")
        result = service.process_video(
            video_path=temp_video_path,
            subtitle_path=temp_subtitle_path,
            show_name=show_name,
            episode_name=episode_name,
            max_expressions=max_expressions,
            language_level=language_level,
            test_mode=test_mode,
            no_shorts=no_shorts,
            progress_callback=update_progress
        )
        
        # Update job with results
        redis_manager.update_job(job_id, {
            "status": "COMPLETED",
            "progress": 100,
            "expressions": result.get("expressions", []),
            "completed_at": datetime.now(timezone.utc).isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error processing job {job_id}: {e}")
        redis_manager.update_job(job_id, {
            "status": "FAILED",
            "error": str(e),
            "failed_at": datetime.now(timezone.utc).isoformat()
        })
    finally:
        # Cleanup temp files
        _cleanup_temp_files(temp_video_path, temp_subtitle_path)
```

#### Step 3: LangFlixPipeline에 진행 상황 콜백 추가
`langflix/main.py`의 `LangFlixPipeline`에 진행 상황 업데이트 지원:

```python
class LangFlixPipeline:
    def __init__(self, ..., progress_callback: Optional[Callable[[int, str], None]] = None):
        self.progress_callback = progress_callback
    
    def run(self, ...):
        if self.progress_callback:
            self.progress_callback(10, "Parsing subtitles...")
        self.subtitles = self._parse_subtitles()
        
        if self.progress_callback:
            self.progress_callback(30, "Analyzing expressions...")
        self.expressions = self._analyze_expressions(...)
        # ... etc
```

### Alternative Approaches Considered

**Option 1: LangFlixPipeline을 그대로 사용**
- 장점: 최소한의 변경
- 단점: CLI 전용 설계로 API의 진행 상황 추적이 어려움
- 선택하지 않은 이유: API 요구사항(진행 상황 업데이트)을 충족하기 어려움

**Option 2: 기존 PipelineRunner 사용**
- 장점: 이미 존재하는 코드 재사용
- 단점: 현재 미완성 상태이고 사용되지 않음, 버그 존재 (`selected_expressions` 변수 미정의)
- 선택하지 않은 이유: 완전히 재작성해야 함

**Option 3: 선택된 접근 (통합 서비스)**
- 장점: 코드 중복 제거, 일관된 인터페이스, 테스트 용이, 유지보수 용이
- 단점: 중간 레이어 추가로 초기 구현 시간 필요
- 선택 이유: 장기적인 유지보수와 확장성 측면에서 최선

### Benefits
- **코드 중복 제거**: 450줄의 중복 로직 제거, 단일 진실 공급원(Single Source of Truth)
- **유지보수성 향상**: 버그 수정이나 기능 추가 시 한 곳만 수정
- **테스트 용이성**: 작은 단위로 분리되어 단위 테스트 작성이 쉬움
- **확장성 향상**: 새로운 클라이언트(예: 웹소켓 실시간 업데이트) 추가가 용이
- **가독성 향상**: 각 함수의 책임이 명확해짐

### Risks & Considerations
- **Breaking Changes**: 기존 API 동작이 변경될 수 있으므로 테스트 필수
- **마이그레이션**: 기존 진행 중인 작업 처리 방안 필요
- **성능**: 추가 레이어로 인한 미세한 오버헤드 가능 (무시 가능한 수준)
- **역호환성**: API 응답 형식 유지 필요

## Testing Strategy

### Unit Tests
- `VideoPipelineService.process_video()`: 다양한 입력에 대한 테스트
- Progress callback이 올바르게 호출되는지 검증
- 에러 발생 시 적절한 정리(cleanup)가 이루어지는지 검증

### Integration Tests
- API 엔드포인트를 통한 전체 워크플로우 테스트
- CLI와 API 모두에서 동일한 결과가 나오는지 검증
- 진행 상황 업데이트가 Redis에 올바르게 저장되는지 검증

### Regression Tests
- 기존 API 테스트 스위트 실행하여 동작 유지 확인
- 기존 CLI 기능 테스트 실행하여 동작 유지 확인

## Files Affected

**새로 생성:**
- `langflix/services/video_pipeline_service.py` - 통합 파이프라인 서비스

**수정:**
- `langflix/api/routes/jobs.py` - `process_video_task` 함수 대폭 간소화 (450줄 → ~100줄)
- `langflix/main.py` - `LangFlixPipeline`에 `progress_callback` 지원 추가
- `tests/api/test_jobs.py` - 새로운 서비스를 사용하도록 테스트 업데이트
- `tests/integration/test_pipeline_service.py` - 새로운 통합 테스트 추가

**제거 고려:**
- `langflix/services/pipeline_runner.py` - 미사용 및 버그 있음, 제거 또는 재작성

## Dependencies
- Depends on: None
- Blocks: TICKET-002 (임시 파일 관리 개선), TICKET-003 (에러 처리 통합)
- Related to: TICKET-004 (파일명 sanitization 중복 제거)

## References
- Related documentation: `docs/core/README_eng.md`, `docs/api/README_eng.md`
- Design patterns: Service Layer Pattern, Strategy Pattern
- Similar issues: `langflix/services/pipeline_runner.py`의 미사용 코드

## Architect Review Questions
**For the architect to consider:**
1. 서비스 레이어 추가가 아키텍처 방향과 일치하는가?
2. 진행 상황 콜백을 이벤트 기반 시스템으로 확장하는 것이 더 나은가?
3. 이 리팩토링이 다른 모듈(예: YouTube 업로더)에도 영향을 주는가?
4. 제안된 타임라인이 현실적인가?
5. 단계적 마이그레이션 전략이 필요한가?

---
## 🏛️ Architect Review & Approval

**Reviewed by:** Architect Agent
**Review Date:** 2025-01-30
**Decision:** ✅ APPROVED

**Strategic Rationale:**
- This is a critical foundation refactoring that eliminates the largest code duplication (450+ lines)
- Aligns with Service Layer Pattern - consolidates business logic into reusable service
- Unblocks other improvements (TICKET-002, TICKET-004 can build on this)
- Long-term maintainability essential for system health
- Single source of truth for video processing pipeline

**Implementation Phase:** Phase 1 - Sprint 1 (Weeks 1-2)
**Sequence Order:** #2 in implementation queue (after TICKET-003)

**Architectural Guidance:**
- **Service Design**: Create `VideoPipelineService` as thin wrapper around `LangFlixPipeline` with progress callbacks
- **Progress Callbacks**: Use simple callback pattern (function: `(progress: int, message: str) -> None`) - can evolve to event-based later if needed
- **File Reuse**: Consider TICKET-002 (temp file management) when implementing cleanup logic
- **Error Handling**: Consider TICKET-005 (error handler integration) for unified error handling
- **Legacy Code**: Evaluate `pipeline_runner.py` - likely can be removed or consolidated into new service
  - Note: `pipeline_runner.py:98` has undefined variable `selected_expressions` - fix or remove
- **Testing Strategy**: Focus on integration tests - ensure API and CLI produce identical results

**Dependencies:**
- **Must complete first:** TICKET-003 (critical bug fix)
- **Should complete first:** None
- **Blocks:** TICKET-002 (can be done in parallel, but coordination helps), TICKET-004 (should follow this)
- **Related work:** TICKET-005 (error handler integration can follow)

**Risk Mitigation:**
- Risk: Breaking API behavior
  - Mitigation: Comprehensive integration tests, ensure response format unchanged
- Risk: Progress callback complexity
  - Mitigation: Start simple (function callback), add error handling wrapper
- Risk: `LangFlixPipeline` interface changes needed
  - Mitigation: Minimize changes, use optional `progress_callback` parameter
- **Rollback strategy:** Keep old `process_video_task` as backup until fully tested

**Enhanced Success Criteria:**
Beyond original ticket criteria:
- [ ] API response format unchanged (backward compatible)
- [ ] CLI functionality unchanged (same `LangFlixPipeline.run()` interface)
- [ ] Progress callbacks tested with Redis job updates
- [ ] `pipeline_runner.py` evaluated and either fixed or removed
- [ ] Integration tests verify identical results from API and CLI
- [ ] Documentation updated (`docs/api/README.md`, `docs/core/README.md`)

**Alternative Approaches Considered:**
- Original proposal: Unified `VideoPipelineService` ✅ Selected
- Alternative 1: Keep separate implementations - Rejected (maintains duplication)
- Alternative 2: Use existing `pipeline_runner.py` - Rejected (has bugs, incomplete)
- **Selected approach:** New service wrapping `LangFlixPipeline` - cleanest separation, minimal changes

**Implementation Notes:**
- Start by: Creating `VideoPipelineService` with minimal interface
- Watch out for: Parameter mismatches between API and CLI (check all `LangFlixPipeline.run()` parameters)
- Coordinate with: TICKET-002 team if working in parallel (temp file management)
- Reference: `langflix/main.py:177-757` for `LangFlixPipeline` implementation, `langflix/api/routes/jobs.py:28-477` for current API logic

**Estimated Timeline:** 2-3 days (with testing and documentation)
**Recommended Owner:** Senior engineer familiar with both API and CLI pipelines

## Success Criteria
How do we know this is successfully implemented?
- [ ] `process_video_task` 함수가 150줄 이하로 감소
- [ ] API와 CLI 모두 동일한 파이프라인 서비스를 사용
- [ ] 모든 기존 테스트 통과
- [ ] 코드 중복이 80% 이상 감소 (중복된 로직 제거)
- [ ] 진행 상황 업데이트가 정상 작동
- [ ] 성능 저하 없음 (벤치마크 테스트)
- [ ] 문서 업데이트 완료

