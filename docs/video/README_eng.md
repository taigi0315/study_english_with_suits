# Video Module

## Overview

The `langflix/video/` module provides video quality enhancement functionality for LangFlix. It offers intelligent video upscaling, frame interpolation, color correction, stabilization, and quality enhancement capabilities.

**Purpose:**
- Enhance video quality for educational content
- Upscale videos to target resolutions
- Stabilize shaky video footage
- Improve color, contrast, and sharpness
- Reduce noise and artifacts

**When to use:**
- When source video quality needs improvement
- When upscaling videos to higher resolutions
- When stabilizing shaky footage
- When enhancing colors or reducing noise

## File Inventory

### `video_enhancer.py`
Main module for video quality enhancement operations.

**Key Classes:**
- `VideoEnhancer` - Main enhancement class
- `VideoQualityMetrics` - Video quality measurement dataclass
- `VideoEnhancementConfig` - Configuration dataclass

**Key Functions:**
- `enhance_video()` - Main enhancement function with quality levels
- `upscale_video()` - Upscale to target resolution
- `stabilize_video()` - Stabilize shaky footage
- `enhance_colors()` - Color correction and enhancement
- `reduce_noise()` - Noise reduction
- `interpolate_frames()` - Frame rate interpolation

## Key Components

### VideoEnhancer Class

```python
class VideoEnhancer:
    """Advanced video quality enhancement system"""
    
    def __init__(self, config: Optional[VideoEnhancementConfig] = None):
        """
        Initialize video enhancer
        
        Args:
            config: Video enhancement configuration
        """
```

**Configuration Options:**
- `target_resolution`: Optional target resolution (width, height)
- `target_fps`: Optional target frame rate
- `target_bitrate`: Optional target bitrate
- `enhance_sharpness`: Enable sharpening (default: True)
- `enhance_colors`: Enable color enhancement (default: True)
- `stabilize`: Enable video stabilization (default: False)
- `interpolate_frames`: Enable frame interpolation (default: False)
- `upscale_quality`: Upscaling quality level (low, medium, high)

### Enhancement Levels

The enhancer supports three quality levels:

**Low Enhancement:**
- Basic sharpening (unsharp filter)
- Standard encoding (CRF 23, medium preset)
- Fast processing

**Medium Enhancement:**
- Sharpening + color enhancement
- Optional stabilization
- Better quality (CRF 20, medium preset)

**High Enhancement:**
- Sharpening + color enhancement + noise reduction
- Optional stabilization and frame interpolation
- Best quality (CRF 18, slow preset)

### Video Quality Metrics

```python
@dataclass
class VideoQualityMetrics:
    """Video quality metrics"""
    resolution: Tuple[int, int]
    fps: float
    bitrate: int
    color_space: str
    color_range: str
    brightness: float
    contrast: float
    saturation: float
    sharpness: float
    noise_level: float
```

**Usage:**
```python
from langflix.video.video_enhancer import VideoEnhancer

enhancer = VideoEnhancer()
metrics = enhancer.enhance_video(
    input_path="input.mkv",
    output_path="output.mkv",
    enhancement_level="medium"
)
```

## Implementation Details

### Video Analysis

The enhancer uses FFprobe to analyze video quality:

```python
def _analyze_video_quality(self, video_path: str) -> VideoQualityMetrics:
    """Analyze video quality metrics using FFprobe"""
    cmd = [
        'ffprobe', '-v', 'quiet', '-print_format', 'json',
        '-show_streams', '-show_format', video_path
    ]
    # Extract resolution, fps, bitrate, etc.
```

### Enhancement Filters

**Sharpening:**
```python
'unsharp=5:5:0.8:3:3:0.4'  # Basic sharpening filter
```

**Color Enhancement:**
```python
'eq=brightness=0.05:contrast=1.1:saturation=1.1'  # Color correction
```

**Noise Reduction:**
```python
'hqdn3d=4:3:6:4.5'  # High-quality denoise filter
```

**Stabilization:**
```python
# Two-pass stabilization
'vidstabdetect=stepsize=6:shakiness=8:accuracy=9:result=transforms.trf'
'vidstabtransform=smoothing=10:input=transforms.trf'
```

