"""
Factory for creating TTS client instances
"""

import os
import logging
from typing import Dict, Any

from .base import TTSClient
from .lemonfox_client import LemonFoxTTSClient

logger = logging.getLogger(__name__)


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
    
    if provider == "lemonfox":
        # Get API key from environment variable first, fallback to config
        api_key = os.getenv("LEMONFOX_API_KEY") or config.get('api_key')
        if not api_key:
            raise ValueError(
                "LemonFox API key is required. Set LEMONFOX_API_KEY environment variable "
                "or provide api_key in configuration"
            )
        
        voice = config.get('voice', 'bella')
        response_format = config.get('response_format', 'wav')
        
        return LemonFoxTTSClient(
            api_key=api_key,
            voice=voice,
            response_format=response_format
        )
    
    # Future providers can be added here
    # elif provider == "google":
    #     return GoogleTTSClient(config)
    # elif provider == "aws":
    #     return AWSPollyClient(config)
    # elif provider == "azure":
    #     return AzureTTSClient(config)
    
    # Unknown provider
    supported_providers = ["lemonfox"]
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
    return ["lemonfox"]

