# AGENTS.md - LangFlix AI Agent Configuration

> This file provides context, rules, and skills for AI coding agents working on the LangFlix project.

---

## Project Overview

**LangFlix** is an AI-powered educational video generation system that:
- Extracts language expressions from any TV show or media subtitles (multi-language support)
- Provides context, translations, and definitions using Google Gemini API
- Generates structured educational videos (16:9) and short-form videos (9:16)
- Supports automated YouTube upload and scheduling

**Tech Stack:** Python 3.9+, FastAPI, Flask, FFmpeg, Google Gemini API, PostgreSQL, Redis

---

## Quick Navigation

| Need | Go To |
|------|-------|
| **Video processing rules** | [rules/video_processing.md](rules/video_processing.md) |
| **Testing standards** | [rules/testing.md](rules/testing.md) |
| **Code conventions** | [rules/code_standards.md](rules/code_standards.md) |
| **Debugging help** | [skills/debugging.md](skills/debugging.md) |
| **FFmpeg patterns** | [skills/ffmpeg_patterns.md](skills/ffmpeg_patterns.md) |
| **Gemini API usage** | [skills/gemini_api.md](skills/gemini_api.md) |
| **New feature process** | [workflows/new_feature.md](workflows/new_feature.md) |
| **Bug fix process** | [workflows/bug_fix.md](workflows/bug_fix.md) |
| **Video generation** | [workflows/video_generation.md](workflows/video_generation.md) |

---

## Critical Rules (Summary)

### ⚠️ MUST Follow

1. **Video Processing**: Use **output seeking** for FFmpeg with subtitles
2. **Error Handling**: Use `@handle_error_decorator` with `retry=False`
3. **Temp Files**: Register with `_register_temp_file()`
4. **Quality**: CRF 18, slow preset for final output
5. **Configuration**: No hardcoded values - use `config/`
6. **Database**: Check `DATABASE_ENABLED` flag

### 🚫 DO NOT

- Use input seeking for subtitle video processing
- Create multi-expression groupings
- Hardcode magic numbers or file paths
- Skip tests when making changes

→ **Full details**: [rules/video_processing.md](rules/video_processing.md)

---

## Development Work Process

```
1. ANALYZE    → Understand the issue/requirement
2. TICKET     → Create ticket in tickets/
3. IMPLEMENT  → Write code following project patterns
4. TEST       → Write/update tests, run test suite
5. GENERATE   → Run video generation (integration test)
6. MOVE TICKET → Move to tickets/approved/
7. DOCUMENT   → Update relevant documentation
```

→ **Detailed workflows**: [workflows/](workflows/)

---

## Critical Files Reference

| File | Purpose |
|------|---------|
| `langflix/main.py` | Pipeline orchestration |
| `langflix/core/video_editor.py` | Video creation methods |
| `langflix/services/video_pipeline_service.py` | Service wrapper |
| `langflix/config/default.yaml` | Default configuration |
| `langflix/core/expression_analyzer.py` | LLM integration |

---

## Quick Commands

```bash
# Start development
make dev-all

# Run tests
make test

# Generate test video
python -m langflix.main --subtitle "test.srt" --test-mode

# View logs
tail -f langflix.log
```

---

## Documentation References

- [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md) - System architecture
- [docs/DEVELOPMENT.md](../docs/DEVELOPMENT.md) - Development guide
- [docs/CONFIGURATION.md](../docs/CONFIGURATION.md) - Configuration options
- [docs/API.md](../docs/API.md) - REST API reference

---

## Language & Communication

- **Queries**: Accept English and Korean
- **Responses**: Korean for user communication
- **Code**: Always English (variables, functions, comments)

---

*Last updated: 2025-12*
