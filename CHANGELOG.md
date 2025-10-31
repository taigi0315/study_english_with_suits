# Changelog

All notable changes to LangFlix will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Media pipeline utilities: `langflix/media/ffmpeg_utils.py`
  - Safe ffprobe wrappers, explicit stream mapping outputs
  - Concat filter helper with v=1,a=1 mapping to prevent audio loss
  - hstack/vstack helpers preserving source dimensions (no forced scaling)
  - **TICKET-001:** `repeat_av_demuxer()` - demuxer-based expression repetition for maximum reliability
  - **TICKET-001:** `concat_demuxer_if_uniform()` - demuxer concat with copy mode for timestamp preservation
  - **TICKET-001:** `apply_final_audio_gain()` - separate final audio gain pass (+25%)
  - **TICKET-001:** `get_duration_seconds()` - duration measurement helper
- Audio timeline module: `langflix/audio/timeline.py`
  - Repeated timeline builder (1.0s start, 0.5s gaps, 1.0s end)
  - Segment extraction to WAV with stereo/48k normalization
- Subtitle overlay module: `langflix/subtitles/overlay.py`
  - Subtitle file discovery, dual-language copy, ASS style builder
  - Drawtext fallback for translation-only overlays
- Slide generator: `langflix/slides/generator.py`
  - Silent slide creation with text layout; no forced 720p/1080p
  - **TICKET-001:** Optional `target_duration` parameter for duration matching

### Changed
- VideoEditor orchestration updated to use the new modules
  - Context+Slide concatenation switched to explicit filter concat to avoid audio drops
  - Subtitle application routed through overlay helpers for stability
  - **TICKET-001:** Long-form layout changed from concat to hstack (side-by-side)
  - **TICKET-001:** Long-form now includes expression repetition on left side
  - **TICKET-001:** Short-form logic simplified (~180 lines removed) to match long-form pattern
  - **TICKET-001:** Both formats now use identical logic (only difference: vstack vs hstack)
  - **TICKET-001:** Short-form reuses long-form's intermediate files for consistency
  - **TICKET-001:** Both formats use same source video (`context_with_subtitles`)

### Fixed
- Intermittent audio loss during concatenation by enforcing explicit stream mapping
- Audio param mismatches by normalizing to stereo (ac=2) and 48kHz (ar=48000)
- **TICKET-001:** Expression repeat audio drop fixed (demuxer-based repetition)
- **TICKET-001:** Long-form missing slide on right side (now uses hstack)
- **TICKET-001:** Long-form missing expression repeat (now included on left side)
- **TICKET-001:** Short-form audio drop in expression repeat (now reuses long-form files)
- **TICKET-001:** Short-form missing first expression (sanitization mismatch fixed)
- **TICKET-001:** Short-form A-V sync lag between segments (demuxer concat with copy mode)
- **TICKET-001:** Short-form A-V sync delay (0.5s delay fixed by simplifying logic)
- **TICKET-001:** Context file conflicts (now checks and reuses existing files)
- **TICKET-001:** Short-form using different source video (now uses same as long-form)

### Notes
- Video tracks preserve original codec/resolution when possible. Re-encoding occurs only when filters are required.
- **TICKET-001:** Demuxer-first approach significantly improves reliability compared to filter-based repetition
- **TICKET-001:** Both long-form and short-form now follow identical pipeline pattern (only layout differs)

## [1.0.0] - 2025-10-25

### Added
- Complete short video generation system (9:16 vertical format)
- Context video + Educational slide split layout
- Automatic batching system (~120 seconds per batch)
- Expression video extraction and concatenation
- Audio timeline with context + expression audio
- Volume enhancement and quality optimization
- Error handling with graceful fallback to freeze frames

### Technical Details
- FFmpeg-based video processing pipeline
- Subtitle-based video file matching
- Configurable repetition count for expression audio
- High-quality encoding (1500+ kbps bitrate)
- Stereo audio output (48kHz, 16-bit)

### Documentation
- Updated ADR-006 with recent enhancements
- Comprehensive implementation timeline
- Technical architecture documentation
- Usage examples and configuration guides
