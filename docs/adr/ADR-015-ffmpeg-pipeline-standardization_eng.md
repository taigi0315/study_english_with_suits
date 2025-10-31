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

**Phase 3 (Short-form Simplification - TICKET-001, 2025-01-30):**
- **Problem**: Short-form had overly complex logic with unnecessary audio extraction/processing (~180 lines) causing A-V sync issues.
- **Root cause**: Short-form was extracting audio separately, processing it, and calculating durations from audio instead of video.
- **Solution**: Completely simplified short-form to match long-form pattern exactly:
  - Removed unnecessary audio extraction/processing logic
  - Removed duplicate expression processing block
  - Changed duration calculation from audio-based to video-based (same as long-form)
  - Simplified flow: context_with_subtitles → expression clip → repeat → concat → vstack → final gain
  - Short-form now follows exact same pattern as long-form (only difference: vstack vs hstack)
- **Result**: Fixed 0.5s A-V sync delay issue, code is now much simpler and maintainable.
- **Key insight**: Short-form and long-form should use identical logic - only difference is layout (vertical vs horizontal).

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
