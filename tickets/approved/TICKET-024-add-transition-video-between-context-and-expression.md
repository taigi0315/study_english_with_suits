# [TICKET-024] Add Transition Video Between Context and Expression Videos

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
- [x] Feature Enhancement

## Impact Assessment
**Business Impact:**
- Enhanced video quality with professional transitions
- Better user experience with smooth visual transitions between segments
- Sound effects provide audio cues for better engagement
- Videos will be 1 second longer (transition duration) to accommodate transition segment

**Technical Impact:**
- Affected modules: `langflix/core/video_editor.py`, `langflix/config/default.yaml`
- Expected files to change: 3-5 files
- Breaking changes: None (additive feature, can be enabled/disabled via config)
- Final video duration: +1 second per expression (transition segment)

**Effort Estimate:**
- Medium (1-3 days)

## Problem Description

### Current State
**Location:** `langflix/core/video_editor.py` (lines ~200-300 for `create_educational_sequence`, ~2200-2500 for `create_short_format_video`)

Currently, context videos and expression videos are directly concatenated without any transition segment:

**Long-form video structure:**
- Context video → Expression repeat (direct concatenation)
- No visual transition between context and expression

**Short-form video structure:**
- Context video → Expression repeat (direct concatenation)
- No visual transition between context and expression

**Issues:**
1. Abrupt transition between context and expression segments
2. No visual indicator separating context from expression learning segment
3. No audio cue to signal transition to expression repetition
4. Professional video production standards suggest smooth transitions

### Root Cause Analysis
- Initial implementation focused on functional correctness
- Transition feature was not part of MVP requirements
- Transition assets (images and sound effects) are now available
- Previous xfade-based transition attempt failed due to A-V sync issues (see TICKET-001, ADR-015)

### Evidence
- Transition images exist: `assets/transition_9_16.png` (short-form), `assets/transition_16_9.png` (long-form)
- Sound effect exists: `assets/sound_effect.mp3`
- Current code uses `concat_filter_with_explicit_map()` for concatenation (line 232 in video_editor.py)
- Configuration has `context_to_expression` transition but it's disabled (`type: "none"`) due to A-V sync issues

## Proposed Solution

### Approach
Add a 1-second transition segment between context video and expression repeat:
1. Create transition video from static image (1 second duration)
2. Add sound effect to transition segment
3. Structure: `context_video → transition_video (1s) → expression_repeat`
4. Select appropriate transition image based on video format (9:16 for short-form, 16:9 for long-form)
5. Mix transition sound effect with any existing audio from context/expression
6. **CRITICAL**: Ensure transition video matches source video parameters (codec, resolution, frame rate) to allow concatenation

### Implementation Details

#### Step 1: Add Configuration
```yaml
# langflix/config/default.yaml
transitions:
  # ... existing transition settings ...
  
  # Context to expression transition
  context_to_expression_transition:
    enabled: true
    duration: 1.0  # 1 second transition
    image_path_9_16: "assets/transition_9_16.png"  # For short-form
    image_path_16_9: "assets/transition_16_9.png"  # For long-form
    sound_effect_path: "assets/sound_effect.mp3"
    sound_effect_volume: 0.5  # Volume level (0.0-1.0)
```

