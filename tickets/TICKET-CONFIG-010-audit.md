# TICKET-V2-010: Config Usage Audit & Cleanup

## Priority: 🟡 Medium
## Type: Tech Debt

## Objective

Audit all config keys in `default.yaml` to verify:
1. Each key is actually used in code
2. Naming is clear and descriptive
3. No duplicate/conflicting settings

## Known Issues Found

### 1. Duplicate `processing:` Section (FIXED ✅)
- Was defined twice (lines 69-80 and 170-174)
- Fixed in V2-005

### 2. Unused `llm.ranking` Section (FIXED ✅)
- Settings never referenced in code
- Commented out in V2-005

### 3. Naming Inconsistencies

| Current | Issue | Suggested |
|---------|-------|-----------|
| `catchy_keywords` (LLM field) | Displayed as "catch words" | Keep internal name, document display name |
| `font.language_fonts.ko` | Unclear: source or target? | Need both source_lang + target_lang handling |
| `short_video.layout.keywords` | Doesn't match "catch words" | Rename to `catch_words` for consistency |

### 4. Missing V2 Integration Points

Configs that need V2 awareness:
- `app.template_file` → Should auto-select based on `dual_language.enabled`
- Font selection → Needs `source_language` + `target_language`, not just one

## Audit Checklist

### Used Settings (Verified)
- [x] `app.show_name`
- [x] `app.template_file`
- [x] `database.*` (all)
- [x] `llm.max_input_length`
- [x] `llm.model_name`
- [x] `llm.temperature`, `top_p`, `top_k`
- [x] `processing.test_mode.*`
- [x] `video.preset`, `video.crf`
- [x] `font.sizes.*`
- [x] `font.language_fonts.*`
- [x] `tts.*`
- [x] `transitions.*`
- [x] `short_video.*`
- [x] `expression.*`

### Unused/Deprecated Settings
- [ ] `llm.ranking.*` (commented out)
- [ ] Any others found during audit

## Implementation

1. Run grep for each top-level config key
2. Document usage in FEATURE_GLOSSARY.md
3. Remove truly unused settings
4. Standardize naming where beneficial

## Testing

- Verify all existing tests pass after changes
- Add config validation tests
