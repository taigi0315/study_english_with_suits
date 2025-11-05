# [TICKET-020] Enhance Multiple Expressions Per Context for Short Videos

## Priority
- [x] High (Feature enhancement, user experience improvement)
- [ ] Critical
- [ ] Medium
- [ ] Low

## Type
- [x] Feature Enhancement
- [ ] Refactoring
- [ ] Performance Optimization
- [ ] Test Coverage
- [ ] Bug Fix
- [ ] Security Issue
- [ ] Technical Debt
- [ ] Code Duplication

## Impact Assessment
**Business Impact:**
- Better learning experience: Users can learn multiple expressions from the same context
- More engaging content: Richer educational videos with multiple expressions
- Better alignment with YouTube Shorts: Ensures context fits within 40 seconds for short videos
- Improved user satisfaction: Users can learn more efficiently from single context

**Technical Impact:**
- Multiple files need modification:
  - `langflix/templates/expression_analysis_prompt_v4.txt` - Update prompt for context duration limits
  - `langflix/core/video_editor.py` - Add context slide creation for multiple expressions
  - `langflix/settings.py` - Ensure config values are passed to prompt generation
  - `langflix/core/expression_analyzer.py` - Pass max_expressions_per_context to prompt
- New functionality: Context slide generation for multiple expressions
- No breaking changes - backward compatible

**Effort Estimate:**
- Medium (2-3 days)
  - Day 1: Update prompt templates and config passing
  - Day 2: Implement context slide generation for multiple expressions
  - Day 3: Testing and edge case handling

## Problem Description

### Current State

**Location:** Multiple files

1. **LLM Prompt Configuration** (`langflix/templates/expression_analysis_prompt_v4.txt`)
   - Currently prompts for 1-3 expressions per context
   - No explicit duration limit for context in short video scenarios
   - Context duration guidance is 25-45 seconds (general, not short-video specific)

2. **Multiple Expressions Support** (`langflix/config/default.yaml:258`)
   - `max_expressions_per_context: 3` already exists in config
   - `allow_multiple_expressions: true` enables the feature
   - But this value is not passed to LLM prompt generation

3. **Slide Generation** (`langflix/core/video_editor.py:1202`)
   - `_create_educational_slide()` creates slides for individual expressions
   - No context slide that displays multiple expressions during context video playback
   - Each expression gets its own educational slide, but no unified context slide

4. **Short Video Constraints** (`tickets/approved/TICKET-019`)
   - Short videos must be under 60 seconds (1 minute)
   - But no specific guidance for context duration within short videos
   - Current context can be up to 45 seconds, leaving only 15 seconds for expressions

**Problem:**
1. **Context Duration Too Long for Short Videos**: 
   - Short videos must be ≤ 60 seconds total
   - Context can currently be 25-45 seconds
   - If context is 45 seconds, only 15 seconds remain for expressions (insufficient for quality learning)
   - Need to limit context to ≤ 40 seconds for short videos, leaving 20 seconds for expressions

2. **Missing Context Slide for Multiple Expressions**:
   - When multiple expressions share the same context, there's no unified slide showing all expressions
   - Users see individual expression slides, but not a combined view during context playback
   - Need a context slide that displays all expressions from the same context together

3. **Config Not Passed to Prompt**:
   - `max_expressions_per_context` exists in config but isn't used in prompt generation
   - LLM prompt should explicitly know the max expressions limit from config
   - Current prompt says "1-3 expressions" but doesn't use config value

4. **No Explicit Short Video Context Duration Guidance**:
   - Prompt doesn't distinguish between short video and regular video context requirements
   - Short videos need stricter context duration limits (≤ 40 seconds)
   - Need to update prompt to find contexts ≤ 40 seconds when processing short videos

### Root Cause Analysis

1. **Short Video Context Duration**:
   - Initial implementation focused on general educational videos (longer format)
   - Short video support was added later (ADR-006, TICKET-019)
   - Context duration constraints weren't adjusted for short video format
   - Short videos need tighter time constraints: 40s context + 20s expressions = 60s total

2. **Missing Context Slide**:
   - Original design focused on individual expression slides
   - Multiple expressions per context was added later (ADR-016, TICKET-008)
   - Context slide feature wasn't part of the original multiple expressions implementation
   - Need to add unified context slide for better UX

3. **Config-to-Prompt Disconnect**:
   - Config value exists but isn't passed through to prompt generation
   - Prompt has hardcoded "1-3 expressions" instead of using config
   - Need to inject config value into prompt template

### Evidence

1. **Short Video Duration Requirements**:
   - TICKET-019: Short videos must be ≤ 60 seconds
   - ADR-006: Short video architecture targets ~120 seconds (but individual expressions should be ≤ 60s)
   - Current context can be 25-45 seconds, which is too long for short video format

