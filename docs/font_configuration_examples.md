# Font Configuration Examples

This document provides practical examples of font configuration for different language pairs and video types in LangFlix.

## Table of Contents

1. [Single Language Configurations](#single-language-configurations)
2. [Dual Language Configurations](#dual-language-configurations)
3. [Real-World Pipeline Examples](#real-world-pipeline-examples)
4. [Testing Configurations](#testing-configurations)

## Single Language Configurations

### Spanish Learning Content (Target: Spanish)

```python
from langflix.core.video.font_resolver import FontResolver

# Configure for Spanish-only videos
resolver = FontResolver(default_language_code="es")

# Example: Render Spanish keywords overlay
def render_spanish_keywords(keywords: list[str], output_path: str):
    font_option = resolver.get_font_option_string(use_case="keywords")

    # Use with FFmpeg drawtext
    import ffmpeg
    (
        ffmpeg.input("input.mp4")
        .drawtext(
            text=", ".join(keywords),
            x="(w-text_w)/2",
            y="50",
            fontsize=28,
            fontcolor="white",
            box=1,
            boxcolor="black@0.5",
            **{font_option.rstrip(":"): ""}  # Convert "fontfile=/path:" to param
        )
        .output(output_path)
        .run()
    )
```

### Korean Learning Content (Target: Korean)

```python
# Configure for Korean-only videos
resolver = FontResolver(default_language_code="ko")

# Example: Render Korean title overlay
def render_korean_title(title: str, video_path: str, output_path: str):
    font_path = resolver.get_font_for_language(use_case="title")

    if not font_path:
        raise ValueError("Korean title font not found")

    import ffmpeg
    (
        ffmpeg.input(video_path)
        .drawtext(
            text=title,
            fontfile=font_path,
            x="(w-text_w)/2",
            y="100",
            fontsize=48,
            fontcolor="white",
            shadowcolor="black",
            shadowx=2,
            shadowy=2
        )
        .output(output_path)
        .run()
    )
```

## Dual Language Configurations

### Korean → Spanish (Learn Korean in Spanish)

```python
from langflix.core.video.font_resolver import FontResolver

# Initialize for Korean source, Spanish target
resolver = FontResolver(
    default_language_code="es",    # Target: Spanish (user's native language)
    source_language_code="ko"      # Source: Korean (learning language)
)

# Validate both languages before rendering
validation = resolver.validate_dual_language_support()
assert validation["source"], "Korean fonts not available"
assert validation["target"], "Spanish fonts not available"

print(f"✅ Source ({validation['source_language']}): {validation['source']}")
print(f"✅ Target ({validation['target_language']}): {validation['target']}")
```

#### Example 1: Expression with Translation

```python
def render_expression_with_translation(
    korean_expression: str,
    spanish_translation: str,
    video_path: str,
    output_path: str
):
    """Render Korean expression at top, Spanish translation at bottom."""

    # Get fonts for each language
    korean_font = resolver.get_source_font(use_case="expression")
    spanish_font = resolver.get_target_font(use_case="translation")

    import ffmpeg

    video = ffmpeg.input(video_path)

    # Korean expression at top (larger)
    video = video.drawtext(
        text=korean_expression,
        fontfile=korean_font,
        x="(w-text_w)/2",
        y="150",
        fontsize=56,
        fontcolor="white",
        borderw=2,
        bordercolor="black"
    )

    # Spanish translation at bottom (smaller)
    video = video.drawtext(
        text=spanish_translation,
        fontfile=spanish_font,
        x="(w-text_w)/2",
        y="h-200",
        fontsize=36,
        fontcolor="yellow",
        borderw=2,
        bordercolor="black"
    )

    video.output(output_path).run()
```

#### Example 2: Vocabulary Annotation (Side-by-side)

```python
def render_vocabulary_annotation(
    korean_word: str,
    spanish_meaning: str,
    position: tuple[int, int],
    video_path: str,
    output_path: str
):
    """Render vocabulary with source and target language side-by-side."""

    source_font, target_font = resolver.get_dual_fonts(use_case="vocabulary")

    x, y = position
    import ffmpeg

    video = ffmpeg.input(video_path)

    # Korean word (left)
    video = video.drawtext(
        text=korean_word,
        fontfile=source_font,
        x=str(x),
        y=str(y),
        fontsize=32,
        fontcolor="white",
        box=1,
        boxcolor="blue@0.7",
        boxborderw=5
    )

    # Spanish meaning (right, slightly offset)
    video = video.drawtext(
        text=spanish_meaning,
        fontfile=target_font,
        x=str(x),
        y=str(y + 40),
        fontsize=24,
        fontcolor="white",
        box=1,
        boxcolor="green@0.7",
        boxborderw=5
    )

    video.output(output_path).run()
```

### English → Korean (Learn English in Korean)

```python
# Configure for English source, Korean target
resolver = FontResolver(
    default_language_code="ko",    # Target: Korean
    source_language_code="en"      # Source: English
)

# Example: Render English dialogue with Korean subtitles
def render_dual_subtitles(
    english_dialogue: str,
    korean_translation: str,
    video_path: str,
    output_path: str
):
    english_font = resolver.get_source_font(use_case="dialogue")
    korean_font = resolver.get_target_font(use_case="translation")

    import ffmpeg

    video = ffmpeg.input(video_path)

    # English dialogue (top)
    video = video.drawtext(
        text=english_dialogue,
        fontfile=english_font,
        x="(w-text_w)/2",
        y="h-150",
        fontsize=28,
        fontcolor="white"
    )

    # Korean translation (bottom)
    video = video.drawtext(
        text=korean_translation,
        fontfile=korean_font,
        x="(w-text_w)/2",
        y="h-100",
        fontsize=24,
        fontcolor="yellow"
    )

    video.output(output_path).run()
```

### Japanese → English (Learn Japanese in English)

```python
resolver = FontResolver(
    default_language_code="en",    # Target: English
    source_language_code="ja"      # Source: Japanese
)

# Example: Educational slide with Japanese + English
def render_educational_slide(
    japanese_phrase: str,
    english_meaning: str,
    example_sentence: str,
    output_image_path: str
):
    """Create educational slide image with dual-language content."""

    japanese_font = resolver.get_source_font(use_case="educational_slide")
    english_font = resolver.get_target_font(use_case="educational_slide")

    # Create blank background using FFmpeg
    import ffmpeg

    (
        ffmpeg.input("color=c=navy:s=1080x1920:d=5", f="lavfi")
        .drawtext(
            text="Today's Phrase",
            fontfile=english_font,
            x="(w-text_w)/2",
            y="200",
            fontsize=40,
            fontcolor="white"
        )
        .drawtext(
            text=japanese_phrase,
            fontfile=japanese_font,
            x="(w-text_w)/2",
            y="400",
            fontsize=64,
            fontcolor="yellow"
        )
        .drawtext(
            text=english_meaning,
            fontfile=english_font,
            x="(w-text_w)/2",
            y="600",
            fontsize=48,
            fontcolor="white"
        )
        .drawtext(
            text=f"Example: {example_sentence}",
            fontfile=japanese_font,
            x="(w-text_w)/2",
            y="900",
            fontsize=32,
            fontcolor="lightblue"
        )
        .output(output_image_path, vframes=1)
        .run()
    )
```

## Real-World Pipeline Examples

### Complete Short-Form Video Pipeline

```python
from langflix.core.video.font_resolver import FontResolver
from langflix.core.video.overlay_renderer import OverlayRenderer
from langflix.core.video.short_form_creator import ShortFormCreator
from pathlib import Path

def create_korean_spanish_short_form(
    long_form_video: str,
    expression_data: dict,
    output_dir: str
):
    """
    Complete pipeline: Create short-form video with dual-language overlays.

    Args:
        long_form_video: Path to source long-form video
        expression_data: Dict with Korean expressions and Spanish translations
        output_dir: Output directory for short-form video
    """

    # Step 1: Initialize FontResolver for Korean→Spanish
    font_resolver = FontResolver(
        default_language_code="es",
        source_language_code="ko"
    )

    # Step 2: Validate fonts before processing
    validation = font_resolver.validate_dual_language_support()
    if not all([validation["source"], validation["target"]]):
        raise ValueError(f"Font validation failed: {validation}")

    # Step 3: Initialize OverlayRenderer with font resolver
    overlay_renderer = OverlayRenderer(
        font_resolver=font_resolver,
        output_dir=Path(output_dir) / "overlays",
        test_mode=False  # Production quality
    )

    # Step 4: Initialize ShortFormCreator
    short_form_creator = ShortFormCreator(
        overlay_renderer=overlay_renderer,
        output_dir=Path(output_dir),
        test_mode=False
    )

    # Step 5: Create short-form video with all overlays
    output_path = short_form_creator.create_short_form_from_long_form(
        long_form_video_path=long_form_video,
        expression=expression_data,
        viral_title="Learn Korean Fast!",  # Spanish title
        catchy_keywords=["#AprendeKoreano", "#ExpresionesKoreanas", "#KoreanLearning"],
        logo_path="/path/to/logo.png"
    )

    return output_path
```

### Batch Processing Multiple Languages

```python
from pathlib import Path

def process_multiple_language_pairs(video_path: str, output_base_dir: str):
    """Process same video for multiple target languages."""

    language_pairs = [
        ("ko", "es"),  # Korean → Spanish
        ("ko", "en"),  # Korean → English
        ("ja", "es"),  # Japanese → Spanish
        ("en", "ko"),  # English → Korean
    ]

    for source_lang, target_lang in language_pairs:
        print(f"Processing {source_lang} → {target_lang}...")

        # Initialize resolver for this language pair
        resolver = FontResolver(
            default_language_code=target_lang,
            source_language_code=source_lang
        )

        # Validate fonts
        if not resolver.validate_dual_language_support()["source"]:
            print(f"⚠️  Skipping {source_lang} → {target_lang}: Missing fonts")
            continue

        # Create output directory
        output_dir = Path(output_base_dir) / f"{source_lang}_to_{target_lang}"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Process video (simplified example)
        overlay_renderer = OverlayRenderer(
            font_resolver=resolver,
            output_dir=output_dir / "overlays",
            test_mode=False
        )

        # ... rendering logic ...

        print(f"✅ Completed {source_lang} → {target_lang}")
```

## Testing Configurations

### Test Mode with Fast Rendering

```python
from langflix.core.video.font_resolver import FontResolver
from langflix.core.video.overlay_renderer import OverlayRenderer

def test_font_rendering():
    """Quick test of font rendering with test_mode enabled."""

    resolver = FontResolver(
        default_language_code="es",
        source_language_code="ko"
    )

    # Test mode uses faster encoding
    overlay_renderer = OverlayRenderer(
        font_resolver=resolver,
        output_dir=Path("/tmp/test_overlays"),
        test_mode=True  # Fast encoding for testing
    )

    # Validate fonts before testing
    validation = resolver.validate_dual_language_support()
    print(f"Font validation: {validation}")

    # Test simple overlay
    test_video = "/tmp/test_input.mp4"
    output = overlay_renderer.add_viral_title(
        video_path=test_video,
        title="Test Title"
    )

    print(f"Test output: {output}")
```

### Font Discovery and Debugging

```python
def debug_font_configuration(source_lang: str, target_lang: str):
    """Debug helper to inspect font configuration."""

    resolver = FontResolver(
        default_language_code=target_lang,
        source_language_code=source_lang
    )

    print(f"\n{'='*60}")
    print(f"Font Configuration Debug: {source_lang} → {target_lang}")
    print(f"{'='*60}\n")

    # Show resolver state
    print(f"Resolver: {repr(resolver)}\n")

    # Validate dual-language support
    validation = resolver.validate_dual_language_support()
    print(f"Validation:")
    for key, value in validation.items():
        status = "✅" if value or isinstance(value, str) else "❌"
        print(f"  {status} {key}: {value}")

    # List all fonts for source language
    print(f"\n{source_lang.upper()} Fonts (Source):")
    source_fonts = resolver.get_all_fonts_for_language(source_lang)
    for use_case, font_path in source_fonts.items():
        status = "✅" if font_path else "❌"
        print(f"  {status} {use_case:20s}: {font_path or 'NOT FOUND'}")

    # List all fonts for target language
    print(f"\n{target_lang.upper()} Fonts (Target):")
    target_fonts = resolver.get_all_fonts_for_language(target_lang)
    for use_case, font_path in target_fonts.items():
        status = "✅" if font_path else "❌"
        print(f"  {status} {use_case:20s}: {font_path or 'NOT FOUND'}")

    print(f"\n{'='*60}\n")

# Run debug for your language pair
debug_font_configuration("ko", "es")
```

### Unit Test Configuration

```python
import pytest
from langflix.core.video.font_resolver import FontResolver

class TestFontConfiguration:
    """Test suite for font configuration validation."""

    @pytest.mark.parametrize("language_code", ["ko", "es", "en", "ja"])
    def test_single_language_support(self, language_code):
        """Test single language configuration."""
        resolver = FontResolver(default_language_code=language_code)
        assert resolver.validate_font_support(language_code)

    @pytest.mark.parametrize("source,target", [
        ("ko", "es"),
        ("ko", "en"),
        ("ja", "es"),
        ("en", "ko"),
    ])
    def test_dual_language_support(self, source, target):
        """Test dual-language configurations."""
        resolver = FontResolver(
            default_language_code=target,
            source_language_code=source
        )

        validation = resolver.validate_dual_language_support()
        assert validation["source"], f"Source font missing for {source}"
        assert validation["target"], f"Target font missing for {target}"

    def test_font_caching(self):
        """Test font caching behavior."""
        resolver = FontResolver(default_language_code="es")

        # First call
        font1 = resolver.get_font_for_language(use_case="keywords")
        cache_size_1 = len(resolver.font_cache)

        # Second call (should use cache)
        font2 = resolver.get_font_for_language(use_case="keywords")
        cache_size_2 = len(resolver.font_cache)

        assert font1 == font2
        assert cache_size_1 == cache_size_2

        # Clear cache
        resolver.clear_cache()
        assert len(resolver.font_cache) == 0
```

## Production Checklist

Before deploying font configuration to production:

- [ ] Validate all required language pairs using `validate_dual_language_support()`
- [ ] Test rendering on sample videos for each language
- [ ] Verify font files exist on production server
- [ ] Check font rendering quality at different resolutions (720p, 1080p)
- [ ] Test special characters (accents, diacritics, etc.)
- [ ] Verify fallback behavior when fonts are missing
- [ ] Monitor cache performance with `repr(resolver)`
- [ ] Test overlay layering (multiple overlays with different fonts)
- [ ] Verify FFmpeg font option strings are correctly formatted
- [ ] Test with both test_mode and production encoding settings

## Additional Resources

- **FontResolver API**: See [font_resolver_guide.md](./font_resolver_guide.md)
- **OverlayRenderer Integration**: See [overlay_renderer documentation]
- **Font Configuration**: See `langflix/config/font_utils.py`
- **Supported Languages**: See `langflix/config/default.yaml`
