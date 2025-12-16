# FontResolver Usage Guide

## Overview

`FontResolver` is a centralized font management system for multi-language video rendering in LangFlix. It handles font resolution, caching, and provides FFmpeg-compatible font options for dual-language educational videos.

## Quick Start

### Basic Usage (Single Language)

```python
from langflix.core.video.font_resolver import FontResolver

# Initialize for Spanish videos
resolver = FontResolver(default_language_code="es")

# Get font for different use cases
default_font = resolver.get_font_for_language(use_case="default")
keyword_font = resolver.get_font_for_language(use_case="keywords")
translation_font = resolver.get_font_for_language(use_case="translation")

# Get FFmpeg font option string
font_option = resolver.get_font_option_string(use_case="keywords")
# Returns: "fontfile=/path/to/spanish/font.ttf:"
```

### Dual-Language Mode (Source + Target)

```python
# Initialize with both source and target languages
resolver = FontResolver(
    default_language_code="es",    # Target language (user's native language)
    source_language_code="ko"      # Source language (language being learned)
)

# Get source language font (for Korean expressions)
korean_font = resolver.get_source_font(use_case="expression")

# Get target language font (for Spanish translations)
spanish_font = resolver.get_target_font(use_case="translation")

# Get both fonts for dual-language rendering
source_font, target_font = resolver.get_dual_fonts(use_case="vocabulary")
```

## Use Cases

FontResolver supports different use cases optimized for specific rendering scenarios:

| Use Case | Description | Typical Language |
|----------|-------------|------------------|
| `default` | General text rendering | Target |
| `expression` | Main expression text | Source |
| `keywords` | Hashtag keywords | Target |
| `translation` | Translated text | Target |
| `vocabulary` | Vocabulary annotations | Both (dual) |
| `narration` | Narration overlays | Target |
| `dialogue` | Dialogue subtitles | Source or Target |
| `title` | Video titles | Target |
| `educational_slide` | Educational slide content | Target |

## Common Patterns

### Pattern 1: Overlay Rendering (Single Language)

```python
from langflix.core.video.font_resolver import FontResolver

def render_keywords_overlay(keywords: list[str], language_code: str):
    resolver = FontResolver(default_language_code=language_code)

    # Get font for keywords
    font_option = resolver.get_font_option_string(use_case="keywords")

    # Use in FFmpeg drawtext filter
    drawtext_filter = f"{font_option}text='{', '.join(keywords)}':fontsize=24"
    return drawtext_filter
```

### Pattern 2: Dual-Language Vocabulary Annotations

```python
def render_vocabulary_annotation(
    source_word: str,
    target_translation: str,
    source_lang: str,
    target_lang: str
):
    resolver = FontResolver(
        default_language_code=target_lang,
        source_language_code=source_lang
    )

    # Get both fonts
    source_font, target_font = resolver.get_dual_fonts(use_case="vocabulary")

    # Build dual-language overlay
    source_option = resolver.get_source_font_option(use_case="vocabulary")
    target_option = resolver.get_target_font_option(use_case="vocabulary")

    return {
        "source": {"text": source_word, "font": source_font, "option": source_option},
        "target": {"text": target_translation, "font": target_font, "option": target_option}
    }
```

### Pattern 3: Font Validation Before Rendering

```python
def safe_render_with_validation(language_code: str):
    resolver = FontResolver(default_language_code=language_code)

    # Validate font support before rendering
    if not resolver.validate_font_support(language_code):
        raise ValueError(f"No font support for language: {language_code}")

    # Proceed with rendering
    font_path = resolver.get_font_for_language(use_case="default")
    return font_path
```

### Pattern 4: Dual-Language Validation

```python
def validate_dual_language_setup(source_lang: str, target_lang: str):
    resolver = FontResolver(
        default_language_code=target_lang,
        source_language_code=source_lang
    )

    # Validate both languages
    validation = resolver.validate_dual_language_support()

    if not validation["source"]:
        raise ValueError(f"Missing font for source language: {source_lang}")
    if not validation["target"]:
        raise ValueError(f"Missing font for target language: {target_lang}")

    return validation
```

## API Reference

### Initialization

```python
FontResolver(
    default_language_code: Optional[str] = None,  # Target language
    source_language_code: Optional[str] = None    # Source language
)
```

### Core Methods

#### `get_font_for_language(language_code, use_case)`
Get font path for specific language and use case.

**Parameters:**
- `language_code` (Optional[str]): Language code (e.g., "ko", "es"). Uses default if not provided.
- `use_case` (str): Use case (default: "default")

**Returns:** Font file path or None

**Example:**
```python
font = resolver.get_font_for_language("es", "keywords")
# Returns: "/System/Library/Fonts/SFPro.ttf"
```

#### `get_source_font(use_case)`
Convenience method for source language font.

**Example:**
```python
korean_font = resolver.get_source_font("expression")
```

#### `get_target_font(use_case)`
Convenience method for target language font.

**Example:**
```python
spanish_font = resolver.get_target_font("translation")
```

#### `get_dual_fonts(use_case)`
Get both source and target fonts for dual-language rendering.

