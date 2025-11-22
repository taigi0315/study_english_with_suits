# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**LangFlix** is an AI-powered educational video generation system that automatically extracts English expressions from TV show subtitles and creates engaging short-form learning videos. It uses Google Gemini API for intelligent expression analysis and combines video processing, text-to-speech, and subtitle generation into a complete educational content pipeline.

**Key Capabilities:**
- Analyzes TV show subtitles to extract valuable English expressions, idioms, and phrases
- Generates structured educational videos (9:16 vertical format) with context clips and educational slides
- Supports multiple language levels (beginner, intermediate, advanced, mixed)
- Provides FastAPI-based REST API for asynchronous video processing with job queue management
- Includes comprehensive testing framework with unit, integration, and end-to-end tests

## Development Commands

### Environment Setup
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Setup configuration
cp env.example .env       # Add GEMINI_API_KEY
cp config/config.example.yaml config/config.yaml
```

### Running the Application
```bash
# CLI: Process a single episode
python -m langflix.main \
  --subtitle "assets/media/Suits/Suits.S01E01.720p.HDTV.x264.srt" \
  --video-dir "assets/media"

# API Server: Start FastAPI service
python -m langflix.api.main
# or with uvicorn directly:
uvicorn langflix.api.main:app --host 0.0.0.0 --port 8000 --reload

# Docker: Run full stack (API + PostgreSQL + Redis)
docker-compose -f docker-compose.dev.yml up -d
```

### Testing
```bash
# Run all tests
python run_tests.py all

# Run specific test suites
python run_tests.py unit
python run_tests.py functional
python run_tests.py integration

# Run with coverage
python run_tests.py all --coverage

# Run step-by-step pipeline tests (debugging)
python tests/step_by_step/run_all_steps.py

# Run single test file
pytest tests/unit/test_expression_analyzer.py -v
```

### Database Management
```bash
# Run migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "Description"

# Reset database (development)
alembic downgrade base && alembic upgrade head
```

### Code Quality
```bash
# Format code
black langflix/
isort langflix/

# Lint
flake8 langflix/
pylint langflix/

