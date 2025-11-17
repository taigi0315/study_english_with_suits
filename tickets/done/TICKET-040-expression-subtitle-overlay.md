# [TICKET-040] Expression Subtitle Overlay at Top

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
- Improves learning experience by highlighting expression text at top of video
- Makes expressions more visible and easier to learn
- Yellow color draws attention to important content

**Technical Impact:**
- Adds dual subtitle layer support (top expression + bottom original)
- Requires expression-only subtitle SRT generation
- Affects: `langflix/core/video_editor.py` - `_add_subtitles_to_context()` method
- Affects: `langflix/core/subtitle_processor.py` - Add expression subtitle generation
- Affects: `langflix/subtitles/overlay.py` - Add dual subtitle layer support

**Effort Estimate:**
- Medium (1-3 days)

## Problem Description

### Current State
**Location:** `langflix/core/video_editor.py:1135-1212` (`_add_subtitles_to_context`)

Current implementation:
- Only applies original subtitles (dual-language) at bottom
- Uses `apply_subtitles_with_file()` from `langflix/subtitles/overlay.py`
- No expression-specific subtitle overlay

### Root Cause Analysis
- Initial implementation focused on original dialogue subtitles only
- User feedback indicates need for expression highlighting
- Expression subtitle helps learners focus on key phrases

### Evidence
- User requirement: "subtitle: original subtitle (current location, bottom) || expression subtitle with yellow top of video"
- Expression subtitle should show only during expression repeat segments

## Proposed Solution

### Approach
1. Generate expression-only subtitle SRT file with timestamps for expression segment
2. Apply expression subtitle at top of video (yellow color, bold)
3. Keep existing original subtitles at bottom
4. Expression subtitle shows only during expression repeat segments
5. Use FFmpeg `subtitles` filter with positioning and styling

### Implementation Details

**Step 1: Add method to generate expression-only subtitle**
```python
# langflix/core/subtitle_processor.py
def generate_expression_subtitle_srt(
    self,
    expression: ExpressionAnalysis,
    expression_start_relative: float,
    expression_end_relative: float
) -> str:
    """
    Generate SRT file with expression text only, positioned at top.
    
    Args:
        expression: ExpressionAnalysis object
        expression_start_relative: Expression start time relative to context (seconds)
        expression_end_relative: Expression end time relative to context (seconds)
        
    Returns:
        SRT formatted string with expression text
    """
    srt_lines = []
    
    # Single subtitle entry for expression
    srt_lines.append("1")
    
    # Format times
    start_time_str = self._seconds_to_srt_time(expression_start_relative)
    end_time_str = self._seconds_to_srt_time(expression_end_relative)
    srt_lines.append(f"{start_time_str} --> {end_time_str}")
    
    # Expression text (not dialogue)
    srt_lines.append(expression.expression)
    srt_lines.append("")
    
    return "\n".join(srt_lines)
```

**Step 2: Update subtitle overlay to support dual layers**
```python
# langflix/subtitles/overlay.py
def apply_dual_subtitle_layers(
    video_path: str,
    original_subtitle_path: str,
    expression_subtitle_path: str,
    output_path: str,
    expression_start_relative: float,
    expression_end_relative: float,
    repeat_count: int
) -> None:
    """
    Apply two subtitle layers:
    - Original subtitles at bottom (existing behavior)
    - Expression subtitle at top (yellow, bold) during expression segments only
    
    Args:
        video_path: Input video path
        original_subtitle_path: Path to original dual-language subtitle SRT
        expression_subtitle_path: Path to expression-only subtitle SRT
        output_path: Output video path
        expression_start_relative: Expression start time relative to context (seconds)
        expression_end_relative: Expression end time relative to context (seconds)
        repeat_count: Number of times expression is repeated
    """
    # Calculate expression segment duration
    expression_duration = expression_end_relative - expression_start_relative
    
    # Create filter complex for dual subtitles
    # 1. Original subtitles at bottom (existing)
    # 2. Expression subtitle at top (yellow, bold) during expression segments
    
    # FFmpeg subtitles filter with force_style for positioning
    # Top subtitle: Alignment=8 (top center), PrimaryColour=&H00FFFF00 (yellow), Bold=1
    # Bottom subtitle: Alignment=2 (bottom center) - default
```

