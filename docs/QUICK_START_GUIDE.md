# LangFlix Quick Start Guide

## Installation (5 minutes)

### Prerequisites Check

```bash
# Verify Python version (3.9+ required, 3.12 recommended)
python --version

# Verify FFmpeg installation
ffmpeg -version
```

### Step 1: Clone and Setup

```bash
# Clone repository
git clone https://github.com/taigi0315/study_english_with_suits.git
cd study_english_with_suits

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 2: Configure API Keys

```bash
# Copy environment template
cp env.example .env

# Edit .env and add your Gemini API key
nano .env
```

Required in `.env`:
```bash
GEMINI_API_KEY=your_actual_api_key_here
```

Get API key: https://aistudio.google.com/

### Step 3: Configure Application

```bash
# Copy configuration template
cp config.example.yaml config.yaml

# Edit config.yaml (optional for first run)
```

---

## Quick Test Run (5 minutes)

### Prepare Test Files

```bash
# Create test directory
mkdir -p assets/media/test

# Copy your video and subtitle files
# Files must have matching names:
# - test.mp4
# - test.srt
```

### Run Test Processing

```bash
# Test mode (2 expressions only)
python -m langflix.main \
  --subtitle "assets/media/test/test.srt" \
  --test-mode \
  --max-expressions 2 \
  --verbose
```

**Expected Output**:
```
INFO: Starting LangFlix Pipeline
INFO: Parsing subtitle file
INFO: Analyzing expressions with Gemini
INFO: Extracted 2 expressions
INFO: Generating videos...
INFO: Processing complete!
```

### Check Results

```bash
# View generated files
ls -la output/test/
```

You should see:
- Context videos with subtitles
- Educational slides
- Final educational videos
- Short format videos (9:16)
- Metadata JSON files

---

## First Real Episode (30 minutes)

### Process Complete Episode

```bash
# Full processing (10-20 expressions)
python -m langflix.main \
  --subtitle "assets/media/Suits/Suits.S01E01.srt" \
  --language-code ko \
  --language-level intermediate \
  --verbose
```

### Monitor Progress

Watch the logs:
```bash
tail -f langflix.log
```

Key stages:
1. ✅ Subtitle parsing
2. ✅ Expression analysis (5-10 seconds per chunk)
3. ✅ WhisperX timestamping (2-3 seconds per minute)
4. ✅ Video slicing (2-5 seconds per expression)
5. ✅ Slide generation (5-10 seconds per expression)
6. ✅ Video composition
7. ✅ Storage and database update

---

## Understanding Output

### Directory Structure

```
output/
├── Suits/
    ├── S01E01/
        ├── shared/
        │   ├── context_videos/        # Expression clips
        │   ├── context_slide_combined/ # Educational videos
        │   └── short_videos/          # Batched shorts
        └── translations/
            └── ko/
                ├── subtitles/
                ├── slides/
                ├── audio/
                └── metadata/
```

### Video Types

**Educational Videos** (16:9 landscape):
```
Context Video (10-25s) → Educational Slide (varies)
```
- Full scene context with target language subtitles
- Expression highlighted in yellow
- Audio: Context audio + TTS (3× repetition)

**Short Videos** (9:16 portrait):
```
Top: Context Video | Bottom: Educational Slide
```
- Optimized for mobile viewing
- Context video freezes during TTS playback
- Batched into ~120-second segments

### Educational Slide Layout (5 sections)

1. **Expression Dialogue** (top, 40px): Full sentence
2. **Expression** (58px, yellow): Key phrase
3. **Dialogue Translation** (middle, 36px): Full translation
4. **Expression Translation** (48px, yellow): Key translation
5. **Similar Expressions** (bottom, 32px): Alternatives

---

## Common Use Cases

### Case 1: Learning from TV Shows

**Goal**: Extract expressions from favorite series

**Steps**:
```bash
# 1. Organize files
assets/media/Suits/
├── Suits.S01E01.mkv
└── Suits.S01E01.srt

# 2. Process episode
python -m langflix.main \
  --subtitle "assets/media/Suits/Suits.S01E01.srt" \
  --language-level intermediate \
  --language-code ko

# 3. Review expressions
cat output/Suits/S01E01/translations/ko/metadata/processing_info.json

# 4. Watch educational videos
open output/Suits/S01E01/translations/ko/context_slide_combined/
```

### Case 2: Creating Social Media Content

**Goal**: Generate short-format videos for Instagram/TikTok

**Steps**:
```bash
# Process with shorts enabled (default)
python -m langflix.main \
  --subtitle "file.srt" \
  --language-level advanced

# Find batched shorts
ls output/*/translations/*/short_videos/batch_*.mkv

# Upload to social media
# Each batch is ~120 seconds, ready for posting
```

### Case 3: Custom Learning Materials

**Goal**: Create targeted content for specific level

**Steps**:
```bash
# For beginners
python -m langflix.main \
  --subtitle "file.srt" \
  --language-level beginner \
  --max-expressions 5

# For advanced learners
python -m langflix.main \
  --subtitle "file.srt" \
  --language-level advanced \
  --max-expressions 10
```

---

## Next Steps

### Learn More

1. **CLI Reference**: Complete command-line options
2. **Configuration Guide**: Advanced settings and customization
3. **API Reference**: Web API usage
4. **Troubleshooting Guide**: Common issues and solutions

### Advanced Topics

- **Performance Optimization**: GPU acceleration, caching
- **Custom Configuration**: Tailored processing settings
- **Batch Processing**: Multiple episodes
- **Cloud Deployment**: Production setup
- **YouTube Integration**: Automated scheduling

### Community

- **GitHub Issues**: Report bugs and request features
- **Documentation**: Read detailed guides
- **Examples**: Sample configurations and workflows

---

## Quick Reference

### Essential Commands

```bash
# Basic processing
python -m langflix.main --subtitle "file.srt"

# Test mode
python -m langflix.main --subtitle "file.srt" --test-mode

# With options
python -m langflix.main \
  --subtitle "file.srt" \
  --language-code ko \
  --language-level intermediate \
  --max-expressions 5
```
