# LangFlix - Copilot Instructions for AI Coding Agents

## Project Overview

**LangFlix** is an end-to-end educational video pipeline that extracts English expressions from TV shows (Suits), provides context and translations, and generates three types of educational videos:

1. **Structured videos** (16:9) - One per expression: context → expression repeat (2x) → slide with audio
2. **Combined structured video** (16:9) - All structured videos concatenated
3. **Short-form videos** (9:16) - Multiple expressions batched (≤180s per batch), vertical layout with centered video

### Key Architectural Principles

- **1:1 Context-Expression Mapping**: Each expression gets its own context clip (no grouping)
- **No Long-form/Short-form Distinction**: Single `create_structured_video()` method creates base format
- **Direct Video Processing**: FFmpeg-based extraction with output seeking for subtitle accuracy
- **Service-Based Architecture**: Pipeline logic in `services/video_pipeline_service.py`, not in main
- **Async Job Processing**: FastAPI backend with background job queue for video generation

---

## Critical Architecture Components

### 1. **Main Pipeline Flow** (`langflix/main.py` - `LangFlixPipeline` class)

**Purpose**: Orchestrates the entire expression → video pipeline

**Key Methods** (in order):
- `_parse_subtitles()` - Parse SRT files
- `_chunk_subtitles()` - Break into analyzable chunks  
- `_analyze_expressions()` - LLM analysis to extract expressions
- `_process_expressions()` - Create subtitle files (context extraction removed in TICKET-038)
- `_create_educational_videos()` - Generate structured videos (one per expression)
- `_create_combined_structured_video()` - Combine all structured videos
- `_create_short_videos()` - Batch structured videos into 9:16 short-form with 180s limit

**Data Flow**: 
```
Subtitles → Chunks → LLM Analysis → Expressions → 
Context Subtitles → Structured Videos → Combined Video → Short-form Batches
```

**Critical Pattern**: Pass original video path directly to `create_structured_video()`, not pre-extracted clips. The VideoEditor extracts context internally.

### 2. **Video Editor** (`langflix/core/video_editor.py`)

**Three Main Methods** (only these are active, others are dead code):

#### `create_structured_video(expression, context_video_path, expression_video_path)`
- **Purpose**: Create single expression video (context → expression repeat 2x → slide)
- **Key Steps**:
  1. Extract context video with subtitles
  2. Extract expression clip (output seeking for subtitle sync)
  3. Repeat expression clip 2 times
  4. Concatenate context + expression repeat
  5. Create educational slide with expression audio
  6. Final concatenation + audio gain (+69%)
- **Returns**: Path to `structured_video_{expression_name}.mkv`
- **Critical Detail**: Uses output seeking (`ss=` and `t=` parameters after input) for accurate subtitle synchronization

#### `create_short_form_from_structured(structured_video_path, expression)`
- **Purpose**: Convert 16:9 structured video to 9:16 short-form
- **Layout**:
  - Top: Expression text (black background, 180px)
  - Middle: Structured video (centered, height 960px, no stretch - crop left/right if needed)
  - Bottom: Subtitles (black background, 100px from bottom)
- **Returns**: Path to `short_form_{expression_name}.mkv` (1080x1920)

#### `create_batched_short_videos(short_form_list, target_duration=180)`
- **Purpose**: Batch multiple short-form videos with 180s limit per batch
- **Key Logic**: Drops videos that exceed max duration (180s default, configurable)
- **Returns**: List of batched video paths

**Dead Code to Ignore**:
- `create_educational_sequence()` - Removed (TICKET-038)
- `create_multi_expression_sequence()` - Removed (TICKET-038)  
- `create_short_format_video()` - Removed (TICKET-038)
- `_create_multi_expression_slide()` - Dead code (multi-expression grouping not implemented)

### 3. **Expression Analyzer** (`langflix/core/expression_analyzer.py`)

**Main Function**: `analyze_chunk(chunk_text, language_level)`
- Uses Google Gemini API for intelligent expression extraction
- Returns `ExpressionAnalysis` objects with timing, translation, definition, etc.

**Grouping**: `group_expressions_by_context(expressions)` 
- Currently creates 1:1 mapping (each expression in own group)
- Reason: "1 context → 1 expression" design (TICKET-038)
- **Note**: Function exists for future multi-expression support but NOT used now

### 4. **Output Structure** (`langflix/services/output_manager.py`)

**Directory Layout**:
```
output/
├── {language}/
│   ├── subtitles/          # Subtitle files per expression
│   ├── structured_videos/  # Individual structured videos
│   ├── short_videos/       # Batched short-form videos
│   └── combined/           # Combined structured video
```

