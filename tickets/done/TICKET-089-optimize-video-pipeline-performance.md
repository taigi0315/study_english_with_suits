# TICKET-089: Optimize Video Creation Pipeline Performance

## Summary
Video creation is significantly slower when processing full episodes compared to test mode. Test mode creates 1 video in ~20 seconds, but full episodes take hours to create 20-30 videos.

## Problem

### Current Behavior
- **Test mode**: 1 video ≈ 20 seconds
- **Full episode**: 20-30 videos ≈ hours (expected: ~10-15 minutes)

### Expected Behavior
- Linear scaling: 30 videos × 20 seconds = 10 minutes total
- Current: 30 videos takes 2-4 hours (10-20x slower than expected)

## Investigation Areas

### 1. FFmpeg Encoding Bottlenecks
- Each video is encoded multiple times (context, expression, slide, combined)
- No parallel encoding
- Using `preset=medium` instead of `preset=fast`

### 2. Sequential Processing
- Videos are created one-by-one sequentially
- No batch processing optimization
- No parallel video creation

### 3. Redundant Operations
- Same video slices may be extracted multiple times
- Transition videos recreated for each expression
- No caching of common assets

### 4. I/O Bottlenecks
- Large intermediate files written to disk
- Re-reading same source video multiple times
- No memory-mapped file operations

## Implementation Plan

### Phase 1: Profiling (1-2 hours)
Add timing measurements to identify actual bottlenecks:

```python
# Add to video_editor.py
import time
start = time.time()
# ... operation ...
logger.info(f"Operation took {time.time() - start:.2f}s")
```

Key operations to measure:
- Video slice extraction
- Expression clip creation
- Transition video creation
- Slide creation
- Final concatenation
- FFmpeg encoding time

### Phase 2: Quick Wins (2-3 hours)
1. **Use faster FFmpeg preset**: `preset=fast` instead of `medium`
2. **Cache transition videos**: Create once, reuse for all expressions
3. **Parallel video encoding**: Use `concurrent.futures` for independent operations

### Phase 3: Architectural Improvements (4-6 hours)
1. **Batch video slice extraction**: Extract all clips in one FFmpeg call
2. **Parallel expression processing**: Process multiple expressions concurrently
3. **Reduce re-encoding**: Use stream copy where possible

## Files to Modify
1. [`langflix/core/video_editor.py`](file:///Users/changikchoi/Documents/langflix/langflix/core/video_editor.py) - Add profiling, optimize encoding
2. [`langflix/services/video_factory.py`](file:///Users/changikchoi/Documents/langflix/langflix/services/video_factory.py) - Add parallel processing
3. [`langflix/media/ffmpeg_utils.py`](file:///Users/changikchoi/Documents/langflix/langflix/media/ffmpeg_utils.py) - Optimize FFmpeg commands

## Verification Plan
1. Run full episode generation with timing logs
2. Create performance baseline report
3. Apply optimizations and compare
4. Target: 50%+ reduction in processing time

## Acceptance Criteria
- [ ] Processing time for 30 videos < 20 minutes (down from hours)
- [ ] Linear scaling with number of expressions
- [ ] No quality degradation
- [ ] Profiling data available for future optimization

## Priority
**High** - Critical for production usability

## Estimated Effort
8-12 hours (phased implementation)
