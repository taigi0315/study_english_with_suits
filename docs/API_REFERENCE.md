# LangFlix API Reference

**Version:** 1.0  
**Last Updated:** January 2025

This document provides comprehensive API documentation for all public classes and methods in LangFlix. Use this reference for programmatic access and integration.

---

## Table of Contents

1. [Core Pipeline](#core-pipeline)
2. [Data Models](#data-models)
3. [Video Processing](#video-processing)
4. [Subtitle Processing](#subtitle-processing)
5. [Expression Analysis](#expression-analysis)
6. [Configuration](#configuration)
7. [Utility Functions](#utility-functions)

---

## Core Pipeline

### `LangFlixPipeline`

Main orchestrator class that coordinates the entire LangFlix workflow.

#### Constructor

```python
LangFlixPipeline(
    subtitle_file: str,
    video_dir: str = "assets/media",
    output_dir: str = "output",
    language_code: str = "ko"
)
```

**Parameters:**
- `subtitle_file` (str): Path to subtitle file (.srt)
- `video_dir` (str): Directory containing video files (default: "assets/media")
- `output_dir` (str): Directory for output files (default: "output")
- `language_code` (str): Target language code (default: "ko")

#### Methods

##### `run(max_expressions=None, dry_run=False, language_level=None, save_llm_output=False, test_mode=False, no_shorts=False) -> Dict[str, Any]`

Execute the complete LangFlix pipeline.

**Parameters:**
- `max_expressions` (int, optional): Maximum number of expressions to process. If None, processes all found expressions.
- `dry_run` (bool): If True, only analyze without creating video files (default: False)
- `language_level` (str, optional): Target language level ("beginner", "intermediate", "advanced", "mixed"). Uses default from settings if None.
- `save_llm_output` (bool): If True, save LLM responses to files for review (default: False)
- `test_mode` (bool): If True, process only the first chunk for testing (default: False)
- `no_shorts` (bool): If True, skip creating short-format videos (default: False, shorts are created by default)

**Returns:**
- Dictionary containing processing results:
  ```python
  {
      "total_subtitles": int,
      "total_chunks": int,
      "total_expressions": int,
      "processed_expressions": int,
      "output_directory": str,
      "series_name": str,
      "episode_name": str,
      "language_code": str,
      "timestamp": str
  }
  ```

**Example:**
```python
from langflix.main import LangFlixPipeline

pipeline = LangFlixPipeline(
    subtitle_file="assets/media/Suits/Suits.S01E01.srt",
    video_dir="assets/media",
    output_dir="output",
    language_code="ko"
)

results = pipeline.run(
    max_expressions=5,
    language_level="intermediate",
    dry_run=False
)

print(f"Processed {results['processed_expressions']} expressions")
```

---

## Data Models

### `ExpressionAnalysis`

Pydantic model representing a single analyzed expression.

```python
class ExpressionAnalysis(BaseModel):
    dialogues: List[str]
    translation: List[str]
    expression: str
    expression_translation: str
    context_start_time: str
    context_end_time: str
    expression_start_time: Optional[str] = None
    expression_end_time: Optional[str] = None
    similar_expressions: List[str]
```

**Fields:**
- `dialogues` (List[str]): Complete dialogue lines in the scene
- `translation` (List[str]): Translations of all dialogue lines in the same order
- `expression` (str): The main expression/phrase to learn
- `expression_translation` (str): Translation of the main expression
- `context_start_time` (str): Timestamp where conversational context should BEGIN (format: "HH:MM:SS,mmm")
- `context_end_time` (str): Timestamp where conversational context should END (format: "HH:MM:SS,mmm")
- `expression_start_time` (str, optional): Exact timestamp where the expression phrase begins
- `expression_end_time` (str, optional): Exact timestamp where the expression phrase ends
- `similar_expressions` (List[str]): 1-3 similar expressions or alternatives

**Example:**
```python
from langflix.models import ExpressionAnalysis

expr = ExpressionAnalysis(
    dialogues=["I'm paying you millions,", "and you're telling me I'm gonna get screwed?"],
    translation=["나는 당신에게 수백만 달러를 지불하고 있는데,", "당신은 내가 속임을 당할 것이라고 말하고 있나요?"],
    expression="I'm gonna get screwed",
    expression_translation="속임을 당할 것 같아요",
    context_start_time="00:01:25,657",
    context_end_time="00:01:32,230",
    similar_expressions=["I'm going to be cheated", "I'm getting the short end of the stick"]
)
```

### `ExpressionAnalysisResponse`

Container for multiple expression analyses.

```python
class ExpressionAnalysisResponse(BaseModel):
    expressions: List[ExpressionAnalysis]
```

---

## Video Processing

### `VideoProcessor`

Handles video file operations including loading, validation, and clip extraction.

#### Constructor

```python
VideoProcessor(media_dir: str = "assets/media")
```

**Parameters:**
- `media_dir` (str): Directory containing video files

#### Methods

##### `find_video_file(subtitle_file_path: str) -> Optional[Path]`

Find corresponding video file for a subtitle file.

**Parameters:**
- `subtitle_file_path` (str): Path to subtitle file

**Returns:**
- `Optional[Path]`: Path to corresponding video file, or None if not found

##### `extract_clip(video_path: str, start_time: str, end_time: str, output_path: str) -> bool`

Extract a video clip between specified timestamps.

**Parameters:**
- `video_path` (str): Path to source video file
- `start_time` (str): Start timestamp (format: "HH:MM:SS,mmm")
- `end_time` (str): End timestamp (format: "HH:MM:SS,mmm")
- `output_path` (str): Path for output clip

**Returns:**
- `bool`: True if extraction successful, False otherwise

##### `get_video_info(video_path: str) -> Dict[str, Any]`

Get video file metadata and properties.

**Parameters:**
- `video_path` (str): Path to video file

**Returns:**
- Dictionary containing video information (duration, resolution, codec, etc.)

**Example:**
```python
from langflix.video_processor import VideoProcessor

processor = VideoProcessor("assets/media")

# Find video file
video_path = processor.find_video_file("assets/media/Suits/Suits.S01E01.srt")
if video_path:
    # Extract clip
    success = processor.extract_clip(
        str(video_path),
        "00:01:25,657",
        "00:01:32,230",
        "output/clip.mkv"
    )
    
    # Get video info
    info = processor.get_video_info(str(video_path))
    print(f"Duration: {info.get('duration')}")
```

### `VideoEditor`

Handles video editing operations including educational video creation and short-format video generation.

#### Constructor

```python
VideoEditor(output_dir: str = "output", language_code: str = None)
```

**Parameters:**
- `output_dir` (str): Output directory for generated videos
- `language_code` (str): Target language code (default: None)

#### Methods

##### `create_short_format_video(context_video_path: str, expression: ExpressionAnalysis, expression_index: int = 0) -> Tuple[str, float]`

Create vertical short-format video (9:16) with context video on top and slide on bottom.

**Parameters:**
- `context_video_path` (str): Path to context video with subtitles
- `expression` (ExpressionAnalysis): Expression data containing text and translations
- `expression_index` (int): Index of expression for voice alternation (default: 0)

**Returns:**
- `Tuple[str, float]`: (output_path, duration) of created short video

**Features:**
- Total duration = context_duration + (TTS_duration × 2) + 0.5s
- Context video plays normally, then freezes on last frame
- TTS audio plays twice with 0.5s gap after context ends
- Slide displays throughout entire video (silent)

##### `create_batched_short_videos(short_format_videos: List[Tuple[str, float]], target_duration: float = 120.0) -> List[str]`

Combine short format videos into batches of ~120 seconds each.

**Parameters:**
- `short_format_videos` (List[Tuple[str, float]]): List of (video_path, duration) tuples
- `target_duration` (float): Target duration for each batch (default: 120.0)

**Returns:**
- `List[str]`: List of created batch video paths

**Example:**
```python
from langflix.video_editor import VideoEditor
from langflix.models import ExpressionAnalysis

editor = VideoEditor("output", "ko")

# Create short format video
output_path, duration = editor.create_short_format_video(
    "context_video.mkv",
    expression,
    expression_index=0
)

# Batch short videos
batched_videos = editor.create_batched_short_videos(
    [(output_path, duration)],
    target_duration=120.0
)
```

---

## Subtitle Processing

### `SubtitleProcessor`

Handles subtitle file operations and processing.

#### Constructor

```python
SubtitleProcessor(subtitle_file: str)
```

**Parameters:**
- `subtitle_file` (str): Path to subtitle file (.srt)

#### Methods

##### `find_expression_timing(expression_text: str, start_time: str, end_time: str) -> Dict[str, str]`

Find precise timing for expression within a time range.

**Parameters:**
- `expression_text` (str): Expression text to find timing for
- `start_time` (str): Start of search range
- `end_time` (str): End of search range

**Returns:**
- Dictionary with `start_time` and `end_time` keys containing precise timestamps

##### `create_dual_language_subtitle_file(expression: ExpressionAnalysis, output_path: str) -> bool`

Create dual-language subtitle file for an expression.

**Parameters:**
- `expression` (ExpressionAnalysis): Expression data containing dialogues and translations
- `output_path` (str): Path for output subtitle file

**Returns:**
- `bool`: True if successful, False otherwise

**Example:**
```python
from langflix.subtitle_processor import SubtitleProcessor
from langflix.models import ExpressionAnalysis

processor = SubtitleProcessor("assets/media/Suits/Suits.S01E01.srt")

# Find expression timing
timing = processor.find_expression_timing(
    "I'm gonna get screwed",
    "00:01:25,657",
    "00:01:32,230"
)

# Create dual-language subtitle
success = processor.create_dual_language_subtitle_file(
    expression,
    "output/expression_subtitles.srt"
)
```

---

## Expression Analysis

### `analyze_chunk`

Function for analyzing subtitle chunks with LLM.

```python
def analyze_chunk(
    subtitle_chunk: List[dict],
    language_level: str = None,
    language_code: str = "ko",
    max_retries: int = 3
) -> List[ExpressionAnalysis]
```

**Parameters:**
- `subtitle_chunk` (List[dict]): List of subtitle dictionaries with 'start_time', 'end_time', 'text' keys
- `language_level` (str, optional): Target language level
- `language_code` (str): Target language code (default: "ko")
- `max_retries` (int): Maximum retry attempts for API calls (default: 3)

**Returns:**
- `List[ExpressionAnalysis]`: List of analyzed expressions

**Example:**
```python
from langflix.expression_analyzer import analyze_chunk

chunk = [
    {"start_time": "00:01:25,657", "end_time": "00:01:28,200", "text": "I'm paying you millions,"},
    {"start_time": "00:01:28,200", "end_time": "00:01:32,230", "text": "and you're telling me I'm gonna get screwed?"}
]

expressions = analyze_chunk(
    chunk,
    language_level="intermediate",
    language_code="ko"
)

for expr in expressions:
    print(f"Expression: {expr.expression}")
    print(f"Translation: {expr.expression_translation}")
```

---

## Configuration

### `settings`

Configuration management module providing access to application settings.
All configuration is now stored in YAML files with clean accessor functions.

#### Section Accessors

##### `get_app_config() -> Dict[str, Any]`

Get application settings including show name and template file.

##### `get_llm_config() -> Dict[str, Any]`

Get LLM configuration including API settings and generation parameters.

##### `get_video_config() -> Dict[str, Any]`

Get video processing configuration including codecs and quality settings.

##### `get_font_config() -> Dict[str, Any]`

Get font configuration including sizes and file paths.

##### `get_processing_config() -> Dict[str, Any]`

Get processing configuration including chunk limits.

##### `get_tts_config() -> Dict[str, Any]`

Get TTS configuration including provider settings.

##### `get_short_video_config() -> Dict[str, Any]`

Get short video configuration including target duration and resolution.

#### Specific Value Accessors

##### `get_show_name() -> str`

Get the TV show name from configuration.

##### `get_template_file() -> str`

Get the template file name for prompts.

##### `get_generation_config() -> Dict[str, Any]`

Get LLM generation configuration with temperature, top_p, top_k.

##### `get_font_size(size_type: str) -> int`

Get font size for different text types (default, expression, translation, similar).

##### `get_font_file(language_code: str = None) -> str`

Get font file path for the given language or platform default.

##### `get_min_expressions_per_chunk() -> int`

Get minimum expressions per chunk limit.

##### `get_max_expressions_per_chunk() -> int`

Get maximum expressions per chunk limit.

##### `get_max_retries() -> int`

Get maximum retry attempts for API calls.

##### `is_tts_enabled() -> bool`

Check if TTS is enabled.

##### `is_short_video_enabled() -> bool`

Check if short video generation is enabled.

**Example:**
```python
from langflix import settings

# Get configuration values using new accessors
show_name = settings.get_show_name()
template_file = settings.get_template_file()
gen_config = settings.get_generation_config()
font_size = settings.get_font_size('expression')
font_file = settings.get_font_file('ko')

# Check feature flags
tts_enabled = settings.is_tts_enabled()
shorts_enabled = settings.is_short_video_enabled()

print(f"Show: {show_name}")
print(f"Template: {template_file}")
print(f"Font size: {font_size}")
print(f"TTS enabled: {tts_enabled}")
```

### `ConfigLoader`

Configuration loader for YAML-based settings.

```python
from langflix.config.config_loader import ConfigLoader

loader = ConfigLoader()
config = loader.get('llm')  # Get LLM configuration section
```

### `font_utils`

Platform-specific font detection utilities.

#### Functions

##### `get_platform_default_font() -> str`

Get appropriate default font based on platform (macOS, Linux, Windows).

##### `get_font_file_for_language(language_code: str = None) -> str`

Get font file path for the given language or platform default.

```python
from langflix.config.font_utils import get_platform_default_font, get_font_file_for_language

# Get platform-specific default font
default_font = get_platform_default_font()

# Get language-specific font
korean_font = get_font_file_for_language('ko')
```

---

## Utility Functions

### Subtitle Parsing

```python
from langflix.subtitle_parser import parse_srt_file, chunk_subtitles

# Parse SRT file
subtitles = parse_srt_file("path/to/subtitle.srt")

# Chunk subtitles for processing
chunks = chunk_subtitles(subtitles)
```

**Returns:**
- `parse_srt_file()`: List of subtitle dictionaries
- `chunk_subtitles()`: List of chunked subtitle lists

### Output Management

```python
from langflix.output_manager import create_output_structure

# Create organized output directory structure
paths = create_output_structure(
    subtitle_file="assets/media/Suits/Suits.S01E01.srt",
    language_code="ko",
    output_dir="output"
)
```

**Returns:**
- Dictionary with organized output paths for different file types

### Prompt Generation

```python
from langflix.prompts import get_prompt_for_chunk

# Generate LLM prompt for subtitle chunk
prompt = get_prompt_for_chunk(
    subtitle_chunk,
    language_level="intermediate",
    language_code="ko"
)
```

**Returns:**
- Formatted prompt string for LLM processing

---

## Error Handling

### Exception Types

**`ValueError`**: Raised for invalid input parameters, missing files, or processing failures.

**`FileNotFoundError`**: Raised when required files (video, subtitle) cannot be found.

**`APIError`**: Raised for LLM API-related failures (timeouts, quota exceeded, etc.).

### Example Error Handling

```python
from langflix.main import LangFlixPipeline
import logging

logger = logging.getLogger(__name__)

try:
    pipeline = LangFlixPipeline("subtitle.srt")
    results = pipeline.run()
except ValueError as e:
    logger.error(f"Invalid input: {e}")
except FileNotFoundError as e:
    logger.error(f"File not found: {e}")
except Exception as e:
    logger.error(f"Unexpected error: {e}")
```

---

## Best Practices

### 1. Resource Management

Always use context managers or proper cleanup for video processing:

```python
# Good: Let the pipeline handle cleanup automatically
pipeline = LangFlixPipeline("subtitle.srt")
results = pipeline.run(max_expressions=5)

# For manual processing, ensure proper cleanup
try:
    processor = VideoProcessor()
    success = processor.extract_clip(video_path, start, end, output)
finally:
    # Cleanup if needed
    pass
```

### 2. Configuration

Use the configuration system instead of hardcoded values:

```python
# Good: Use configuration
from langflix import settings

max_retries = settings.get_max_retries()
gen_config = settings.get_generation_config()

# Avoid: Hardcoded values
max_retries = 3  # Bad
```

### 3. Error Handling

Always handle potential failures gracefully:

```python
processor = VideoProcessor()
video_path = processor.find_video_file("subtitle.srt")

if video_path is None:
    logger.error("Video file not found")
    return False

try:
    success = processor.extract_clip(str(video_path), start, end, output)
    if not success:
        logger.error("Video extraction failed")
except Exception as e:
    logger.error(f"Unexpected error during extraction: {e}")
```

### 4. Logging

Use structured logging for debugging:

```python
import logging

logger = logging.getLogger(__name__)

# Log important operations
logger.info(f"Processing {len(expressions)} expressions")
logger.debug(f"Expression details: {expression.expression}")
logger.error(f"Failed to process expression: {error}")
```

---

## Integration Examples

### Basic Pipeline Integration

```python
from langflix.main import LangFlixPipeline
from langflix.models import ExpressionAnalysis

def process_episode(subtitle_path: str, max_expressions: int = 10):
    """Process a single episode and return results."""
    pipeline = LangFlixPipeline(
        subtitle_file=subtitle_path,
        language_code="ko"
    )
    
    results = pipeline.run(
        max_expressions=max_expressions,
        language_level="intermediate",
        dry_run=False
    )
    
    return {
        "success": results["processed_expressions"] > 0,
        "expressions_count": results["processed_expressions"],
        "output_dir": results["output_directory"]
    }

# Usage
result = process_episode("assets/media/Suits/Suits.S01E01.srt")
```

### Custom Expression Processing

```python
from langflix.expression_analyzer import analyze_chunk
from langflix.video_processor import VideoProcessor
from langflix.subtitle_processor import SubtitleProcessor

def custom_expression_processing(subtitle_path: str, video_dir: str):
    """Custom processing workflow."""
    # Initialize processors
    video_processor = VideoProcessor(video_dir)
    subtitle_processor = SubtitleProcessor(subtitle_path)
    
    # Parse and analyze (simplified)
    from langflix.subtitle_parser import parse_srt_file, chunk_subtitles
    
    subtitles = parse_srt_file(subtitle_path)
    chunks = chunk_subtitles(subtitles)
    
    all_expressions = []
    for chunk in chunks:
        expressions = analyze_chunk(chunk)
        all_expressions.extend(expressions)
    
    return all_expressions
```

---

**For Korean version of this API reference, see [API_REFERENCE_KOR.md](API_REFERENCE_KOR.md)**

**Related Documentation:**
- [User Manual](USER_MANUAL.md) - Complete usage guide
- [Troubleshooting Guide](TROUBLESHOOTING.md) - Common issues and solutions

---

*This API reference is automatically updated with each release. For the latest information, always refer to the version in your codebase.*
