# ADR-015: WhisperX Integration for Precise Timestamp Detection

## Status
**Accepted** - 2024-12-19

## Context

The Expression-Based Learning Feature requires precise timestamp detection for expressions within video content. The current subtitle-based approach has limitations:

1. **Subtitle Timing Accuracy**: SRT subtitles often have imprecise timing, especially for word-level accuracy
2. **Missing Expressions**: Some expressions may not be captured in subtitles
3. **Language Detection**: Subtitles may not accurately reflect the spoken language
4. **Word-Level Precision**: Current approach cannot provide word-level timestamp accuracy

## Decision

We will integrate **WhisperX** as the primary ASR (Automatic Speech Recognition) solution for precise timestamp detection in Phase 3 of the Expression-Based Learning Feature.

### Key Components

1. **AudioPreprocessor**: Extract and preprocess audio from video files
2. **WhisperXClient**: Interface with WhisperX for transcription and alignment
3. **TimestampAligner**: Align expressions with precise word-level timestamps
4. **ASR Exceptions**: Comprehensive error handling for ASR operations

### Architecture

```
Video File → AudioPreprocessor → WhisperXClient → TimestampAligner
     ↓              ↓                    ↓              ↓
  Extract      Preprocess         Transcribe      Align
   Audio        Audio            with Timestamps  Expressions
```

## Rationale

### Why WhisperX?

1. **Word-Level Timestamps**: WhisperX provides precise word-level timestamps, essential for expression alignment
2. **High Accuracy**: State-of-the-art ASR performance with excellent language detection
3. **Alignment Capabilities**: Built-in alignment models for precise timestamp detection
4. **Open Source**: No API costs, runs locally
5. **Language Support**: Excellent support for multiple languages including English

### Why Not Alternatives?

- **Google Cloud Speech-to-Text**: API costs, rate limits, and dependency on external service
- **Azure Speech Services**: Similar limitations to Google Cloud
- **OpenAI Whisper**: Lacks word-level alignment capabilities
- **AssemblyAI**: API costs and external dependency

## Implementation Details

### 1. AudioPreprocessor

**Purpose**: Extract and preprocess audio from video files for WhisperX

**Key Features**:
- Video format support (MP4, MKV, AVI, MOV, WebM)
- Audio extraction using FFmpeg
- Audio validation and preprocessing
- Sample rate conversion (16kHz for WhisperX)
- Mono channel conversion

**Configuration**:
```yaml
expression:
  whisper:
    sample_rate: 16000
    channels: 1
    format: wav
    timeout: 300
```

### 2. WhisperXClient

**Purpose**: Interface with WhisperX for transcription and alignment

**Key Features**:
- Model loading and management
- Audio transcription with timestamps
- Word-level alignment
- Language detection
- Device management (CPU/GPU)

**Configuration**:
```yaml
expression:
  whisper:
    model_size: base
    device: cpu
    compute_type: float32
    language: null  # Auto-detect
    batch_size: 16
```

### 3. TimestampAligner

**Purpose**: Align expressions with precise word-level timestamps

**Key Features**:
- Fuzzy string matching for expression detection
- Context buffer around expressions
- Confidence scoring
- Alignment statistics

**Configuration**:
```yaml
expression:
  whisper:
    fuzzy_threshold: 0.85
    context_buffer: 0.5
```

### 4. ASR Exceptions

**Purpose**: Comprehensive error handling for ASR operations

**Exception Types**:
- `AudioExtractionError`: Audio extraction failures
- `WhisperXError`: WhisperX transcription errors
- `TimestampAlignmentError`: Expression alignment failures
- `ModelLoadError`: Model loading failures
- `AudioPreprocessingError`: Audio preprocessing failures
- `TranscriptionTimeoutError`: Transcription timeout

## Configuration

### Default Configuration

```yaml
expression:
  whisper:
    # Model settings
    model_size: base
    device: cpu
    compute_type: float32
    language: null  # Auto-detect
    
    # Audio settings
    sample_rate: 16000
    channels: 1
    format: wav
    timeout: 300
    
    # Alignment settings
    fuzzy_threshold: 0.85
    context_buffer: 0.5
    batch_size: 16
```

### Environment Variables

```bash
# WhisperX settings
WHISPERX_MODEL_SIZE=base
WHISPERX_DEVICE=cpu
WHISPERX_LANGUAGE=en
WHISPERX_TIMEOUT=300
```

## Dependencies

### New Dependencies

```txt
# Phase 3: WhisperX ASR Integration
whisperx>=3.1.0  # Automatic Speech Recognition with word-level timestamps
torch>=2.0.0     # PyTorch for WhisperX
torchaudio>=2.0.0 # Audio processing for WhisperX
```

### System Requirements

