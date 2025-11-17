# [TICKET-038] Long-form Sequential Layout with Transition

## Priority
- [ ] Critical (System stability, security, data loss risk)
- [ ] High (Performance issues, significant tech debt)
- [x] Medium (Code quality, maintainability improvements)
- [ ] Low (Nice-to-have refactorings)

## Type
- [ ] Refactoring
- [ ] Performance Optimization
- [ ] Test Coverage
- [ ] Bug Fix
- [ ] Security Issue
- [ ] Technical Debt
- [x] Code Duplication

## Impact Assessment
**Business Impact:**
- Improves video viewing experience by using full-screen sequential layout instead of side-by-side
- Better mobile viewing experience (full-screen videos are more engaging)
- Professional video production standard (sequential transitions)

**Technical Impact:**
- Changes core video construction logic in `create_educational_sequence()`
- Replaces hstack with sequential concatenation
- Requires transition video creation between video and slide segments
- Affects: `langflix/core/video_editor.py` (lines 333-338)

**Effort Estimate:**
- Medium (1-3 days)

## Problem Description

### Current State
**Location:** `langflix/core/video_editor.py:333-338`

Current implementation uses side-by-side layout (hstack):
- Left half: context video → expression repeat
- Right half: educational slide
- Both visible simultaneously

```python
# Step 4: Use hstack to create side-by-side layout (long-form)
# Left: context → expression repeat, Right: educational slide
logger.info("Creating long-form side-by-side layout with hstack")
hstack_temp_path = self.output_dir / f"temp_hstack_long_{safe_expression}.mkv"
self._register_temp_file(hstack_temp_path)
hstack_keep_height(str(left_side_path), str(educational_slide), str(hstack_temp_path))
```

### Root Cause Analysis
- Initial implementation used side-by-side layout for educational purposes
- User feedback indicates preference for sequential full-screen layout
- Sequential layout provides better viewing experience and is more professional

### Evidence
- User requirement: "longform: video (original ratio, full screen) -> (after video done, transition to) education slide (full screen)"
- Existing transition infrastructure already available (`_create_transition_video()` method)

## Proposed Solution

### Approach
1. Replace `hstack_keep_height()` with sequential concatenation
2. Create transition video between video segment and educational slide
3. Structure: `video (full-screen, original ratio) → transition → slide (full-screen)`
4. Ensure all segments maintain same resolution for proper concatenation
5. Use existing `_create_transition_video()` method and transition config

### Implementation Details

**Step 1: Remove hstack, add transition video creation**
```python
# Replace lines 333-338 in create_educational_sequence()

# Step 4: Create transition video between video and slide
from langflix import settings
transition_config = settings.get_transitions_config()
context_to_slide_transition = transition_config.get('context_to_slide_transition', {})

if context_to_slide_transition.get('enabled', True):  # Default enabled
    transition_image_path = context_to_slide_transition.get('image_path_16_9', 'assets/transition_16_9.png')
    sound_effect_path = context_to_slide_transition.get('sound_effect_path', 'assets/sound_effect.mp3')
    transition_duration = context_to_slide_transition.get('duration', 1.0)
    sound_volume = context_to_slide_transition.get('sound_effect_volume', 0.5)
    
    # Find transition assets (reuse existing logic from context_to_expression_transition)
    # Create transition video matching left_side_path resolution
    transition_video_path = self.output_dir / f"temp_transition_video_slide_{safe_expression}.mkv"
    self._register_temp_file(transition_video_path)
    transition_video = self._create_transition_video(
        duration=transition_duration,
        image_path=transition_image_path,
        sound_effect_path=sound_effect_path,
        output_path=transition_video_path,
        source_video_path=str(left_side_path),  # Match video segment resolution
        fps=25,
        sound_effect_volume=sound_volume
    )
    
    # Step 5: Concatenate sequentially: video → transition → slide
    logger.info("Creating long-form sequential layout (video → transition → slide)")
    sequential_temp_path = self.output_dir / f"temp_sequential_long_{safe_expression}.mkv"
    self._register_temp_file(sequential_temp_path)
    
    # Concatenate: left_side_path → transition → educational_slide
    concat_filter_with_explicit_map(
        str(left_side_path),
        str(transition_video),
        str(sequential_temp_path)
    )
    
    # Then add slide
    final_sequential_path = self.output_dir / f"temp_final_sequential_{safe_expression}.mkv"
    self._register_temp_file(final_sequential_path)
    concat_filter_with_explicit_map(
        str(sequential_temp_path),
        str(educational_slide),
        str(final_sequential_path)
    )
    
    temp_output_path = final_sequential_path
else:
    # No transition: direct concatenation
    temp_output_path = self.output_dir / f"temp_sequential_long_{safe_expression}.mkv"
    self._register_temp_file(temp_output_path)
    concat_filter_with_explicit_map(
        str(left_side_path),
        str(educational_slide),
        str(temp_output_path)
    )

# Step 6: Apply final audio gain (unchanged)
apply_final_audio_gain(str(temp_output_path), str(output_path), gain_factor=1.69)
```