2. **User Feedback** (from ticket):
   - "multiple expression is good, give audience chance to learn multiple expression in one context"
   - "short video should be under 1 minute, context should not longer than 40 sec, 20 seconds can be used for expressions"

3. **Current Implementation Gaps**:
   - No context slide for multiple expressions
   - Config value not used in prompt
   - No short-video-specific context duration guidance

## Proposed Solution

### Approach

1. **Update LLM Prompt for Short Video Context Duration**:
   - Add explicit guidance: "For short videos, context must be ≤ 40 seconds"
   - Update prompt to use `max_expressions_per_context` from config
   - Clarify that expressions can be 1 to max (from config), not forced to find max

2. **Pass Config to Prompt Generation**:
   - Update `expression_analyzer.py` to read `max_expressions_per_context` from config
   - Pass this value to prompt template
   - Replace hardcoded "1-3" with dynamic config value

3. **Create Context Slide for Multiple Expressions**:
   - New method: `_create_context_slide_for_multiple_expressions()`
   - Display format:
     ```
     * expression 1
       translation 1
     * expression 2
       translation 2
     * expression 3
       translation 3
     ```
   - Slide shown during context video playback
   - Only created when there are 2+ expressions in the same context

4. **Update Video Processing Pipeline**:
   - Detect when multiple expressions share same context
   - Generate context slide before context video
   - Insert context slide into video timeline
   - Ensure context slide duration matches context video duration

### Implementation Details

#### 1. Update Prompt Template

**File:** `langflix/templates/expression_analysis_prompt_v4.txt`

Add section after line ~230:

```text
**SHORT VIDEO CONTEXT DURATION (if applicable):**

For short videos (≤ 60 seconds total):
- Context must be ≤ 40 seconds
- Remaining ~20 seconds reserved for expression slides
- When finding contexts, prioritize segments that are ≤ 40 seconds
- If no suitable context ≤ 40 seconds exists, use the best available context but note it may not fit short video format

**EXPRESSION COUNT:**
- Find 1 to {max_expressions_per_context} expressions per context
- Do NOT force yourself to find {max_expressions_per_context} expressions
- Quality over quantity: Only select expressions that are truly valuable
- If you find 1 excellent expression, that's better than forcing 3 mediocre ones
- The goal is to find the BEST expressions, not necessarily the maximum number
```

Update line ~356 (FINAL CHECKLIST):
```text
- ✓ Context is 25-45 seconds for regular videos (or ≤ 40 seconds for short videos)
- ✓ 1-{max_expressions_per_context} expressions total (minimum 1, maximum {max_expressions_per_context})
```

#### 2. Update Expression Analyzer to Pass Config

**File:** `langflix/core/expression_analyzer.py`

Locate prompt generation method and update:

```python
def _generate_prompt(self, subtitle_text: str, ...) -> str:
    """Generate prompt for expression analysis"""
    # Get max expressions from config
    max_expressions = settings.get_max_expressions_per_context()
    
    # Load prompt template
    template_path = settings.get_expression_template_path()
    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()
    
    # Replace placeholder in template
    prompt = template.format(
        max_expressions_per_context=max_expressions,
        # ... other format parameters
    )
    
    return prompt
```

#### 3. Create Context Slide Generator

**File:** `langflix/core/video_editor.py`

Add new method:

```python
def _create_context_slide_for_multiple_expressions(
    self,
    expressions: List[ExpressionAnalysis],
    context_duration: float,
    output_path: Optional[Path] = None
) -> str:
    """
    Create a slide displaying multiple expressions from the same context.
    
    This slide is shown during context video playback to show all expressions
    that will be learned from this context.
    
    Args:
        expressions: List of expressions from the same context (2+ required)
        context_duration: Duration of context video (seconds)
        output_path: Optional output path, defaults to temp file
        
    Returns:
        str: Path to created slide video file
        
    Format:
        * expression 1
          translation 1
        * expression 2
          translation 2
        * expression 3
          translation 3
    """
    if len(expressions) < 2:
        raise ValueError("Context slide requires at least 2 expressions")
    
    # Validate all expressions share same context
    first_context = (expressions[0].context_start_time, expressions[0].context_end_time)
    for expr in expressions[1:]:
        if (expr.context_start_time, expr.context_end_time) != first_context:
            raise ValueError("All expressions must share the same context times")
    
    # Create slide content
    slide_lines = []
    for expr in expressions:
        slide_lines.append(f"* {expr.expression}")
        slide_lines.append(f"  {expr.expression_translation}")
    
    slide_text = "\n".join(slide_lines)
    
    # Generate slide with same duration as context
    # Use existing slide creation infrastructure
    # ... implementation details ...
```

#### 4. Update Video Processing Pipeline

