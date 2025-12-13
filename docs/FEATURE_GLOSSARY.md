# LangFlix Feature Glossary

Standard terminology for visual features in generated videos.

## Visual Layout Reference

```
┌────────────────────────────────────────┐
│          TOP BLACK PADDING              │  ← Catch Words
│          (440px)                        │
├────────────────────────────────────────┤
│                                        │
│                                        │
│            VIDEO AREA                  │
│           (1040px)                     │  ← Vocabulary Annotations
│                                        │     (random position)
│                                        │
│    ────────────────────────────────    │  ← Dialogue Subtitles
│    "[Source dialogue]"                 │     (over video bottom)
│    "[Target translation]"              │
│                                        │
├────────────────────────────────────────┤
│          BOTTOM BLACK PADDING           │
│          (440px)                        │
│                                        │
│    Expression: [phrase]                │  ← Expression Display
│    Translation: [translation]          │
│                                        │
└────────────────────────────────────────┘
```

## Standard Feature Names

### Catch Words
- **Location:** Top black padding
- **Config Key:** `short_video.layout.keywords`
- **LLM Output Field:** `catchy_keywords`
- **Purpose:** Engaging keywords/hashtags to hook viewers
- **Language:** Target language (Korean, Spanish, etc.)
- **Example:** "상사한테 한 마디!", "자신감 폭발"

### Vocabulary Annotations
- **Location:** Random position within video area
- **Config Key:** `short_video.layout.vocabulary_annotations`
- **LLM Output Field:** `vocabulary_annotations`
- **Purpose:** Dynamic word overlays when words are spoken
- **Format:** "word = translation"
- **Example:** "knock = 치다"

### Expression Display
- **Location:** Bottom black padding
- **Config Key:** `short_video.layout.expression`, `short_video.layout.translation`
- **LLM Output Fields:** `expression`, `expression_translation`
- **Purpose:** The main expression being taught + translation
- **Example:** "knock it out of the park" + "완벽하게 해내다"

### Dialogue Subtitles
- **Location:** Over video, near bottom
- **Config Key:** `short_video.layout.dialogue_subtitle`
- **LLM Output Fields:** `dialogues`, `translation`
- **Purpose:** Full dialogue context with translation
- **Style:** Two lines (source above, target below)

## V1 → V2 Terminology Changes

| V1 Term | V2 Standard | Notes |
|---------|-------------|-------|
| `catchy_keywords` | **Catch Words** | Keep field name, use display name |
| `keywords` (config) | `catch_words` | Optional rename for clarity |
| `expression_highlight` | **Expression Display** | Merged with translation_highlight |
| `translation_highlight` | **Expression Display** | Part of same feature |
| `subtitle_styling.expression_highlight` | Remove | Duplicate of expression display |

## LLM Output Fields Reference

```json
{
  "title": "Catchy title in target language",
  "catchy_keywords": ["keyword1", "keyword2"],
  "expression": "The key phrase to learn",
  "expression_translation": "Translation of expression",
  "dialogues": ["Line 1", "Line 2"],
  "translation": ["Line 1 translated", "Line 2 translated"],
  "vocabulary_annotations": [
    {"word": "phrase", "translation": "번역", "dialogue_index": 0}
  ],
  "scene_type": "humor|drama|tension|emotional|witty|sexy|surprising",
  "intro_hook": "Hook question in target language"
}
```

## Configuration Quick Reference

| Feature | Config Path | Default |
|---------|-------------|---------|
| Catch Words Font Size | `short_video.layout.keywords.font_size` | 50 |
| Expression Font Size | `short_video.layout.expression.font_size` | 50 |
| Translation Font Size | `short_video.layout.translation.font_size` | 50 |
| Vocabulary Font Size | `short_video.layout.vocabulary_annotations.font_size` | 50 |
| Dialogue Font Size | `short_video.layout.dialogue_subtitle.font_size` | 9 |
