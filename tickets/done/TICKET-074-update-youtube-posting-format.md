# [TICKET-074] Update YouTube Posting Format

## Priority
- [ ] Critical (System stability, security, data loss risk)
- [ ] High (Performance issues, significant tech debt)
- [x] Medium (Code quality, maintainability improvements)
- [ ] Low (Nice-to-have refactorings)

## Type
- [x] Refactoring
- [ ] Performance Optimization
- [ ] Test Coverage
- [ ] Bug Fix
- [ ] Security Issue
- [ ] Technical Debt
- [ ] Code Duplication

## Impact Assessment
**Business Impact:**
- Improves video discoverability and relevance for target audience by including both original expression and translation in the title.
- Better user engagement with localized descriptions and tags.

**Technical Impact:**
- Affected module: `langflix/youtube/metadata_generator.py`
- Changes required in title generation logic and templates.
- Low risk of breaking changes, mostly string formatting updates.

**Effort Estimate:**
- Small (< 1 day)

## Problem Description

### Current State
**Location:** `langflix/youtube/metadata_generator.py`

The current YouTube title format is inconsistent and often only includes the expression or a generic "English Expression" prefix.
Example: `English Expression 최고의 실력을 발휘하다 / 최선을 다하다 from Suits.s01e05`

The body and tags are not fully optimized for the target audience's language as requested.

### Root Cause Analysis
The current templates and generation logic do not strictly follow the `Expression | translation | from Show Episodes` format and do not fully enforce localized tags/body structure as per the new requirements.

## Proposed Solution

### Approach
1.  Update `YouTubeMetadataGenerator` to support the new title format: `{expression} | {translation} | from {episode}`.
2.  Update `_generate_title` to include `{translation}` in the format arguments.
3.  Update `_load_translations` to reflect the new templates for supported languages.
4.  Ensure the body includes:
    *   `Expression: {Original Expression}`
    *   Translated "Watch and learn..." message.
5.  Ensure tags are in the target language.

### Implementation Details
```python
# In langflix/youtube/metadata_generator.py

# Update templates in _load_translations
"Korean": {
    # ...
    "title_template": "{expression} | {translation} | from {episode}",
    # ...
}

# Update _generate_title to pass translation
translation = video_metadata.expression_translation or self._get_translation(video_metadata)
format_args["translation"] = translation
```

### Benefits
- Consistent and informative titles.
- Better localization.

## Testing Strategy
- Verify generated metadata for a sample video with known expression and translation.
- Check title format, description content, and tags.

## Files Affected
- `langflix/youtube/metadata_generator.py`

## Success Criteria
- [ ] Title follows `Expression | translation | from Show Episodes` format.
- [ ] Description includes original expression and translated "Watch and learn".
- [ ] Tags are in target language.

---
## ✅ Implementation Complete

**Implemented by:** Antigravity
**Implementation Date:** 2025-11-26
**Branch:** feature/TICKET-074-update-youtube-posting-format
**PR:** Merged directly

### What Was Implemented
Updated the YouTube metadata generation logic to strictly follow the requested format for titles and descriptions, including better localization support.

### Files Modified
- `langflix/youtube/metadata_generator.py` - Updated templates and generation logic.

### Files Created
- `tests/unit/test_metadata_generator_ticket_074.py` - Unit tests for the new format.

### Tests Added
**Unit Tests:**
- `TestYouTubeMetadataGeneratorTicket074`
  - `test_korean_metadata_format`: Verifies title, description, and tags for Korean target language.
  - `test_english_metadata_format`: Verifies title and description for English target language.

### Verification Performed
- [x] All tests pass
- [x] Manual verification of output format via test script

### Additional Notes
The `implementation_plan.md` was created during the process and will be removed in the cleanup phase.
