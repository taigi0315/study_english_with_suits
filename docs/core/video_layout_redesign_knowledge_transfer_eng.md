# Video Layout Redesign - Knowledge Transfer Document

**Date**: 2025-01-XX  
**Branch**: `feature/TICKET-038-039-040-video-layout-redesign`  
**Status**: In Progress (Subtitle sync issues being resolved)

---

## Executive Summary

This document provides comprehensive knowledge transfer for the video layout redesign project, including:
- **TICKET-038**: Long-form sequential layout (full-screen video → transition → slide)
- **TICKET-039**: Short-form centered video with letterbox
- **TICKET-040**: Dual subtitle layers (original at bottom + expression at top)

**Current Status**: Core functionality implemented, but subtitle synchronization issues persist and require ongoing attention.

---

## 1. Project Goals

### 1.1 Long-form Video Layout (TICKET-038)

**Goal**: Change from side-by-side layout to sequential full-screen layout

**Before**:
- Side-by-side: `[Video | Education Slide]` (both visible simultaneously)
- Layout: `hstack` (horizontal stack)

**After**:
- Sequential: `Video (full-screen) → Transition → Education Slide (full-screen)`
- Layout: Sequential concatenation with transition video
- Video maintains original aspect ratio, full-screen
- Education slide is full-screen after transition

**Key Changes**:
- Replaced `hstack_keep_height()` with sequential `concat_filter_with_explicit_map()`
- Added transition video creation (`_create_transition_video()`)
- Transition uses configured images and sound effects

### 1.2 Short-form Video Layout (TICKET-039)

**Goal**: Change from top-bottom layout to centered video with letterbox

**Before**:
- Top-bottom: `[Video | Education Slide]` (both visible simultaneously)
- Layout: `vstack` (vertical stack)

**After**:
- Centered video: Video in middle of screen (vertical ratio) with letterboxing
- Sequential: `Video (centered) → Transition → Education Slide (full-screen)`
- Video maintains original aspect ratio, centered with black bars (letterboxing)
- Education slide is full-screen after transition

**Key Changes**:
- Replaced `vstack_keep_width()` with `center_video_with_letterbox()`
- Added sequential concatenation with transition
- Letterboxing preserves original video aspect ratio

### 1.3 Dual Subtitle Layers (TICKET-040)

**Goal**: Add expression subtitle overlay at top (yellow) in addition to original subtitles

**Before**:
- Only original subtitles at bottom (dual-language: English + Korean)

**After**:
- Original subtitles at bottom (unchanged)
- Expression subtitle at top (yellow, bold) during expression segments only
- Expression subtitle shows only during the expression segment in context video

**Key Changes**:
- Added `generate_expression_subtitle_srt()` in `SubtitleProcessor`
- Added `apply_dual_subtitle_layers()` in `subtitle/overlay.py`
- Expression subtitle uses ASS style: `Alignment=8` (top center), `MarginV=50` (50px from top)

---

## 2. Implementation Details

### 2.1 Long-form Sequential Layout

**File**: `langflix/core/video_editor.py`  
**Method**: `create_educational_sequence()`  
**Lines**: ~333-450

**Process**:
1. Extract expression clip from context video (with subtitles)
2. Repeat expression clip (configured repeat count)
3. Create left side: Context video → Expression repeat (if not skipping context)
4. Create transition video (1 second, with image and sound effect)
5. Create educational slide with expression audio (not TTS)
6. Concatenate sequentially: Left side → Transition → Slide

**Key Code**:
```python
# Sequential concatenation (replaces hstack)
concat_filter_with_explicit_map(
    str(left_side_path),
    str(transition_video),
    str(temp_video_transition)
)
concat_filter_with_explicit_map(
    str(temp_video_transition),
    str(educational_slide),
    str(sequential_temp_path)
)
```

### 2.2 Short-form Centered Video

**File**: `langflix/core/video_editor.py`  
**Method**: `create_short_format_video()`  
**Lines**: ~635-750

**Process**:
1. Extract and concatenate context + expression repeat
2. Center video with letterboxing (maintains original aspect ratio)
3. Create transition video
4. Create educational slide
5. Concatenate sequentially: Letterboxed video → Transition → Slide

**Key Code**:
```python
# Center video with letterboxing (replaces vstack)
center_video_with_letterbox(
    str(concatenated_video_path),
    target_width=1080,
    target_height=1920,
    out_path=str(letterboxed_video_path)
)
```

**Letterboxing Function**: `langflix/media/ffmpeg_utils.py::center_video_with_letterbox()`
- Calculates scaling to fit target resolution
- Adds black padding (letterboxing) to center video
- Preserves original aspect ratio

