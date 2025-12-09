# [TICKET-060] Generate YouTube Metadata in Target Language for All Video Types

## Priority
- [ ] Critical (System stability, security, data loss risk)
- [x] High (Performance issues, significant tech debt)
- [ ] Medium (Code quality, maintainability improvements)
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
- **User Experience**: Target language users (Korean, Japanese, Chinese, etc.) will see metadata in their native language, improving discoverability and engagement
- **YouTube SEO**: Localized metadata improves search visibility in target language markets
- **Content Accessibility**: Non-English speakers can better understand video content before watching
- **Risk of NOT fixing**: Current English-only metadata reduces engagement from target audience, limiting video reach and educational effectiveness

**Technical Impact:**
- Primary file: `langflix/youtube/metadata_generator.py`
- Affected methods: `_generate_title()`, `_generate_description()`, `_generate_tags()`
- Estimated files: 1-2 files (metadata_generator.py + tests)
- Potential breaking changes: None (backward compatible with existing videos)

**Effort Estimate:**
- Medium (1-3 days)

## Problem Description

### Current State
**Location:** `langflix/youtube/metadata_generator.py`

Current implementation has inconsistent target language support:

1. **Short videos (partially implemented in TICKET-056)**:
   - ✅ Title: Uses target language template
   - ❌ Description: Uses target language labels but expression text is still in English
   - ❌ Tags: Hardcoded English tags (`#Shorts #EnglishLearning #Suits #EnglishExpressions #LearnEnglish`)

2. **Long-form/Final videos (not implemented)**:
   - ❌ Title: Always uses English template
   - ❌ Description: Always uses English template
   - ❌ Tags: Always uses English tags

**Current Code Issues:**

```python
# langflix/youtube/metadata_generator.py:431-435
# Short video description - expression is still in English
description = f"""🎬 {quick_lesson}
📚 {expression_label}: {expression_text}  # <-- expression_text is English
📖 {meaning_label}: {translation_text}    # <-- translation_text is correct
💡 {watch_and_learn}
#Shorts #EnglishLearning #Suits #EnglishExpressions #LearnEnglish"""  # <-- Hardcoded English tags
```

```python
# langflix/youtube/metadata_generator.py:206-219
# Title generation - only short videos use target language
if video_metadata.video_type == "short" and target_language:
    title_template = self._get_template_translation("title_template", target_language)
else:
    title_template = template.title_template  # <-- Always English for long-form/final
```

```python
# langflix/youtube/metadata_generator.py:449-455
# Long-form/Final description - always English
return template.description_template.format(
    expression=video_metadata.expression,  # <-- English expression
    translation=self._get_translation(video_metadata),  # <-- May be English fallback
    episode=episode_display,
    language=video_metadata.language.upper(),
    expressions_list=expressions_list
)
```

### Root Cause Analysis
- TICKET-056 implemented partial target language support for short videos only
- Long-form and final videos were not updated to use target language
- Expression text in descriptions is not translated (uses original English expression)
- Tags are hardcoded in English without target language variants
- No systematic approach to ensure all metadata respects target language setting

### Evidence
- **Current behavior**: Korean users see English titles/descriptions for long-form videos
- **User feedback**: Target language users expect localized metadata
- **YouTube best practices**: Localized metadata improves discoverability in target markets
- **Related work**: TICKET-056 added partial support but didn't complete the implementation

## Proposed Solution

### Approach
1. **Extend target language support to all video types** (short, long-form, final)
2. **Use translated expression text** in descriptions (from `expression_translation` field)
3. **Generate localized tags** based on target language
4. **Ensure consistent target language detection** across all metadata generation methods
5. **Add comprehensive tests** for all video types and target languages

### Implementation Details

#### 1. Update Title Generation for All Video Types

```python
# langflix/youtube/metadata_generator.py
def _generate_title(self, video_metadata: VideoMetadata, template: YouTubeContentTemplate, 
                   custom_title: Optional[str], target_language: Optional[str] = None) -> str:
    """Generate video title in target language"""
    if custom_title:
        return custom_title.strip()
    
    # Get target language if not provided
    if target_language is None:
        target_language = self._get_target_language()
    
    # Use target language template for ALL video types
    if target_language:
        title_template = self._get_template_translation("title_template", target_language)
    else:
        title_template = template.title_template
    
    # Use translated expression if available
    expression = video_metadata.expression_translation or video_metadata.expression
    # ... rest of implementation
```

