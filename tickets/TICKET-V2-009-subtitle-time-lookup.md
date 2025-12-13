# TICKET-V2-009: Subtitle Index-Based Time Lookup

## Priority: 🟠 High
## Type: Enhancement

## Overview

Implement the core V2 philosophy: **LLM provides indices, system looks up times from subtitles**.

This ticket formalizes the time lookup pipeline that was sketched in V2-001 and V2-002.

## Current Flow (V1)

```
Subtitles → LLM → {expression, context_start_time, context_end_time, ...}
                         ↓
                   Video Slicer uses timestamps directly
```

## V2 Flow

```
Source Subtitles ─┐
                  ├→ LLM → {expression, context_start_index, context_end_index, ...}
Target Subtitles ─┘           ↓
                   enrich_content_selection()
                              ↓
                   {expression, expression_translation, context_start_time, context_end_time}
                              ↓
                        Video Slicer
```

## Key Functions

### 1. Subtitle Index → Time Lookup (EXISTING)

```python
# content_selection_models.py: enrich_content_selection()
def enrich_content_selection(selection, source_dialogues, target_dialogues):
    # Get context start time from source dialogues
    if 0 <= selection.context_start_index < len(source_dialogues):
        start_line = source_dialogues[selection.context_start_index]
        selection.context_start_time = start_line.get('start', '')
    
    # Get context end time
    if 0 <= selection.context_end_index < len(source_dialogues):
        end_line = source_dialogues[selection.context_end_index]
        selection.context_end_time = end_line.get('end', '')
```

### 2. Expression Word Search (NEW)

When vocabulary annotation contains just `word` and `dialogue_index`, we need to:
1. Get the source dialogue text at `dialogue_index`
2. Find the exact position of `word` in that dialogue
3. Calculate approximate timestamp within that dialogue (optional)

### 3. Translation Lookup (EXISTING)

```python
# Already in enrich_content_selection()
if 0 <= selection.expression_dialogue_index < len(target_dialogues):
    target_line = target_dialogues[selection.expression_dialogue_index]
    selection.expression_translation = target_line.get('text', '')
```

## Edge Cases

### 1. Misaligned Subtitle Counts
- Source has 38 entries, target has 744 entries (observed in real data)
- Solution: Use ONLY source subtitles for timestamps
- Target subtitles are used for text only, not timing

### 2. Index Out of Bounds
- LLM returns index > len(dialogues)
- Solution: Clamp to valid range + warning log

### 3. Empty Dialogue at Index
- Source dialogue at index has empty text
- Solution: Skip or use previous/next dialogue

### 4. Multi-Variant Subtitles
- Multiple subtitle files per language (e.g., 3_Korean.srt, 4_Korean.srt)
- Solution: V2-005 config `variant_selection` controls which to use

## Implementation Tasks

1. [ ] Verify `enrich_content_selection()` handles edge cases
2. [ ] Add index validation with warnings
3. [ ] Add unit tests for edge cases
4. [ ] Test with real Netflix subtitle data (aligned vs misaligned)

## Dependencies

- V2-001: DualSubtitle model
- V2-002: V2ContentSelection model
- V2-008: Token optimization (removes timestamps from input)
