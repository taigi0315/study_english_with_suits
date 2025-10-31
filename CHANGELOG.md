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
- Audio timeline module: `langflix/audio/timeline.py`
  - Repeated timeline builder (1.0s start, 0.5s gaps, 1.0s end)
  - Segment extraction to WAV with stereo/48k normalization
- Subtitle overlay module: `langflix/subtitles/overlay.py`
  - Subtitle file discovery, dual-language copy, ASS style builder
  - Drawtext fallback for translation-only overlays
- Slide generator: `langflix/slides/generator.py`
  - Silent slide creation with text layout; no forced 720p/1080p

### Changed
- VideoEditor orchestration updated to use the new modules
  - Context+Slide concatenation switched to explicit filter concat to avoid audio drops
  - Subtitle application routed through overlay helpers for stability

### Fixed
- Intermittent audio loss during concatenation by enforcing explicit stream mapping
- Audio param mismatches by normalizing to stereo (ac=2) and 48kHz (ar=48000)

### Notes
- Video tracks preserve original codec/resolution when possible. Re-encoding occurs only when filters are required.

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
