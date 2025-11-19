# TTS Module

## Overview

The `langflix/tts/` module provides a swappable Text-to-Speech (TTS) architecture supporting multiple providers. It offers a unified interface for generating speech audio from text, with support for Google Gemini TTS and LemonFox TTS.

**Purpose:**
- Generate speech audio from expression text
- Support multiple TTS providers (Gemini, LemonFox)
- Provide consistent interface across providers
- Handle SSML configuration for natural speech
- Support voice alternation for multiple expressions

**When to use:**
- When generating TTS audio for expressions
- When switching between TTS providers
- When customizing voice settings and SSML parameters
- When implementing voice alternation logic

## File Inventory

### `base.py`
Abstract base class for TTS clients.

**Key Classes:**
- `TTSClient` - Abstract base class for all TTS providers

**Key Methods:**
- `generate_speech()` - Generate speech from text (abstract)
- `validate_config()` - Validate client configuration (abstract)
- `_sanitize_text_for_speech()` - Clean text for synthesis
- `_convert_numbers_to_words()` - Number to word conversion

### `factory.py`
Factory function for creating TTS client instances.

**Key Functions:**
- `create_tts_client()` - Create TTS client based on provider
- `get_available_providers()` - List available TTS providers
- `get_google_tts_language_code()` - Convert language code for Google TTS

**Supported Providers:**
- `google` - Google Gemini TTS
- `lemonfox` - LemonFox TTS

### `gemini_client.py`
Google Gemini TTS client implementation.

**Key Classes:**
- `GeminiTTSClient` - Gemini TTS implementation

**Features:**
- SSML support for speech control
- Multiple voice options
- Configurable speaking rate and pitch
- Language code support

### `google_client.py`
Legacy Google TTS client (may be deprecated).

### `lemonfox_client.py`
LemonFox TTS client implementation.

**Key Classes:**
- `LemonFoxTTSClient` - LemonFox TTS implementation

**Features:**
- Multiple voice options
- Response format configuration
- API key authentication

### `__init__.py`
Module exports.

**Exports:**
- `create_tts_client` - Factory function
- `TTSClient` - Base class

## Key Components

### TTSClient Base Class

```python
class TTSClient(ABC):
    """Abstract base class for Text-to-Speech clients"""
    
    @abstractmethod
    def generate_speech(self, text: str, output_path: Path = None) -> Path:
        """
        Generate speech audio from text.
        
        Args:
            text: The text to convert to speech
            output_path: Optional output path for the audio file
            
        Returns:
            Path to the generated audio file
        """
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """
        Validate that the client configuration is correct.
        
        Returns:
            True if configuration is valid, False otherwise
        """
        pass
```

### Factory Pattern

The module uses a factory pattern to create TTS clients:

```python
def create_tts_client(provider: str, config: Dict[str, Any]) -> TTSClient:
    """
    Factory function to create appropriate TTS client based on provider.
    
    Args:
        provider: TTS provider name (e.g., "lemonfox", "google")
        config: Configuration dictionary for the provider
        
    Returns:
        Initialized TTS client instance
    """
```

**Usage:**
```python
from langflix.tts.factory import create_tts_client

config = {
    'api_key': 'your_key',
    'voice': 'bella',
    'response_format': 'wav'
}
client = create_tts_client('lemonfox', config)

audio_path = client.generate_speech("Hello, world!")
```

### Gemini TTS Client

```python
class GeminiTTSClient(TTSClient):
    """
    Google Gemini TTS client.
    
    Uses Gemini API for text-to-speech with SSML support.
    """
    
    def __init__(
        self,
        api_key: str,
        voice_name: str = "Kore",
        language_code: str = "en-us",
        speaking_rate: str = "medium",
        pitch: float = 0.0,
        model_name: str = "gemini-2.5-flash-preview-tts"
    ):
        """
        Initialize Gemini TTS client.
        
        Args:
            api_key: Gemini API key
            voice_name: Voice name (e.g., "Kore", "Charon")
            language_code: Language code (e.g., "en-us", "ko-kr")
            speaking_rate: Speaking rate (slow, medium, fast)
            pitch: Pitch adjustment (-20.0 to 20.0)
            model_name: Gemini model name
        """
```

**SSML Support:**
- Speaking rate control
- Pitch adjustment
- Voice selection
- Language-specific settings

**Voice Options:**
- `Kore` - Default voice
- `Charon` - Alternative voice
- Additional voices via configuration

### LemonFox TTS Client

```python
class LemonFoxTTSClient(TTSClient):
    """
    LemonFox TTS client.
    
    Uses LemonFox API for text-to-speech.
    """
    
    def __init__(
        self,
        api_key: str,
        voice: str = "bella",
        response_format: str = "wav"
    ):
        """
        Initialize LemonFox TTS client.
        
        Args:
            api_key: LemonFox API key
            voice: Voice name (e.g., "bella")
            response_format: Audio format (wav, mp3, etc.)
        """
```

