# FFmpeg Patterns

> Common FFmpeg patterns used in LangFlix

---

## Video Extraction

### Extract Clip with Output Seeking (Recommended)

```python
import ffmpeg

# Output seeking - accurate for subtitles
stream = ffmpeg.input(str(video_path))
stream = ffmpeg.output(
    stream.video,
    stream.audio,
    str(output_path),
    ss=start_time,      # Output seeking
    t=duration,
    c='copy'            # Stream copy when possible
)
stream.run(overwrite_output=True)
```

### Re-encode Clip (When Needed)

```python
stream = ffmpeg.input(str(video_path))
stream = ffmpeg.output(
    stream.video,
    stream.audio,
    str(output_path),
    ss=start_time,
    t=duration,
    vcodec='libx264',
    crf=18,
    preset='slow',
    acodec='aac',
    audio_bitrate='256k'
)
```

---

## Concatenation

### Concat Filter (Same codec)

```python
# Prepare inputs with timestamp reset
inputs = []
for video in video_list:
    stream = ffmpeg.input(str(video))
    v = stream.video.filter('setpts', 'PTS-STARTPTS')
    a = stream.audio.filter('asetpts', 'PTS-STARTPTS')
    inputs.extend([v, a])

# Concatenate
joined = ffmpeg.concat(*inputs, v=1, a=1)
output = ffmpeg.output(joined, str(output_path))
output.run()
```

### Concat Demuxer (Different codecs)

```python
# Create concat file
with open('concat.txt', 'w') as f:
    for video in video_list:
        f.write(f"file '{video}'\n")

# Run concat
ffmpeg.input('concat.txt', f='concat', safe=0).output(
    str(output_path),
    c='copy'
).run()
```

---

## Subtitle Overlay

### Burn Subtitles

```python
stream = ffmpeg.input(str(video_path))
stream = stream.filter(
    'subtitles',
    str(subtitle_path),
    force_style='FontSize=24,PrimaryColour=&HFFFFFF&'
)
ffmpeg.output(stream, str(output_path)).run()
```

### ASS Subtitle Style

```python
force_style = (
    'FontName=Arial,'
    'FontSize=24,'
    'PrimaryColour=&HFFFFFF&,'
    'OutlineColour=&H000000&,'
    'Outline=2,'
    'Shadow=1'
)
```

---

## Audio Processing

### Extract Audio

```python
ffmpeg.input(str(video_path)).output(
    str(audio_path),
    acodec='aac',
    audio_bitrate='256k'
).run()
```

### Adjust Volume

```python
stream = ffmpeg.input(str(video_path))
audio = stream.audio.filter('volume', 1.69)  # +69% gain
ffmpeg.output(stream.video, audio, str(output_path)).run()
```

### Mix Audio Tracks

```python
video = ffmpeg.input(str(video_path))
audio = ffmpeg.input(str(audio_path))
ffmpeg.output(
    video.video,
    audio.audio,
    str(output_path),
    shortest=None
).run()
```

---

## Video Transformations

### Scale to Resolution

```python
stream = ffmpeg.input(str(video_path))
stream = stream.filter('scale', 1080, 1920)  # 9:16
ffmpeg.output(stream, str(output_path)).run()
```

### Crop Video

```python
stream = stream.filter('crop', out_w=1080, out_h=960, x='(iw-1080)/2', y=0)
```

### Add Black Padding

```python
stream = stream.filter(
    'pad',
    width=1080,
    height=1920,
    x='(ow-iw)/2',
    y=180,
    color='black'
)
```

---

## Probing

### Get Video Info

```python
probe = ffmpeg.probe(str(video_path))
duration = float(probe['format']['duration'])
width = probe['streams'][0]['width']
height = probe['streams'][0]['height']
```

### Get Stream Info

```bash
ffprobe -v quiet -print_format json -show_streams video.mkv
```
