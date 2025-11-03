# [TICKET-017] Fix ParallelProcessor Event Loop Error in ThreadPoolExecutor

## Priority
- [ ] Critical (System stability, security, data loss risk)
- [x] High (Performance issues, significant tech debt)
- [ ] Medium (Code quality, maintainability improvements)
- [ ] Low (Nice-to-have refactorings)

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
- **User Experience**: Batch video processing fails completely with "no running event loop" errors
- **Data Loss**: Videos fail to process, resulting in "No expressions found" errors even when expressions are actually extracted
- **Reliability**: Critical feature (parallel expression analysis) is broken, causing 100% failure rate for batch operations

**Technical Impact:**
- **Affected Modules**: 
  - `langflix/core/parallel_processor.py` - Core parallel processing infrastructure
  - `langflix/main.py` - Expression analysis workflow
  - `langflix/core/expression_analyzer.py` - Expression extraction
- **Files to Change**: ~2-3 files
- **Breaking Changes**: None (fix only, maintains API)

**Effort Estimate:**
- Small (< 1 day)
  - Root cause is clear
  - Fix is straightforward
  - Testing: verify parallel processing works correctly

## Problem Description

### Current State

**Location:** `langflix/core/parallel_processor.py:143-157`

The `ParallelProcessor._execute_task` method incorrectly uses `asyncio.wait_for` and `asyncio.create_task` inside a `ThreadPoolExecutor` context. When `ThreadPoolExecutor.submit()` executes code in a worker thread, that thread does **not** have a running event loop. Attempting to use `asyncio.wait_for` or `asyncio.create_task` in such a context raises `RuntimeError: no running event loop`.

**Current problematic code:**
```python
def _execute_task(
    self,
    function: Callable,
    args: Tuple,
    kwargs: Dict[str, Any],
    timeout: Optional[float]
) -> Any:
    """Execute a single task with timeout"""
    if timeout:
        return asyncio.wait_for(  # ❌ ERROR: No event loop in thread!
            asyncio.create_task(self._run_task(function, args, kwargs)),  # ❌ ERROR: No event loop in thread!
            timeout=timeout
        )
    else:
        return self._run_task(function, args, kwargs)
```

**Error from terminal logs:**
```
21:37:10 | ERROR    | Task chunk_9 failed: no running event loop
21:37:10 | ERROR    | Task chunk_15 failed: no running event loop
21:37:10 | ERROR    | Task chunk_16 failed: no running event loop
21:37:43 | ERROR    | Task chunk_1 failed: no running event loop
21:37:43 | ERROR    | Task chunk_2 failed: no running event loop
```

### Root Cause Analysis

1. **Architecture Mismatch**: `ParallelProcessor` uses `ThreadPoolExecutor` (or `ProcessPoolExecutor`) for parallel execution, which runs code in separate threads/processes
2. **Async/Sync Confusion**: The code attempts to use `asyncio` primitives (`wait_for`, `create_task`) in a synchronous threading context
3. **Missing Event Loop**: Worker threads created by `ThreadPoolExecutor` do not have an event loop by default - they're purely synchronous threads
4. **Timeout Implementation Error**: The timeout logic assumes async context, but we're in sync thread context

**Why this problem exists:**
- The code was likely ported from an async implementation or mixed async/sync design patterns
- `asyncio.wait_for` is an async function that requires an event loop
- `ThreadPoolExecutor` is for synchronous code, not async code

### Evidence

**Terminal Log Evidence:**
```
21:37:43 | INFO     | ✅ Expression 1 validated: 'behind my back' (14 dialogues/translations)
21:37:43 | INFO     | ✅ Expression 2 validated: 'hedge your bets' (14 dialogues/translations)
21:37:43 | INFO     | ✅ Expression 3 validated: 'stick his neck out' (12 dialogues/translations)
21:37:43 | INFO     | Successfully parsed 3 expressions from 3 total
21:37:10 | ERROR    | Task chunk_15 failed: no running event loop
21:37:43 | ERROR    | Chunk analysis failed: no running event loop
21:37:43 | INFO     | Parallel analysis complete in 171.26s
21:37:43 | INFO     | Total expressions found: 0  # ❌ Should be > 0!
21:37:43 | ERROR    | ❌ No expressions found after analysis
```

**Observation:**
- Individual chunks **do** find expressions successfully (see validation logs)
- But chunks fail with "no running event loop" error
- Failed chunks return empty lists in `ExpressionBatchProcessor.analyze_expression_chunks` (line 231)
- This causes `all_expressions` to remain empty, leading to "No expressions found"

**Code Evidence:**
```python:langflix/core/parallel_processor.py
230:231:langflix/core/parallel_processor.py
                logger.error(f"Chunk analysis failed: {result.error}")
                successful_results.append([])  # Empty list for failed chunks
```

When chunks fail, empty lists are appended, diluting successful results.

## Proposed Solution

### Approach

Replace async timeout logic with synchronous timeout using `concurrent.futures.ThreadPoolExecutor` with timeout support or `signal.alarm` (Unix) / threading-based timeout (cross-platform).

**Strategy:**
1. Remove `asyncio.wait_for` and `asyncio.create_task` from `_execute_task`
2. Use synchronous timeout mechanism suitable for ThreadPoolExecutor
3. Keep the same timeout functionality but implement it correctly for threading context

### Implementation Details

**Option 1: Use `concurrent.futures.Future.result(timeout)` (Recommended)**

