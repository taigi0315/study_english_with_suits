# [TICKET-053] Add English as Target Language Support

## Priority
- [ ] Critical (System stability, security, data loss risk)
- [ ] High (Performance issues, significant tech debt)
- [x] Medium (Code quality, maintainability improvements)
- [ ] Low (Nice-to-have refactorings)

## Type
- [ ] Refactoring
- [ ] Performance Optimization
- [ ] Test Coverage
- [ ] Bug Fix
- [ ] Security Issue
- [ ] Technical Debt
- [x] Code Duplication

## Impact Assessment
**Business Impact:**
- Enables English-to-English learning mode (e.g., for native speakers learning advanced expressions)
- Expands target audience to English learners who prefer English explanations
- Low risk - additive feature, doesn't break existing functionality

**Technical Impact:**
- Requires updates to `langflix/core/language_config.py` to add 'en' language code
- May need updates to `langflix/config/default.yaml` for default target language
- May need updates to TTS and prompt generation to handle English target language
- Estimated files: 3-5 files

**Effort Estimate:**
- Small (< 1 day)

## Problem Description

### Current State
**Location:** `langflix/core/language_config.py:16-62`

The `LanguageConfig` class only supports non-English target languages:
- Korean ('ko')
- Japanese ('ja')
- Chinese ('zh')
- Spanish ('es')
- French ('fr')

English ('en') is not included in `LANGUAGE_CONFIGS`, which means:
1. Users cannot select English as target language
2. System falls back to Korean when 'en' is requested
3. English-to-English learning scenarios are not supported

```python
# Current code - missing 'en' entry
LANGUAGE_CONFIGS = {
    'ko': { ... },
    'ja': { ... },
    'zh': { ... },
    'es': { ... },
    'fr': { ... }
    # Missing: 'en' for English
}
```

### Root Cause Analysis
- Original design focused on non-English speakers learning English
- English target language was not considered in initial requirements
- No validation or error when 'en' is used as target language

### Evidence
- `langflix/core/language_config.py` line 76-78: Falls back to 'ko' if language not found
- `langflix/main.py` line 1219-1224: Language code choices don't include 'en' as target
- `langflix/config/default.yaml` line 45: Default target_language is "Korean"

## Proposed Solution

### Approach
1. Add 'en' entry to `LANGUAGE_CONFIGS` in `language_config.py`
2. Configure appropriate English font paths (system default fonts work well)
3. Update CLI argument choices to include 'en' as target language option
4. Update default config to allow "English" as target_language
5. Ensure prompt generation handles English target language correctly

### Implementation Details
```python
# Add to LANGUAGE_CONFIGS in langflix/core/language_config.py
'en': {
    'name': 'English',
    'font_path': '/System/Library/Fonts/HelveticaNeue.ttc',
    'font_fallback': '/System/Library/Fonts/Arial.ttf',
    'prompt_language': 'English',
    'translation_style': 'natural',
    'character_encoding': 'utf-8'
}
```

```python
# Update langflix/main.py line 1222
choices=['ko', 'ja', 'zh', 'es', 'fr', 'en'],  # Add 'en'
```

```yaml
# Update langflix/config/default.yaml line 45
target_language: "Korean"  # Allow "English" as valid option
```

### Alternative Approaches Considered
- Option 1: Create separate English-specific config - Not needed, same structure works
- Option 2: Auto-detect English and skip translation - Too complex, breaks consistency

### Benefits
- Enables English-to-English learning scenarios
- Consistent with existing language support pattern
- Minimal code changes required
- No breaking changes

### Risks & Considerations
- Need to verify prompt templates work with English target language
- TTS may need adjustment if English target language requires different voice
- Testing needed to ensure English explanations are generated correctly

## Testing Strategy
- Unit test: Add 'en' to language config and verify it's accessible
- Integration test: Generate video with English target language
- Verify prompt generation produces English explanations
- Verify font rendering works correctly

## Files Affected
- `langflix/core/language_config.py` - Add 'en' entry to LANGUAGE_CONFIGS
- `langflix/main.py` - Add 'en' to language code choices
- `langflix/config/default.yaml` - Document "English" as valid target_language option
- `langflix/utils/prompts.py` - Verify prompt generation handles English target language
- `tests/unit/test_language_config.py` - Add test for English language support

## Dependencies
- Depends on: None
- Blocks: None
- Related to: TICKET-054 (YouTube metadata in target language)

## References
- Related documentation: `docs/CONFIGURATION_GUIDE.md`
- Language config: `langflix/core/language_config.py`

## Architect Review Questions
**For the architect to consider:**
1. Should English target language use different prompt templates?
2. Are there any special considerations for English-to-English learning?
3. Should we add validation to ensure target language != source language?

## Success Criteria
How do we know this is successfully implemented?
- [ ] 'en' language code is accessible via `LanguageConfig.get_config('en')`
- [ ] CLI accepts 'en' as valid language code
- [ ] Video generation works with English target language
- [ ] Prompt generation produces English explanations
- [ ] Unit tests pass
- [ ] Documentation updated

