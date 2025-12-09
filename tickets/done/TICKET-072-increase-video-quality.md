# [TICKET-072] Increase Video Quality - Better Encoding Settings

## Priority
- [x] High (Performance issues, significant tech debt)
- [ ] Medium (Code quality, maintainability improvements)
- [ ] Low (Nice-to-have refactorings)

## Type
- [x] Performance Optimization
- [ ] Refactoring
- [ ] Bug Fix
- [ ] Test Coverage
- [ ] Security Issue
- [ ] Technical Debt
- [ ] Code Duplication

## Impact Assessment
**Business Impact:**
- **Current Issue**: Output video quality is significantly worse than original, especially for 720p source videos
- **User Impact**: Poor video quality affects learning experience and viewer engagement
- **Risk of NOT fixing**: Users may stop using the system due to unacceptable quality

**Technical Impact:**
- **Affected Modules**: 
  - `langflix/core/video_editor.py` - Multiple hardcoded encoding settings
  - `langflix/core/video_processor.py` - Clip extraction encoding
  - `langflix/config/default.yaml` - Default quality settings
  - `langflix/media/ffmpeg_utils.py` - Encoding utility functions
- **Files to Change**: ~15-20 files with hardcoded preset/crf values
- **Breaking Changes**: None (quality improvement only)

**Effort Estimate:**
- Medium (1-3 days)
  - Find and replace all hardcoded values
  - Update configuration defaults
  - Test with various source resolutions
  - Verify quality improvements

## Problem Description

### Current State
**Location:** Multiple files with hardcoded encoding parameters

The system currently has inconsistent and quality-degrading encoding settings:

1. **Hardcoded Low-Quality Settings:**
   ```python
   # langflix/core/video_editor.py (multiple locations)
   preset='fast', crf=23  # Too high CRF, too fast preset
   preset='veryfast', crf=25  # Even worse quality
   ```

2. **Inconsistent Configuration Usage:**
   - `default.yaml` has `preset: "fast"` and `crf: 10`
   - But many code locations ignore config and use hardcoded `crf=23` or `crf=25`
   - Some locations use `preset='veryfast'` which prioritizes speed over quality

3. **Quality Degradation:**
   - CRF 23-25 is too high for 720p source videos (visible quality loss)
   - "fast" and "veryfast" presets sacrifice quality for speed
   - Multiple encoding passes accumulate quality loss

### Root Cause Analysis
- **Historical Context**: Settings were optimized for speed (TICKET-035) but quality was sacrificed
- **Pattern**: Hardcoded values scattered throughout codebase instead of using centralized config
- **Related Issues**: TICKET-055 attempted to improve quality but didn't address all hardcoded values

### Evidence
- User report: "Current transcoding time is faster than before, but the outcome video is so bad. Especially the original video is 720p, it is very bad."
- Code audit shows:
  - `video_editor.py`: 15+ locations with `crf=23` or `crf=25`
  - `video_processor.py`: `crf=23` hardcoded
  - `default.yaml`: `crf: 10` (good) but not consistently used
  - `ffmpeg_utils.py`: Falls back to `crf=20` (better but still not optimal)

## Proposed Solution

### Approach
1. **Update Default Configuration:**
   - Change `preset` from `"fast"` to `"medium"` (better quality, acceptable speed)
   - Change `crf` from `10` to `18` (high quality, good balance)
   - For 720p sources, consider `crf=16-18` for near-lossless quality

2. **Remove All Hardcoded Values:**
   - Replace all `preset='fast'` and `crf=23` with config-based values
   - Ensure all encoding operations use `_get_video_output_args()` or similar
   - Create helper functions to get quality settings based on source resolution

3. **Resolution-Aware Quality:**
   - For 720p and below: Use `crf=18` (higher quality)
   - For 1080p and above: Use `crf=20` (good quality, smaller files)
   - Allow override via config for users who prioritize speed

### Implementation Details

**Step 1: Update Default Configuration**
```yaml
# langflix/config/default.yaml
video:
  # Encoding preset: medium provides better quality than fast
  # Acceptable encoding speed with significantly better quality
  preset: "medium"
  
  # CRF: 18 provides high quality (near-lossless for most content)
  # Lower values = better quality (18-20 is excellent range)
  crf: 18
  
  # Optional: Resolution-specific overrides
  quality_by_resolution:
    720p: 18    # Higher quality for 720p sources
    1080p: 20   # Good quality for 1080p
    2160p: 22   # Acceptable quality for 4K (smaller files)
```

