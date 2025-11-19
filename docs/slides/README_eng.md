# Slides Module

## Overview

The `langflix/slides/` module provides educational slide generation functionality for LangFlix. It creates video slides with text overlays containing expression information, translations, similar expressions, and educational content.

**Purpose:**
- Generate educational slides with expression content
- Create silent or audio-backed slide videos
- Apply text overlays with proper styling
- Support multiple slide template types
- Integrate with video pipeline for educational content

**When to use:**
- When creating educational slides for expressions
- When generating slide videos with text overlays
- When customizing slide templates and layouts

## File Inventory

### `generator.py`
Main slide generation module using FFmpeg.

**Key Functions:**
- `create_silent_slide()` - Create slide video without audio
- `_get_background_input()` - Get background image or color
- `_clean_for_draw()` - Clean text for drawtext filter
- `_esc_draw()` - Escape special characters for drawtext
- `_font_size()` - Get font size from settings

**Key Classes:**
- `SlideText` - Dataclass for slide text content

### `slide_templates.py`
Template management for different slide types.

**Key Classes:**
- `SlideType` - Enum for slide template types
- `SlideTemplate` - Template configuration dataclass
- `SlideTemplates` - Template manager class

**Slide Types:**
- `EXPRESSION` - Main expression slide
- `USAGE` - Usage examples slide
- `CULTURAL` - Cultural notes slide
- `GRAMMAR` - Grammar explanations slide
- `PRONUNCIATION` - Pronunciation guide slide
- `SIMILAR` - Similar expressions slide

### `slide_generator.py`
Educational slide content generation using LLM.

**Key Classes:**
- `SlideContent` - Educational slide content dataclass
- `SlideContentGenerator` - Content generator using Gemini API

### `slide_renderer.py`
Slide rendering with image generation.

**Key Classes:**
- `SlideRenderer` - Renders slides to images

### `advanced_templates.py`
Advanced template configurations and layouts.

## Key Components

### SlideText Dataclass

```python
@dataclass
class SlideText:
    dialogue: str                    # Full dialogue line
    expression: str                   # Expression text
    dialogue_trans: str               # Dialogue translation
    expression_trans: str             # Expression translation
    similar1: Optional[str] = None   # First similar expression
    similar2: Optional[str] = None   # Second similar expression
```

### Creating Silent Slides

```python
def create_silent_slide(
    text: SlideText,
    duration: float,
    output_path: Path,
) -> Path:
    """
    Create silent slide video with text overlays.
    
    Args:
        text: Slide text content
        duration: Slide duration in seconds
        output_path: Output video path
        
    Returns:
        Path to created slide video
    """
```

**Features:**
- Uses background image or solid color
- Applies multiple text overlays (dialogue, expression, translations, similar)
- Configurable font sizes from settings
- Proper text cleaning and escaping for FFmpeg

### Slide Templates

The module supports multiple slide template types:

```python
class SlideType(Enum):
    EXPRESSION = "expression"      # Main expression display
    USAGE = "usage"                # Usage examples
    CULTURAL = "cultural"          # Cultural context
    GRAMMAR = "grammar"            # Grammar explanations
    PRONUNCIATION = "pronunciation" # Pronunciation guide
    SIMILAR = "similar"            # Similar expressions
```

**Template Configuration:**
```python
@dataclass
class SlideTemplate:
    template_type: SlideType
    background_color: str
    text_color: str
    font_family: str
    font_size: int
    title_font_size: int
    layout: Dict[str, Any]
    margins: Dict[str, int]
    spacing: Dict[str, int]
```

### Background Selection

The module automatically selects background:

```python
def _get_background_input() -> tuple[str, str]:
    """
    Get background input for slide.
    
    Tries in order:
    1. assets/education_slide_background.png
    2. assets/education_slide_background.jpg
    3. assets/background.png
    4. assets/background.jpg
    5. Fallback: Solid color (0x1a1a2e, 1920x1080)
    
    Returns:
        Tuple of (input_string, input_type)
    """
```

## Implementation Details

### Text Processing

Text is cleaned and escaped for FFmpeg drawtext filter:

```python
def _clean_for_draw(text: str, limit: int) -> str:
    """
    Clean text for drawtext filter.
    
    Removes:
    - Special characters: ', ", :, ,, \, newlines, tabs
    - Non-printable characters
    - Characters: @#$%^&*+=|<>
    
    Limits length to specified limit.
    """
```