### 2.3 Dual Subtitle Layers

**File**: `langflix/core/video_editor.py`  
**Method**: `_add_subtitles_to_context()`  
**Lines**: ~1273-1375

**Process**:
1. Generate expression subtitle SRT (only for expression segment)
2. Apply dual subtitle layers:
   - Original subtitles at bottom (existing)
   - Expression subtitle at top (yellow, bold)

**Key Code**:
```python
# Generate expression subtitle SRT
expression_subtitle_content = self.subtitle_processor.generate_expression_subtitle_srt(
    expression,
    expression_start_relative,  # Start when expression begins in context
    expression_end_relative     # End when expression ends in context
)

# Apply dual subtitle layers
subs_overlay.apply_dual_subtitle_layers(
    str(video_path),
    str(temp_sub),  # Original subtitle file
    str(expression_subtitle_path),  # Expression subtitle file
    str(output_path),
    expression_start_relative,
    expression_end_relative
)
```

**Subtitle Style**:
- Expression: `Alignment=8` (top center), `MarginV=50` (50px from top), Yellow (`#FFFF00`), Bold
- Original: `Alignment=2` (bottom center), White, Normal weight

---

## 3. Critical Issues and Solutions

### 3.1 Subtitle Synchronization (ONGOING ISSUE)

**Problem**: Subtitles become desynchronized when extracting expression clips from context videos.

**Root Cause**:
- Context video has subtitles already rendered into the video stream
- When extracting expression clip, timing must be precise to match subtitle timestamps
- Using `trim` filter works on frames, not timestamps, causing misalignment

**Solution Implemented**:
- **Use output seeking** (`ss`/`t` in output) instead of `trim` filter
- Output seeking decodes entire video and seeks to exact timestamp
- Two-pass process:
  1. Extract clip using output seeking (`ss`/`t` in output)
  2. Reset timestamps using `setpts` filters (required for repeated clips)

**Key Code** (Current Implementation):
```python
# Step 1: Extract with output seeking (accurate timestamp-based extraction)
ffmpeg.output(
    video_stream,
    audio_stream,
    str(expression_video_clip_path),
    ss=relative_start,  # Output seeking: apply after input for accuracy
    t=expression_duration
)

# Step 2: Reset timestamps (required for repeated clips)
reset_input = ffmpeg.input(str(expression_video_clip_path))
reset_video = ffmpeg.filter(reset_input['v'], 'setpts', 'PTS-STARTPTS')
reset_audio = ffmpeg.filter(reset_input['a'], 'asetpts', 'PTS-STARTPTS')
```

**Why Two Passes?**:
- Output seeking must happen first for accurate subtitle sync
- Timestamp reset must happen after extraction for repeated clips to work
- Cannot combine both in single pass without breaking subtitle sync

**Reference**: `langflix/media/expression_slicer.py` uses the same approach (output seeking)

**Status**: ⚠️ **ONGOING** - Still experiencing sync issues, may need further refinement

### 3.2 Expression Subtitle Position

**Problem**: Expression subtitle appeared at wrong position (not properly at top-center).

**Solution**:
- Added `MarginV=50` to expression subtitle style
- `MarginV` controls vertical margin from alignment position
- For `Alignment=8` (top center), `MarginV=50` means 50 pixels from top edge

**Key Code**:
```python
expression_style = (
    "Alignment=8,"  # Top center
    "PrimaryColour=&H00FFFF00,"  # Yellow
    "MarginV=50"  # 50 pixels from top edge
)
```

**Status**: ✅ **RESOLVED**

### 3.3 Expression Audio Mismatch

**Problem**: Expression audio played during education slide didn't match the expression.

**Root Cause**:
- Was extracting audio from context-extracted clip instead of original video
- Context-extracted clip may have timing issues

**Solution**:
- Extract audio from original `expression_video_path` (not context-extracted clip)
- Use expression timestamps (`expression_start_time`, `expression_end_time`) for accurate extraction
- Use output seeking for accurate audio extraction

**Key Code**:
```python
# Extract audio from original expression video using expression timestamps
expression_start_seconds = self._time_to_seconds(expression.expression_start_time)
expression_end_seconds = self._time_to_seconds(expression.expression_end_time)
expression_audio_duration = expression_end_seconds - expression_start_seconds

audio_input = ffmpeg.input(str(original_video_path))
audio_stream = audio_input['a']

ffmpeg.output(
    audio_stream,
    str(output_path),
    ss=expression_start_seconds,  # Output seeking
    t=expression_audio_duration
)
```

