# [TICKET-007] Implement Parallel LLM Request Processing for Faster Expression Analysis

## Priority
- [ ] Critical (System stability, security, data loss risk)
- [x] High (Performance issues, significant tech debt)
- [ ] Medium (Code quality, maintainability improvements)
- [ ] Low (Nice-to-have refactorings)

## Type
- [ ] Refactoring
- [x] Performance Optimization
- [ ] Test Coverage
- [ ] Bug Fix
- [ ] Security Issue
- [ ] Technical Debt
- [ ] Code Duplication

## Impact Assessment
**Business Impact:**
- 현재 순차 처리로 expression 분석이 매우 느림 (각 청크마다 LLM 호출 대기)
- 병렬 처리로 전체 처리 시간을 3-5배 개선 가능
- 더 나은 사용자 경험과 더 빠른 결과 제공

**Technical Impact:**
- 영향받는 모듈: `langflix/main.py`, `langflix/core/parallel_processor.py`, `langflix/core/expression_analyzer.py`
- 예상 변경 파일: 5-7개
- 이미 `ParallelProcessor`가 구현되어 있으나 실제로 사용되지 않음

**Effort Estimate:**
- Medium (1-3 days)

## Problem Description

### Current State
**Location:** `langflix/main.py:391-457`

현재 expression 분석이 완전히 순차적으로 처리됩니다:

```python
def _analyze_expressions(self, max_expressions: int = None, ...):
    """Analyze expressions from subtitle chunks"""
    all_expressions = []
    
    # In test mode, process only the first chunk
    chunks_to_process = [self.chunks[0]] if test_mode and self.chunks else self.chunks
    
    for i, chunk in enumerate(chunks_to_process):  # ❌ 순차 반복
        if max_expressions is not None and len(all_expressions) >= max_expressions:
            break
            
        try:
            # Each call waits for LLM response - slow!
            expressions = analyze_chunk(chunk, language_level, self.language_code, save_llm_output, output_dir)
            if expressions:
                all_expressions.extend(expressions)
```

**문제점:**
- 각 청크마다 LLM API 호출을 기다림
- 10개 청크가 있다면 순차 처리 시간 = 각 청크별 5초 × 10 = 50초
- 병렬 처리 시 3-5초로 단축 가능

### Root Cause Analysis
- `ParallelProcessor`는 이미 구현되어 있음 (`langflix/core/parallel_processor.py`)
- `ExpressionBatchProcessor`도 존재하지만 실제 `LangFlixPipeline`에서 사용되지 않음
- 기존 코드가 단순한 순차 처리 패턴으로 작성되었고 이후 병렬 처리가 통합되지 않음

### Evidence
- `langflix/core/parallel_processor.py:168-229`: `ExpressionBatchProcessor` 구현되어 있음
- `langflix/core/parallel_processor.py:352-372`: `process_expressions_parallel` 함수 존재
- `langflix/main.py:391-457`: 실제로는 순차 반복문 사용
- grep 결과: `ExpressionBatchProcessor`가 코드베이스 어디에서도 실제로 import/사용되지 않음

## Proposed Solution

### Approach
1. `LangFlixPipeline`의 `_analyze_expressions`를 병렬 처리로 변경
2. 기존 `ExpressionBatchProcessor` 활용
3. 진행 상황 콜백 유지
4. 설정에서 병렬 처리 활성화/비활성화 가능하게

### Implementation Details

#### Step 1: 병렬 처리 활성화 설정
`langflix/config/default.yaml`에 추가:

```yaml
# Expression processing configuration
expression:
  llm:
    # Parallel processing configuration
    parallel_processing:
      enabled: true
      max_workers: null  # null = auto-detect based on CPU count
      timeout_per_chunk: 300  # seconds
      batch_size: null  # null = process all chunks at once
    
    # Chunking configuration
    min_expressions_per_chunk: 1
    max_expressions_per_chunk: 3
    max_llm_input_length: 5000
```

#### Step 2: LangFlixPipeline 리팩토링
`langflix/main.py`의 `_analyze_expressions` 메서드 변경:

