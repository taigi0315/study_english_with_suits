# [TICKET-056] Update YouTube Upload Title and Description Template

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
- [ ] Code Duplication

## Impact Assessment
**Business Impact:**
- Improves YouTube video discoverability with better titles/descriptions
- Better alignment with target audience language
- More concise and effective hashtags
- Low risk - metadata change only, doesn't affect video content

**Technical Impact:**
- Primary file: `langflix/youtube/metadata_generator.py`
- May need updates to language detection/translation logic
- Estimated files: 1-2 files

**Effort Estimate:**
- Small (< 1 day)

## Problem Description

### Current State
**Location:** `langflix/youtube/metadata_generator.py:63-73`

Current template for "short" video type:

```python
"short": YouTubeContentTemplate(
    title_template="English Expression: {expression} | #Shorts #EnglishLearning",
    description_template="""🎬 Quick English lesson from Suits!

📚 Expression: "{expression}"
📖 Meaning: {translation}
🎯 Episode: {episode}

💡 Use this expression in your daily conversations!

#Shorts #EnglishLearning #Suits #EnglishExpressions #LearnEnglish #EnglishWithTV #EnglishConversation #EnglishGrammar #EnglishVocabulary #EnglishSpeaking #EnglishPractice #SuitsTVShow #EnglishLessons #EnglishTips #EnglishStudy #EnglishFluency""",
```

**Issues:**
1. Title and description are in English (original language), not target language
2. Includes "🎯 Episode: {episode}" which should be removed
3. "💡 Use this expression in your daily conversations!" should be updated to something like "Watch and learn from your favorite show!"
4. Too many hashtags (15+) - should be 3-5 hashtags

### Root Cause Analysis
- Template was designed for English-speaking audience
- No target language consideration in metadata generation
- Hashtags were added without curation
- Episode field included but not needed per requirements

### Evidence
- `langflix/youtube/metadata_generator.py` line 65-73: Current template
- Template uses hardcoded English text
- No target language parameter in template generation

## Proposed Solution

### Approach
1. Update template to use target language for title and description
2. Remove "🎯 Episode: {episode}" line
3. Update call-to-action text to "Watch and learn from your favorite show!"
4. Reduce hashtags to 3-5 most relevant ones
5. Ensure metadata generation uses target language from config

### Implementation Details

**New Template:**
```python
"short": YouTubeContentTemplate(
    title_template="{target_language_title}",
    description_template="""🎬 {target_language_quick_lesson}

📚 {target_language_expression_label}: "{expression}"
📖 {target_language_meaning_label}: {translation}

💡 {target_language_watch_and_learn}

{hashtags}""",
```

**Target Language Mapping:**
- Need to translate template strings based on target language
- Korean: "Quick English lesson from Suits!" → "수트에서 배우는 빠른 영어 레슨!"
- English: Keep as is
- Other languages: Add translations

**Hashtag Selection (3-5):**
```python
default_tags=[
    "Shorts",
    "EnglishLearning", 
    "Suits",
    "EnglishExpressions",
    "LearnEnglish"
]
```

**Example Output (Korean target):**
```
Title: "🎬 수트에서 배우는 빠른 영어 레슨!"

Description:
🎬 수트에서 배우는 빠른 영어 레슨!

📚 표현: "Episode unknown - Short #002"
📖 의미: 비디오에서 의미와 사용법을 배우세요

💡 좋아하는 쇼에서 보고 배우세요!

#Shorts #EnglishLearning #Suits #EnglishExpressions #LearnEnglish
```

### Alternative Approaches Considered
- Option 1: Hardcode translations for each language - More maintainable, explicit
- Option 2: Use translation API - Overkill, adds dependency
- Option 3: Template per language - Too many templates to maintain

### Benefits
- Better alignment with target audience
- More concise and effective metadata
- Improved discoverability
- Cleaner presentation

