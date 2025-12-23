# [EPIC-V2-001] LangFlix V2: Dual Language Subtitle Architecture

## Priority
- [x] Critical (System stability, security, data loss risk)
- [ ] High (Performance issues, significant tech debt)
- [ ] Medium (Code quality, maintainability improvements)
- [ ] Low (Nice-to-have refactorings)

## Type
- [x] Refactoring
- [ ] Performance Optimization
- [ ] Test Coverage
- [ ] Bug Fix
- [ ] Security Issue
- [ ] Technical Debt
- [x] Feature Request

## Epic Overview

This epic implements a fundamental architectural shift in how LangFlix handles subtitles and content generation. **The key change is that we now receive complete subtitles for both source AND target languages directly from Netflix**, eliminating the need for LLM-based translation.

## Problem Statement

### Current V1 Workflow (Translation-Focused)
```
Source Language Subtitle → LLM (Translation + Analysis) → Generated Video
```

**Issues with Current Approach:**
- LLM handles both translation AND content selection (dual responsibility)
- Translation quality varies and requires extensive prompting
- No guarantee of translation accuracy
- Complex LLM prompt (500+ lines) tries to do too much
- Configuration (default.yaml) has many unused translation-related settings

### New V2 Workflow (Content Selection-Focused)
```
Source Subtitle ─┐
                 ├→ LLM (Content Selection + Annotation) → Generated Video
Target Subtitle ─┘
```

**Benefits:**
- LLM focuses purely on content quality: selecting engaging scenes, slicing clips
- Guaranteed translation accuracy from Netflix's professional subtitles
- Simpler, more focused LLM prompt
- User can select any source/target language pair available
- Cleaner configuration with reduced feature bloat

## Business Value

**Quality Improvement:**
- Professional Netflix translations vs. LLM-generated translations
- More accurate educational content
- Better learning experience for users