**Step 3: Update _add_subtitles_to_context to use dual layers**
```python
# langflix/core/video_editor.py - _add_subtitles_to_context()
# After creating original subtitle file, also create expression subtitle

# Generate expression-only subtitle SRT
expression_start_relative = self._time_to_seconds(expression.expression_start_time) - \
                           self._time_to_seconds(expression.context_start_time)
expression_end_relative = self._time_to_seconds(expression.expression_end_time) - \
                         self._time_to_seconds(expression.context_start_time)

# Calculate total expression duration including repeats
from langflix import settings
repeat_count = settings.get_expression_repeat_count()
expression_duration = expression_end_relative - expression_start_relative
total_expression_duration = expression_duration * repeat_count

# Generate expression subtitle SRT
expression_subtitle_content = self.subtitle_processor.generate_expression_subtitle_srt(
    expression,
    expression_start_relative,
    expression_start_relative + total_expression_duration  # Include all repeats
)

# Save expression subtitle to temp file
expression_subtitle_path = self.output_dir / f"temp_expression_subtitle_{safe_expression}.srt"
expression_subtitle_path.write_text(expression_subtitle_content, encoding='utf-8')
self._register_temp_file(expression_subtitle_path)

# Apply dual subtitle layers
from langflix.subtitles.overlay import apply_dual_subtitle_layers
apply_dual_subtitle_layers(
    str(video_path),
    str(temp_sub),
    str(expression_subtitle_path),
    str(output_path),
    expression_start_relative,
    expression_start_relative + total_expression_duration,
    repeat_count
)
```

### Alternative Approaches Considered
- **Option 1**: Use drawtext filter for expression text
  - **Why not chosen**: SRT subtitles provide better timing control and styling
  
- **Option 2**: Overlay expression text as image
  - **Why not chosen**: More complex, requires image generation
  
- **Selected approach**: Dual subtitle layers with FFmpeg subtitles filter
  - Reuses existing subtitle infrastructure
  - Better timing control
  - Standard subtitle styling

### Benefits
- **Better learning experience**: Expression highlighted at top
- **Clear visibility**: Yellow color draws attention
- **Precise timing**: Expression subtitle shows only during expression segments
- **Reuses existing code**: Uses proven subtitle infrastructure

### Risks & Considerations
- **Subtitle timing**: Expression subtitle must align precisely with expression segments
- **Performance**: Additional subtitle layer may impact encoding time
- **Style compatibility**: Must ensure yellow color is visible on all backgrounds
- **Repeat segments**: Expression subtitle must cover all repeat segments

## Testing Strategy
- Unit tests: Test expression subtitle SRT generation with correct timestamps
- Integration tests: Full video creation with dual subtitle layers
- Manual verification: Visual inspection of subtitle positioning and timing
- Regression tests: Ensure original subtitles still work correctly

## Files Affected
- `langflix/core/video_editor.py` - `_add_subtitles_to_context()` method
- `langflix/core/subtitle_processor.py` - Add `generate_expression_subtitle_srt()` method
- `langflix/subtitles/overlay.py` - Add `apply_dual_subtitle_layers()` method
- `tests/unit/test_subtitle_processor.py` - Add tests for expression subtitle generation
- `tests/integration/test_video_creation.py` - Integration tests

## Dependencies
- Depends on: TICKET-038, TICKET-039 (needs final video structure)
- Blocks: None

## References
- FFmpeg subtitles filter documentation
- Existing subtitle overlay: `langflix/subtitles/overlay.py`
- Subtitle processor: `langflix/core/subtitle_processor.py`

## Architect Review Questions
1. Should expression subtitle color be configurable?
2. Should expression subtitle position be configurable (top-left, top-center, top-right)?
3. Are there performance concerns with dual subtitle layers?

## Success Criteria
- [ ] Expression subtitles appear at top (yellow, bold) during expression segments only
- [ ] Original subtitles remain at bottom (unchanged)
- [ ] Expression subtitle timing aligns with expression repeat segments
- [ ] Both subtitle layers work correctly together
- [ ] Tests pass for dual subtitle functionality
- [ ] Documentation updated

