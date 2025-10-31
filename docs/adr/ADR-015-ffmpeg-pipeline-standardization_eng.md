# ADR-015: FFmpeg Pipeline Standardization for Audio Stability and Source Fidelity

## Status
Accepted

## Context
- Intermittent audio loss occurred after concat/stack steps in the pipeline.
- Expression repeating segments sometimes had no audio after filter-based concatenation.
- Requirement: Keep original video format (codec, resolution) when possible; preserve audio without mid-pipeline modifications.

## Decision
**Phase 1 (Initial):**
- Add centralized FFmpeg utilities ensuring explicit stream mapping and audio normalization.
- Stream copy video when no filters are applied; re-encode only when filters are required.
- Use filter-concat with v=1,a=1 and explicit mapping when inputs differ.
- Normalize audio to ac=2, ar=48000 at concat/stack boundaries.
- Remove hard-coded scaling (720p/1080p). Preserve original dimensions; compute scales dynamically.

**Phase 2 (Audio Drop Fix - TICKET-001):**
- **Demuxer-first approach**: Replace filter-based repetition with concat demuxer (`repeat_av_demuxer`).
- **Standardized layouts**: 
  - Long-form: hstack (left=AV, right=slide), slide visible full time
  - Short-form: vstack (top=AV, bottom=slide), slide visible full time
- **Separate final gain pass**: Apply audio volume boost (+25%) as a separate final step, not inside filter_complex.
- **No mid-pipeline audio transforms**: Keep audio untouched until final gain application.
- **Robust fallback**: Filter concat falls back to demuxer concat on failure.
- **Verification**: Add ffprobe-based checks in `tools/verify_media_pipeline.py` to ensure audio presence.

**Phase 3 (User Feedback - Long-form Layout & Short-form Audio, 2025-01-30):**
- **Issue 1: Long-form missing slide on right side AND missing expression repeat**
  - Problem: Long-form videos used concat instead of hstack, showing context and slide sequentially
  - Solution: Updated `create_educational_sequence()` to use `hstack_keep_height()` for side-by-side layout
  - Critical fix: Added expression repetition - context + expression repeat on left, slide on right
  - Added duration matching - slide extended to match context+expression duration for proper hstack
  - Result: Long-form now shows context → expression repeat on left, slide on right (WITH AUDIO ✅)

- **Issue 2: Short-form audio in expression repeat**
  - Root cause #1: Short-form was regenerating `temp_expr_repeated_xxx` instead of reusing long-form's output
  - Root cause #2: Short-form was using separate `tts_audio_path` instead of concatenated video audio
  - Root cause #3: Short-form was extracting/boosting audio unnecessarily
  - Solution: Use `vstack_keep_width()` output directly - it already preserves audio from concatenated_video_path
  - No need to extract, boost, or remux audio - just copy stacked output to final file
  - Result: Short-form now reuses long-form's expression repeat file AND uses vstack output as-is

**Phase 4 (A-V Sync & Consistency Issues, 2025-01-30 Evening):**
- **Issue 3: Short-form missing first expression**
  - Root cause: Expression name sanitization mismatch between `jobs.py` and `video_editor.py`
  - Solution: Updated `jobs.py` to use exact same sanitization regex as `video_editor.py`
  - Result: All expressions now properly matched and included in short-form videos ✅

- **Issue 4: Short-form A-V sync lag between segments**
  - Root cause: Short-form used `concat_filter_with_explicit_map` which re-encodes video streams
  - Re-encoding changes timestamps, causing A-V desync lag and video speeding up/freezing
  - Solution: Replace filter concat with direct `concat_demuxer_if_uniform` for short-form
  - Remove transition logic entirely (was causing A-V sync issues)
  - Use copy mode (no re-encode) to preserve timestamps
  - Result: No more A-V sync lag, smooth transitions between segments ✅

- **Issue 5 & 6: context_with_subtitles reuse to ensure consistency**
  - Root cause: Short-form was calling `_add_subtitles_to_context` which tried to recreate files, causing conflicts
  - Also short-form used original `context_video_path` while long-form used `context_with_subtitles` (different encoding params)
  - Solution: Updated `_add_subtitles_to_context` to reuse existing files
  - Updated `create_short_format_video` to use `context_with_subtitles` for ALL subsequent operations
  - Result: No conflicts, both long-form and short-form use identical source videos ✅

**Phase 5 (Short-form Logic Simplification, 2025-01-30):**
- **Problem**: Short-form had overly complex logic with unnecessary audio extraction/processing (~180 lines) causing A-V sync issues.
- **Root cause**: Short-form was extracting audio separately, processing it, and calculating durations from audio instead of video.
- **Solution**: Completely simplified short-form to match long-form pattern exactly:
  - Removed unnecessary audio extraction/processing logic (~180 lines removed)
  - Removed duplicate expression processing block
  - Changed duration calculation from audio-based to video-based (same as long-form)
  - Simplified flow: context_with_subtitles → expression clip → repeat → concat → vstack → final gain
  - Short-form now follows exact same pattern as long-form (only difference: vstack vs hstack)
- **Result**: Fixed 0.5s A-V sync delay issue, code is now much simpler and maintainable.
- **Key insight**: Short-form and long-form should use identical logic - only difference is layout (vertical vs horizontal).
- **Commit**: `3df2207` - refactor: simplify short-form video logic to match long-form pattern

## Consequences
**Positive:**
- Audio drops are mitigated via explicit mapping, demuxer-first approach, and robust fallbacks.
- More reliable expression repetition without audio loss.
- Clear separation of concerns (AV build → layout → final gain).
- Code is more modular and maintainable: `media/ffmpeg_utils.py`, `audio/timeline.py`, `subtitles/overlay.py`, `slides/generator.py`.

**Trade-offs:**
- Minor extra CPU cost when re-encoding is required by filters.
- 2-pass finalization (video layout + audio gain) adds IO but improves reliability.
- Demuxer concat requires uniform parameters; falls back to filter concat otherwise.

## Implementation Details
### Key Functions
- `repeat_av_demuxer()`: Repeat AV segments using concat demuxer for maximum reliability.
- `concat_demuxer_if_uniform()`: Demuxer-based concatenation with parameter probing.
- `hstack_keep_height()`: Horizontal stacking for long-form layout.
- `vstack_keep_width()`: Vertical stacking for short-form layout.
- Enhanced `concat_filter_with_explicit_map()`: Automatic fallback to demuxer on filter failure.

### Verification
Run `python tools/verify_media_pipeline.py` to verify:
1. Demuxer-based AV repetition preserves audio
2. Concatenation maintains audio
3. Stacking preserves audio
4. Layouts match spec (hstack/vstack)
5. Audio parameters are valid

## References
- `langflix/media/ffmpeg_utils.py` - Centralized FFmpeg utilities
- `langflix/core/video_editor.py` - Video editing pipeline using new utilities
- `tools/verify_media_pipeline.py` - Pipeline verification script
- `tests/integration/test_media_pipeline_audio.py` - Integration tests
- `docs/TROUBLESHOOTING_GUIDE.md`
