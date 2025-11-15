# Short-Form Video Structure (9:16 Vertical Format)

## Overview

Short-form videos are vertical format (9:16 aspect ratio, 1080x1920px) designed for social media platforms like TikTok, Instagram Reels, and YouTube Shorts. Each video presents a single English expression with context and translations.

## Layout Specification

### Canvas: 1080x1920px (9:16 aspect ratio)

```
┌─────────────────────────────────────────────────────┐
│ (1080px width)                                      │
│                                                     │
│  ┌─────────────────────────────────────────────────┐│ ┐
│  │                                                 ││ │
│  │  • Logo (top-left, optional)                   ││ │ 180px
│  │  • Yellow Expression text (centered)           ││ │
│  │  • Yellow Expression subtitle                  ││ │
│  │                                                 ││ ┘
│  ├─────────────────────────────────────────────────┤│ ┐
│  │                                                 ││ │
│  │        VIDEO (Structured Video)                ││ │ 960px
│  │        height = 960px                          ││ │
│  │        Width = adjusted to 9:16 ratio          ││ │
│  │        **Have cut off left & right**           ││ │
│  │        **No stretching, keep ratio, cut off**  ││ │
│  │                                                 ││ │
│  │  (Centered horizontally + vertically)          ││ │
│  │                                                 ││ ┘
│  ├─────────────────────────────────────────────────┤│ ┐
│  │                                                 ││ │
│  │  • Dialogue (original language, white text)    ││ │ 100px
│  │  • Subtitle (target language, yellow text)     ││ │
│  │  (positioned 100px from bottom)                ││ │
│  │                                                 ││ ┘
│  └─────────────────────────────────────────────────┘│
│                                                     │
└─────────────────────────────────────────────────────┘
```

## Component Breakdown

### Top Section (Black background, 180px height)
- **Logo**: Optional white circular logo in top-left corner
- **Expression Text**: Main English expression
  - Color: Yellow (`#FFFF00`)
  - Font Size: 24pt (reduced from 48pt for readability)
  - Alignment: Center horizontally
  - Position: ~50px from top
  - Style: Bold, clear sans-serif font

- **Expression Subtitle**: Translation or additional context
  - Color: Yellow (`#FFFF00`)
  - Font Size: Proportional to expression text
  - Alignment: Center horizontally
  - Position: Below expression text

### Middle Section (960px height)
**Structured Video Content** (centered, no stretching)
- **Aspect Ratio**: Maintains original or adjusted to 9:16
- **Scaling Logic**:
  1. Scale video to height = 960px
  2. Maintain original aspect ratio
  3. If width exceeds 1080px, crop from left and right (center crop)
  4. **No stretching** - always crop, never squeeze/stretch
- **Position**: Centered both horizontally and vertically within available space
- **Content**: Context → Expression (2x repeat) → Educational slide

### Bottom Section (Black background, 100px height)
- **Dialogue Text**: Original language dialogue
  - Color: White (`#FFFFFF`)
  - Font Size: 32pt
  - Alignment: Bottom center
  - Position: 100px from bottom edge

- **Subtitle Text**: Target language translation
  - Color: Yellow (`#FFFF00`)
  - Font Size: 32pt (from ASS subtitle style)
  - Alignment: Bottom center
  - Position: Below dialogue, 100px from bottom edge

---

## Implementation Details

### Video Processing Pipeline

```python
# 1. Input: Structured video (16:9 or original ratio)
# 2. Scale to height 960px, maintain aspect ratio
# 3. Crop if width > 1080px
# 4. Pad to 1080x1920 with black background
# 5. Add expression text (drawtext filter, fontsize=24)
# 6. Apply subtitles (ASS format with MarginV=100)
# 7. Output: Final 1080x1920 short-form video
```

### FFmpeg Filter Chain

```bash
# Pseudo-code for filter chain
input_video
  → scale(-1, 960)           # Scale to height 960px
  → crop(1080, 960, x, 0)    # Crop if needed
  → pad(1080, 1920, 0, y)    # Pad to 1080x1920
  → drawtext(...)            # Add expression at top
  → subtitles(...)           # Add subtitles at bottom
  → output
```

### Key FFmpeg Parameters

**drawtext (Expression text at top)**:
```
fontsize=24
fontcolor=yellow
x=(w-text_w)/2    # Center horizontally
y=50               # 50px from top
```

**subtitles (Dialogue + Translation at bottom)**:
```
force_style=Alignment=2,FontSize=32,MarginV=100
# Alignment=2 = bottom center
# MarginV=100 = 100px from bottom
```

---

## Technical Specifications

### Resolution
- **Final Output**: 1080x1920px
- **Video Section**: Width varies (up to 1080px), Height = 960px
- **Aspect Ratio**: 9:16 (vertical/portrait)