# Type checking
mypy langflix/
```

## Architecture Overview

### High-Level Pipeline Flow
```
1. Subtitle Parsing → 2. Expression Analysis (Gemini API) → 3. Video Processing →
4. Audio Generation (TTS) → 5. Educational Slide Creation → 6. Video Assembly →
7. Short-form Video Generation
```

### Core Components

**`langflix/core/`** - Core processing logic
- `subtitle_parser.py` - SRT file parsing and subtitle chunking
- `expression_analyzer.py` - Gemini API integration for expression extraction
- `video_processor.py` - Video file mapping and clip extraction
- `video_editor.py` - Video assembly and transition effects
- `subtitle_processor.py` - Dual-language subtitle generation
- `models.py` - Pydantic models for structured data validation

**`langflix/api/`** - FastAPI REST API
- `main.py` - API server entry point
- `routes/` - API endpoint definitions (jobs, expressions, health)
- `dependencies.py` - Dependency injection (DB sessions, settings)
- `middleware.py` - Request/response middleware

**`langflix/services/`** - Business logic services
- `video_pipeline_service.py` - Main video generation orchestration
- `queue_processor.py` - Background job processing
- `batch_queue_service.py` - Batch job management
- `output_manager.py` - Output file organization and management

**`langflix/db/`** - Database layer (PostgreSQL + SQLAlchemy)
- `models.py` - SQLAlchemy ORM models
- `crud.py` - Database CRUD operations
- `session.py` - Database session management

**`langflix/config/`** - Configuration management
- `config_loader.py` - YAML config loading with environment variable overrides
- `font_utils.py` - Platform-specific font detection
- `default.yaml` - Default configuration values

**`langflix/tts/`** - Text-to-speech integration
- Google Gemini TTS with SSML control for natural speech

**`langflix/slides/`** - Educational slide generation
- 5-section layout with dialogue context and expression highlighting

### Key Architectural Patterns

**1. Structured Video Creation (Current Architecture as of 2025-01)**
- Individual expression processing (1:1 expression-to-video mapping)
- Structured videos combine context clip + educational slide
- Short-form videos (9:16) generated from structured videos with max duration limits
- See `docs/core/structured_video_creation_eng.md` for details

**2. Configuration Cascade**
- Built-in defaults (`langflix/config/default.yaml`)
- User overrides (`config/config.yaml`)
- Environment variables (`LANGFLIX_*` prefix)

**3. Video Processing Strategy (TICKET-035)**
- Auto mode: Attempts stream copy first, falls back to re-encode
- Configurable via `video.clip_extraction.strategy` (auto/copy/encode)
- Optimizes for both speed and accuracy

**4. Database Integration**
- Optional database support (can run without DB)
- Tracks media files, expressions, and processing jobs
- Alembic migrations for schema management

**5. Job Queue Architecture**
- Redis-backed job queue for async processing
- Job status tracking (pending, processing, completed, failed)
- Progress reporting and error handling

## Critical Implementation Details

### Expression Analysis with Gemini API

The system chunks subtitles into ~2000 character segments and sends them to Gemini API with a detailed prompt template (`langflix/templates/expression_analysis_prompt.txt`). The API returns structured JSON validated against Pydantic models.

**Key Considerations:**
- API retry logic with exponential backoff (max 3 retries)
- Structured output validation using Pydantic
- Expression limits: min/max per chunk configurable in `config.yaml`
- Supports multiple language levels and target languages

### Video Processing Pipeline

**Context Video Extraction:**
- Frame-accurate clip extraction (0.1s precision)
- Buffer times configurable (default: 0.2s before/after expression)
- Dual-language subtitle overlay on context clips

**Educational Slides:**
- 5-section layout: expression, translation, dialogue context, similar expressions, catchy keywords
- Background video with text overlays using ffmpeg filters
- Font detection based on platform (macOS/Linux/Windows)

**Transition Effects:**
- Smooth transitions between segments (xfade, fade)
- Configurable in `config.yaml` under `transitions` section
- Duration and effect type customizable per transition type

### Testing Strategy

**7-Stage Step-by-Step Tests** (`tests/step_by_step/`):
1. Load & analyze subtitles with LLM
2. Extract context video clips
3. Add target language subtitles
4. Extract expression audio
5. Create educational slides
6. Combine context + slides
7. Create final concatenated video

Each stage is independently testable for debugging complex pipeline issues.

**Test Organization:**
- `tests/unit/` - Unit tests for individual components
- `tests/integration/` - Cross-module integration tests
- `tests/functional/` - End-to-end workflow tests
- `tests/api/` - API endpoint tests

## Common Development Tasks

### Adding a New Expression Field

1. Update `langflix/core/models.py` - Add field to `ExpressionAnalysis` Pydantic model
2. Update prompt template - Modify `langflix/templates/expression_analysis_prompt.txt`
3. Update database model - Add field to `langflix/db/models.py` (Expression model)
4. Create migration - `alembic revision --autogenerate -m "Add field"`
5. Update tests - Add test cases in `tests/unit/test_models.py`

### Modifying Video Layout

1. Review current architecture - Read `docs/core/structured_video_creation_eng.md`
2. Modify video creation - Edit `langflix/core/video_editor.py`
3. Update slide generation - Modify `langflix/slides/` components
4. Test changes - Run `python tests/step_by_step/test_step5_create_slide.py`
5. Update documentation - Edit relevant docs in `docs/core/`

### Adding a New API Endpoint

1. Create route file - Add to `langflix/api/routes/`
2. Define request/response models - Use Pydantic in `langflix/api/models/`
3. Implement business logic - In `langflix/services/`
4. Register route - Import in `langflix/api/main.py`
5. Add tests - Create test file in `tests/api/`
6. Update API docs - FastAPI auto-generates OpenAPI docs

### Debugging Video Processing Issues

```bash
# Run step-by-step tests to isolate the problem stage
python tests/step_by_step/test_step1_load_and_analyze.py  # LLM analysis
python tests/step_by_step/test_step2_slice_video.py       # Video extraction
python tests/step_by_step/test_step3_add_subtitles.py     # Subtitle overlay
# ... continue through steps 4-7

# Enable verbose logging
python -m langflix.main --subtitle "path/to/file.srt" --verbose

# Save LLM outputs for inspection
python -m langflix.main --subtitle "path/to/file.srt" --save-llm-output