```python
def _analyze_expressions(self, max_expressions: int = None, language_level: str = None, save_llm_output: bool = False, test_mode: bool = False) -> List[ExpressionAnalysis]:
    """Analyze expressions from subtitle chunks - PARALLEL VERSION"""
    
    # In test mode, process only the first chunk
    chunks_to_process = [self.chunks[0]] if test_mode and self.chunks else self.chunks
    
    # Check if parallel processing is enabled
    from langflix import settings
    parallel_enabled = settings.get_parallel_llm_processing_enabled()
    
    if parallel_enabled and len(chunks_to_process) > 1:
        logger.info(f"Using PARALLEL processing for {len(chunks_to_process)} chunks")
        return self._analyze_expressions_parallel(chunks_to_process, max_expressions, language_level, save_llm_output)
    else:
        logger.info(f"Using SEQUENTIAL processing for {len(chunks_to_process)} chunks")
        return self._analyze_expressions_sequential(chunks_to_process, max_expressions, language_level, save_llm_output, test_mode)

def _analyze_expressions_parallel(
    self, 
    chunks: List[List[Dict[str, Any]]], 
    max_expressions: int = None, 
    language_level: str = None,
    save_llm_output: bool = False
) -> List[ExpressionAnalysis]:
    """Analyze expressions in parallel using ExpressionBatchProcessor"""
    from langflix.core.parallel_processor import get_expression_processor
    from langflix.core.expression_analyzer import analyze_chunk
    from langflix import settings
    from pathlib import Path
    
    # Get parallel processor configuration
    max_workers = settings.get_parallel_llm_max_workers()
    timeout_per_chunk = settings.get_parallel_llm_timeout()
    
    # Get output directory for LLM outputs
    output_dir = None
    if save_llm_output:
        try:
            metadata_paths = self.paths.get('episode', {}).get('metadata', {})
            if metadata_paths and 'llm_outputs' in metadata_paths:
                output_dir = str(metadata_paths['llm_outputs'])
            else:
                episode_dir = self.paths.get('episode', {}).get('episode_dir')
                if episode_dir:
                    output_dir = str(episode_dir / 'llm_outputs')
                    Path(output_dir).mkdir(parents=True, exist_ok=True)
        except (KeyError, AttributeError) as e:
            logger.warning(f"Could not determine LLM output directory: {e}")
            output_dir = None
    
    # Progress callback
    completed_chunks = [0]
    total_chunks = len(chunks)
    
    def progress_callback(completed: int, total: int):
        completed_chunks[0] = completed
        progress_pct = int((completed / total) * 100) if total > 0 else 0
        logger.info(f"Analyzed {completed}/{total} chunks ({progress_pct}%)")
        if self.progress_callback:
            self.progress_callback(30 + (progress_pct * 0.5), f"Analyzing expressions... {completed}/{total} chunks")
    
    # Create ExpressionBatchProcessor with configuration
    processor = ExpressionBatchProcessor(max_workers=max_workers)
    
    # Analyze chunks in parallel
    logger.info(f"Starting parallel analysis of {len(chunks)} chunks with {max_workers} workers")
    start_time = time.time()
    
    # Note: ExpressionBatchProcessor uses analyze_chunk internally
    # We need to pass save_output parameter through
    # Since processor doesn't support this, we'll create a wrapper
    results = []
    for i, chunk in enumerate(chunks):
        if max_expressions is not None and len(results) >= max_expressions:
            break
        
        try:
            expressions = analyze_chunk(
                chunk, 
                language_level, 
                self.language_code, 
                save_output=save_llm_output,
                output_dir=output_dir
            )
            results.extend(expressions)
        except Exception as e:
            logger.error(f"Error analyzing chunk {i+1}: {e}")
            continue
    
    duration = time.time() - start_time
    logger.info(f"Parallel analysis complete: {len(results)} expressions in {duration:.2f}s")
    
    # Limit to max_expressions
    limited_expressions = results[:max_expressions] if max_expressions else results
    logger.info(f"Total expressions to process: {len(limited_expressions)}")
    
    # Find expression timing for each expression
    logger.info("Finding exact expression timings from subtitles...")
    for expression in limited_expressions:
        try:
            expression_start, expression_end = self.subtitle_processor.find_expression_timing(expression)
            expression.expression_start_time = expression_start
            expression.expression_end_time = expression_end
            logger.info(f"Expression '{expression.expression}' timing: {expression_start} to {expression_end}")
        except Exception as e:
            logger.warning(f"Could not find timing for expression '{expression.expression}': {e}")
    
    return limited_expressions

def _analyze_expressions_sequential(self, ...):
    """Original sequential implementation (kept for fallback)"""
    # Keep existing implementation as-is
    ...
```