**Key Function**: `create_output_structure(output_dir, language)` - Creates directories on demand

### 5. **Service Layer** (`langflix/services/video_pipeline_service.py`)

**Purpose**: Wrapper service for pipeline execution with job tracking

**Main Method**: `process_video(video_path, subtitle_path, language, job_id, short_form_max_duration=180)`
- Instantiates `LangFlixPipeline`
- Executes pipeline stages
- Returns job result with output paths

**Config Integration**: 
- `short_form_max_duration` parameter for configurable batch duration
- Default 180 seconds (configurable in `langflix/config/default.yaml`)

### 6. **API Layer** (`langflix/api/main.py` and `langflix/api/routes/`)

**FastAPI Backend** on port 8000

**Key Endpoints**:
- `POST /api/jobs/process-video` - Submit video for processing
- `GET /api/jobs/{job_id}` - Get job status
- `GET /api/jobs/{job_id}/result` - Get output paths when complete

**Async Pattern**: Jobs run in background queue, responses include `job_id` for polling

### 7. **Web UI** (`langflix/youtube/web_ui.py`)

**Flask Frontend** on port 5000
- Dashboard for submitting videos
- Status monitoring
- Download generated videos

---

## Essential Development Workflows

### Running the Pipeline Locally

```bash
# Start development environment
make dev-all

# OR start individually:
make dev-backend      # FastAPI on :8000
make dev-frontend     # Flask on :5000

# Backend API docs: http://localhost:8000/docs
# Frontend: http://localhost:5000
```

### Command-Line Usage

```bash
# Full pipeline (old CLI interface, still works)
python -m langflix.main \
  --video assets/media/suits_s01e01.mkv \
  --subtitle assets/subtitles/suits_s01e01.srt \
  --language en \
  --output output/

# Or use API endpoint via curl
curl -X POST http://localhost:8000/api/jobs/process-video \
  -F "video_file=@suits_s01e01.mkv" \
  -F "subtitle_file=@suits_s01e01.srt" \
  -F "language=en"
```

### Running Tests

```bash
# All tests
python run_tests.py

# Specific test file
pytest tests/unit/test_video_editor.py -v

# Integration tests (requires API running)
pytest tests/integration/ -v
```

### Docker

```bash
# Start database and cache services
make docker-up

# Stop services
make docker-down

# View logs
make docker-logs
```

---

## Project-Specific Patterns & Conventions

### 1. **Error Handling Decorator**

```python
@handle_error_decorator(
    ErrorContext(
        operation="create_structured_video",
        component="core.video_editor"
    ),
    retry=False,  # Video processing shouldn't auto-retry
    fallback=False
)
def create_structured_video(self, ...):
    # Implementation
```

**Pattern**: All video processing methods use `@handle_error_decorator` with `retry=False` because video processing failures are deterministic, not transient.

### 2. **Temporary File Management**

```python
# Register temp file for tracking
temp_file = self.output_dir / f"temp_expr_{safe_name}.mkv"
self._register_temp_file(temp_file)

# Automatically cleaned up after pipeline completes
```

**Pattern**: Use `_register_temp_file()` for any temporary video file. The `TempFileManager` tracks and cleans them automatically.

### 3. **FFmpeg Integration**

**Use output seeking for subtitle accuracy** (CRITICAL for TICKET-038):
```python
# CORRECT: Output seeking (ss/t after input)
ffmpeg.output(
    video_stream,
    audio_stream,
    str(output_path),
    ss=relative_start,  # After input
    t=duration
).run()

# WRONG: Input seeking (ss before input) - causes subtitle misalignment
ffmpeg.input(str(video), ss=start)  # Don't do this for subtitled videos
```

**Pattern**: Always use `ffmpeg.filter()` with `setpts` to reset timestamps for concatenation.

### 4. **Language Configuration**

```python
from langflix.core.language_config import LanguageConfig

# Each language has specific TTS voice, fonts, etc.
config = LanguageConfig(language='en')
config.get_tts_voice()    # Get Gemini TTS voice
config.get_font_config()  # Get subtitle font
```

**Pattern**: Language-specific settings are centralized. Always check `LanguageConfig` before hardcoding.

### 5. **Expression Model Structure**

```python
class ExpressionAnalysis(BaseModel):
    expression: str                    # "You killed it"
    context_start_time: str           # "00:00:15,000"
    context_end_time: str             # "00:00:45,000"
    expression_start_time: str        # "00:00:28,500"
    expression_end_time: str          # "00:00:30,200"
    original_dialogue: str            # Full context dialogue
    expression_dialogue: Optional[str]# Just expression dialogue
    translation: str                  # Translated meaning
    definition: str                   # Dictionary definition
    usage_example: str                # How to use it
    expression_level: str             # "Beginner", "Intermediate", etc.
```

