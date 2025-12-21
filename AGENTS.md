# AGENTS.md

A guide for AI coding agents working on the LangFlix project.

## Project Overview

LangFlix is a language learning video generation platform that:
- Analyzes TV show subtitles to extract educational expressions
- Uses Gemini AI for content analysis and translation
- Generates short-form and long-form educational videos with dual-language subtitles
- Supports V2 dual-language workflow with Netflix-style subtitle folders

**Tech Stack**: Python 3.9+, FastAPI, Flask, FFmpeg, Gemini AI, PostgreSQL, Redis

## Setup Commands

```bash
# Create virtual environment and install dependencies
make setup

# Start development servers (Backend: 8000, Frontend: 5000)
make dev-all

# Start Docker services (PostgreSQL, Redis, Celery)
make docker-up

# Stop all services
make stop-all
```

## Build and Test Commands

```bash
# Run all tests
make test

# Run specific test suites
make test-unit          # Unit tests
make test-api           # API tests

# Run step-by-step workflow tests
python tests/step_by_step/run_all_steps.py

# Run the main pipeline (analysis + video generation)
python -m langflix.main --subtitle "path/to/subtitle.srt" --video-dir "assets/media"
```

## Directory Structure

```
langflix/
├── langflix/                 # Main package
│   ├── main.py              # Pipeline entry point
│   ├── settings.py          # Configuration management
│   ├── api/                 # FastAPI endpoints
│   ├── core/                # Core business logic (video_editor, subtitle_parser, etc.)
│   ├── services/            # Service layer (translation, processing)
│   ├── config/              # YAML configuration files
│   └── templates/           # LLM prompt templates
├── tests/                   # Test suite
│   ├── unit/               # Unit tests
│   ├── functional/         # End-to-end tests
│   ├── integration/        # API integration tests
│   └── step_by_step/       # Step-by-step workflow tests
├── docs/                   # Documentation
├── deploy/                 # Docker and deployment configs
├── config/                 # User configuration overrides
└── Makefile               # Development commands
```

## Code Style

- **Type hints**: Use throughout for function signatures
- **Pydantic models**: For data validation (`langflix/core/models/`)
- **YAML configuration**: Primary config in `langflix/config/default.yaml`
- **Docstrings**: Include for all public functions and classes
- **Logging**: Use `logging` module, not print statements

## Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| Main Pipeline | `langflix/main.py` | Orchestrates video generation workflow |
| Settings | `langflix/settings.py` | Configuration loading and access |
| Video Editor | `langflix/core/video_editor.py` | FFmpeg video processing |
| Subtitle Parser | `langflix/core/subtitle_parser.py` | SRT/VTT parsing |
| Content Analyzer | `langflix/core/content_selection_analyzer.py` | V2 LLM content selection |
| API Endpoints | `langflix/api/` | FastAPI REST API |
| Web UI | `langflix/youtube/web_ui.py` | Flask frontend |

## Testing Instructions

1. **Always run tests before committing**: `make test`
2. **Add tests for new functionality** in appropriate `tests/` subdirectory
3. **Use step-by-step tests** for debugging pipeline issues
4. **Check logs** at `langflix.log` for detailed error information

## Configuration

Primary configuration: `langflix/config/default.yaml`

Key settings:
- `dual_language.enabled`: V2 mode toggle
- `dual_language.source_language`: Language being learned (e.g., "English")
- `dual_language.target_language`: User's native language (e.g., "Korean")
- `llm.model_name`: Gemini model for content analysis
- `llm.max_input_length`: 0 = process entire script at once

Override via environment variables: `LANGFLIX_<SECTION>_<KEY>=value`

## Subtitle Folder Structure

LangFlix V2 expects Netflix-style subtitle folders:

```
assets/media/ShowName/
├── ShowName.S01E01.mkv
└── Subs/
    └── ShowName.S01E01/
        ├── 3_Korean.srt       # Netflix indexed format
        ├── 6_English.srt
        └── Spanish.srt        # Simple format (translated)
```

## Related Documentation

- [README.md](README.md) - Project overview
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - V2 system design
- [docs/CONFIGURATION.md](docs/CONFIGURATION.md) - Configuration reference
- [docs/QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md) - Visual workflows
