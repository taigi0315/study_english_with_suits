# Structured Video Creation - New Architecture

**Date**: 2025-01-XX  
**Branch**: `feature/multiple-expressions-per-context`  
**Status**: Implemented

---

## Executive Summary

This document describes the new structured video creation architecture that replaces the previous long-form/short-form distinction. The system now creates:

1. **Structured Videos**: Individual videos for each expression with format `[context → expression repeat (2x) → slide (expression audio 2x)]`
2. **Combined Structured Video**: All structured videos concatenated into one
3. **Short-form Videos**: Vertical 9:16 videos created from structured videos with special layout

---

## 1. Architecture Overview

### 1.1 Key Changes

**Before (Old Architecture)**:
- Long-form videos: Side-by-side or sequential layout
- Short-form videos: Top-bottom layout with vstack
- Expression grouping: Multiple expressions per context (ExpressionGroup)

**After (New Architecture)**:
- **Structured videos**: Each expression gets its own structured video (1:1 mapping)
- **No long-form/short-form distinction**: All videos follow the same structure
- **Individual expression processing**: No grouping, each expression processed independently
- **Short-form videos**: Created from structured videos with 9:16 layout

### 1.2 Video Output Structure

```
output/Series/Episode/translations/ko/
├── structured_videos/                    # New directory
│   ├── structured_video_{expression_1}.mkv
│   ├── structured_video_{expression_2}.mkv
│   ├── ...
│   └── combined_structured_video_{episode}.mkv  # All combined
└── short_form_videos/                    # Short-form videos
    ├── short_form_{expression_1}.mkv
    ├── short_form_{expression_2}.mkv
    ├── ...
    └── short-form_{episode}_{batch_01}.mkv  # Batched videos
```

---

## 2. Structured Video Creation

### 2.1 Method: `create_structured_video()`

**File**: `langflix/core/video_editor.py`  
**Method**: `create_structured_video()`  
**Lines**: ~540-727

**Purpose**: Create a structured video for a single expression following the pattern:
```
[Context Video] → [Expression Video (2x)] → [Educational Slide (Expression Audio 2x)]
```

**Process**:
1. Extract expression clip from context video
2. Repeat expression clip 2 times
3. Concatenate: context → expression (2x)
4. Create educational slide with expression audio (2x)
5. Concatenate: context+expression → slide
6. Apply final audio gain

**Key Features**:
- **No transitions**: Structured videos do not include transition effects
- **16:9 or original ratio**: Maintains original video aspect ratio
- **Expression audio**: Uses original expression audio from video, not TTS
- **2x repetition**: Expression video and audio both repeat 2 times

**Code Example**:
```python
structured_video = self.video_editor.create_structured_video(
    expression,
    str(context_video),  # Context clip for this expression
    expression_source_video,  # Original video for expression audio
    expression_index=expr_idx  # Expression index for voice alternation
)
```

### 2.2 Combined Structured Video

**File**: `langflix/main.py`  
**Method**: `_create_combined_structured_video()`  
**Lines**: ~1022-1006

**Purpose**: Concatenate all structured videos into a single combined video

**Process**:
1. Collect all structured videos
2. Validate video files exist and are valid
3. Create concat file with all video paths
4. Concatenate using FFmpeg concat demuxer
5. Output to `structured_videos/combined_structured_video_{episode}.mkv`

**Features**:
- Maintains 16:9 or original aspect ratio
- No transitions between structured videos
- Simple concatenation for seamless playback

---

## 3. Short-form Video Creation

### 3.1 Method: `create_short_form_from_structured()`

**File**: `langflix/core/video_editor.py`  
**Method**: `create_short_form_from_structured()`  
**Lines**: ~737-1037

**Purpose**: Convert structured video (16:9) to short-form video (9:16) with special layout

**Layout Specification**:
- **Target Resolution**: 1080x1920 (9:16 vertical)
- **Structured Video**: 
  - Centered in middle of screen
  - Height: 960px (half of total height)
  - Left/right cropped (no stretching)
  - Maintains original aspect ratio
- **Expression Text**: 
  - Displayed at top (outside structured video area)
  - Position: y=50px from top
  - Color: Yellow, bold, centered
  - Background: Black screen
- **Subtitles**: 
  - Displayed at bottom (outside structured video area)
  - Position: MarginV=100 (100px from bottom)
  - Color: White
  - Background: Black screen

**Process**:
1. Scale structured video to height 960px (maintain aspect ratio)
2. Crop left/right if width exceeds 1080px (center crop)
3. Create 1080x1920 black background
4. Center structured video vertically (y_offset calculation)
5. Add expression text at top using drawtext filter
6. Apply subtitles at bottom using ASS subtitle overlay
7. Output final short-form video

**Code Example**:
```python
short_form_video = self.video_editor.create_short_form_from_structured(
    str(structured_video),
    expression,
    expression_index=expr_idx
)
```

### 3.2 Short-form Batching

**File**: `langflix/main.py`  
**Method**: `_create_batched_short_videos_with_max_duration()`  
**Lines**: ~957-1020

**Purpose**: Batch short-form videos with maximum duration limit

**Configuration**:
- **Default max_duration**: 180 seconds (configurable)
- **Location**: `langflix/config/default.yaml` → `short_video.max_duration`
- **UI Setting**: User can set via `short_form_max_duration` parameter

**Process**:
1. Iterate through short-form videos
2. Check if video exceeds max_duration → drop if exceeds
3. Add videos to batch until max_duration reached
4. Create batch video when limit reached
5. Continue with next batch

