# [TICKET-039] Short-form Centered Video with Letterbox

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
- Improves short-form video viewing experience with centered video layout
- Better mobile viewing (centered video is more natural)
- Professional appearance with letterboxing maintaining original aspect ratio

**Technical Impact:**
- Changes core short-form video construction logic in `create_short_format_video()`
- Replaces vstack with centered video + letterbox + sequential concatenation
- Requires FFmpeg pad filter for letterboxing
- Affects: `langflix/core/video_editor.py` (lines 3467-3474)

**Effort Estimate:**
- Medium (1-3 days)

## Problem Description

### Current State
**Location:** `langflix/core/video_editor.py:3467-3474`

Current implementation uses top-bottom layout (vstack):
- Top half: context video → expression repeat
- Bottom half: educational slide
- Both visible simultaneously

```python
# Step 6: Use vstack to create vertical layout (short-form) - same approach as long-form hstack
# Top: context → expression repeat, Bottom: educational slide
logger.info("Creating short-form vertical layout with vstack")
vstack_temp_path = self.output_dir / f"temp_vstack_short_{safe_expression}.mkv"
self._register_temp_file(vstack_temp_path)
# Track vstack file for preservation (TICKET-029) - this is the complete individual expression video
self.short_format_temp_files.append(vstack_temp_path)
vstack_keep_width(str(concatenated_video_path), str(slide_path), str(vstack_temp_path))
```

### Root Cause Analysis
- Initial implementation used top-bottom layout for educational purposes
- User feedback indicates preference for centered video with letterbox
- Sequential layout provides better viewing experience

### Evidence
- User requirement: "short form: video - locate this in the middle of screen (vertical ratio) -> (after video done, transition to) education slide"
- Video should maintain original aspect ratio with letterbox (black bars top/bottom)

## Proposed Solution

### Approach
1. Replace `vstack_keep_width()` with centered video layout using FFmpeg `pad` filter
2. Add letterboxing (black bars top/bottom) to maintain video aspect ratio
3. Center video vertically in 9:16 frame (1080x1920)
4. Structure: `video (centered, letterboxed) → transition → slide (full-screen)`
5. Use existing transition infrastructure

### Implementation Details

**Step 1: Create helper function for centered video with letterbox**
```python
# langflix/media/ffmpeg_utils.py
def center_video_with_letterbox(
    input_path: str,
    target_width: int,
    target_height: int,
    out_path: Path | str
) -> None:
    """
    Center video in target frame with letterboxing (black bars top/bottom).
    
    Maintains original video aspect ratio by adding black bars.
    For short-form: target is 1080x1920 (9:16), video is centered vertically.
    
    Args:
        input_path: Input video path
        target_width: Target frame width (e.g., 1080)
        target_height: Target frame height (e.g., 1920)
        out_path: Output video path
    """
    input_vp = get_video_params(input_path)
    video_width = input_vp.width or target_width
    video_height = input_vp.height or target_height
    
    # Calculate letterbox dimensions
    # Maintain aspect ratio, center vertically
    aspect_ratio = video_width / video_height
    
    # Calculate scaled dimensions to fit within target
    if video_width > target_width:
        # Scale to fit width
        scaled_width = target_width
        scaled_height = int(target_width / aspect_ratio)
    else:
        # Use original dimensions
        scaled_width = video_width
        scaled_height = video_height
    
    # Center calculation
    x_offset = (target_width - scaled_width) // 2
    y_offset = (target_height - scaled_height) // 2
    
    # FFmpeg pad filter: pad=width:height:x:y:color=black
    video_in = ffmpeg.input(input_path)
    video_stream = ffmpeg.filter(
        video_in['v'],
        'scale',
        scaled_width,
        scaled_height
    )
    video_stream = ffmpeg.filter(
        video_stream,
        'pad',
        target_width,
        target_height,
        x_offset,
        y_offset,
        color='black'
    )
    
    # Use audio from input
    audio_stream = video_in['a'] if 'a' in video_in else None
    
    # Output
    output_args = make_video_encode_args_from_source(input_path)
    if audio_stream:
        output_with_explicit_streams(
            video_stream,
            audio_stream,
            out_path,
            **output_args,
            **make_audio_encode_args_copy()
        )
    else:
        output_with_explicit_streams(
            video_stream,
            None,
            out_path,
            **output_args
        )
```

