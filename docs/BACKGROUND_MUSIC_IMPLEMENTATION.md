# Background Music Implementation Guide

**Branch:** `feature/background-music`
**Commit:** 29150f7
**Date:** 2025-01-27

## Overview

This document describes the implementation of the background music system for LangFlix short-form videos. The system automatically selects and applies mood-appropriate instrumental music to educational videos based on scene analysis.

## What Was Implemented

### 1. LLM-Based Music Selection

**File:** `langflix/templates/expression_analysis_prompt.txt`

The LLM prompt now includes:
- **12 Mood-Based Music Categories** with descriptions
- **Selection Criteria** for choosing appropriate music
- **Output Schema** with `background_music_id` and `background_music_reasoning` fields

The LLM analyzes each expression's scene and selects the most appropriate background music from:
1. comedic_funny
2. tense_suspenseful
3. dramatic_serious
4. romantic_tender
5. action_energetic
6. melancholic_sad
7. mysterious_intriguing
8. triumphant_victorious
9. confrontational_angry
10. inspirational_uplifting
11. awkward_uncomfortable
12. reflective_contemplative

### 2. Data Model Updates

**Files:**
- `langflix/core/models.py` (Pydantic models)
- `langflix/db/models.py` (SQLAlchemy models)
- `langflix/db/migrations/versions/0003_add_background_music_fields.py`

**New Fields:**
```python
background_music_id: Optional[str]  # Music category ID
background_music_reasoning: Optional[str]  # LLM's selection explanation
```

**Database Migration:**
```bash
# To apply migration (when database is running):
alembic upgrade head
```

### 3. Configuration System

**File:** `langflix/config/default.yaml`

New `background_music` section:
```yaml
background_music:
  enabled: true  # Toggle background music on/off
  volume: 0.20  # 20% of dialogue volume (0.0-1.0)
  mixing_strategy: "constant"  # or "ducking" (future feature)
  fade_in_duration: 1.0  # seconds
  fade_out_duration: 1.0  # seconds
  music_directory: "assets/background_music"

  library:
    comedic_funny:
      file: "comedic_funny.mp3"
      description: "Light, playful, bouncy music for humorous scenes"
    # ... (11 more categories)
```

### 4. Video Processing Integration

**File:** `langflix/core/video_editor.py`

**New Method:** `_apply_background_music()`
- Takes video path, expression object, and output path
- Reads music file based on expression's `background_music_id`
- Loops music to match video duration
- Applies volume adjustment (default 20%)
- Adds fade in/out effects
- Mixes music with original dialogue audio using FFmpeg

**Integration Point:** `create_short_form_from_long_form()`
- Step 7 now applies background music before final output
- Graceful fallback if music is disabled or files are missing

**FFmpeg Audio Processing:**
```python
# 1. Loop music to match video duration
music_input = ffmpeg.input(music_path, stream_loop=-1, t=video_duration)

# 2. Apply volume and fades
music_audio = music_input.audio.filter('volume', 0.20)
music_audio = music_audio.filter('afade', type='in', duration=1.0)
music_audio = music_audio.filter('afade', type='out', start_time=fade_start)

# 3. Mix with original dialogue
mixed_audio = ffmpeg.filter([video_audio, music_audio], 'amix', inputs=2)
```

### 5. Assets Directory Structure

**Directory:** `assets/background_music/`

Created with:
- `README.md` - Comprehensive guide for music generation and usage
- `.gitkeep` - Ensures directory is tracked in git
- Exception in `.gitignore` to allow structure files but not music files

## How It Works

### Workflow

1. **Expression Analysis**
   - LLM receives subtitle chunks with music library information
   - For each expression, LLM analyzes scene mood/tone
   - LLM selects appropriate `background_music_id` from 12 categories
   - LLM provides reasoning for selection

2. **Video Generation**
   - Short-form video created with all visual elements
   - Background music applied as final step (Step 7)
   - Music file loaded from `assets/background_music/{music_id}.mp3`
   - Music looped to match video duration (~60s source → any duration)

3. **Audio Mixing**
   - Original dialogue/audio: 100% volume
   - Background music: 20% volume (configurable)
   - Fade in: 1 second at start
   - Fade out: 1 second at end
   - Mixed using FFmpeg amix filter

### Fallback Behavior

The system gracefully handles missing music files:
- If `background_music.enabled: false` → Skip music
- If `background_music_id` not provided → Skip music
- If music file not found → Skip music, log warning
- If FFmpeg error occurs → Copy video without music, log error

All fallback scenarios produce a working video without background music.

## Configuration Options

### Volume Control
```yaml
background_music:
  volume: 0.20  # 20% of dialogue volume
```
- Range: 0.0 (silent) to 1.0 (full volume)
- Recommended: 0.15-0.25 for subtle background
- Default: 0.20 (20%)

### Fade Durations
```yaml
background_music:
  fade_in_duration: 1.0
  fade_out_duration: 1.0
```
- Both in seconds
- Recommended: 0.5-2.0 seconds
- Set to 0 to disable fades

### Enable/Disable
```yaml
background_music:
  enabled: true  # Set to false to disable globally
```

### Custom Music Directory
```yaml
background_music:
  music_directory: "path/to/music"  # Custom path
```

## Adding Music Files

### Requirements

Each music file should be:
- **Duration:** ~60 seconds (will loop automatically)
- **Format:** MP3 (recommended) or WAV
- **Seamless Loop:** No noticeable gap when looping
- **Instrumental Only:** No vocals or lyrics
- **Quality:** 256kbps or higher for MP3
- **Volume:** Natural/original volume (will be adjusted by config)

### File Naming

