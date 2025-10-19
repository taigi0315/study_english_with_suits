# LangFlix — Final System Design & Development Plan

> Consolidated and finalised system design and phased development plan for the LangFlix educational video pipeline. This document synthesises the provided English and Korean plans and the Educational Video Terminology into one actionable plan.

---

## 1. Project Summary (one-liner)

LangFlix converts raw video + subtitle files into short, language-learning educational videos composed of: Context Video → Expression Repeat Clip → Educational Slide (multi-language support, configurable pipeline).

---

## 2. High-level architecture

A modular, local-first pipeline executed from CLI. Key flow:

```
Raw Video (.mp4) + Subtitles (.srt/.vtt)
    → main controller (CLI)
    → subtitle parser
    → expression analyzer (LLM)
    → video processor (ffmpeg)
    → output/Series/Episode/<lang>/final_video.mp4 + metadata.json
```

External services: LLM API (e.g., OpenAI) for content extraction and localization; otherwise processing is local (ffmpeg, Pillow etc.).

---

## 3. Components & responsibilities

### 3.1 main.py (Orchestrator)

* Accepts CLI args / config file: input video, subtitle, target languages, output path, mode (dry-run / full-run), logging level.
* Validates inputs and environment (ffmpeg availability, API key presence if required).
* Invokes pipeline modules in sequence and coordinates retries / error handling.

### 3.2 subtitle_parser.py

* Parses `.srt` and `.vtt` into canonical subtitle objects: `{index, start_time, end_time, text}`.
* Normalises timestamps to a consistent ISO-like format / seconds.fraction.
* Provides utilities: join adjacent short/subsplit lines, merge overlapping ranges, map dialogue turns to speaker if available.
* Unit tests for different subtitle encodings/formats.

### 3.3 expression_analyzer.py (LLM integration)

* Groups subtitles into scene chunks suitable for extracting expressions and context (configurable chunk size / silence threshold).
* Builds clear, structured prompts to the LLM requesting JSON output that contains learning cards. Each learning card includes:

  ```json
  {
    "expression": "...",
    "context_start_time": "...",
    "context_end_time": "...",
    "repeat_start_time": "...",
    "repeat_end_time": "...",
    "definition": "...",
    "translations": {"ko": "...", ...},
    "notes": "...",
    "examples": ["..."],
    "confidence": 0.0
  }
  ```
* Performs schema validation and sanitisation of LLM output. Fall back to heuristics when the LLM fails.
* Dry-run mode: produce JSON without invoking video processing.

### 3.4 video_processor.py

* Responsibilities:

  * Extract context clip for each card (`[context_start_time, context_end_time]`).
  * Create expression repeat clip (expression audio/video repeated 3×).
  * Render educational slide (image -> short clip) containing expression, translation, and optional example sentence with audio.
  * Concatenate: Context Video → Expression Repeat Clip → Educational Slide.
  * Ensure consistent resolution (default 1280×720), framerate (23.98 fps), codecs (H.264/AAC), audio normalization.
* Implementation details:

  * Use `ffmpeg-python` or call `ffmpeg` CLI for reliability.
  * Use `Pillow` to render slides; convert slide images to short silent video and overlay TTS or original audio when required.
  * Store intermediate clips in per-episode temp folder for debugging and reassembly.

### 3.5 i18n & localization

* Centralized translations per episode in `translations/<lang>/`.
* Font support and fallback per language.
* Template-based slide layouts for each language.

### 3.6 metadata & outputs

* Produce `metadata.json` per generated video with learning card indices, timestamps, durations, used fonts, LLM prompt snapshot (for reproducibility), and checksums for inputs.
* Folder layout:

```
output/
└─ Series/
   └─ Episode001/
      ├─ shared/
      ├─ translations/
      │  ├─ ko/
      │  ├─ ja/
      │  └─ ...
      └─ metadata.json
```

---

## 4. Data models (canonical)

* **SubtitleEntry**: `{index:int, start_sec:float, end_sec:float, text:str}`
* **LearningCard** (validated): `{id:int, expression:str, context_start_sec:float, context_end_sec:float, repeat_start_sec:float, repeat_end_sec:float, definition:str, translations:dict, examples:list, tags:list, quality_score:float}`

---

## 5. Phased Development Plan & Deliverables (phases/milestones)