**Step 2: Replace vstack with centered video + sequential concatenation**
```python
# Replace lines 3467-3474 in create_short_format_video()

# Step 6: Center video with letterbox (short-form)
# TICKET-039: Changed from top-bottom (vstack) to centered video with letterbox
logger.info("Creating short-form centered video with letterbox")
letterboxed_video_path = self.output_dir / f"temp_letterboxed_short_{safe_expression}.mkv"
self._register_temp_file(letterboxed_video_path)
# Track for preservation (TICKET-029)
self.short_format_temp_files.append(letterboxed_video_path)

# Center video in 9:16 frame (1080x1920) with letterbox
from langflix.media.ffmpeg_utils import center_video_with_letterbox
center_video_with_letterbox(
    str(concatenated_video_path),
    target_width=1080,
    target_height=1920,
    out_path=str(letterboxed_video_path)
)

# Step 7: Create transition video between letterboxed video and slide
# Get transition configuration
transition_config = settings.get_transitions_config()
context_to_slide_transition = transition_config.get('context_to_slide_transition', {})

transition_enabled = context_to_slide_transition.get('enabled', True)

if transition_enabled:
    # Create transition video (9:16 format for short-form)
    transition_image_path = context_to_slide_transition.get('image_path_9_16', 'assets/transition_9_16.png')
    sound_effect_path = context_to_slide_transition.get('sound_effect_path', 'assets/sound_effect.mp3')
    transition_duration = context_to_slide_transition.get('duration', 1.0)
    sound_volume = context_to_slide_transition.get('sound_effect_volume', 0.5)
    
    # Find transition assets (reuse existing logic)
    # ... (same as long-form)
    
    if transition_image_full and sound_effect_full:
        transition_video_path = self.output_dir / f"temp_transition_short_slide_{safe_expression}.mkv"
        self._register_temp_file(transition_video_path)
        transition_video = self._create_transition_video(
            duration=transition_duration,
            image_path=str(transition_image_full),
            sound_effect_path=str(sound_effect_full),
            output_path=transition_video_path,
            source_video_path=str(letterboxed_video_path),  # Match letterboxed video resolution
            fps=25,
            sound_effect_volume=sound_volume
        )
        
        # Concatenate: letterboxed_video → transition → slide
        temp_video_transition = self.output_dir / f"temp_video_transition_short_{safe_expression}.mkv"
        self._register_temp_file(temp_video_transition)
        concat_filter_with_explicit_map(
            str(letterboxed_video_path),
            str(transition_video),
            str(temp_video_transition)
        )
        
        sequential_temp_path = self.output_dir / f"temp_sequential_short_{safe_expression}.mkv"
        self._register_temp_file(sequential_temp_path)
        concat_filter_with_explicit_map(
            str(temp_video_transition),
            str(slide_path),
            str(sequential_temp_path)
        )
        temp_output_path = sequential_temp_path
    else:
        # Fallback: direct concatenation
        sequential_temp_path = self.output_dir / f"temp_sequential_short_{safe_expression}.mkv"
        self._register_temp_file(sequential_temp_path)
        concat_filter_with_explicit_map(
            str(letterboxed_video_path),
            str(slide_path),
            str(sequential_temp_path)
        )
        temp_output_path = sequential_temp_path
else:
    # Transition disabled
    sequential_temp_path = self.output_dir / f"temp_sequential_short_{safe_expression}.mkv"
    self._register_temp_file(sequential_temp_path)
    concat_filter_with_explicit_map(
        str(letterboxed_video_path),
        str(slide_path),
        str(sequential_temp_path)
    )
    temp_output_path = sequential_temp_path

# Step 8: Apply final audio gain (unchanged)
apply_final_audio_gain(str(temp_output_path), str(output_path), gain_factor=1.69)
```

### Alternative Approaches Considered
- **Option 1**: Scale video to fill frame (crop/stretch)
  - **Why not chosen**: User explicitly requested maintaining original ratio with letterbox
  
- **Option 2**: Use scale filter with aspect ratio preservation
  - **Why not chosen**: pad filter provides better control and explicit centering

- **Selected approach**: FFmpeg pad filter with letterbox
  - Maintains original aspect ratio
  - Explicit centering control
  - Professional appearance

### Benefits
- **Better viewing experience**: Centered video is more natural
- **Aspect ratio preservation**: No distortion of original video
- **Mobile-friendly**: Centered layout works well on mobile devices
- **Professional appearance**: Letterboxing is standard practice

### Risks & Considerations
- **Letterbox calculation**: Must correctly calculate padding for various aspect ratios
- **Resolution matching**: Transition and slide must match letterboxed video resolution (1080x1920)
- **Performance**: Additional FFmpeg operation for letterboxing
- **Backward compatibility**: Breaking change - existing videos will have different layout

## Testing Strategy
- Unit tests: Test letterbox calculation for various aspect ratios
- Integration tests: Full short-form video creation with centered layout
- Manual verification: Visual inspection of video centering and letterbox
- Regression tests: Ensure audio sync is maintained

## Files Affected
- `langflix/core/video_editor.py` - `create_short_format_video()` method (lines 3467-3479)
- `langflix/media/ffmpeg_utils.py` - Add `center_video_with_letterbox()` helper function
- `langflix/config/default.yaml` - May need to add short-form transition config (reuse context_to_slide_transition)
- `tests/unit/test_video_editor.py` - Add tests for letterbox calculation
- `tests/integration/test_video_creation.py` - Integration tests

## Dependencies
- Depends on: None (uses existing transition infrastructure)
- Blocks: TICKET-040 (expression subtitle overlay needs final video structure)

## References
- FFmpeg pad filter documentation
- Existing transition implementation: `langflix/core/video_editor.py:766-861`
- Concatenation helper: `langflix/media/ffmpeg_utils.py:concat_filter_with_explicit_map`

## Architect Review Questions
1. Should letterbox color be configurable (currently black)?
2. Should we support different target resolutions for short-form?
3. Are there performance concerns with additional FFmpeg operations?

## Success Criteria
- [ ] Short-form videos use centered layout with letterbox
- [ ] Video maintains original aspect ratio (no distortion)
- [ ] Video is centered vertically in 9:16 frame
- [ ] Transition works smoothly between video and slide
- [ ] All segments have matching resolution (1080x1920)
- [ ] Audio sync is maintained throughout
- [ ] Tests pass for new centered layout
- [ ] Documentation updated