Files must match exact names from config:
```
assets/background_music/
├── comedic_funny.mp3
├── tense_suspenseful.mp3
├── dramatic_serious.mp3
├── romantic_tender.mp3
├── action_energetic.mp3
├── melancholic_sad.mp3
├── mysterious_intriguing.mp3
├── triumphant_victorious.mp3
├── confrontational_angry.mp3
├── inspirational_uplifting.mp3
├── awkward_uncomfortable.mp3
└── reflective_contemplative.mp3
```

### Music Generation

Use AI music generation tools with prompts from `docs/Background music.md`:

**Option 1: Suno AI** (https://suno.ai)
- Enter prompts directly
- Request instrumental version
- Export as MP3

**Option 2: MusicGen** (Facebook/Meta)
- Use detailed prompts
- Control tempo and style
- Generate locally

**Option 3: AIVA** (https://aiva.ai)
- AI music composition
- Download high-quality files
- Commercial license options

**Example Prompt (Comedic/Funny):**
```
Create a light, playful instrumental track with upbeat tempo (120-140 BPM).
Use pizzicato strings, xylophone, ukulele, or quirky synth sounds.
Include bouncy rhythms and whimsical melodies that evoke sitcom or comedy sketches.
Add occasional comedic accents (boings, whistles).
Duration: 60 seconds, seamless loop.
```

See `docs/Background music.md` for all 12 category prompts.

## Testing

### Manual Testing

1. **Generate or place music file:**
   ```bash
   cp your_music.mp3 assets/background_music/comedic_funny.mp3
   ```

2. **Ensure config is enabled:**
   ```yaml
   background_music:
     enabled: true
   ```

3. **Run video generation:**
   ```bash
   python -m langflix.main --subtitle "path/to/file.srt" --video-dir "path/to/videos"
   ```

4. **Check logs for:**
   ```
   INFO: Applying background music: comedic_funny (assets/background_music/comedic_funny.mp3)
   INFO: ✅ Background music applied successfully
   ```

5. **Verify video:**
   - Play short-form video
   - Background music should be audible but subtle
   - Music should fade in at start, fade out at end
   - Dialogue should be clear and prominent

### Validation Checks

**Music File Exists:**
```bash
ls -la assets/background_music/*.mp3
```

**Config Syntax:**
```bash
python -c "from langflix import settings; print(settings.config.get('background_music'))"
```

**Database Migration (if using DB):**
```bash
alembic current  # Check current migration
alembic upgrade head  # Apply if needed
```

## Troubleshooting

### Music Not Playing

**Check 1: Config Enabled**
```yaml
background_music:
  enabled: true  # Must be true
```

**Check 2: Music File Exists**
```bash
ls assets/background_music/comedic_funny.mp3
```

**Check 3: LLM Provided Music ID**
- Check generated expression JSON for `background_music_id` field
- Should be one of the 12 valid category IDs

**Check 4: Logs**
```bash
grep "background music" langflix.log
```

### Music Too Loud/Quiet

Adjust volume in config:
```yaml
background_music:
  volume: 0.15  # Lower (15%)
  # or
  volume: 0.30  # Higher (30%)
```

### Music Doesn't Loop Smoothly

Issue: Source music file has gap/silence at start/end

Solution:
- Use music generation tool with "seamless loop" option
- Edit audio file to remove leading/trailing silence
- Ensure music starts and ends at same musical point

### FFmpeg Error

Check FFmpeg version supports required filters:
```bash
ffmpeg -filters | grep amix
ffmpeg -filters | grep afade
```

Required filters: `amix`, `afade`, `volume`

## Architecture Notes

### Why Volume at 20%?

Based on best practices for educational content:
- Dialogue must be clearly audible (primary content)
- Music enhances mood without distraction
- 15-25% is recommended range for background music
- User can adjust based on preference

### Why 60-Second Music?

- Short enough for quick generation
- Long enough to avoid repetitive loops
- Easy to create seamless loops at this length
- Efficiently loops for any video duration (30s to 3min)

### Why MP3 Format?

- Widely supported
- Good compression (smaller files)
- Acceptable quality at 256kbps
- Easy to generate with AI tools

WAV is also supported for higher quality.

## Future Enhancements

### Potential Additions

1. **Ducking Strategy**
   - Automatically reduce music volume during dialogue
   - Restore music volume during pauses
   - Config: `mixing_strategy: "ducking"`

2. **Music Intensity Levels**
   - Same mood, different intensity levels
   - Example: `tense_suspenseful_light`, `tense_suspenseful_heavy`
   - More granular mood control

3. **Custom Music Upload via API**
   - Allow users to upload custom music files
   - Web UI for music library management
   - Preview before applying

4. **Music Sync to Transitions**
   - Align music beats with visual transitions
   - More polished, professional feel

5. **A/B Testing**
   - Generate same video with different music
   - Compare engagement metrics
   - Optimize music selection

## References

- **Music Prompts:** `docs/Background music.md`
- **Configuration:** `langflix/config/default.yaml`
- **Implementation:** `langflix/core/video_editor.py:959-1078`
- **Assets Guide:** `assets/background_music/README.md`

## Summary

The background music system is fully implemented and ready for use. The main requirement now is to **generate or obtain the 12 music files** and place them in `assets/background_music/` directory.

Once music files are in place, the system will:
1. ✅ Automatically select appropriate music via LLM
2. ✅ Loop music to match video duration
3. ✅ Mix at appropriate volume (20%)
4. ✅ Add smooth fade in/out transitions
5. ✅ Create engaging educational videos

The implementation is backward-compatible (works without music files) and can be toggled via configuration.
