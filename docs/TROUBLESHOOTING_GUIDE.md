# LangFlix Troubleshooting Guide

## Quick Diagnosis

### System Health Check

Run this command to check all components:

```bash
# Comprehensive health check
python -m langflix.diagnostics --full

# Or manually check each component:
python --version                    # Check Python version
ffmpeg -version                     # Check FFmpeg
echo $GEMINI_API_KEY               # Check API key
psql langflix -c "SELECT 1;"       # Check database
curl http://localhost:8000/health  # Check API
```

---

## Common Issues by Category

### Installation & Setup Issues

#### Issue: "ModuleNotFoundError: No module named 'langflix'"

**Symptoms**:
```
ModuleNotFoundError: No module named 'langflix'
```

**Causes**:
- Virtual environment not activated
- Dependencies not installed
- Running from wrong directory

**Solutions**:

1. Activate virtual environment:
```bash
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run from project root:
```bash
cd /path/to/study_english_with_suits
python -m langflix.main --subtitle "file.srt"
```

4. Verify installation:
```bash
python -c "import langflix; print(langflix.__version__)"
```

---

#### Issue: "ffmpeg: command not found"

**Symptoms**:
```
FileNotFoundError: [Errno 2] No such file or directory: 'ffmpeg'
```

**Solutions**:

**macOS**:
```bash
brew install ffmpeg
```

**Ubuntu/Debian**:
```bash
sudo apt update
sudo apt install ffmpeg
```

**Windows**:
```bash
# Using Chocolatey
choco install ffmpeg

# Or download from https://ffmpeg.org/download.html
# Add to PATH
```

**Verify**:
```bash
ffmpeg -version
which ffmpeg  # Linux/macOS
where ffmpeg  # Windows
```

---

#### Issue: "GEMINI_API_KEY not found"

**Symptoms**:
```
Error: GEMINI_API_KEY environment variable not set
KeyError: 'GEMINI_API_KEY'
```

**Solutions**:

1. Create `.env` file:
```bash
cp env.example .env
nano .env
```

2. Add API key:
```bash
GEMINI_API_KEY=your_actual_api_key_here
```

3. Get API key:
- Visit https://aistudio.google.com/
- Sign in with Google account
- Create new API key

4. Verify:
```bash
echo $GEMINI_API_KEY
cat .env | grep GEMINI_API_KEY
```

---

### Processing Issues

#### Issue: API Timeout (504 Gateway Timeout)

**Symptoms**:
```
Error: 504 Gateway Timeout
Gemini API request timed out
TimeoutError: Request exceeded 120 seconds
```

**Causes**:
- Input chunk too large
- Network connectivity issues
- API server overload
- Firewall blocking requests

**Solutions**:

1. Reduce chunk size:
```yaml
# config.yaml
llm:
  max_input_length: 1200  # Reduce from 1680
  chunk_size: 30          # Reduce from 50
  timeout: 180            # Increase timeout
```

2. Check network:
```bash
ping google.com
curl https://generativelanguage.googleapis.com
```

3. Test with smaller input:
```bash
python -m langflix.main \
  --subtitle "file.srt" \
  --test-mode \
  --max-expressions 1
```

4. Check API status:
```bash
curl -I https://generativelanguage.googleapis.com
```

---

#### Issue: "MAX_TOKENS" Finish Reason

**Symptoms**:
```
Warning: LLM response ended with MAX_TOKENS
Response may be incomplete
```

**Causes**:
- Output exceeds token limit (2048 tokens)
- Too many expressions requested
- Complex prompt

**Solutions**:

1. Reduce expressions per chunk:
```yaml
processing:
  max_expressions_per_chunk: 2  # Reduce from 3-4
```

2. Simplify prompt template:
```yaml
llm:
  max_input_length: 1200
```

3. Process fewer subtitles:
```bash
python -m langflix.main \
  --subtitle "file.srt" \
  --max-expressions 5
```

---

#### Issue: Empty or Invalid JSON Response

**Symptoms**:
```
JSONDecodeError: Expecting value
Error: Failed to parse JSON from LLM response
Invalid expression data
```

**Causes**:
- API returned non-JSON text
- Response was cut off
- Model hallucination
- Network corruption

**Solutions**:

1. Save LLM output for inspection:
```bash
python -m langflix.main \
  --subtitle "file.srt" \
  --save-llm-output \
  --verbose
