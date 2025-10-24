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

## CLI Mode Usage Patterns

### Basic Commands

```bash
# Standard processing
python -m langflix.main --subtitle "file.srt"

# With language selection
python -m langflix.main \
  --subtitle "file.srt" \
  --language-code ja \
  --language-level advanced

# Skip short videos
python -m langflix.main \
  --subtitle "file.srt" \
  --no-shorts

# Dry run (analysis only, no videos)
python -m langflix.main \
  --subtitle "file.srt" \
  --dry-run
```

### Common Workflows

**Learning Different Levels**:
```bash
# Beginner: Simple, practical expressions
python -m langflix.main --subtitle "file.srt" --language-level beginner

# Advanced: Complex idioms and phrases
python -m langflix.main --subtitle "file.srt" --language-level advanced
```

**Target Different Languages**:
```bash
# Korean
python -m langflix.main --subtitle "file.srt" --language-code ko

# Japanese
python -m langflix.main --subtitle "file.srt" --language-code ja

# Spanish
python -m langflix.main --subtitle "file.srt" --language-code es
```

**Control Processing**:
```bash
# Limit expressions
python -m langflix.main --subtitle "file.srt" --max-expressions 5

# Test mode (first chunk only)
python -m langflix.main --subtitle "file.srt" --test-mode

# Save LLM output for review
python -m langflix.main --subtitle "file.srt" --save-llm-output
```

---

## API Mode Setup (15 minutes)

### Database Setup

```bash
# Install PostgreSQL (if not already)
brew install postgresql  # macOS
sudo apt install postgresql  # Ubuntu

# Create database
createdb langflix

# Run migrations
alembic upgrade head
```

### Start API Server

```bash
# Development mode
uvicorn langflix.api.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn langflix.api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Test API

```bash
# Health check
curl http://localhost:8000/health

# View API docs
open http://localhost:8000/docs
```

### Submit Processing Job

```bash
# Create job via API
curl -X POST "http://localhost:8000/api/v1/jobs" \
  -F "video_file=@video.mp4" \
  -F "subtitle_file=@subtitle.srt" \
  -F "language_code=en" \
  -F "show_name=Suits" \
  -F "episode_name=S01E01"

# Response:
# {"job_id": "uuid", "status": "PENDING"}

# Check status
curl "http://localhost:8000/api/v1/jobs/{job_id}"

# Get results
curl "http://localhost:8000/api/v1/jobs/{job_id}/expressions"
```

---

## Understanding Output

### Directory Structure

```
output/
â""â"€â"€ Suits/
    â""â"€â"€ S01E01/
        â"œâ"€â"€ shared/
        â"‚   â"œâ"€â"€ context_videos/        # Expression clips
        â"‚   â"œâ"€â"€ context_slide_combined/ # Educational videos
        â"‚   â""â"€â"€ short_videos/          # Batched shorts
        â""â"€â"€ translations/
            â""â"€â"€ ko/
                â"œâ"€â"€ subtitles/
                â"œâ"€â"€ slides/
                â"œâ"€â"€ audio/
                â""â"€â"€ metadata/
```

### Video Types

**Educational Videos** (16:9 landscape):
```
Context Video (10-25s) â†' Educational Slide (varies)
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
â"œâ"€â"€ Suits.S01E01.mkv
â""â"€â"€ Suits.S01E01.srt

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

### Case 4: YouTube Channel Automation

**Goal**: Schedule automated uploads

**Steps**:
```bash
# 1. Start API server
uvicorn langflix.api.main:app --host 0.0.0.0 --port 8000

# 2. Login to YouTube
curl -X POST http://localhost:8000/api/youtube/login

# 3. Get next available time
curl "http://localhost:8000/api/schedule/next-available?video_type=final"

# 4. Schedule upload
curl -X POST http://localhost:8000/api/upload/schedule \
  -H "Content-Type: application/json" \
  -d '{
    "video_path": "/path/to/video.mp4",
    "video_type": "final"
  }'
```

---

## Troubleshooting Quick Fixes

### "GEMINI_API_KEY not found"

```bash
# Check if .env exists
cat .env | grep GEMINI_API_KEY

# If missing, add it
echo "GEMINI_API_KEY=your_key_here" >> .env
```

### "ffmpeg not found"

```bash
# Install FFmpeg
brew install ffmpeg  # macOS
sudo apt install ffmpeg  # Ubuntu

# Verify
ffmpeg -version
```

### "Video file not found"

```bash
# Ensure matching filenames
ls -la assets/media/

# Files must match exactly:
# video.mp4 â†' video.srt
```

### "Out of memory"

```bash
# Process fewer expressions
python -m langflix.main \
  --subtitle "file.srt" \
  --max-expressions 3

# Or use test mode
python -m langflix.main \
  --subtitle "file.srt" \
  --test-mode
```

### "API timeout"

```bash
# Reduce chunk size in config.yaml
llm:
  max_input_length: 1200  # Reduce from 1680
```

### Processing too slow

```bash
# Enable GPU acceleration (if available)
# Edit config.yaml:
video:
  hardware_acceleration: "cuda"
  codec: "h264_nvenc"

whisper:
  device: cuda
```

---

## Next Steps

### Learn More

1. **User Manual**: Complete feature documentation
2. **API Reference**: Endpoint specifications
3. **Configuration Guide**: Advanced settings
4. **Troubleshooting**: Comprehensive solutions

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


# LangFlix Configuration Reference

## Overview

LangFlix uses a multi-layered configuration system with the following priority (highest to lowest):

1. **CLI Arguments** (highest priority)
2. **Environment Variables**
3. **config.yaml File**
4. **Default Values** (lowest priority)

---

## Configuration File Structure

### Main Configuration File: `config.yaml`

