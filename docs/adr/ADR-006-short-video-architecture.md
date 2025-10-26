# ADR-006: Short Video Architecture

**Date:** 2025-10-20  
**Status:** Accepted  
**Deciders:** Development Team  

## Context

LangFlix needed to support short-format videos for social media platforms like Instagram, TikTok, and YouTube Shorts. The existing educational video format (16:9 landscape) was not suitable for mobile-first social media consumption. Users requested the ability to create vertical videos optimized for mobile viewing and social sharing.

## Decision

We will implement a short video generation system that creates 9:16 aspect ratio videos with the following architecture:

1. **Vertical Format**: 9:16 aspect ratio (1080x1920)
2. **Split Layout**: Upper half shows context video, lower half shows educational slide
3. **Automatic Batching**: Combine multiple expressions into ~120-second videos
4. **Social Media Ready**: Optimized for mobile viewing and sharing

## Implementation Details

### Technical Architecture

1. **Video Layout**:
   - **Upper Half**: Context video with target language subtitles (1080x960)
   - **Lower Half**: Educational slide without audio (1080x960)
   - **Combined**: 1080x1920 (9:16 vertical format)

2. **Audio Timeline**:
   - Context audio plays during video portion
   - After context ends: Expression audio plays with configurable repetitions
   - **Expression video loops** during expression audio playback (no freeze frame)
   - 40% volume boost applied for optimal audio quality

3. **Batching System**:
   - Target duration: ~120 seconds per batch
   - Automatic combination of individual short videos
   - Configurable duration variance (±10 seconds)

### Configuration

```yaml
short_video:
  enabled: true
  resolution: "1080x1920"  # 9:16 vertical format
  target_duration: 120    # Target duration per batch (seconds)
  duration_variance: 10   # Allow ±10 seconds variance
```

### Output Structure

```
output/Series/Episode/translations/ko/
├── context_slide_combined/  # Educational videos
│   ├── educational_expression_01.mkv
│   └── educational_expression_02.mkv
└── short_videos/            # Short-format batched videos
    ├── batch_01_120s.mkv   # ~120 seconds, multiple expressions
    ├── batch_02_115s.mkv
    └── batch_03_95s.mkv
```

### CLI Integration

```bash
# Default: short videos enabled
python -m langflix.main --subtitle "file.srt"

# Skip short video creation
python -m langflix.main --subtitle "file.srt" --no-shorts
```

## Consequences

### Positive

- **Social Media Ready**: Optimized for Instagram, TikTok, YouTube Shorts
- **Mobile First**: 9:16 format perfect for mobile viewing
- **Automatic Batching**: Reduces manual work for content creators
- **Flexible Configuration**: Adjustable duration and resolution
- **Backward Compatibility**: Existing educational videos still created

### Negative

- **Additional Processing**: More video processing required
- **Storage Requirements**: Additional disk space for short videos
- **Complexity**: More complex video processing pipeline

### Technical Considerations

1. **Video Processing**: Requires FFmpeg with vertical stacking support
2. **Audio Synchronization**: Complex audio timeline with context + TTS
3. **Batch Management**: Automatic duration calculation and batching
4. **Quality Control**: Ensure consistent quality across batches

## Alternatives Considered

1. **Manual Video Creation**: Rejected due to time-consuming nature
2. **Separate Tool**: Rejected due to integration complexity
3. **Post-Processing Script**: Rejected due to workflow disruption
4. **Different Aspect Ratios**: Rejected due to social media standards

## Implementation Timeline

1. **Phase 1**: Basic short video creation (context + slide) ✅
2. **Phase 2**: Audio timeline implementation ✅
3. **Phase 3**: Batching system ✅
4. **Phase 4**: CLI integration and configuration ✅
5. **Phase 5**: Expression video playback enhancement ✅

## Recent Enhancements (October 2025)

### Expression Video Playback
- **Issue**: Previously used freeze frame during expression audio repetition
- **Solution**: Implemented expression video looping to match audio timeline
- **Result**: Continuous video motion throughout entire short video

### Audio-Video Synchronization
- **Issue**: Expression video duration (2-3s) shorter than audio timeline (5-8s)
- **Solution**: FFmpeg loop filter to repeat expression video seamlessly
- **Result**: Perfect synchronization between video and audio content

### Video File Matching
- **Issue**: Incorrect video file selection for audio extraction
- **Solution**: Use same video matching logic as educational videos
- **Result**: Accurate expression audio from correct source video

### Technical Improvements
- **Multiple Expressions**: Support for batching multiple expressions per video
- **Volume Enhancement**: 40% volume boost for optimal audio quality
- **Quality Preservation**: Maintained high-quality encoding (1500+ kbps)
- **Error Handling**: Graceful fallback to freeze frame if video processing fails

## References

- [Instagram Video Specifications](https://business.instagram.com/blog/instagram-video-specs)
- [TikTok Video Requirements](https://support.tiktok.com/en/using-tiktok/creating-videos/video-specifications)
- [YouTube Shorts Guidelines](https://support.google.com/youtube/answer/12500910)
