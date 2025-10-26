# Changelog

All notable changes to LangFlix will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Expression video playback during audio repetition (replaces freeze frames)
- Perfect audio-video synchronization with FFmpeg loop filter
- 40% volume boost for optimal audio quality
- Multiple expression support in short video batches
- Correct video file matching for accurate audio extraction

### Changed
- Short videos now show continuous motion throughout entire duration
- Expression videos loop seamlessly to match audio timeline duration
- Improved video-audio synchronization prevents breaking during repetition

### Fixed
- Expression video duration mismatch with audio timeline
- Incorrect video file selection for audio extraction
- Single expression limitation in short video generation
- Audio-video desynchronization during expression repetition

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