#### 2. Update Description Generation

```python
# langflix/youtube/metadata_generator.py
def _generate_description(self, video_metadata: VideoMetadata, template: YouTubeContentTemplate, 
                         custom_description: Optional[str], target_language: Optional[str] = None) -> str:
    """Generate video description in target language"""
    if custom_description:
        return custom_description
    
    if target_language is None:
        target_language = self._get_target_language()
    
    # For ALL video types, use target language
    if video_metadata.video_type == "short":
        # Use translated labels and translated expression
        quick_lesson = self._get_template_translation("quick_lesson", target_language)
        expression_label = self._get_template_translation("expression_label", target_language)
        meaning_label = self._get_template_translation("meaning_label", target_language)
        watch_and_learn = self._get_template_translation("watch_and_learn", target_language)
        
        # Use TRANSLATED expression text (not English)
        expression_text = video_metadata.expression_translation or video_metadata.expression
        translation_text = video_metadata.expression_translation or self._get_translation(video_metadata)
        
        # Generate localized tags
        tags = self._generate_localized_tags(video_metadata, target_language)
        
        description = f"""🎬 {quick_lesson}
📚 {expression_label}: {expression_text}
📖 {meaning_label}: {translation_text}
💡 {watch_and_learn}
{tags}"""
        
        return description
    else:
        # Long-form/Final videos - use target language template
        # ... similar approach with target language templates
```

#### 3. Generate Localized Tags

```python
# langflix/youtube/metadata_generator.py
def _generate_localized_tags(self, video_metadata: VideoMetadata, target_language: str) -> str:
    """Generate hashtags in target language"""
    tag_translations = {
        "Korean": {
            "shorts": "#쇼츠",
            "english_learning": "#영어학습",
            "suits": "#수트",
            "english_expressions": "#영어표현",
            "learn_english": "#영어공부"
        },
        "Japanese": {
            "shorts": "#ショート",
            "english_learning": "#英語学習",
            "suits": "#スーツ",
            "english_expressions": "#英語表現",
            "learn_english": "#英語勉強"
        },
        "Chinese": {
            "shorts": "#短片",
            "english_learning": "#英语学习",
            "suits": "#金装律师",
            "english_expressions": "#英语表达",
            "learn_english": "#学英语"
        },
        # Add more languages as needed
    }
    
    translations = tag_translations.get(target_language, tag_translations["Korean"])
    return f"{translations['shorts']} {translations['english_learning']} {translations['suits']} {translations['english_expressions']} {translations['learn_english']}"
```

#### 4. Update Template Translations

Add missing template translations for long-form/final videos:

```python
# langflix/youtube/metadata_generator.py
def _load_translations(self) -> Dict[str, Dict[str, str]]:
    """Load translations for template strings by target language"""
    return {
        "Korean": {
            "quick_lesson": "수트에서 배우는 빠른 영어 레슨!",
            "expression_label": "표현",
            "meaning_label": "의미",
            "watch_and_learn": "좋아하는 쇼에서 보고 배우세요!",
            "title_template": "영어 표현 {expression} from {episode}",
            # Add long-form templates
            "long_form_title": "수트에서 배우는 영어 표현 - {episode}",
            "long_form_description": "수트 드라마에서 배우는 실용적인 영어 표현들을 모았습니다.",
            # ... more templates
        },
        # ... other languages
    }
```

### Alternative Approaches Considered
- **Option 1: Keep English metadata, add target language as subtitle**
  - Why not: Doesn't address discoverability issue in target language markets
  - YouTube search works better with localized metadata

- **Option 2: Generate both English and target language metadata, let user choose**
  - Why not: Adds complexity, most users want target language only
  - Can be added later if needed

- **Option 3: Use AI translation for all metadata**
  - Why not: We already have translations from expression analysis, should use those
  - More reliable and consistent with video content

### Benefits
- **Improved User Experience**: Target language users see metadata in their language
- **Better SEO**: Localized metadata improves YouTube search visibility
- **Consistency**: All video types use same target language approach
- **Maintainability**: Centralized target language logic
- **Scalability**: Easy to add new target languages