**Frame Interpolation:**
```python
'minterpolate=fps=60:mi_mode=mci'  # Motion-compensated interpolation
```

### Upscaling

The module supports high-quality upscaling using Lanczos algorithm:

```python
def upscale_video(
    self,
    input_path: str,
    output_path: str,
    target_resolution: Tuple[int, int],
    upscale_quality: str = "high"
) -> str:
    """
    Upscale video to target resolution
    
    High quality: Lanczos scaling, CRF 18, slow preset
    Standard: Bilinear scaling, CRF 23, medium preset
    """
```

## Dependencies

**External Libraries:**
- `ffmpeg` - Video processing (via subprocess)
- `ffprobe` - Video analysis

**Internal Dependencies:**
- None (standalone module)

**FFmpeg Filters Required:**
- `unsharp` - Sharpening
- `eq` - Color correction
- `hqdn3d` - Noise reduction
- `vidstabdetect` / `vidstabtransform` - Stabilization
- `minterpolate` - Frame interpolation
- `scale` - Resolution scaling

## Common Tasks

### Basic Video Enhancement

```python
from langflix.video.video_enhancer import VideoEnhancer

enhancer = VideoEnhancer()
metrics = enhancer.enhance_video(
    input_path="input.mkv",
    output_path="enhanced.mkv",
    enhancement_level="medium"
)

print(f"Resolution: {metrics.resolution}")
print(f"FPS: {metrics.fps}")
print(f"Bitrate: {metrics.bitrate}")
```

### Upscaling Video

```python
from langflix.video.video_enhancer import VideoEnhancer

enhancer = VideoEnhancer()
output = enhancer.upscale_video(
    input_path="720p.mkv",
    output_path="1080p.mkv",
    target_resolution=(1920, 1080),
    upscale_quality="high"
)
```

### Stabilizing Shaky Video

```python
from langflix.video.video_enhancer import VideoEnhancer

enhancer = VideoEnhancer()
output = enhancer.stabilize_video(
    input_path="shaky.mkv",
    output_path="stable.mkv"
)
```

### Color Enhancement

```python
from langflix.video.video_enhancer import VideoEnhancer

enhancer = VideoEnhancer()
output = enhancer.enhance_colors(
    input_path="dull.mkv",
    output_path="vibrant.mkv"
)
```

### Getting Enhancement Recommendations

```python
from langflix.video.video_enhancer import VideoEnhancer

enhancer = VideoEnhancer()
metrics = enhancer._analyze_video_quality("input.mkv")
recommendations = enhancer.get_enhancement_recommendations(metrics)

for rec in recommendations:
    print(f"- {rec}")
```

## Gotchas and Notes

### Important Considerations

1. **Processing Time:**
   - High enhancement levels take significantly longer
   - Stabilization requires two passes (detect + transform)
   - Frame interpolation is computationally expensive

2. **Quality vs. Speed:**
   - Low: Fast, basic quality
   - Medium: Balanced quality and speed
   - High: Best quality, slowest processing

3. **Stabilization:**
   - Requires two-pass processing
   - Creates `transforms.trf` file in current directory
   - May crop video edges slightly

4. **Frame Interpolation:**
   - Increases file size significantly
   - Best for slow-motion or smooth motion
   - May introduce artifacts in fast-moving scenes

5. **Upscaling:**
   - Cannot add detail that doesn't exist
   - Best results with high-quality source
   - Lanczos algorithm provides better quality than bilinear

### Performance Tips

- Use medium enhancement for most cases
- Only use high enhancement for final output
- Disable unnecessary features (stabilization, interpolation) if not needed
- Process in batches for multiple videos

### Error Handling

- FFprobe analysis may fail for corrupted videos
- Returns default metrics on analysis failure
- FFmpeg errors raise exceptions (handle in calling code)

### Current Implementation Status

**Note:** The current implementation provides a solid foundation for video enhancement. Some features may need refinement based on specific use cases:

- Brightness/contrast/saturation metrics are placeholders
- Advanced quality analysis could be enhanced
- Custom filter chains could be added

## Related Documentation

- [Media Module](../media/README_eng.md) - FFmpeg utilities and media processing
- [Core Module](../core/README_eng.md) - Video editing and pipeline logic