```yaml
# Application Settings
app:
  show_name: "Suits"
  language_code: "en"
  target_language: "Korean"
  template_file: "expression_analysis_prompt.txt"

# Database Configuration
database:
  enabled: true
  url: "postgresql://user:password@localhost:5432/langflix"
  pool_size: 10
  max_overflow: 20
  echo: false  # Set true for SQL debugging

# Storage Configuration
storage:
  backend: "local"  # "local" or "gcs"
  local:
    base_path: "output"
  gcs:
    bucket_name: "langflix-storage"
    credentials_path: "service-account.json"

# LLM Configuration
llm:
  provider: "gemini"
  model: "gemini-1.5-pro"
  api_key: "${GEMINI_API_KEY}"  # From environment
  temperature: 0.7
  top_p: 0.8
  top_k: 40
  max_input_length: 1680
  chunk_size: 50
  overlap: 5
  max_retries: 5
  retry_backoff_seconds: 3
  timeout: 120
  
  # Expression Extraction
  extraction:
    max_expressions_per_chunk: 5
    min_difficulty: 1
    max_difficulty: 10
    categories:
      - idiom
      - slang
      - formal
      - greeting
      - cultural
  
  # Ranking System
  ranking:
    difficulty_weight: 0.4
    frequency_weight: 0.3
    educational_value_weight: 0.3
    fuzzy_match_threshold: 85

# WhisperX Configuration
whisper:
  model_size: "base"  # tiny, base, small, medium, large-v2
  device: "cpu"       # cpu, cuda
  compute_type: "float32"  # float32, float16, int8
  language: null      # null for auto-detect
  fuzzy_threshold: 0.85
  buffer_start: 0.2
  buffer_end: 0.2
  cache_dir: "./cache/audio"
  batch_size: 16
  sample_rate: 16000
  channels: 1
  format: "wav"
  timeout: 300

# Video Processing
video:
  codec: "libx264"
  preset: "medium"    # ultrafast, fast, medium, slow, veryslow
  crf: 20            # 18-28, lower = better quality
  resolution: "1920x1080"
  frame_rate: 23.976
  hardware_acceleration: null  # null, cuda, qsv, vaapi
  thread_count: 0    # 0 = auto
  
  # Quality presets
  quality_presets:
    low:
      crf: 28
      preset: "veryfast"
    medium:
      crf: 23
      preset: "medium"
    high:
      crf: 18
      preset: "slow"
    lossless:
      crf: 0
      preset: "veryslow"

# Audio Processing
audio:
  codec: "aac"
  bitrate: "192k"
  sample_rate: 48000
  channels: 2
  normalize: true

# TTS Configuration
tts:
  enabled: true
  provider: "google"
  repeat_count: 2
  
  google:
    language_code: "en-us"
    model_name: "gemini-2.5-flash-preview-tts"
    response_format: "wav"
    speaking_rate: "slow"  # x-slow, slow, medium, fast, x-fast
    pitch: "-4st"          # Semitones: -20st to +20st
    alternate_voices:
      - "Despina"
      - "Puck"
      - "Kore"

# Media Processing
media:
  slicing:
    quality: "high"  # low, medium, high, lossless
    buffer_start: 0.2
    buffer_end: 0.2
    output_format: "mp4"
  
  subtitles:
    style: "expression_highlight"
    font_size: 24
    font_color: "#FFFFFF"
    background_color: "#000000"
    highlight_color: "#FFD700"
    encoding: "utf-8"

# Slide Generation
slides:
  templates:
    expression:
      background_color: "#1a1a1a"
      text_color: "#ffffff"
      font_family: "DejaVu Sans"
      font_size: 48
      title_font_size: 72
    usage:
      background_color: "#2d2d2d"
      text_color: "#ffffff"
      font_family: "DejaVu Sans"
      font_size: 36
    cultural:
      background_color: "#1a3a4a"
      text_color: "#ffffff"
      font_family: "DejaVu Sans"
      font_size: 40
    grammar:
      background_color: "#3a1a2a"
      text_color: "#ffffff"
      font_family: "DejaVu Sans"
      font_size: 38
    pronunciation:
      background_color: "#2a3a1a"
      text_color: "#ffffff"
      font_family: "DejaVu Sans Mono"

# LangFlix Configuration Reference

## Overview

LangFlix uses a multi-layered configuration system with the following priority (highest to lowest):

1. **CLI Arguments** (highest priority)
2. **Environment Variables**
3. **config.yaml File**
4. **Default Values** (lowest priority)

---

## Configuration File Structure

### Main Configuration File: `config.yaml`

```yaml
# Application Settings
app:
  show_name: "Suits"
  language_code: "en"
  target_language: "Korean"
  template_file: "expression_analysis_prompt.txt"

# Database Configuration
database:
  enabled: true
  url: "postgresql://user:password@localhost:5432/langflix"
  pool_size: 10
  max_overflow: 20
  echo: false  # Set true for SQL debugging

# Storage Configuration
storage:
  backend: "local"  # "local" or "gcs"
  local:
    base_path: "output"
  gcs:
    bucket_name: "langflix-storage"
    credentials_path: "service-account.json"

# LLM Configuration
llm:
  provider: "gemini"
  model: "gemini-1.5-pro"
  api_key: "${GEMINI_API_KEY}"  # From environment
  temperature: 0.7
  top_p: 0.8
  top_k: 40
  max_input_length: 1680
  chunk_size: 50
  overlap: 5
  max_retries: 5
  retry_backoff_seconds: 3
  timeout: 120
  
  # Expression Extraction
  extraction:
    max_expressions_per_chunk: 5
    min_difficulty: 1
    max_difficulty: 10
    categories:
      - idiom
      - slang
      - formal
      - greeting
      - cultural
  
  # Ranking System
  ranking:
    difficulty_weight: 0.4
    frequency_weight: 0.3
    educational_value_weight: 0.3
    fuzzy_match_threshold: 85

# WhisperX Configuration
whisper:
  model_size: "base"  # tiny, base, small, medium, large-v2
  device: "cpu"       # cpu, cuda
  compute_type: "float32"  # float32, float16, int8
  language: null      # null for auto-detect
  fuzzy_threshold: 0.85
  buffer_start: 0.2
  buffer_end: 0.2
  cache_dir: "./cache/audio"
  batch_size: 16
  sample_rate: 16000
  channels: 1
  format: "wav"
  timeout: 300

# Video Processing
video:
  codec: "libx264"
  preset: "medium"    # ultrafast, fast, medium, slow, veryslow
  crf: 20            # 18-28, lower = better quality
  resolution: "1920x1080"
  frame_rate: 23.976
  hardware_acceleration: null  # null, cuda, qsv, vaapi
  thread_count: 0    # 0 = auto
  
  # Quality presets
  quality_presets:
    low:
      crf: 28
      preset: "veryfast"
    medium:
      crf: 23
      preset: "medium"
    high:
      crf: 18
      preset: "slow"
    lossless:
      crf: 0
      preset: "veryslow"

# Audio Processing
audio:
  codec: "aac"
  bitrate: "192k"
  sample_rate: 48000
  channels: 2
  normalize: true

# TTS Configuration
tts:
  enabled: true
  provider: "google"
  repeat_count: 2
  
  google:
    language_code: "en-us"
    model_name: "gemini-2.5-flash-preview-tts"
    response_format: "wav"
    speaking_rate: "slow"  # x-slow, slow, medium, fast, x-fast
    pitch: "-4st"          # Semitones: -20st to +20st
    alternate_voices:
      - "Despina"
      - "Puck"
      - "Kore"

