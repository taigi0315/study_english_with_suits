# [TICKET-V2-002] LLM Prompt Refocus - Content Selection

## Priority
- [x] Critical
- [ ] High
- [ ] Medium
- [ ] Low

## Type
- [x] Refactoring
- [ ] Feature Request
- [ ] Bug Fix

## Parent Epic
[EPIC-V2-001](./EPIC-V2-001-dual-language-architecture.md)

## Summary
Refactor the LLM prompt to focus purely on **content selection and annotation** rather than translation. Since we now have both source and target subtitles, the LLM should focus on:
- Finding engaging, educational moments
- Determining clip boundaries (start/end times)
- Selecting vocabulary for annotation
- Generating catchy keywords
- Scene type classification

## Background

### Current Prompt (V1) - `expression_analysis_prompt_v7.txt`
- 504 lines
- Handles BOTH translation AND content selection
- Complex instructions for natural translation (의역 vs 직역)
- Translation quality variable

### New Prompt (V2) - `content_selection_prompt_v1.txt`
- Focus: Content selection, engagement, educational value
- Input: Source subtitle + Target subtitle (already translated)
- Output: Selected clips with annotations, no translation needed
- Simpler, more focused prompt

## Current vs. New LLM Responsibilities

| Responsibility | V1 | V2 |
|---------------|-----|-----|
| Find expressions | ✓ | ✓ |
| Determine clip timing | ✓ | ✓ |
| Select vocabulary | ✓ | ✓ |
| Generate catch words | ✓ | ✓ |
| Classify scene type | ✓ | ✓ |
| **Translate dialogues** | ✓ | ✗ (from Netflix) |
| **Translate expression** | ✓ | ✗ (from Netflix) |

## New LLM Focus Areas

### 1. Content Selection Quality
- Is this scene engaging? (humor, drama, tension, sexy)
- Does this expression have educational value?
- Is the context compelling enough for a short video?

### 2. Clip Boundary Optimization
- Where should the clip start for maximum context?
- Where should it end for satisfying closure?
- Target duration guidance

### 3. Expression Identification
- Which expression in the dialogue is most valuable?
- What is the expression_dialogue line? (identify, not translate)
- Link expression to corresponding target language line

### 4. Vocabulary Annotation
- Which words deserve dynamic overlays?
- Match source words to target translations (from subtitle alignment)

### 5. Engagement Elements
- Catchy keywords (still generated in target language)
- Scene type classification
- Title generation

## New Input Format

```json
{
  "source_dialogue": [
    {"index": 1, "text": "I'll knock it out of the park.", "start": "00:01:00", "end": "00:01:03"},
    {"index": 2, "text": "You better.", "start": "00:01:03", "end": "00:01:05"}
  ],
  "target_dialogue": [
    {"index": 1, "text": "제가 완벽하게 처리해드릴게요.", "start": "00:01:00", "end": "00:01:03"},
    {"index": 2, "text": "그러는 게 좋을 거야.", "start": "00:01:03", "end": "00:01:05"}
  ],
  "source_language": "English",
  "target_language": "Korean"
}
```

## New Output Format

```json
{
  "expressions": [{
    "title": "회사에서 자신감 넘치는 한마디",
    "expression_dialogue_index": 1,
    "expression": "knock it out of the park",
    "context_start_time": "00:00:50",
    "context_end_time": "00:01:10",
    "catchy_keywords": ["자신감 폭발", "상사한테 한 마디"],
    "vocabulary_annotations": [
      {"word": "knock", "source_index": 1}
    ],
    "scene_type": "drama"
  }]
}
```

**Key Change:** `expression_dialogue_index` instead of `expression_dialogue` text + translations. The actual text comes from the subtitle files.

## Files to Create/Modify

| Action | File | Purpose |
|--------|------|---------|
| CREATE | `langflix/templates/content_selection_prompt_v1.txt` | New focused prompt |
| MODIFY | `langflix/core/expression_analyzer.py` | Use new prompt, accept dual subtitles |
| MODIFY | `langflix/core/models.py` | Update ExpressionAnalysis for index-based references |
| MODIFY | `langflix/config/default.yaml` | New template_file reference |
| CREATE | `tests/unit/test_content_selection.py` | Tests for new prompt output parsing |

## Acceptance Criteria

- [ ] New prompt template created
- [ ] expression_analyzer.py accepts DualSubtitle input
- [ ] Output model uses index references instead of text duplication
- [ ] Existing tests updated for new flow
- [ ] Manual test with real subtitles produces expected output

## Dependencies
- TICKET-V2-001: Dual Language Subtitle Support

## Notes
- Consider keeping V1 prompt as fallback during transition
- A/B test old vs new prompt quality if possible
