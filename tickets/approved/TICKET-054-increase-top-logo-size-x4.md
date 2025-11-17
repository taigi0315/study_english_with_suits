# [TICKET-054] Increase Top Logo Size to 4x (Width and Height) While Keeping Y=0 Position

## Priority
- [ ] Critical (System stability, security, data loss risk)
- [ ] High (Performance issues, significant tech debt)
- [ ] Medium (Code quality, maintainability improvements)
- [x] Low (Nice-to-have refactorings)

## Type
- [ ] Refactoring
- [ ] Performance Optimization
- [ ] Test Coverage
- [ ] Bug Fix
- [ ] Security Issue
- [ ] Technical Debt
- [ ] Code Duplication

## Impact Assessment
**Business Impact:**
- Improves logo visibility in short-form videos
- Better brand recognition on social media platforms
- Low risk - visual change only, doesn't affect functionality

**Technical Impact:**
- Single file change: `langflix/core/video_editor.py`
- Change logo scale from 150px height to 600px height (4x)
- Position remains at y=0 (absolute top)
- Estimated files: 1 file

**Effort Estimate:**
- Small (< 1 day)

## Problem Description

### Current State
**Location:** `langflix/core/video_editor.py:884`

The top logo is currently scaled to 150px height:

```python
logo_video = logo_input['v'].filter('scale', -1, 150)  # Original size: 150px height
```

This is too small for visibility in 1080x1920px short-form videos. The logo should be 4x larger (600px height) while maintaining its position at y=0.

### Root Cause Analysis
- Logo size was set to 150px to fix positioning issues in previous implementation
- Comment indicates it was "reverted to original size to fix positioning issue"
- Size was not optimized for visibility in vertical format videos

### Evidence
- `langflix/core/video_editor.py` line 884: Logo scaled to 150px height
- Comment on line 882: "Reverted to original size (150px height) to fix positioning"
- Video canvas is 1080x1920px, so 150px logo is only ~7.8% of canvas height

## Proposed Solution

### Approach
1. Change logo scale from 150px to 600px height (4x increase)
2. Keep y=0 position (absolute top)
3. Maintain horizontal centering (x='(W-w)/2')
4. Update comment to reflect new size

### Implementation Details
```python
# Current code (line 884)
logo_video = logo_input['v'].filter('scale', -1, 150)  # Original size: 150px height

# Proposed change
logo_video = logo_input['v'].filter('scale', -1, 600)  # 4x size: 600px height (was 150px)
```

```python
# Update comment (line 882-894)
# Add logo at the very end to ensure it stays at absolute top (y=0)
# Logo position: absolute top (y=0) of black padding, above hashtags
# Logo size: 600px height (4x original for better visibility)
logo_path = Path(__file__).parent.parent.parent / "assets" / "top_logo.png"
if logo_path.exists():
    try:
        # Load logo image and overlay it at top center
        # Logo size: 600px height (4x for better visibility in 1080x1920px videos)
        logo_input = ffmpeg.input(str(logo_path))
        logo_video = logo_input['v'].filter('scale', -1, 600)  # 4x size: 600px height
        
        # Overlay logo at absolute top center - LAST in filter chain
        final_video = ffmpeg.overlay(
            final_video,
            logo_video,
            x='(W-w)/2',  # Center horizontally (W = canvas width, w = logo width)
            y=0,  # Absolute top - logo's top-left corner at y=0 (canvas top)
            enable='between(t,0,999999)'  # Ensure logo appears throughout entire video
        )
        logger.info("Added logo at absolute top of short-form video (y=0, 600px height)")
```

### Alternative Approaches Considered
- Option 1: Scale based on canvas percentage (e.g., 10% of height) - More complex, current approach is clearer
- Option 2: Make size configurable - Overkill for single use case

### Benefits
- 4x larger logo improves visibility
- Better brand recognition
- Simple change, low risk
- Maintains existing positioning logic

### Risks & Considerations
- Larger logo may overlap with expression text if expression text is too high
- Need to verify logo doesn't exceed canvas width (1080px)
- May need to adjust if logo aspect ratio causes width issues

## Testing Strategy
- Visual test: Generate short-form video and verify logo size
- Verify logo remains at y=0 position
- Verify logo is horizontally centered
- Check logo doesn't overlap with expression text
- Verify logo width doesn't exceed 1080px canvas width

## Files Affected
- `langflix/core/video_editor.py` - Update logo scale from 150px to 600px height (line 884)
- Update comment to reflect new size (lines 882-894)

## Dependencies
- Depends on: None
- Blocks: None
- Related to: None

## References
- Video editor: `langflix/core/video_editor.py:875-898`
- Short-form video structure: `docs/SHORT_FORM_VIDEO_STRUCTURE.md`

## Architect Review Questions
**For the architect to consider:**
1. Should logo size be configurable instead of hardcoded?
2. Are there any layout conflicts with larger logo?
3. Should we add validation for logo dimensions?

## Success Criteria
How do we know this is successfully implemented?
- [ ] Logo is scaled to 600px height (4x original)
- [ ] Logo remains at y=0 position (absolute top)
- [ ] Logo is horizontally centered
- [ ] Logo doesn't overlap with expression text
- [ ] Logo width doesn't exceed canvas width (1080px)
- [ ] Visual test confirms improved visibility