# Media Processing
media:
  slicing:
    quality: "high"  # low, medium, high, lossless
    buffer_start: 0.2
    buffer_end: 0.2
    output_format: "mp4"
  
  subtitles:
    style: "expression_highlight"
    font_size: 24
    font_color: "#FFFFFF"
    background_color: "#000000"
    highlight_color: "#FFD700"
    encoding: "utf-8"

# Slide Generation
slides:
  templates:
    expression:
      background_color: "#1a1a1a"
      text_color: "#ffffff"
      font_family: "DejaVu Sans"
      font_size: 48
      title_font_size: 72
    usage:
      background_color: "#2d2d2d"
      text_color: "#ffffff"
      font_family: "DejaVu Sans"
      font_size: 36
    cultural:
      background_color: "#1a3a4a"
      text_color: "#ffffff"
      font_family: "DejaVu Sans"
      font_size: 40
    grammar:
      background_color: "#3a1a2a"
      text_color: "#ffffff"
      font_family: "DejaVu Sans"
      font_size: 38
    pronunciation:
      background_color: "#2a3a1a"
      text_color: "#ffffff"
      font_family: "DejaVu Sans Mono"

# LangFlix Troubleshooting Guide

## Quick Diagnosis

### System Health Check

Run this command to check all components:

```bash
# Comprehensive health check
python -m langflix.diagnostics --full

# Or manually check each component:
python --version                    # Check Python version
ffmpeg -version                     # Check FFmpeg
echo $GEMINI_API_KEY               # Check API key
psql langflix -c "SELECT 1;"       # Check database
curl http://localhost:8000/health  # Check API
```

---

## Common Issues by Category

### Installation & Setup Issues

#### Issue: "ModuleNotFoundError: No module named 'langflix'"

**Symptoms**:
```
ModuleNotFoundError: No module named 'langflix'
```

**Causes**:
- Virtual environment not activated
- Dependencies not installed
- Running from wrong directory

**Solutions**:

1. Activate virtual environment:
```bash
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run from project root:
```bash
cd /path/to/study_english_with_suits
python -m langflix.main --subtitle "file.srt"
```

4. Verify installation:
```bash
python -c "import langflix; print(langflix.__version__)"
```

---

#### Issue: "ffmpeg: command not found"

**Symptoms**:
```
FileNotFoundError: [Errno 2] No such file or directory: 'ffmpeg'
```

**Solutions**:

**macOS**:
```bash
brew install ffmpeg
```

**Ubuntu/Debian**:
```bash
sudo apt update
sudo apt install ffmpeg
```

**Windows**:
```bash
# Using Chocolatey
choco install ffmpeg

# Or download from https://ffmpeg.org/download.html
# Add to PATH
```

**Verify**:
```bash
ffmpeg -version
which ffmpeg  # Linux/macOS
where ffmpeg  # Windows
```

---

#### Issue: "GEMINI_API_KEY not found"

**Symptoms**:
```
Error: GEMINI_API_KEY environment variable not set
KeyError: 'GEMINI_API_KEY'
```

**Solutions**:

1. Create `.env` file:
```bash
cp env.example .env
nano .env
```

2. Add API key:
```bash
GEMINI_API_KEY=your_actual_api_key_here
```

3. Get API key:
- Visit https://aistudio.google.com/
- Sign in with Google account
- Create new API key

4. Verify:
```bash
echo $GEMINI_API_KEY
cat .env | grep GEMINI_API_KEY
```

---

### Processing Issues

#### Issue: API Timeout (504 Gateway Timeout)

**Symptoms**:
```
Error: 504 Gateway Timeout
Gemini API request timed out
TimeoutError: Request exceeded 120 seconds
```

**Causes**:
- Input chunk too large
- Network connectivity issues
- API server overload
- Firewall blocking requests

**Solutions**:

1. Reduce chunk size:
```yaml
# config.yaml
llm:
  max_input_length: 1200  # Reduce from 1680
  chunk_size: 30          # Reduce from 50
  timeout: 180            # Increase timeout
```

2. Check network:
```bash
ping google.com
curl https://generativelanguage.googleapis.com
```

3. Test with smaller input:
```bash
python -m langflix.main \
  --subtitle "file.srt" \
  --test-mode \
  --max-expressions 1
```

4. Check API status:
```bash
curl -I https://generativelanguage.googleapis.com
```

---

#### Issue: "MAX_TOKENS" Finish Reason

**Symptoms**:
```
Warning: LLM response ended with MAX_TOKENS
Response may be incomplete
```

**Causes**:
- Output exceeds token limit (2048 tokens)
- Too many expressions requested
- Complex prompt

**Solutions**:

1. Reduce expressions per chunk:
```yaml
processing:
  max_expressions_per_chunk: 2  # Reduce from 3-4
```

2. Simplify prompt template:
```yaml
llm:
  max_input_length: 1200
```

3. Process fewer subtitles:
```bash
python -m langflix.main \
  --subtitle "file.srt" \
  --max-expressions 5
```

---

#### Issue: Empty or Invalid JSON Response

**Symptoms**:
```
JSONDecodeError: Expecting value
Error: Failed to parse JSON from LLM response
Invalid expression data
```

**Causes**:
- API returned non-JSON text
- Response was cut off
- Model hallucination
- Network corruption

**Solutions**:

1. Save LLM output for inspection:
```bash
python -m langflix.main \
  --subtitle "file.srt" \
  --save-llm-output \
  --verbose
```

2. Check saved output:
```bash
cat output/llm_output_*.txt
```

3. Adjust temperature:
```yaml
llm:
  temperature: 0.1  # Lower = more consistent
  top_p: 0.8
```

4. Retry with test mode:
```bash
python -m langflix.main \
  --subtitle "file.srt" \
  --test-mode \
  --dry-run
```

---

#### Issue: Rate Limiting / Quota Exceeded

**Symptoms**:
```
Error: 429 Too Many Requests
Quota exceeded for metric
ResourceExhausted: Quota exceeded
```

**Solutions**:

1. Check API quota:
- Visit https://console.cloud.google.com/
- Navigate to Gemini API quotas
- Check current usage

2. Add delays:
```yaml
llm:
  retry_backoff_seconds: 5  # Increase from 2
  max_retries: 5
```

3. Process fewer expressions:
```bash
python -m langflix.main \
  --subtitle "file.srt" \
  --max-expressions 3