## Implementation Details

### Text Sanitization

All TTS clients sanitize text before synthesis:

```python
def _sanitize_text_for_speech(self, text: str) -> str:
    """
    Clean and prepare text for speech synthesis.
    
    Removes:
    - Leading/trailing whitespace
    - Special characters (keeps alphanumeric, spaces, basic punctuation)
    - Normalizes whitespace
    """
```

### Configuration Validation

Each client validates its configuration:

```python
def validate_config(self) -> bool:
    """
    Validate client configuration.
    
    Checks:
    - API key presence
    - Voice availability
    - Language code validity
    - Model availability (for Gemini)
    """
```

### Voice Alternation

The system supports voice alternation for multiple expressions:

```python
# In video_editor.py
voice_names = ["Kore", "Charon", "Kore"]  # Alternating voices
voice_name = voice_names[expression_index % len(voice_names)]

config = {
    'voice_name': voice_name,
    'language_code': 'en-us',
    'speaking_rate': 'medium',
    'pitch': 0.0
}
client = create_tts_client('google', config)
```

## Dependencies

**External Libraries:**
- `google-generativeai` - Gemini API client (for Gemini TTS)
- `requests` - HTTP client (for LemonFox TTS)
- `wave` - WAV file handling

**Internal Dependencies:**
- `langflix.settings` - Configuration access
- `langflix.utils` - Utility functions

**Environment Variables:**
- `GEMINI_API_KEY` - Gemini API key (for Gemini TTS)
- `LEMONFOX_API_KEY` - LemonFox API key (for LemonFox TTS)

## Common Tasks

### Using Gemini TTS

```python
from langflix.tts.factory import create_tts_client

config = {
    'api_key': os.getenv('GEMINI_API_KEY'),
    'voice_name': 'Kore',
    'language_code': 'en-us',
    'speaking_rate': 'medium',
    'pitch': 0.0
}

client = create_tts_client('google', config)
audio_path = client.generate_speech("break the ice", output_path=Path("audio.wav"))
```

### Using LemonFox TTS

```python
from langflix.tts.factory import create_tts_client

config = {
    'api_key': os.getenv('LEMONFOX_API_KEY'),
    'voice': 'bella',
    'response_format': 'wav'
}

client = create_tts_client('lemonfox', config)
audio_path = client.generate_speech("break the ice", output_path=Path("audio.wav"))
```

### Switching Providers

```python
from langflix.tts.factory import create_tts_client
from langflix import settings

provider = settings.get_tts_provider()  # 'google' or 'lemonfox'

if provider == 'google':
    config = {'api_key': os.getenv('GEMINI_API_KEY'), ...}
else:
    config = {'api_key': os.getenv('LEMONFOX_API_KEY'), ...}

client = create_tts_client(provider, config)
```

### Voice Alternation

```python
# Alternate voices for multiple expressions
voices = ["Kore", "Charon"]
for i, expression in enumerate(expressions):
    voice_name = voices[i % len(voices)]
    config = {'voice_name': voice_name, ...}
    client = create_tts_client('google', config)
    audio = client.generate_speech(expression.text)
```

## Gotchas and Notes

### Important Considerations

1. **API Keys:**
   - Gemini: Set `GEMINI_API_KEY` environment variable
   - LemonFox: Set `LEMONFOX_API_KEY` environment variable
   - Keys are required for client creation

2. **Language Codes:**
   - Gemini uses lowercase format: `en-us`, `ko-kr`
   - Language code conversion handled by factory
   - Default: `en-us` for English

3. **Voice Selection:**
   - Gemini: `Kore` (default), `Charon`, and others
   - LemonFox: `bella` and other voices
   - Voice availability depends on provider

4. **SSML Configuration:**
   - Gemini supports SSML for speech control
   - Speaking rate: `slow`, `medium`, `fast`
   - Pitch: -20.0 to 20.0 (semitones)

5. **Audio Format:**
   - Gemini: WAV format (24kHz, mono)
   - LemonFox: Configurable (WAV, MP3, etc.)
   - Output format depends on provider

### Performance Tips

- Cache audio files for repeated expressions
- Use appropriate voice for language
- Batch process multiple expressions
- Consider rate limits for API calls

### Error Handling

- Missing API keys raise `ValueError`
- Invalid configurations fail validation
- Network errors should be handled by caller
- Audio generation errors raise exceptions

### Current Implementation Status

**Note:** The TTS module provides a solid foundation with factory pattern and multiple provider support. Some areas for enhancement:

- Error retry logic
- Audio format conversion
- Caching mechanisms
- Batch processing support

## Related Documentation

- [Core Module](../core/README_eng.md) - Expression processing that uses TTS
- [Audio Module](../audio/README_eng.md) - Audio processing and optimization
- [Config Module](../config/README_eng.md) - TTS configuration settings

