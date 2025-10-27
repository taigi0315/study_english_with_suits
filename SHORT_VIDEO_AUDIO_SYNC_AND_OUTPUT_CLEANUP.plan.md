# Short Video Audio Sync & Output Structure Cleanup Plan

**Date:** 2025-10-27  
**Status:** In Progress  
**Branch:** `fix/ui-ux-improvements` (to be extended)  
**Priority:** High

## 🎯 Overview

This plan addresses critical issues identified after UI/UX improvements:
1. **Audio-Video Mismatch in Short Videos** - Expression audio not synced with video
2. **Output Directory Structure Cleanup** - Unnecessary folders and poor file naming
3. **File Naming Convention Improvements** - Better naming for final and short videos

## 🔍 Current Issues Analysis

### Issue 1: Short Video Audio Mismatch
**Problem:**
- Context part: ✅ Perfect (video + audio)
- Expression part: ✅ Video good | ❌ Audio mismatch

**Root Cause:**
- Video extraction: Uses `context_video` with relative timestamps ✅
- Audio extraction: Uses `original_video` with absolute timestamps ❌
- This creates audio-video desynchronization in expression segments

**Evidence:**
```python
# In video_editor.py line 2112-2114
# Audio still uses original video (WRONG)
expression_timeline_path, expression_timeline_duration = self._extract_original_audio_timeline(
    expression, original_video, tts_audio_dir, expression_index, {}, repeat_count=repeat_count
)

# While video uses context video (CORRECT)
(ffmpeg.input(context_video_path, ss=relative_start, t=expression_duration)
 .output(str(expression_video_path), vcodec='libx264', an=None, preset='fast', crf=23)
```

### Issue 2: Output Directory Structure Problems
**Current Structure:**
```
output/
├── Suits/
│   └── S01E01/
│       ├── metadata/          # ❓ Unknown purpose
│       ├── shared/            # ❓ Supposed to be reusable intermediate files?
│       └── translations/      # ✅ Most outputs go here
│           └── ko/
│               ├── context_videos/
│               ├── slides/
│               ├── short_videos/
│               └── final_videos/
```

**Problems:**
- `metadata/` and `shared/` folders created but unclear purpose
- Most files end up in `translations/` making other folders redundant
- Inconsistent file organization

### Issue 3: File Naming Convention Issues
**Current Naming:**
- Final videos: `final_educational_video_with_slides_S01E01.mkv` ❌ Too long, unclear
- Short videos: Follow media file name pattern ❌ Not descriptive

**Desired Naming:**
- Final videos: `long-form_S01E01_[original_filename].mkv` ✅
- Short videos: `short-form_S01E01_001.mkv`, `short-form_S01E01_002.mkv` ✅

## 📋 Implementation Plan

### Phase 1: Fix Audio-Video Sync ⚡ HIGH PRIORITY

#### Task 1.1: Implement Context Audio Extraction
- **File:** `langflix/core/video_editor.py`
- **Action:** Create `_extract_context_audio_timeline()` method
- **Logic:**
  1. Calculate relative timestamps within context video
  2. Create modified ExpressionAnalysis with relative times
  3. Extract audio from context video using relative timestamps
  4. Maintain same repetition pattern as original method

#### Task 1.2: Update Short Video Generation
- **File:** `langflix/core/video_editor.py` 
- **Action:** Replace `_extract_original_audio_timeline()` call
- **Change:**
  ```python
  # FROM:
  expression_timeline_path, duration = self._extract_original_audio_timeline(
      expression, original_video, tts_audio_dir, expression_index, {}, repeat_count
  )
  
  # TO:
  expression_timeline_path, duration = self._extract_context_audio_timeline(
      expression, context_video_path, tts_audio_dir, expression_index, repeat_count
  )
  ```

#### Task 1.3: Add Helper Method
- **File:** `langflix/core/video_editor.py`
- **Action:** Add `_seconds_to_time()` method for timestamp conversion
- **Purpose:** Convert seconds back to "HH:MM:SS.mmm" format

### Phase 2: Clean Up Output Directory Structure 🧹

#### Task 2.1: Analyze Current Folder Usage
- **Action:** Investigate `metadata/` and `shared/` folder purposes
- **Files to check:**
  - `langflix/services/output_manager.py`
  - `langflix/core/video_editor.py`
  - `langflix/slides/slide_renderer.py`

#### Task 2.2: Consolidate Output Structure
- **Target Structure:**
  ```
  output/
  ├── Suits/
  │   └── S01E01/
  │       └── translations/
  │           └── ko/
  │               ├── context_videos/
  │               ├── slides/
  │               ├── short_videos/      # Renamed to short-form
  │               └── long_videos/       # Renamed from final_videos
  ```

#### Task 2.3: Remove Unnecessary Folders
- **Action:** Update output manager to not create `metadata/` and `shared/`
- **Condition:** Only if confirmed they're not essential

