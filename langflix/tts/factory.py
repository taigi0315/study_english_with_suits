"""
Factory for creating TTS client instances
"""

import os
import logging
from typing import Dict, Any, Tuple, List

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from .base import TTSClient
from .lemonfox_client import LemonFoxTTSClient

# Import Google client with error handling
try:
    from .google_client import GoogleTTSClient
    GOOGLE_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Google Cloud TTS not available: {e}")
    GoogleTTSClient = None
    GOOGLE_AVAILABLE = False

logger = logging.getLogger(__name__)


def get_google_tts_language_code(target_language: str) -> str:
    """
    Map target language names to Google Cloud TTS language codes.
    
    Note: Currently not used - TTS uses original language (English) for audio generation,
    not the target language. This function is kept for future use if needed.
    
    Args:
        target_language: Target language name (e.g., "Korean", "Spanish", "French")
        
    Returns:
        Google Cloud TTS language code (e.g., "ko-KR", "es-ES", "fr-FR")
    """
    # Language mapping from target language names to Google Cloud TTS language codes
    language_mapping = {
        "Korean": "ko-KR",
        "korean": "ko-KR",
        "ko": "ko-KR",
        "Spanish": "es-ES", 
        "spanish": "es-ES",
        "es": "es-ES",
        "French": "fr-FR",
        "french": "fr-FR", 
        "fr": "fr-FR",
        "German": "de-DE",
        "german": "de-DE",
        "de": "de-DE",
        "Japanese": "ja-JP",
        "japanese": "ja-JP",
        "ja": "ja-JP",
        "Chinese": "zh-CN",
        "chinese": "zh-CN",
        "zh": "zh-CN",
        "Mandarin": "zh-CN",
        "mandarin": "zh-CN",
        "Italian": "it-IT",
        "italian": "it-IT",
        "it": "it-IT",
        "Portuguese": "pt-PT",
        "portuguese": "pt-PT",
        "pt": "pt-PT",
        "Russian": "ru-RU",
        "russian": "ru-RU",
        "ru": "ru-RU",
        "Arabic": "ar-SA",
        "arabic": "ar-SA",
        "ar": "ar-SA",
        "Dutch": "nl-NL",
        "dutch": "nl-NL",
        "nl": "nl-NL",
        "English": "en-US",
        "english": "en-US",
        "en": "en-US"
    }
    
    # Normalize the input (strip whitespace, handle case)
    normalized_lang = target_language.strip()
    language_code = language_mapping.get(normalized_lang)
    
    if language_code:
        logger.info(f"Mapped target language '{target_language}' to Google TTS code '{language_code}'")
        return language_code
    else:
        logger.warning(f"Unknown target language '{target_language}', falling back to 'en-US'")
        return "en-US"


def get_google_tts_voices_for_language(language_code: str) -> Tuple[List[str], str]:
    """
    Get appropriate voices for a given language code.
    
    Args:
        language_code: Google Cloud TTS language code (e.g., "ko-KR", "es-ES")
        
    Returns:
        Tuple of (voice_list, default_voice)
    """
    # Voice mapping for different languages (using Google Cloud TTS voice names)
    voice_mapping = {
        "ko-KR": {
            "voices": ["ko-KR-Wavenet-A", "ko-KR-Wavenet-B", "ko-KR-Standard-A", "ko-KR-Standard-B"],
            "default": "ko-KR-Wavenet-A",
            "alternate": ["ko-KR-Wavenet-A", "ko-KR-Wavenet-B"]  # Puck and Leda for Korean
        },
        "es-ES": {
            "voices": ["es-ES-Wavenet-A", "es-ES-Wavenet-B", "es-ES-Standard-A", "es-ES-Standard-B"],
            "default": "es-ES-Wavenet-A",
            "alternate": ["es-ES-Wavenet-A", "es-ES-Wavenet-B"]
        },
        "fr-FR": {
            "voices": ["fr-FR-Wavenet-A", "fr-FR-Wavenet-B", "fr-FR-Standard-A", "fr-FR-Standard-B"],
            "default": "fr-FR-Wavenet-A", 
            "alternate": ["fr-FR-Wavenet-A", "fr-FR-Wavenet-B"]
        },
        "de-DE": {
            "voices": ["de-DE-Wavenet-A", "de-DE-Wavenet-B", "de-DE-Standard-A", "de-DE-Standard-B"],
            "default": "de-DE-Wavenet-A",
            "alternate": ["de-DE-Wavenet-A", "de-DE-Wavenet-B"]
        },
        "ja-JP": {
            "voices": ["ja-JP-Wavenet-A", "ja-JP-Wavenet-B", "ja-JP-Standard-A", "ja-JP-Standard-B"],
            "default": "ja-JP-Wavenet-A",
            "alternate": ["ja-JP-Wavenet-A", "ja-JP-Wavenet-B"]
        },
        "zh-CN": {
            "voices": ["zh-CN-Wavenet-A", "zh-CN-Wavenet-B", "zh-CN-Standard-A", "zh-CN-Standard-B"],
            "default": "zh-CN-Wavenet-A",
            "alternate": ["zh-CN-Wavenet-A", "zh-CN-Wavenet-B"]
        },
        "en-US": {
            "voices": ["en-US-Wavenet-A", "en-US-Wavenet-D", "en-US-Standard-A", "en-US-Standard-D"],
            "default": "en-US-Wavenet-D",  # Puck
            "alternate": ["en-US-Wavenet-D", "en-US-Wavenet-A"]  # Puck and Leda
        }
    }
    
    # Get voices for the language, fallback to English
    voice_info = voice_mapping.get(language_code, voice_mapping["en-US"])
    return voice_info["alternate"], voice_info["default"]