```

4. Upgrade API plan if needed

---

### Video Processing Issues

#### Issue: "Video file not found"

**Symptoms**:
```
Error: Could not find video file for subtitle
FileNotFoundError: Video file not found at /path/to/video.mkv
```

**Causes**:
- Video and subtitle names don't match
- Video in different directory
- Wrong file extension

**Solutions**:

1. Check file names match exactly:
```bash
ls -la assets/media/

# Must match:
# video.mp4 → video.srt
# NOT: video_1080p.mp4 → video.srt
```

2. Specify video directory:
```bash
python -m langflix.main \
  --subtitle "path/to/subtitle.srt" \
  --video-dir "path/to/videos"
```

3. Check file extensions:
```bash
# Supported: .mp4, .mkv, .avi, .mov
```

---

#### Issue: FFmpeg Encoding Errors

**Symptoms**:
```
Error: ffmpeg returned non-zero exit code
Error processing video: codec not supported
Stream map 'video:0' matches no streams
```

**Solutions**:

1. Check video codec:
```bash
ffmpeg -i input_video.mkv
ffprobe -v error -show_entries stream=codec_name input_video.mkv
```

2. Re-encode if needed:
```bash
ffmpeg -i problematic.mkv -c:v libx264 -c:a aac fixed.mkv
```

3. Update FFmpeg:
```bash
brew upgrade ffmpeg  # macOS
sudo apt upgrade ffmpeg  # Ubuntu
```

4. Test video file:
```bash
ffmpeg -v error -i video.mkv -f null -
```

---

#### Issue: Video/Audio Sync Problems

**Symptoms**:
- Audio doesn't match video
- Subtitles appear at wrong time
- Expression timing is off

**Solutions**:

1. Check frame rate:
```bash
ffprobe -v error -select_streams v:0 \
  -show_entries stream=r_frame_rate \
  input.mkv
```

2. Match in config:
```yaml
video:
  frame_rate: 23.976  # Match source
```

3. Handle Variable Frame Rate (VFR):
```bash
# Convert VFR to CFR
ffmpeg -i input_vfr.mkv -vsync cfr -r 23.976 output_cfr.mkv
```

4. Check subtitle timing:
```bash
# Open subtitle in text editor
nano subtitle.srt
# Verify timestamps match video
```

---

#### Issue: Out of Memory

**Symptoms**:
```
MemoryError: Unable to allocate memory
Killed (signal 9)
OSError: [Errno 12] Cannot allocate memory
```

**Solutions**:

1. Process fewer expressions:
```bash
python -m langflix.main \
  --subtitle "file.srt" \
  --max-expressions 3
```

2. Lower video resolution:
```yaml
video:
  resolution: "1280x720"  # From 1920x1080
  crf: 25  # Higher = smaller files
```

3. Close other applications

4. Check available memory:
```bash
free -h  # Linux
vm_stat  # macOS
```

5. Add swap space (Linux):
```bash
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

---

### TTS Issues (Phase 2)

#### Issue: No TTS Audio Generated

**Symptoms**:
- Educational slides have no audio
- Silent fallback audio used
- Missing audio files

**Causes**:
- Missing API key
- TTS disabled in config
- API quota exceeded
- Network issues

**Solutions**:

1. Check API key:
```bash
echo $GEMINI_API_KEY
cat .env | grep GEMINI_API_KEY
```

2. Enable TTS:
```yaml
tts:
  enabled: true
  provider: "google"
```

3. Check logs:
```bash
tail -f langflix.log | grep "TTS"
```

4. Test TTS directly:
```python
from langflix.tts import TTSGenerator
tts = TTSGenerator()
audio = tts.generate("test text")
print(f"Audio generated: {len(audio)} bytes")
```

---

#### Issue: Poor TTS Quality

**Symptoms**:
- Robotic voice
- Unnatural pronunciation
- Wrong emphasis

**Solutions**:

1. Adjust SSML settings:
```yaml
tts:
  google:
    speaking_rate: "slow"      # x-slow, slow, medium, fast
    pitch: "-4st"              # Lower pitch
```

2. Try different voices:
```yaml
tts:
  google:
    alternate_voices:
      - "Despina"
      - "Puck"
      - "Kore"
```

3. Use full dialogue context (already implemented in Phase 2)

---

### Subtitle Processing Issues (Phase 2)

#### Issue: Subtitle Encoding Errors

**Symptoms**:
```
UnicodeDecodeError: 'utf-8' codec can't decode byte
SubtitleEncodingError: Failed to decode subtitle file
```

**Phase 2 Solution**:
The system now **automatically handles** most encoding issues!

**Check automatic detection**:
```bash
# Look for encoding detection in logs
tail -f langflix.log | grep "encoding"
# Should see: "Detected encoding: cp949 (confidence: 0.95)"
```

**Manual fix (if auto-detection fails)**:
```bash
# Convert encoding
iconv -f ISO-8859-1 -t UTF-8 subtitle.srt > subtitle_utf8.srt

# Use converted file
python -m langflix.main --subtitle subtitle_utf8.srt
```

---

#### Issue: Too Many Duplicate Expressions (Phase 2)

**Symptoms**:
- Similar expressions appearing multiple times
- Redundant content

**Phase 2 Solution**:
Adjust fuzzy matching threshold:

```yaml
llm:
  ranking:
    fuzzy_match_threshold: 90  # More strict (default: 85)
```

**Check duplicate removal**:
```bash
# Look in logs
tail -f langflix.log | grep "duplicate"
# Should see: "Removed 3 duplicate expressions"
```

---

#### Issue: Expression Quality Problems (Phase 2)

**Symptoms**:
- Expressions too easy/hard
- Not relevant for learning level

**Phase 2 Solution**:
Adjust ranking weights:

```yaml
llm:
  ranking:
    # For advanced learners
    difficulty_weight: 0.6      # Increase difficulty weight
    frequency_weight: 0.2
    educational_value_weight: 0.2
    
    # For beginners
    difficulty_weight: 0.2      # Decrease difficulty weight
    frequency_weight: 0.5       # Increase frequency weight
    educational_value_weight: 0.3
```

---

### WhisperX Issues

#### Issue: WhisperX Model Loading Failed

**Symptoms**:
```
Error loading WhisperX model
ModelNotFoundError: Model 'base' not found
CUDA out of memory
```

**Solutions**:

1. Use CPU if GPU unavailable:
```yaml
whisper:
  device: "cpu"
  compute_type: "float32"
```

2. Use smaller model:
```yaml
whisper:
  model_size: "tiny"  # Smallest model
```

3. Check CUDA availability:
```python
import torch
print(torch.cuda.is_available())
```

4. Clear model cache:
```bash
rm -rf cache/whisperx/
```

---

#### Issue: Slow WhisperX Processing

**Symptoms**:
- Processing takes very long
- High CPU usage
- System freezing