# Dry run (analysis only, no video processing)
python -m langflix.main --subtitle "path/to/file.srt" --dry-run
```

## Configuration Guide

### Key Configuration Sections

**LLM Settings** (`llm` in config.yaml):
- `max_input_length`: Characters per chunk (default: 4000)
- `target_language`: Translation language (default: "Korean")
- `default_language_level`: beginner/intermediate/advanced/mixed
- `temperature`, `top_p`, `top_k`: Gemini API parameters

**Video Processing** (`video`):
- `preset`: FFmpeg encoding preset (default: "veryfast")
- `crf`: Constant Rate Factor for quality (default: 0)

**Expression Limits** (`processing`):
- `min_expressions_per_chunk`: Minimum expressions to extract (default: 1)
- `max_expressions_per_chunk`: Maximum expressions per chunk (default: 3)

**Transitions** (`transitions`):
- `enabled`: Enable/disable smooth transitions
- `context_to_expression_transition`: Transition video with image/sound effects
- `context_to_slide_transition`: Slide transition with image/sound effects

**Expression** (`expression`):
- `repeat_count`: Global repeat count for TTS and videos (default: 3)
- `llm.parallel_processing`: Settings for parallel LLM processing
- `llm.allow_multiple_expressions`: Enable multiple expressions per context

### Environment Variable Overrides

Any config value can be overridden with environment variables:
```bash
export LANGFLIX_LLM_MAX_INPUT_LENGTH=3000
export LANGFLIX_VIDEO_CRF=28
export LANGFLIX_TARGET_LANGUAGE="French"
```

## Important Notes

### Media File Organization

The system expects a specific directory structure for automatic video-subtitle matching:
```
assets/media/
└── Suits/
    ├── Suits.S01E01.720p.HDTV.x264.mkv
    ├── Suits.S01E01.720p.HDTV.x264.srt
    └── ...
```

The video processor uses fuzzy filename matching to handle truncated or slightly different filenames.

### Git Workflow (from .cursorrules)

- **Branch naming**: `feature/ticket-number-description`, `fix/ticket-number-description`, `refactor/ticket-number-description`
- **Commit format**: `[type] brief description` where type is `feat`, `fix`, `refactor`, `docs`, `test`, `chore`
- **Code language**: English (variables, functions, comments)
- **Documentation**: Bilingual versions (`filename_eng.md`, `filename_kor.md`)

### Database Migration Safety

Always review auto-generated migrations before applying:
```bash
# Generate migration
alembic revision --autogenerate -m "Description"

# Review the generated file in alembic/versions/
# Then apply if correct
alembic upgrade head
```

### Performance Considerations

- **Parallel Processing**: Expression analysis can be parallelized (configurable max concurrent workers)
- **Video Processing**: Stream copy mode is faster but less accurate than re-encoding
- **Memory Management**: Large video files are processed in chunks to avoid memory issues
- **Redis Caching**: LLM responses can be cached to avoid redundant API calls

## Troubleshooting Quick Reference

**"GEMINI_API_KEY not found"**
- Ensure `.env` file exists with valid API key

**"Could not find video file for subtitle"**
- Check filename matching between video and subtitle files
- Verify `--video-dir` path is correct
- Try placing video file in same directory as subtitle

**"JSON parsing error from LLM"**
- Check `langflix.log` for raw API response
- May indicate prompt template issue or API instability
- Try with `--save-llm-output` to inspect responses

**"Database connection error"**
- Verify PostgreSQL is running: `docker-compose ps`
- Check connection string in `.env` file
- Ensure database exists and migrations are up to date

**Docker container fails to start**
- Check logs: `docker-compose -f docker-compose.dev.yml logs`
- Verify `.env` file is configured
- Ensure required ports (8000, 5432, 6379) are not in use

For comprehensive troubleshooting, see `docs/TROUBLESHOOTING.md` (English) or `docs/TROUBLESHOOTING_KOR.md` (Korean).

## Additional Resources

- **User Manual**: `docs/en/USER_MANUAL.md` (also available in Korean)
- **API Reference**: `docs/en/API_REFERENCE.md`
- **System Design**: `docs/system_design_and_development_plan.md`
- **Development Diary**: `docs/development_diary.md`
- **Deployment Guide**: `docs/en/DEPLOYMENT.md`
- **Performance Guide**: `docs/en/PERFORMANCE.md`

## Recent Major Changes

**2025-01-XX - Structured Video Architecture (TICKET-038, 039, 040)**
- Removed ExpressionGroup concept → Individual expression processing
- Introduced `create_structured_video()` for 1:1 expression-to-video mapping
- New `create_short_form_from_structured()` for 9:16 format conversion
- Added short-form max duration configuration
- See `docs/core/structured_video_creation_eng.md` for complete details

**2024-XX - YouTube Integration (Phase 6+)**
- YouTube upload functionality with OAuth2 authentication
- Schedule management for automated uploads
- Metadata generation for video titles, descriptions, tags

**2024-XX - API and Database Support (Phase 5)**
- FastAPI REST API with async job processing
- PostgreSQL database with SQLAlchemy ORM
- Redis-backed job queue
- Web UI for job management
