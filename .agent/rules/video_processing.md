# Video Processing Rules

> Critical rules for video processing in LangFlix

---

## FFmpeg Operations

### ⚠️ MUST: Use Output Seeking for Subtitles

When processing videos with subtitles, always use **output seeking** (parameters after input):

```python
# ✅ CORRECT: Output seeking (ss/t after input)
ffmpeg.output(
    video_stream,
    audio_stream,
    str(output_path),
    ss=relative_start,  # After input
    t=duration
).run()

# ❌ WRONG: Input seeking - causes subtitle misalignment
ffmpeg.input(str(video), ss=start)  # Don't do this for subtitled videos
```

### Quality Encoding Standards

| Parameter | Value | Purpose |
|-----------|-------|---------|
| CRF | 18 | High quality (lower = better, 18 is visually lossless) |
| Preset | slow | Best compression at given CRF |
| Audio Bitrate | 256k | High quality audio |

```python
# Quality encoding example
ffmpeg.output(
    video_stream,
    audio_stream,
    str(output_path),
    vcodec='libx264',
    crf=18,
    preset='slow',
    acodec='aac',
    audio_bitrate='256k'
)
```

---

## Clip Extraction

- Frame-accurate extraction (0.1s precision)
- Buffer times: 0.2s before/after expression (configurable)
- Apply dual-language subtitle overlay on context clips

### Timestamp Reset for Concatenation

```python
ffmpeg.filter('setpts', 'PTS-STARTPTS')
```

---

## Temporary File Management

```python
# Register for automatic cleanup
temp_file = self.output_dir / f"temp_expr_{safe_name}.mkv"
self._register_temp_file(temp_file)
```

---

## Video Format Specifications

### Structured Video (16:9)
- Context clip + expression repeat (2x) + educational slide
- Audio gain: +69%

### Short-form Video (9:16)
- Dimensions: 1080x1920
- Top: Expression text (black background, 180px)
- Middle: Video (centered, height 960px)
- Bottom: Subtitles (black background, 100px from bottom)