### Phase 3: Improve File Naming Conventions 📝

#### Task 3.1: Update Final Video Naming
- **Current:** `final_educational_video_with_slides_S01E01.mkv`
- **New:** `long-form_S01E01_[original_filename].mkv`
- **Files to modify:**
  - `langflix/core/video_editor.py`
  - `langflix/services/output_manager.py`

#### Task 3.2: Update Short Video Naming
- **Current:** Based on media file name
- **New:** `short-form_S01E01_001.mkv`, `short-form_S01E01_002.mkv`
- **Logic:** Sequential numbering per episode (001, 002, 003...)

#### Task 3.3: Update Directory Names
- **Changes:**
  - `final_videos/` → `long_videos/`
  - `short_videos/` → `short_videos/` (keep, but improve file naming)

### Phase 4: Testing & Validation 🧪

#### Task 4.1: Create Test Cases
- **Audio Sync Test:** Verify expression audio matches video timing
- **Directory Structure Test:** Confirm clean output organization
- **File Naming Test:** Validate new naming conventions

#### Task 4.2: Manual Testing
- **Test Scenario:** Generate short video for S01E01
- **Verification Points:**
  1. Context part: video + audio sync ✅
  2. Expression part: video + audio sync ✅
  3. Clean directory structure ✅
  4. Proper file naming ✅

## 🔧 Technical Implementation Details

### Audio Extraction Logic
```python
def _extract_context_audio_timeline(self, expression, context_video_path, ...):
    # Calculate relative timestamps
    context_start = self._time_to_seconds(expression.context_start_time)
    expr_start = self._time_to_seconds(expression.expression_start_time)
    expr_end = self._time_to_seconds(expression.expression_end_time)
    
    # Convert to relative position within context video
    relative_start = expr_start - context_start
    relative_end = expr_end - context_start
    
    # Create modified expression with relative timestamps
    relative_expression = ExpressionAnalysis(
        expression=expression.expression,
        translation=expression.translation,
        context_start_time=self._seconds_to_time(0),
        context_end_time=self._seconds_to_time(relative_end - relative_start + 2),
        expression_start_time=self._seconds_to_time(relative_start),
        expression_end_time=self._seconds_to_time(relative_end),
        # ... other fields
    )
    
    # Extract from context video using relative timestamps
    return create_original_audio_timeline(
        expression=relative_expression,
        original_video_path=context_video_path,  # Use context instead of original
        # ... other params
    )
```

### File Naming Pattern
```python
# Long-form videos
def generate_long_form_filename(episode, original_filename):
    return f"long-form_{episode}_{original_filename}.mkv"

# Short-form videos  
def generate_short_form_filename(episode, sequence_number):
    return f"short-form_{episode}_{sequence_number:03d}.mkv"
```

## 📊 Success Criteria

### Phase 1 Complete When: ✅
- [x] `_extract_context_audio_timeline()` method implemented
- [x] Short video generation uses context audio extraction
- [x] Audio-video sync verified in expression segments
- [x] No regression in context segments

### Phase 2 Complete When: ✅
- [x] `metadata/` and `shared/` folder usage analyzed
- [x] Unnecessary folders removed from output structure
- [x] All outputs properly organized under `translations/`

### Phase 3 Complete When: ✅
- [x] Final videos renamed to `long-form_*` pattern
- [x] Short videos use sequential numbering per episode
- [x] Directory names updated consistently
- [x] All file naming conventions documented

### Phase 4 Complete When: ✅
- [x] UI updated to show only uploadable files (long-form, short-form)
- [x] Video type detection updated for new naming convention
- [x] Intermediate files excluded from UI display
- [x] Backward compatibility maintained for legacy files

## 🚨 Risk Assessment

### High Risk
- **Audio extraction changes** could break existing functionality
- **Directory structure changes** might affect other components

### Medium Risk  
- **File naming changes** could impact YouTube upload metadata
- **Backward compatibility** with existing output files

### Mitigation Strategies
1. **Incremental implementation** with fallback mechanisms
2. **Comprehensive testing** before each phase
3. **Backup/restore** capability for output directories
4. **Feature flags** for new vs old behavior

## 📅 Timeline Estimate

- **Phase 1 (Audio Sync):** 2-3 hours
- **Phase 2 (Directory Cleanup):** 1-2 hours  
- **Phase 3 (File Naming):** 1-2 hours
- **Phase 4 (Testing):** 1 hour
- **Total:** 5-8 hours

## 🔄 Next Steps

1. **Immediate:** Complete `_extract_context_audio_timeline()` implementation
2. **Test:** Verify audio-video sync fix
3. **Investigate:** Analyze `metadata/` and `shared/` folder usage
4. **Implement:** Directory structure and naming improvements
5. **Validate:** Comprehensive testing and documentation

---

**Note:** This plan extends the existing `fix/ui-ux-improvements` branch to address these additional critical issues identified during testing.
