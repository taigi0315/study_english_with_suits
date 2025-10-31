# Core Module Documentation

## Overview

The `langflix/core/` module contains the core video editing functionality for LangFlix. This module orchestrates the creation of educational video sequences, including long-form (side-by-side) and short-form (vertical) video layouts.

**Last Updated:** 2025-01-30  
**Related Ticket:** TICKET-001

## Purpose

This module is responsible for:
- Creating educational video sequences with context clips and expression repetitions
- Generating long-form videos with side-by-side layout (hstack)
- Generating short-form videos with vertical layout (vstack)
- Managing subtitle overlays and educational slides
- Coordinating audio/video synchronization throughout the pipeline

## Key Components

### LangFlixPipeline Class

The main pipeline class for processing TV show content into learning materials.

**Location:** `langflix/main.py`

**Progress Callback Support (TICKET-001):**
- Added optional `progress_callback` parameter to `__init__()`
- Callback signature: `(progress: int, message: str) -> None`
- Progress milestones automatically reported at key pipeline steps:
  - 10%: Parsing subtitles
  - 20%: Chunking subtitles
  - 30%: Analyzing expressions
  - 50%: Processing expressions
  - 70%: Creating educational videos
  - 80%: Creating short-format videos
  - 95%: Generating summary
  - 98%: Cleaning up temporary files
  - 100%: Pipeline completed successfully

**Usage:**
```python
def progress_callback(progress: int, message: str):
    print(f"Progress: {progress}% - {message}")

pipeline = LangFlixPipeline(
    subtitle_file="path/to/subtitle.srt",
    video_dir="assets/media",
    output_dir="output",
    language_code="ko",
    progress_callback=progress_callback  # Optional
)
```

### VideoEditor Class

The main class that orchestrates video creation.

**Location:** `langflix/core/video_editor.py`

**Temporary File Management (TICKET-002):**
- Uses `TempFileManager` for all temporary file operations
- Temporary files are automatically cleaned up via context managers
- No manual cleanup required - `TempFileManager` handles it via `atexit` registration
- Individual short video files are automatically cleaned up after batch creation

**Key Methods:**

#### `create_educational_sequence()`
Creates long-form educational video sequence with side-by-side layout:
- **Left side:** Context video → expression repeat (with subtitles)
- **Right side:** Educational slide (background + text + audio)
- **Layout:** Horizontal stack (hstack) using `hstack_keep_height()`
- **Audio:** From AV stream only (no slide audio mixing)

**Workflow:**
1. Create context video with dual-language subtitles
2. Extract expression clip from context video
3. Repeat expression clip using `repeat_av_demuxer()` (demuxer-based for reliability)
4. Concatenate context + expression repeat
5. Create educational slide extended to match left side duration
6. Stack horizontally (hstack) - left=AV, right=slide
7. Apply final audio gain (+25%) as separate pass

**Parameters:**
- `expression`: ExpressionAnalysis object
- `context_video_path`: Path to context video
- `expression_video_path`: Path to expression video
- `expression_index`: Index for voice alternation

**Returns:** Path to created educational video

#### `create_short_format_video()`
Creates short-form educational video sequence with vertical layout:
- **Top:** Concatenated context + expression segments (with subtitles)
- **Bottom:** Educational slide (visible throughout)
- **Layout:** Vertical stack (vstack) using `vstack_keep_width()`
- **Audio:** From concatenated video only (preserved by vstack)

**Workflow (Simplified in TICKET-001 Phase 5):**
1. Generate `context_with_subtitles` (reuses if exists from long-form)
2. Extract expression clip (reuses if exists from long-form)
3. Repeat expression clip (reuses if exists from long-form)
4. Concatenate context + expression segments using `concat_demuxer_if_uniform()` (copy mode)
5. Create educational slide extended to match video duration
6. Stack vertically (vstack) - top=AV, bottom=slide
7. Apply final audio gain (+25%) as separate pass

**Key Improvements (TICKET-001):**
- Removed ~180 lines of unnecessary audio extraction/processing
- Uses same source video as long-form (`context_with_subtitles`)
- Reuses intermediate files from long-form (expression clips, repeated segments)
- Duration calculated from video, not audio
- No separate audio processing - audio stays with video throughout

**Parameters:**
- `expressions`: List of ExpressionAnalysis objects
- `context_video_path`: Path to context video
- `output_filename`: Output filename

**Returns:** Path to created short-form video

### Helper Methods

#### `_add_subtitles_to_context()`
Adds dual-language subtitles to context video.

**Improvements (TICKET-001 Phase 4):**
- Checks if file exists and reuses it (prevents conflicts between long-form and short-form)
- Uses consistent subtitle styling

#### `_sanitize_filename()`
Sanitizes expression names for filename usage.

**Critical for TICKET-001 Phase 4:**
- Uses regex: `re.sub(r'[^\w\s-]', '', text)` then `re.sub(r'[-\s]+', '_', text)`
- Must match exactly with `jobs.py` sanitization to ensure expression matching

#### `_create_educational_slide()`
Creates educational slide with background image/text and optional TTS audio.

**Improvements (TICKET-001):**
- Accepts optional `target_duration` parameter
- When provided, extends slide duration to match target (for proper hstack/vstack alignment)

## Architecture Patterns

### Demuxer-First Approach (TICKET-001)

The module now uses demuxer-based operations for maximum reliability:

1. **Expression Repetition:** `repeat_av_demuxer()` - uses concat demuxer instead of filter concat
2. **Concatenation:** `concat_demuxer_if_uniform()` - uses copy mode (no re-encode) to preserve timestamps
3. **Fallback:** Automatic fallback to filter concat if demuxer fails

