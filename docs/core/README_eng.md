# Core Module Documentation

## Overview

The `langflix/core/` module contains the core video editing functionality for LangFlix. This module orchestrates the creation of educational video sequences, including long-form (side-by-side) and short-form (vertical) video layouts.

**Last Updated:** 2025-01-30  
**Related Tickets:** TICKET-001, TICKET-005

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

**Parallel LLM Processing (TICKET-001):**
- Expression analysis now supports parallel processing for multiple chunks
- Automatically uses `ExpressionBatchProcessor` to process chunks concurrently
- Configurable via `expression.llm.parallel_processing` in `default.yaml`

**How It Works:**
1. `_analyze_expressions()` checks if parallel processing is enabled and if multiple chunks exist
2. If enabled and multiple chunks available (and not in test_mode), uses `_analyze_expressions_parallel()`
3. Otherwise, falls back to sequential processing via `_analyze_expressions_sequential()`
4. Parallel processing uses `ExpressionBatchProcessor` which creates parallel tasks using `ThreadPoolExecutor`
5. Progress is reported as chunks complete (not sequentially)

**Configuration:**
```yaml
expression:
  llm:
    parallel_processing:
      enabled: true  # Enable parallel processing
      max_workers: null  # null = auto-detect (min(cpu_count(), 5))
      timeout_per_chunk: 300  # seconds
```

**When Parallel Processing is Used:**
- ✅ Parallel processing enabled (`expression.llm.parallel_processing.enabled: true`)
- ✅ Multiple chunks to process (`len(chunks) > 1`)
- ✅ Not in test mode (`test_mode=False`)

**When Sequential Processing is Used:**
- ❌ Parallel processing disabled
- ❌ Single chunk (no benefit from parallelization)
- ❌ Test mode (`test_mode=True`) - always sequential for debugging

**Performance Benefits:**
- 3-5x faster processing for 10+ chunks
- Processes chunks concurrently instead of waiting for each LLM API call
- Conservative default: max 5 workers to avoid Gemini API rate limits

**Example:**
```python
# With parallel processing enabled (default)
pipeline = LangFlixPipeline(...)
result = pipeline.run(
    max_expressions=10,
    test_mode=False  # Will use parallel processing if multiple chunks
)

# Logs will show:
# "Using PARALLEL processing for 15 chunks"
# "Starting parallel analysis of 15 chunks with 5 workers"
# "Parallel analysis complete in 45.2s"
```

**Multiple Expressions Per Context (TICKET-008):**
- Expressions sharing the same `context_start_time` and `context_end_time` are automatically grouped
- Groups share a single context video clip (efficiency gain)
- Each expression still gets its own educational video (separate mode, backward compatible)
- Configurable via `expression.llm.allow_multiple_expressions` and `expression.llm.max_expressions_per_context`