**Returns:** Tuple of (source_font_path, target_font_path)

**Example:**
```python
source, target = resolver.get_dual_fonts("vocabulary")
```

### FFmpeg Integration Methods

#### `get_font_option_string(language_code, use_case)`
Get FFmpeg-compatible font option string.

**Returns:** String like "fontfile=/path/to/font.ttf:" or empty string

**Example:**
```python
option = resolver.get_font_option_string("es", "keywords")
# Returns: "fontfile=/System/Library/Fonts/SFPro.ttf:"
```

#### `get_source_font_option(use_case)`
FFmpeg font option for source language.

#### `get_target_font_option(use_case)`
FFmpeg font option for target language.

### Validation Methods

#### `validate_font_support(language_code)`
Check if font is available for language.

**Returns:** bool

#### `validate_dual_language_support()`
Validate both source and target language fonts.

**Returns:** Dictionary with validation status

```python
{
    "source": True,
    "target": True,
    "source_language": "ko",
    "target_language": "es"
}
```

### Utility Methods

#### `get_all_fonts_for_language(language_code)`
Get all font paths for all use cases.

**Returns:** Dictionary mapping use_case to font_path

#### `clear_cache()`
Clear the font cache.

## Caching Behavior

FontResolver automatically caches font lookups for performance:

```python
resolver = FontResolver(default_language_code="es")

# First call - hits font_utils and caches result
font1 = resolver.get_font_for_language(use_case="keywords")

# Second call - returns cached result (faster)
font2 = resolver.get_font_for_language(use_case="keywords")

# Clear cache if needed
resolver.clear_cache()
```

Cache keys include both language code and use case: `"es:keywords"`

## Integration with OverlayRenderer

```python
from langflix.core.video.font_resolver import FontResolver
from langflix.core.video.overlay_renderer import OverlayRenderer

# Initialize with dual-language support
font_resolver = FontResolver(
    default_language_code="es",
    source_language_code="ko"
)

# Pass to OverlayRenderer
overlay_renderer = OverlayRenderer(
    font_resolver=font_resolver,
    output_dir="/tmp/overlays",
    test_mode=True
)

# OverlayRenderer automatically uses correct fonts for each overlay type
overlay_renderer.add_viral_title(...)  # Uses target language font
overlay_renderer.add_expression_text(...)  # Uses source + target fonts
overlay_renderer.add_vocabulary_annotations(...)  # Uses dual fonts
```

## Troubleshooting

### Font Not Found

```python
resolver = FontResolver(default_language_code="unknown")
font = resolver.get_font_for_language(use_case="default")
# Returns: None

# Check validation first
if not resolver.validate_font_support("unknown"):
    print("Font not supported for this language")
```

### Missing Font File

FontResolver checks if font file exists:

```python
# If font_utils returns path but file doesn't exist
font = resolver.get_font_for_language("es", "default")
# Returns: None (logged as warning)
```

### Debugging Font Resolution

```python
# Get all fonts for a language to debug
fonts = resolver.get_all_fonts_for_language("es")
for use_case, font_path in fonts.items():
    print(f"{use_case}: {font_path}")

# Check resolver state
print(repr(resolver))
# Output: FontResolver(target=es, source=ko, cache_size=5)
```

## Best Practices

1. **Initialize Once**: Create FontResolver once and reuse it
   ```python
   # Good
   resolver = FontResolver(default_language_code="es")
   for item in items:
       font = resolver.get_font_for_language(use_case="keywords")

   # Bad - creates new resolver each time
   for item in items:
       resolver = FontResolver(default_language_code="es")
       font = resolver.get_font_for_language(use_case="keywords")
   ```

2. **Use Convenience Methods**: For dual-language, use `get_source_font()` / `get_target_font()`
   ```python
   # Good - clear intent
   source_font = resolver.get_source_font("expression")

   # Less clear
   source_font = resolver.get_font_for_language(resolver.source_language_code, "expression")
   ```

3. **Validate Before Rendering**: Check font support before expensive operations
   ```python
   if not resolver.validate_dual_language_support()["source"]:
       raise ValueError("Source language font not available")

   # Proceed with rendering...
   ```

4. **Use Appropriate Use Cases**: Match use case to content type
   ```python
   # Good - specific use cases
   resolver.get_font_for_language(use_case="keywords")     # For hashtags
   resolver.get_font_for_language(use_case="expression")   # For expressions

   # Less optimal - using default for everything
   resolver.get_font_for_language(use_case="default")
   ```

## Migration from Old Code

If you have code directly calling `font_utils`:

```python
# Old approach
from langflix.config.font_utils import get_font_file_for_language
font = get_font_file_for_language("es", "keywords")

# New approach with caching and validation
from langflix.core.video.font_resolver import FontResolver
resolver = FontResolver(default_language_code="es")
font = resolver.get_font_for_language(use_case="keywords")
```

Benefits of migration:
- Automatic caching for repeated lookups
- Built-in validation
- Dual-language support
- FFmpeg integration helpers
- Consistent API across codebase
