# TICKET-090: Refactor video_editor.py (2916 Lines)

## Summary
`video_editor.py` has grown to 2916 lines (151KB), making it difficult to maintain, test, and understand. The file violates single responsibility principle with multiple concerns mixed together.

## Problem

### Current State
- **File size**: 2916 lines, 151KB
- **Class methods**: 35+ methods
- **Responsibilities mixed**:
  - Long-form video creation
  - Short-form video creation
  - Educational slide creation
  - TTS timeline generation
  - Audio extraction
  - FFmpeg operations
  - Subtitle handling
  - Transition video creation
  - Video batching

### Issues
1. **Hard to test**: Large methods with many dependencies
2. **Code duplication**: Similar logic repeated across methods
3. **Difficult to modify**: Changes risk breaking unrelated features
4. **Poor separation of concerns**: Video editing, audio processing, and slide generation all mixed

## Implementation Plan

### Phase 1: Extract Slide Generator (2-3 hours)
Extract slide-related methods into `langflix/core/slide_generator.py`:
- `_create_educational_slide()` (570 lines!)
- `_generate_tts_timeline()`
- `_create_timeline_from_tts()`
- `_create_context_audio_timeline_direct()`
- `_extract_original_audio_timeline()`
- `_create_silence_fallback()`

### Phase 2: Extract Video Batcher (1-2 hours)
Extract batching logic into `langflix/core/video_batcher.py`:
- `create_batched_short_videos()`
- `_create_video_batch()`
- `combine_videos()`

### Phase 3: Extract Transition Generator (1 hour)
Extract into `langflix/core/transition_generator.py`:
- `_create_transition_video()`

### Phase 4: Extract Helper Methods (1-2 hours)
Move utility methods to appropriate modules:
- `_time_to_seconds()` → `langflix/utils/time_utils.py`
- `_seconds_to_time()` → `langflix/utils/time_utils.py`
- `_get_font_option()` → `langflix/media/font_utils.py`
- `_get_video_output_args()` → `langflix/media/ffmpeg_utils.py`

### Proposed Structure After Refactoring
```
langflix/core/
├── video_editor.py          # ~500 lines - orchestration only
├── slide_generator.py       # ~600 lines - slide creation
├── video_batcher.py         # ~150 lines - video batching
├── transition_generator.py  # ~120 lines - transitions

langflix/utils/
├── time_utils.py            # Time conversion utilities
```

## Files to Create/Modify
1. **Create**: `langflix/core/slide_generator.py`
2. **Create**: `langflix/core/video_batcher.py`
3. **Create**: `langflix/core/transition_generator.py`
4. **Modify**: `langflix/core/video_editor.py` - reduce to orchestration
5. **Modify**: `langflix/utils/time_utils.py` - add time conversion functions

## Verification Plan
1. Run full test suite after each phase
2. Verify video output quality is identical
3. Run integration test with full episode
4. Check for any import errors or missing dependencies

## Acceptance Criteria
- [ ] `video_editor.py` reduced to < 600 lines
- [ ] All extracted modules have clear single responsibility
- [ ] No functionality regression
- [ ] All tests pass
- [ ] Code is easier to understand and modify

## Priority
**Medium** - Technical debt reduction, improves maintainability

## Estimated Effort
8-12 hours (phased over multiple PRs)

## Dependencies
None - can be done independently

## Risk Assessment
- **Low risk**: Each phase can be done incrementally
- **Rollback**: Easy to revert individual PRs