**Status**: ✅ **RESOLVED** (with improved logging)

---

## 4. Key Technical Concepts

### 4.1 Output Seeking vs Input Seeking

**Input Seeking** (`-ss` before `-i`):
- Faster but less accurate
- Seeks to nearest keyframe
- May not match exact timestamp
- ❌ **NOT suitable for subtitle sync**

**Output Seeking** (`-ss` after `-i`):
- Slower but more accurate
- Decodes entire video and seeks to exact timestamp
- ✅ **REQUIRED for subtitle sync**

**Reference**: See `docs/core/subtitle_sync_guide_eng.md` for detailed explanation

### 4.2 Subtitle Timestamp Calculation

**Context Video**:
- Starts at timestamp 0
- Subtitles must have timestamps relative to context start (0)

**Expression Clip Extraction**:
- Expression starts at `relative_start` seconds in context video
- Expression ends at `relative_end` seconds in context video
- Expression duration: `relative_end - relative_start`

**Expression Subtitle**:
- Must show only during expression segment in context video
- Timestamps: `expression_start_relative` to `expression_end_relative` (relative to context start)

### 4.3 Transition Video Creation

**Configuration**: `langflix/config/default.yaml`
```yaml
context_to_slide_transition:
  enabled: true
  duration: 1.0  # 1 second transition
  image_path_16_9: "assets/transition_16_9.png"  # For long-form
  image_path_9_16: "assets/transition_9_16.png"  # For short-form
  sound_effect_path: "assets/sound_effect.mp3"
  sound_effect_volume: 0.5
```

**Process**:
1. Create video from transition image (target duration)
2. Add sound effect (if configured)
3. Concatenate with video segments

### 4.4 Letterboxing

**Purpose**: Center video in vertical frame while maintaining original aspect ratio

**Process**:
1. Calculate scaling to fit target resolution
2. Scale video to fit width or height (whichever is smaller)
3. Add black padding (letterboxing) to center video
4. Result: Video centered with black bars on top/bottom or left/right

**Function**: `langflix/media/ffmpeg_utils.py::center_video_with_letterbox()`

---

## 5. File Structure

### 5.1 Modified Files

**Core Video Editing**:
- `langflix/core/video_editor.py`
  - `create_educational_sequence()` - Long-form sequential layout
  - `create_short_format_video()` - Short-form centered layout
  - `_add_subtitles_to_context()` - Dual subtitle layers
  - `_create_educational_slide()` - Expression audio extraction

**Subtitle Processing**:
- `langflix/core/subtitle_processor.py`
  - `generate_expression_subtitle_srt()` - Expression-only subtitle generation

**Subtitle Overlay**:
- `langflix/subtitles/overlay.py`
  - `apply_dual_subtitle_layers()` - Dual subtitle layer application

**FFmpeg Utilities**:
- `langflix/media/ffmpeg_utils.py`
  - `center_video_with_letterbox()` - Letterboxing function

**Configuration**:
- `langflix/config/default.yaml`
  - `context_to_slide_transition` - Transition configuration

**Main Pipeline**:
- `langflix/main.py`
  - `VideoEditor` initialization with `subtitle_processor`

### 5.2 New Functions

1. `center_video_with_letterbox()` - Letterboxing for short-form videos
2. `generate_expression_subtitle_srt()` - Expression subtitle SRT generation
3. `apply_dual_subtitle_layers()` - Dual subtitle layer application
4. `_create_transition_video()` - Transition video creation (if not exists)

---

## 6. Common Pitfalls and Solutions

### 6.1 Subtitle Sync Issues

**Pitfall**: Using `trim` filter for expression clip extraction
- **Why**: `trim` works on frames, not timestamps, causing misalignment
- **Solution**: Use output seeking (`ss`/`t` in output)

**Pitfall**: Applying `setpts` before output seeking
- **Why**: Breaks output seeking accuracy
- **Solution**: Extract first, then reset timestamps

**Pitfall**: Using input seeking (`-ss` before `-i`)
- **Why**: Seeks to nearest keyframe, not exact timestamp
- **Solution**: Always use output seeking for subtitle sync

### 6.2 Expression Audio Issues

**Pitfall**: Extracting audio from context-extracted clip
- **Why**: Clip may have timing issues
- **Solution**: Extract from original video using expression timestamps

**Pitfall**: Not using output seeking for audio extraction
- **Why**: May extract wrong segment
- **Solution**: Use output seeking (`ss`/`t` in output)

### 6.3 Subtitle Position Issues

