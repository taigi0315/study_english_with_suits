# LangFlix Troubleshooting Guide

**Version:** 1.0  
**Last Updated:** October 19, 2025

This guide helps you diagnose and fix common issues when using LangFlix.

---

## Table of Contents

1. [Installation Issues](#installation-issues)
2. [API and LLM Issues](#api-and-llm-issues)
3. [TTS (Text-to-Speech) Issues](#tts-text-to-speech-issues)
4. [Video Processing Issues](#video-processing-issues)
5. [Subtitle Processing Issues](#subtitle-processing-issues)
6. [Performance and Resource Issues](#performance-and-resource-issues)
7. [Output and Quality Issues](#output-and-quality-issues)
8. [Configuration Issues](#configuration-issues)
9. [Debugging Tips](#debugging-tips)
10. [Error Messages Reference](#error-messages-reference)
11. [FAQ](#faq)

---

## Installation Issues

### Problem: "ModuleNotFoundError: No module named 'langflix'"

**Symptoms:**
```
ModuleNotFoundError: No module named 'langflix'
```

**Solutions:**
1. Ensure virtual environment is activated:
   ```bash
   source venv/bin/activate  # macOS/Linux
   venv\Scripts\activate     # Windows
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run from project root directory:
   ```bash
   cd /path/to/study_english_with_sutis
   python -m langflix.main --subtitle "file.srt"
   ```

---

### Problem: "ffmpeg: command not found"

**Symptoms:**
```
FileNotFoundError: [Errno 2] No such file or directory: 'ffmpeg'
```

**Solutions:**

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**Windows:**
```bash
# Using Chocolatey
choco install ffmpeg

# Or download from: https://ffmpeg.org/download.html
# Add to PATH manually
```

**Verify installation:**
```bash
ffmpeg -version
```

---

### Problem: "GEMINI_API_KEY not found"

**Symptoms:**
```
Error: GEMINI_API_KEY environment variable not set
```

**Solutions:**

1. Create `.env` file:
   ```bash
   cp env.example .env
   ```

2. Edit `.env` and add your API key:
   ```
   GEMINI_API_KEY=your_actual_api_key_here
   ```

3. Get API key from:
   - https://aistudio.google.com/
   - Sign in with Google account
   - Generate new API key

4. Verify `.env` is in project root directory

---

## API and LLM Issues

### Problem: API Timeout (504 Gateway Timeout)

**Symptoms:**
```
Error: 504 Gateway Timeout
Gemini API request timed out
```

**Causes:**
- Input chunk too large
- Network connectivity issues
- API server overload

**Solutions:**

1. **Reduce chunk size in `config.yaml`:**
   ```yaml
   llm:
     max_input_length: 1680  # Try lower values: 1200, 800
   ```

2. **Enable retry logic (should be automatic):**
   ```yaml
   llm:
     max_retries: 3
     retry_backoff_seconds: 2
   ```

3. **Test with smaller input:**
   ```bash
   python -m langflix.main \
     --subtitle "file.srt" \
     --test-mode \
     --max-expressions 1
   ```

4. **Check network connectivity:**
   ```bash
   ping google.com
   curl https://generativelanguage.googleapis.com
   ```

---

### Problem: "MAX_TOKENS" Finish Reason

**Symptoms:**
```
Warning: LLM response ended with MAX_TOKENS
Response may be incomplete
```

**Causes:**
- Output exceeds token limit
- Too many expressions requested
- Complex prompt requires more tokens

**Solutions:**

1. **Reduce expressions per chunk:**
   ```yaml
   processing:
     max_expressions_per_chunk: 2  # Try 1 or 2
   ```

2. **Simplify prompt (edit `langflix/templates/expression_analysis_prompt.txt`)**

3. **Process fewer subtitles per chunk:**
   ```yaml
   llm:
     max_input_length: 1200  # Reduce from 1680
   ```

---

### Problem: Empty or Invalid JSON Response

**Symptoms:**
```
Error: Failed to parse JSON from LLM response
JSONDecodeError: Expecting value
```

**Causes:**
- API returned non-JSON text
- Response was cut off
- Model hallucination

**Solutions:**

1. **Save LLM output for inspection:**
   ```bash
   python -m langflix.main \
     --subtitle "file.srt" \
     --save-llm-output
   ```
   Check `output/llm_output_*.txt` for actual response

2. **Retry with different parameters:**
   ```yaml
   llm:
     temperature: 0.1  # Lower temperature = more consistent
     top_p: 0.8
     top_k: 40
   ```

3. **Use test mode to isolate issue:**
   ```bash
   python -m langflix.main \
     --subtitle "file.srt" \
     --test-mode \
     --dry-run
   ```

---

### Problem: API Rate Limiting / Quota Exceeded

**Symptoms:**
```
Error: 429 Too Many Requests
Quota exceeded for metric
```

**Solutions:**

1. **Check API quota:**
   - Visit https://console.cloud.google.com/
   - Check Gemini API usage and limits

2. **Add delays between requests:**
   ```yaml
   llm:
     retry_backoff_seconds: 5  # Increase delay
   ```

3. **Process fewer expressions at once:**
   ```bash
   python -m langflix.main \
     --subtitle "file.srt" \
     --max-expressions 3
   ```

4. **Upgrade API plan** if using free tier extensively

---

## TTS (Text-to-Speech) Issues

### Problem: "Google Cloud API key is required"

**Symptoms:**
```
Error: Google Cloud API key is required. Set GOOGLE_API_KEY environment variable
```

**Solutions:**
1. **Add API key to `.env` file:**
   ```bash
   GOOGLE_API_KEY_1=your_google_cloud_api_key_here
   ```

2. **Verify key is loaded:**
   ```bash
   cat .env | grep GOOGLE_API_KEY
   ```

3. **Test API key:**
   ```bash
   python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('API Key:', os.getenv('GOOGLE_API_KEY_1')[:10] + '...' if os.getenv('GOOGLE_API_KEY_1') else 'Not found')"
   ```

### Problem: "TTS audio not generating or playing"

**Symptoms:**
- No audio in educational slides
- Silent files generated
- Audio files created but empty/not playing

**Solutions:**
1. **Check TTS configuration in `default.yaml`:**
   ```yaml
   tts:
     enabled: true
     provider: "google"
     google:
       language_code: "en-US"
       response_format: "mp3"
   ```

2. **Verify API key format:**
   - Google Cloud API key should start with `AIza`
   - No quotes or spaces around the key in `.env`

3. **Test TTS directly:**
   ```bash
   python tests/test_tts_integration.py
   ```

4. **Check logs for TTS errors:**
   ```bash
   python -m langflix.main --verbose --test-mode
   ```

### Problem: "ModuleNotFoundError: No module named 'google.cloud'"

**Symptoms:**
```
ModuleNotFoundError: No module named 'google.cloud'
```

**Solutions:**
```bash
pip install google-cloud-texttospeech>=2.16.0
```

### Problem: TTS audio quality issues

**Symptoms:**
- Audio too fast/slow
- Unclear pronunciation
- Wrong voice used

**Solutions:**
1. **Adjust speaking rate in config:**
   ```yaml
   tts:
     google:
       speaking_rate: 0.75  # 75% speed (slower)
   ```

2. **Change voice:**
   ```yaml
   tts:
     google:
       voice_name: "en-US-Wavenet-A"  # Try different voices
       alternate_voices: ["en-US-Wavenet-A", "en-US-Wavenet-D"]
   ```

3. **Check text sanitization:**
   - Expression text should be clean English
   - No special characters or symbols

---

## Video Processing Issues

### Problem: "Video file not found"

**Symptoms:**
```
Error: Could not find video file for subtitle
Searched: [list of paths]
```

**Solutions:**

1. **Ensure video and subtitle have matching names:**
   ```
   ✓ Suits.S01E01.720p.HDTV.x264.mkv
   ✓ Suits.S01E01.720p.HDTV.x264.srt
   
   ✗ Suits_S01E01.mkv
   ✗ Suits.S01E01.srt  (different format in name)
   ```

2. **Specify video directory explicitly:**
   ```bash
   python -m langflix.main \
     --subtitle "path/to/subtitle.srt" \
     --video-dir "path/to/videos"
   ```

3. **Check file permissions:**
   ```bash
   ls -la path/to/video/file.mkv
   chmod 644 path/to/video/file.mkv  # If needed
   ```

---

### Problem: FFmpeg encoding errors

**Symptoms:**
```
Error: ffmpeg returned non-zero exit code
Error processing video: codec not supported
```

**Solutions:**

1. **Check video codec compatibility:**
   ```bash
   ffmpeg -i input_video.mkv
   # Look for video codec (h264, hevc, etc.)
   ```

2. **Re-encode problematic video:**
   ```bash
   ffmpeg -i problematic.mkv -c:v libx264 -c:a aac fixed.mkv
   ```

3. **Update ffmpeg to latest version:**
   ```bash
   # macOS
   brew upgrade ffmpeg
   
   # Ubuntu
   sudo apt update && sudo apt upgrade ffmpeg
   ```

4. **Check video file integrity:**
   ```bash
   ffmpeg -v error -i video.mkv -f null -
   ```

---

### Problem: Video/Audio sync issues

**Symptoms:**
- Audio doesn't match video
- Subtitles appear at wrong time
- Expression timing is off

**Solutions:**

1. **Verify subtitle timing:**
   - Open subtitle file in text editor
   - Check timestamps match video playback

2. **Re-extract with precise timing:**
   ```yaml
   video:
     frame_rate: 23.976  # Match source video exactly
   ```

3. **Check for variable frame rate (VFR):**
   ```bash
   ffmpeg -i video.mkv
   # Look for "Variable frame rate" warning
   
   # Convert VFR to CFR if needed:
   ffmpeg -i input.mkv -vsync cfr -r 23.976 output.mkv
   ```

---

### Problem: "Out of memory" during video processing

**Symptoms:**
```
MemoryError: Unable to allocate memory
Killed (signal 9)
```

**Solutions:**

1. **Process fewer expressions at once:**
   ```bash
   python -m langflix.main \
     --subtitle "file.srt" \
     --max-expressions 3
   ```

2. **Lower video resolution:**
   ```yaml
   video:
     resolution: "1280x720"  # Instead of 1920x1080
     crf: 25  # Higher CRF = smaller files
   ```

3. **Close other applications** before processing

4. **Check available memory:**
   ```bash
   # macOS/Linux
   free -h
   
   # macOS
   vm_stat
   ```

5. **Enable swap space** (Linux):
   ```bash
   sudo fallocate -l 4G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   ```

---

## Subtitle Processing Issues

### Problem: "Subtitle encoding error"

**Symptoms:**
```
UnicodeDecodeError: 'utf-8' codec can't decode byte
Invalid subtitle format
```

**Solutions:**

1. **Convert subtitle to UTF-8:**
   ```bash
   iconv -f ISO-8859-1 -t UTF-8 subtitle.srt > subtitle_utf8.srt
   ```

2. **Check subtitle encoding:**
   ```bash
   file -i subtitle.srt
   ```

3. **Use subtitle editor to fix:**
   - Subtitle Edit (Windows)
   - Aegisub (cross-platform)
   - Save as UTF-8 encoding

---

### Problem: "No matching subtitles found for expression"

**Symptoms:**
```
Warning: Could not find subtitle timing for expression
Skipping expression: [expression text]
```

**Solutions:**

1. **Check subtitle file completeness:**
   - Ensure subtitles cover entire video duration
   - No large gaps in timing

2. **Verify expression text matches subtitle:**
   - LLM might have modified expression text
   - Check with `--save-llm-output`

3. **Adjust matching tolerance** (code modification needed):
   ```python
   # In subtitle_processor.py
   # Increase fuzzy matching threshold
   ```

---

### Problem: "Translation missing" in output videos

**Symptoms:**
- Educational slides show "[translation missing]"
- Dual-language subtitles incomplete

**Causes:**
- LLM didn't provide translation for all dialogues
- Dialogue/translation array mismatch

**Solutions:**

1. **System validates this automatically** - expressions with mismatched translations are filtered out

2. **Check LLM output:**
   ```bash
   python -m langflix.main \
     --subtitle "file.srt" \
     --save-llm-output
   ```
   Inspect `llm_output_*.txt` for dialogue/translation counts

3. **Adjust prompt if needed** (edit `langflix/templates/expression_analysis_prompt.txt`)

---

### Problem: Subtitles not appearing in some context videos

**Symptoms:**
- Some context videos show no subtitles while others display correctly
- Subtitle files exist in `translations/{lang}/subtitles/` directory
- Error logs show "Could not find subtitle file for expression"

**Causes:**
- Subtitle file naming mismatch due to filename truncation
- Expression text is longer than filename allows (e.g., `get_to_someone_through_someone_else` becomes `expression_01_get_to_someone_through_someone.srt`)

**Solutions:**

1. **System handles this automatically** - LangFlix uses smart partial matching to find subtitle files even when names are truncated

2. **If issues persist, check subtitle file matching:**
   ```bash
   # Check available subtitle files
   ls -la output/Series/Episode/translations/{lang}/subtitles/
   
   # Verify file naming pattern matches expression
   # Pattern: expression_XX_{expression_text}.srt
   ```

3. **For debugging, enable verbose logging:**
   Look for these log messages:
   ```
   INFO | Looking for subtitle files in: {directory}
   INFO | Available subtitle files: [...]
   INFO | Found potential match via partial matching: {file_path}
   ```

**Technical Details:**
The system uses multiple matching strategies:
- Exact match with expression text
- Partial matching for truncated filenames  
- Pattern matching with indexed prefixes (expression_01_, expression_02_, etc.)

---

## Performance and Resource Issues

### Problem: Processing is very slow

**Symptoms:**
- Takes hours to process one episode
- CPU usage consistently high

**Solutions:**

1. **Use test mode first:**
   ```bash
   python -m langflix.main \
     --subtitle "file.srt" \
     --test-mode \
     --max-expressions 2
   ```

2. **Optimize video encoding:**
   ```yaml
   video:
     preset: "ultrafast"  # Faster encoding, larger files
     # Or: "fast", "medium", "slow"
   ```

3. **Reduce video quality:**
   ```yaml
   video:
     crf: 28  # Higher = faster encoding (18-28)
     resolution: "1280x720"
   ```

4. **Process in batches:**
   - Process 5-10 expressions at a time
   - Prevents memory buildup

---

### Problem: Disk space running out

**Symptoms:**
```
OSError: [Errno 28] No space left on device
```

**Solutions:**

1. **Check available space:**
   ```bash
   df -h
   ```

2. **Clean up temporary files:**
   ```bash
   # Remove old outputs
   rm -rf output/old_series/
   
   # Clear test outputs
   rm -rf test_output/
   ```

3. **Adjust video compression:**
   ```yaml
   video:
     crf: 25  # Higher = smaller files
   ```

4. **Process one episode at a time** and archive completed videos

---

## Output and Quality Issues

### Problem: Expression quality is poor

**Symptoms:**
- Expressions are too basic/advanced
- Not practical or useful
- Too many boring dialogues

**Solutions:**

1. **Adjust language level:**
   ```bash
   # For more advanced expressions
   python -m langflix.main \
     --subtitle "file.srt" \
     --language-level advanced
   ```

2. **Modify expression limits:**
   ```yaml
   processing:
     min_expressions_per_chunk: 2
     max_expressions_per_chunk: 3  # Force more selective
   ```

3. **Customize prompt template:**
   - Edit `langflix/templates/expression_analysis_prompt.txt`
   - Adjust selection criteria
   - Add specific requirements

---

### Problem: Educational slides text is cut off

**Symptoms:**
- Long expressions don't fit on slide
- Text truncated mid-word

**Solutions:**

1. **Adjust font sizes in `config.yaml`:**
   ```yaml
   font:
     sizes:
       expression: 42  # Reduce from 48
       translation: 36  # Reduce from 40
   ```

2. **Text length limits are configured** in `video_editor.py`:
   - Expression: 200 characters max
   - Translation: 200 characters max
   - Similar: 100 characters max

3. **Use shorter expressions** by adjusting prompt

---

### Problem: Audio quality is poor

**Symptoms:**
- Crackling or distortion
- Volume too low/high
- Audio out of sync

**Solutions:**

1. **Check source video audio:**
   ```bash
   ffmpeg -i video.mkv
   # Check audio codec and bitrate
   ```

2. **Audio settings in `config.yaml`:**
   ```yaml
   audio:
     codec: "aac"
     bitrate: "192k"
     sample_rate: 48000
   ```

3. **Re-extract with audio normalization:**
   - System automatically normalizes audio
   - Check ffmpeg logs for errors

---

## Configuration Issues

### Problem: Configuration file not loaded

**Symptoms:**
```
Warning: Could not load config.yaml
Using default settings
```

**Solutions:**

1. **Ensure `config.yaml` exists in project root:**
   ```bash
   ls -la config.yaml
   ```

2. **Copy from example:**
   ```bash
   cp config.example.yaml config.yaml
   ```

3. **Check YAML syntax:**
   ```bash
   python -c "import yaml; yaml.safe_load(open('config.yaml'))"
   ```

4. **Validate with yamllint:**
   ```bash
   pip install yamllint
   yamllint config.yaml
   ```

---

### Problem: Environment variables not working

**Symptoms:**
- Changes to `.env` file not taking effect
- API key not recognized

**Solutions:**

1. **Ensure `.env` file is in project root:**
   ```bash
   ls -la .env
   ```

2. **No spaces around `=` in `.env`:**
   ```
   # Correct:
   GEMINI_API_KEY=abc123
   
   # Wrong:
   GEMINI_API_KEY = abc123
   ```

3. **Restart terminal/shell** after editing `.env`

4. **Check if variable is set:**
   ```bash
   echo $GEMINI_API_KEY
   ```

---

## Debugging Tips

### Enable Verbose Logging

```bash
python -m langflix.main \
  --subtitle "file.srt" \
  --verbose
```

This provides:
- Detailed function call traces
- Parameter values
- Timing information
- Error context

### Check Log Files

```bash
# View main log
tail -f langflix.log

# Search for errors
grep "ERROR" langflix.log
grep "Exception" langflix.log
```

### Use Dry Run Mode

```bash
# Test without video processing
python -m langflix.main \
  --subtitle "file.srt" \
  --dry-run
```

Benefits:
- Much faster
- Tests LLM integration only
- Identifies configuration issues
- No video storage needed

### Save LLM Output

```bash
python -m langflix.main \
  --subtitle "file.srt" \
  --save-llm-output
```

Inspect `output/llm_output_*.txt` to see:
- Exact prompts sent to LLM
- Raw LLM responses
- Expression analysis decisions

### Test Individual Steps

Use step-by-step testing system:

```bash
# Test each stage independently
cd tests/step_by_step

python test_step1_load_and_analyze.py
python test_step2_slice_video.py
python test_step3_add_subtitles.py
python test_step4_extract_audio.py
python test_step5_create_slide.py
```

See `tests/step_by_step/README.md` for details.

### Check Video File Integrity

```bash
# Check for errors
ffmpeg -v error -i video.mkv -f null -

# Get detailed info
ffprobe -v quiet -print_format json -show_format -show_streams video.mkv
```

### Verify Python Environment

```bash
# Check Python version
python --version  # Should be 3.9+

# Check installed packages
pip list | grep -E "(pysrt|ffmpeg|openai|pydantic)"

# Verify langflix package
python -c "import langflix; print(langflix.__file__)"
```

---

## Error Messages Reference

### Common Error Patterns

| Error Message | Likely Cause | Solution Section |
|--------------|--------------|------------------|
| `ModuleNotFoundError` | Missing dependencies | [Installation Issues](#installation-issues) |
| `GEMINI_API_KEY not found` | API key not set | [Installation Issues](#installation-issues) |
| `504 Gateway Timeout` | API timeout | [API and LLM Issues](#api-and-llm-issues) |
| `MAX_TOKENS` | Response too long | [API and LLM Issues](#api-and-llm-issues) |
| `Video file not found` | File mapping issue | [Video Processing Issues](#video-processing-issues) |
| `ffmpeg returned non-zero` | Video encoding error | [Video Processing Issues](#video-processing-issues) |
| `MemoryError` | Out of memory | [Video Processing Issues](#video-processing-issues) |
| `UnicodeDecodeError` | Subtitle encoding | [Subtitle Processing Issues](#subtitle-processing-issues) |
| `No space left on device` | Disk full | [Performance Issues](#performance-and-resource-issues) |
| `JSONDecodeError` | Invalid LLM response | [API and LLM Issues](#api-and-llm-issues) |

---

## FAQ

### Q: How long should processing take?

**A:** Depends on episode length and system:
- **Test mode (2 expressions):** 2-5 minutes
- **Full episode (10-20 expressions):** 20-60 minutes
- **Limiting factor:** Video encoding time

### Q: Can I process multiple episodes in parallel?

**A:** Not recommended:
- High memory usage
- API rate limiting
- File system contention
- Better to process sequentially

### Q: How much does the API cost?

**A:** Gemini API:
- Free tier: Generous limits for personal use
- Check current pricing: https://ai.google.dev/pricing
- LangFlix optimizes chunk sizes to minimize costs

### Q: Can I use a different LLM?

**A:** Currently supports Gemini only, but:
- Architecture allows LLM swapping
- Would require code modification
- See `langflix/expression_analyzer.py`

### Q: How do I improve expression quality?

**A:** 
1. Adjust `language_level` parameter
2. Modify prompt template in `langflix/templates/`
3. Change `min_expressions_per_chunk` and `max_expressions_per_chunk`
4. Use `--save-llm-output` to review decisions

### Q: Can I customize the educational slide design?

**A:** Yes:
- Edit background image: `assets/education_slide_background.png`
- Adjust font sizes in `config.yaml`
- Modify layout in `video_editor.py` (requires code changes)

### Q: Where are temporary files stored?

**A:** 
- Temporary video clips: Cleaned up automatically
- Output videos: `output/[Series]/[Episode]/`
- LLM outputs: `output/llm_output_*.txt` (if enabled)
- Logs: `langflix.log`

### Q: How do I update LangFlix?

**A:**
```bash
git pull origin main
pip install -r requirements.txt --upgrade
```

### Q: Can I process non-English subtitles?

**A:** 
- Currently optimized for English learning
- Source subtitles should be in English
- Target translations can be in multiple languages

---

## Getting Additional Help

If your issue isn't covered here:

1. **Check logs:** `langflix.log` and console output
2. **Enable verbose mode:** `--verbose` flag
3. **Search GitHub Issues:** https://github.com/taigi0315/study_english_with_suits/issues
4. **Create new issue** with:
   - Error message (full stack trace)
   - Command you ran
   - Config file (remove API keys!)
   - Log output
   - System information (OS, Python version)

---

**Need more help?** See [USER_MANUAL.md](USER_MANUAL.md) for detailed usage instructions.

*For Korean version, see [TROUBLESHOOTING_KOR.md](TROUBLESHOOTING_KOR.md)*