**How It Works:**
1. After expression analysis, `group_expressions_by_context()` groups expressions by shared context times
2. `_process_expressions()` extracts ONE context clip per group (shared by all expressions in group)
3. Separate subtitle files are created for each expression
4. `_create_educational_videos()` creates videos in this order:
   - **Multi-expression groups**: First creates a context video with multi-expression slide (left: context video, right: slide showing all expressions)
   - **Each expression**: Creates individual educational video (left: expression repeat only for multi-expression groups, or context + expression repeat for single-expression groups; right: expression's own slide)
5. Context clips are cached to avoid duplicate extractions

**Video Output Structure:**
- **Multi-expression group** (2+ expressions):
  1. Context video: left (context video) | right (multi-expression slide with all expressions)
  2. Expression 1 video: left (expression repeat only) | right (expression 1's slide)
  3. Expression 2 video: left (expression repeat only) | right (expression 2's slide)
  
- **Single-expression group** (backward compatible):
  1. Expression video: left (context + expression repeat) | right (expression's slide)

**Configuration:**
```yaml
expression:
  llm:
    allow_multiple_expressions: true  # Enable/disable feature
    max_expressions_per_context: 3    # Maximum expressions per context
  educational_video_mode: "separate"  # "separate" or "combined" (Phase 2)
```

**ExpressionGroup Model:**
- `ExpressionGroup` contains multiple `ExpressionAnalysis` objects sharing same context
- Validates that all expressions in group have matching `context_start_time` and `context_end_time`
- Supports iteration, indexing, and length queries for easy access

**Benefits:**
- More educational value from same content (multiple expressions from one context)
- Processing efficiency: shared context clips reduce duplicate video extractions
- Resource optimization: lower storage usage and faster processing
- Backward compatible: single expressions automatically become groups of 1

**Example:**
```python
# Grouping is automatic when enabled (default)
pipeline = LangFlixPipeline(
    subtitle_file="path/to/subtitle.srt",
    video_dir="assets/media",
    output_dir="output",
    enable_expression_grouping=True  # Default: True
)

# After run(), access groups:
groups = pipeline.expression_groups
for group in groups:
    print(f"Group has {len(group)} expression(s)")
    for expr in group:
        print(f"  - {expr.expression}")
```

**When Grouping is Used:**
- ✅ `enable_expression_grouping=True` (default)
- ✅ Multiple expressions share same context times
- ✅ Feature enabled in config (`expression.llm.allow_multiple_expressions: true`)

**When Single-Expression Groups are Created:**
- ❌ Grouping disabled (`enable_expression_grouping=False`)
- ❌ All expressions have different contexts (no grouping needed)
- ❌ Feature disabled in config

**Efficiency Gain:**
- If 3 expressions share the same context, only 1 context clip is extracted (instead of 3)
- Example: 10 expressions with 3 groups → 3 context clips instead of 10 (70% reduction)

### VideoEditor Class

The main class that orchestrates video creation.

**Location:** `langflix/core/video_editor.py`

**Error Handler Integration (TICKET-005):**
- `create_educational_sequence()` is wrapped with `@handle_error_decorator` for structured error reporting
- `create_short_format_video()` is wrapped with `@handle_error_decorator` for structured error reporting
- `_create_timeline_from_tts()` uses `@retry_on_error` decorator for automatic retry on transient failures (max 2 attempts, 1s delay)
- All errors are automatically logged with context (operation, component) via error handler
- Error reports include operation context for easier debugging

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

#### Filename Sanitization
The `VideoEditor` class uses `sanitize_for_expression_filename()` from `langflix.utils.filename_utils` for consistent filename sanitization across the codebase. See [Filename Utils Documentation](../utils/filename_utils_eng.md) for details.

**Critical for TICKET-001 Phase 4:**
- All filename sanitization now uses `sanitize_for_expression_filename()` from `langflix.utils.filename_utils`
- Ensures consistent sanitization across codebase (TICKET-004)
- Must match exactly between job creation and video file naming to ensure expression matching

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

### ExpressionAnalyzer Class

The class responsible for analyzing subtitle chunks using Gemini API.

**Location:** `langflix/core/expression_analyzer.py`

**Error Handler Integration (TICKET-005):**
- `analyze_chunk()` is wrapped with `@handle_error_decorator` for structured error reporting
- `_generate_content_with_retry()` now reports errors to error handler for each retry attempt
- Error context includes: `operation`, `component`, `max_retries`, `attempt`, `prompt_length`
- Errors are automatically categorized (NETWORK for timeouts/connection errors, PROCESSING for parsing errors)
- Error reports include retry attempt information for debugging API failures

**Key Features:**
- Automatic retry with exponential backoff for API failures
- Structured error reporting for all API errors
- Error categorization for better monitoring
- Detailed error context for debugging

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
- `langflix/utils/filename_utils.py::sanitize_for_expression_filename()` - See [Filename Utils Documentation](../utils/filename_utils_eng.md)
- `langflix/api/routes/jobs.py` (sanitization in job creation)

**Mismatch causes:** Short-form missing first expression (TICKET-001 Issue 3)

**Solution:** Use `sanitize_for_expression_filename()` from `langflix.utils.filename_utils` in both places (TICKET-004):
```python
from langflix.utils.filename_utils import sanitize_for_expression_filename

sanitized = sanitize_for_expression_filename(expression_text)
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
