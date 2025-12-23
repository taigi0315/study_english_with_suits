# LangFlix Configuration Guide

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
  echo: false # Set true for SQL debugging

# Storage Configuration
storage:
  backend: "local" # "local" or "gcs"
  local:
    base_path: "output"
  gcs:
    bucket_name: "langflix-storage"
    credentials_path: "service-account.json"

# LLM Configuration
llm:
  provider: "gemini"
  model: "gemini-2.0-flash"
  api_key: "${GEMINI_API_KEY}" # From environment
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
  model_size: "base" # tiny, base, small, medium, large-v2
  device: "cpu" # cpu, cuda
  compute_type: "float32" # float32, float16, int8
  language: null # null for auto-detect
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
  preset: "medium" # ultrafast, fast, medium, slow, veryslow
  crf: 20 # 18-28, lower = better quality
  resolution: "1920x1080"
  frame_rate: 23.976
  hardware_acceleration: null # null, cuda, qsv, vaapi
  thread_count: 0 # 0 = auto

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
    speaking_rate: "slow" # x-slow, slow, medium, fast, x-fast
    pitch: "-4st" # Semitones: -20st to +20st
    alternate_voices:
      - "Despina"
      - "Puck"
      - "Kore"

# Media Processing
media:
  slicing:
    quality: "high" # low, medium, high, lossless
    buffer_start: 0.2
    buffer_end: 0.2
    output_format: "mp4"

  subtitles:
    style: "expression_highlight"
    font_size: 24
    font_color: "#FFFFFF" # Source dialogue color (White)
    translation_color: "#FFFF00" # Translation color (Yellow)
    background_color: "#000000"
    highlight_color: "#FFD700"
    encoding: "utf-8"
    max_chars_per_line: 25 # Maximum characters before line wrap

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

# Short Video Configuration
short_video:
  enabled: true
  target_duration: 120 # seconds
  resolution: "1080x1920" # 9:16 aspect ratio
  batch_size: 5
  transition_duration: 0.5

# YouTube Integration
youtube:
  enabled: false
  daily_limits:
    final: 2
    short: 5
  upload_settings:
    privacy: "unlisted"
    category: "Education"
    tags: ["english", "learning", "suits"]
```

---

## Configuration Sections

### Application Settings

```yaml
app:
  show_name: "Suits" # Default show name
  language_code: "en" # Source language
  target_language: "Korean" # Target language for translations
  template_file: "expression_analysis_prompt.txt" # LLM prompt template
```

### Database Configuration

```yaml
database:
  enabled: true # Enable database integration
  url: "postgresql://user:password@localhost:5432/langflix"
  pool_size: 10 # Connection pool size
  max_overflow: 20 # Maximum overflow connections
  echo: false # SQL query logging
```

### Storage Configuration

```yaml
storage:
  backend: "local" # "local" or "gcs"
  local:
    base_path: "output" # Local storage path
  gcs:
    bucket_name: "langflix-storage" # Google Cloud Storage bucket
    credentials_path: "service-account.json"
```

### LLM Configuration

```yaml
llm:
  provider: "gemini" # LLM provider
  model: "gemini-2.0-flash" # Model name
  api_key: "${GEMINI_API_KEY}" # API key from environment
  temperature: 0.7 # Response randomness (0-1)
  top_p: 0.8 # Nucleus sampling
  top_k: 40 # Top-k sampling
  max_input_length: 1680 # Maximum input tokens
  chunk_size: 50 # Subtitle chunk size
  overlap: 5 # Chunk overlap
  max_retries: 5 # Maximum retry attempts
  retry_backoff_seconds: 3 # Retry delay
  timeout: 120 # Request timeout
```

### Video Processing Configuration

```yaml
video:
  codec: "libx264" # Video codec
  preset: "medium" # Encoding preset
  crf: 20 # Constant Rate Factor (quality)
  resolution: "1920x1080" # Output resolution
  frame_rate: 23.976 # Frame rate
  hardware_acceleration: null # Hardware acceleration
  thread_count: 0 # Thread count (0 = auto)
```

### TTS Configuration

```yaml
tts:
  enabled: true # Enable TTS
  provider: "google" # TTS provider
  repeat_count: 2 # Number of repetitions

  google:
    language_code: "en-us" # Voice language
    model_name: "gemini-2.5-flash-preview-tts"
    response_format: "wav" # Audio format
    speaking_rate: "slow" # Speaking speed
    pitch: "-4st" # Voice pitch
    alternate_voices: # Voice alternatives
      - "Despina"
      - "Puck"
      - "Kore"