**File:** `langflix/api/tasks/processing.py` or `langflix/main.py`

Update processing flow:

```python
# After grouping expressions by context
for group in expression_groups:
    if len(group.expressions) >= 2:
        # Create context slide for multiple expressions
        context_slide = video_editor._create_context_slide_for_multiple_expressions(
            expressions=group.expressions,
            context_duration=group.context_duration
        )
        
        # Insert context slide before context video
        # ... video timeline assembly ...
    
    # Continue with existing expression processing...
```

### Benefits

1. **Better Learning Experience**:
   - Users see all expressions from a context at once
   - Better understanding of how expressions relate to each other
   - More efficient learning from single context

2. **Short Video Compatibility**:
   - Context duration ≤ 40 seconds ensures short videos fit YouTube Shorts format
   - 20 seconds reserved for expressions provides adequate learning time
   - Clear guidance helps LLM find appropriate contexts

3. **Configurability**:
   - `max_expressions_per_context` now actually used in prompt
   - Admins can adjust limit without code changes
   - More flexible system configuration

4. **Quality Control**:
   - LLM explicitly told not to force maximum expressions
   - Quality over quantity approach
   - Better expression selection

5. **Unified User Experience**:
   - Context slide provides overview of what will be learned
   - Better visual organization for multiple expressions
   - More professional educational content

### Risks & Considerations

1. **Risk**: Context slide creation adds processing time
   - **Mitigation**: Only create for 2+ expressions, use efficient rendering
   - **Impact**: Minimal, only for multi-expression contexts

2. **Risk**: Slide duration matching context video duration
   - **Mitigation**: Ensure slide duration exactly matches context video
   - **Impact**: Visual sync issues if not handled correctly

3. **Risk**: Prompt changes may affect expression quality
   - **Mitigation**: Test with various content, adjust prompt if needed
   - **Impact**: Temporary, can be refined

4. **Risk**: Breaking existing single-expression workflows
   - **Mitigation**: Context slide only created for 2+ expressions, backward compatible
   - **Impact**: None - single expressions work as before

5. **Risk**: Config value changes may confuse LLM
   - **Mitigation**: Validate config value (1-5 reasonable range), provide clear guidance
   - **Impact**: Low - default is 3, which is reasonable

## Testing Strategy

### Unit Tests

1. **Prompt Generation**:
   - Test that `max_expressions_per_context` is correctly injected into prompt
   - Test with different config values (1, 3, 5)
   - Verify short video context duration guidance appears in prompt

2. **Context Slide Creation**:
   - Test with 2 expressions
   - Test with 3 expressions
   - Test with expressions that don't share context (should fail)
   - Test slide duration matches context duration
   - Test slide text formatting

3. **Expression Grouping**:
   - Test that expressions are correctly grouped by context
   - Test that context slides are only created for 2+ expressions
   - Test single expression workflows (no context slide)

### Integration Tests

1. **End-to-End Short Video**:
   - Process video with multiple expressions per context
   - Verify context duration ≤ 40 seconds
   - Verify context slide is created and inserted
   - Verify final video duration ≤ 60 seconds

2. **Prompt LLM Integration**:
   - Test that LLM respects max_expressions_per_context limit
   - Test that LLM finds contexts ≤ 40 seconds for short videos
   - Test that LLM doesn't force maximum expressions

### Edge Cases

1. **Single Expression** (no context slide needed)
2. **Context exactly 40 seconds** (boundary test)
3. **Context 41 seconds** (should still work but warn)
4. **Max expressions = 1** (should work like single expression)
5. **Max expressions = 5** (test upper limit)

## Files Affected

**Modified Files:**
- `langflix/templates/expression_analysis_prompt_v4.txt` - Add short video context duration guidance and use config value
- `langflix/core/expression_analyzer.py` - Pass `max_expressions_per_context` to prompt template
- `langflix/core/video_editor.py` - Add `_create_context_slide_for_multiple_expressions()` method
- `langflix/api/tasks/processing.py` or `langflix/main.py` - Update pipeline to create context slides
- `langflix/config/default.yaml` - Document new prompt behavior (no code changes, just documentation)

**New Test Files:**
- `tests/unit/test_context_slide_generation.py` - Unit tests for context slide creation
- `tests/integration/test_multiple_expressions_context_slide.py` - Integration tests

**Updated Test Files:**
- `tests/unit/test_expression_analyzer.py` - Test config passing to prompt
- `tests/integration/test_end_to_end_video_generation.py` - Test context slide in pipeline

## Dependencies

- Depends on: TICKET-008 (Multiple expressions per context - already implemented)
- Depends on: TICKET-019 (Short video duration limit - already implemented)
- Blocks: None
- Related to: ADR-016 (Multiple expressions per context architecture)