#### Step 2: Create Transition Video Helper Method
```python
# langflix/core/video_editor.py
def _create_transition_video(
    self, 
    duration: float, 
    image_path: str, 
    sound_effect_path: str,
    output_path: Path,
    source_video_path: str,  # Use source video params to match codec/resolution
    fps: int = 25
) -> str:
    """
    Create transition video from static image with sound effect.
    
    Args:
        duration: Transition duration in seconds
        image_path: Path to transition image
        sound_effect_path: Path to sound effect MP3
        output_path: Output video path
        source_video_path: Source video to match codec/resolution/params
        fps: Output frame rate
        
    Returns:
        Path to created transition video
    """
    # Get video params from source to ensure matching
    from langflix.media.ffmpeg_utils import get_video_params, get_audio_params
    source_vp = get_video_params(source_video_path)
    source_ap = get_audio_params(source_video_path)
    
    width = source_vp.width or 1920
    height = source_vp.height or 1080
    
    # Create video from static image using loop filter
    # Duration must match exactly
    image_input = ffmpeg.input(image_path, loop=1, t=duration)
    
    # Scale image to match source resolution
    video_stream = ffmpeg.filter(image_input['v'], 'scale', width, height)
    video_stream = ffmpeg.filter(video_stream, 'fps', fps=fps)
    
    # Add sound effect, loop if needed to match duration
    sound_input = ffmpeg.input(sound_effect_path, stream_loop=-1)
    sound_stream = ffmpeg.filter(sound_input['a'], 'atrim', duration=duration)
    
    # Create silent audio if source has audio, mix sound effect
    if source_ap.sample_rate:
        # Generate silent audio to match source audio params
        silent_audio = ffmpeg.input('anullsrc=r={}:cl=stereo'.format(source_ap.sample_rate), 
                                   f='lavfi', t=duration)
        # Mix sound effect with silent audio
        audio_stream = ffmpeg.filter([silent_audio['a'], sound_stream], 'amix', inputs=2)
    else:
        audio_stream = sound_stream
    
    # Output with same codec params as source
    # CRITICAL: Use same codec/resolution to allow demuxer concat if possible
    output_args = make_video_encode_args_from_source(source_video_path)
    output_args.update(make_audio_encode_args(normalize=True))
    
    # ... rest of implementation
```

#### Step 3: Modify Long-form Video Creation
**Location:** `create_educational_sequence()` in `langflix/core/video_editor.py` (line ~232)

**Current flow:**
```python
# Current: context + expression_repeat → left_side_path
concat_filter_with_explicit_map(str(context_with_subtitles), str(repeated_expression_path), str(left_side_path))
```

**New flow:**
```python
# Check if transition is enabled
from langflix import settings
transition_config = settings.get_transition_config()
if transition_config.get('context_to_expression_transition', {}).get('enabled', False):
    # 1. Create transition video (1 second) - MUST match source params
    transition_video_path = self._create_transition_video(
        duration=transition_config['context_to_expression_transition']['duration'],
        image_path=transition_config['context_to_expression_transition']['image_path_16_9'],
        sound_effect_path=transition_config['context_to_expression_transition']['sound_effect_path'],
        output_path=self.output_dir / f"temp_transition_{safe_expression}.mkv",
        source_video_path=str(context_with_subtitles),  # Match source params
        fps=25
    )
    self._register_temp_file(transition_video_path)
    
    # 2. Concatenate: context → transition → expression_repeat
    # Use concat_filter_with_explicit_map (same as current approach)
    # First: context + transition
    temp_context_transition = self.output_dir / f"temp_context_transition_{safe_expression}.mkv"
    self._register_temp_file(temp_context_transition)
    concat_filter_with_explicit_map(str(context_with_subtitles), str(transition_video_path), str(temp_context_transition))
    
    # Then: (context + transition) + expression_repeat
    concat_filter_with_explicit_map(str(temp_context_transition), str(repeated_expression_path), str(left_side_path))
else:
    # Original flow without transition
    concat_filter_with_explicit_map(str(context_with_subtitles), str(repeated_expression_path), str(left_side_path))
```

#### Step 4: Modify Short-form Video Creation
**Location:** `create_short_format_video()` in `langflix/core/video_editor.py`

**Similar modification:**
- Use `transition_9_16.png` for short-form (9:16 aspect ratio)
- Insert transition between context and expression repeat
- Final structure: `context → transition (1s) → expression_repeat → vstack with slide`

#### Step 5: Handle Sound Effect Mixing
- Transition sound effect should play during the 1-second transition
- Mix with any existing audio from context or expression segments
- Use FFmpeg audio filter (`amix`) to properly mix/overlay sound effect
- Volume control via configuration

### Alternative Approaches Considered
- **Option 1**: Use FFmpeg xfade filter for transition (similar to existing transition system)
  - **Why not chosen**: Previous attempt failed due to A-V sync issues (TICKET-001, ADR-015)
  - Xfade transitions require re-encoding which caused timestamp issues
  
- **Option 2**: Overlay transition image on last frame of context video
  - **Why not chosen**: Dedicated transition segment provides cleaner separation
  - Easier to control sound effect timing
  
- **Option 3**: Use concat_demuxer_if_uniform for all segments (copy mode)
  - **Why not chosen**: Transition video must be created (re-encoding required), so cannot use pure copy mode
  - However, transition video should match source params to minimize re-encoding in subsequent concats
  