**Step 2: Create Resolution-Aware Quality Helper**
```python
# langflix/core/video_editor.py
def _get_quality_settings(self, source_video_path: Optional[str] = None) -> dict:
    """Get quality settings based on source video resolution."""
    video_config = settings.get_video_config()
    base_crf = video_config.get('crf', 18)
    base_preset = video_config.get('preset', 'medium')
    
    # If source video provided, adjust quality based on resolution
    if source_video_path:
        from langflix.media.ffmpeg_utils import get_video_params
        vp = get_video_params(source_video_path)
        height = vp.height or 720
        
        # Higher quality for lower resolution sources (720p needs more care)
        if height <= 720:
            crf = min(base_crf, 18)  # Ensure high quality for 720p
        elif height <= 1080:
            crf = base_crf
        else:
            crf = max(base_crf, 20)  # Can use slightly lower for 4K
            
        return {
            'preset': base_preset,
            'crf': crf,
            'vcodec': video_config.get('codec', 'libx264'),
            'acodec': video_config.get('audio_codec', 'aac')
        }
    
    return {
        'preset': base_preset,
        'crf': base_crf,
        'vcodec': video_config.get('codec', 'libx264'),
        'acodec': video_config.get('audio_codec', 'aac')
    }
```

**Step 3: Replace All Hardcoded Values**
```python
# Before (video_editor.py line 302):
preset='fast', crf=23

# After:
video_args = self._get_quality_settings(source_video_path)
preset=video_args['preset'], crf=video_args['crf']
```

**Files to Update:**
- `langflix/core/video_editor.py` - ~15 locations
- `langflix/core/video_processor.py` - 2 locations
- `langflix/config/default.yaml` - Update defaults
- `langflix/config/config.example.yaml` - Update examples

### Alternative Approaches Considered
- **Option 1: Two-Pass Encoding** - Better quality but 2x encoding time (rejected: too slow)
- **Option 2: Keep fast preset, lower CRF** - Faster but still quality loss (rejected: doesn't solve problem)
- **Option 3: Resolution-aware quality** - Selected: Best balance of quality and speed

### Benefits
- **Improved Quality**: CRF 18 vs 23 = significantly better visual quality
- **Better Preset**: Medium vs Fast = better compression efficiency
- **Resolution-Aware**: 720p sources get extra quality care
- **Consistent Settings**: All encoding uses centralized config
- **Configurable**: Users can still override for speed if needed

### Risks & Considerations
- **Encoding Time**: Medium preset is ~2x slower than fast (acceptable trade-off)
- **File Size**: CRF 18 produces larger files than CRF 23 (~20-30% increase)
- **Backward Compatibility**: Existing configs may need update (documented in migration guide)
- **Testing Required**: Verify quality improvements with various source resolutions

## Testing Strategy
- **Unit Tests**: Verify `_get_quality_settings()` returns correct values
- **Integration Tests**: Test video creation with new settings
- **Quality Validation**: 
  - Compare output quality metrics (PSNR, SSIM) before/after
  - Visual inspection of 720p source → output comparison
  - File size comparison (expect 20-30% increase)
- **Performance Tests**: Measure encoding time increase (expect ~2x for medium preset)

## Files Affected
- `langflix/config/default.yaml` - Update preset and crf defaults
- `langflix/config/config.example.yaml` - Update example values
- `langflix/core/video_editor.py` - Replace all hardcoded preset/crf values (~15 locations)
- `langflix/core/video_processor.py` - Replace hardcoded values in clip extraction
- `langflix/media/ffmpeg_utils.py` - Update default fallback values
- `tests/core/test_video_editor.py` - Add tests for quality settings
- `docs/CONFIGURATION_GUIDE.md` - Document new quality settings

## Dependencies
- Depends on: None
- Blocks: None
- Related to: TICKET-055 (previous quality improvement attempt)

## References
- FFmpeg CRF Guide: https://trac.ffmpeg.org/wiki/Encode/H.264
- CRF Quality Ranges:
  - 18-20: Visually lossless / High quality
  - 21-23: Good quality
  - 24-28: Acceptable quality
  - 29+: Low quality
- Preset Comparison:
  - veryfast: ~5x faster, ~30% larger files, lower quality
  - fast: ~3x faster, ~20% larger files, good quality
  - medium: Baseline, balanced
  - slow: ~2x slower, ~10% smaller files, better quality

## Success Criteria
- [ ] All hardcoded `preset` and `crf` values removed from codebase
- [ ] Default config uses `preset: "medium"` and `crf: 18`
- [ ] 720p source videos produce visibly better quality output
- [ ] Quality metrics (PSNR/SSIM) show improvement
- [ ] Encoding time increase is acceptable (<3x slower)
- [ ] All tests pass
- [ ] Documentation updated with quality settings guide

