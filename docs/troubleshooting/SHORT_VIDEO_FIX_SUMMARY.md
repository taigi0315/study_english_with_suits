# Short Video Audio-Video Sync Fix Summary

## Problem
Short video expression sections showed **freeze frame** instead of actual video playback during expression repetition, with audio playing but no visual movement.

## Root Cause Analysis

### Issue 1: FFmpeg Loop Filter Failure
- Original code used `ffmpeg loop filter` to repeat expression video
- Filter failed with `t=required_expression_duration` parameter causing conflicts
- Result: Expression video creation failed → fallback to freeze frame

### Issue 2: Repeat Count Mismatch
- Audio timeline was using `get_tts_repeat_count()` → 2 repetitions
- Video editor was using `get_short_video_expression_repeat_count()` → 3 repetitions
- Result: Audio-video duration mismatch

### Issue 3: Audio Source Error
- Combined video (context + expression) had no audio (video only)
- Code tried to boost audio from video file → no audio to boost
- Result: Silent video or incorrect audio

## Solution Implemented

### 1. Unified Repeat Count Configuration
Created single source of truth for expression repeat count:

```yaml
# langflix/config/default.yaml
expression:
  repeat_count: 3  # Unified setting for all expression repetitions
```

Removed duplicate configurations:
- ~~`tts.repeat_count: 2`~~ → removed
- ~~`short_video.expression_repeat_count: 3`~~ → removed

### 2. New Settings Function
```python
# langflix/settings.py
def get_expression_repeat_count() -> int:
    """Get unified expression repeat count for all video types"""
    return int(get_expression_config().get('repeat_count', 3))
```

Legacy functions now use unified setting:
```python
def get_tts_repeat_count() -> int:
    """DEPRECATED: Use get_expression_repeat_count() instead"""
    return get_expression_repeat_count()

def get_short_video_expression_repeat_count() -> int:
    """DEPRECATED: Use get_expression_repeat_count() instead"""
    return get_expression_repeat_count()
```

### 3. Concat Demuxer Instead of Loop Filter
Changed from unreliable loop filter to stable concat demuxer:

**Before (BROKEN):**
```python
(ffmpeg.input(str(expression_video_path))
 .video.filter('loop', loop=num_loops-1, size=32767)
 .audio.filter('aloop', loop=num_loops-1, size=32767)
 .output(str(looped_expression_path), vcodec='libx264', acodec='aac', 
         t=required_expression_duration, preset='fast', crf=23)  # ❌ t param breaks loop
 .overwrite_output()
 .run(quiet=True))
```

**After (FIXED):**
```python
# Create concat file listing expression video N times
concat_file = output_dir / f"temp_expression_concat_{safe_expression}.txt"
with open(concat_file, 'w') as f:
    for i in range(num_loops):
        f.write(f"file '{expression_video_path.absolute()}'\n")

# Use concat demuxer (no audio, video only)
(ffmpeg.input(str(concat_file), format='concat', safe=0)
 .output(str(looped_expression_path), vcodec='libx264', 
         t=required_expression_duration, preset='fast', crf=23)  # ✅ Works!
 .overwrite_output()
 .run(quiet=True))
```

### 4. Separate Audio Processing
- Expression video extraction: video only (`an=None`)
- Audio processing: separate combined audio track
- Final output: concat demuxer for video, combined audio from timeline

### 5. Audio Source Fix
```python
# Fixed: Use combined audio timeline instead of video file
audio_source = tts_audio_path  # ✅ Combined audio with proper timeline
# NOT: audio_source = concatenated_video_path  # ❌ Video has no audio
```

## Files Modified

1. **langflix/config/default.yaml**
   - Added `expression.repeat_count: 3`
   - Removed duplicate `tts.repeat_count` and `short_video.expression_repeat_count`

2. **langflix/settings.py**
   - Added `get_expression_repeat_count()` function
   - Modified legacy functions to use unified setting

3. **langflix/audio/original_audio_extractor.py**
   - Added `repeat_count` parameter to `create_audio_timeline()`
   - Changed default source from `get_tts_repeat_count()` to `get_expression_repeat_count()`
   - Updated convenience function signature

4. **langflix/core/video_editor.py**
   - Changed from `get_short_video_expression_repeat_count()` to `get_expression_repeat_count()`
   - Updated expression video extraction: `an=None` (video only)
   - Replaced loop filter with concat demuxer approach
   - Fixed audio source: use `tts_audio_path` instead of `concatenated_video_path`
   - Enhanced error logging with stderr output

## Testing

### Unit Tests Created
- `test_expression_video_loop.py` - Configuration, concat file, duration calculation
- `test_ffmpeg_concat.py` - Actual FFmpeg concat demuxer with real video files
- `test_repeat_count_flow.py` - Repeat count parameter flow

### Test Results
```
✅ Configuration unified: All return 3
✅ Concat file creation: Works correctly
✅ Duration calculation: Correct (10.5s for 3 reps)
✅ FFmpeg concat demuxer: Successfully looped 2s clip → 6.01s
✅ Repeat count flow: Function accepts parameter correctly
```

## Expected Behavior After Fix

**Before:**
```
Context video (plays) → Freeze frame on last frame (no audio) → Next context
❌ Video static, audio playing expression repetition
```

**After:**
```
Context video (plays with audio) → Expression video loop 3x (plays with audio) → Next context
✅ Video loops showing expression, audio syncs perfectly
```

## Configuration

To change expression repeat count, edit one place:

```yaml
# langflix/config/default.yaml
expression:
  repeat_count: 3  # Change this to adjust repetition for all videos
```

This affects:
- TTS audio generation
- Original audio extraction
- Short video loops
- Educational video playback

## Validation Checklist

- [x] Unified configuration created
- [x] Legacy functions deprecated but working
- [x] Concat demuxer implementation tested
- [x] Audio processing fixed
- [x] Error logging enhanced
- [x] All tests passing
- [ ] **Actual video generation pending** - Ready to test!

## Next Steps

To verify the fix works:
1. Run pipeline to generate new short videos
2. Check logs for "Using repeat count: 3" (not 2)
3. Verify no "Failed to create expression video" warnings
4. Play video and confirm expression section shows actual video, not freeze frame

---

**Status:** Code changes complete, ready for production testing.
