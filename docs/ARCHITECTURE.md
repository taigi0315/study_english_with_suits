# LangFlix Architecture

## Overview

LangFlix is an AI-powered language learning platform that extracts educational expressions from TV show subtitles and generates learning videos.

```
┌─────────────────────────────────────────────────────────────────┐
│                         LangFlix System                         │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Web UI    │  │  REST API   │  │        CLI              │  │
│  │  (Flask)    │  │  (FastAPI)  │  │   (langflix.main)       │  │
│  └──────┬──────┘  └──────┬──────┘  └───────────┬─────────────┘  │
│         │                │                      │                │
│         └────────────────┼──────────────────────┘                │
│                          │                                       │
│              ┌───────────┴───────────┐                          │
│              │  VideoPipelineService │                          │
│              └───────────┬───────────┘                          │
│                          │                                       │
│    ┌─────────────────────┼─────────────────────┐                │
│    │                     │                     │                │
│    ▼                     ▼                     ▼                │
│ ┌──────────┐      ┌────────────┐      ┌───────────────┐        │
│ │Subtitle  │      │ Expression │      │    Video      │        │
│ │Parser    │──────│ Analyzer   │──────│   Editor      │        │
│ └──────────┘      │ (Gemini)   │      └───────────────┘        │
│                   └────────────┘              │                 │
│                                               │                 │
│                          ┌────────────────────┼────────────┐    │
│                          │                    │            │    │
│                          ▼                    ▼            ▼    │
│                   ┌────────────┐      ┌───────────┐  ┌───────┐ │
│                   │    TTS     │      │  FFmpeg   │  │YouTube│ │
│                   │  (Gemini)  │      │  Utils    │  │Upload │ │
│                   └────────────┘      └───────────┘  └───────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Modules

### `langflix/core/`
| Module | Purpose |
|--------|---------|
| `video_editor.py` | Main video creation logic - long-form, short-form, slides |
| `expression_analyzer.py` | Gemini LLM integration for expression extraction |
| `video_processor.py` | Video clip extraction and processing |
| `subtitle_processor.py` | Subtitle parsing and translation |
| `models.py` | Pydantic data models (ExpressionAnalysis, etc.) |

### `langflix/services/`
| Module | Purpose |
|--------|---------|
| `video_pipeline_service.py` | Unified pipeline orchestration |
| `video_factory.py` | Video creation factory |
| `translation_service.py` | Multi-language translation |
| `queue_processor.py` | Background job processing |

### `langflix/api/`
| Module | Purpose |
|--------|---------|
| `main.py` | FastAPI application entry point |
| `routes/` | API endpoint definitions |

### `langflix/media/`
| Module | Purpose |
|--------|---------|
| `ffmpeg_utils.py` | FFmpeg wrapper functions |
| `audio_optimizer.py` | Audio processing utilities |

---

## Data Flow

```
1. INPUT: Subtitle file (.srt) + Video file (.mkv)
           │
           ▼
2. PARSE:  SubtitleParser chunks subtitles
           │
           ▼
3. ANALYZE: ExpressionAnalyzer (Gemini) extracts expressions
           │
           ▼
4. PROCESS: For each expression:
           ├── Extract context video clip
           ├── Generate TTS audio
           ├── Create educational slide
           └── Combine into learning video
           │
           ▼
5. OUTPUT: Long-form video (16:9) + Short-form video (9:16)
           │
           ▼
6. UPLOAD: YouTube integration (optional)
```

---

## Key Configuration

All configuration is in `config/default.yaml` and `config.yaml`:

- **LLM Settings**: Model, temperature, max tokens
- **Video Settings**: Codec, preset, quality
- **TTS Settings**: Provider, voice selection
- **Expression Settings**: Min/max per chunk, repeat count

See [CONFIGURATION.md](CONFIGURATION.md) for details.

---

## Entry Points

| Entry Point | Command | Use Case |
|-------------|---------|----------|
| CLI | `python -m langflix.main` | Batch processing |
| API | `python -m langflix.api.main` | Web service |
| Web UI | `python -m langflix.youtube.web_ui` | User interface |
| Make | `make dev-all` | Development |

---

## Directory Structure

```
langflix/
├── langflix/           # Main application
│   ├── api/           # FastAPI endpoints
│   ├── core/          # Core business logic
│   ├── services/      # Service layer
│   ├── media/         # Media processing
│   ├── tts/           # Text-to-speech
│   ├── youtube/       # YouTube integration
│   └── settings.py    # Configuration
├── config/            # YAML configuration
├── assets/            # Media assets
├── tests/             # Test suite
├── docs/              # Documentation
└── deploy/            # Docker deployment
```