**Pattern**: All timing is in `HH:MM:SS,mmm` SRT format. Use `_time_to_seconds()` for calculations.

### 6. **Configuration Pattern**

```python
# In langflix/config/default.yaml:
short_video:
  max_duration: 180  # Configurable batch duration

# Access in code:
from langflix import settings
max_duration = settings.get_short_video_max_duration()
```

**Pattern**: All configurable values go in YAML, accessed via `settings` module. Never hardcode magic numbers.

---

## Common Tasks & Solutions

### Task: Add a New Video Processing Step

1. Add method to `VideoEditor` class with `@handle_error_decorator`
2. Register any temp files with `self._register_temp_file()`
3. Use FFmpeg output seeking for subtitle-dependent processing
4. Call from `LangFlixPipeline._create_*_videos()` method
5. Update output manager if new directories needed

### Task: Modify Short-Form Batching Logic

1. Edit `create_batched_short_videos()` in `video_editor.py`
2. Update batching duration: check `settings.get_short_video_max_duration()` 
3. Test with various video counts and durations in `tests/unit/test_batched_videos.py`

### Task: Add New Expression Filter/Ranking

1. Extend `ExpressionSelector` in `langflix/core/expression_selector.py`
2. Add method like `rank_by_frequency()` or `filter_by_level()`
3. Call from `_analyze_expressions()` in `main.py`
4. Add tests in `tests/unit/test_expression_ranking.py`

### Task: Debug Subtitle Misalignment

1. Check that `create_structured_video()` uses **output seeking** (ss/t after input)
2. Verify `_add_subtitles_to_context()` creates subtitle file correctly
3. Use `ffprobe` to check subtitle timing: `ffprobe -show_entries packet=pts_time video.mkv`
4. Enable DEBUG logging: `python main.py --verbose`

---

## Critical Files Map

| Path | Purpose | Modify When |
|------|---------|-------------|
| `langflix/main.py` | Pipeline orchestration | Changing sequence of steps |
| `langflix/core/video_editor.py` | Video creation methods | Adding new video layouts |
| `langflix/services/video_pipeline_service.py` | Service wrapper | Adding pipeline configuration options |
| `langflix/api/routes/jobs.py` | API job endpoints | Adding API parameters |
| `langflix/config/default.yaml` | Configuration values | Changing defaults |
| `langflix/services/output_manager.py` | Output directory structure | Changing output paths |
| `langflix/core/expression_analyzer.py` | LLM prompt/analysis | Tweaking expression extraction |

---

## Known Limitations & Deprecated Patterns

❌ **DO NOT USE** (Removed in TICKET-038):
- `create_educational_sequence()` - Use `create_structured_video()` instead
- `create_multi_expression_sequence()` - Multi-expression videos not currently supported
- `ExpressionGroup.validate_expressions()` - Not implemented for 1:1 mapping
- Input seeking for subtitle video (`ffmpeg.input(..., ss=...)`) - Use output seeking only

---

## Video Format Documentation

### Short-Form Video Structure (9:16 Vertical)
**See**: `docs/SHORT_FORM_VIDEO_STRUCTURE.md`

Complete reference for short-form video layout, including:
- Canvas specification (1080x1920px)
- Component breakdown (top/middle/bottom sections)
- FFmpeg filter chain details
- Technical specifications (colors, fonts, timing)
- Platform-specific notes (TikTok, Instagram, YouTube)

This document details the exact layout used in `create_short_form_from_structured()` method.

---

## Quick Reference: Common Commands

```bash
# Start everything
make dev-all

# Run single expression test
pytest tests/unit/test_expression_analyzer.py::test_basic_expression -v

# Check code style
black --check langflix/

# Profile pipeline
python -c "from langflix.profiling import PipelineProfiler; p = PipelineProfiler(); p.print_report()"

# Generate sample output
python -m langflix.main --video test_video.mkv --subtitle test.srt --output ./output
```

---

## Communication & Collaboration Notes

- **Language**: Accept queries in English/Korean, but code/commits are English-only
- **Git Workflow**: Use `feature/TICKET-XXX-description` branch naming
- **Commit Format**: `[feat/fix/refactor] brief description` in English
- **Code Review**: Reference specific line numbers and explain the "why"
- **When Stuck**: Check test files first (`tests/` directory) - they document expected behavior