```

---

## Environment Variables

### Required Variables

```bash
# Gemini API Key
GEMINI_API_KEY=your_actual_api_key_here

# Database URL (if using database)
DATABASE_URL=postgresql://user:password@localhost:5432/langflix

# Redis URL (if using Redis)
REDIS_URL=redis://localhost:6379/0
```

### Optional Variables

```bash
# Google Cloud Storage (if using GCS)
GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json

# YouTube API (if using YouTube integration)
YOUTUBE_CLIENT_ID=your_client_id
YOUTUBE_CLIENT_SECRET=your_client_secret

# Logging
LANGFLIX_LOG_LEVEL=INFO
```

---

## Configuration Examples

### Beginner-Friendly Configuration

```yaml
llm:
  extraction:
    max_expressions_per_chunk: 3
    min_difficulty: 1
    max_difficulty: 5
  ranking:
    difficulty_weight: 0.2
    frequency_weight: 0.5
    educational_value_weight: 0.3

video:
  preset: "fast"
  crf: 25
  resolution: "1280x720"
```

### Advanced User Configuration

```yaml
llm:
  extraction:
    max_expressions_per_chunk: 5
    min_difficulty: 5
    max_difficulty: 10
  ranking:
    difficulty_weight: 0.6
    frequency_weight: 0.2
    educational_value_weight: 0.2

video:
  preset: "slow"
  crf: 18
  resolution: "1920x1080"
  hardware_acceleration: "cuda"
```

### Performance-Optimized Configuration

```yaml
video:
  preset: "veryfast"
  crf: 28
  resolution: "1280x720"
  hardware_acceleration: "cuda"

whisper:
  model_size: "tiny"
  device: "cuda"
  compute_type: "float16"

llm:
  chunk_size: 30
  max_input_length: 1200
```

---

## Configuration Validation

### Validate Configuration

```bash
# Validate config.yaml
python -c "import yaml; yaml.safe_load(open('config.yaml'))"

# Test configuration
python -m langflix.config.validate config.yaml
```

### Common Configuration Issues

1. **Invalid YAML syntax**: Check indentation and quotes
2. **Missing required fields**: Ensure all required sections are present
3. **Invalid values**: Check value ranges and types
4. **File permissions**: Ensure config file is readable

---

## Advanced Configuration

### Custom Prompt Templates

```yaml
app:
  template_file: "custom_prompt.txt"
```

Create `custom_prompt.txt`:

```
You are an expert English teacher. Analyze the following subtitle chunk and extract educational expressions.

Subtitle chunk: {chunk}

Target language: {target_language}
Language level: {language_level}

Extract {max_expressions} expressions that are:
1. Useful for {language_level} learners
2. Commonly used in {target_language} contexts
3. Have clear educational value

Format your response as JSON...
```

### Custom Slide Templates

```yaml
slides:
  templates:
    custom:
      background_color: "#1a1a1a"
      text_color: "#ffffff"
      font_family: "Arial"
      font_size: 48
      title_font_size: 72
```

### Hardware Acceleration

```yaml
video:
  hardware_acceleration: "cuda" # NVIDIA GPU
  # hardware_acceleration: "qsv"       # Intel Quick Sync
  # hardware_acceleration: "vaapi"     # AMD/NVIDIA VA-API

whisper:
  device: "cuda"
  compute_type: "float16"
```

---

## Configuration Best Practices

### Performance Optimization

1. **Use appropriate presets**: Balance quality vs speed
2. **Enable hardware acceleration**: Use GPU when available
3. **Optimize chunk sizes**: Balance memory vs processing time
4. **Use appropriate models**: Choose model size based on needs

### Quality Optimization

1. **Adjust CRF values**: Lower = better quality, larger files
2. **Use appropriate presets**: Higher quality presets for final output
3. **Optimize TTS settings**: Balance speed vs quality
4. **Fine-tune ranking weights**: Adjust for your learning goals

### Resource Management

1. **Monitor memory usage**: Adjust batch sizes accordingly
2. **Use appropriate resolutions**: Balance quality vs file size
3. **Enable cleanup**: Remove temporary files
4. **Optimize caching**: Use appropriate cache sizes

---

## Troubleshooting Configuration

### Common Issues

1. **Configuration not loaded**: Check file path and permissions
2. **Invalid values**: Verify value ranges and types
3. **Missing dependencies**: Ensure required packages are installed
4. **Environment variables**: Check variable names and values

### Debug Configuration

```bash
# Enable debug logging
export LANGFLIX_LOG_LEVEL=DEBUG

# Validate configuration
python -m langflix.config.validate config.yaml

# Test configuration loading
python -c "from langflix import settings; print(settings.get_config())"
```
