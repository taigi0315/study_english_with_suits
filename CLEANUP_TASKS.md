# LangFlix Codebase Cleanup Task List

**Generated**: 2025-12-26
**Status**: Ready for review and prioritization

---

## 🔴 HIGH PRIORITY - Critical Issues

### 1. Duplicate Dependencies in requirements.txt
**Issue**: Same packages listed multiple times
**Location**: `/requirements.txt`
- Line 40 & 43: `ffmpeg-python` appears twice
- Line 39 & 44: `Pillow` appears twice

**Action**: Remove lines 43-44 (keep only lines 39-40)

**Impact**: Could cause version conflicts, confusing for maintainers

---

### 2. Duplicate Utility Function: `get_expr_attr()`
**Issue**: Same helper function defined in 3 separate files
**Locations**:
- `langflix/utils/expression_utils.py:14` ✅ **Canonical version (keep this)**
- `langflix/services/video_factory.py:21` ❌ **Remove and import from expression_utils**
- `langflix/media/subtitle_renderer.py:21` ❌ **Remove and import from expression_utils**

**Action**:
```python
# Add to video_factory.py and subtitle_renderer.py:
from langflix.utils.expression_utils import get_expr_attr

# Remove local definitions
```

**Impact**: Reduces code duplication, single source of truth for this utility

---

### 3. Deleted Module Still Being Imported
**Issue**: `bible_manager.py` shows as deleted in git status but is imported
**Location**:
- Import: `langflix/pipeline/orchestrator.py:15`
- Status: `D langflix/pipeline/bible_manager.py`

**Action**: Verify if:
- File should be restored (currently exists at: `langflix/pipeline/bible_manager.py` - 5037 bytes)
- Git status is incorrect
- File needs to be committed

**Impact**: CRITICAL - May cause runtime import errors

---

## 🟡 MEDIUM PRIORITY - Code Quality Issues

### 4. Unused Dependency: google-cloud-texttospeech
**Issue**: Dependency marked as "legacy, optional" but never imported
**Location**: `requirements.txt:20`
- Comment says: `# TTS (legacy, optional - only if using Google Cloud TTS)`
- Project uses `google-genai` and `gemini_client.py` instead
- No imports found in codebase

**Action**: Remove line 20 from requirements.txt

**Impact**: Reduces dependency bloat, faster installs

---

### 5. Print Statements Instead of Logging
**Issue**: Test/debug code uses `print()` instead of proper logging
**Locations**:
- `langflix/core/subtitle_processor.py:893-926` (main block with prints)
- `langflix/core/video_processor.py:352-374` (main block with prints)
- `langflix/core/subtitle_parser.py:418` (single print statement)

**Examples**:
```python
# Current (BAD):
print(f"Found {len(subtitles)} subtitles...")

# Should be (GOOD):
logger.info(f"Found {len(subtitles)} subtitles...")
```

**Action**: Convert all `print()` to `logger.debug()` or `logger.info()`

**Impact**: Better log management, consistent logging across codebase

---

### 6. Excessive Debug Logging with Emojis
**Issue**: 50+ debug statements with emoji characters (🎯, ✅, ❌, 💡, ✨)
**Locations**:
- `langflix/media/ffmpeg_utils.py` - Lines 75, 94, 203, 594, 598, 685, 1030, 1103, 1107
- `langflix/core/redis_client.py` - 50+ instances
- `langflix/services/queue_processor.py` - Multiple instances
- `langflix/api/routes/jobs.py` - Multiple instances

**Examples**:
```python
# Current:
logger.debug(f"🔍 FFprobe cache MISS for {Path(path).name}...")
logger.debug(f"✅ FFprobe completed for {Path(path).name}")

# Should be:
logger.debug(f"[MISS] FFprobe cache MISS for {Path(path).name}...")
logger.debug(f"[OK] FFprobe completed for {Path(path).name}")
```

**Action**: Standardize to text-based status indicators
- Replace 🎯 → `[TARGET]` or `[DEBUG]`
- Replace ✅ → `[OK]` or `[SUCCESS]`
- Replace ❌ → `[ERROR]` or `[FAIL]`
- Replace 🔍 → `[SEARCH]` or `[LOOKUP]`
- Replace ✨ → `[HIT]`

**Impact**: Better terminal/log file compatibility, searchable logs, professional appearance

---

### 7. Unused Configuration Options
**Issue**: Config keys defined but not actively used
**Location**: `langflix/config/default.yaml`

**Specific configs**:
- Lines 469-473: `expression.llm.parallel_processing` configuration
  - `batch_size` (line 473) never read from config
  - Parallel processing effectively disabled (enabled: false at line 254)
- Lines 254-258: `allow_multiple_expressions` - defined but not used

**Action**: Either:
1. Remove unused config options, OR
2. Implement the parallel processing feature

**Impact**: Cleaner config, less confusion about available features

---

### 8. Optional Dependencies Should Be Required or Removed
**Issue**: Dependencies with conditional imports create maintenance burden
**Locations**:
- `rapidfuzz` - Only used in `core/expression_analyzer.py` (conditional import)
  - If missing, duplicate removal is skipped with warning
- `chardet` - Used in `core/subtitle_parser.py` (conditional import)
  - If missing, assumes UTF-8 encoding