**User Experience:**
- User selects source language (what they're learning)
- User selects target language (their native language)
- Support for any language pair Netflix provides

**Developer Experience:**
- Cleaner codebase with single-responsibility components
- Reduced LLM prompt complexity
- Clearer feature definitions and naming

## Epic Scope

### In Scope

1. **Subtitle System Redesign:**
   - Dual language subtitle loading (source + target)
   - New file structure: media/{show}/subtitles/{language}.srt
   - Subtitle alignment/synchronization service

2. **LLM Prompt Refocus:**
   - Remove translation responsibilities
   - Focus on: scene selection, content slicing, engagement optimization
   - Vocabulary annotation, catch words, expressions (without translation)

3. **Frontend UI Updates:**
   - Source language selector
   - Target language selector
   - Language pair validation

4. **Configuration Cleanup:**
   - Audit default.yaml for unused settings
   - Remove translation-specific configurations
   - Consolidate feature definitions

5. **Feature Naming Standardization:**
   - Catch Words → Top black padding keywords
   - Vocabulary Annotations → Dynamic on-screen overlays
   - Expression + Translation → Bottom padding content
   - Dialogue + Translation → Over-video subtitles

### Out of Scope (V3 and Beyond)
- Multi-language video generation (multiple target languages in one video)
- Automatic subtitle download from Netflix
- Speech-to-text for missing subtitles
- Community subtitle contributions

## Sub-Tickets

| Ticket | Title | Priority | Dependencies |
|--------|-------|----------|--------------|
| TICKET-V2-001 | Dual Language Subtitle Support | Critical | None |
| TICKET-V2-002 | LLM Prompt Refocus | Critical | V2-001 |
| TICKET-V2-003 | Frontend Language Selector | High | V2-001 |
| TICKET-V2-004 | File Structure Reorganization | High | None |
| TICKET-V2-005 | Config Cleanup (default.yaml) | Medium | V2-002 |
| TICKET-V2-006 | Feature Consolidation & Naming | Medium | V2-005 |

## New File Structure

### Existing Structure (Already in Place!)
The V2-compatible file structure **already exists** in the codebase:

```
assets/media/test_media/
├── The.Glory.S01E01.KOREAN.1080p.WEBRip.x265-RARBG[eztv.re].mp4   # Media file
└── The.Glory.S01E01.KOREAN.1080p.WEBRip.x265-RARBG[eztv.re]/      # Subtitle folder (same name as media without extension)
    ├── 3_Korean.srt          # Korean subtitles
    ├── 4_Korean.srt          # Korean (alternate)
    ├── 5_English.srt         # English (CC)
    ├── 6_English.srt         # English
    ├── 7_English.srt         # English (SDH)
    ├── 8_Arabic.srt
    ├── 9_Czech.srt
    ├── 10_Danish.srt
    ├── 11_German.srt
    ├── 12_Greek.srt
    ├── 13_Spanish.srt
    ├── 14_Spanish.srt        # Spanish (alternate)
    ├── ...                   # 36 language files total
    └── 38_Chinese.srt
```

### File Naming Convention
- Format: `{index}_{Language}.srt`
- Multiple variants per language (e.g., CC, SDH, regional variants)
- Index preserves Netflix's original ordering
- Language name is human-readable (Korean, English, Spanish, etc.)

### Implementation Notes
- **Media file and subtitle folder share the same base name** (minus extension)
- **No nested `subtitles/` folder needed** - subtitles are directly in the named folder
- **Multiple variants per language** - need to handle selection or default to first

## Technical Architecture Changes

### Subtitle Service Refactor
```python
class SubtitleService:
    def load_dual_subtitles(
        self, 
        media_path: str, 
        source_lang: str,  # e.g., "English"
        target_lang: str   # e.g., "Korean"
    ) -> DualSubtitle:
        """
        Loads both source and target language subtitles
        and aligns them by timestamp.
        """
        ...
```

### New Model: DualSubtitle
```python
class DualSubtitle(BaseModel):
    source_entries: List[SubtitleEntry]
    target_entries: List[SubtitleEntry]
    source_language: str
    target_language: str
    
    def get_aligned_pair(self, timestamp: str) -> Tuple[str, str]:
        """Returns (source_text, target_text) for a timestamp"""
        ...
```

### LLM Prompt Focus Areas (V2)
1. **Scene Selection:** Pick engaging, high-energy moments
2. **Content Slicing:** Determine start/end times for clips
3. **Catch Words:** Generate engaging keywords in target language
4. **Vocabulary Annotations:** Identify interesting vocabulary to highlight
5. **Scene Type Classification:** Humor, drama, tension, etc.

### Configuration Consolidation

**Features with Clear Definitions:**
| Config Key | Feature | Display Location |
|------------|---------|------------------|
| `catch_words` | Engaging keywords | Top black padding |
| `vocabulary_annotations` | Word highlights | Random on-screen |
| `expression_display` | Expression + translation | Bottom padding |
| `dialogue_subtitles` | Full dialogue with translation | Over video |

## Implementation Phases

### Phase 1: Foundation (TICKET-V2-001, V2-004)
- Implement new file structure
- Create DualSubtitle model
- Implement subtitle loading service
- **Duration:** 3-4 days

### Phase 2: LLM Refactor (TICKET-V2-002)
- Create new prompt template (content_selection_prompt_v1.txt)
- Remove translation logic from prompt
- Update expression_analyzer.py
- Update models.py
- **Duration:** 4-5 days

### Phase 3: Frontend (TICKET-V2-003)
- Add source language dropdown
- Add target language dropdown
- Update API endpoints
- **Duration:** 2-3 days

### Phase 4: Cleanup (TICKET-V2-005, V2-006)
- Audit and clean default.yaml
- Remove unused configuration
- Standardize feature naming
- Update documentation
- **Duration:** 2-3 days

**Total Estimated Duration:** 11-15 days (~2-3 weeks)

## Risks & Mitigations

### Risk 1: Subtitle Alignment Mismatch
- **Risk:** Source and target subtitles may have different timing
- **Mitigation:** Implement fuzzy timestamp matching, allow configurable tolerance

### Risk 2: Missing Subtitle Languages
- **Risk:** Some shows may not have all languages
- **Mitigation:** Graceful error handling, UI shows only available languages

### Risk 3: Breaking Changes for Existing Users
- **Risk:** V1 subtitle structure won't work with V2
- **Mitigation:** Provide migration script, maintain backward compatibility mode

### Risk 4: LLM Prompt Regression
- **Risk:** New prompt may perform worse initially
- **Mitigation:** A/B testing, maintain V1 prompt as fallback

## Success Criteria

- [ ] Users can select source and target languages in UI
- [ ] System loads both subtitle files correctly
- [ ] LLM prompt no longer handles translation
- [ ] Video generation works with dual subtitles
- [ ] All existing tests pass
- [ ] New tests for dual subtitle functionality
- [ ] default.yaml cleaned up (no unused settings)
- [ ] Feature naming is consistent across codebase
- [ ] Documentation updated for V2 workflow
- [ ] Migration guide for V1 → V2 file structure

## Migration Guide (V1 → V2)

```bash
# Script to migrate existing file structure
python scripts/migrate_to_v2_structure.py \
  --media-dir assets/media \
  --source-lang English \
  --target-lang Korean
```

## Notes

- This is a significant architectural change - take time to design correctly
- Consider maintaining backward compatibility for transition period
- Update all documentation as changes are implemented
- Communicate changes clearly to any existing users

---

**Branch:** `feature/v2-dual-language-architecture`

**Created:** 2025-12-13