- **FFmpeg**: Required for audio extraction
- **PyTorch**: Required for WhisperX models
- **CUDA**: Optional, for GPU acceleration

## Testing Strategy

### Unit Tests

1. **AudioPreprocessor Tests**:
   - Audio extraction success/failure
   - Format validation
   - Error handling

2. **WhisperXClient Tests**:
   - Model loading
   - Transcription with timestamps
   - Error handling

3. **TimestampAligner Tests**:
   - Expression alignment
   - Fuzzy matching
   - Statistics collection

4. **ASR Exception Tests**:
   - Exception creation and attributes
   - Error message formatting

### Integration Tests

1. **Complete Pipeline Test**:
   - Video → Audio → Transcription → Alignment
   - End-to-end workflow validation

2. **Error Handling Test**:
   - Invalid inputs
   - Network failures
   - Model loading failures

3. **Performance Test**:
   - Processing time measurement
   - Memory usage monitoring
   - Accuracy validation

## Performance Considerations

### Processing Time

- **Audio Extraction**: ~1-2 seconds per minute of video
- **WhisperX Transcription**: ~2-3 seconds per minute of audio
- **Expression Alignment**: ~0.1 seconds per expression

### Memory Usage

- **Model Loading**: ~1-2GB RAM for base model
- **Audio Processing**: ~100-200MB per minute of audio
- **Alignment**: ~50-100MB for expression alignment

### Optimization Strategies

1. **Model Caching**: Keep models loaded in memory
2. **Batch Processing**: Process multiple expressions together
3. **GPU Acceleration**: Use CUDA when available
4. **Audio Compression**: Optimize audio format for WhisperX

## Security Considerations

### Data Privacy

- **Local Processing**: All ASR processing happens locally
- **No External APIs**: No data sent to external services
- **Temporary Files**: Audio files are cleaned up after processing

### Model Security

- **Model Verification**: Verify model integrity
- **Safe Loading**: Secure model loading practices
- **Error Handling**: Prevent model injection attacks

## Monitoring and Logging

### Logging

```python
logger.info(f"Starting WhisperX transcription: {audio_path}")
logger.debug(f"Audio loaded: {len(audio)} samples")
logger.info(f"Detected language: {detected_language}")
logger.info(f"Word-level alignment completed")
logger.info(f"Transcription complete: {len(transcript.segments)} segments")
```

### Metrics

- **Processing Time**: Track transcription and alignment time
- **Accuracy**: Monitor alignment success rate
- **Error Rate**: Track ASR error frequency
- **Resource Usage**: Monitor CPU/GPU usage

## Future Considerations

### Potential Enhancements

1. **Model Fine-tuning**: Custom models for specific domains
2. **Real-time Processing**: Live transcription capabilities
3. **Multi-language Support**: Enhanced language detection
4. **Custom Alignment**: Domain-specific alignment models

### Scalability

1. **Distributed Processing**: Multiple worker processes
2. **Model Optimization**: Smaller, faster models
3. **Caching**: Result caching for repeated content
4. **Batch Processing**: Process multiple videos simultaneously

## Consequences

### Positive

- **Precise Timestamps**: Word-level accuracy for expressions
- **Better Alignment**: Improved expression-to-audio alignment
- **Language Detection**: Automatic language detection
- **No API Costs**: Local processing eliminates external costs
- **Privacy**: All processing happens locally

### Negative

- **System Requirements**: Requires FFmpeg and PyTorch
- **Processing Time**: Longer processing time compared to subtitle parsing
- **Memory Usage**: Higher memory requirements for models
- **Complexity**: More complex error handling and configuration

### Risks

- **Model Loading**: Potential failures in model loading
- **Audio Quality**: Poor audio quality affects transcription accuracy
- **Resource Usage**: High CPU/GPU usage during processing
- **Error Handling**: Complex error scenarios to handle

## Migration Strategy

### Phase 3 Implementation

1. **AudioPreprocessor**: Implement audio extraction and preprocessing
2. **WhisperXClient**: Integrate WhisperX for transcription
3. **TimestampAligner**: Implement expression alignment
4. **Testing**: Comprehensive unit and integration tests
5. **Documentation**: Update user manuals and ADRs

### Backward Compatibility

- **Fallback**: Keep subtitle-based approach as fallback
- **Configuration**: Allow users to choose ASR method
- **Gradual Migration**: Optional feature during Phase 3

## Conclusion

WhisperX integration provides the precise timestamp detection required for the Expression-Based Learning Feature. While it introduces complexity and system requirements, the benefits of word-level accuracy and local processing make it the optimal solution for our use case.

The implementation follows a modular architecture that allows for easy testing, maintenance, and future enhancements. Comprehensive error handling and monitoring ensure reliable operation in production environments.