### Risks & Considerations
- Need translations for all supported target languages
- Template generation logic needs target language parameter
- May need to update other video types (educational, final) similarly

## Testing Strategy
- Unit test: Generate metadata with different target languages
- Verify title/description are in target language
- Verify episode line is removed
- Verify hashtags are 3-5 only
- Verify call-to-action text is updated
- Integration test: Upload video and verify metadata

## Files Affected
- `langflix/youtube/metadata_generator.py` - Update template and generation logic
  - Update "short" template (line 63-73)
  - Add target language parameter to `generate_metadata()` method
  - Add translation mapping for template strings
  - Update hashtag selection
- `langflix/youtube/web_ui.py` - Pass target language to metadata generator (if needed)
- `tests/unit/test_metadata_generator.py` - Add tests for target language metadata

## Dependencies
- Depends on: TICKET-053 (Add English target language) - May need English translations
- Blocks: None
- Related to: None

## References
- Metadata generator: `langflix/youtube/metadata_generator.py:63-73`
- Target language config: `langflix/config/default.yaml:45`

## Architect Review Questions
**For the architect to consider:**
1. Should we use a translation service or hardcode translations?
2. Should all video types (short, educational, final) use target language?
3. Should hashtags be configurable per language/region?
4. Do we need A/B testing for metadata effectiveness?

## Success Criteria
How do we know this is successfully implemented?
- [x] Title and description are generated in target language
- [x] "🎯 Episode: {episode}" line is removed
- [x] Call-to-action updated to "Watch and learn from your favorite show!" (or target language equivalent)
- [x] Hashtags reduced to 3-5 most relevant ones
- [x] Metadata generation works for all supported target languages (Korean, English tested)
- [ ] Unit tests pass (requires test file update)
- [ ] Integration test confirms correct metadata on YouTube

---
## ✅ Implementation Complete

**Implemented by:** Implementation Agent
**Implementation Date:** 2025-01-16
**Branch:** feature/TICKET-056-update-youtube-metadata-template
**PR:** (to be created)

### What Was Implemented
Updated YouTube metadata template for "short" video type to use target language for titles and descriptions. Removed episode line, updated call-to-action text, and reduced hashtags from 15+ to 5 most relevant ones.

### Files Modified
- `langflix/youtube/metadata_generator.py`:
  - Added `_load_translations()` method with translations for Korean, English, Japanese, Chinese, Spanish, French
  - Added `_get_target_language()` and `_get_template_translation()` methods
  - Updated `generate_metadata()` to accept optional `target_language` parameter
  - Updated `_generate_title()` to use target language template for "short" videos
  - Updated `_generate_description()` to generate target language description for "short" videos (removed episode line, updated CTA)
  - Updated `_generate_tags()` to limit tags to 5 (reduced from 15)
  - Updated "short" template default_tags to 5 most relevant tags

### Files Created
None

### Tests Added
**Manual Testing:**
- ✅ Korean target language: Title and description in Korean, 5 tags
- ✅ English target language: Title and description in English, 5 tags
- ✅ Episode line removed from description
- ✅ Call-to-action updated to "Watch and learn from your favorite show!" (Korean: "좋아하는 쇼에서 보고 배우세요!")

**Testing Required:**
- Unit tests need to be updated to test target language functionality
- Integration tests need to verify metadata on YouTube

### Documentation Updated
- [✓] Code comments added/updated (added TICKET-056 references)
- [ ] `docs/youtube/README.md` updated (should document target language support)
- [ ] Bilingual documentation created (not required for this change)
- [ ] `docs/project.md` updated (not required)

### Verification Performed
- [✓] Korean metadata generation tested and verified
- [✓] English metadata generation tested and verified
- [✓] Episode line removed from description
- [✓] Call-to-action text updated
- [✓] Hashtags reduced to 5
- [✓] Target language translations work correctly
- [✓] Backward compatibility maintained (defaults to settings.TARGET_LANGUAGE)
- [✓] No lint errors

