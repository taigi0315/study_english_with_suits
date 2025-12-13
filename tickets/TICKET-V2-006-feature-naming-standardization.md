# [TICKET-V2-006] Feature Consolidation & Naming Standardization

## Priority
- [ ] Critical
- [ ] High
- [x] Medium
- [ ] Low

## Type
- [x] Refactoring
- [ ] Feature Request
- [ ] Bug Fix

## Parent Epic
[EPIC-V2-001](./EPIC-V2-001-dual-language-architecture.md)

## Summary
Standardize feature naming across the codebase. Define clear, consistent terminology for all display features and where they appear.

## Background
The current codebase has confusing and inconsistent naming for visual features. This ticket establishes a clear terminology.

## Feature Definitions (V2 Standard)

| Feature Name | Config Key | Display Location | Description |
|--------------|------------|------------------|-------------|
| **Catch Words** | `catch_words` | Top black padding | Engaging keywords/hashtags to hook viewers (in target language) |
| **Vocabulary Annotations** | `vocabulary_annotations` | Random on-screen | Dynamic word overlays that appear when words are spoken |
| **Expression Display** | `expression_display` | Bottom black padding | The main expression + translation being taught |
| **Dialogue Subtitles** | `dialogue_subtitles` | Over video | Full dialogue with translation during context clip |

## Visual Layout Reference

```
┌────────────────────────────────────────┐
│          TOP BLACK PADDING              │  ← Catch Words: "상사한테 한 마디!"
│          (Catch Words)                  │
├────────────────────────────────────────┤
│                                        │
│                                        │
│            VIDEO AREA                  │
│                                        │  ← Vocabulary Annotations (random position)
│                                        │     "knock = 치다"
│                                        │
│    ────────────────────────────────    │  ← Dialogue Subtitles (over video)
│    "I'll knock it out of the park."   │
│    "제가 완벽하게 처리해드릴게요."        │
│                                        │
├────────────────────────────────────────┤
│          BOTTOM BLACK PADDING           │
│                                        │
│    Expression: knock it out of the park│  ← Expression Display
│    Translation: 완벽하게 해내다          │
│                                        │
└────────────────────────────────────────┘
```

## Current Naming Confusion

| Current Term | Used In | New Standard Term |
|--------------|---------|-------------------|
| `catchy_keywords` | models.py, prompt | `catch_words` |
| `keywords` | default.yaml | `catch_words` |
| `vocabulary_annotations` | models.py | ✓ Keep |
| `expression` | everywhere | `expression_display.source` |
| `expression_translation` | models.py | `expression_display.target` |
| `dialogue_subtitle` | default.yaml | `dialogue_subtitles` (plural) |
| `expression_highlight` | default.yaml | Remove (duplicate of expression_display) |
| `translation_highlight` | default.yaml | Remove (duplicate) |

## Requirements

### 1. Update Models
```python
# langflix/core/models.py

class CatchWords(BaseModel):
    """Engaging keywords for top padding"""
    phrases: List[str]  # e.g., ["상사한테 한 마디", "자신감 폭발"]

class VocabularyAnnotation(BaseModel):
    """Dynamic word overlays"""
    word: str
    translation: str
    dialogue_index: int

class ExpressionDisplay(BaseModel):
    """Main expression in bottom padding"""
    source: str     # "knock it out of the park"
    target: str     # "완벽하게 해내다"
```

### 2. Update Configuration
- Rename keys in default.yaml
- Update short_video.layout section
- Remove duplicate/unused settings

### 3. Update Codebase References
- Search for old terms
- Replace with new standard terms
- Update comments and docstrings

### 4. Update Documentation
- Create feature glossary
- Update README with visual reference
- Update any user-facing docs

## Files to Modify

| Action | File | Purpose |
|--------|------|---------|
| MODIFY | `langflix/core/models.py` | Standardize model names |
| MODIFY | `langflix/config/default.yaml` | Rename config keys |
| MODIFY | `langflix/core/video_editor.py` | Update references |
| MODIFY | `langflix/templates/*.txt` | Update prompt terminology |
| CREATE | `docs/FEATURE_GLOSSARY.md` | Document standard terms |

## Acceptance Criteria

- [ ] Feature terminology documented in glossary
- [ ] Models use standard names
- [ ] Config uses standard keys
- [ ] Video editor uses standard terms
- [ ] All tests pass
- [ ] README updated with visual reference

## Dependencies
- TICKET-V2-005: Config Cleanup (do cleanup first, then naming)

## Notes
- This is a naming/terminology change, not functionality
- May require updating tests that reference old names
- Consider backward compatibility aliases during transition