**Benefits:**
- Preserves audio reliably
- Preserves timestamps (no A-V sync issues)
- Simpler pipeline graphs
- Better performance (copy mode)

### File Reuse Strategy (TICKET-001 Phase 3-4)

Both long-form and short-form now share intermediate files:

1. **Shared Expression Repeat:** `temp_expr_repeated_{expression}.mkv`
   - Created by long-form
   - Reused by short-form if exists

2. **Shared Expression Clip:** `temp_expr_clip_long_{expression}.mkv`
   - Created by long-form
   - Reused by short-form if exists

3. **Shared Context with Subtitles:** `context_with_subtitles`
   - Created by both formats
   - Checked before creation (reuses if exists)

**Benefits:**
- Consistent source material
- Reduced processing time
- No conflicts or mismatches

### Separation of Concerns

The pipeline follows a clear separation:

1. **AV Build:** Create concatenated video (context + expression repeat)
2. **Layout:** Stack AV with slide (hstack for long-form, vstack for short-form)
3. **Final Gain:** Apply audio gain (+25%) as separate pass

**Benefits:**
- Easier to test each stage
- Clearer error handling
- Better maintainability

## Dependencies

### Internal Dependencies
- `langflix/media/ffmpeg_utils.py` - FFmpeg utilities
  - `repeat_av_demuxer()` - Expression repetition
  - `concat_demuxer_if_uniform()` - Concatenation
  - `concat_filter_with_explicit_map()` - Fallback concatenation
  - `hstack_keep_height()` - Long-form layout
  - `vstack_keep_width()` - Short-form layout
  - `apply_final_audio_gain()` - Final audio boost
  - `get_duration_seconds()` - Duration measurement
- `langflix/subtitles/overlay.py` - Subtitle overlay functionality
- `langflix/slides/generator.py` - Educational slide generation
- `langflix/config/` - Configuration management

### External Dependencies
- `ffmpeg-python` - FFmpeg Python bindings
- `pathlib` - Path manipulation
- Standard library: `logging`, `os`, `re`

## Common Tasks

### Adding a New Video Layout Format

1. Create new stacking function in `langflix/media/ffmpeg_utils.py` (e.g., `grid_keep_aspect()`)
2. Add new method to `VideoEditor` class (e.g., `create_grid_format_video()`)
3. Follow same pattern: AV build → layout → final gain
4. Ensure file reuse with shared intermediate files
5. Add tests in `tests/integration/test_media_pipeline_*.py`

### Modifying Expression Repetition Logic

1. The repetition logic is centralized in `langflix/media/ffmpeg_utils.py`
2. Both `create_educational_sequence()` and `create_short_format_video()` use `repeat_av_demuxer()`
3. Ensure shared filename format: `temp_expr_repeated_{sanitized_expression}.mkv`
4. Test with different expression lengths and counts

### Debugging A-V Sync Issues

1. **Verify timestamp preservation:**
   ```bash
   ffprobe -v error -show_entries stream=codec_time_base,input_time_base input.mkv
   ```

2. **Check if copy mode is used:**
   - Look for `vcodec=copy` in logs (demuxer concat)
   - Avoid re-encoding when possible

3. **Verify frame rate consistency:**
   - All inputs should use same frame rate (normalized to 25fps in filter concat)

4. **Run verification script:**
   ```bash
   python tools/verify_media_pipeline.py
   ```

## Gotchas and Notes

### Expression Name Sanitization

⚠️ **Critical:** Expression name sanitization must match exactly between:
- `langflix/core/video_editor.py::_sanitize_filename()`
- `langflix/api/routes/jobs.py` (sanitization in job creation)

**Mismatch causes:** Short-form missing first expression (TICKET-001 Issue 3)

**Solution:** Use identical regex pattern in both places:
```python
sanitized = re.sub(r'[^\w\s-]', '', text)
sanitized = re.sub(r'[-\s]+', '_', sanitized)
```

### File Reuse and Conflicts

⚠️ **Important:** Both long-form and short-form create `context_with_subtitles`. Always check if file exists before creation:

```python
if Path(context_with_subtitles).exists():
    logger.info(f"Reusing existing context_with_subtitles: {context_with_subtitles}")
else:
    # Create new file
```

### Audio Processing Simplification

✅ **Best Practice:** After TICKET-001 Phase 5, short-form should NOT:
- Extract audio separately
- Process audio separately  
- Calculate durations from audio

✅ **Should:**
- Keep audio with video throughout pipeline
- Calculate durations from video
- Use vstack output directly (audio already preserved)

### Demuxer vs Filter Concat

**Use demuxer concat when:**
- Parameters are uniform (same codec, resolution, frame rate)
- You want copy mode (no re-encode, preserves timestamps)
- Performance is important

**Use filter concat when:**
- Parameters differ between inputs
- You need frame rate normalization
- Demuxer concat fails

**Current strategy:** Try demuxer first, fallback to filter concat automatically.

## Testing

### Integration Tests
- `tests/integration/test_media_pipeline_audio.py` - Audio preservation through pipeline
- `tests/functional/test_educational_video.py` - End-to-end educational video creation

### Verification Script
- `tools/verify_media_pipeline.py` - Comprehensive pipeline verification with ffprobe checks

## Related Documentation

- [ADR-015: FFmpeg Pipeline Standardization](../adr/ADR-015-ffmpeg-pipeline-standardization_eng.md)
- [Media Module Documentation](../media/README_eng.md)
- [Troubleshooting Guide](../TROUBLESHOOTING_GUIDE.md#videoaudio-sync-problems-a-v-sync)