**Step 2: Add configuration for context_to_slide transition**
```yaml
# langflix/config/default.yaml
transitions:
  # ... existing transitions ...
  
  # Transition from video segment to educational slide (long-form)
  context_to_slide_transition:
    enabled: true
    duration: 1.0
    image_path_16_9: "assets/transition_16_9.png"
    sound_effect_path: "assets/sound_effect.mp3"
    sound_effect_volume: 0.5
```

### Alternative Approaches Considered
- **Option 1**: Use xfade filter for transition
  - **Why not chosen**: Previous attempts caused A-V sync issues (TICKET-001, ADR-015)
  - Dedicated transition video is more reliable
  
- **Option 2**: Simple cut without transition
  - **Why not chosen**: User explicitly requested transition
  - Transition provides better user experience

- **Selected approach**: Dedicated transition video segment
  - Reuses existing `_create_transition_video()` infrastructure
  - Proven to work (already used for context_to_expression transitions)
  - Maintains A-V sync

### Benefits
- **Better viewing experience**: Full-screen videos are more engaging
- **Professional appearance**: Sequential layout with transitions
- **Mobile-friendly**: Full-screen works better on mobile devices
- **Reuses existing code**: Uses proven `_create_transition_video()` method

### Risks & Considerations
- **Resolution matching**: Must ensure video segment and slide have matching resolution
- **Aspect ratio**: Video must maintain original aspect ratio (no cropping/stretching)
- **Duration impact**: Transition adds 1 second to video duration
- **Backward compatibility**: Breaking change - existing videos will have different layout

## Testing Strategy
- Unit tests: Test transition video creation with matching resolution
- Integration tests: Full long-form video creation with sequential layout
- Manual verification: Visual inspection of video layout and transition smoothness
- Regression tests: Ensure audio sync is maintained

## Files Affected
- `langflix/core/video_editor.py` - `create_educational_sequence()` method (lines 333-342)
- `langflix/config/default.yaml` - Add `context_to_slide_transition` configuration
- `tests/unit/test_video_editor.py` - Add tests for sequential layout
- `tests/integration/test_video_creation.py` - Integration tests

## Dependencies
- Depends on: None (uses existing `_create_transition_video()` method)
- Blocks: TICKET-040 (expression subtitle overlay needs final video structure)

## References
- Existing transition implementation: `langflix/core/video_editor.py:766-861` (`_create_transition_video`)
- Transition config: `langflix/config/default.yaml:156-179`
- Concatenation helper: `langflix/media/ffmpeg_utils.py:concat_filter_with_explicit_map`

## Architect Review Questions
1. Should transition be configurable (enabled/disabled) or always enabled?
2. Should we support different transition durations for video-to-slide vs context-to-expression?
3. Are there any performance concerns with sequential layout vs side-by-side?

## Success Criteria
- [ ] Long-form videos use sequential layout (video → transition → slide)
- [ ] Video maintains original aspect ratio (no distortion)
- [ ] Transition works smoothly between video and slide
- [ ] All segments have matching resolution for proper concatenation
- [ ] Audio sync is maintained throughout
- [ ] Tests pass for new sequential layout
- [ ] Documentation updated