### Risks & Considerations
- **Breaking changes**: None - backward compatible
- **Migration**: Existing videos won't be affected (only new uploads)
- **Testing**: Need comprehensive tests for all video types and languages
- **Performance**: Minimal impact (just string lookups)
- **Backward compatibility**: Falls back to English if target language not available

## Testing Strategy

### Unit Tests
Add to `tests/youtube/test_metadata_generator.py`:

```python
def test_generate_title_target_language_short(self, generator, sample_video_metadata):
    """Test title generation for short video in target language"""
    sample_video_metadata.video_type = "short"
    sample_video_metadata.expression = "Not the point"
    sample_video_metadata.expression_translation = "요점이 아니야"
    
    title = generator._generate_title(sample_video_metadata, template, None, target_language="Korean")
    
    assert "영어 표현" in title or "요점이 아니야" in title
    assert "#Shorts" in title or "쇼츠" in title

def test_generate_title_target_language_long_form(self, generator, sample_video_metadata):
    """Test title generation for long-form video in target language"""
    sample_video_metadata.video_type = "long-form"
    
    title = generator._generate_title(sample_video_metadata, template, None, target_language="Korean")
    
    assert "수트" in title or "영어" in title

def test_generate_description_target_language_short(self, generator, sample_video_metadata):
    """Test description generation for short video in target language"""
    sample_video_metadata.video_type = "short"
    sample_video_metadata.expression = "Not the point"
    sample_video_metadata.expression_translation = "요점이 아니야"
    
    description = generator._generate_description(sample_video_metadata, template, None, target_language="Korean")
    
    assert "수트에서 배우는" in description
    assert "요점이 아니야" in description  # Translated expression, not English
    assert "표현" in description
    assert "의미" in description

def test_generate_localized_tags_korean(self, generator, sample_video_metadata):
    """Test localized tag generation for Korean"""
    tags = generator._generate_localized_tags(sample_video_metadata, "Korean")
    
    assert "#쇼츠" in tags or "#영어학습" in tags

def test_generate_localized_tags_japanese(self, generator, sample_video_metadata):
    """Test localized tag generation for Japanese"""
    tags = generator._generate_localized_tags(sample_video_metadata, "Japanese")
    
    assert "#ショート" in tags or "#英語学習" in tags
```

### Integration Tests
- Test full metadata generation pipeline with different target languages
- Verify metadata is correctly used in YouTube upload process
- Test with actual video files from different language outputs

### Manual Testing
- Generate videos for Korean, Japanese, Chinese target languages
- Verify YouTube metadata preview shows correct target language
- Check that uploaded videos have localized metadata

## Files Affected
- `langflix/youtube/metadata_generator.py` - Update title, description, tag generation methods
- `tests/youtube/test_metadata_generator.py` - Add comprehensive target language tests
- `langflix/youtube/video_manager.py` - May need to ensure expression_translation is populated (already done in TICKET-059)

## Dependencies
- **Depends on**: TICKET-059 (populate expression metadata) - ensures expression_translation is available
- **Blocks**: None
- **Related to**: TICKET-056 (partial implementation for short videos)

## References
- Related documentation: `docs/youtube/README_eng.md`
- Previous work: `tickets/done/TICKET-056-update-youtube-metadata-template.md`
- YouTube best practices: Localized metadata improves discoverability

## Architect Review Questions
**For the architect to consider:**
1. Should we support multiple languages per video (e.g., English + Korean)?
2. Should target language be configurable per video or global setting?
3. Do we need to maintain backward compatibility with English metadata?
4. Should we add language detection from video path/name?
5. Should tags be bilingual (English + target language) for better discoverability?

## Success Criteria
How do we know this is successfully implemented?
- [ ] All video types (short, long-form, final) generate metadata in target language
- [ ] Expression text in descriptions uses translated version (not English)
- [ ] Tags are localized based on target language
- [ ] All unit tests pass for Korean, Japanese, Chinese target languages
- [ ] Integration tests verify metadata is correctly used in upload process
- [ ] Manual testing confirms YouTube preview shows localized metadata
- [ ] Documentation updated with target language metadata examples
- [ ] Code review approved

---
## 🏛️ Architect Review & Approval

**Reviewed by:** Architect Agent
**Review Date:** 2025-01-21
**Decision:** ✅ APPROVED

