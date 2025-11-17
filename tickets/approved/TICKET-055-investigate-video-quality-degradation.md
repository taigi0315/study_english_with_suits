# [TICKET-055] Investigate and Fix Video Quality Degradation in Output Videos

## Priority
- [ ] Critical (System stability, security, data loss risk)
- [x] High (Performance issues, significant tech debt)
- [ ] Medium (Code quality, maintainability improvements)
- [ ] Low (Nice-to-have refactorings)

## Type
- [ ] Refactoring
- [ ] Performance Optimization
- [ ] Test Coverage
- [x] Bug Fix
- [ ] Security Issue
- [ ] Technical Debt
- [ ] Code Duplication

## Impact Assessment
**Business Impact:**
- Output videos have significantly worse quality than original source videos
- Affects user experience and content quality
- High priority - core functionality issue affecting video output

**Technical Impact:**
- Need to investigate encoding settings across video processing pipeline
- Multiple files may need changes:
  - `langflix/config/default.yaml` - CRF and preset settings
  - `langflix/media/ffmpeg_utils.py` - Encoding arguments
  - `langflix/core/video_editor.py` - Video processing filters
  - Any other video encoding locations
- Estimated files: 3-5 files

**Effort Estimate:**
- Medium (1-3 days) - Investigation + fixes

## Problem Description

### Current State
**Location:** Multiple files in video processing pipeline

User reports that output video quality is "much worse than original video". This suggests encoding settings are too aggressive or incorrect.

**Potential Issues:**

1. **CRF Setting Too High:**
   ```yaml
   # langflix/config/default.yaml line 93
   crf: 0  # This is lossless, but may be overridden elsewhere
   ```

2. **Encoding Preset Too Fast:**
   ```yaml
   # langflix/config/default.yaml line 89
   preset: "veryfast"  # Optimized for speed, may sacrifice quality
   ```

3. **Multiple Re-encodings:**
   - Video may be encoded multiple times through pipeline
   - Each re-encoding loses quality
   - Need to use stream copy when possible

4. **Incorrect Codec or Settings:**
   ```python
   # langflix/media/ffmpeg_utils.py line 363
   args["crf"] = video_config.get("crf", 25)  # Default CRF 25 may be too high
   ```

### Root Cause Analysis
- CRF 0 (lossless) in default.yaml but may be overridden to 25 in code
- "veryfast" preset prioritizes speed over quality
- Multiple encoding passes may accumulate quality loss
- No quality preservation strategy (stream copy when possible)

### Evidence
- `langflix/config/default.yaml` line 93: `crf: 0` (lossless)
- `langflix/media/ffmpeg_utils.py` line 363: Falls back to `crf: 25` if config not available
- `langflix/media/ffmpeg_utils.py` line 362: Falls back to `preset: "veryfast"`
- User report: "output video quality is much worse than original"

## Proposed Solution

### Approach
1. **Investigate current encoding settings:**
   - Check all CRF values used in codebase
   - Check all preset values
   - Identify all video encoding locations
   - Measure quality loss at each stage

2. **Optimize encoding settings:**
   - Use CRF 18-23 for high quality (lower = better quality)
   - Use "medium" or "slow" preset for better quality
   - Prefer stream copy when no filters are needed
   - Use two-pass encoding for critical videos if needed

3. **Minimize re-encoding:**
   - Use stream copy for operations that don't require re-encoding
   - Combine filters to reduce encoding passes
   - Cache intermediate results when possible

4. **Add quality validation:**
   - Compare source vs output quality metrics
   - Add logging for encoding parameters
   - Warn if quality degradation detected

### Implementation Details

**Step 1: Audit Current Settings**
```bash
# Find all CRF references
grep -r "crf" langflix/ --include="*.py" --include="*.yaml"

# Find all preset references  
grep -r "preset" langflix/ --include="*.py" --include="*.yaml"
```

**Step 2: Update Default Config**
```yaml
# langflix/config/default.yaml
video:
  preset: "medium"  # Change from "veryfast" to "medium" for better quality
  crf: 20           # Change from 0 to 20 (high quality, not lossless but much better than 25)
```

**Step 3: Update Encoding Utils**
```python
# langflix/media/ffmpeg_utils.py line 362-363
args["preset"] = video_config.get("preset", "medium")  # Better default
args["crf"] = video_config.get("crf", 20)              # Better default (was 25)
```

**Step 4: Add Quality Logging**
```python
# Log encoding parameters before encoding
logger.info(f"Encoding video with preset={args['preset']}, crf={args['crf']}, codec={args['vcodec']}")
```

### Alternative Approaches Considered
- Option 1: Use CRF 18 (near-lossless) - May be too slow for production
- Option 2: Two-pass encoding - Too complex, single-pass with good settings should suffice
- Option 3: Hardware acceleration - Good for performance but doesn't solve quality issue

### Benefits
- Significantly improved output video quality
- Better user experience
- Maintainable quality settings
- Configurable for different use cases

### Risks & Considerations
- Slower encoding with "medium" preset (acceptable trade-off)
- Larger file sizes with lower CRF (acceptable for quality)
- Need to test encoding time impact
- May need different settings for different video types

