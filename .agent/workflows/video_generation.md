# Video Generation Workflow

> End-to-end process for generating educational videos

---

## Prerequisites

- [ ] FFmpeg installed
- [ ] Gemini API key configured in `.env`
- [ ] Virtual environment activated
- [ ] Source video and subtitle files ready

---

## Quick Start

### Development Mode (Recommended)

```bash
# Start full environment
make dev-all

# Access:
# - API: http://localhost:8000/docs
# - UI: http://localhost:5000
```

### CLI Mode

```bash
# Test mode (2 expressions only)
python -m langflix.main \
  --subtitle "assets/media/test/test.srt" \
  --test-mode \
  --max-expressions 2

# Full processing
python -m langflix.main \
  --subtitle "assets/media/Show/Show.S01E01.srt" \
  --language-code ko \
  --verbose
```

---

## Pipeline Stages

```
1. PARSE      → Subtitle file parsed into chunks
2. ANALYZE    → Gemini extracts expressions from chunks
3. EXTRACT    → Context video clips extracted per expression
4. SUBTITLE   → Dual-language subtitles overlaid
5. TTS        → Expression audio generated
6. SLIDE      → Educational slide created
7. COMBINE    → Context + Slide combined
8. SHORT      → 9:16 short-form version generated
```

---

## Output Structure

```
output/
├── {language}/
│   ├── subtitles/          # Subtitle files per expression
│   ├── structured_videos/  # Individual 16:9 videos
│   ├── short_videos/       # Batched 9:16 videos (≤180s)
│   └── combined/           # All structured videos concatenated
```

---

## Debugging

### Step-by-Step Isolation

If generation fails, identify which stage:

```bash
python tests/step_by_step/test_step1_load_and_analyze.py  # LLM
python tests/step_by_step/test_step2_slice_video.py       # Extraction
python tests/step_by_step/test_step3_add_subtitles.py     # Subtitles
python tests/step_by_step/test_step4_generate_audio.py    # TTS
python tests/step_by_step/test_step5_create_slide.py      # Slides
python tests/step_by_step/test_step6_combine.py           # Combine
python tests/step_by_step/test_step7_final.py             # Final
```

### Enable Verbose Logging

```bash
python -m langflix.main --subtitle "file.srt" --verbose --save-llm-output
```

### Check Logs

```bash
tail -f langflix.log
grep "ERROR" langflix.log
```

---

## Quality Verification

### After Generation

- [ ] Watch full video
- [ ] Check subtitle timing and accuracy
- [ ] Verify audio is clear and synced
- [ ] Confirm video quality (no artifacts)
- [ ] Test on target platform (TikTok, YouTube, etc.)

### Common Issues

| Issue | Check | Fix |
|-------|-------|-----|
| Black frames | Timestamp reset | Add setpts filter |
| Subtitle offset | Seeking method | Use output seeking |
| Audio desync | Re-encoding | Re-encode both streams |
| Low quality | CRF/preset | Use CRF 18, slow preset |

---

## Post-Generation

### YouTube Upload (Optional)

```bash
# Via Web UI
open http://localhost:5000

# Or via API
curl -X POST http://localhost:8000/api/youtube/upload \
  -F "video_file=@output/short_videos/batch_1.mkv" \
  -F "title=Learning English"
```
