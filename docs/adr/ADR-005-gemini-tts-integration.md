# ADR-005: Gemini TTS Integration

**Date:** 2025-10-19  
**Status:** Accepted  
**Deciders:** Development Team  

## Context

LangFlix was experiencing issues with TTS (Text-to-Speech) audio quality. The existing TTS implementation using Google Cloud TTS was producing robotic-sounding speech that was not suitable for educational content. Users reported that the audio sounded unnatural and was difficult to understand.

## Decision

We will integrate Google's Gemini 2.5 Flash TTS model to replace the existing Google Cloud TTS implementation. This decision was made based on:

1. **Superior Audio Quality**: Gemini TTS produces more natural-sounding speech
2. **SSML Support**: Direct SSML control for rate and pitch adjustment
3. **Modern API**: Uses the latest Google GenAI SDK
4. **Better Voice Options**: Multiple high-quality voices available

## Implementation Details

### Technical Changes

1. **New TTS Client**: `langflix/tts/gemini_client.py`
   - Uses `google-genai` library
   - Model: `gemini-2.5-flash-preview-tts`
   - Output format: WAV
   - SSML support for rate and pitch control

2. **Configuration Updates**: `langflix/config/default.yaml`
   ```yaml
   tts:
     provider: "google"
     google:
       model_name: "gemini-2.5-flash-preview-tts"
       response_format: "wav"
       speaking_rate: "slow"
       pitch: "-4st"
       alternate_voices: ["Despina", "Puck"]
   ```

3. **Environment Variables**: 
   - `GEMINI_API_KEY` (replaces `GOOGLE_API_KEY_1`)

### SSML Configuration

The implementation uses direct SSML configuration instead of numeric conversion:

```yaml
speaking_rate: "slow"  # x-slow, slow, medium, fast, x-fast
pitch: "-4st"          # x-low, low, medium, high, x-high, or semitones
```

## Consequences

### Positive

- **Improved Audio Quality**: More natural-sounding speech
- **Better User Experience**: Easier to understand educational content
- **Flexible Configuration**: Direct SSML control for fine-tuning
- **Modern Architecture**: Uses latest Google AI services

### Negative

- **API Key Change**: Users need to update from `GOOGLE_API_KEY_1` to `GEMINI_API_KEY`
- **Dependency Change**: New `google-genai` library required
- **Learning Curve**: New configuration options for SSML

### Migration Path

1. Update environment variables:
   ```bash
   # Old
   GOOGLE_API_KEY_1=your_key
   
   # New
   GEMINI_API_KEY=your_key
   ```

2. Install new dependency:
   ```bash
   pip install google-genai
   ```

3. Update configuration if needed:
   ```yaml
   tts:
     google:
       speaking_rate: "slow"  # Adjust as needed
       pitch: "-4st"          # Adjust as needed
   ```

## Alternatives Considered

1. **Keep Google Cloud TTS**: Rejected due to poor audio quality
2. **Use Other TTS Providers**: Rejected due to integration complexity
3. **Improve Existing TTS**: Rejected due to fundamental limitations

## References

- [Google GenAI Documentation](https://ai.google.dev/gemini-api/docs/speech-generation)
- [Gemini 2.5 Flash TTS Models](https://ai.google.dev/gemini-api/docs/models#gemini-2.5-flash-tts)
- [SSML Reference](https://cloud.google.com/text-to-speech/docs/ssml)
