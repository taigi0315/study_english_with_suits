# TICKET-V2-008: Optimize V2 Prompt Token Usage

## Priority: 🟠 High
## Type: Optimization

## Problem

Current V2 prompt still sends full dialogue timelines in input, but they're **unnecessary** since:
1. We have both source/target subtitles with timestamps
2. LLM only needs to identify **dialogue indices** (0-indexed)
3. Timestamps can be looked up from subtitles after LLM returns

**Current Token Usage (Estimated):**
- Input: ~500-800 tokens per dialogue line (text + timestamp)
- Output: ~300 tokens per expression

**Optimized Token Usage:**
- Input: ~200-400 tokens per dialogue line (just numbered text)
- Output: ~150 tokens per expression (just indices)

## Current Prompt Input Format

```
[0] (00:00:01,000 - 00:00:02,000): Hello!
[1] (00:00:03,000 - 00:00:04,000): How are you?
[2] (00:00:05,000 - 00:00:07,000): I'll knock it out of the park.
```

## Optimized Input Format

```
[0] Hello!
[1] How are you?
[2] I'll knock it out of the park.
```

## Current Output Fields

LLM returns:
- `expression` (text)
- `expression_dialogue_index` (number)
- `context_start_index` (number)
- `context_end_index` (number)
- `vocabulary_annotations` (word + dialogue_index)
- `title`, `catchy_keywords`, etc.

## What V2 Really Needs from LLM

The LLM should focus on **creative content**:
```json
{
  "expression": "knock it out of the park",
  "expression_dialogue_index": 2,
  "context_start_index": 0,
  "context_end_index": 3,
  "title": "완벽하게 해내다!",
  "catchy_keywords": ["자신감 폭발"],
  "vocabulary_annotations": [
    {"word": "knock", "dialogue_index": 2}
  ],
  "scene_type": "humor",
  "intro_hook": "영어로 '완벽하게 해내다'를 어떻게 말할까요?"
}
```

All timestamps are then looked up from subtitles post-processing.

## Required Changes

### 1. content_selection_analyzer.py
- Modify `_format_dialogues_for_prompt()` to exclude timestamps
- Just: `[{i}] {text}` not `[{i}] (start - end): {text}`

### 2. content_selection_prompt_v1.txt
- Remove references to timestamp format in output
- Clarify that timestamps are derived from indices

### 3. V2VocabularyAnnotation Model
- Currently only has `word` and `dialogue_index` ✅ (Already correct!)
- Translation is looked up from target_dialogues

### 4. enrich_content_selection() 
- Already populates timestamps from subtitles ✅ (Already correct!)

## Token Savings Estimate

| Version | Input (per chunk) | Output (per expr) | Total (5 chunks, 3 exprs) |
|---------|-------------------|-------------------|---------------------------|
| V1      | ~3000 tokens      | ~400 tokens       | ~16,200 tokens           |
| V2 Now  | ~2000 tokens      | ~300 tokens       | ~10,900 tokens           |
| V2 Opt  | ~1200 tokens      | ~200 tokens       | ~6,600 tokens            |

**~40% reduction** from current V2 implementation.

## Risk Assessment

- Low risk: Post-processing already handles timestamp lookup
- Edge case: Ensure dialogue indices are within bounds
- Testing: Verify with real subtitle data
