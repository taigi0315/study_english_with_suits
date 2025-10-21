# ADR-007: Direct SSML Configuration

**Date:** 2025-10-21  
**Status:** Accepted  
**Deciders:** Development Team  

## Context

The initial Gemini TTS implementation used numeric values for `speaking_rate` and `pitch` that were converted to SSML keywords internally. This approach was complex and error-prone, requiring conversion logic that was difficult to maintain and understand. Users found it confusing to configure TTS parameters using numeric values when SSML provides more intuitive keyword-based options.

## Decision

We will implement direct SSML configuration in YAML files, allowing users to specify SSML keywords and values directly without any conversion logic. This approach provides:

1. **Direct SSML Control**: Users can specify SSML values directly
2. **Simplified Code**: Remove complex conversion logic
3. **Better Documentation**: Clear SSML options in configuration
4. **User-Friendly**: More intuitive configuration options

## Implementation Details

### Configuration Changes

**Before (Numeric Conversion)**:
```yaml
tts:
  google:
    speaking_rate: 0.95  # Numeric value
    pitch: -1.0          # Numeric value
```

**After (Direct SSML)**:
```yaml
tts:
  google:
    speaking_rate: "slow"    # SSML keyword
    pitch: "-4st"            # SSML semitone value
```

### SSML Options

**Speaking Rate Options**:
- `x-slow`, `slow`, `medium`, `fast`, `x-fast`
- Percentage values: `"0.8"`, `"1.2"`

**Pitch Options**:
- Keywords: `x-low`, `low`, `medium`, `high`, `x-high`
- Percentage: `"+10%"`, `"-5%"`
- Semitones: `"-2st"`, `"+1st"`

### Code Changes

1. **Remove Conversion Logic**: Delete numeric-to-SSML conversion functions
2. **Direct SSML Application**: Apply SSML values directly in TTS client
3. **Configuration Validation**: Validate SSML values in configuration loader

### Example Implementation

```python
# Before: Complex conversion logic
def convert_rate_to_ssml(rate: float) -> str:
    if rate < 0.8:
        return "x-slow"
    elif rate < 0.9:
        return "slow"
    # ... more conversion logic

# After: Direct SSML application
if self.speaking_rate != "medium" or self.pitch != "0st":
    ssml_text = f'<speak><prosody rate="{self.speaking_rate}" pitch="{self.pitch}">{text_cleaned}</prosody></speak>'
```

## Consequences

### Positive

- **Simplified Code**: Remove complex conversion logic
- **Better User Experience**: More intuitive configuration
- **Direct Control**: Users can use any valid SSML value
- **Easier Maintenance**: Less code to maintain and debug
- **Better Documentation**: Clear SSML options in config files

### Negative

- **Breaking Change**: Existing numeric configurations need updating
- **Learning Curve**: Users need to learn SSML syntax
- **Validation Required**: Need to validate SSML values

### Migration Path

1. **Update Configuration**:
   ```yaml
   # Old
   speaking_rate: 0.95
   pitch: -1.0
   
   # New
   speaking_rate: "slow"
   pitch: "-4st"
   ```

2. **Documentation Update**: Update all documentation with SSML examples
3. **Validation**: Add SSML value validation in configuration loader

## Alternatives Considered

1. **Keep Numeric Conversion**: Rejected due to complexity and user confusion
2. **Hybrid Approach**: Rejected due to increased complexity
3. **SSML Templates**: Rejected due to over-engineering

## Configuration Examples

### Basic Configuration
```yaml
tts:
  google:
    speaking_rate: "slow"
    pitch: "-4st"
```

### Advanced Configuration
```yaml
tts:
  google:
    speaking_rate: "x-slow"  # Very slow speech
    pitch: "-2st"            # Two semitones lower
```

### Percentage Values
```yaml
tts:
  google:
    speaking_rate: "0.8"     # 80% speed
    pitch: "+10%"            # 10% higher pitch
```

## References

- [SSML Specification](https://www.w3.org/TR/speech-synthesis11/)
- [Google TTS SSML Support](https://cloud.google.com/text-to-speech/docs/ssml)
- [Gemini TTS SSML Documentation](https://ai.google.dev/gemini-api/docs/speech-generation)
