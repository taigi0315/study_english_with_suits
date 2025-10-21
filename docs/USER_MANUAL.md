# LangFlix User Manual

**Version:** 1.0  
**Last Updated:** October 19, 2025

Welcome to LangFlix! This manual will guide you through everything you need to know to create educational English learning videos from your favorite TV shows.

---

## Table of Contents

1. [Introduction](#introduction)
2. [Getting Started](#getting-started)
3. [Basic Usage](#basic-usage)
4. [Advanced Usage](#advanced-usage)
5. [Configuration](#configuration)
6. [Understanding Output](#understanding-output)
7. [Command Reference](#command-reference)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

---

## Introduction

### What is LangFlix?

LangFlix automatically analyzes TV show subtitles to extract valuable English expressions, idioms, and phrases, then creates educational videos with:
- Context video clips with target language subtitles
- Educational slides with expression breakdowns
- Audio pronunciation with 3x repetition
- Similar expressions and usage examples

### Who is it for?

- Language learners who want to learn from authentic media
- Teachers creating educational content
- Content creators building language learning materials

### System Requirements

- **Python:** 3.9 or higher
- **ffmpeg:** Latest version (for video processing)
- **Storage:** At least 5GB free space per episode
- **API Key:** Google Gemini API key (free tier available)

---

## Getting Started

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/taigi0315/study_english_with_suits.git
cd study_english_with_suits

# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install ffmpeg (if not already installed)
# macOS:
brew install ffmpeg
# Ubuntu/Debian:
sudo apt update && sudo apt install ffmpeg
# Windows:
choco install ffmpeg
```

### 2. Configuration

```bash
# Copy example configuration
cp config.example.yaml config.yaml

# Copy environment file
cp env.example .env

# Edit .env and add your API key
# GEMINI_API_KEY=your_api_key_here
```

### 3. Prepare Media Files

Organize your files in this structure:

```
assets/
└── media/
    └── Suits/                    # Series folder
        ├── Suits.S01E01.720p.HDTV.x264.mkv
        ├── Suits.S01E01.720p.HDTV.x264.srt
        ├── Suits.S01E02.720p.HDTV.x264.mkv
        ├── Suits.S01E02.720p.HDTV.x264.srt
        └── ...
```

**File Requirements:**
- Video and subtitle files must have matching names
- Supported video formats: `.mp4`, `.mkv`, `.avi`, `.mov`
- Subtitle format: `.srt` (UTF-8 encoding recommended)

---

## Basic Usage

### Quick Start: Process One Episode

```bash
python -m langflix.main \
  --subtitle "assets/media/Suits/Suits.S01E01.720p.HDTV.x264.srt" \
  --video-dir "assets/media"
```

This will:
1. Parse the subtitle file
2. Analyze expressions using AI
3. Extract video clips
4. Create educational videos
5. Save everything to `output/` directory

### Check the Results

After processing, you'll find:

```
output/
└── Suits/
    └── S01E01_720p.HDTV.x264/
        ├── shared/
        │   └── video_clips/              # Raw expression clips
        └── translations/
            └── ko/                        # Korean (or your target language)
                ├── context_videos/        # Context clips with subtitles
                ├── slides/                # Educational slides
                ├── final_videos/          # Complete educational sequences
                │   ├── educational_expression_01.mkv
                │   ├── educational_expression_02.mkv
                │   └── final_educational_video_with_slides.mkv  # All combined!
                └── metadata/              # Processing information
```

### Test Mode (Recommended for First Run)

```bash
# Process only first chunk to test setup
python -m langflix.main \
  --subtitle "assets/media/Suits/Suits.S01E01.720p.HDTV.x264.srt" \
  --video-dir "assets/media" \
  --test-mode \
  --max-expressions 2
```

---

## Advanced Usage

### Language Level Selection

Target different proficiency levels:

```bash
# Beginner level (simple, practical expressions)
python -m langflix.main \
  --subtitle "path/to/subtitle.srt" \
  --language-level beginner

# Intermediate level (balanced complexity)
python -m langflix.main \
  --subtitle "path/to/subtitle.srt" \
  --language-level intermediate

# Advanced level (complex idioms and phrases)
python -m langflix.main \
  --subtitle "path/to/subtitle.srt" \
  --language-level advanced

# Mixed level (variety of difficulties)
python -m langflix.main \
  --subtitle "path/to/subtitle.srt" \
  --language-level mixed
```

### Target Language Selection

LangFlix supports multiple target languages:

```bash
# Korean (default)
python -m langflix.main \
  --subtitle "path/to/subtitle.srt" \
  --language-code ko

# Japanese
python -m langflix.main \
  --subtitle "path/to/subtitle.srt" \
  --language-code ja

# Spanish
python -m langflix.main \
  --subtitle "path/to/subtitle.srt" \
  --language-code es
```

**Supported Languages:**
- `ko` - Korean
- `ja` - Japanese
- `zh` - Chinese
- `es` - Spanish
- `fr` - French
- `de` - German
- `pt` - Portuguese
- `vi` - Vietnamese

### Expression Limits

Control how many expressions to extract per chunk:

```bash
# Process specific number of expressions
python -m langflix.main \
  --subtitle "path/to/subtitle.srt" \
  --max-expressions 5

# Process ALL expressions found (default)
python -m langflix.main \
  --subtitle "path/to/subtitle.srt"
```

The system automatically limits expressions per chunk (default: 1-3) based on your configuration.

### Dry Run Mode

Test the analysis without creating videos:

```bash
python -m langflix.main \
  --subtitle "path/to/subtitle.srt" \
  --dry-run
```

This will:
- Parse subtitles
- Analyze expressions with AI
- Save results to JSON
- **Skip** video processing (much faster!)

### Save LLM Output for Review

Debug or review AI decisions:

```bash
python -m langflix.main \
  --subtitle "path/to/subtitle.srt" \
  --save-llm-output
```

LLM responses will be saved to `output/llm_output_*.txt` for manual inspection.

### Custom Output Directory

```bash
python -m langflix.main \
  --subtitle "path/to/subtitle.srt" \
  --output-dir "custom_output"
```

### Verbose Logging

Enable detailed debug logs:

```bash
python -m langflix.main \
  --subtitle "path/to/subtitle.srt" \
  --verbose
```

---

## Configuration

### YAML Configuration File

LangFlix uses `config.yaml` for advanced settings. Copy from example:

```bash
cp config.example.yaml config.yaml
```

### Key Configuration Sections

#### 1. LLM Settings

```yaml
llm:
  max_input_length: 1680        # Characters per chunk
  target_language: "Korean"      # Default target language
  default_language_level: "intermediate"
  temperature: 0.1               # AI creativity (0.0-1.0)
  top_p: 0.8                     # Sampling parameter
  top_k: 40                      # Sampling parameter
  max_retries: 3                 # API retry attempts
  retry_backoff_seconds: 2       # Initial retry delay
```

#### 2. Expression Limits

```yaml
processing:
  min_expressions_per_chunk: 1   # Minimum expressions per chunk
  max_expressions_per_chunk: 3   # Maximum expressions per chunk
```

#### 3. Video Processing

```yaml
video:
  codec: "libx264"               # Video codec
  preset: "fast"                 # Encoding speed/quality
  crf: 23                        # Quality (18-28, lower=better)
  resolution: "1920x1080"        # Output resolution
  frame_rate: 23.976             # Frame rate
```

#### 4. Font Settings

```yaml
font:
  sizes:
    expression: 48               # Expression text size
    translation: 40              # Translation text size
    similar: 32                  # Similar expressions size
    default: 32                  # Default text size
```

#### 5. Transitions

```yaml
transitions:
  enabled: true                  # Enable/disable transitions
  context_to_slide:
    type: "xfade"               # Transition type
    effect: "fade"              # Effect style
    duration: 0.5               # Duration in seconds
```

#### 6. Text-to-Speech (TTS)

LangFlix uses Google Cloud Text-to-Speech for pronunciation audio generation:

```yaml
tts:
  enabled: true                  # Enable/disable TTS audio generation
  provider: "google"             # TTS provider (google, lemonfox)
  
  google:
    language_code: "en-US"       # Original language for audio (English)
    voice_name: "en-US-Wavenet-D" # Default voice (Puck)
    response_format: "mp3"       # Audio format (mp3, wav)
    speaking_rate: 0.75          # Speech speed (0.75 = 75% speed, slower)
    alternate_voices:            # Voice alternation between expressions
      - "en-US-Wavenet-D"        # Puck (male, neutral tone)
      - "en-US-Wavenet-A"        # Leda (female, neutral tone)
```

**TTS Features:**
- **Voice Alternation**: Automatically switches between Puck and Leda voices for each expression
- **Timeline Structure**: 1s pause - TTS - 0.5s pause - TTS - 0.5s pause - TTS - 1s pause
- **Speech Speed**: Configurable slower speech for better learning (75% speed)
- **Original Language**: Uses English (original language) for audio generation, not target language

**Setup Requirements:**
- Google Cloud TTS API key in environment: `GOOGLE_API_KEY_1=your_key_here`
- Add to `.env` file in project root

### Environment Variables

Override configuration with environment variables:

```bash
export LANGFLIX_LLM_MAX_INPUT_LENGTH=2000
export LANGFLIX_VIDEO_CRF=20
export LANGFLIX_TARGET_LANGUAGE="Japanese"
```

Format: `LANGFLIX_<SECTION>_<KEY>=<VALUE>`

---

## Understanding Output

### Output Directory Structure

```
output/
└── [Series]/
    └── [Episode]/
        ├── shared/
        │   └── video_clips/              # Expression clips (no subtitles)
        │       ├── expression_01_[name].mkv
        │       └── expression_02_[name].mkv
        └── translations/
            └── [language_code]/
                ├── context_videos/        # Context with target language subs
                │   ├── context_01_[name].mkv
                │   └── context_02_[name].mkv
                ├── slides/                # Educational slides
                │   ├── slide_01_[name].mkv
                │   └── slide_02_[name].mkv
                ├── subtitles/            # Dual-language subtitle files
                │   ├── expression_01_[name].srt
                │   └── expression_02_[name].srt
                ├── context_slide_combined/ # Individual educational videos
                │   ├── educational_[expression_01].mkv
                │   ├── educational_[expression_02].mkv
                │   ├── short_[expression_01].mkv      # Short format videos (9:16)
                │   └── short_[expression_02].mkv
                ├── final_videos/         # Complete educational sequences
                │   └── final_educational_video_with_slides.mkv
                ├── short_videos/         # Batched short format videos
                │   ├── short_video_001.mkv
                │   └── short_video_002.mkv
                └── metadata/             # Processing metadata
                    └── processing_info.json
```

### Video Structure

Each educational video follows this sequence:

1. **Context Video** (10-25 seconds)
   - Scene context with target language subtitles
   - Natural dialogue flow
   - Expression appears in middle

2. **Educational Slide** (varies)
   - **NEW 5-Section Layout:**
     1. Expression Dialogue (top, 40px) - Full sentence containing the expression
     2. Expression (below dialogue, 58px, yellow highlight) - Key expression/phrase to learn
     3. Expression Dialogue Translation (middle, 36px) - Translation of full sentence
     4. Expression Translation (below dialogue translation, 48px, yellow highlight) - Key phrase translation
     5. Similar Expressions (bottom, 32px, max 2) - Alternative ways to say the same thing
   - Audio: Full dialogue + expression repeated 3 times

3. **Next Expression** (repeat pattern)

### Short Format Videos (9:16 Aspect Ratio)

Short format videos are optimized for social media platforms and follow this structure:

1. **Total Duration**: `context_duration + (TTS_duration × 2) + 0.5s`
   - Example: Context (7.2s) + TTS×2 (2.8s) + gap (0.5s) = **10.5s total**

2. **Layout**:
   - **Top half**: Context video with subtitles
     - Plays normally for original context duration
     - Freezes on last frame for remaining duration
   - **Bottom half**: Educational slide (silent, displays throughout entire video)
     - **NEW 5-Section Layout:** Expression dialogue, highlighted expression, dialogue translation, highlighted expression translation, and similar expressions
     - No audio (context audio + TTS audio only)

3. **Audio Timeline**:
   - Context audio plays during video portion
   - After context ends: TTS audio plays twice with 0.5s gap between repetitions
   - Total audio length matches video length

4. **Batching**: Individual short videos are automatically batched into ~120-second segments in the `short_videos/` folder for easier social media posting.

### Metadata Files

The `metadata/processing_info.json` contains:

```json
{
  "series_name": "Suits",
  "episode_name": "S01E01_720p.HDTV.x264",
  "language_code": "ko",
  "total_expressions": 5,
  "processing_date": "2025-10-19T10:30:00",
  "expressions": [
    {
      "id": 1,
      "expression": "the ball's in your court",
      "translation": "이제 당신이 결정할 차례입니다",
      "context_start": "00:05:23,456",
      "context_end": "00:05:35,789",
      "scene_type": "confrontation"
    }
  ]
}
```

---

## Command Reference

### Main Command

```bash
python -m langflix.main [OPTIONS]
```

### Required Arguments

| Argument | Description |
|----------|-------------|
| `--subtitle PATH` | Path to subtitle file (.srt) |

### Optional Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `--video-dir PATH` | `assets/media` | Directory containing video files |
| `--output-dir PATH` | `output` | Output directory for results |
| `--language-code CODE` | `ko` | Target language code (ko, ja, es, etc.) |
| `--language-level LEVEL` | `intermediate` | Language level (beginner/intermediate/advanced/mixed) |
| `--max-expressions N` | None | Maximum expressions to process (None = all) |
| `--test-mode` | False | Process only first chunk for testing |
| `--dry-run` | False | Analysis only, no video processing |
| `--save-llm-output` | False | Save LLM responses to files |
| `--no-shorts` | False | Skip creating short-format videos (shorts enabled by default) |
| `--verbose` | False | Enable debug logging |

### Examples

```bash
# Basic usage
python -m langflix.main --subtitle "file.srt"

# Full customization
python -m langflix.main \
  --subtitle "assets/media/Suits/Suits.S01E01.srt" \
  --video-dir "assets/media" \
  --output-dir "my_output" \
  --language-code ja \
  --language-level advanced \
  --max-expressions 10 \
  --save-llm-output \
  --verbose

# Quick test
python -m langflix.main \
  --subtitle "file.srt" \
  --test-mode \
  --max-expressions 2

# Analysis only
python -m langflix.main \
  --subtitle "file.srt" \
  --dry-run

# Skip short videos
python -m langflix.main \
  --subtitle "file.srt" \
  --no-shorts \
  --verbose
```

---

## Best Practices

### 1. Start Small

- Use `--test-mode` and `--max-expressions 2` for first runs
- Verify output quality before processing full episodes
- Test with different language levels to find best fit

### 2. Optimize Performance

- Process one episode at a time for stability
- Use `--dry-run` to test expressions before video processing
- Monitor disk space (videos can be large)

### 3. Quality Control

- Review LLM output with `--save-llm-output`
- Check first few expressions for quality
- Adjust `language_level` if expressions are too easy/hard

### 4. File Organization

- Keep consistent naming: `Series.S01E01.quality.format.ext`
- Store subtitles next to video files
- Use series-specific folders

### 5. Configuration Management

- Create separate config files for different use cases
- Use environment variables for API keys (never commit!)
- Back up your config.yaml after tuning

### 6. Resource Management

- Close other applications during video processing
- Ensure 5GB+ free space per episode
- Use `test-mode` to verify before full processing

---

## Troubleshooting

For detailed troubleshooting, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

### Quick Fixes

**Problem:** API timeout errors
```bash
# Reduce chunk size in config.yaml
llm:
  max_input_length: 1680  # Try lower if timeouts persist
```

**Problem:** Video not found
```bash
# Ensure video and subtitle have matching names
# Use --video-dir to specify directory
python -m langflix.main --subtitle "file.srt" --video-dir "path/to/videos"
```

**Problem:** Out of memory
```bash
# Process fewer expressions at once
python -m langflix.main --subtitle "file.srt" --max-expressions 5
```

**Problem:** Poor expression quality
```bash
# Adjust language level
python -m langflix.main --subtitle "file.srt" --language-level advanced
```

### Getting Help

1. Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed solutions
2. Review logs in `langflix.log`
3. Use `--verbose` flag for detailed debug information
4. Check [GitHub Issues](https://github.com/taigi0315/study_english_with_suits/issues)

---

## Next Steps

- Read [API Reference](API_REFERENCE.md) for programmatic usage
- See [DEPLOYMENT.md](DEPLOYMENT.md) for production setup
- Check [PERFORMANCE.md](PERFORMANCE.md) for optimization tips
- Review [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for common issues

---

**Happy Learning! 🎓**

*For the Korean version of this manual, see [USER_MANUAL_KOR.md](USER_MANUAL_KOR.md)*

