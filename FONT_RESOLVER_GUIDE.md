# FontResolver Usage Guide

## 🎯 Purpose

FontResolver solves font issues across languages and video sections:
- ✅ Spanish fonts breaking (Latin Extended-A characters: é, ó, ñ)
- ✅ Font overlap issues
- ✅ Wrong fonts being used
- ✅ Different fonts per section (keywords, narrations, subtitles, etc.)

---

## 📖 Basic Usage

### 1. Import and Initialize

```python
from langflix.core.video.font_resolver import FontResolver

# Initialize with default language
resolver = FontResolver(default_language_code="es")  # Spanish

# Or without default (specify each time)
resolver = FontResolver()
```

### 2. Get Font for Language

```python
# Get default font for Spanish
font_path = resolver.get_font_for_language(language_code="es", use_case="default")
# Returns: "/System/Library/Fonts/Supplemental/Arial Unicode MS.ttf"

# Get font for Korean keywords
font_path = resolver.get_font_for_language(language_code="ko", use_case="keywords")

# Use default language (if set in __init__)
font_path = resolver.get_font_for_language(use_case="expression")
```

### 3. Get FFmpeg Font Option String

```python
# Get fontfile option for FFmpeg drawtext
font_option = resolver.get_font_option_string(language_code="es", use_case="default")
# Returns: "fontfile=/System/Library/Fonts/Supplemental/Arial Unicode MS.ttf:"

# Use in FFmpeg drawtext filter:
drawtext_filter = f"{font_option}text='Hola':fontsize=24:fontcolor=white"
```

### 4. Validate Font Support

```python
# Check if fonts are available for a language
is_supported = resolver.validate_font_support("es")
if not is_supported:
    print("⚠️ Spanish fonts not available!")
```

---

## 🎨 Use Cases (Sections)

FontResolver supports different font selections per video section:

| Use Case | Description | Example |
|----------|-------------|---------|
| `default` | General purpose | Subtitles, general text |
| `expression` | Main expression text | "throw someone off" |
| `keywords` | Keyword highlights | Bold/emphasized words |
| `narration` | Narration text | TTS narration overlays |
| `translation` | Translation text | Translated expressions |
| `vocabulary` | Vocabulary definitions | Dictionary-style text |
| `educational_slide` | Educational slides | Slide content |
| `title` | Video titles | Viral title overlays |
| `dialogue` | Dialogue subtitles | Character dialogue |

---

## 🌍 Language-Specific Examples

### Spanish (es) - Mixed Content Support

Spanish videos need fonts that support:
- Korean source text (CJK characters)
- Spanish target text (Latin Extended-A: é, ó, ñ, á, etc.)

```python
resolver = FontResolver(default_language_code="es")

# For narration (mixed Korean + Spanish)
narration_font = resolver.get_font_for_language(use_case="narration")
# Returns: Arial Unicode MS (best Unicode coverage)

# For keywords (Spanish only)
keyword_font = resolver.get_font_for_language(use_case="keywords")
# Returns: Helvetica Neue or Arial Unicode MS

# For expression text
expression_font = resolver.get_font_for_language(use_case="expression")
```

**Why it works:**
- Arial Unicode MS: Best Unicode coverage (CJK + Latin Extended-A)
- Helvetica Neue: Good Latin Extended support
- AppleSDGothicNeo: Fallback with CJK + basic Latin

### Korean (ko)

```python
resolver = FontResolver(default_language_code="ko")

# Korean uses AppleSDGothicNeo on macOS
font = resolver.get_font_for_language(use_case="default")
# Returns: "/System/Library/Fonts/AppleSDGothicNeo.ttc"

# Different use cases use the same font
expression_font = resolver.get_font_for_language(use_case="expression")
keywords_font = resolver.get_font_for_language(use_case="keywords")
```

### English (en)

```python
resolver = FontResolver(default_language_code="en")

# English can use system defaults
font = resolver.get_font_for_language(use_case="default")
```

---

## 🔧 In VideoEditor

FontResolver is automatically initialized in VideoEditor:

```python
from langflix.core.video_editor import VideoEditor

# VideoEditor initializes FontResolver with language_code
editor = VideoEditor(
    output_dir="output",
    language_code="es",  # Spanish
    source_language_code="ko"  # Learning Korean
)

# Use through VideoEditor methods
font_option = editor._get_font_option()  # Uses default use case
font_path = editor._get_font_path_for_use_case("es", "keywords")
```

---

## ⚙️ Font Configuration (YAML)

Fonts are configured in `langflix/config/default.yaml`:

```yaml
language_fonts:
  # Spanish configuration (mixed Korean + Spanish content)
  es:
    default: "/System/Library/Fonts/Supplemental/Arial Unicode MS.ttf"
    keywords: "/System/Library/Fonts/HelveticaNeue.ttc"
    expression: "/System/Library/Fonts/Supplemental/Arial Unicode MS.ttf"
    narration: "/System/Library/Fonts/Supplemental/Arial Unicode MS.ttf"

  # Korean configuration
  ko:
    default: "/System/Library/Fonts/AppleSDGothicNeo.ttc"
    keywords: "/System/Library/Fonts/AppleSDGothicNeo.ttc"

  # Global defaults (fallback)
  default:
    default: "/System/Library/Fonts/AppleSDGothicNeo.ttc"
    educational_slide: "assets/fonts/Maplestory_Bold.ttf"
```