- **Selected approach**: Dedicated 1-second transition video segment
  - Clean separation between context and expression
  - Better control over visual and audio elements
  - Easy to enable/disable via configuration
  - Matches existing concat pattern (concat_filter_with_explicit_map)

### Benefits
- **Professional video quality**: Smooth transitions enhance viewing experience
- **Clear visual separation**: Users can distinguish between context and expression segments
- **Audio cues**: Sound effect signals transition to learning segment
- **Configurable**: Can be enabled/disabled via configuration
- **Maintainable**: Reusable helper method for transition creation
- **Consistent with existing patterns**: Uses same concat approach as current code

### Risks & Considerations
- **Duration impact**: Each expression video will be 1 second longer
- **File size**: Slight increase in output video file sizes
- **Performance**: Additional FFmpeg operations for transition video creation
- **Image resolution**: Must match video resolution (16:9 for long-form, 9:16 for short-form)
- **Sound effect mixing**: Proper audio level balancing needed
- **Backward compatibility**: Feature can be disabled to maintain current behavior
- **A-V Sync**: Transition video creation requires re-encoding, but using same codec/params as source minimizes issues
- **Codec matching**: Transition video must match source codec/resolution/frame rate for proper concatenation

## Testing Strategy

### Unit Tests
- Test `_create_transition_video()` method:
  - Creates video with correct duration (1 second)
  - Uses correct image based on format (9:16 vs 16:9)
  - Includes sound effect in output
  - Proper video resolution matching format
  - Matches source video codec/params

### Integration Tests
- Test long-form video creation with transition:
  - Final video is 1 second longer than without transition
  - Transition appears between context and expression
  - Sound effect plays during transition
  - All segments properly concatenated
  - No A-V sync issues

- Test short-form video creation with transition:
  - Final video is 1 second longer than without transition
  - Transition appears between context and expression
  - Correct aspect ratio image used (9:16)
  - Vertical stack still works correctly

### Edge Cases
- Transition disabled via configuration
- Missing transition image file
- Missing sound effect file
- Different video resolutions/aspect ratios
- Transition duration configuration changes
- Source video with no audio stream
- Source video with different codecs

## Files Affected
- `langflix/core/video_editor.py`:
  - Add `_create_transition_video()` method
  - Modify `create_educational_sequence()` to include transition
  - Modify `create_short_format_video()` to include transition
  
- `langflix/config/default.yaml`:
  - Add `context_to_expression_transition` configuration section
  
- `tests/unit/test_video_editor.py`:
  - Add tests for `_create_transition_video()`
  - Add tests for transition integration in long-form
  - Add tests for transition integration in short-form

- `tests/integration/test_video_generation.py`:
  - Integration test for full video pipeline with transitions
  - Verify final video duration (+1 second)
  - Verify A-V sync is maintained

## Dependencies
- Depends on: None
- Blocks: None
- Related to: 
  - TICKET-001 (video pipeline standardization, A-V sync fixes)
  - ADR-015 (FFmpeg pipeline standardization, explains why xfade was disabled)

## References
- Related documentation: `docs/core/README_eng.md` - VideoEditor details
- ADR-015: FFmpeg pipeline standardization (explains A-V sync issues with transitions)
- FFmpeg image-to-video: https://ffmpeg.org/ffmpeg-filters.html#loop
- FFmpeg audio mixing: https://ffmpeg.org/ffmpeg-filters.html#amix

## Architect Review Questions
**For the architect to consider:**
1. Should transition be configurable per video format or global?
2. Is 1 second duration appropriate, or should it be configurable?
3. Should transition sound effect volume be configurable?
4. Should we support different transition images per language/theme?
5. Performance impact acceptable for the added video quality?
6. Should we attempt to use demuxer concat after transition creation, or is filter concat acceptable?

---
## 🏛️ Architect Review & Approval

**Reviewed by:** Architect Agent
**Review Date:** 2025-01-30
**Decision:** ✅ APPROVED (with modifications)

**Strategic Rationale:**
Why this aligns with our architectural vision:
- **User Experience Enhancement**: Professional transitions improve video quality and user engagement
- **Feature Completeness**: Addresses gap in video production quality (previously disabled due to A-V sync issues)
- **Maintainable Approach**: Uses existing concat patterns, avoids risky xfade approach
- **Configurable**: Can be disabled if issues arise, maintains backward compatibility

