# TTS Testing Guide

This guide explains how to test the new Text-to-Speech (TTS) integration in the `feature/text_to_audio` branch.

## Quick Test

### 1. Run the TTS Integration Test

```bash
# Activate virtual environment
source venv/bin/activate

# Run the test (will skip actual API calls by default)
python tests/test_tts_integration.py
```

**Expected Output:**
```
✅ TTS configuration test passed
✅ TTS client creation test passed
✅ Text sanitization test passed
✅ All tests passed!
```

### 2. Test with Actual API Call (Optional)

If you want to test actual TTS generation:

```bash
# Run the test and choose 'y' when prompted
python tests/test_tts_integration.py
# When asked: "Continue? (y/n):" type 'y'
```

This will:
- Make a real API call to LemonFox
- Generate audio for "get screwed"
- Verify the audio file is created
- Clean up the test file

## Full Pipeline Test

To test TTS in the complete video processing pipeline:

```bash
# Run LangFlix with test data
python -m langflix.main \
  --subtitle "assets/subtitles/your_subtitle_file.srt" \
  --video-dir "assets/media" \
  --max-expressions 2 \
  --test-mode
```

**What to Check:**
1. ✅ Educational slide videos have TTS-generated audio (3x repetition)
2. ✅ Context videos still have original audio
3. ✅ No errors in logs about TTS generation
4. ✅ Audio quality is clear and understandable

## Configuration Options

### Change TTS Voice

Edit `langflix/config/default.yaml`:

```yaml
tts:
  lemonfox:
    voice: "bella"  # Try: sarah, adam, or other available voices
```

### Change Audio Format

```yaml
tts:
  lemonfox:
    response_format: "mp3"  # Options: mp3, wav
```

*Note: WAV is recommended for video processing*

### Disable TTS (Fallback to Original Audio)

```yaml
tts:
  enabled: false  # Will use silence as fallback
```

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'inflect'"

**Solution:**
```bash
pip install inflect>=6.0.0
```

### Issue: "ModuleNotFoundError: No module named 'yaml'"

**Solution:**
```bash
pip install PyYAML>=6.0
```

### Issue: "LemonFox API request failed"

**Possible causes:**
1. Invalid API key
2. Network connectivity issues
3. API service down

**Check:**
```python
# Verify API key in config
cat langflix/config/default.yaml | grep api_key
```

### Issue: TTS audio quality is poor

**Try:**
1. Different voice: Change `voice: "bella"` to `voice: "sarah"`
2. Clean text better: Check expression text has no special characters
3. Use WAV format: Change `response_format: "wav"`

## Text Sanitization Examples

The TTS system automatically cleans expression text:

| Original | Sanitized | With Numbers |
|----------|-----------|--------------|
| `I'm gonna get screwed` | `I'm gonna get screwed` | `I'm gonna get screwed` |
| `don't_worry_2_much!` | `don't worry 2 much` | `don't worry two much` |
| `2 cups of coffee` | `2 cups of coffee` | `two cups of coffee` |
| `the 3rd time's a charm` | `the 3rd time's a charm` | `the three-rd time's a charm` |
| `hello@#$%world` | `hello world` | `hello world` |

## Monitoring TTS in Logs

When processing videos, look for these log messages:

**Success:**
```
INFO | Generating TTS audio for expression: 'get screwed'
INFO | Successfully generated TTS audio: /path/to/audio.wav
INFO | TTS audio duration: 1.23s
INFO | Successfully created 3x repeated TTS audio: 3.69s
```

**Fallback (if TTS fails):**
```
ERROR | Error generating TTS audio: <error details>
WARNING | Using 2.00s silence as TTS fallback
```

## Adding a New TTS Provider

To add a new provider (e.g., Google Cloud TTS):

1. **Create provider client:**
   ```python
   # langflix/tts/google_client.py
   from .base import TTSClient
   
   class GoogleTTSClient(TTSClient):
       def generate_speech(self, text, output_path=None):
           # Implementation
           pass
   ```

2. **Update factory:**
   ```python
   # langflix/tts/factory.py
   elif provider == "google":
       return GoogleTTSClient(...)
   ```

3. **Add config:**
   ```yaml
   # langflix/config/default.yaml
   tts:
     provider: "google"
     google:
       credentials_path: "path/to/creds.json"
       voice_name: "en-US-Standard-A"
   ```

## Performance Notes

- **TTS Generation Time**: ~1-3 seconds per expression
- **Audio File Size**: ~50-200 KB per expression (WAV format)
- **API Rate Limits**: LemonFox API has rate limits (check their docs)

## Next Steps

After testing:

1. ✅ Verify TTS audio quality meets expectations
2. ✅ Test with various expression types (short, long, with numbers)
3. ✅ Check final video quality with TTS audio
4. ✅ Consider adding more providers if needed

---

**For issues or questions, check the TTS_IMPLEMENTATION_SUMMARY.md document.**
