# Media Module Documentation

## Overview

The `langflix/media/` module contains centralized FFmpeg utilities for LangFlix. This module provides reliable, maintainable video and audio processing functions that ensure audio preservation and optimal performance.

**Last Updated:** 2025-01-30  
**Related Ticket:** TICKET-001

## Purpose

This module is responsible for:
- Centralizing all FFmpeg-related logic
- Providing explicit stream mapping helpers to prevent audio loss
- Ensuring original video format preservation (codec, resolution, pixel format) when possible
- Offering reliable concatenation and stacking operations
- Supporting demuxer-first approach for maximum reliability

## Goals

1. **Keep original video format** (codec, resolution, pixel format) whenever possible
2. **Force audio to stereo 48k** consistently to avoid concat/drop issues
3. **Provide explicit stream mapping** helpers to prevent audio loss
4. **Offer safe probing** and parameter extraction
5. **Support demuxer-first** approach for concatenation and repetition

## Key Functions

### Probing Functions

#### `run_ffprobe(path: str) -> Dict[str, Any]`
Runs ffprobe and returns parsed JSON, raising on failure.

- Uses subprocess for reliable error handling
- Falls back to ffmpeg-python probe if needed

#### `get_video_params(path: str) -> VideoParams`
Extracts video parameters from a file.

**Returns VideoParams:**
- `codec`: Video codec (e.g., "h264", "hevc")
- `width`: Video width in pixels
- `height`: Video height in pixels
- `pix_fmt`: Pixel format (e.g., "yuv420p")
- `r_frame_rate`: Frame rate (e.g., "25/1")

#### `get_audio_params(path: str) -> AudioParams`
Extracts audio parameters from a file.

**Returns AudioParams:**
- `codec`: Audio codec (e.g., "aac", "mp3")
- `channels`: Number of audio channels
- `sample_rate`: Sample rate in Hz

#### `get_duration_seconds(path: str) -> float`
Gets media duration in seconds.

- Uses ffprobe for accurate duration
- Returns 0.0 on error

### Concatenation Functions

#### `repeat_av_demuxer(input_path: str, repeat_count: int, out_path: Path | str) -> None`
**TICKET-001 Enhancement:** Repeat AV segment N times using concat demuxer for maximum reliability.

This is the **preferred method** for expression repetition.

**How it works:**
1. Creates temporary concat list file with N copies of input
2. Uses concat demuxer (copy mode) to preserve audio and timestamps
3. Falls back to file-based method if pipe input fails

**Benefits:**
- Preserves audio reliably (no audio drops)
- Preserves timestamps (no A-V sync issues)
- Simpler pipeline (no complex filter graphs)
- Better performance (copy mode, no re-encode)

**Example:**
```python
from langflix.media.ffmpeg_utils import repeat_av_demuxer

# Repeat expression clip 3 times
repeat_av_demuxer("expression_clip.mkv", repeat_count=3, out_path="repeated.mkv")
```

#### `concat_demuxer_if_uniform(list_file: Path | str, out_path: Path | str) -> None`
**TICKET-001 Enhancement:** Use concat demuxer when all inputs are uniform.

**How it works:**
1. Reads concat list file (format: `file 'path'\nfile 'path'\n...`)
2. Probes first file to get encoding params
3. Uses concat demuxer with copy mode (no re-encode)
4. Preserves timestamps perfectly

**When to use:**
- All inputs have same codec/resolution/frame rate
- You want copy mode (no re-encode, better performance)
- You need to preserve timestamps (prevents A-V sync issues)

**Example:**
```python
# Create concat list file
with open("concat.txt", "w") as f:
    f.write("file 'video1.mkv'\n")
    f.write("file 'video2.mkv'\n")

# Concatenate using demuxer
concat_demuxer_if_uniform("concat.txt", "output.mkv")
```

#### `concat_filter_with_explicit_map(left_path: str, right_path: str, out_path: Path | str) -> None`
Concat two segments with filter concat ensuring v=1,a=1 and explicit mapping.

**TICKET-001 Enhancement:** Now includes automatic fallback to demuxer concat.

**How it works:**
1. Normalizes frame rate to 25fps to prevent A-V sync issues
2. Resets timestamps (setpts/asetpts) to start from 0
3. Uses explicit stream mapping (v=1,a=1)
4. Falls back to demuxer concat if filter concat fails

**When to use:**
- Input parameters differ (different codecs/resolutions)
- Frame rate normalization needed
- Demuxer concat fails

**Example:**
```python
# Concatenate two videos with different parameters
concat_filter_with_explicit_map("video1.mkv", "video2.mkv", "output.mkv")
```

### Stacking Functions

#### `hstack_keep_height(left_path: str, right_path: str, out_path: Path | str) -> None`
**TICKET-001 Enhancement:** Stack two videos horizontally keeping source heights.

Used for **long-form layout** (side-by-side).

**How it works:**
1. Scales right video to match left height (preserves aspect ratio)
2. Stacks horizontally (hstack)
3. Uses audio from left input
4. Preserves original video encoding params

**Example:**
```python
# Long-form: context+expression on left, slide on right
hstack_keep_height("left_video.mkv", "right_slide.mkv", "long_form.mkv")
```

#### `vstack_keep_width(top_path: str, bottom_path: str, out_path: Path | str) -> None`
**TICKET-001 Enhancement:** Stack two videos vertically keeping source widths.

Used for **short-form layout** (top-bottom).

**How it works:**
1. Scales bottom video to match top width (preserves aspect ratio)
2. Stacks vertically (vstack)
3. Uses audio from top input
4. Preserves original video encoding params

**Example:**
```python
# Short-form: video on top, slide on bottom
vstack_keep_width("top_video.mkv", "bottom_slide.mkv", "short_form.mkv")
```