## Testing Strategy
- **Quality Comparison:**
  - Generate test video from high-quality source
  - Compare PSNR/SSIM metrics between source and output
  - Visual quality inspection
  
- **Performance Testing:**
  - Measure encoding time with new settings
  - Compare file sizes
  - Verify acceptable performance impact

- **Regression Testing:**
  - Ensure all video generation paths still work
  - Test with different video types (short, final, context)
  - Verify no breaking changes

## Files Affected
- `langflix/config/default.yaml` - Update CRF and preset defaults
- `langflix/media/ffmpeg_utils.py` - Update encoding argument defaults
- `langflix/core/video_editor.py` - Verify encoding settings used
- `langflix/core/video_processor.py` - Check clip extraction encoding
- Any other files that encode video

## Dependencies
- Depends on: None
- Blocks: None
- Related to: TICKET-035 (adaptive clip extraction - may have encoding settings)

## References
- FFmpeg CRF guide: https://trac.ffmpeg.org/wiki/Encode/H.264
- Video quality settings: `docs/CONFIGURATION_GUIDE.md:94-116`
- Encoding utils: `langflix/media/ffmpeg_utils.py:329-373`

## Architect Review Questions
**For the architect to consider:**
1. Should we have different quality settings for different video types?
2. Is encoding speed or quality more important for this use case?
3. Should we add quality presets (low/medium/high) for users to choose?
4. Do we need hardware acceleration to maintain performance with better quality?

## Success Criteria
How do we know this is successfully implemented?
- [ ] Output video quality is comparable to or better than current (measured via PSNR/SSIM)
- [ ] Visual inspection confirms improved quality
- [ ] Encoding time is acceptable (within 2x of current)
- [ ] All video generation paths tested and working
- [ ] Encoding parameters logged for debugging
- [ ] Documentation updated with quality settings

---
## 🏛️ Architect Review & Approval

**Reviewed by:** Architect Agent
**Review Date:** 2025-01-16
**Decision:** ✅ APPROVED

**Strategic Rationale:**
Why this aligns with our architectural vision:
- Video quality is a core product differentiator - poor quality directly impacts user experience and content value
- This addresses a critical user-reported issue that affects the primary output of the system
- Quality improvements align with our goal of producing professional-grade educational content
- This enables better content distribution and user satisfaction

**Implementation Phase:** Phase 1 - Sprint 1 (High Priority)
**Sequence Order:** #1 in implementation queue (should be done first)

**Architectural Guidance:**
Key considerations for implementation:
- **Quality vs Speed Trade-off**: Balance encoding quality with processing time. CRF 20 + "medium" preset is a good starting point, but monitor encoding times
- **Configuration Pattern**: Ensure encoding settings are centralized in config and can be overridden per video type if needed
- **Stream Copy Strategy**: Prioritize using stream copy when no filters are applied to avoid unnecessary re-encoding
- **Logging**: Add comprehensive logging for encoding parameters to enable debugging and quality monitoring
- **Performance Target**: Encoding time should not exceed 2x current time; if it does, consider hardware acceleration or quality presets

**Dependencies:**
- **Must complete first:** None
- **Should complete first:** None
- **Blocks:** None (but should be prioritized)
- **Related work:** TICKET-035 (may have encoding settings to review)

**Risk Mitigation:**
- **Risk**: Slower encoding may impact batch processing times
  - **Mitigation**: Start with "medium" preset, monitor performance, adjust if needed
- **Risk**: Larger file sizes with lower CRF
  - **Mitigation**: Acceptable trade-off for quality; document expected file size increase
- **Risk**: Different video types may need different settings
  - **Mitigation**: Make settings configurable per video type in config.yaml
- **Rollback Strategy**: Settings are in config files - easy to revert if performance issues arise

**Enhanced Success Criteria:**
Beyond original ticket criteria:
- [ ] Encoding settings are centralized and configurable
- [ ] Performance impact is documented (encoding time, file size)
- [ ] Quality metrics (PSNR/SSIM) are measured and logged
- [ ] Documentation updated in `docs/CONFIGURATION_GUIDE.md` with quality settings explanation
- [ ] All video encoding paths use consistent quality settings

**Alternative Approaches Considered:**
- Original proposal: CRF 20 + "medium" preset - **Selected approach** - Good balance of quality and speed
- Alternative 1: CRF 18 + "slow" preset - Too slow for production use
- Alternative 2: Two-pass encoding - Too complex, single-pass with good settings sufficient
- Alternative 3: Hardware acceleration only - Doesn't solve quality issue, can be added later

**Implementation Notes:**
- Start by: Auditing all encoding locations with `grep -r "crf\|preset"` to find all places
- Watch out for: Multiple encoding passes that accumulate quality loss
- Coordinate with: None
- Reference: FFmpeg CRF guide, existing encoding utils in `langflix/media/ffmpeg_utils.py`

**Estimated Timeline:** 2-3 days (includes investigation + implementation + testing)
**Recommended Owner:** Senior engineer with video encoding experience