### Font Configuration

Font sizes are retrieved from settings:

```python
def _font_size(key: str, default: int) -> int:
    """
    Get font size from settings.
    
    Keys:
    - expression_dialogue: Dialogue line font size
    - expression: Expression text font size
    - expression_dialogue_trans: Dialogue translation font size
    - expression_trans: Expression translation font size
    - similar: Similar expressions font size
    """
```

### FFmpeg Filter Chain

Slides use complex FFmpeg filter chains:

```python
# Background input
bg_input = _get_background_input()

# Text overlays using drawtext
filters = [
    f"drawtext=text='{dialogue}':fontsize={d_size}:...",
    f"drawtext=text='{expression}':fontsize={e_size}:...",
    f"drawtext=text='{dialogue_trans}':fontsize={dt_size}:...",
    f"drawtext=text='{expression_trans}':fontsize={et_size}:...",
    # Similar expressions if available
]

# Create video with specified duration
ffmpeg.input(bg_input[0], t=duration, loop=1, framerate=30)
    .output(output_path, vf=','.join(filters), ...)
```

## Dependencies

**External Libraries:**
- `ffmpeg-python` - Video processing and text overlay
- `Pillow` (PIL) - Image rendering (for slide_renderer)

**Internal Dependencies:**
- `langflix.settings` - Font and configuration access
- `langflix.core.models` - ExpressionAnalysis model
- `langflix.llm.gemini_client` - LLM content generation

**Assets Required:**
- `assets/education_slide_background.png` (optional)
- Font files (via `settings.get_font_file()`)

## Common Tasks

### Creating a Simple Slide

```python
from langflix.slides.generator import create_silent_slide, SlideText
from pathlib import Path

text = SlideText(
    dialogue="I need to break the ice with the new client.",
    expression="break the ice",
    dialogue_trans="새 고객과 분위기를 깨야 해요.",
    expression_trans="분위기를 깨다",
    similar1="start a conversation",
    similar2="make small talk"
)

output = create_silent_slide(
    text=text,
    duration=5.0,  # 5 seconds
    output_path=Path("slide.mkv")
)
```

### Using Slide Templates

```python
from langflix.slides.slide_templates import SlideTemplates, SlideType

templates = SlideTemplates()
expression_template = templates.get_template(SlideType.EXPRESSION)

# Customize template
expression_template.background_color = "#2a2a2a"
expression_template.font_size = 56
```

### Generating Slide Content with LLM

```python
from langflix.slides.slide_generator import SlideContentGenerator
from langflix.llm.gemini_client import GeminiClient

client = GeminiClient(api_key="...")
generator = SlideContentGenerator(client)

slide_content = await generator.generate_slide_content(expression)
```

## Gotchas and Notes

### Important Considerations

1. **Text Length:**
   - Text is limited to 100 characters per field
   - Longer text is truncated
   - Special characters are removed for FFmpeg compatibility

2. **Background Images:**
   - Prefers PNG over JPG
   - Falls back to solid color if images not found
   - Default color: Dark blue-gray (0x1a1a2e)

3. **Font Files:**
   - Font file path from settings
   - Falls back to system default if not found
   - Font file must be accessible to FFmpeg

4. **Text Positioning:**
   - Positions are hardcoded in filter chains
   - May need adjustment for different resolutions
   - Consider using layout configuration

5. **Duration:**
   - Silent slides have fixed duration
   - Audio-backed slides match audio length
   - Minimum duration: 1 second

### Performance Tips

- Cache background images
- Reuse font file paths
- Batch process multiple slides
- Use appropriate duration (not too long)

### Error Handling

- Missing background images fall back to solid color
- Font errors use system default
- Text cleaning prevents FFmpeg filter errors
- Invalid paths raise exceptions

### Current Implementation Status

**Note:** The current implementation focuses on silent slides with text overlays. Advanced features like:

- Image-based slide rendering (slide_renderer.py)
- LLM-generated content (slide_generator.py)
- Advanced templates (advanced_templates.py)

May be in development or used by other parts of the system.

## Related Documentation

- [Core Module](../core/README_eng.md) - Expression processing and video editing
- [Config Module](../config/README_eng.md) - Font and styling configuration
- [Media Module](../media/README_eng.md) - FFmpeg utilities

