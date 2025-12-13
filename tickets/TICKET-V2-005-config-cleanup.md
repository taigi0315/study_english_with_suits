# [TICKET-V2-005] Configuration Cleanup (default.yaml)

## Priority
- [ ] Critical
- [ ] High
- [x] Medium
- [ ] Low

## Type
- [x] Refactoring
- [ ] Feature Request
- [ ] Bug Fix

## Parent Epic
[EPIC-V2-001](./EPIC-V2-001-dual-language-architecture.md)

## Summary
Audit and clean up `default.yaml` configuration file. Remove unused settings, clarify feature definitions, and organize the configuration for V2.

## Background
The current `default.yaml` is 429 lines with many settings that:
- Are not actively used
- Have unclear purposes
- Overlap with each other
- Relate to translation (no longer needed in V2)

## Current State Analysis

### Settings Overview (429 lines)

| Section | Lines | Status |
|---------|-------|--------|
| `app` | 9-13 | ✓ Keep |
| `database` | 17-30 | ✓ Keep |
| `llm` | 34-64 | ⚠️ Review (translation-related) |
| `processing` | 68-80 | ✓ Keep (duplicate at 169-174) |
| `language_levels` | 84-100 | ✓ Keep |
| `video` | 104-118 | ✓ Keep |
| `font` | 122-165 | ⚠️ Review (complex, duplicated) |
| `transitions` | 178-205 | ✓ Keep |
| `tts` | 209-239 | ✓ Keep |
| `short_video` | 243-367 | ⚠️ Review (very large, mixed concerns) |
| `expression` | 372-428 | ⚠️ Review (subtitle_styling, etc.) |

### Suspected Unused Settings

1. **LLM section:**
   - `ranking.*` - May not be actively used
   - Translation-specific settings (V2 removes translation)

2. **Expression section:**
   - `subtitle_styling.*` - Check if actually used
   - `educational_video_mode` - Check usage

3. **Font section:**
   - Duplicate definitions (`font.sizes` vs `short_video.layout.fonts`)

## Requirements

### 1. Audit Each Setting
- [ ] Grep codebase for each config key
- [ ] Document usage or mark as unused
- [ ] Create spreadsheet of settings status

### 2. Remove Unused Settings
- Comment out with explanation
- Or remove entirely with note in commit

### 3. Consolidate Duplicates
- `processing` appears twice (lines 68-80 and 169-174)
- Font definitions in multiple places

### 4. Add V2 Settings
```yaml
# V2: Dual Language Settings
dual_language:
  # Default source language for learning
  default_source_language: "English"
  
  # Default target language (user's native language)
  default_target_language: "Korean"
  
  # Subtitle file pattern recognition
  subtitle_pattern: "{index}_{Language}.srt"
```

### 5. Improve Documentation
- Add comments explaining each section
- Document which features use which settings

## Files to Modify

| Action | File | Purpose |
|--------|------|---------|
| MODIFY | `langflix/config/default.yaml` | Cleanup and reorganize |
| CREATE | `docs/CONFIG_AUDIT.md` | Document audit results |
| MODIFY | `langflix/settings.py` | Update for any removed settings |

## Acceptance Criteria

- [ ] All settings audited and documented
- [ ] Unused settings removed or commented
- [ ] No duplicate settings
- [ ] V2 settings added
- [ ] All tests pass after cleanup
- [ ] Documentation updated

## Dependencies
- TICKET-V2-002: LLM Prompt Refocus (determines which LLM settings to keep)

## Notes
- Keep backup of original config
- Changes may affect tests - run full test suite
