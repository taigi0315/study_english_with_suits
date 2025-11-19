# Subtitles Module

## Overview

The `langflix/subtitles/` module provides subtitle overlay functionality for video processing. It handles locating subtitle files, adjusting timestamps for context video clips, and applying dual-language subtitles to videos using FFmpeg filters.

**Purpose:**
- Locate and manage subtitle files for expressions
- Adjust subtitle timestamps when extracting context clips from source videos
- Apply subtitles to videos with proper styling (ASS format with force_style)
- Support dual-language subtitle overlays

**When to use:**
- When processing expressions and need to overlay subtitles on context videos
- When extracting context clips and need to adjust subtitle timestamps
- When applying styled subtitles to educational videos

## File Inventory

### `overlay.py`
Primary module for subtitle overlay operations.

**Key Functions:**
- `find_subtitle_file()` - Locate subtitle file for an expression
- `adjust_subtitle_timestamps()` - Adjust timestamps when extracting context clips
- `apply_subtitles_with_file()` - Apply subtitles to video using FFmpeg subtitles filter
- `apply_dual_subtitle_layers()` - Apply original subtitles to context video segment
- `build_ass_force_style()` - Generate ASS format styling string from settings
- `drawtext_fallback_single_line()` - Fallback method using drawtext filter

## Key Components

### Subtitle File Location

```python
def find_subtitle_file(subtitle_dir: Path, expression_text: str) -> Optional[Path]:
    """
    Find subtitle file for an expression using multiple pattern matching strategies.
    
    Patterns tried:
    1. expression_*_{safe_expr[:30]}.srt
    2. expression_{safe_expr[:30]}.srt
    3. expression_*_{sanitized}.srt
    4. expression_{sanitized}.srt
    5. Partial match fallback
    
    Returns:
        Path to subtitle file if found, None otherwise
    """
```

**Usage:**
```python
from langflix.subtitles.overlay import find_subtitle_file
from pathlib import Path

subtitle_dir = Path("output/ko/subtitles")
expression = "break the ice"
subtitle_file = find_subtitle_file(subtitle_dir, expression)
```

### Timestamp Adjustment

When extracting a context clip from a source video, subtitles have absolute timestamps from the original video. The `adjust_subtitle_timestamps()` function subtracts the context start time to align subtitles with the sliced video.

```python
def adjust_subtitle_timestamps(
    subtitle_file: Path, 
    offset_seconds: float, 
    output_file: Path
) -> Path:
    """
    Adjust all subtitle timestamps by subtracting offset_seconds.
    
    This is used when applying subtitles to a sliced context video.
    The subtitles have absolute timestamps from the original video,
    but the context video starts at context_start_time, so we need
    to subtract that offset to align subtitles with the sliced video.
    
    Args:
        subtitle_file: Source SRT file with absolute timestamps
        offset_seconds: Time offset to subtract (context_start_time in seconds)
        output_file: Output SRT file with adjusted timestamps
        
    Returns:
        Path to output file
    """
```

**Example:**
```python
from langflix.subtitles.overlay import adjust_subtitle_timestamps

# Context clip starts at 120.5 seconds in original video
adjusted = adjust_subtitle_timestamps(
    subtitle_file=Path("original.srt"),
    offset_seconds=120.5,
    output_file=Path("adjusted.srt")
)
```

### Subtitle Application

The module provides two methods for applying subtitles:

**1. Using FFmpeg subtitles filter (preferred):**
```python
def apply_subtitles_with_file(
    input_video: Path, 
    subtitle_file: Path, 
    output_path: Path, 
    is_expression: bool = False
) -> Path:
    """
    Apply subtitles to video using FFmpeg subtitles filter with ASS styling.
    
    Args:
        input_video: Input video path
        subtitle_file: SRT subtitle file path
        output_path: Output video path
        is_expression: If True, use expression highlight styling
        
    Returns:
        Path to output video with subtitles
    """
```

**2. Using drawtext filter (fallback):**
```python
def drawtext_fallback_single_line(
    input_video: Path, 
    text: str, 
    output_path: Path
) -> Path:
    """
    Fallback method using drawtext filter when subtitles filter fails.
    Used for single-line text overlay at bottom of video.
    """
```

### Dual Subtitle Layers

The `apply_dual_subtitle_layers()` function extracts a context segment from the source video and applies original subtitles. Note: The cyan expression subtitle layer has been removed per user requirements.

```python
def apply_dual_subtitle_layers(
    video_path: str,
    original_subtitle_path: str,
    expression_subtitle_path: str,  # Not used, kept for API compatibility
    output_path: str,
    context_start_seconds: float,
    context_end_seconds: float
) -> Path:
    """
    Extract context segment from source video, then apply original subtitles only.
    
    CRITICAL: Uses trim filter to extract context segment FIRST, then apply subtitles.
    This ensures we're working with a short ~30s clip, not a 40+ minute source video.
    
    Args:
        video_path: Input video path (full source video)
        original_subtitle_path: Path to original dual-language subtitle SRT
        expression_subtitle_path: Not used (kept for API compatibility)
        output_path: Output video path (context segment with subtitles)
        context_start_seconds: Context start time in source video (seconds)
        context_end_seconds: Context end time in source video (seconds)
        
    Returns:
        Path to output video with subtitles
    """
```

