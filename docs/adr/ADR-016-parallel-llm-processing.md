# ADR-016: Parallel LLM Processing for Expression Analysis

**Date:** 2025-01-30  
**Status:** Proposed  
**Deciders:** Development Team  
**Related ADRs:** ADR-014 (Enhanced Subtitle Processing & LLM Integration)

## Context

현재 LangFlix의 expression 분석은 순차적으로 처리됩니다. 각 subtitle chunk마다 LLM API 호출을 기다리면서 전체 처리 시간이 매우 길어집니다.

### Problem

- **현재**: 10개 청크 × 5초/청크 = 50초 소요
- **목표**: 병렬 처리로 3-5초로 단축
- **기존 코드**: `ParallelProcessor`와 `ExpressionBatchProcessor`가 이미 구현되어 있으나 실제 사용되지 않음

### Current State

```
Chunk 1 (5s) → Chunk 2 (5s) → Chunk 3 (5s) → ... → Chunk 10 (5s)
Total: 50s
```

## Decision

병렬 LLM 처리를 활성화하여 성능을 향상시킵니다.

### Architecture

```
Chunk 1 ┐
Chunk 2 ├→ ParallelProcessor (ThreadPool) → Aggregate Results
Chunk 3 ┘
...
Chunk 10 ┘

Expected: 5s (single API call duration)
```

### Implementation

1. **기존 인프라 활용**: `ExpressionBatchProcessor` 통합
2. **ThreadPoolExecutor**: I/O-bound LLM 호출에 적합
3. **설정 가능**: 순차/병렬 전환 가능
4. **진행 상황**: 콜백 유지

### Configuration

```yaml
expression:
  llm:
    parallel_processing:
      enabled: true
      max_workers: null  # auto-detect
      timeout_per_chunk: 300
```

## Consequences

### Benefits
- **3-5배 빠른 처리 시간**
- **CPU 코어 활용 향상**
- **사용자 대기 시간 감소**

### Trade-offs
- **API Rate Limits**: 동시 요청 증가
- **메모리**: 여러 청크 동시 처리
- **복잡도**: 병렬 처리 로직 추가

### Risks & Mitigations

**Risk**: Gemini API rate limit 초과  
**Mitigation**: 설정으로 worker 수 제한

**Risk**: 메모리 사용량 증가  
**Mitigation**: 청크 크기 제한

**Risk**: 일부 청크 실패  
**Mitigation**: graceful degradation, 로깅

## Alternatives Considered

**Option 1**: 순차 처리 유지  
- 장점: 단순
- 단점: 느림

**Option 2**: asyncio 사용  
- 장점: 진짜 비동기
- 단점: Gemini가 sync API

**Option 3**: ThreadPoolExecutor  
- 장점: I/O bound에 적합, 기존 인프라 활용
- 선택

## Success Criteria

- 병렬 처리 시 3배 이상 속도 향상
- 모든 테스트 통과
- 순차/병렬 선택 가능
- 에러가 있어도 일부는 완료

## References

- TICKET-001: Parallel LLM Processing
- `langflix/core/parallel_processor.py:168-229`
- `langflix/main.py:391-457` (현재 순차 처리)