```python
def _execute_task(
    self,
    function: Callable,
    args: Tuple,
    kwargs: Dict[str, Any],
    timeout: Optional[float]
) -> Any:
    """Execute a single task with timeout"""
    if timeout:
        # Submit task to a separate thread executor for timeout
        with ThreadPoolExecutor(max_workers=1) as timeout_executor:
            future = timeout_executor.submit(
                self._run_task,
                function,
                args,
                kwargs
            )
            try:
                return future.result(timeout=timeout)
            except TimeoutError:
                logger.error(f"Task timed out after {timeout}s")
                raise
    else:
        return self._run_task(function, args, kwargs)
```

**Option 2: Use `threading.Timer` for timeout (Simpler, but less precise)**

```python
def _execute_task(
    self,
    function: Callable,
    args: Tuple,
    kwargs: Dict[str, Any],
    timeout: Optional[float]
) -> Any:
    """Execute a single task with timeout"""
    if timeout:
        result_container = [None]
        exception_container = [None]
        
        def run_with_timeout():
            try:
                result_container[0] = self._run_task(function, args, kwargs)
            except Exception as e:
                exception_container[0] = e
        
        thread = threading.Thread(target=run_with_timeout)
        thread.daemon = True
        thread.start()
        thread.join(timeout=timeout)
        
        if thread.is_alive():
            logger.error(f"Task timed out after {timeout}s")
            raise TimeoutError(f"Task execution exceeded {timeout}s timeout")
        
        if exception_container[0]:
            raise exception_container[0]
        
        return result_container[0]
    else:
        return self._run_task(function, args, kwargs)
```

**Recommended: Option 1** - Uses standard library `Future.result(timeout)` which is cleaner and more reliable.

### Alternative Approaches Considered

**Option A: Make tasks async and use async executor**
- **Pros**: Could use native async/await timeout
- **Cons**: Requires rewriting all callers, breaking change, complex migration
- **Decision**: Rejected - too invasive

**Option B: Remove timeout feature**
- **Pros**: Simplest fix
- **Cons**: Loses timeout protection, tasks could hang indefinitely
- **Decision**: Rejected - timeout is important for reliability

**Option C: Use ProcessPoolExecutor with signal-based timeout**
- **Pros**: Process isolation
- **Cons**: More complex, slower startup, not needed for I/O-bound expression analysis
- **Decision**: Rejected - overkill for current use case

### Benefits

- **Fixes Critical Bug**: Parallel processing will work correctly
- **Maintains Timeout**: Task timeout functionality preserved
- **No Breaking Changes**: API remains the same
- **Better Reliability**: Batch operations will complete successfully
- **No Performance Impact**: Uses efficient standard library primitives

### Risks & Considerations

- **Timeout Precision**: `Future.result(timeout)` may not be as precise as `asyncio.wait_for`, but sufficient for our use case (expression analysis tasks typically take 30-60s)
- **Thread Overhead**: Creating additional executor for timeout adds minimal overhead
- **Testing**: Must verify timeout still works correctly after fix
- **Backward Compatibility**: No API changes, fully backward compatible

## Testing Strategy

### Unit Tests
1. Test `_execute_task` with timeout - verify timeout works correctly
2. Test `_execute_task` without timeout - verify normal execution
3. Test `_execute_task` with long-running function - verify timeout triggers
4. Test `ParallelProcessor.process_batch` - verify parallel execution succeeds
5. Test `ExpressionBatchProcessor.analyze_expression_chunks` - verify results are aggregated correctly

### Integration Tests
1. End-to-end batch expression analysis - verify expressions are found and aggregated
2. Test with multiple chunks - verify all chunks process correctly
3. Test with timeout scenarios - verify timeout works without breaking batch processing

### Manual Testing
1. Run batch video processing with multiple videos
2. Verify expressions are extracted successfully
3. Check logs for absence of "no running event loop" errors
4. Verify final expression count matches individual chunk counts

## Files Affected

1. **`langflix/core/parallel_processor.py`**
   - Fix `_execute_task` method to use synchronous timeout
   - Remove `asyncio` imports/usage from timeout logic
   - Add proper timeout handling for ThreadPoolExecutor context

2. **`tests/unit/test_parallel_processor.py`** (create if doesn't exist)
   - Add unit tests for `_execute_task` with/without timeout
   - Add tests for timeout behavior
   - Add tests for batch processing

## Dependencies

- **None** - This is a standalone bug fix
- **Related to**: TICKET-014 (batch processing queue) - this bug affects batch processing reliability

## References

- [Python ThreadPoolExecutor documentation](https://docs.python.org/3/library/concurrent.futures.html#threadpoolexecutor)
- [Future.result(timeout) documentation](https://docs.python.org/3/library/concurrent.futures.html#concurrent.futures.Future.result)
- Related: TICKET-014 (batch processing implementation)

## Architect Review Questions

**For the architect to consider:**

1. **Timeout Implementation**: Should we keep timeout functionality or simplify by removing it? The current timeout is 300s (5 min) for expression analysis.

2. **Error Handling**: When chunks fail due to timeout, should we:
   - Retry failed chunks automatically?
   - Fail the entire batch?
   - Continue with successful chunks (current behavior)?

3. **Logging**: Should we add more detailed logging around timeout scenarios to help diagnose issues?

4. **Performance**: Are there any performance concerns with the proposed timeout implementation?

## Success Criteria

How do we know this is successfully implemented?
- [ ] All parallel processing tasks complete without "no running event loop" errors
- [ ] Expressions are successfully aggregated from all chunks
- [ ] Batch video processing completes successfully
- [ ] Timeout functionality works correctly for long-running tasks
- [ ] Unit tests cover timeout scenarios
- [ ] Integration tests verify end-to-end batch processing
- [ ] Manual testing confirms batch operations work in production
- [ ] No regressions in single-video processing