실제 병렬 처리를 위해 `ExpressionBatchProcessor`가 `save_output` 파라미터를 지원하도록 수정 필요:

#### Step 3: ExpressionBatchProcessor 업데이트
`langflix/core/parallel_processor.py` 수정:

```python
def analyze_expression_chunks(
    self,
    chunks: List[List[Dict[str, Any]]],
    language_level: str = None,
    language_code: str = "ko",
    save_output: bool = False,
    output_dir: str = None,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> List[List[Any]]:
    """
    Analyze multiple expression chunks in parallel
    
    Args:
        chunks: List of subtitle chunks
        language_level: Target language level
        language_code: Target language code
        save_output: Whether to save LLM outputs
        output_dir: Directory to save LLM outputs
        progress_callback: Progress callback
        
    Returns:
        List of expression analysis results
    """
    from langflix.core.expression_analyzer import analyze_chunk
    
    # Create tasks for each chunk
    tasks = []
    for i, chunk in enumerate(chunks):
        task = ProcessingTask(
            task_id=f"chunk_{i}",
            function=analyze_chunk,
            args=(chunk, language_level, language_code),
            kwargs={"save_output": save_output, "output_dir": output_dir},
            priority=len(chunk)  # Prioritize larger chunks
        )
        tasks.append(task)
    
    # Process in parallel
    results = self.processor.process_batch(tasks, progress_callback)
    
    # Extract successful results
    successful_results = []
    for result in results:
        if result.success:
            successful_results.append(result.result)
        else:
            logger.error(f"Chunk analysis failed: {result.error}")
            successful_results.append([])  # Empty list for failed chunks
    
    return successful_results
```

#### Step 4: Settings 접근자 추가
`langflix/settings.py`에 추가:

```python
def get_parallel_llm_processing_enabled() -> bool:
    """Check if parallel LLM processing is enabled"""
    expression_config = get_expression_config()
    parallel_config = expression_config.get('llm', {}).get('parallel_processing', {})
    return parallel_config.get('enabled', True)

def get_parallel_llm_max_workers() -> Optional[int]:
    """Get max workers for parallel LLM processing"""
    expression_config = get_expression_config()
    parallel_config = expression_config.get('llm', {}).get('parallel_processing', {})
    max_workers = parallel_config.get('max_workers')
    if max_workers is None:
        # Auto-detect based on CPU count
        import multiprocessing
        return multiprocessing.cpu_count()
    return max_workers

def get_parallel_llm_timeout() -> float:
    """Get timeout per chunk for parallel processing"""
    expression_config = get_expression_config()
    parallel_config = expression_config.get('llm', {}).get('parallel_processing', {})
    return parallel_config.get('timeout_per_chunk', 300)
```

#### Step 5: API Routes에도 병렬 처리 적용
`langflix/api/routes/jobs.py`의 `process_video_task`에서도 병렬 처리 사용

### Alternative Approaches Considered

**Option 1: ThreadPoolExecutor 직접 사용**
- 장점: 제어하기 쉬움
- 단점: 기존 ParallelProcessor 재사용 못함, 코드 중복
- 선택하지 않은 이유: 기존 인프라 활용 불가

**Option 2: asyncio와 async/await 사용**
- 장점: 실제 비동기 처리
- 단점: 모든 코드를 async로 변경 필요, Gemini API가 sync
- 선택하지 않은 이유: 대규모 리팩토링 필요

**Option 3: 선택된 접근 (ThreadPoolExecutor via ParallelProcessor)**
- 장점: 기존 코드 재사용, 최소 변경, I/O bound 작업에 적합
- 단점: GIL로 인한 성능 제한 (LLM 호출은 I/O bound라 영향 적음)
- 선택 이유: 최소 변경, 이미 구현된 인프라 활용