**Solutions**:

1. Enable GPU:
```yaml
whisper:
  device: "cuda"
  compute_type: "float16"
```

2. Reduce batch size:
```yaml
whisper:
  batch_size: 8  # Reduce from 16
```

3. Use faster model:
```yaml
whisper:
  model_size: "base"  # Instead of medium/large
```

---

### Short Video Issues

#### Issue: Short Videos Not Created

**Symptoms**:
- No `short_videos/` directory
- Only educational videos created

**Solutions**:

1. Enable short videos:
```yaml
short_video:
  enabled: true
```

2. Don't use `--no-shorts` flag:
```bash
# Remove --no-shorts
python -m langflix.main --subtitle "file.srt"
```

3. Check logs:
```bash
tail -f langflix.log | grep "short"
```

---

#### Issue: Wrong Aspect Ratio

**Symptoms**:
- Short videos not 9:16 format
- Incorrect resolution

**Solutions**:

1. Verify resolution:
```yaml
short_video:
  resolution: "1080x1920"  # 9:16 vertical
```

2. Check output:
```bash
ffprobe output/short_videos/batch_01.mkv
# Should show: 1080x1920
```

---

### YouTube Integration Issues

#### Issue: OAuth Authentication Failed

**Symptoms**:
```
Error: Authentication failed
OAuth2Error: invalid_grant
CredentialsError: Unable to authenticate
```

**Solutions**:

1. Check credentials file:
```bash
ls -la youtube_credentials.json
cat youtube_credentials.json | jq
```

2. Verify redirect URIs in Google Cloud Console

3. Delete and recreate tokens:
```bash
rm youtube_token.json
curl -X POST http://localhost:8000/api/youtube/login
```

4. Check test user permissions (if in testing)

---

#### Issue: Quota Exceeded

**Symptoms**:
```
Error: No remaining quota for final videos
Daily limit reached: 2/2
```

**Solutions**:

1. Check quota status:
```

# LangFlix Troubleshooting Guide

## Quick Diagnosis

### System Health Check

Run this command to check all components:

```bash
# Comprehensive health check
python -m langflix.diagnostics --full

# Or manually check each component:
python --version                    # Check Python version
ffmpeg -version                     # Check FFmpeg
echo $GEMINI_API_KEY               # Check API key
psql langflix -c "SELECT 1;"       # Check database
curl http://localhost:8000/health  # Check API
```

---

## Common Issues by Category

### Installation & Setup Issues

#### Issue: "ModuleNotFoundError: No module named 'langflix'"

**Symptoms**:
```
ModuleNotFoundError: No module named 'langflix'
```

**Causes**:
- Virtual environment not activated
- Dependencies not installed
- Running from wrong directory

**Solutions**:

1. Activate virtual environment:
```bash
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run from project root:
```bash
cd /path/to/study_english_with_suits
python -m langflix.main --subtitle "file.srt"
```

4. Verify installation:
```bash
python -c "import langflix; print(langflix.__version__)"
```

---

#### Issue: "ffmpeg: command not found"

**Symptoms**:
```
FileNotFoundError: [Errno 2] No such file or directory: 'ffmpeg'
```

**Solutions**:

**macOS**:
```bash
brew install ffmpeg
```

**Ubuntu/Debian**:
```bash
sudo apt update
sudo apt install ffmpeg
```

**Windows**:
```bash
# Using Chocolatey
choco install ffmpeg

# Or download from https://ffmpeg.org/download.html
# Add to PATH
```

**Verify**:
```bash
ffmpeg -version
which ffmpeg  # Linux/macOS
where ffmpeg  # Windows
```

---

#### Issue: "GEMINI_API_KEY not found"

**Symptoms**:
```
Error: GEMINI_API_KEY environment variable not set
KeyError: 'GEMINI_API_KEY'
```

**Solutions**:

1. Create `.env` file:
```bash
cp env.example .env
nano .env
```

2. Add API key:
```bash
GEMINI_API_KEY=your_actual_api_key_here
```

3. Get API key:
- Visit https://aistudio.google.com/
- Sign in with Google account
- Create new API key

4. Verify:
```bash
echo $GEMINI_API_KEY
cat .env | grep GEMINI_API_KEY
```

---

### Processing Issues

#### Issue: API Timeout (504 Gateway Timeout)

**Symptoms**:
```
Error: 504 Gateway Timeout
Gemini API request timed out
TimeoutError: Request exceeded 120 seconds
```

**Causes**:
- Input chunk too large
- Network connectivity issues
- API server overload
- Firewall blocking requests

**Solutions**:

1. Reduce chunk size:
```yaml
# config.yaml
llm:
  max_input_length: 1200  # Reduce from 1680
  chunk_size: 30          # Reduce from 50
  timeout: 180            # Increase timeout
```

2. Check network:
```bash
ping google.com
curl https://generativelanguage.googleapis.com
```

3. Test with smaller input:
```bash
python -m langflix.main \
  --subtitle "file.srt" \
  --test-mode \
  --max-expressions 1
```

4. Check API status:
```bash
curl -I https://generativelanguage.googleapis.com
```

---

#### Issue: "MAX_TOKENS" Finish Reason

**Symptoms**:
```
Warning: LLM response ended with MAX_TOKENS
Response may be incomplete
```

**Causes**:
- Output exceeds token limit (2048 tokens)
- Too many expressions requested
- Complex prompt

**Solutions**:

1. Reduce expressions per chunk:
```yaml
processing:
  max_expressions_per_chunk: 2  # Reduce from 3-4
```

2. Simplify prompt template:
```yaml
llm:
  max_input_length: 1200
```

3. Process fewer subtitles:
```bash
python -m langflix.main \
  --subtitle "file.srt" \
  --max-expressions 5
```

---

#### Issue: Empty or Invalid JSON Response

**Symptoms**:
```
JSONDecodeError: Expecting value
Error: Failed to parse JSON from LLM response
Invalid expression data
```

**Causes**:
- API returned non-JSON text
- Response was cut off
- Model hallucination
- Network corruption

**Solutions**:

1. Save LLM output for inspection:
```bash
python -m langflix.main \
  --subtitle "file.srt" \
  --save-llm-output \
  --verbose
```

2. Check saved output:
```bash
cat output/llm_output_*.txt
```

3. Adjust temperature:
```yaml
llm:
  temperature: 0.1  # Lower = more consistent
  top_p: 0.8
```

4. Retry with test mode:
```bash
python -m langflix.main \
  --subtitle "file.srt" \
  --test-mode \
  --dry-run
```

---

#### Issue: Rate Limiting / Quota Exceeded

