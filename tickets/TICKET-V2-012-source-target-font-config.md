# TICKET-V2-012: Source+Target Language Font Config

## Priority: 🔴 Critical
## Type: Enhancement

## Problem

Current font config assumes ONE language code (`self.language_code`), but V2 needs BOTH:

- **Source language** (e.g., Korean) - for expression text, source dialogue
- **Target language** (e.g., Spanish) - for translations, catch words, vocabulary translations

## Current Implementation

```python
# video_editor.py
class VideoEditor:
    def __init__(self, ..., language_code=...):
        self.language_code = language_code  # ONLY ONE!

    def _get_font_path_for_use_case(self, language_code, use_case):
        # Uses single language_code
```

## Required Changes

### 1. VideoEditor Constructor

```python
class VideoEditor:
    def __init__(
        self, ...,
        source_language_code: str = "en",
        target_language_code: str = "ko",
    ):
        self.source_language_code = source_language_code
        self.target_language_code = target_language_code
```

### 2. Font Selection for Different Elements

| Element | Language | Use Case |
|---------|----------|----------|
| Expression text | SOURCE | `expression` |
| Expression translation | TARGET | `translation` |
| Dialogue (source) | SOURCE | `dialogue` |
| Dialogue translation | TARGET | `dialogue` |
| Catch Words | TARGET | `keywords` |
| Vocabulary word | SOURCE | `vocabulary` |
| Vocabulary translation | TARGET | `vocabulary` |
| Educational slide expression | SOURCE | `educational_slide` |
| Educational slide translation | TARGET | `educational_slide` |

### 3. default.yaml Font Config

Already has language entries:
```yaml
font:
  language_fonts:
    default: ...
    ko: ...  # Korean
    es: ...  # Spanish
```

Need to ensure common source languages are covered:
- `en` (English)
- `ko` (Korean)
- `es` (Spanish)
- `ja` (Japanese) - for future
- `zh` (Chinese) - for future

### 4. Language Code Detection

From Netflix subtitle filenames:
- `3_Korean.srt` → `ko`
- `6_English.srt` → `en`
- `5_Spanish.srt` → `es`

Need mapping function:
```python
def language_name_to_code(name: str) -> str:
    mapping = {
        "Korean": "ko",
        "English": "en",
        "Spanish": "es",
        "Japanese": "ja",
        "Chinese": "zh",
    }
    return mapping.get(name, "en")  # Default to English
```

## Implementation Tasks

1. [ ] Add `source_language_code` to VideoEditor
2. [ ] Update font selection calls with correct language
3. [ ] Add language name → code mapping function
4. [ ] Ensure default.yaml has entries for common source languages
5. [ ] Test with Korean source + Spanish target
6. [ ] Test with English source + Korean target

## Testing

- Create video with mixed language text
- Verify Korean characters render with Korean font
- Verify Spanish characters render with Spanish font
- Verify no broken glyphs in vocabulary annotations
