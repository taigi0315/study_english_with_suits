# TICKET-088: Eliminate Duplicate LLM Translation Calls

## Summary
The translation pipeline makes redundant LLM API calls. The initial expression analysis already returns translations in the `ExpressionAnalysis` model, but `TranslationService` makes additional LLM calls to re-translate the same content.

## Problem

### Current Behavior
1. `expression_analyzer.py` calls Gemini API and returns `ExpressionAnalysis` with:
   - `translation`: List of translated dialogues
   - `expression_translation`: Translated expression
   - `expression_dialogue_translation`: Translated expression dialogue
   
2. `TranslationService.translate()` then calls `translate_expression_to_language()` which makes **another** Gemini API call to translate the same content again

### Evidence from Logs
```
14:33:09 | INFO | ✅ Expression 1 validated: 'break a sweat' (5 dialogues/translations)
14:33:09 | INFO | Translating expression 'break a sweat' to ko
14:33:09 | INFO | Sending translation request to Gemini API for ko...
```

The translations already exist from the first call, but a second API call is made.

### Impact
- **Wasted API costs**: Each expression triggers 2 API calls instead of 1
- **Increased latency**: Extra ~15-20 seconds per expression for unnecessary translation
- **Rate limiting**: More likely to hit API quotas

## Root Cause Analysis

**File:** [`langflix/services/translation_service.py`](file:///Users/changikchoi/Documents/langflix/langflix/services/translation_service.py#L34-L38)

```python
if lang == source_language_code:
    # Use original expressions (already translated during analysis)
    translated_expressions[lang] = expressions
    logger.info(f"Using original expressions for {lang} (already translated)")
    continue
```

The check `lang == source_language_code` doesn't work correctly because:
- `source_language_code` is the language used for analysis (e.g., "ko")
- But `target_languages` also contains "ko"
- The comparison may not be matching due to how languages are passed through the pipeline

## Implementation Plan

### Option A: Fix the Language Check (Recommended)
1. Ensure `source_language_code` is correctly passed from `main.py` to `TranslationService`
2. Verify the comparison is case-insensitive
3. Add logging to debug the actual values being compared

### Option B: Skip Translation Entirely for Primary Language
1. In `main.py`, filter out the primary language from `target_languages` before calling translation
2. The primary language translations already exist from expression analysis

### Files to Modify
1. [`langflix/main.py`](file:///Users/changikchoi/Documents/langflix/langflix/main.py) - Check how `language_code` is passed
2. [`langflix/services/translation_service.py`](file:///Users/changikchoi/Documents/langflix/langflix/services/translation_service.py) - Fix the language comparison
3. [`langflix/core/translator.py`](file:///Users/changikchoi/Documents/langflix/langflix/core/translator.py) - Add early return if already translated

## Verification Plan
1. Run pipeline with `--verbose` logging
2. Verify only ONE Gemini API call per expression (for initial analysis)
3. Check logs for "Using original expressions" message instead of "Sending translation request"
4. Compare API usage before/after fix

## Acceptance Criteria
- [ ] No duplicate LLM calls for the primary target language
- [ ] Translations from initial analysis are reused
- [ ] API call count reduced by ~50%
- [ ] Pipeline timing improves by 15-20 seconds per expression

## Priority
**High** - Direct cost savings and performance improvement

## Estimated Effort
1-2 hours