def create_tts_client(provider: str, config: Dict[str, Any]) -> TTSClient:
    """
    Factory function to create appropriate TTS client based on provider.
    
    Args:
        provider: TTS provider name (e.g., "lemonfox", "google", "aws")
        config: Configuration dictionary for the provider
        
    Returns:
        Initialized TTS client instance
        
    Raises:
        ValueError: If provider is unknown or configuration is invalid
        
    Example:
        >>> config = {
        ...     'api_key': 'your_key',
        ...     'voice': 'bella',
        ...     'response_format': 'wav'
        ... }
        >>> client = create_tts_client('lemonfox', config)
    """
    provider = provider.lower()
    
    logger.info(f"Creating TTS client for provider: {provider}")
    logger.debug(f"TTS config provided: {config}")
    
    if provider == "lemonfox":
        # Force reload environment variables
        try:
            from dotenv import load_dotenv
            load_dotenv(override=True)  # Override existing env vars
        except ImportError:
            pass
        
        # Get API key from environment variable first, fallback to config
        api_key = os.getenv("LEMONFOX_API_KEY") or config.get('api_key')
        
        logger.info(f"API Key validation:")
        logger.info(f"  Environment LEMONFOX_API_KEY exists: {bool(os.getenv('LEMONFOX_API_KEY'))}")
        logger.info(f"  Config api_key exists: {bool(config.get('api_key'))}")
        logger.info(f"  Final API key length: {len(api_key) if api_key else 'None'}")
        
        # Enhanced API key validation
        if not api_key:
            logger.error("No LemonFox API key found in environment variable LEMONFOX_API_KEY or config")
            logger.error("Please check:")
            logger.error("1. .env file exists in project root")
            logger.error("2. LEMONFOX_API_KEY is set in .env file")
            logger.error("3. Run: echo $LEMONFOX_API_KEY")
            raise ValueError(
                "LemonFox API key is required. Set LEMONFOX_API_KEY environment variable "
                "or provide api_key in configuration. "
                "Example: export LEMONFOX_API_KEY='your_api_key_here'"
            )
        
        # Validate API key format (basic check)
        if len(api_key) < 10:
            logger.warning("API key seems too short, please verify it's correct")
        
        # Remove any whitespace or newlines from API key
        api_key = api_key.strip()
        logger.info(f"Using API key: {api_key[:10]}...{api_key[-10:] if len(api_key) > 20 else '***'}")
        
        # Get configuration with better defaults and validation
        voice = config.get('voice', 'bella')
        response_format = config.get('response_format', 'wav')
        
        # Validate response format
        if response_format not in ['wav', 'mp3']:
            logger.warning(f"Invalid response_format '{response_format}', defaulting to 'wav'")
            response_format = 'wav'
        
        logger.info(f"Creating LemonFox client with voice='{voice}', format='{response_format}'")
        logger.info(f"API key configured: {'*' * (len(api_key) - 4) + api_key[-4:] if len(api_key) > 4 else '****'}")
        
        try:
            client = LemonFoxTTSClient(
                api_key=api_key,
                voice=voice,
                response_format=response_format
            )
            
            # Validate the client configuration
            if not client.validate_config():
                raise ValueError("TTS client configuration validation failed")
            
            logger.info("TTS client created and validated successfully")
            return client
            
        except Exception as e:
            logger.error(f"Failed to create LemonFox TTS client: {e}")
            raise ValueError(f"Failed to initialize LemonFox TTS client: {e}")
    
    elif provider == "google":
        if not GOOGLE_AVAILABLE or GoogleTTSClient is None:
            raise ValueError(
                "Google Cloud TTS is not available. Install with: "
                "pip install google-cloud-texttospeech"
            )
        
        # Force reload environment variables
        try:
            from dotenv import load_dotenv
            load_dotenv(override=True)
        except ImportError:
            pass
        
        # Get API key from environment variable first, fallback to config
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GOOGLE_API_KEY_1") or config.get('api_key')
        
        logger.info(f"Google TTS API Key validation:")
        logger.info(f"  Environment GOOGLE_API_KEY exists: {bool(os.getenv('GOOGLE_API_KEY'))}")
        logger.info(f"  Environment GOOGLE_API_KEY_1 exists: {bool(os.getenv('GOOGLE_API_KEY_1'))}")
        logger.info(f"  Config api_key exists: {bool(config.get('api_key'))}")
        logger.info(f"  Final API key length: {len(api_key) if api_key else 'None'}")
        
        if not api_key:
            logger.error("No Google Cloud API key found in environment variables or config")
            logger.error("Please check:")
            logger.error("1. .env file exists in project root")
            logger.error("2. GOOGLE_API_KEY or GOOGLE_API_KEY_1 is set in .env file")
            raise ValueError(
                "Google Cloud API key is required. Set GOOGLE_API_KEY environment variable "
                "or provide api_key in configuration."
            )
        
        # TTS should use original language (English) for audio generation, not target language
        # Target language is for translations, but audio should be in the original language of the content
        language_code = config.get('language_code', 'en-US')  # Default to English (original language)
        
        # Use English voices for original language content
        alternate_voices, default_voice = get_google_tts_voices_for_language(language_code)
        
        # Get configuration with defaults for original language (English)
        voice_name = config.get('voice_name', default_voice)
        speaking_rate = config.get('speaking_rate', 0.85)
        
        # Update config with English voices for voice alternation (Puck and Leda)
        if 'alternate_voices' not in config or not config.get('alternate_voices'):
            config['alternate_voices'] = alternate_voices
            logger.info(f"Set original language (English) alternate voices: {alternate_voices}")
        else:
            logger.info(f"Using configured alternate voices: {config['alternate_voices']}")
        
        logger.info(f"TTS using original language: {language_code} (target language not used for audio generation)")
        
        logger.info(f"Creating Google Cloud TTS client with voice='{voice_name}', language='{language_code}', rate={speaking_rate}")
        logger.info(f"API key configured: {'*' * (len(api_key) - 4) + api_key[-4:] if len(api_key) > 4 else '****'}")
        
        try:
            client = GoogleTTSClient(
                api_key=api_key,
                voice_name=voice_name,
                language_code=language_code,
                speaking_rate=speaking_rate
            )
            
            # Validate the client configuration
            if not client.validate_config():
                raise ValueError("Google TTS client configuration validation failed")
            
            logger.info("Google Cloud TTS client created and validated successfully")
            return client
            
        except Exception as e:
            logger.error(f"Failed to create Google Cloud TTS client: {e}")
            raise ValueError(f"Failed to initialize Google Cloud TTS client: {e}")
    
    # Future providers can be added here
    # elif provider == "aws":
    #     return AWSPollyClient(config)
    # elif provider == "azure":
    #     return AzureTTSClient(config)
    
    # Unknown provider
    supported_providers = ["lemonfox"]
    if GOOGLE_AVAILABLE:
        supported_providers.append("google")
    
    raise ValueError(
        f"Unknown TTS provider: {provider}. "
        f"Supported providers: {', '.join(supported_providers)}"
    )


def get_available_providers() -> list:
    """
    Get list of available TTS providers.
    
    Returns:
        List of supported provider names
    """
    providers = ["lemonfox"]
    if GOOGLE_AVAILABLE:
        providers.append("google")
    return providers

