# Architect Review Notes - 2025-01-30

## System Understanding

### Architecture Overview
- **High-level Architecture**: LangFlix is a video processing pipeline that extracts educational content from TV shows
- **Key Components**: 
  - `langflix/core/` - Core video processing logic (VideoEditor, ExpressionAnalyzer, etc.)
  - `langflix/api/` - FastAPI HTTP interface for job management
  - `langflix/services/` - Business logic services
  - `langflix/media/` - FFmpeg utilities for video/audio processing
  - `langflix/db/` - Database integration (optional)
- **Critical Workflows**: 
  1. Video upload → Subtitle parsing → Expression analysis → Video generation → Output
  2. API job creation → Background processing → Status updates → Result retrieval

### Current State Assessment

**Strengths:**
- Well-modularized codebase with clear separation of concerns (core/api/services)
- Comprehensive documentation in `docs/` folder
- Good test structure (unit/integration/functional)
- Robust FFmpeg pipeline with demuxer-first approach (ADR-015)
- Error handler module exists but underutilized

**Known Issues:**
- Code duplication between CLI (`LangFlixPipeline`) and API (`process_video_task`)
- Inconsistent temporary file management across modules
- Unused/underutilized code (`error_handler.py`, `pipeline_runner.py`)
- Bug in `get_job_expressions` endpoint (undefined variable)
- Inconsistent filename sanitization logic

**Architectural Goals:**
- Consolidate video processing logic into unified service layer
- Standardize resource management (temp files, error handling)
- Remove code duplication and technical debt
- Improve maintainability and testability
- Align with service-oriented architecture pattern

### Technical Constraints
- **Performance**: Video processing is CPU-intensive, need efficient resource management
- **Scalability**: Current architecture supports single-node deployment
- **Integration dependencies**: 
  - Redis for job state management
  - Optional database integration
  - FFmpeg for video processing
  - External APIs for TTS/LLM

### Design Patterns Used
- **Service Layer Pattern**: Business logic in `services/` module
- **Pipeline Pattern**: Sequential processing in `LangFlixPipeline`
- **Repository Pattern**: Database abstraction in `db/` module
- **Strategy Pattern**: Different TTS providers, storage backends

### Technology Stack
- **Language**: Python 3.x
- **Framework**: FastAPI for HTTP API
- **Video Processing**: FFmpeg via `ffmpeg-python`
- **Storage**: File system, Redis for job state
- **Database**: SQLite (optional, via SQLAlchemy)

### Integration Points
- **External Services**: TTS APIs (Google, LemonFox), LLM APIs (Gemini)
- **File System**: Input media, output videos, temporary files
- **Redis**: Job status and progress tracking

---
## Ticket Review Process Starting Below

