# TICKET-V2-007: Dual-Font Vocabulary Annotations

## Priority: 🔴 Critical
## Type: Bug Fix / Enhancement

## Problem

Vocabulary annotations show both source and target language text but render with a **single font**. This breaks character rendering for mixed-language displays.

**Current Code** (video_editor.py:1094):
```python
annot_text = f"{word} : {translation}"  # One drawtext call, one font
```

**Screenshot Example:**
- Text: `던지다 : querida/extrañada`
- Issue: Korean characters `던지다` rendered with Spanish font → broken glyphs

## Root Cause

1. Vocabulary annotation is rendered as one `drawtext` filter with one font
2. `word` is in source language (e.g., Korean)
3. `translation` is in target language (e.g., Spanish)
4. System selects font based on `self.language_code` which is the target language

## Proposed Solution

Split vocabulary annotation into TWO separate `drawtext` calls:

```python
# 1. Render source word with SOURCE language font
word_text = escape_drawtext_string(word)
source_font = self._get_font_path_for_use_case(source_language_code, "vocabulary")

# 2. Render separator with neutral font
separator_text = " : "

# 3. Render translation with TARGET language font  
translation_text = escape_drawtext_string(translation)
target_font = self._get_font_path_for_use_case(target_language_code, "vocabulary")

# Position them sequentially
# word_x → separator_x → translation_x
```

## Required Changes

### 1. VideoEditor Initialization
- Accept `source_language_code` in addition to `target_language_code`
- Store both for font lookups

### 2. video_editor.py Vocabulary Section (~lines 1079-1138)
- Split single `drawtext` into THREE calls
- Calculate X positions for sequential layout
- Use appropriate font for each segment

### 3. Font Config (default.yaml)
- Ensure `font.language_fonts` has entries for common source languages
- Current config has: `ko`, `es`, `default`

## Visual Layout (Before/After)

**Before (BROKEN):**
```
던지다 : querida/extrañada  ← All same font, Korean chars broken
```

**After (FIXED):**
```
[던지다] : [querida/extrañada]
   ↑           ↑
Korean      Spanish
  font        font
```

## Testing

- Create video with Korean source + Spanish target
- Create video with English source + Korean target
- Verify all characters render correctly in both cases

## Dependencies

- V2-005 config (dual_language section)
- V2-001 (DualSubtitle with language info)
