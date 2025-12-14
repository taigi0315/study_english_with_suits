# LangFlix V2 Configuration

## Overview

V2 introduces dual-language settings for Netflix subtitle support. All V1 configuration options remain valid.

## Configuration File

**Location:** `langflix/config/default.yaml`

## V2-Specific Settings

### Dual Language Mode

```yaml
dual_language:
  # Master switch for V2 dual-language features
  enabled: true
  
  # Source language: The language you're learning FROM (video audio)
  # This is typically English for most users
  source_language: "English"
  
  # Target language: Your native language (translate TO)
  # This is what subtitles/translations will be shown in
  target_language: "Korean"
```

### Language Codes

The system supports both full names and ISO codes:

| Full Name | ISO Code |
|-----------|----------|
| English   | en       |
| Korean    | ko       |
| Japanese  | ja       |
| Chinese   | zh       |
| Spanish   | es       |
| French    | fr       |

### Subtitle Discovery

```yaml
dual_language:
  subtitle_discovery:
    # Auto-detect Netflix folder format
    auto_detect: true
    
    # Patterns to match subtitle files
    source_pattern: "*English*"  # e.g., 7_English.srt
    target_pattern: "*Korean*"   # e.g., 4_Korean.srt
```

## UI Settings

The Create Content modal now includes:

1. **Source Language** (dropdown) - Language you're learning FROM
2. **Target Language** (checkboxes) - Your native language(s)

These values are sent to the API as:
- `source_language`: Single language code (e.g., "ko")
- `target_languages`: Array of language codes (e.g., ["en", "es"])

## API Configuration

### Environment Variables

```bash
# Enable V2 dual-language mode
LANGFLIX_DUAL_LANGUAGE_ENABLED=true

# Default source language (overridable per-request)
LANGFLIX_SOURCE_LANGUAGE=en
```

### Per-Request Override

Job creation supports per-request language settings:

```json
{
  "source_language": "ko",
  "target_languages": ["en"],
  "language_level": "intermediate"
}
```

## Font Configuration

V2 requires fonts for both source and target languages:

```yaml
fonts:
  # Font for source language (learning FROM)
  source_font: "NotoSansKR-Medium.ttf"
  
  # Font for target language (native language)
  target_font: "Roboto-Medium.ttf"
  
  # Fallback / universal font
  fallback_font: "NotoSans-Regular.ttf"
```

### Language-Font Mapping

```yaml
language_fonts:
  ko: "NotoSansKR-Medium.ttf"
  ja: "NotoSansJP-Medium.ttf"
  zh: "NotoSansSC-Medium.ttf"
  en: "Roboto-Medium.ttf"
  es: "Roboto-Medium.ttf"
  fr: "Roboto-Medium.ttf"
```

## Migration from V1

### Enabling V2

1. Update `config/default.yaml`:
   ```yaml
   dual_language:
     enabled: true
   ```

2. Ensure Netflix subtitle folders are in your media directory

3. Restart the application

### Fallback Behavior

If V2 is enabled but no dual subtitles are found, the system falls back to V1 mode automatically.

## Related Documents

- [ARCHITECTURE.md](./ARCHITECTURE.md) - How V2 dual-language works
- [v1/CONFIGURATION.md](./v1/CONFIGURATION.md) - Original V1 configuration
