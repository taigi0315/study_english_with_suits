# Background Music Library

This directory contains background music files used for short-form educational videos.

## Music Categories

The system supports 12 mood-based background music categories:

1. **comedic_funny.mp3** - Light, playful music for humorous scenes
2. **tense_suspenseful.mp3** - Dark, atmospheric music with building tension
3. **dramatic_serious.mp3** - Powerful orchestral music with emotional weight
4. **romantic_tender.mp3** - Soft, warm music with gentle melodies
5. **action_energetic.mp3** - Fast-paced music with powerful beats
6. **melancholic_sad.mp3** - Slow, somber music with emotional depth
7. **mysterious_intriguing.mp3** - Subtle, curious music with atmospheric sounds
8. **triumphant_victorious.mp3** - Uplifting, heroic music with powerful crescendos
9. **confrontational_angry.mp3** - Aggressive, intense music with sharp accents
10. **inspirational_uplifting.mp3** - Hopeful, motivating music that builds gradually
11. **awkward_uncomfortable.mp3** - Quirky, off-kilter music with unusual sounds
12. **reflective_contemplative.mp3** - Calm, thoughtful music with space for reflection

## Music Requirements

- **Duration**: ~60 seconds (will be looped automatically to match video length)
- **Format**: MP3 (recommended) or WAV
- **Seamless Loop**: Music should loop smoothly without noticeable gaps
- **Volume**: Original/natural volume (will be adjusted to 20% by default in config)
- **Instrumental Only**: No vocals or lyrics
- **Quality**: High-quality audio (256kbps or higher for MP3)

## How to Generate Music

You can use AI music generation tools with the prompts from `docs/Background music.md`:

1. **Suno AI** (https://suno.ai) - Enter the music generation prompts
2. **MusicGen** - Use the detailed prompts for each category
3. **AIVA** (https://aiva.ai) - AI music composition platform
4. **Soundraw** - AI music generator with mood controls

Example prompt for **comedic_funny**:
```
Create a light, playful instrumental track with upbeat tempo (120-140 BPM).
Use pizzicato strings, xylophone, ukulele, or quirky synth sounds.
Include bouncy rhythms and whimsical melodies that evoke sitcom or comedy sketches.
Duration: 60 seconds, seamless loop.
```

## File Naming

Files must match the exact names in the configuration:
- `comedic_funny.mp3`
- `tense_suspenseful.mp3`
- etc.

## Configuration

Background music settings are in `langflix/config/default.yaml` under the `background_music` section:

```yaml
background_music:
  enabled: true
  volume: 0.20  # 20% of original volume
  fade_in_duration: 1.0
  fade_out_duration: 1.0
  music_directory: "assets/background_music"
```

## Adding New Music

1. Generate or obtain music file matching the requirements above
2. Name the file according to the category (e.g., `comedic_funny.mp3`)
3. Place the file in this directory (`assets/background_music/`)
4. The system will automatically detect and use it when that mood is selected

## Testing

To test if music files are working:

1. Ensure files exist in this directory
2. Run the video generation pipeline with expressions that have `background_music_id` set
3. Check the logs for "Applying background music: [music_id]"
4. Verify the output video has background music at appropriate volume

## Troubleshooting

**Music not playing:**
- Check file exists with exact name from config
- Verify `background_music.enabled: true` in config
- Check logs for warnings about missing music files

**Music too loud/quiet:**
- Adjust `background_music.volume` in config (0.0-1.0)
- Default is 0.20 (20% volume)

**Music doesn't loop smoothly:**
- Ensure source music is designed for seamless looping
- Check fade_in/fade_out durations in config
