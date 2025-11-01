# ADR-016: Multiple Expressions Per Context Support

**Date:** 2025-01-30  
**Status:** Accepted  
**Deciders:** Development Team  
**Related Ticket:** TICKET-008

## Context

Currently, LangFlix extracts only one expression per context time range. However, a single dialogue segment or scene can contain multiple valuable expressions that learners would benefit from. The system already prompts the LLM to find "1-3 expressions" but processes them as if each comes from a separate context, leading to:

1. **Inefficiency**: Same context video clip is extracted multiple times when multiple expressions share the same context
2. **Lost value**: Some valuable expressions may be missed if only one is selected per context
3. **Poor resource usage**: Duplicate video processing wastes storage and processing time

Example scenario:
- Context: "I'll knock it out of the park for you, and you can count on it." (00:05:30 - 00:06:10)
  - Expression 1: "knock it out of the park" (00:05:35 - 00:05:45)
  - Expression 2: "count on it" (00:05:50 - 00:05:55)
  - Both expressions are valuable and share the same context - both should be extracted and processed

## Decision

We will implement support for multiple expressions per context through a phased approach:

### Phase 1: Grouping + Separate Mode (Current Implementation)
- Add `ExpressionGroup` model to group expressions sharing same context times
- Implement grouping logic to automatically group expressions by context
- Use shared context video clips (one clip per group, reused by all expressions in group)
- Each expression still gets its own educational video (separate mode)
- Backward compatible: Single expressions automatically become groups of 1

### Phase 2: Combined Mode (Future)
- Optional mode to create one educational video containing multiple expressions from same context
- More complex video editing logic
- Can be implemented after Phase 1 is proven and stable

## Implementation Strategy

### Phase 1: Core Grouping Infrastructure

1. **ExpressionGroup Model**
   - Groups expressions with matching `context_start_time` and `context_end_time`
   - Contains list of `ExpressionAnalysis` objects
   - Validates that all expressions in group share same context times

2. **Grouping Logic**
   - Function: `group_expressions_by_context(expressions) -> List[ExpressionGroup]`
   - Groups by exact time match (no tolerance initially)
   - Handles edge cases (empty lists, single expressions)

3. **Video Processing**
   - Extract ONE context clip per group (shared by all expressions)
   - Create separate subtitle files for each expression
   - Generate separate educational videos for each expression (separate mode)
   - Cache context clips to avoid duplicate extractions

4. **Configuration**
   - `allow_multiple_expressions: true` - Enable/disable feature
   - `max_expressions_per_context: 3` - Maximum expressions allowed per context
   - `educational_video_mode: "separate"` - Mode (separate or combined for Phase 2)

### Phase 2: Combined Mode (Future)

- Single educational video containing all expressions from a group
- More complex subtitle and audio handling
- UI considerations for displaying multiple expressions

## Consequences

### Benefits

1. **Content Richness**: More educational value extracted from same content
2. **Processing Efficiency**: Shared context clips reduce duplicate video extractions
3. **Resource Optimization**: Lower storage usage and faster processing
4. **Flexibility**: Configurable behavior (enabled/disabled, separate/combined modes)
5. **Backward Compatibility**: Existing single-expression workflows continue to work

### Drawbacks

1. **Complexity**: Additional data model and processing logic
2. **Video Editing Complexity**: Multi-expression scenarios require more sophisticated handling
3. **Testing Overhead**: More test scenarios (1, 2, 3+ expressions per context)
4. **Potential Confusion**: Users need to understand grouping behavior

### Risks & Mitigations

1. **Risk**: Breaking existing single-expression workflows
   - **Mitigation**: Default to separate mode, single expressions = groups of 1, fully backward compatible

2. **Risk**: Video processing complexity
   - **Mitigation**: Start with separate mode only (simpler), add combined mode in Phase 2

3. **Risk**: Data migration issues
   - **Mitigation**: New feature - no migration needed, old data works as-is

4. **Risk**: Timing precision issues
   - **Mitigation**: Use exact time matching initially, can add tolerance later if needed

## Alternatives Considered

### Option 1: Always Combine Expressions
- **Pros**: Maximum efficiency
- **Cons**: Complex video editing, breaks current UX, harder to understand
- **Rejected**: Too complex, breaks user expectations

### Option 2: Always Separate (Current)
- **Pros**: Simple, predictable
- **Cons**: Misses efficiency gains, doesn't support multi-expression contexts
- **Rejected**: Doesn't solve the problem

### Option 3: Configurable Grouping (Selected)
- **Pros**: Flexibility, backward compatible, efficiency gains
- **Cons**: More complex implementation
- **Selected**: Best balance of benefits and complexity

## Implementation Details

### Data Model

```python
class ExpressionGroup(BaseModel):
    context_start_time: str
    context_end_time: str
    expressions: List[ExpressionAnalysis]  # min_length=1
    
    @validator('expressions')
    def validate_single_context(cls, v):
        # Ensure all expressions share same context times
```

### Grouping Strategy

- Key: `f"{context_start_time}_{context_end_time}"`
- Exact time match only (no floating-point tolerance initially)
- Maintains order (first expression determines group order)

### Video Processing Flow

1. Group expressions by context
2. For each group:
   - Extract ONE context clip (shared)
   - For each expression in group:
     - Create subtitle file
     - Create educational video (using shared context clip)
3. Cache context clips by context key

## References

- TICKET-008: Support Multiple Expressions Per Context
- Related code: `langflix/core/models.py`, `langflix/core/expression_analyzer.py`, `langflix/main.py`
- Prompt template: `langflix/templates/expression_analysis_prompt_v4.txt`

## Status

- **Phase 1**: In Progress
- **Phase 2**: Future