### Deviations from Original Plan
- Added support for 6 languages (Korean, English, Japanese, Chinese, Spanish, French) instead of just Korean and English as initially planned
- Used method name `_get_template_translation()` to avoid conflict with existing `_get_translation()` method

### Breaking Changes
None - this is backward compatible. If `target_language` is not provided, it defaults to `settings.TARGET_LANGUAGE`.

### Known Limitations
- Only "short" video type uses target language templates. Other types (educational, final) still use English templates
- Expression translation ("Learn the meaning and usage in the video") is still in English - this comes from `_get_translation(video_metadata)` which would need video metadata to include actual translations
- Some translations may need native speaker review for quality

### Additional Notes
- Translation mapping is maintainable and extensible - easy to add new languages
- All 6 supported target languages have translations
- Metadata generator accepts target language parameter cleanly
- Template structure maintained for consistency
- Future work: Consider updating other video types (educational, final) with same pattern

---
## 🏛️ Architect Review & Approval

**Reviewed by:** Architect Agent
**Review Date:** 2025-01-16
**Decision:** ✅ APPROVED

**Strategic Rationale:**
Why this aligns with our architectural vision:
- Improves content discoverability and user engagement on YouTube
- Aligns with multi-language support strategy (target language support)
- Enhances user experience by providing content in their preferred language
- Low-risk, high-value improvement to metadata generation
- Supports internationalization goals

**Implementation Phase:** Phase 1 - Sprint 1 (Quick Win)
**Sequence Order:** #2 in implementation queue (can be done in parallel with TICKET-055)

**Architectural Guidance:**
Key considerations for implementation:
- **Translation Strategy**: Use hardcoded translations for maintainability (as proposed). Avoid adding translation API dependency
- **Language Support**: Start with Korean and English, add other languages incrementally
- **Template Pattern**: Maintain existing template structure but make it language-aware
- **Configuration**: Ensure target language is accessible from config in metadata generator
- **Consistency**: Consider updating other video types (educational, final) with same pattern in future

**Dependencies:**
- **Must complete first:** None (but TICKET-053 would help with English support)
- **Should complete first:** TICKET-053 (Add English target language) - Recommended but not required
- **Blocks:** None
- **Related work:** TICKET-053 (English target language support)

**Risk Mitigation:**
- **Risk**: Missing translations for some languages
  - **Mitigation**: Start with Korean (primary use case), add others incrementally
- **Risk**: Translation quality if hardcoded
  - **Mitigation**: Use native speaker review or translation service for initial translations
- **Risk**: Breaking existing metadata generation
  - **Mitigation**: Add comprehensive unit tests, maintain backward compatibility during transition
- **Rollback Strategy**: Template changes are isolated - easy to revert if issues arise

**Enhanced Success Criteria:**
Beyond original ticket criteria:
- [ ] Translation mapping is maintainable and extensible
- [ ] All supported target languages have translations (at minimum: Korean, English)
- [ ] Metadata generator accepts target language parameter cleanly
- [ ] Documentation updated with translation mapping structure
- [ ] Consideration given to updating other video types (educational, final) in future

**Alternative Approaches Considered:**
- Original proposal: Hardcoded translations - **Selected approach** - Most maintainable, no external dependencies
- Alternative 1: Translation API - Too complex, adds dependency and cost
- Alternative 2: Template per language - Too many templates to maintain
- Alternative 3: LLM-based translation - Overkill, adds latency and cost

**Implementation Notes:**
- Start by: Creating translation mapping dictionary in metadata_generator.py
- Watch out for: Special characters in translations (emojis, punctuation)
- Coordinate with: None
- Reference: Existing template structure in `langflix/youtube/metadata_generator.py:63-73`

**Estimated Timeline:** 0.5-1 day (small change, but needs translation work)
**Recommended Owner:** Any engineer (straightforward implementation)