```

2. Check saved output:
```bash
cat output/llm_output_*.txt
```

3. Adjust temperature:
```yaml
llm:
  temperature: 0.1  # Lower = more consistent
  top_p: 0.8
```

4. Retry with test mode:
```bash
python -m langflix.main \
  --subtitle "file.srt" \
  --test-mode \
  --dry-run
```

---

#### Issue: Rate Limiting / Quota Exceeded

**Symptoms**:
```
Error: 429 Too Many Requests
Quota exceeded for metric
ResourceExhausted: Quota exceeded
```

**Solutions**:

1. Check API quota:
- Visit https://console.cloud.google.com/
- Navigate to Gemini API quotas
- Check current usage

2. Add delays:
```yaml
llm:
  retry_backoff_seconds: 5  # Increase from 2
  max_retries: 5
```

3. Process fewer expressions:
```bash
python -m langflix.main \
  --subtitle "file.srt" \
  --max-expressions 3
```

4. Upgrade API plan if needed

---

### Video Processing Issues

#### Issue: "Broken or Missing Fonts in Subtitles"

**Symptoms**:
```
- Spanish or Japanese characters appear as boxes or question marks
- Subtitles display incorrectly for non-Latin scripts
- Font rendering errors in FFmpeg output
```

**Causes**:
- System doesn't have appropriate fonts for the target language
- FFmpeg not finding the correct font files
- Font path configuration issues

**Solutions**:

1. **Check Available Fonts**:
```bash
# macOS
ls /System/Library/Fonts/ | grep -E "(Spanish|Japanese|Chinese)"

# Linux
fc-list | grep -E "(Spanish|Japanese|Chinese)"
```

2. **Install Language-Specific Fonts**:
```bash
# macOS - usually pre-installed
# For additional fonts, install via Font Book or download from Apple

# Linux - install Noto fonts for CJK support
sudo apt install fonts-noto-cjk fonts-noto-cjk-extra
```

3. **Verify Font Configuration**:
```bash
# Check font paths in configuration
python -c "from langflix.core.language_config import LanguageConfig; print(LanguageConfig.get_font_path('ja'))"
```

4. **Manual Font Override** (if needed):
Update `langflix/core/language_config.py` with correct font paths for your system.

#### Issue: "Video file not found"

**Symptoms**:
```
Error: Could not find video file for subtitle
FileNotFoundError: Video file not found at /path/to/video.mkv
```

**Causes**:
- Video and subtitle names don't match
- Video in different directory
- Wrong file extension

**Solutions**:

1. Check file names match exactly:
```bash
ls -la assets/media/

# Must match:
# video.mp4 → video.srt
# NOT: video_1080p.mp4 → video.srt
```

2. Specify video directory:
```bash
python -m langflix.main \
  --subtitle "path/to/subtitle.srt" \
  --video-dir "path/to/videos"
```

3. Check file extensions:
```bash
# Supported: .mp4, .mkv, .avi, .mov
```

---

#### Issue: FFmpeg Encoding Errors

**Symptoms**:
```
Error: ffmpeg returned non-zero exit code
Error processing video: codec not supported
Stream map 'video:0' matches no streams
```

**Solutions**:

1. Check video codec:
```bash
ffmpeg -i input_video.mkv
ffprobe -v error -show_entries stream=codec_name input_video.mkv
```

2. Re-encode if needed:
```bash
ffmpeg -i problematic.mkv -c:v libx264 -c:a aac fixed.mkv
```

3. Update FFmpeg:
```bash
brew upgrade ffmpeg  # macOS
sudo apt upgrade ffmpeg  # Ubuntu
```

4. Test video file:
```bash
ffmpeg -v error -i video.mkv -f null -
```

---

#### Issue: Video/Audio Sync Problems

**Symptoms**:
- Audio doesn't match video
- Subtitles appear at wrong time
- Expression timing is off

**Solutions**:

1. Check frame rate:
```bash
ffprobe -v error -select_streams v:0 \
  -show_entries stream=r_frame_rate \
  input.mkv
```

2. Match in config:
```yaml
video:
  frame_rate: 23.976  # Match source
