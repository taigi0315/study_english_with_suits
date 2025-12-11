# Debugging Skills

> Techniques for debugging LangFlix issues

---

## Step-by-Step Pipeline Debugging

Isolate which pipeline stage is failing:

```bash
python tests/step_by_step/test_step1_load_and_analyze.py  # LLM analysis
python tests/step_by_step/test_step2_slice_video.py       # Video extraction
python tests/step_by_step/test_step3_add_subtitles.py     # Subtitle overlay
python tests/step_by_step/test_step4_generate_audio.py    # TTS generation
python tests/step_by_step/test_step5_create_slide.py      # Slide creation
python tests/step_by_step/test_step6_combine.py           # Video combination
python tests/step_by_step/test_step7_final.py             # Final assembly
```

---

## Logging

### Enable Verbose Mode

```bash
python -m langflix.main --subtitle "path/to/file.srt" --verbose
```

### Check Log Files

```bash
# Main application log
tail -f langflix.log

# Filter by component
grep "video_editor" langflix.log
grep "ERROR" langflix.log
```

### Save LLM Output for Inspection

```bash
python -m langflix.main --subtitle "path/to/file.srt" --save-llm-output
```

---

## Video/Audio Debugging

### Inspect Video Metadata

```bash
ffprobe -v quiet -print_format json -show_format -show_streams video.mkv
```

### Check Subtitle Timing

```bash
ffprobe -show_entries packet=pts_time video.mkv
```

### Extract Single Frame

```bash
ffmpeg -i video.mkv -ss 00:00:05 -frames:v 1 frame.png
```

### Play Specific Segment

```bash
ffplay -ss 00:00:10 -t 5 video.mkv
```

---

## Common Issues

| Symptom | Check | Solution |
|---------|-------|----------|
| Subtitle misaligned | FFmpeg seeking method | Use output seeking, not input seeking |
| Black frames | Timestamp reset | Add `setpts=PTS-STARTPTS` filter |
| Audio drift | Async audio/video | Re-encode both streams |
| Memory error | Large video chunks | Process in smaller segments |
| API timeout | Network/rate limits | Check quota, add delays |

---

## Database Debugging

```bash
# Check if database is enabled
echo $DATABASE_ENABLED

# View database logs
docker-compose logs postgres

# Connect to database
psql -h localhost -U langflix -d langflix
```

---

## API Debugging

```bash
# Check API health
curl http://localhost:8000/health

# View API docs
open http://localhost:8000/docs

# Test specific endpoint
curl -X POST http://localhost:8000/api/jobs/process-video \
  -F "subtitle_file=@test.srt" \
  -F "language=en"
```
