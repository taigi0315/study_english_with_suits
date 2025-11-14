# Subtitle Synchronization Guide

## Overview

This guide explains the proper way to apply subtitles to videos in the LangFlix pipeline to ensure accurate synchronization. Subtitle sync issues are a common problem that can occur when making changes to video processing code.

## Key Principles

### 1. Output Seeking vs Input Seeking

FFmpeg supports two types of seeking:

- **Input Seeking** (`-ss` before `-i`): Faster but less accurate. FFmpeg seeks to the nearest keyframe, which may not match the exact timestamp.
- **Output Seeking** (`-ss` after `-i`): Slower but more accurate. FFmpeg decodes the entire video and seeks to the exact timestamp.

**For subtitle synchronization, always use output seeking.**

### 2. Why Subtitle Sync Breaks

Subtitle sync can break when:

1. **Using input seeking instead of output seeking**: When extracting video clips, using `-ss` before `-i` can cause timing mismatches.
2. **Timestamp reset issues**: When extracting clips, timestamps must be reset to start from 0 using `setpts` filters.
3. **Subtitle file timestamps**: Subtitle files must have timestamps relative to the video they're applied to (starting from 0).

## Proper Implementation

### Extracting Expression Clips from Context Video

When extracting an expression clip from a context video, use output seeking:

```python
# ❌ WRONG: Input seeking (faster but inaccurate)
input_stream = ffmpeg.input(str(context_with_subtitles), ss=relative_start, t=expression_duration)

# ✅ CORRECT: Output seeking (slower but accurate)
input_stream = ffmpeg.input(str(context_with_subtitles))
# Apply seeking and duration trimming after input (output seeking)
video_stream = ffmpeg.filter(input_stream['v'], 'setpts', 'PTS-STARTPTS')
audio_stream = ffmpeg.filter(input_stream['a'], 'asetpts', 'PTS-STARTPTS')

ffmpeg.output(
    video_stream,
    audio_stream,
    str(output_path),
    ss=relative_start,  # Output seeking: apply after input for accuracy
    t=expression_duration  # Duration limit
)
```

### Applying Subtitles to Context Video

When applying subtitles to a context video:

1. **Ensure subtitle timestamps are relative to context start (0)**:
   - The subtitle file should have timestamps starting from 0
   - If the subtitle file has timestamps relative to the original video, adjust them to be relative to the context start

2. **Use proper subtitle overlay**:
   - Use `apply_dual_subtitle_layers()` for dual subtitles (original + expression)
   - Ensure expression subtitle timing matches the expression segment in the context video

### Extracting Audio from Original Video

When extracting audio from the original video for educational slides:

```python
# ✅ CORRECT: Extract audio using expression timestamps with output seeking
expression_start_seconds = self._time_to_seconds(expression.expression_start_time)
expression_end_seconds = self._time_to_seconds(expression.expression_end_time)
expression_audio_duration = expression_end_seconds - expression_start_seconds

audio_input = ffmpeg.input(str(original_video_path))
audio_stream = audio_input['a']

ffmpeg.output(
    audio_stream,
    str(output_path),
    ss=expression_start_seconds,  # Output seeking: apply after input for accuracy
    t=expression_audio_duration  # Duration limit
)
```

## Code Locations

### Expression Clip Extraction

**File**: `langflix/core/video_editor.py`  
**Method**: `create_educational_sequence()`  
**Lines**: ~179-208

```python
# IMPORTANT: Use output seeking for accurate subtitle sync
input_stream = ffmpeg.input(str(context_with_subtitles))
video_stream = ffmpeg.filter(input_stream['v'], 'setpts', 'PTS-STARTPTS')
audio_stream = ffmpeg.filter(input_stream['a'], 'asetpts', 'PTS-STARTPTS')

ffmpeg.output(
    video_stream,
    audio_stream,
    str(expression_video_clip_path),
    ss=relative_start,  # Output seeking
    t=expression_duration
)
```

### Expression Audio Extraction

**File**: `langflix/core/video_editor.py`  
**Method**: `_create_educational_slide()`  
**Lines**: ~1609-1649

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

### Expression Slicer

**File**: `langflix/media/expression_slicer.py`  
**Method**: `slice_expression()`  
**Lines**: ~129-143

```python
# IMPORTANT: Put -ss AFTER -i for accurate seeking and subtitle sync
ffmpeg_cmd = [
    'ffmpeg',
    '-i', media_path,
    '-ss', str(start_time),  # Seek to start (output seeking for accuracy)
    '-t', str(duration),  # Duration
    # ... other options
]
```

## Common Mistakes to Avoid

### ❌ Don't Use Input Seeking for Subtitle Sync

```python
# WRONG: Input seeking (causes subtitle sync issues)
input_stream = ffmpeg.input(str(video_path), ss=start_time, t=duration)
```

### ❌ Don't Forget to Reset Timestamps

```python
# WRONG: Timestamps not reset (causes delay in repeated clips)
video_stream = input_stream['v']
audio_stream = input_stream['a']
```

### ✅ Always Use Output Seeking and Reset Timestamps

```python
# CORRECT: Output seeking with timestamp reset
input_stream = ffmpeg.input(str(video_path))
video_stream = ffmpeg.filter(input_stream['v'], 'setpts', 'PTS-STARTPTS')
audio_stream = ffmpeg.filter(input_stream['a'], 'asetpts', 'PTS-STARTPTS')

ffmpeg.output(
    video_stream,
    audio_stream,
    str(output_path),
    ss=start_time,  # Output seeking
    t=duration
)
```

## Testing Subtitle Sync

To verify subtitle synchronization:

1. **Check subtitle timing in output video**:
   ```bash
   ffprobe -v error -show_entries frame=pkt_pts_time -select_streams v:0 output.mkv
   ```

2. **Extract subtitles from output video**:
   ```bash
   ffmpeg -i output.mkv -map 0:s:0 output.srt
   ```

3. **Compare with original subtitle file**:
   - Open both subtitle files in a text editor
   - Verify timestamps match the video content

## References

- [FFmpeg Seeking Documentation](https://trac.ffmpeg.org/wiki/Seeking)
- [FFmpeg Filter Documentation](https://ffmpeg.org/ffmpeg-filters.html)
- `langflix/core/video_editor.py` - Main video editing logic
- `langflix/media/expression_slicer.py` - Expression slicing with proper seeking
- `langflix/subtitles/overlay.py` - Subtitle overlay functions

## Summary

**Key Takeaways**:

1. **Always use output seeking** (`-ss` after `-i`) for subtitle synchronization
2. **Reset timestamps** using `setpts` filters when extracting clips
3. **Ensure subtitle timestamps** are relative to the video they're applied to (starting from 0)
4. **Extract audio from original video** using expression timestamps with output seeking
5. **Test subtitle sync** after any changes to video processing code

When in doubt, prefer accuracy over speed. Subtitle sync issues are harder to debug than slower processing times.