**Pitfall**: Only using `Alignment=8` without `MarginV`
- **Why**: Subtitle may appear at very top edge
- **Solution**: Add `MarginV=50` for proper spacing

---

## 7. Testing and Verification

### 7.1 Manual Testing Checklist

**Long-form Videos**:
- [ ] Video plays full-screen (not side-by-side)
- [ ] Transition appears between video and slide
- [ ] Education slide is full-screen
- [ ] Expression audio plays during slide
- [ ] Subtitles are synchronized

**Short-form Videos**:
- [ ] Video is centered with letterboxing
- [ ] Original aspect ratio is preserved
- [ ] Transition appears between video and slide
- [ ] Education slide is full-screen
- [ ] Subtitles are synchronized

**Dual Subtitles**:
- [ ] Original subtitles appear at bottom
- [ ] Expression subtitle appears at top (yellow, bold)
- [ ] Expression subtitle shows only during expression segment
- [ ] Both subtitles are synchronized

### 7.2 Subtitle Sync Verification

**Method 1**: Visual inspection
- Play video and check if subtitles match dialogue
- Expression subtitle should appear exactly when expression is spoken

**Method 2**: Extract subtitles and compare
```bash
ffmpeg -i output.mkv -map 0:s:0 output.srt
# Compare timestamps with original subtitle file
```

**Method 3**: Check expression clip extraction
- Verify expression clip starts at correct time in context video
- Check if subtitles in expression clip match expression segment

---

## 8. Known Issues and Limitations

### 8.1 Ongoing Issues

**Subtitle Synchronization**:
- ⚠️ **Status**: Still experiencing sync issues
- **Impact**: Subtitles may appear slightly off from dialogue
- **Workaround**: None currently
- **Next Steps**: Further investigation needed

### 8.2 Performance Considerations

**Two-Pass Encoding**:
- Expression clip extraction requires two passes (extract + reset timestamps)
- This doubles encoding time for expression clips
- **Trade-off**: Accuracy over speed (required for subtitle sync)

**Output Seeking**:
- Slower than input seeking (decodes entire video)
- **Trade-off**: Accuracy over speed (required for subtitle sync)

### 8.3 Limitations

**Transition Images**:
- Must be provided in configuration
- Different images for long-form (16:9) and short-form (9:16)
- If missing, transition may fail

**Letterboxing**:
- Always adds black bars (may not be desired for all videos)
- Aspect ratio is preserved, but video may appear smaller

---

## 9. Future Improvements

### 9.1 Subtitle Sync

**Potential Solutions**:
1. Investigate frame-accurate extraction methods
2. Consider using `select` filter with timestamp conditions
3. Explore subtitle stream extraction and re-application

### 9.2 Performance Optimization

**Potential Improvements**:
1. Cache expression clips to avoid re-extraction
2. Optimize two-pass encoding (maybe combine passes)
3. Use hardware acceleration if available

### 9.3 Configuration

**Potential Enhancements**:
1. Make expression subtitle position configurable
2. Make expression subtitle color configurable
3. Add transition animation options

---

## 10. References

### 10.1 Documentation

- `docs/core/subtitle_sync_guide_eng.md` - Subtitle synchronization guide
- `docs/core/subtitle_sync_guide_kor.md` - 자막 동기화 가이드 (한글)
- `tickets/review-required/TICKET-038-longform-sequential-layout.md`
- `tickets/review-required/TICKET-039-shortform-centered-letterbox.md`
- `tickets/review-required/TICKET-040-expression-subtitle-overlay.md`

### 10.2 Code References

- `langflix/core/video_editor.py` - Main video editing logic
- `langflix/media/expression_slicer.py` - Expression slicing (reference for output seeking)
- `langflix/subtitles/overlay.py` - Subtitle overlay functions
- `langflix/media/ffmpeg_utils.py` - FFmpeg utility functions

### 10.3 External Resources

- [FFmpeg Seeking Documentation](https://trac.ffmpeg.org/wiki/Seeking)
- [FFmpeg Filter Documentation](https://ffmpeg.org/ffmpeg-filters.html)
- [ASS Subtitle Format](https://github.com/libass/libass/wiki/ASS-Subtitle-Format)

---

## 11. Contact and Support

**For Issues**:
- Check `docs/core/subtitle_sync_guide_eng.md` for subtitle sync troubleshooting
- Review commit history for recent fixes
- Check logs for FFmpeg errors

**For Questions**:
- Review this document first
- Check code comments in `langflix/core/video_editor.py`
- Refer to ticket documentation in `tickets/review-required/`

---

**Last Updated**: 2025-01-XX  
**Document Version**: 1.0  
**Status**: Active Development