## References

- **ADR-016**: Multiple Expressions Per Context Support
- **TICKET-008**: Support Multiple Expressions Per Context (done)
- **TICKET-019**: Reduce Short-Form Video Duration Limit (done)
- **ADR-006**: Short Video Architecture
- Current prompt: `langflix/templates/expression_analysis_prompt_v4.txt`
- Expression analyzer: `langflix/core/expression_analyzer.py`
- Video editor: `langflix/core/video_editor.py`
- Config: `langflix/config/default.yaml:258`

## Architect Review Questions

1. Should context slide be optional (configurable)?
2. Should we support different context duration limits for different video types?
3. Should context slide have audio narration or just visual?
4. How should context slide be styled (background, fonts, layout)?

## Success Criteria

- [ ] LLM prompt includes `max_expressions_per_context` from config
- [ ] LLM prompt explicitly guides for ≤ 40 second contexts in short videos
- [ ] Context slides are created for contexts with 2+ expressions
- [ ] Context slide displays all expressions in format: `* expression\n  translation`
- [ ] Context slide duration matches context video duration
- [ ] Short videos with multiple expressions have context ≤ 40 seconds
- [ ] Single expression workflows unchanged (backward compatible)
- [ ] All tests pass (unit, integration, edge cases)
- [ ] Documentation updated

---
## 🏛️ Architect Review & Approval

**Reviewed by:** Architect Agent
**Review Date:** 2025-01-30
**Decision:** ✅ APPROVED

**Strategic Rationale:**
Why this aligns with our architectural vision:
- **Enhances Learning Experience**: Multiple expressions per context is a core educational feature. This enhancement makes it more usable and aligned with short video format.
- **Improves Content Quality**: Better context duration limits ensure short videos meet YouTube Shorts requirements while maintaining educational value.
- **Configurability**: Using config values in prompts makes the system more flexible and maintainable.
- **User Experience**: Context slide provides better visual organization and learning flow for multiple expressions.

**Implementation Phase:** Phase 1 - Sprint 1 (Next 2 weeks)
**Sequence Order:** #1 in implementation queue (after TICKET-021, TICKET-022, TICKET-023 completed)

**Architectural Guidance:**
Key considerations for implementation:
- **Slide Duration Matching**: Critical - context slide must exactly match context video duration for proper sync
- **Backward Compatibility**: Ensure single-expression workflows are completely unchanged
- **Config Validation**: Validate `max_expressions_per_context` is in reasonable range (1-5)
- **Performance**: Context slide creation should be efficient - only create when needed (2+ expressions)
- **Template Flexibility**: Use template formatting for max_expressions_per_context to allow future config changes

**Dependencies:**
- **Must complete first:** None (TICKET-008 and TICKET-019 already done)
- **Should complete first:** None
- **Blocks:** None
- **Related work:** TICKET-008 (multiple expressions), TICKET-019 (short video duration)

**Risk Mitigation:**
- **Risk:** Context slide duration mismatch
  - **Mitigation:** Test thoroughly, use exact context duration for slide, add validation
- **Risk:** Prompt changes affect expression quality
  - **Mitigation:** Test with diverse content, monitor LLM output quality, iterate on prompt if needed
- **Risk:** Performance impact from slide generation
  - **Mitigation:** Only create for 2+ expressions, optimize rendering, consider caching

**Enhanced Success Criteria:**
Beyond original ticket criteria:
- [ ] Context slide rendering time < 2 seconds per slide
- [ ] Slide text is readable and properly formatted
- [ ] Config validation prevents invalid max_expressions_per_context values
- [ ] Documentation updated in `docs/core/README_eng.md` and `docs/core/README_kor.md`
- [ ] Prompt template changes tested with real LLM calls

**Alternative Approaches Considered:**
- **Original proposal:** Update prompt, pass config, create context slide
  - **Selected:** ✅ Best approach - addresses all requirements
- **Alternative 1:** Separate short video prompt template
  - **Why not chosen:** More maintenance overhead, single template with conditional guidance is cleaner
- **Alternative 2:** Don't create context slide, just update prompt
  - **Why not chosen:** Context slide provides significant UX improvement, worth the implementation effort

**Implementation Notes:**
- Start by: Updating prompt template to include config value and short video guidance
- Watch out for: Slide duration must exactly match context video duration
- Coordinate with: Test with real videos to ensure context slides look good
- Reference: `langflix/core/video_editor.py` for existing slide creation patterns

**Estimated Timeline:** 2-3 days (refined from Medium estimate)
- Day 1: Update prompt template and config passing (4-6 hours)
- Day 2: Implement context slide creation (6-8 hours)
- Day 3: Integration and testing (4-6 hours)

**Recommended Owner:** Senior engineer with video processing experience