- `inflect` - Used in `tts/base.py` and `gemini_client.py` (conditional)
  - For number-to-word conversion

**Action**: Decide for each dependency:
1. Make it required (add to requirements.txt without try/except)
2. Fully remove it and its fallback code

**Impact**: More predictable behavior, easier testing, simpler dependency management

---

## 🟢 LOW PRIORITY - Technical Debt & Documentation

### 9. TODO/FIXME Comments
**Issue**: Comments indicating incomplete implementation
**Locations**:

1. `langflix/youtube/video_manager.py:304`
   ```python
   # TODO: Add map or config reader here.
   ```

2. `langflix/core/language_config.py:204`
   ```python
   # TODO: Add actual character support validation using fonttools or similar
   ```

3. `langflix/core/subtitle_parser.py:400`
   ```python
   # TODO: Implement parsers for VTT, ASS, SSA if not already done
   ```

4. `langflix/core/audio/audio_processor.py` - Lines 80, 109, 136, 159
   ```python
   # TODO: Implementation in Phase 1, Day 4
   ```

5. `langflix/core/video/video_composer.py:96`
   ```python
   # TODO: Implementation in Phase 1, Day 2
   ```

**Action**: For each TODO:
- Implement the feature, OR
- Create GitHub issue and reference it in comment, OR
- Remove if no longer relevant

**Impact**: Better project management, clearer technical debt tracking

---

### 10. Commented Out Code Blocks
**Issue**: Old code left commented instead of deleted
**Locations**:

1. `langflix/api/__init__.py:10`
   ```python
   # from .main import app, create_app
   ```
   - Intentionally commented to prevent circular imports
   - Comment explains why (lines 8-9)
   - **Action**: Add better documentation of this pattern

2. `langflix/tts/factory.py` - AWS provider commented out
   ```python
   # elif provider == "aws":
   #     return AWSPollyClient(config)
   ```
   - AWS Polly provider disabled but code remains
   - **Action**: Remove if AWS support not planned

**Impact**: Cleaner code, less confusion about what's active

---

### 11. Configuration File Comments
**Issue**: Config files have outdated comments
**Locations**:
- `config/config.example.yaml:11` - References `expression_analysis_prompt_v5.txt` (legacy naming)
- `langflix/config/default.yaml` - Comments about "Changed from X to Y" are outdated

**Action**: Update comments to reflect current state only, remove historical notes

**Impact**: Less confusion for new developers

---

### 12. Slide Generation Module Analysis
**Issue**: Multiple slide-related modules (1565 total lines) - may have consolidation opportunities
**Modules**:
- `langflix/slides/generator.py` (165 lines)
- `langflix/slides/slide_generator.py` (266 lines)
- `langflix/slides/slide_templates.py` (310 lines)
- `langflix/slides/advanced_templates.py` (441 lines)
- `langflix/slides/slide_renderer.py` (364 lines)

**Used by**:
- main.py
- pipeline/orchestrator.py
- pipeline/agents/script_agent.py
- youtube/video_manager.py
- youtube/web_ui.py

**Action**: Audit whether all modules are actively used, consider consolidation

**Impact**: Potential for significant code reduction

---

## 📊 Summary Statistics

| Category | Count | Estimated Effort |
|----------|-------|-----------------|
| Duplicate Dependencies | 2 | 5 minutes |
| Duplicate Functions | 2 files | 15 minutes |
| Unused Dependencies | 1 | 5 minutes |
| Print → Logger Conversions | 10+ instances | 30 minutes |
| Emoji Log Standardization | 50+ instances | 1-2 hours |
| Unused Config Options | 3-4 keys | 30 minutes |
| Optional Dependencies | 3 packages | 1 hour (decision + implementation) |
| TODO Comments | 5+ locations | Varies by TODO |
| Commented Code | 2 blocks | 15 minutes |
| Config Comment Cleanup | Multiple files | 30 minutes |

**Total Estimated Effort**: 4-6 hours for all medium/high priority items

---

## 🎯 Recommended Execution Order

### Phase 1: Quick Wins (30 minutes)
1. Fix duplicate dependencies in requirements.txt
2. Verify/fix bible_manager.py import issue
3. Remove google-cloud-texttospeech

### Phase 2: Code Quality (2 hours)
4. Consolidate get_expr_attr() function
5. Convert print() to logger calls
6. Remove commented code blocks

### Phase 3: Standardization (2 hours)
7. Standardize emoji debug logging
8. Clean up config comments
9. Decide on optional dependencies

### Phase 4: Technical Debt (Variable)
10. Address TODO comments (create issues or implement)
11. Audit and consolidate slide modules
12. Remove or implement parallel processing config

---

## 📝 Notes

- This analysis was performed on 2025-12-26
- Git status shows some deleted files that may need attention
- All findings are based on static code analysis
- Recommended to create a feature branch for cleanup work
- Consider running tests after each phase to ensure nothing breaks

---

## 🔗 Reference

**Exploration Agent ID**: ae40271 (can resume for additional analysis)

**Files Modified in Recent Cleanup**:
- Removed: aggregator.txt, translator.txt, subtitle_translation_service.py
- Removed: tests/broken/, tests/archive/, tests/step_by_step/
- Modified: config/default.yaml, settings.py, models.py, orchestrator.py

**Current Branch**: main (as of this analysis)