**Symptoms**:
```
Error: 429 Too Many Requests
Quota exceeded for metric
ResourceExhausted: Quota exceeded
```

**Solutions**:

1. Check API quota:
- Visit https://console.cloud.google.com/
- Navigate to Gemini API quotas
- Check current usage

2. Add delays:
```yaml
llm:
  retry_backoff_seconds: 5  # Increase from 2
  max_retries: 5
```

3. Process fewer expressions:
```bash
python -m langflix.main \
  --subtitle "file.srt" \
  --max-expressions 3
```

4. Upgrade API plan if needed

---

### Video Processing Issues

#### Issue: "Video file not found"

**Symptoms**:
```
Error: Could not find video file for subtitle
FileNotFoundError: Video file not found at /path/to/video.mkv
```

**Causes**:
- Video and subtitle names don't match
- Video in different directory
- Wrong file extension

**Solutions**:

1. Check file names match exactly:
```bash
ls -la assets/media/

# Must match:
# video.mp4 → video.srt
# NOT: video_1080p.mp4 → video.srt
```

2. Specify video directory:
```bash
python -m langflix.main \
  --subtitle "path/to/subtitle.srt" \
  --video-dir "path/to/videos"
```

3. Check file extensions:
```bash
# Supported: .mp4, .mkv, .avi, .mov
```

---

#### Issue: FFmpeg Encoding Errors

**Symptoms**:
```
Error: ffmpeg returned non-zero exit code
Error processing video: codec not supported
Stream map 'video:0' matches no streams
```

**Solutions**:

1. Check video codec:
```bash
ffmpeg -i input_video.mkv
ffprobe -v error -show_entries stream=codec_name input_video.mkv
```

2. Re-encode if needed:
```bash
ffmpeg -i problematic.mkv -c:v libx264 -c:a aac fixed.mkv
```

3. Update FFmpeg:
```bash
brew upgrade ffmpeg  # macOS
sudo apt upgrade ffmpeg  # Ubuntu
```

4. Test video file:
```bash
ffmpeg -v error -i video.mkv -f null -
```

---

#### Issue: Video/Audio Sync Problems

**Symptoms**:
- Audio doesn't match video
- Subtitles appear at wrong time
- Expression timing is off

**Solutions**:

1. Check frame rate:
```bash
ffprobe -v error -select_streams v:0 \
  -show_entries stream=r_frame_rate \
  input.mkv
```

2. Match in config:
```yaml
video:
  frame_rate: 23.976  # Match source
```

3. Handle Variable Frame Rate (VFR):
```bash
# Convert VFR to CFR
ffmpeg -i input_vfr.mkv -vsync cfr -r 23.976 output_cfr.mkv
```

4. Check subtitle timing:
```bash
# Open subtitle in text editor
nano subtitle.srt
# Verify timestamps match video
```

---

#### Issue: Out of Memory

**Symptoms**:
```
MemoryError: Unable to allocate memory
Killed (signal 9)
OSError: [Errno 12] Cannot allocate memory
```

**Solutions**:

1. Process fewer expressions:
```bash
python -m langflix.main \
  --subtitle "file.srt" \
  --max-expressions 3
```

2. Lower video resolution:
```yaml
video:
  resolution: "1280x720"  # From 1920x1080
  crf: 25  # Higher = smaller files
```

3. Close other applications

4. Check available memory:
```bash
free -h  # Linux
vm_stat  # macOS
```

5. Add swap space (Linux):
```bash
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

---

### TTS Issues (Phase 2)

#### Issue: No TTS Audio Generated

**Symptoms**:
- Educational slides have no audio
- Silent fallback audio used
- Missing audio files

**Causes**:
- Missing API key
- TTS disabled in config
- API quota exceeded
- Network issues

**Solutions**:

1. Check API key:
```bash
echo $GEMINI_API_KEY
cat .env | grep GEMINI_API_KEY
```

2. Enable TTS:
```yaml
tts:
  enabled: true
  provider: "google"
```

3. Check logs:
```bash
tail -f langflix.log | grep "TTS"
```

4. Test TTS directly:
```python
from langflix.tts import TTSGenerator
tts = TTSGenerator()
audio = tts.generate("test text")
print(f"Audio generated: {len(audio)} bytes")
```

---

#### Issue: Poor TTS Quality

**Symptoms**:
- Robotic voice
- Unnatural pronunciation
- Wrong emphasis

**Solutions**:

1. Adjust SSML settings:
```yaml
tts:
  google:
    speaking_rate: "slow"      # x-slow, slow, medium, fast
    pitch: "-4st"              # Lower pitch
```

2. Try different voices:
```yaml
tts:
  google:
    alternate_voices:
      - "Despina"
      - "Puck"
      - "Kore"
```

3. Use full dialogue context (already implemented in Phase 2)

---

### Subtitle Processing Issues (Phase 2)

#### Issue: Subtitle Encoding Errors

**Symptoms**:
```
UnicodeDecodeError: 'utf-8' codec can't decode byte
SubtitleEncodingError: Failed to decode subtitle file
```

**Phase 2 Solution**:
The system now **automatically handles** most encoding issues!

**Check automatic detection**:
```bash
# Look for encoding detection in logs
tail -f langflix.log | grep "encoding"
# Should see: "Detected encoding: cp949 (confidence: 0.95)"
```

**Manual fix (if auto-detection fails)**:
```bash
# Convert encoding
iconv -f ISO-8859-1 -t UTF-8 subtitle.srt > subtitle_utf8.srt

# Use converted file
python -m langflix.main --subtitle subtitle_utf8.srt
```

---

#### Issue: Too Many Duplicate Expressions (Phase 2)

**Symptoms**:
- Similar expressions appearing multiple times
- Redundant content

**Phase 2 Solution**:
Adjust fuzzy matching threshold:

```yaml
llm:
  ranking:
    fuzzy_match_threshold: 90  # More strict (default: 85)
```

**Check duplicate removal**:
```bash
# Look in logs
tail -f langflix.log | grep "duplicate"
# Should see: "Removed 3 duplicate expressions"
```

---

#### Issue: Expression Quality Problems (Phase 2)

**Symptoms**:
- Expressions too easy/hard
- Not relevant for learning level

**Phase 2 Solution**:
Adjust ranking weights:

```yaml
llm:
  ranking:
    # For advanced learners
    difficulty_weight: 0.6      # Increase difficulty weight
    frequency_weight: 0.2
    educational_value_weight: 0.2
    
    # For beginners
    difficulty_weight: 0.2      # Decrease difficulty weight
    frequency_weight: 0.5       # Increase frequency weight
    educational_value_weight: 0.3