```

3. Handle Variable Frame Rate (VFR):
```bash
# Convert VFR to CFR
ffmpeg -i input_vfr.mkv -vsync cfr -r 23.976 output_cfr.mkv
```

4. Check subtitle timing:
```bash
# Open subtitle in text editor
nano subtitle.srt
# Verify timestamps match video
```

---

#### Issue: Out of Memory

**Symptoms**:
```
MemoryError: Unable to allocate memory
Killed (signal 9)
OSError: [Errno 12] Cannot allocate memory
```

**Solutions**:

1. Process fewer expressions:
```bash
python -m langflix.main \
  --subtitle "file.srt" \
  --max-expressions 3
```

2. Lower video resolution:
```yaml
video:
  resolution: "1280x720"  # From 1920x1080
  crf: 25  # Higher = smaller files
```

3. Close other applications

4. Check available memory:
```bash
free -h  # Linux
vm_stat  # macOS
```

5. Add swap space (Linux):
```bash
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

---

### TTS Issues

#### Issue: No TTS Audio Generated

**Symptoms**:
- Educational slides have no audio
- Silent fallback audio used
- Missing audio files

**Causes**:
- Missing API key
- TTS disabled in config
- API quota exceeded
- Network issues

**Solutions**:

1. Check API key:
```bash
echo $GEMINI_API_KEY
cat .env | grep GEMINI_API_KEY
```

2. Enable TTS:
```yaml
tts:
  enabled: true
  provider: "google"
```

3. Check logs:
```bash
tail -f langflix.log | grep "TTS"
```

4. Test TTS directly:
```python
from langflix.tts import TTSGenerator
tts = TTSGenerator()
audio = tts.generate("test text")
print(f"Audio generated: {len(audio)} bytes")
```

---

#### Issue: Poor TTS Quality

**Symptoms**:
- Robotic voice
- Unnatural pronunciation
- Wrong emphasis

**Solutions**:

1. Adjust SSML settings:
```yaml
tts:
  google:
    speaking_rate: "slow"      # x-slow, slow, medium, fast
    pitch: "-4st"              # Lower pitch
```

2. Try different voices:
```yaml
tts:
  google:
    alternate_voices:
      - "Despina"
      - "Puck"
      - "Kore"
```

3. Use full dialogue context (already implemented in Phase 2)

---

### Subtitle Processing Issues

#### Issue: Subtitle Encoding Errors

**Symptoms**:
```
UnicodeDecodeError: 'utf-8' codec can't decode byte
SubtitleEncodingError: Failed to decode subtitle file
```

**Phase 2 Solution**:
The system now **automatically handles** most encoding issues!

**Check automatic detection**:
```bash
# Look for encoding detection in logs
tail -f langflix.log | grep "encoding"
# Should see: "Detected encoding: cp949 (confidence: 0.95)"
```

**Manual fix (if auto-detection fails)**:
```bash
# Convert encoding
iconv -f ISO-8859-1 -t UTF-8 subtitle.srt > subtitle_utf8.srt

# Use converted file
python -m langflix.main --subtitle subtitle_utf8.srt
```

---

#### Issue: Too Many Duplicate Expressions

**Symptoms**:
- Similar expressions appearing multiple times
- Redundant content

**Phase 2 Solution**:
Adjust fuzzy matching threshold:

```yaml
llm:
  ranking:
    fuzzy_match_threshold: 90  # More strict (default: 85)
```

**Check duplicate removal**:
```bash
# Look in logs
tail -f langflix.log | grep "duplicate"
# Should see: "Removed 3 duplicate expressions"
```

---

#### Issue: Expression Quality Problems

**Symptoms**:
- Expressions too easy/hard
- Not relevant for learning level

**Phase 2 Solution**:
Adjust ranking weights:

```yaml
llm:
  ranking:
    # For advanced learners
    difficulty_weight: 0.6      # Increase difficulty weight
    frequency_weight: 0.2
    educational_value_weight: 0.2
    
    # For beginners
    difficulty_weight: 0.2      # Decrease difficulty weight
    frequency_weight: 0.5       # Increase frequency weight
    educational_value_weight: 0.3
```

---

### WhisperX Issues

#### Issue: WhisperX Model Loading Failed

**Symptoms**:
```
Error loading WhisperX model
ModelNotFoundError: Model 'base' not found
CUDA out of memory
```

