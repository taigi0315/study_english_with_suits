# Audio Module Documentation

## Overview

The `langflix/audio/` module provides audio processing functionality for LangFlix, including audio optimization, original audio extraction, and timeline creation for educational content.

**Last Updated:** 2025-01-30

## Purpose

This module is responsible for:
- Audio quality optimization and enhancement
- Extracting audio segments from original video files
- Creating audio timelines with repetition patterns for educational purposes
- Managing audio format conversions and synchronization

## Key Components

### AudioOptimizer

**Location:** `langflix/audio/audio_optimizer.py`

Advanced audio optimization system that provides:
- Audio normalization to target loudness levels
- Noise reduction
- Dynamic range compression
- Audio quality analysis and metrics

**Key Methods:**

```python
def optimize_audio(
    input_path: str,
    output_path: str,
    optimization_level: str = "medium"
) -> AudioQualityMetrics:
    """
    Optimize audio file for educational content.
    
    Optimization levels:
    - low: Basic loudness normalization
    - medium: Normalization + filtering + compression
    - high: Full enhancement with equalization
    """
```

**Audio Quality Metrics:**
- `loudness_lufs`: Integrated loudness in LUFS
- `peak_db`: Peak level in dB
- `dynamic_range`: Dynamic range
- `noise_floor_db`: Noise floor level
- `frequency_response`: Frequency response data
- `distortion_percent`: Distortion percentage

**Example Usage:**

```python
from langflix.audio.audio_optimizer import AudioOptimizer, AudioOptimizationConfig

config = AudioOptimizationConfig(
    target_loudness=-23.0,
    noise_reduction=0.3,
    enhance_clarity=True
)

optimizer = AudioOptimizer(config)
metrics = optimizer.optimize_audio(
    "input.wav",
    "output.wav",
    optimization_level="medium"
)

print(f"Loudness: {metrics.loudness_lufs} LUFS")
print(f"Peak: {metrics.peak_db} dB")
```

### OriginalAudioExtractor

**Location:** `langflix/audio/original_audio_extractor.py`

Extracts audio segments from original video files when TTS is disabled, creating the same 3x repetition timeline pattern as TTS for consistency.

**Key Methods:**

```python
def extract_expression_audio(
    self, 
    expression: ExpressionAnalysis, 
    output_path: Path, 
    audio_format: str = "wav"
) -> Tuple[Path, float]:
    """
    Extract audio segment for an expression from the original video.
    
    Args:
        expression: ExpressionAnalysis with timestamps
        output_path: Output path for extracted audio
        audio_format: Audio format (wav or mp3)
        
    Returns:
        Tuple of (audio_file_path, duration_in_seconds)
    """
```

```python
def create_audio_timeline(
    self,
    expression: ExpressionAnalysis,
    output_dir: Path,
    expression_index: int = 0,
    audio_format: str = "wav",
    repeat_count: int = None
) -> Tuple[Path, float]:
    """
    Create audio timeline with configurable repetition pattern.
    
    Timeline pattern: 
    1s silence - audio - 0.5s silence - audio - ... - 1s silence (repeat_count times)
    """
```

**Features:**
- Automatic timestamp conversion from SRT format
- Stereo downmixing from 5.1 audio
- Preserves original sample rate (typically 48kHz)
- Configurable repeat count matching TTS behavior

**Example Usage:**

```python
from langflix.audio.original_audio_extractor import OriginalAudioExtractor
from pathlib import Path

extractor = OriginalAudioExtractor("original_video.mp4")
timeline_path, duration = extractor.create_audio_timeline(
    expression,
    output_dir=Path("output/audio"),
    expression_index=0,
    audio_format="wav",
    repeat_count=3
)
```

### Timeline Builder Utilities

**Location:** `langflix/audio/timeline.py`

Low-level utilities for building repeated audio timelines using FFmpeg.

**Key Functions:**

```python
def build_repeated_timeline(
    base_audio_path: Path,
    out_path: Path,
    repeat_count: int,
    start_silence: float = 1.0,
    gap_silence: float = 0.5,
    end_silence: float = 1.0,
) -> Tuple[Path, float]:
    """
    Create timeline: 1s - (segment + 0.5s) * repeat_count - last segment - 1s.
    
    Returns (timeline_path, total_duration_seconds).
    """
```

**Features:**
- All outputs normalized to stereo 48kHz for stable muxing
- Uses FFmpeg concatenation for efficient audio assembly
- Automatic silence generation at correct sample rate

## Implementation Details

### Audio Processing Pipeline

1. **Extraction**: Extract audio segment from video using FFmpeg
2. **Format Conversion**: Convert to target format (WAV/MP3) with proper codec settings
3. **Timeline Creation**: Concatenate audio segments with silence gaps
4. **Optimization** (optional): Apply audio enhancements

### FFmpeg Integration

The module uses FFmpeg for all audio operations:
- Audio extraction: `ffmpeg -ss [start] -i [video] -t [duration] -vn`
- Format conversion: `-c:a pcm_s16le` (WAV) or `-c:a mp3 -b:a 192k` (MP3)
- Concatenation: `ffmpeg -f concat -safe 0 -i [list]`

### Audio Format Handling

- **WAV**: 16-bit PCM, stereo, preserves original sample rate
- **MP3**: 192k bitrate, stereo
- **Sample Rate**: Maintains 48kHz (typical for video audio)
- **Channels**: Downmixes to stereo from 5.1 if needed

## Dependencies

- `subprocess`: FFmpeg command execution
- `pathlib`: Path handling
- `tempfile`: Temporary file management
- `langflix.core.models`: ExpressionAnalysis model
- `langflix.settings`: Configuration access

## Common Tasks

### Extract Audio for Single Expression

```python
from langflix.audio.original_audio_extractor import OriginalAudioExtractor

extractor = OriginalAudioExtractor("video.mp4")
audio_path, duration = extractor.extract_expression_audio(
    expression,
    Path("output/audio.wav"),
    audio_format="wav"
)
```

### Create Timeline with Custom Repeat Count

```python
timeline_path, total_duration = extractor.create_audio_timeline(
    expression,
    output_dir=Path("output"),
    expression_index=0,
    repeat_count=5  # Repeat 5 times
)
```

### Optimize Audio Quality

```python
from langflix.audio.audio_optimizer import get_audio_optimizer

optimizer = get_audio_optimizer()
metrics = optimizer.optimize_audio(
    "input.wav",
    "output.wav",
    optimization_level="high"
)

recommendations = optimizer.get_optimization_recommendations(metrics)
for rec in recommendations:
    print(f"Recommendation: {rec}")
```

## Configuration

Audio settings are controlled through `langflix.settings`:

- `expression.repeat_count`: Number of audio repetitions in timeline
- Audio format preferences
- Sample rate and channel settings

## Gotchas and Notes

1. **Sample Rate Consistency**: Always use 48kHz for video audio to avoid sync issues
2. **Silence Generation**: Silence files must match the audio sample rate exactly
3. **FFmpeg Requirements**: FFmpeg must be installed and available in PATH
4. **File Permissions**: Ensure write permissions for output directories
5. **Temporary Files**: Module uses temporary directories for intermediate processing - ensure sufficient disk space

## Related Modules

- `langflix/core/`: ExpressionAnalysis model
- `langflix/media/`: Video processing utilities
- `langflix/tts/`: TTS audio generation (alternative to original audio)