**Implementation Phase:** Phase 1 - Sprint 1 (Medium Priority)
**Sequence Order:** #4 in implementation queue (after critical fixes)

**Architectural Guidance:**
Key considerations for implementation:

1. **Codec Matching Critical**:
   - Transition video MUST match source video codec, resolution, frame rate, pixel format
   - Use `get_video_params()` and `get_audio_params()` from source video
   - This ensures concat works properly and minimizes re-encoding issues

2. **A-V Sync Considerations**:
   - Current code uses `concat_filter_with_explicit_map` which applies setpts/asetpts
   - This approach is acceptable (already in use)
   - Transition video creation will require re-encoding, but subsequent concat can use existing pattern
   - Monitor for A-V sync issues in testing

3. **Configuration Design**:
   - Add `context_to_expression_transition` section under existing `transitions` config
   - Keep `enabled: true` as default, but allow easy disabling
   - Add volume control for sound effect (0.0-1.0)

4. **Implementation Pattern**:
   - Follow existing `concat_filter_with_explicit_map` pattern (line 232 in video_editor.py)
   - Use same temp file management with `_register_temp_file()`
   - Match existing error handling patterns

5. **Performance Optimization**:
   - Transition video creation is one-time per expression
   - Could cache transition videos if same image/params used across expressions
   - But keep it simple for v1 - optimize later if needed

**Dependencies:**
- **Must complete first:** None
- **Should complete first:** None
- **Blocks:** None
- **Related work:** 
  - TICKET-001 (understanding A-V sync fixes)
  - ADR-015 (FFmpeg pipeline patterns)

**Risk Mitigation:**
- **Risk:** A-V sync issues from transition video creation
  - **Mitigation:** Match source video params exactly, use existing concat pattern with setpts/asetpts
  - **Testing:** Comprehensive A-V sync tests required
- **Risk:** Performance impact from additional FFmpeg operations
  - **Mitigation:** One-time transition creation per expression, acceptable for UX improvement
  - **Monitoring:** Profile if performance becomes issue
- **Risk:** Missing assets (transition images, sound effects)
  - **Mitigation:** Graceful fallback - disable transition if assets missing, log warning
- **Rollback Strategy:** Feature can be disabled via config (`enabled: false`), no breaking changes

**Enhanced Success Criteria:**
Beyond original ticket criteria:
- [ ] Transition video matches source codec/resolution/frame rate exactly
- [ ] A-V sync maintained (no audio lag/drift)
- [ ] Graceful fallback if assets missing (disable transition, continue)
- [ ] Sound effect volume configurable (default 0.5)
- [ ] Performance impact acceptable (< 2 seconds per expression)
- [ ] Works with both long-form (16:9) and short-form (9:16)
- [ ] Configuration properly integrated with existing transition system

**Alternative Approaches Considered:**
- **Original proposal:** Dedicated transition video segment
  - **Selected:** ✅ Best approach - clean, controllable, matches existing patterns
- **Alternative 1: xfade filter (re-attempt)**
  - **Why not chosen:** Previously failed due to A-V sync issues (TICKET-001). This approach avoids that.
- **Alternative 2: Overlay on last frame**
  - **Why not chosen:** Dedicated segment provides better control and cleaner separation

**Implementation Notes:**
- Start by: Creating `_create_transition_video()` helper method
- Watch out for: Codec/resolution mismatches - must probe source video first
- Coordinate with: Test thoroughly with different video formats and codecs
- Reference: `langflix/media/ffmpeg_utils.py` for concat patterns, `langflix/core/video_editor.py:232` for current concat usage

**Estimated Timeline:** 2-3 days (refined from 1-3 days)
- Day 1: Implement `_create_transition_video()` method, add configuration
- Day 2: Integrate into long-form and short-form creation, sound effect mixing
- Day 3: Testing, A-V sync verification, edge cases, documentation

**Recommended Owner:** Senior backend engineer with FFmpeg experience

**Important Notes:**
- This feature was previously attempted with xfade but disabled due to A-V sync issues
- Current approach (dedicated transition video) avoids xfade problems
- Must ensure transition video matches source params to allow proper concatenation
- Monitor for A-V sync issues during implementation and testing