**Solutions**:

1. Use CPU if GPU unavailable:
```yaml
whisper:
  device: "cpu"
  compute_type: "float32"
```

2. Use smaller model:
```yaml
whisper:
  model_size: "tiny"  # Smallest model
```

3. Check CUDA availability:
```python
import torch
print(torch.cuda.is_available())
```

4. Clear model cache:
```bash
rm -rf cache/whisperx/
```

---

#### Issue: Slow WhisperX Processing

**Symptoms**:
- Processing takes very long
- High CPU usage
- System freezing

**Solutions**:

1. Enable GPU:
```yaml
whisper:
  device: "cuda"
  compute_type: "float16"
```

2. Reduce batch size:
```yaml
whisper:
  batch_size: 8  # Reduce from 16
```

3. Use faster model:
```yaml
whisper:
  model_size: "base"  # Instead of medium/large
```

---

### Short Video Issues

#### Issue: Short Videos Not Created

**Symptoms**:
- No `short_videos/` directory
- Only educational videos created

**Solutions**:

1. Enable short videos:
```yaml
short_video:
  enabled: true
```

2. Don't use `--no-shorts` flag:
```bash
# Remove --no-shorts
python -m langflix.main --subtitle "file.srt"
```

3. Check logs:
```bash
tail -f langflix.log | grep "short"
```

---

#### Issue: Wrong Aspect Ratio

**Symptoms**:
- Short videos not 9:16 format
- Incorrect resolution

**Solutions**:

1. Verify resolution:
```yaml
short_video:
  resolution: "1080x1920"  # 9:16 vertical
```

2. Check output:
```bash
ffprobe output/short_videos/batch_01.mkv
# Should show: 1080x1920
```

---

### YouTube Integration Issues

#### Issue: OAuth Authentication Failed

**Symptoms**:
```
Error: Authentication failed
OAuth2Error: invalid_grant
CredentialsError: Unable to authenticate
```

**Solutions**:

1. Check credentials file:
```bash
ls -la youtube_credentials.json
cat youtube_credentials.json | jq
```

2. Verify redirect URIs in Google Cloud Console

3. Delete and recreate tokens:
```bash
rm youtube_token.json
curl -X POST http://localhost:8000/api/youtube/login
```

4. Check test user permissions (if in testing)

---

#### Issue: Quota Exceeded

**Symptoms**:
```
Error: No remaining quota for final videos
Daily limit reached: 2/2
```

**Solutions**:

1. Check quota status:
```bash
curl "http://localhost:8000/api/quota/status"
```

2. Wait for quota reset (midnight UTC)

3. Adjust daily limits if needed:
```yaml
youtube:
  daily_limits:
    final: 3  # Increase if allowed
    short: 7
```

4. Use scheduling to spread uploads:
```bash
curl "http://localhost:8000/api/schedule/next-available?video_type=final"
```

---

### Database Issues

#### Issue: Database Connection Failed

**Symptoms**:
```
sqlalchemy.exc.OperationalError: could not connect to server
Connection refused
database "langflix" does not exist
```

**Solutions**:

1. Check PostgreSQL is running:
```bash
pg_isready
systemctl status postgresql  # Linux
brew services list | grep postgresql  # macOS
```

2. Start PostgreSQL:
```bash
systemctl start postgresql  # Linux
brew services start postgresql  # macOS
```

3. Create database:
```bash
createdb langflix
```

4. Check connection string:
```bash
echo $DATABASE_URL
psql $DATABASE_URL -c "SELECT 1;"
```

5. Run migrations:
```bash
alembic upgrade head
```

---

#### Issue: Migration Errors

**Symptoms**:
```
alembic.util.exc.CommandError: Can't locate revision
sqlalchemy.exc.IntegrityError: duplicate key value
```

**Solutions**:

1. Check current version:
```bash
alembic current
```

2. Reset migrations (careful!):
```bash
alembic downgrade base
alembic upgrade head
```

3. Fix conflicts:
```bash
alembic stamp head
alembic revision --autogenerate -m "fix conflicts"
alembic upgrade head
```

---

### Storage Issues

#### Issue: Storage Backend Error

**Symptoms**:
```
StorageError: Failed to save file
google.auth.exceptions.DefaultCredentialsError
PermissionError: Access denied
```