### Timing
- **Total Duration**: Up to 180 seconds per batch (configurable)
- **Video Content**: 
  - Context segment: ~15-30 seconds
  - Expression repeat (2x): ~2-4 seconds
  - Educational slide: ~5-10 seconds
- **Audio**: Synchronized with video, expression audio plays 2x during slide

### Colors
- **Background**: Black (`#000000`)
- **Expression Text**: Yellow (`#FFFF00`)
- **Dialogue Text**: White (`#FFFFFF`)
- **Subtitle Text**: Yellow (`#FFFF00`)
- **Outline**: Black with 2px border for subtitle readability

### Fonts
- **Expression Text**: 24pt, Bold
- **Dialogue/Subtitle**: 32pt (ASS style)
- **Font Family**: Language-specific (configured in `LanguageConfig`)

---

## Layout Zones

| Zone | Height | Y Offset | Content | Background |
|------|--------|----------|---------|------------|
| **Top** | 180px | 0-180 | Logo, Expression text, Subtitle | Black |
| **Middle** | 960px | 180-1140 | Structured video (centered) | Black |
| **Bottom** | 100px | 1140-1920 | Dialogue, Subtitles | Black |
| **Total** | 1920px | - | - | - |

---

## Design Rationale

### Why 9:16 (Vertical)?
- Optimized for mobile viewing (primary platform for short-form content)
- Fills screen on TikTok, Instagram Reels, YouTube Shorts
- Better engagement on social media algorithms

### Why Center Crop Instead of Stretch?
- Maintains original video aspect ratio and quality
- Prevents distortion of actors' faces
- Preserves readability of on-screen text

### Why Black Borders?
- Provides clean contrast for text overlays
- Separates content zones (top, middle, bottom)
- Professional appearance

### Why Large Expression Text (but reduced to 24pt)?
- Communicates main learning point clearly
- Yellow color provides high contrast on black
- Positioned above video for immediate visibility

### Why Expression Audio 2x?
- Reinforces pronunciation and listening comprehension
- Fits naturally within educational slide duration
- Optimal for language learning retention

---

## Output Directory Structure

```
output/
├── Series/
│   └── Episode/
│       └── translations/
│           └── {language}/
│               └── videos/                                     # Unified videos directory
│                   ├── short_form_{expression_name_1}.mkv      # Single 9:16 video
│                   ├── short_form_{expression_name_2}.mkv      # Single 9:16 video
│                   ├── short-form_{episode}_{batch_001}.mkv   # Batched short-form videos (≤180s)
│                   ├── structured_video_{expression_1}.mkv    # Structured videos
│                   └── combined_structured_video_{episode}.mkv # Combined structured video
```

---

## Rendering Quality

### Video Codec
- **Codec**: H.264 (libx264)
- **Preset**: fast (balance between speed and quality)
- **CRF**: 23 (recommended for social media)
- **Frame Rate**: 30fps (source or 29.97fps depending on input)

### Audio Codec
- **Codec**: AAC
- **Channels**: 2 (stereo)
- **Sample Rate**: 48000Hz
- **Bitrate**: Auto (VBR)

---

## Accessibility Considerations

1. **High Contrast**: Yellow text on black background (WCAG AA compliant)
2. **Large Font**: 24pt-32pt fonts for readability
3. **Subtitles**: Both original dialogue and target language provided
4. **Centered Layout**: Content centered for better visibility
5. **No Auto-play Sound**: Video requires user interaction to play

---

## Platform-Specific Notes

### TikTok
- Supports 9:16 natively
- Recommended: 1080x1920 resolution
- Max file size: 287.6MB
- Audio focus: Important for engagement

### Instagram Reels
- Accepts 9:16 format
- Recommended: 1080x1920 resolution
- Auto-crops larger videos
- Text recommendations: 14-48pt

### YouTube Shorts
- Prefers 9:16 aspect ratio
- Recommended: 1080x1920 resolution
- Max duration: 60 seconds (or up to 180s for Shorts Feed)
- Full metadata support

---

## Future Enhancements

1. **Transitions**: Add fade/slide transitions between zones
2. **Animated Text**: Bring in expression text with animation
3. **Background Music**: Optional low-volume background audio
4. **Custom Overlays**: Language-specific overlays or badges
5. **Watermark**: Add channel/brand watermark to bottom-right
6. **QR Code**: Add QR linking to full lesson (small, top-right corner)

---

## Related Documentation

- `docs/API_REFERENCE.md` - API endpoints for video generation
- `docs/CONFIGURATION_GUIDE.md` - Tuning video parameters
- `.github/instructions/copilot-instructions.md` - Architecture overview
- `langflix/core/video_editor.py` - Implementation reference

---

**Last Updated**: November 14, 2025  
**Status**: Active  
**Version**: 1.0