**Features**:
- Videos exceeding max_duration are dropped (not included)
- Batches created sequentially
- Each batch maintains 9:16 aspect ratio

---

## 4. Expression Processing Changes

### 4.1 Removal of ExpressionGroup

**Before**: Expressions were grouped by context using `ExpressionGroup`
- Multiple expressions could share the same context
- Grouped expressions processed together

**After**: Each expression processed individually
- **1 context → 1 expression** rule (each expression has its own context)
- No grouping logic
- Each expression gets its own structured video

**Code Changes**:
- `group_expressions_by_context()` function removed/not used
- `_process_expressions()` creates individual context videos per expression
- `_create_educational_videos()` processes expressions individually

### 4.2 Context Video Creation

**File**: `langflix/main.py`  
**Method**: `_process_expressions()`  
**Lines**: ~650-724

**Process**:
1. For each expression individually:
   - Extract context time range
   - Create context video clip
   - Save as `temp_expression_{idx}_{name}.mkv`
2. No grouping or merging of contexts
3. Each expression has independent context video

---

## 5. Configuration

### 5.1 Short-form Max Duration

**Location**: `langflix/config/default.yaml`

```yaml
short_video:
  enabled: true
  resolution: "1080x1920"
  target_duration: 120
  duration_variance: 10
  max_duration: 180  # Maximum duration for short-form batches (seconds)
```

**Access**: `langflix/settings.py` → `get_short_video_max_duration()`

### 5.2 API Parameters

**Endpoint**: `POST /api/v1/jobs`

**New Parameter**:
- `short_form_max_duration` (float, default: 180.0)
  - Maximum duration for short-form video batches
  - Videos exceeding this duration are dropped

**Example**:
```json
{
  "video_file": "...",
  "subtitle_file": "...",
  "language_code": "ko",
  "show_name": "Suits",
  "episode_name": "S02E01",
  "short_form_max_duration": 180.0
}
```

### 5.3 UI Configuration

**File**: `langflix/templates/video_dashboard.html`

**New Input Field**:
- Short-form Max Duration (seconds)
- Default: 180
- Range: 60-300
- Step: 10

---

## 6. File Structure

### 6.1 Output Directories

```
output/Series/Episode/translations/ko/
├── structured_videos/              # NEW: Structured videos directory
│   ├── structured_video_{expr1}.mkv
│   ├── structured_video_{expr2}.mkv
│   └── combined_structured_video_{episode}.mkv
├── short_form_videos/              # Short-form videos
│   ├── short_form_{expr1}.mkv
│   ├── short_form_{expr2}.mkv
│   └── short-form_{episode}_{batch}.mkv
└── ...
```

### 6.2 Directory Creation

**File**: `langflix/services/output_manager.py`

**New Directory**: `structured_videos` added to language structure

```python
structured_videos_dir = lang_dir / "structured_videos"
structured_videos_dir.mkdir(exist_ok=True)
```

---

## 7. Key Technical Details

### 7.1 Video Scaling and Cropping

**Short-form Video Processing**:
1. Calculate scale factor: `scale_factor = 960 / original_height`
2. Scale to height: `scaled_width = original_width * scale_factor`
3. If `scaled_width > 1080`: Crop from center
   - `crop_x = (scaled_width - 1080) // 2`
   - Crop: `1080 x 960` from center

**No Stretching**: Video aspect ratio always maintained

### 7.2 Subtitle Positioning

**Expression Text (Top)**:
- FFmpeg drawtext filter
- Position: `x='(w-text_w)/2'` (centered), `y=50` (50px from top)
- Style: Yellow, bold, 48px font

**Subtitles (Bottom)**:
- ASS subtitle overlay
- Style: `Alignment=2` (bottom center), `MarginV=100` (100px from bottom)
- Color: White, 32px font

### 7.3 Audio Processing

**Structured Videos**:
- Expression audio extracted from original video using output seeking
- Audio repeated 2 times to match video repetition
- Final audio gain applied (+69%)

**Short-form Videos**:
- Audio from structured video preserved
- No additional audio processing

---

## 8. Migration Notes

### 8.1 Breaking Changes

1. **No ExpressionGroup**: Code expecting `ExpressionGroup` objects will need updates
2. **No long-form/short-form distinction**: All videos follow structured format
3. **New directory structure**: `structured_videos/` directory added
4. **API changes**: New `short_form_max_duration` parameter

### 8.2 Backward Compatibility

- Old methods (`create_educational_sequence`, `create_short_format_video`) still exist but not used
- Can be removed in future cleanup
- Test code may need updates

---

## 9. Testing

### 9.1 Test Scenarios

1. **Single Expression**:
   - Verify structured video created
   - Verify combined video created
   - Verify short-form video created

2. **Multiple Expressions**:
   - Verify each expression gets its own structured video
   - Verify combined video contains all expressions
   - Verify short-form batching works correctly

3. **Max Duration**:
   - Verify videos exceeding max_duration are dropped
   - Verify batches don't exceed max_duration
   - Verify UI parameter is passed correctly

### 9.2 Known Issues

- None currently identified
- Monitor for subtitle synchronization issues
- Monitor for video quality issues after scaling/cropping

---

## 10. Future Improvements

1. **Transition Support**: Add optional transitions between structured videos
2. **Custom Aspect Ratios**: Support custom aspect ratios for structured videos
3. **Batch Optimization**: Improve batching algorithm for better duration distribution
4. **Quality Settings**: Add quality settings for short-form video scaling

---

**Last Updated**: 2025-01-XX  
**Maintainer**: Development Team