**Solutions**:

1. For Local Storage:
```bash
# Check permissions
ls -la output/
chmod 755 output/

# Check disk space
df -h
```

2. For GCS:
```bash
# Check credentials
echo $GOOGLE_APPLICATION_CREDENTIALS
cat $GOOGLE_APPLICATION_CREDENTIALS | jq

# Test access
gsutil ls gs://your-bucket/

# Check permissions
gsutil iam get gs://your-bucket/
```

3. Switch to local storage temporarily:
```yaml
storage:
  backend: "local"
```

---

### API Issues

#### Issue: API Won't Start

**Symptoms**:
```
OSError: [Errno 98] Address already in use
Error: Port 8000 is already in use
uvicorn.config.ConfigException
```

**Solutions**:

1. Check port usage:
```bash
lsof -i :8000
netstat -an | grep 8000
```

2. Kill existing process:
```bash
kill $(lsof -t -i :8000)
pkill -f uvicorn
```

3. Use different port:
```bash
uvicorn langflix.api.main:app --port 8001
```

4. Check configuration:
```bash
python -c "import yaml; print(yaml.safe_load(open('config.yaml')))"
```

---

#### Issue: Background Tasks Not Running

**Symptoms**:
- Jobs stuck in PENDING status
- No progress updates
- Files not generated

**Solutions**:

1. Check logs:
```bash
tail -f langflix.log | grep "background"
```

2. Verify task execution:
```bash
curl "http://localhost:8000/api/v1/jobs/{job_id}"
```

3. Restart API:
```bash
systemctl restart langflix-api
```

4. Check system resources:
```bash
free -h
df -h
top
```

---

## Performance Issues

### Issue: Processing Too Slow

**Symptoms**:
- Takes hours to process episode
- CPU usage low
- No progress

**Solutions**:

1. Enable GPU acceleration:
```yaml
video:
  hardware_acceleration: "cuda"
  codec: "h264_nvenc"

whisper:
  device: "cuda"
  compute_type: "float16"
```

2. Use faster presets:
```yaml
video:
  preset: "fast"  # Instead of "slow"
  crf: 23  # Slightly lower quality
```

3. Increase parallel processing:
```yaml
processing:
  max_concurrent_jobs: 8
```

4. Check bottlenecks:
```bash
# CPU usage
top -p $(pgrep -f langflix)

# I/O wait
iostat -x 1

# Network latency (for API calls)
ping google.com
```

---

### Issue: High Memory Usage

**Symptoms**:
- System runs out of RAM
- Swap usage very high
- OOM killer activated

**Solutions**:

1. Reduce batch size:
```yaml
processing:
  max_expressions_per_chunk: 2
  batch_size: 5
```

2. Lower resolution:
```yaml
video:
  resolution: "1280x720"
```

3. Use smaller models:
```yaml
whisper:
  model_size: "tiny"
```

4. Enable memory limits:
```yaml
processing:
  max_memory_mb: 6144  # 6GB limit
```

5. Process sequentially:
```yaml
processing:
  max_concurrent_jobs: 1
```

---

### Issue: Disk Space Running Out

**Symptoms**:
```
OSError: [Errno 28] No space left on device
Error writing file
```

**Solutions**:

1. Check disk usage:
```bash
df -h
du -sh output/
```

2. Clean old outputs:
```bash
find output/ -mtime +30 -delete
rm -rf test_output/
```

3. Increase compression:
```yaml
video:
  crf: 28  # Higher = smaller files
```

4. Enable cleanup:
```yaml
processing:
  cleanup_temp_files: true
```

---

## Known Issues & Limitations

### Current Limitations

1. **Single-instance Processing**
   - No distributed task queue (Celery planned)
   - One video processed at a time

2. **Manual GPU Configuration**
   - No automatic GPU detection
   - Requires manual config changes

3. **Limited Error Recovery**
   - Basic retry logic only
   - Manual intervention needed for some failures

4. **No User Authentication**
   - Planned for Phase 8
   - Single-user system currently

5. **No Rate Limiting**
   - API open to all requests
   - Planned for Phase 8

---

## Debugging Tools

### Enable Debug Logging

