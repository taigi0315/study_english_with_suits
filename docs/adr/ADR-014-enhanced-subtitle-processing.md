# ADR-014: Enhanced Subtitle Processing & LLM Integration

**Status**: Implemented  
**Date**: 2025-10-22  
**Authors**: Development Team  
**Related**: [ADR-013](./ADR-013-expression-configuration-architecture.md)

## Context

Following Phase 1's expression configuration foundation, Phase 2 focuses on improving the subtitle processing pipeline and enhancing the LLM-based expression extraction system. The current system lacks:

1. **Robust Subtitle Handling**:
   - No encoding detection for non-UTF-8 subtitle files
   - Limited error handling for malformed subtitle files
   - No format validation before processing
   - Generic error messages that don't help debugging

2. **Expression Quality Issues**:
   - No ranking system to prioritize valuable expressions
   - Duplicate expressions appearing in results
   - No way to control expression quality across chunks
   - Limited ability to filter expressions by educational value

3. **System Scalability**:
   - Processing all extracted expressions regardless of quality
   - No mechanism to limit expressions per video
   - Inefficient handling of large subtitle files

## Decision

We have implemented Phase 2 enhancements across three key areas:

### 1. Enhanced Subtitle Parser

#### Custom Exception Hierarchy

Created a comprehensive exception system in `langflix/core/subtitle_exceptions.py`:

```python
class SubtitleNotFoundError(FileNotFoundError)
class SubtitleFormatError(ValueError)
class SubtitleEncodingError(UnicodeError)
class SubtitleParseError(ValueError)
```

**Benefits**:
- Clear error categorization for debugging
- Detailed error messages with context
- Better error handling in calling code
- Improved logging and monitoring

#### Encoding Detection

Integrated `chardet` library for automatic encoding detection:

```python
def detect_encoding(file_path: str) -> str:
    """Detect file encoding using chardet library"""
    # Auto-detect encoding with confidence score
    # Fallback to UTF-8 if detection fails
    # Support for common encodings (UTF-8, CP949, EUC-KR, Latin-1)
```

**Benefits**:
- Handles Korean and other non-UTF-8 subtitles
- Automatic fallback to common encodings
- Confidence scores for debugging
- Prevents encoding-related crashes

#### File Validation

Added comprehensive validation before parsing:

```python
def validate_subtitle_file(file_path: str) -> tuple[bool, Optional[str]]:
    """Validate subtitle file existence and format"""
    # Check file existence
    # Validate file type (not directory)
    # Check supported formats (.srt, .vtt, .ass, .ssa)
```

**Benefits**:
- Early failure detection
- Clear validation errors
- Supported format documentation
- Prevents processing invalid files

### 2. Expression Ranking System

#### Ranking Algorithm

Implemented a weighted scoring system in `langflix/core/expression_analyzer.py`:

```python
def calculate_expression_score(
    expression: ExpressionAnalysis,
    difficulty_weight: float = 0.4,
    frequency_weight: float = 0.3,
    educational_value_weight: float = 0.3
) -> float:
    """Calculate ranking score for an expression"""
    # Normalize difficulty (1-10 → 0-10)
    # Normalize frequency (logarithmic scale)
    # Use educational_value_score directly (0-10)
    # Calculate weighted sum
```

**Formula**: `score = difficulty × 0.4 + log(frequency) × 0.3 + educational_value × 0.3`

**Rationale**:
- **Difficulty (40%)**: Prioritizes challenging but learnable expressions
- **Frequency (30%)**: Values commonly used expressions
- **Educational Value (30%)**: Focuses on expressions with clear learning benefit
- **Logarithmic frequency**: Prevents extremely common expressions from dominating

#### Fuzzy Duplicate Removal

Integrated `rapidfuzz` for intelligent duplicate detection:

```python
def _remove_duplicates(expressions: List[ExpressionAnalysis]) -> List[ExpressionAnalysis]:
    """Remove duplicate expressions using fuzzy string matching"""
    # Use rapidfuzz.fuzz.ratio() for similarity scoring
    # Configurable threshold (default: 85%)
    # Case-insensitive comparison
```

**Benefits**:
- Removes exact duplicates
- Detects similar expressions ("get screwed" ≈ "Get Screwed")
- Handles typos and variations
- Configurable sensitivity

#### Ranking Pipeline

Complete ranking workflow:

```python
def rank_expressions(
    expressions: List[ExpressionAnalysis],
    max_count: int = 5,
    remove_duplicates: bool = True
) -> List[ExpressionAnalysis]:
    """
    Process:
    1. Remove duplicates (fuzzy matching)
    2. Calculate ranking scores
    3. Sort by score (highest first)
    4. Return top N expressions
    """
```

### 3. Data Model Extensions

Enhanced `ExpressionAnalysis` model with ranking fields:

```python
class ExpressionAnalysis(BaseModel):
    # ... existing fields ...
    
    # Phase 2 additions:
    educational_value_score: float = Field(default=5.0, ge=0.0, le=10.0)
    frequency: int = Field(default=1, ge=1)
    context_relevance: float = Field(default=5.0, ge=0.0, le=10.0)
    ranking_score: float = Field(default=0.0)
```

### 4. Configuration Integration

Extended `langflix/config/default.yaml` with ranking settings:

```yaml
llm:
  # ... existing settings ...
  
  ranking:
    difficulty_weight: 0.4
    frequency_weight: 0.3
    educational_value_weight: 0.3
    fuzzy_match_threshold: 85

expression:
  llm:
    # ... existing settings ...
    max_expressions_per_chunk: 5
```

## Implementation Details

### Backward Compatibility

All changes maintain backward compatibility:

1. **Existing Functions**: All original functions (`parse_srt_file`, `parse_subtitle_file`) retained
2. **Optional Validation**: `parse_srt_file` has optional `validate` parameter (default: True)
3. **Graceful Fallbacks**: If `chardet` or `rapidfuzz` not installed, system continues with warnings
4. **Default Values**: All new model fields have sensible defaults

### Error Handling Strategy

Three-level error handling approach:

1. **Validation Level**: File validation before processing
2. **Parsing Level**: Encoding detection and fallback
3. **Application Level**: Custom exceptions with detailed messages

### Performance Considerations

1. **Lazy Imports**: `chardet` and `rapidfuzz` imported only when needed
2. **Logarithmic Frequency**: Prevents linear scaling issues
3. **Early Filtering**: Remove duplicates before expensive operations
4. **Configurable Limits**: `max_expressions_per_chunk` prevents resource exhaustion

## Testing

### Test Coverage

**Subtitle Validation Tests** (16 tests):
- File existence and format validation
- Encoding detection (UTF-8, Latin-1, CP949)
- Error message accuracy
- Support for multiple subtitle formats
- Edge cases (directories, missing files)

**Expression Ranking Tests** (18 tests):
- Score calculation correctness
- Duplicate removal (exact and fuzzy)
- Ranking algorithm verification
- Weight configuration
- Edge cases (empty lists, single expressions)

**Results**: 34/34 tests passing (100% success rate)

### Test Files

- `tests/unit/test_subtitle_validation.py`: Subtitle processing tests
- `tests/unit/test_expression_ranking.py`: Ranking system tests

## Dependencies

### New Dependencies

Added to `requirements.txt`:

```txt
# Phase 2: Subtitle processing & expression ranking
chardet>=5.0.0  # Encoding detection
rapidfuzz>=3.0.0  # Fuzzy string matching for duplicate removal
```

**Justification**:
- **chardet**: Industry standard for encoding detection (100M+ downloads)
- **rapidfuzz**: Fast, well-maintained fuzzy matching library (10M+ downloads)

## Consequences

### Benefits

1. **Improved Reliability**:
   - Handles encoding issues automatically
   - Clear error messages for debugging
   - Comprehensive validation prevents crashes

2. **Better Expression Quality**:
   - Ranking ensures high-value expressions selected
   - No duplicate expressions in output
   - Configurable quality control

3. **Enhanced User Experience**:
   - More relevant expressions for learning
   - Consistent expression quality
   - Better error feedback

4. **System Scalability**:
   - Controlled expression count per video
   - Efficient duplicate removal
   - Configurable ranking weights

### Trade-offs

1. **Performance Overhead**:
   - Encoding detection adds ~50-100ms per file
   - Fuzzy matching is O(n²) for duplicates
   - Ranking adds computational cost
   - **Mitigation**: Overhead is negligible compared to LLM API calls

2. **Additional Dependencies**:
   - Two new dependencies to maintain
   - Increased installation size (~2MB)
   - **Mitigation**: Both are widely used, well-maintained libraries

3. **Configuration Complexity**:
   - More settings to tune (weights, thresholds)
   - Requires understanding of ranking algorithm
   - **Mitigation**: Sensible defaults provided, documentation available

### Risks and Mitigations

1. **Risk**: Fuzzy matching removes valid similar expressions
   - **Mitigation**: 85% threshold is conservative, configurable
   - **Monitoring**: Log all removed duplicates

2. **Risk**: Ranking weights may not suit all content types
   - **Mitigation**: Weights are configurable per deployment
   - **Future**: Could add content-type-specific presets

3. **Risk**: Encoding detection failures on rare formats
   - **Mitigation**: Fallback to common encodings (UTF-8, CP949, EUC-KR)
   - **Monitoring**: Log encoding detection failures

## Future Enhancements

1. **Adaptive Ranking**:
   - Learn optimal weights from user feedback
   - Content-type-specific ranking profiles
   - A/B testing for weight optimization

2. **Advanced Deduplication**:
   - Semantic similarity using embeddings
   - Context-aware duplicate detection
   - Cluster similar expressions

3. **Subtitle Format Support**:
   - .vtt subtitle format parsing
   - .ass subtitle format support
   - Subtitle format conversion

4. **Performance Optimization**:
   - Caching encoding detection results
   - Parallel duplicate detection
   - Incremental ranking updates

## References

- [Phase 1: Expression Configuration](./ADR-013-expression-configuration-architecture.md)
- [North Star Document](../north-start-doc.md)
- [chardet Documentation](https://chardet.readthedocs.io/)
- [RapidFuzz Documentation](https://rapidfuzz.github.io/RapidFuzz/)

## Approval

- **Architecture Review**: Approved
- **Security Review**: Not applicable
- **Performance Review**: Approved with monitoring recommendations

---

**Last Updated**: 2025-10-22  
**Next Review**: After Phase 3 implementation