## Implementation Details

### ASS Styling

The module generates ASS (Advanced SubStation Alpha) format styling strings from configuration settings:

```python
def build_ass_force_style(is_expression: bool = False) -> str:
    """
    Build ASS force_style string from settings.
    
    Configuration path: expression.subtitle_styling
    - default: White text, normal weight
    - expression_highlight: Gold text (#FFD700), bold, larger font
    
    Returns:
        ASS format force_style string
    """
```

**Styling Configuration:**
- Font size: From `settings.get_font_size()`
- Color: Hex to ASS BGR format conversion
- Background/outline: Configurable outline color and width
- Font weight: Bold for expressions, normal for default

### Timestamp Conversion

Internal helper functions for SRT timestamp format:

```python
def _time_to_seconds(time_str: str) -> float:
    """Convert SRT time string (HH:MM:SS,mmm) to seconds"""
    
def _seconds_to_time(seconds: float) -> str:
    """Convert seconds to SRT time string (HH:MM:SS,mmm)"""
```

### Subtitle Filtering

When adjusting timestamps, subtitles that fall before the context start time are filtered out:

```python
# Only include subtitles that are still within valid range (after offset)
if end_seconds > 0:
    # Adjust to start from 0 if start is negative
    if start_seconds < 0:
        start_seconds = 0
    # Include subtitle
else:
    # This subtitle is before the context start, skip it
```

## Dependencies

**External Libraries:**
- `ffmpeg-python` - Video processing and subtitle overlay
- `pathlib` - Path manipulation

**Internal Dependencies:**
- `langflix.settings` - Configuration access
- `langflix.utils.filename_utils` - Filename sanitization

**FFmpeg Requirements:**
- FFmpeg with `subtitles` filter support
- `libass` library for ASS subtitle rendering

## Common Tasks

### Adding Subtitle Overlay to Context Video

```python
from langflix.subtitles.overlay import apply_dual_subtitle_layers

output_video = apply_dual_subtitle_layers(
    video_path="source_video.mkv",
    original_subtitle_path="dual_lang.srt",
    expression_subtitle_path="",  # Not used
    output_path="context_with_subtitles.mkv",
    context_start_seconds=120.5,
    context_end_seconds=150.0
)
```

### Adjusting Timestamps for Context Clip

```python
from langflix.subtitles.overlay import adjust_subtitle_timestamps

# Original subtitles are for full video (0-2400 seconds)
# Context clip is from 120.5 to 150.0 seconds
adjusted = adjust_subtitle_timestamps(
    subtitle_file=Path("original.srt"),
    offset_seconds=120.5,  # Subtract context start time
    output_file=Path("adjusted.srt")
)
```

### Finding Subtitle File for Expression

```python
from langflix.subtitles.overlay import find_subtitle_file

subtitle_file = find_subtitle_file(
    subtitle_dir=Path("output/ko/subtitles"),
    expression_text="break the ice"
)

if subtitle_file:
    print(f"Found subtitle: {subtitle_file}")
else:
    print("Subtitle file not found")
```

## Gotchas and Notes

### Important Considerations

1. **Timestamp Adjustment:**
   - Always adjust timestamps when extracting context clips
   - Subtitles with negative start times are clamped to 0
   - Subtitles before context start are filtered out

2. **Subtitle Filter Performance:**
   - Using `subtitles` filter on full-length videos is slow
   - Always extract context segment FIRST, then apply subtitles
   - See `apply_dual_subtitle_layers()` for correct pattern

3. **Expression Subtitle Layer:**
   - Cyan expression subtitle layer has been removed
   - Only original dual-language subtitles are applied
   - `expression_subtitle_path` parameter kept for API compatibility but not used

4. **Font Requirements:**
   - ASS styling requires proper font files
   - Font detection handled by `langflix.config.font_utils`
   - Fallback to system default fonts if configured font not found

5. **Subtitle File Matching:**
   - Uses multiple pattern matching strategies
   - Handles sanitized and unsanitized expression names
   - Partial matching fallback for edge cases

### Performance Tips

- Extract context clips before applying subtitles (not after)
- Use `subtitles` filter for SRT files (faster than drawtext)
- Cache adjusted subtitle files if processing multiple expressions from same context

### Error Handling

- Missing subtitle files return `None` (check before use)
- Invalid timestamp formats log warnings and keep original
- FFmpeg errors raise exceptions (handle in calling code)

## Related Documentation

- [Core Module](../core/README_eng.md) - Expression processing and video editing
- [Media Module](../media/README_eng.md) - FFmpeg utilities
- [Config Module](../config/README_eng.md) - Font and styling configuration