```bash
# Environment variable
export LANGFLIX_LOG_LEVEL=DEBUG

# CLI flag
python -m langflix.main --verbose --subtitle "file.srt"

# Configuration
# config.yaml
logging:
  level: DEBUG
```

### Save LLM Output

```bash
python -m langflix.main \
  --subtitle "file.srt" \
  --save-llm-output

# Check output
cat output/llm_output_*.txt
```

### Test Individual Components

```bash
# Test subtitle parsing
python -c "from langflix.subtitle_parser import parse_srt_file; print(parse_srt_file('test.srt'))"

# Test LLM connection
python -c "from langflix.expression_analyzer import ExpressionAnalyzer; print('LLM OK')"

# Test video processing
ffmpeg -i test.mp4 -t 10 test_clip.mp4

# Test database
psql langflix -c "SELECT COUNT(*) FROM jobs;"
```

### Performance Profiling

```bash
# Profile Python code
python -m cProfile -s cumulative -m langflix.main --subtitle "test.srt"

# Monitor system resources
htop
iotop
nvidia-smi  # For GPU
```

### Network Debugging

```bash
# Test API connectivity
curl -v http://localhost:8000/health

# Check Gemini API
curl -v https://generativelanguage.googleapis.com

# Monitor network traffic
tcpdump -i any port 8000
```

---

## Getting Help

### Before Asking for Help

1. **Check logs**:
```bash
tail -100 langflix.log
grep ERROR langflix.log
```

2. **Run diagnostics**:
```bash
python -m langflix.diagnostics --full
```

3. **Test with minimal example**:
```bash
python -m langflix.main \
  --subtitle "test.srt" \
  --test-mode \
  --max-expressions 1
```

4. **Check documentation**:
- User Manual
- API Reference
- Configuration Guide

---

### Reporting Issues

Include the following information:

1. **Environment**:
```bash
python --version
ffmpeg -version
uname -a  # Linux/macOS
```

2. **Configuration** (sanitized):
```bash
cat config.yaml  # Remove API keys
```

3. **Error message** (full):
```bash
tail -100 langflix.log
```

4. **Steps to reproduce**:
```bash
# Exact commands you ran
```

5. **Expected vs actual behavior**

---

### Community Resources

- **GitHub Issues**: https://github.com/taigi0315/study_english_with_suits/issues
- **Documentation**: Full documentation in `docs/`
- **Examples**: Sample configurations in `examples/`

---

## Quick Reference Card

### Emergency Commands

```bash
# Kill stuck process
pkill -f langflix

# Clear cache
rm -rf cache/

# Reset database
alembic downgrade base && alembic upgrade head

# Check system health
python -m langflix.diagnostics

# View recent errors
tail -50 langflix.log | grep ERROR

# Test configuration
python -m langflix.config.validate config.yaml
```

### Common Fix Commands

```bash
# Fix file permissions
chmod -R 755 output/

# Fix encoding issues
iconv -f ISO-8859-1 -t UTF-8 subtitle.srt > subtitle_utf8.srt

# Restart services
systemctl restart postgresql
systemctl restart langflix-api

# Clear stuck jobs
psql langflix -c "UPDATE jobs SET status='FAILED' WHERE status='PROCESSING' AND started_at < NOW() - INTERVAL '1 hour';"
```

---

## Preventive Measures

### Regular Maintenance

```bash
# Weekly tasks
alembic upgrade head  # Update database
find cache/ -mtime +7 -delete  # Clear old cache
vacuumdb langflix  # Optimize database

# Monthly tasks
pg_dump langflix > backup.sql  # Backup database
du -sh output/  # Check disk usage
grep ERROR langflix.log | wc -l  # Count errors
```

### Monitoring Setup

```bash
# Monitor API health
watch -n 30 'curl -s http://localhost:8000/health | jq'

# Monitor disk space
watch -n 300 'df -h'

# Monitor jobs
watch -n 10 'curl -s http://localhost:8000/api/v1/jobs?status=PROCESSING | jq'
```

### Best Practices

1. **Always use test mode first**
2. **Keep configurations in version control**
3. **Regular backups**
4. **Monitor resource usage**
5. **Update dependencies regularly**
6. **Review logs periodically**

---

**For more information, see:**
- System Architecture Overview
- Quick Start Guide
- API & Operations Guide
- Configuration Reference