**Resolution Priority:**
1. `language_fonts[language_code][use_case]`
2. `language_fonts[language_code]['default']`
3. `language_fonts['default'][use_case]`
4. `language_fonts['default']['default']`
5. Platform default (macOS/Linux/Windows)

---

## 🐛 Troubleshooting

### Issue: Spanish Characters Breaking (é, ó, ñ)

**Problem:** AppleSDGothicNeo doesn't render Latin Extended-A properly in FFmpeg drawtext.

**Solution:**
```python
# Use Arial Unicode MS for Spanish
resolver = FontResolver(default_language_code="es")
font = resolver.get_font_for_language(use_case="narration")
# ✅ Returns: Arial Unicode MS (supports é, ó, ñ, á, etc.)
```

**Configuration:**
```yaml
language_fonts:
  es:
    default: "/System/Library/Fonts/Supplemental/Arial Unicode MS.ttf"
    narration: "/System/Library/Fonts/Supplemental/Arial Unicode MS.ttf"
```

### Issue: Font Overlap

**Problem:** Different sections using incompatible fonts causing overlap.

**Solution:** Use consistent font sizing per use case:
```python
# Keywords: Larger, bold
keyword_font = resolver.get_font_for_language(use_case="keywords")
# Use with: fontsize=36

# Narration: Medium
narration_font = resolver.get_font_for_language(use_case="narration")
# Use with: fontsize=24

# Subtitles: Smaller
subtitle_font = resolver.get_font_for_language(use_case="dialogue")
# Use with: fontsize=18
```

### Issue: Wrong Fonts Being Used

**Problem:** Font not found, falling back to system default.

**Solution:** Validate fonts before processing:
```python
resolver = FontResolver(default_language_code="es")

# Check if Spanish fonts are available
if not resolver.validate_font_support("es"):
    print("⚠️ Spanish fonts not configured!")
    print("Please add Spanish fonts to config/default.yaml")

# Check specific use case
font = resolver.get_font_for_language(language_code="es", use_case="keywords")
if font is None:
    print("⚠️ Keywords font not found for Spanish!")
```

---

## 💡 Best Practices

### 1. Initialize Once, Reuse

```python
# ✅ Good: Initialize once at the start
resolver = FontResolver(default_language_code="es")

# Reuse throughout your code
font1 = resolver.get_font_for_language(use_case="keywords")
font2 = resolver.get_font_for_language(use_case="narration")
font3 = resolver.get_font_for_language(use_case="expression")
```

### 2. Use Caching

```python
# FontResolver automatically caches results
resolver = FontResolver(default_language_code="ko")

# First call: Resolves font
font1 = resolver.get_font_for_language(use_case="default")

# Second call: Uses cache (faster!)
font2 = resolver.get_font_for_language(use_case="default")
```

### 3. Validate Before Processing

```python
def process_video(language_code: str):
    resolver = FontResolver(default_language_code=language_code)

    # Validate first
    if not resolver.validate_font_support(language_code):
        raise ValueError(f"Fonts not available for {language_code}")

    # Now safe to use
    font = resolver.get_font_for_language(use_case="narration")
    # ... process video
```

### 4. Log Font Paths for Debugging

```python
import logging
logger = logging.getLogger(__name__)

resolver = FontResolver(default_language_code="es")

# Get fonts for all use cases
use_cases = ["default", "keywords", "expression", "narration"]
for use_case in use_cases:
    font = resolver.get_font_for_language(use_case=use_case)
    logger.info(f"Spanish {use_case}: {font}")
```

---

## 🔍 Quick Reference

```python
# Initialize
resolver = FontResolver(default_language_code="es")

# Get font path
font = resolver.get_font_for_language(language_code="es", use_case="keywords")

# Get FFmpeg option
option = resolver.get_font_option_string(language_code="es", use_case="keywords")

# Validate
is_ok = resolver.validate_font_support("es")

# Use in FFmpeg
drawtext = f"{option}text='Hola':fontsize=24:fontcolor=white:x=100:y=100"
```

---

## 📝 Platform Notes

### macOS
- Primary: Arial Unicode MS (`/System/Library/Fonts/Supplemental/Arial Unicode MS.ttf`)
- Fallback: Helvetica Neue (`/System/Library/Fonts/HelveticaNeue.ttc`)
- CJK: AppleSDGothicNeo (`/System/Library/Fonts/AppleSDGothicNeo.ttc`)

### Linux/Docker
- Primary: Noto Sans CJK (`/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc`)
- Fallback: Nanum Gothic (`/usr/share/fonts/truetype/nanum/NanumGothic.ttc`)

### Windows
- Primary: Malgun Gothic (`C:/Windows/Fonts/malgun.ttf`)
- Fallback: Arial (`C:/Windows/Fonts/arial.ttf`)

---

## 🎉 Summary

FontResolver gives you:
- ✅ **Language-specific fonts** - Different fonts per language
- ✅ **Section-specific fonts** - Different fonts per video section
- ✅ **Automatic caching** - Fast repeated lookups
- ✅ **Graceful fallbacks** - Never crashes if font missing
- ✅ **Easy configuration** - YAML-based font settings
- ✅ **Multi-platform** - macOS, Linux, Windows support

**Your font issues are now solved!** 🎨
