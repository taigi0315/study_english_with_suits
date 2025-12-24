# Test Suite Review - Phase 1

**Date**: 2025-12-24
**Ticket**: TICKET-093 Phase 1
**Reviewer**: Claude Code

## Overview

Total files to review:
- **Archived**: 25 tests in `tests/archive/`
- **Broken**: 17 tests in `tests/broken/`
- **Total**: 42 test files

## Review Categories

- ✅ **Keep & Fix**: Test is valuable, needs minor updates
- 🔄 **Migrate**: Test is useful, move to appropriate location
- ❌ **Remove**: Test is obsolete or redundant
- 🔍 **Manual Test**: Not a unit test, should be in scripts/ or tools/

---

## Archived Tests (25 files)

### 1. test_path_utils.py ✅ KEEP & FIX
- **Test Results**: 16/17 passed (94%)
- **Purpose**: Tests path utility functions for subtitle file discovery
- **Issue**: One test expects old directory structure (needs "Subs/" prefix)
- **Action**: Fix 1 test to match new Netflix-style folder structure
- **Priority**: HIGH - Active code with good coverage

### 2. test_video_processor.py ✅ KEEP & FIX
- **Test Results**: 23/24 passed (96%)
- **Purpose**: Tests video clip extraction and validation
- **Issue**: One mock setup needs adjustment
- **Action**: Fix mock configuration for extract_clip test
- **Priority**: HIGH - Core functionality

### 3. test_font_configuration.py ✅ KEEP & FIX
- **Test Results**: 8/10 passed (80%)
- **Purpose**: Tests font resolution for multiple languages
- **Issue**: Font fallback logic has changed
- **Action**: Update 2 tests for new font resolution strategy
- **Priority**: MEDIUM - Font system is stable

### 4. test_expression_analyzer.py ⚠️ NEEDS MAJOR UPDATE
- **Test Results**: 0/6 passed (0%)
- **Purpose**: Tests expression analyzer with mocked LLM
- **Issues**:
  - Missing prompt template file (`expression_analysis_prompt_v8.yaml`)
  - Wrong mock patch paths (`langflix.expression_analyzer` vs `langflix.core.expression_analyzer`)
  - API changes in expression analyzer
- **Action**: Major refactoring needed or remove if obsolete
- **Priority**: LOW - May be outdated approach

### 5. test_expression_slicer.py
- **Status**: 🔍 **Under Review**
- **Purpose**: Tests expression slicer (media.expression_slicer)
- **Decision**: TBD

### 6. test_ffmpeg_utils.py
- **Status**: 🔍 **Under Review**
- **Purpose**: Tests ffmpeg utility functions
- **Decision**: TBD

### 7-25. [Remaining archived tests]
- **Status**: 🔍 **Pending Review**

---

## Broken Tests (17 files)

### 1. test_fuzzy_match.py
- **Status**: 🔍 **Manual Test**
- **Purpose**: Demo script for fuzzy subtitle matching
- **Type**: Executable script, not unit test
- **Hardcoded paths**: `/Users/changikchoi/Documents/langflix/assets/media/test_media/`
- **Decision**: 🔄 **Migrate to tools/** or ❌ **Remove**

### 2. test_llm_only.py
- **Status**: 🔍 **Manual Test**
- **Purpose**: Manual test script for LLM-only expression analysis
- **Type**: Executable script with CLI args
- **Decision**: 🔄 **Migrate to tools/** or keep as manual test

### 3. test_step1_load_and_analyze.py
- **Status**: 🔍 **Under Review**
- **Purpose**: Step-by-step pipeline test - Step 1
- **Note**: Part of 7-step pipeline testing system
- **Decision**: TBD - may need fixing

### 4-17. [Remaining broken tests]
- **Status**: 🔍 **Pending Review**

---

## Next Steps

1. Run each test to identify actual errors
2. Categorize based on:
   - Import errors (module moved/renamed)
   - API changes (function signature changed)
   - Obsolete functionality (feature removed)
   - Hardcoded paths (needs configuration)
3. Create action plan for each category
4. Document decisions in this file

---

## Testing Commands

```bash
# Run individual test
python -m pytest tests/archive/test_path_utils.py -v

# Run with verbose error output
python -m pytest tests/broken/test_fuzzy_match.py -vv

# Check imports without running
python -c "from tests.archive import test_expression_analyzer"
```

---

## Progress Tracker

- [ ] Review all 25 archived tests
- [ ] Review all 17 broken tests
- [ ] Categorize all tests
- [ ] Create action items
- [ ] Execute cleanup plan