> Deliverables are concrete module outputs; no time estimates are enforced in this document — focus on order of implementation and acceptance criteria.

### Phase 1 — Core pipeline & LLM extraction

**Deliverables:**

* Project skeleton and `requirements.txt`.
* `subtitle_parser` with unit tests + canonicalised subtitle outputs.
* `expression_analyzer` that produces validated `metadata.json` / `learning_cards.json` in dry-run mode.
* Logging and error handling basics.

**Acceptance criteria:** Given `video.mp4` + `subs.srt`, the system emits `learning_cards.json` with ≥1 validated learning card per detected expression, and unit tests pass.

### Phase 2 — Video clip extraction & card assets

**Deliverables:**

* `video_processor` that extracts context clips and stores them.
* Title/slide image renderer and converter to short clip.
* Expression repeat generator (audio/video repeated 3×, synced).
* Concatenation routine producing a single MP4 per episode.

**Acceptance criteria:** For a sample episode, pipeline produces a final MP4 where each expression section follows: Context → 3× Expression → Slide, and video plays with no glitches.

### Phase 3 — Usability, configuration, localization, polish

**Deliverables:**

* Robust CLI (`click` recommended) supporting target language, dry-run, and selective re-run of phases.
* `.env` support for API keys and config.
* Documentation (`README.md`, examples, prompt templates).
* Improvements: audio leveling, transitions, subtitle burn-in option, batch processing mode.

**Acceptance criteria:** Non-developer can run the pipeline with minimal steps and produce localized outputs for at least two languages.

### Phase 4 — Testing, monitoring & maintenance

**Deliverables:**

* End-to-end integration tests (sample videos).
* Smoke tests for LLM outputs and ffmpeg operations.
* CI pipeline configuration (GitHub Actions / similar) to run unit + integration tests.
* Maintenance notes (how to update prompts, swap LLM, update ffmpeg settings).

**Acceptance criteria:** CI runs tests automatically on PRs and key workflows are covered by tests.

---

## 6. Technology stack (recommended)

* **Language:** Python 3.9+
* **Subtitle parsing:** `pysrt` or `webvtt-py`
* **LLM client:** `openai` (or pluggable adapter for other LLMs)
* **Video:** `ffmpeg` (invoked via `ffmpeg-python` or shell)
* **Image rendering:** `Pillow`
* **TTS (optional):** local TTS or cloud TTS for slide audio
* **CLI:** `click` (better UX) or `argparse`
* **Env management:** `python-dotenv`
* **Testing:** `pytest`
* **Packaging / CI:** standard Git + GitHub Actions

---

## 7. Quality, testing & validation

* Unit tests for parser, timestamp conversions, and small helper functions.
* Schema validation for LLM JSON outputs (reject and log malformed responses, attempt re-prompt with stricter schema).
* Integration tests with short sample videos.
* Manual QA checklist for output video (timing correctness, audio sync, text legibility across languages).

---

## 8. Operational considerations

* **Local-first processing:** avoid shipping raw media to cloud unless user opts in.
* **Privacy:** never log full subtitle text or PII to central logs; redact or hash if storing.
* **Resource usage:** keep temp working directory per run and provide `--clean` option to delete intermediates.
* **Extensibility:** design LLM adapter interface and abstraction layer for alternate models.

---

## 9. Risks & mitigations

* **LLM output variability:** validate schema and provide clear re-prompting + fallback heuristics.
* **Timestamp imprecision:** allow padding on context windows and provide manual timestamp overrides in metadata.
* **ffmpeg compatibility across platforms:** detect ffmpeg in PATH and document installation steps.

---

## 10. Next steps & recommended immediate actions

1. Initialize repository with skeleton, requirements, and CI config.
2. Implement `subtitle_parser` and write unit tests (Phase 1 start).
3. Design LLM prompt templates and a simple adapter returning the expected JSON shape (dry-run).
4. Prepare a small sample video + .srt to be used as an integration test fixture for Phase 2.

---

## 11. Appendix

* **Educational video sequence** (canonical): Context Video → Expression Repeat Clip (×3) → Educational Slide (audio + 3s pause). See terminology file for durations and media settings.
* **Recommended media defaults:** 1280×720, H.264, AAC, 23.98 fps.

---

*End of plan.*