**Strategic Rationale:**
Why this aligns with our architectural vision:
- **Completes TICKET-056 work**: Finishes the incomplete target language implementation started in TICKET-056
- **User Experience Priority**: Target language users are the primary audience - metadata should be in their language
- **YouTube SEO**: Localized metadata significantly improves discoverability in target language markets
- **Consistency**: All video types should follow the same localization pattern
- **Low Risk, High Value**: Backward compatible, no breaking changes, immediate user experience improvement
- **Natural Extension**: Builds on existing translation infrastructure from TICKET-056

**Implementation Phase:** Phase 1 - Sprint 1 (Quick Win)
**Sequence Order:** #3 in implementation queue (after TICKET-059 completion)

**Architectural Guidance:**
Key considerations for implementation:
- **Expression Translation Priority**: Use `expression_translation` from VideoMetadata (populated by TICKET-059) - this is the actual translated expression, not the English original
- **Tag Strategy**: Consider bilingual tags (English + target language) for maximum discoverability - English tags help international audience, target language helps local audience
- **Template Consistency**: Extend existing `_load_translations()` pattern from TICKET-056 to all video types
- **Language Detection**: Use `video_metadata.language` field to infer target language if not explicitly provided
- **Fallback Strategy**: Always fall back to English if target language translation is missing (backward compatibility)
- **Long-form Templates**: Add long-form/final video templates to translation dictionary (similar to short video templates)

**Dependencies:**
- **Must complete first:** TICKET-059 (populate expression metadata) - ensures `expression_translation` field is available in VideoMetadata
- **Should complete first:** None
- **Blocks:** None
- **Related work:** TICKET-056 (partial implementation), TICKET-059 (metadata population)

**Risk Mitigation:**
- **Risk**: Expression translation may not be available for all videos
  - **Mitigation**: Fall back to English expression if `expression_translation` is missing (graceful degradation)
- **Risk**: Tag translations may not be accurate for SEO
  - **Mitigation**: Consider bilingual tags (English + target language) for better discoverability
- **Risk**: Long-form video templates need new translations
  - **Mitigation**: Start with simple translations, can refine based on user feedback
- **Rollback Strategy**: Changes are isolated to metadata generation - easy to revert if issues arise. Existing videos unaffected.

**Enhanced Success Criteria:**
Beyond original ticket criteria:
- [ ] All video types (short, long-form, final) consistently use target language
- [ ] Expression text uses `expression_translation` when available (from TICKET-059)
- [ ] Tags are localized (consider bilingual for maximum reach)
- [ ] Long-form/final video templates added to translation dictionary
- [ ] Language detection from `video_metadata.language` works correctly
- [ ] Fallback to English works gracefully when translations missing
- [ ] Documentation includes examples for all supported languages

**Alternative Approaches Considered:**
- Original proposal: Full target language metadata - **Selected approach** - Best user experience, aligns with target audience
- Alternative 1: Bilingual metadata (English + target language) - Consider for tags only, not full description (too verbose)
- Alternative 2: Language detection from video path - Good fallback, but explicit target language parameter is preferred
- Alternative 3: Per-video language configuration - Overkill for current use case, global setting is sufficient

**Implementation Notes:**
- Start by: Extending `_load_translations()` to include long-form/final templates
- Watch out for: Expression text should use `expression_translation` (not `expression`) in descriptions
- Coordinate with: TICKET-059 completion to ensure metadata is populated
- Reference: TICKET-056 implementation pattern for consistency
- Tag consideration: Evaluate bilingual tags (English + target) for better SEO - can be added incrementally

**Estimated Timeline:** 2-3 days (includes translation work and comprehensive testing)
**Recommended Owner:** Any engineer (straightforward extension of existing pattern)

**Architect Decisions on Review Questions:**
1. **Multiple languages per video**: Not needed for v1 - single target language is sufficient. Can add later if demand exists.
2. **Per-video vs global language**: Global setting is sufficient (from config). Per-video can be added later if needed.
3. **Backward compatibility**: Yes - always fall back to English if target language unavailable. No breaking changes.
4. **Language detection from path**: Good fallback strategy - use `video_metadata.language` field as secondary source.
5. **Bilingual tags**: Recommended for tags only (not description) - helps with international discoverability while maintaining local relevance.