### Benefits
- **성능 향상**: 3-5배 빠른 처리 시간
- **사용자 경험**: 더 빠른 결과 제공
- **리소스 활용**: CPU 코어 효율적 사용
- **기존 코드 재사용**: ParallelProcessor 활용
- **설정 가능**: 필요 시 순차 처리로 폴백

### Risks & Considerations
- **API Rate Limits**: 병렬 요청으로 인한 rate limit 초과 가능성
- **메모리 사용량**: 여러 청크 동시 처리로 메모리 증가
- **에러 처리**: 일부 청크 실패 시 전체 처리 영향 최소화 필요
- **GIL 영향**: Python GIL이지만 LLM 호출은 I/O bound라 영향 적음

## Testing Strategy

### Unit Tests
- `_analyze_expressions_parallel`: 병렬 처리 검증
- `ExpressionBatchProcessor`: 여러 청크 동시 처리 검증
- 에러 발생 시 일부 청크만 실패하는지 검증

### Integration Tests
- 실제 LLM API 호출을 통한 병렬 처리 검증
- 진행 상황 콜백이 올바르게 작동하는지 검증

### Performance Tests
- 병렬 vs 순차 처리 시간 비교 벤치마크
- 다양한 청크 수에 대한 성능 측정
- 메모리 사용량 측정

## Files Affected

**수정:**
- `langflix/main.py` - `_analyze_expressions` 메서드 병렬 처리 추가
- `langflix/core/parallel_processor.py` - `ExpressionBatchProcessor`에 `save_output` 지원 추가
- `langflix/settings.py` - 병렬 처리 설정 접근자 추가
- `langflix/config/default.yaml` - 병렬 처리 설정 추가
- `langflix/api/routes/jobs.py` - 병렬 처리 사용 (선택적)

**테스트 추가:**
- `tests/unit/test_parallel_expression_analysis.py` - 병렬 처리 단위 테스트
- `tests/integration/test_parallel_llm_integration.py` - 통합 테스트
- `tests/performance/test_parallel_vs_sequential.py` - 성능 벤치마크

## Dependencies
- Depends on: None
- Blocks: TICKET-002 (multiple expressions per context)
- Related to: None

## References
- Related code: `langflix/core/parallel_processor.py:168-229`
- Design patterns: ThreadPool Pattern, Batch Processing

## Architect Review Questions
**For the architect to consider:**
1. Gemini API rate limit이 병렬 처리 시 문제가 될 수 있는가?
2. 최적의 worker 수는? (Auto-detect vs 고정값)
3. 메모리 사용량 증가가 문제가 되는가?
4. failover 전략이 필요한가?

---
## 🏛️ Architect Review & Approval

**Reviewed by:** Architect Agent
**Review Date:** 2025-01-30
**Decision:** ✅ APPROVED (with architectural enhancements)

**Strategic Rationale:**
- Leverages existing investment - `ParallelProcessor` and `ExpressionBatchProcessor` are fully implemented but unused
- Significant performance improvement - 3-5x faster expression analysis
- Aligns with ADR-016 (Parallel LLM Processing)
- Low risk - existing infrastructure tested, can fallback to sequential
- High ROI - minimal code changes for major performance gain

**Implementation Phase:** Phase 1 - Sprint 1 (Weeks 1-2)
**Sequence Order:** #1 in implementation queue

**Architectural Guidance:**

**Critical Implementation Issue Found:**
The proposed Step 2 implementation (lines 179-195) still uses a **sequential for loop** - this defeats the purpose of parallel processing! Must use `ExpressionBatchProcessor.analyze_expression_chunks()` directly.

**Corrected Implementation Approach:**
1. **Use ExpressionBatchProcessor directly** - Don't wrap it in a sequential loop
2. **Extend ExpressionBatchProcessor** - Add `save_output` and `output_dir` parameters to `analyze_expression_chunks()`
3. **Rate Limiting Strategy:**
   - Default: `max_workers = min(cpu_count(), 5)` for Gemini API
   - Configuration: Allow override but warn if > 10
   - Circuit breaker: Track 429 errors, reduce workers if rate limited