### Audio Processing Functions

#### `apply_final_audio_gain(input_path: str, out_path: Path | str, gain_factor: float = 1.25) -> None`
**TICKET-001 Enhancement:** Apply audio gain as separate final pass (simple map, no filter_complex).

**How it works:**
1. Extracts video and audio streams
2. Applies volume filter to audio only (gain_factor, default 1.25 = +25%)
3. Copies video stream (no re-encode if possible)
4. Encodes audio (requires encoding due to filter)

**When to use:**
- Final step in pipeline (after layout is complete)
- Need to boost audio volume
- Want to preserve video stream

**Example:**
```python
# Apply final audio boost (+25%)
apply_final_audio_gain("final_video.mkv", "output.mkv", gain_factor=1.25)
```

### Encoding Helpers

#### `make_video_encode_args_from_source(source_path: str) -> Dict[str, Any]`
Create encoder arguments that match the source video as closely as possible.

- Reuses source codec when possible (h264, hevc, vp9, prores)
- Preserves resolution
- Avoids forcing pixel format unless necessary

#### `make_audio_encode_args(normalize: bool = False) -> Dict[str, Any]`
Get audio encoding arguments.

- If `normalize=True`: Normalizes to stereo/48k (aac codec)
- If `normalize=False`: Uses copy mode (no re-encode)

#### `make_audio_encode_args_copy() -> Dict[str, Any]`
Prefer copying audio without re-encoding.

- Returns `{"acodec": "copy"}`

### Utility Functions

#### `should_copy_video(input_path: str) -> bool`
Decide whether we can `-c:v copy` safely.

- Returns True if video has valid codec/width/height
- Used to determine if copy mode is possible

#### `log_media_params(path: str, label: str = "media") -> None`
Log media parameters for debugging.

- Logs video codec, resolution, pixel format
- Logs audio codec, channels, sample rate

## Architecture Patterns

### Demuxer-First Approach (TICKET-001)

**Priority Order:**
1. **Demuxer concat** (preferred) - copy mode, preserves timestamps
2. **Filter concat** (fallback) - when parameters differ or demuxer fails

**Benefits:**
- Maximum reliability (fewer audio drops)
- Better performance (copy mode, no re-encode)
- Preserves timestamps (no A-V sync issues)
- Simpler pipeline graphs

### Explicit Stream Mapping

**Critical for audio preservation:**
- Always use `v=1,a=1` in filter concat
- Always map video and audio streams explicitly in output
- Use `output_with_explicit_streams()` helper

### Copy Mode Preference

**Prefer copy mode when:**
- No filters are applied
- Parameters are uniform
- Timestamp preservation is critical

**Use encoding when:**
- Filters are required
- Parameters need normalization
- Format conversion is needed

## Common Tasks

### Adding a New Stacking Operation

1. Create new function in `ffmpeg_utils.py` (e.g., `grid_keep_aspect()`)
2. Use same pattern: probe params → scale → stack → explicit output
3. Preserve audio from primary input
4. Add tests in `tests/integration/test_media_pipeline_*.py`

### Modifying Concatenation Logic

1. Prefer demuxer concat when possible (copy mode)
2. Use filter concat as fallback (with frame rate normalization)
3. Always include explicit stream mapping
4. Add automatic fallback between methods

### Debugging Audio Drops

1. **Check explicit mapping:**
   ```python
   # Ensure v=1,a=1 in filter concat
   concat_node = ffmpeg.concat(v1, a1, v2, a2, v=1, a=1, n=2)
   ```

2. **Verify audio presence:**
   ```bash
   ffprobe -v error -show_entries stream=codec_type input.mkv | grep audio
   ```

3. **Check copy mode:**
   ```python
   # Look for "acodec=copy" in encode args
   encode_args = make_audio_encode_args_copy()
   ```

## Gotchas and Notes

### Demuxer Concat Requirements

⚠️ **Important:** Demuxer concat requires:
- Uniform codec across inputs
- Uniform resolution (or compatible aspect ratios)
- Uniform frame rate (or compatible rates)
- Same container format

**If parameters differ:** Use `concat_filter_with_explicit_map()` instead.

### Frame Rate Normalization

⚠️ **Critical for A-V Sync:** Filter concat normalizes frame rate to 25fps:
- Prevents freezing during playback
- Ensures smooth A-V sync
- Resets timestamps to start from 0

**If you see A-V sync issues:** Verify frame rate normalization is applied.

### Copy Mode Limitations

⚠️ **Cannot use copy mode when:**
- Filters are applied (fps, scale, volume, etc.)
- Parameters need normalization
- Format conversion is required

**Use encoding when:** Any filter or normalization is needed.

### Audio Processing Order

✅ **Best Practice:** Apply audio transformations at the end:
1. Build video pipeline (concat, stack, etc.)
2. Apply audio gain as final step
3. No mid-pipeline audio transforms

**Reason:** Preserves audio throughout pipeline, only modifies at final step.

## Testing

### Integration Tests
- `tests/integration/test_media_pipeline_audio.py` - Audio preservation through pipeline
- `tests/functional/test_educational_video.py` - End-to-end video creation

### Verification Script
- `tools/verify_media_pipeline.py` - Comprehensive pipeline verification
  - Tests demuxer repeat
  - Tests concat operations
  - Tests stack operations
  - Verifies audio presence with ffprobe

## Related Documentation

- [ADR-015: FFmpeg Pipeline Standardization](../adr/ADR-015-ffmpeg-pipeline-standardization_eng.md)
- [Core Module Documentation](../core/README_eng.md)
- [Troubleshooting Guide](../TROUBLESHOOTING_GUIDE.md#videoaudio-sync-problems-a-v-sync)