```

---

### WhisperX Issues

#### Issue: WhisperX Model Loading Failed

**Symptoms**:
```
Error loading WhisperX model
ModelNotFoundError: Model 'base' not found
CUDA out of memory
```

**Solutions**:

1. Use CPU if GPU unavailable:
```yaml
whisper:
  device: "cpu"
  compute_type: "float32"
```

2. Use smaller model:
```yaml
whisper:
  model_size: "tiny"  # Smallest model
```

3. Check CUDA availability:
```python
import torch
print(torch.cuda.is_available())
```

4. Clear model cache:
```bash
rm -rf cache/whisperx/
```

---

#### Issue: Slow WhisperX Processing

**Symptoms**:
- Processing takes very long
- High CPU usage
- System freezing

**Solutions**:

1. Enable GPU:
```yaml
whisper:
  device: "cuda"
  compute_type: "float16"
```

2. Reduce batch size:
```yaml
whisper:
  batch_size: 8  # Reduce from 16
```

3. Use faster model:
```yaml
whisper:
  model_size: "base"  # Instead of medium/large
```

---

### Short Video Issues

#### Issue: Short Videos Not Created

**Symptoms**:
- No `short_videos/` directory
- Only educational videos created

**Solutions**:

1. Enable short videos:
```yaml
short_video:
  enabled: true
```

2. Don't use `--no-shorts` flag:
```bash
# Remove --no-shorts
python -m langflix.main --subtitle "file.srt"
```

3. Check logs:
```bash
tail -f langflix.log | grep "short"
```

---

#### Issue: Wrong Aspect Ratio

**Symptoms**:
- Short videos not 9:16 format
- Incorrect resolution

**Solutions**:

1. Verify resolution:
```yaml
short_video:
  resolution: "1080x1920"  # 9:16 vertical
```

2. Check output:
```bash
ffprobe output/short_videos/batch_01.mkv
# Should show: 1080x1920
```

---

### YouTube Integration Issues

#### Issue: OAuth Authentication Failed

**Symptoms**:
```
Error: Authentication failed
OAuth2Error: invalid_grant
CredentialsError: Unable to authenticate
```

**Solutions**:

1. Check credentials file:
```bash
ls -la youtube_credentials.json
cat youtube_credentials.json | jq
```

2. Verify redirect URIs in Google Cloud Console

3. Delete and recreate tokens:
```bash
rm youtube_token.json
curl -X POST http://localhost:8000/api/youtube/login
```

4. Check test user permissions (if in testing)

---

#### Issue: Quota Exceeded

**Symptoms**:
```
Error: No remaining quota for final videos
Daily limit reached: 2/2
```

**Solutions**:

1. Check quota status:
```bash
curl "http://localhost:8000/api/quota/status"
```

2. Wait for quota reset (midnight UTC)

3. Adjust daily limits if needed:
```yaml
youtube:
  daily_limits:
    final: 3  # Increase if allowed
    short: 7
```

4. Use scheduling to spread uploads:
```bash
curl "http://localhost:8000/api/schedule/next-available?video_type=final"
```

---

### Database Issues

#### Issue: Database Connection Failed

**Symptoms**:
```
sqlalchemy.exc.OperationalError: could not connect to server
Connection refused
database "langflix" does not exist
```

**Solutions**:

1. Check PostgreSQL is running:
```bash
pg_isready
systemctl status postgresql  # Linux
brew services list | grep postgresql  # macOS
```

2. Start PostgreSQL:
```bash
systemctl start postgresql  # Linux
brew services start postgresql  # macOS
```

3. Create database:
```bash
createdb langflix
```

4. Check connection string:
```bash
echo $DATABASE_URL
psql $DATABASE_URL -c "SELECT 1;"
```

5. Run migrations:
```bash
alembic upgrade head
```

---

#### Issue: Migration Errors

**Symptoms**:
```
alembic.util.exc.CommandError: Can't locate revision
sqlalchemy.exc.IntegrityError: duplicate key value
```

**Solutions**:

1. Check current version:
```bash
alembic current
```

2. Reset migrations (careful!):
```bash
alembic downgrade base
alembic upgrade head
```

3. Fix conflicts:
```bash
alembic stamp head
alembic revision --autogenerate -m "fix conflicts"
alembic upgrade head
```

---

### Storage Issues

#### Issue: Storage Backend Error

**Symptoms**:
```
StorageError: Failed to save file
google.auth.exceptions.DefaultCredentialsError
PermissionError: Access denied
```

**Solutions**:

1. For Local Storage:
```bash
# Check permissions
ls -la output/
chmod 755 output/

# Check disk space
df -h
```

2. For GCS:
```bash
# Check credentials
echo $GOOGLE_APPLICATION_CREDENTIALS
cat $GOOGLE_APPLICATION_CREDENTIALS | jq

# Test access
gsutil ls gs://your-bucket/

# Check permissions
gsutil iam get gs://your-bucket/
```

3. Switch to local storage temporarily:
```yaml
storage:
  backend: "local"
```

---

### API Issues

#### Issue: API Won't Start

**Symptoms**:
```
OSError: [Errno 98] Address already in use
Error: Port 8000 is already in use
uvicorn.config.ConfigException
```

**Solutions**:

1. Check port usage:
```bash
lsof -i :8000
netstat -an | grep 8000
```

2. Kill existing process:
```bash
kill $(lsof -t -i :8000)
pkill -f uvicorn
```

3. Use different port:
```bash
uvicorn langflix.api.main:app --port 8001
```

4. Check configuration:
```bash
python -c "import yaml; print(yaml.safe_load(open('config.yaml')))"
```

---

#### Issue: Background Tasks Not Running

**Symptoms**:
- Jobs stuck in PENDING status
- No progress updates
- Files not generated

**Solutions**:

1. Check logs:
```bash
tail -f langflix.log | grep "background"
```

2. Verify task execution:
```bash
curl "http://localhost:8000/api/v1/jobs/{job_id}"
```

3. Restart API:
```bash
systemctl restart langflix-api
```

4. Check system resources:
```bash
free -h
df -h
top
```

---

## Performance Issues

### Issue: Processing Too Slow

**Symptoms**:
- Takes hours to process episode
- CPU usage low
- No progress

**Solutions**:

1. Enable GPU acceleration:
```yaml
video:
  hardware_acceleration: "cuda"
  codec: "h264_nvenc"

whisper:
  device: "cuda"
  compute_type: "float16"
```

2. Use faster presets:
```yaml
video:
  preset: "fast"  # Instead of "slow"
  crf: 23  # Slightly lower quality
```

3. Increase parallel processing:
```yaml
processing:
  max_concurrent_jobs: 8