4. **Error Handling:**
   - Partial failure tolerance - continue with successful chunks
   - Log failed chunks but don't fail entire batch
   - Retry failed chunks in sequential mode as fallback
5. **Progress Callback:**
   - Update progress as chunks complete (not sequentially)
   - Report failed chunks separately
6. **Memory Management:**
   - Consider chunking large batches (> 20 chunks)
   - Stream results if possible (don't hold all in memory)

**Dependencies:**
- **Must complete first:** None
- **Should complete first:** None
- **Blocks:** TICKET-002 (multiple expressions - parallel processing helps with larger batches)
- **Related work:** ADR-016 already documents this approach

**Risk Mitigation:**
- Risk: Gemini API rate limits (429 errors)
  - Mitigation: Conservative default (max 5 workers), exponential backoff, circuit breaker pattern
  - Monitor: Track rate limit errors, auto-adjust workers
- Risk: Memory usage with large batches
  - Mitigation: Batch chunking (> 20 chunks = process in sub-batches)
  - Monitor: Track memory usage, add limits if needed
- Risk: Partial failures affecting user experience
  - Mitigation: Graceful degradation - continue with successful chunks, log failures
  - Fallback: Retry failed chunks sequentially
- **Rollback strategy:** Simple - set `parallel_processing.enabled: false` in config to revert to sequential

**Enhanced Success Criteria:**
Beyond original ticket criteria:
- [ ] Actually uses `ExpressionBatchProcessor` (not sequential loop)
- [ ] `save_output` parameter supported in `ExpressionBatchProcessor`
- [ ] Rate limit handling with circuit breaker
- [ ] Performance benchmark: 3x+ improvement for 10+ chunks
- [ ] Memory usage acceptable (< 500MB increase for 20 chunks)
- [ ] Partial failure handling tested (some chunks fail)
- [ ] Configuration allows tuning worker count
- [ ] Integration tests verify parallel vs sequential produce same results

**Alternative Approaches Considered:**
- Original proposal: Wrapper function (but has sequential loop bug) - Rejected (doesn't actually parallelize)
- Alternative 1: Use `process_expressions_parallel` convenience function - Considered, but needs extension
- Alternative 2: Direct `ExpressionBatchProcessor` usage - ✅ Selected (cleanest, most direct)
- **Selected approach:** Extend `ExpressionBatchProcessor` to support `save_output`, use directly in pipeline

**Implementation Notes:**
- Start by: Extending `ExpressionBatchProcessor.analyze_expression_chunks()` to accept `save_output` and `output_dir`
- Watch out for: Sequential loops that defeat parallelization (CRITICAL: Step 2 implementation bug)
- Coordinate with: None
- Reference: `langflix/core/parallel_processor.py:184-229` for current implementation, `ADR-016` for design decisions

**Critical Fix Required:**
The Step 2 implementation code (lines 179-195) is **incorrect** - it still processes chunks sequentially! Must be:
```python
# CORRECT: Use ExpressionBatchProcessor directly
processor = ExpressionBatchProcessor(max_workers=max_workers)
all_results = processor.analyze_expression_chunks(
    chunks_to_process,
    language_level=language_level,
    language_code=self.language_code,
    save_output=save_llm_output,
    output_dir=output_dir,
    progress_callback=progress_callback
)

# Flatten results
all_expressions = []
for chunk_results in all_results:
    all_expressions.extend(chunk_results)
```

**Estimated Timeline:** 2-3 days (with testing and rate limit handling)
**Recommended Owner:** Senior engineer (requires understanding of concurrent processing and API limits)

## Success Criteria
How do we know this is successfully implemented?
- [ ] 병렬 처리 시 순차 처리 대비 3배 이상 성능 향상
- [ ] 모든 기존 테스트 통과
- [ ] 병렬/순차 처리 모두 지원
- [ ] 진행 상황 콜백 정상 작동
- [ ] 설정으로 활성화/비활성화 가능
- [ ] 에러 발생 시 graceful degradation
- [ ] 메모리 사용량이 허용 범위 내