```

4. Check bottlenecks:
```bash
# CPU usage
top -p $(pgrep -f langflix)

# I/O wait
iostat -x 1

# Network latency (for API calls)
ping google.com
```

---

### Issue: High Memory Usage

**Symptoms**:
- System runs out of RAM
- Swap usage very high
- OOM killer activated

**Solutions**:

1. Reduce batch size:
```yaml
processing:
  max_expressions_per_chunk: 2
  batch_size: 5
```

2. Lower resolution:
```yaml
video:
  resolution: "1280x720"
```

3. Use smaller models:
```yaml
whisper:
  model_size: "tiny"
```

4. Enable memory limits:
```yaml
processing:
  max_memory_mb: 6144  # 6GB limit
```

5. Process sequentially:
```yaml
processing:
  max_concurrent_jobs: 1
```

---

### Issue: Disk Space Running Out

**Symptoms**:
```
OSError: [Errno 28] No space left on device
Error writing file
```

**Solutions**:

1. Check disk usage:
```bash
df -h
du -sh output/
```

2. Clean old outputs:
```bash
find output/ -mtime +30 -delete
rm -rf test_output/
```

3. Increase compression:
```yaml
video:
  crf: 28  # Higher = smaller files
```

4. Enable cleanup:
```yaml
processing:
  cleanup_temp_files: true
```

---

## Known Issues & Limitations

### Phase 7: Architecture Conflict (CRITICAL)

**Issue**: Flask UI and FastAPI backend conflict

**Symptoms**:
- File upload errors ("read of closed file")
- Port 5000 conflicts
- API communication overhead

**Status**: ⚠️ Design phase, implementation pending

**Workaround**: Use CLI mode or API directly

**Planned Fix**: Consolidate into single FastAPI application

---

### Current Limitations

1. **Single-instance Processing**
   - No distributed task queue (Celery planned)
   - One video processed at a time

2. **Manual GPU Configuration**
   - No automatic GPU detection
   - Requires manual config changes

3. **Limited Error Recovery**
   - Basic retry logic only
   - Manual intervention needed for some failures

4. **No User Authentication**
   - Planned for Phase 8
   - Single-user system currently

5. **No Rate Limiting**
   - API open to all requests
   - Planned for Phase 8

---

## Debugging Tools

### Enable Debug Logging

```bash
# Environment variable
export LANGFLIX_LOG_LEVEL=DEBUG

# CLI flag
python -m langflix.main --verbose --subtitle "file.srt"

# Configuration
# config.yaml
logging:
  level: DEBUG
```

### Save LLM Output

```bash
python -m langflix.main \
  --subtitle "file.srt" \
  --save-llm-output

# Check output
cat output/llm_output_*.txt
```

### Test Individual Components

```bash
# Test subtitle parsing
python -c "from langflix.subtitle_parser import parse_srt_file; print(parse_srt_file('test.srt'))"

# Test LLM connection
python -c "from langflix.expression_analyzer import ExpressionAnalyzer; print('LLM OK')"

# Test video processing
ffmpeg -i test.mp4 -t 10 test_clip.mp4

# Test database
psql langflix -c "SELECT COUNT(*) FROM jobs;"
```

### Performance Profiling

```bash
# Profile Python code
python -m cProfile -s cumulative -m langflix.main --subtitle "test.srt"

# Monitor system resources
htop
iotop
nvidia-smi  # For GPU
```

### Network Debugging

```bash
# Test API connectivity
curl -v http://localhost:8000/health

# Check Gemini API
curl -v https://generativelanguage.googleapis.com

# Monitor network traffic
tcpdump -i any port 8000
```

---

## Getting Help

### Before Asking for Help

1. **Check logs**:
```bash
tail -100 langflix.log
grep ERROR langflix.log
```

2. **Run diagnostics**:
```bash
python -m langflix.diagnostics --full
```

3. **Test with minimal example**:
```bash
python -m langflix.main \
  --subtitle "test.srt" \
  --test-mode \
  --max-expressions 1
```

4. **Check documentation**:
- User Manual
- API Reference
- Configuration Guide

---

### Reporting Issues

Include the following information:

1. **Environment**:
```bash
python --version
ffmpeg -version
uname -a  # Linux/macOS
```

2. **Configuration** (sanitized):
```bash
cat config.yaml  # Remove API keys
```

3. **Error message** (full):
```bash
tail -100 langflix.log
```

4. **Steps to reproduce**:
```bash
# Exact commands you ran
```

5. **Expected vs actual behavior**

---

### Community Resources

- **GitHub Issues**: https://github.com/taigi0315/study_english_with_suits/issues
- **Documentation**: Full documentation in `docs/`
- **Examples**: Sample configurations in `examples/`

---

## Quick Reference Card

### Emergency Commands

```bash
# Kill stuck process
pkill -f langflix

# Clear cache
rm -rf cache/

# Reset database
alembic downgrade base && alembic upgrade head

# Check system health
python -m langflix.diagnostics

# View recent errors
tail -50 langflix.log | grep ERROR

# Test configuration
python -m langflix.config.validate config.yaml
```

### Common Fix Commands

```bash
# Fix file permissions
chmod -R 755 output/

# Fix encoding issues
iconv -f ISO-8859-1 -t UTF-8 subtitle.srt > subtitle_utf8.srt

# Restart services
systemctl restart postgresql
systemctl restart langflix-api

# Clear stuck jobs
psql langflix -c "UPDATE jobs SET status='FAILED' WHERE status='PROCESSING' AND started_at < NOW() - INTERVAL '1 hour';"
```

---

## Preventive Measures

### Regular Maintenance

```bash
# Weekly tasks
alembic upgrade head  # Update database
find cache/ -mtime +7 -delete  # Clear old cache
vacuumdb langflix  # Optimize database

# Monthly tasks
pg_dump langflix > backup.sql  # Backup database
du -sh output/  # Check disk usage
grep ERROR langflix.log | wc -l  # Count errors
```

### Monitoring Setup

```bash
# Monitor API health
watch -n 30 'curl -s http://localhost:8000/health | jq'

# Monitor disk space
watch -n 300 'df -h'

# Monitor jobs
watch -n 10 'curl -s http://localhost:8000/api/v1/jobs?status=PROCESSING | jq'
```

### Best Practices

1. **Always use test mode first**
2. **Keep configurations in version control**
3. **Regular backups**
4. **Monitor resource usage**
5. **Update dependencies regularly**
6. **Review logs periodically**

---

**For more information, see:**
- System Architecture Overview
- Quick Start Guide
- API & Operations Guide
- Configuration Reference