"""
LemonFox TTS Client implementation
"""

import os
import logging
import tempfile
import requests
from pathlib import Path
from typing import Optional

from .base import TTSClient

logger = logging.getLogger(__name__)


class LemonFoxTTSClient(TTSClient):
    """
    Text-to-Speech client for LemonFox API.
    
    Generates speech audio using the LemonFox API service.
    """
    
    def __init__(self, api_key: str, voice: str = "bella", response_format: str = "wav"):
        """
        Initialize LemonFox TTS client.
        
        Args:
            api_key: LemonFox API key
            voice: Voice name to use (default: "bella")
            response_format: Audio format - "mp3" or "wav" (default: "wav")
        """
        self.api_key = api_key
        self.voice = voice
        self.response_format = response_format
        self.url = "https://api.lemonfox.ai/v1/audio/speech"
        
        logger.info(f"Initialized LemonFox TTS client with voice: {voice}, format: {response_format}")
    
    def validate_config(self) -> bool:
        """
        Validate LemonFox client configuration.
        
        Returns:
            True if configuration is valid
        """
        if not self.api_key:
            logger.error("LemonFox API key is missing")
            return False
        
        if not self.voice:
            logger.error("LemonFox voice is not specified")
            return False
        
        if self.response_format not in ["mp3", "wav"]:
            logger.error(f"Invalid response format: {self.response_format}")
            return False
        
        return True
    
    def generate_speech(self, text: str, output_path: Path = None) -> Path:
        """
        Generate speech from text using LemonFox API.
        
        Args:
            text: Text to convert to speech
            output_path: Optional custom output path
            
        Returns:
            Path to generated audio file
            
        Raises:
            requests.RequestException: If API request fails
            ValueError: If response is invalid
        """
        # Validate configuration first
        if not self.validate_config():
            raise ValueError("Invalid LemonFox TTS configuration")
        
        # Clean and prepare text for speech
        clean_text = self._sanitize_text_for_speech(text)
        clean_text = self._convert_numbers_to_words(clean_text)
        
        logger.info(f"Generating speech for text: '{clean_text}'")
        
        # Prepare API request
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "input": clean_text,
            "voice": self.voice,
            "response_format": self.response_format
        }
        
        try:
            # Make API request
            logger.info(f"Making API request to: {self.url}")
            logger.info(f"Request data: {data}")
            
            response = requests.post(self.url, headers=headers, json=data, timeout=30)
            
            # Debug response details
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response headers: {dict(response.headers)}")
            logger.info(f"Response content length: {len(response.content)} bytes")
            
            # Check if we got a successful response
            response.raise_for_status()
            
            # Verify we got binary audio content (not error message)
            content_type = response.headers.get('content-type', '').lower()
            logger.info(f"Content-Type: {content_type}")
            
            if len(response.content) < 100:
                logger.warning(f"Very small response content ({len(response.content)} bytes), might be error message:")
                logger.warning(f"Content preview: {response.content[:200]}")
            
            # Determine output path
            if output_path is None:
                # Create temporary file
                suffix = f".{self.response_format}"
                temp_file = tempfile.NamedTemporaryFile(
                    delete=False, 
                    suffix=suffix, 
                    prefix="langflix_tts_"
                )
                output_path = Path(temp_file.name)
                temp_file.close()
            else:
                output_path = Path(output_path)
            
            # Save audio content
            with open(output_path, "wb") as f:
                f.write(response.content)
            
            # Verify the saved file
            file_size = output_path.stat().st_size
            logger.info(f"Successfully generated speech audio: {output_path}")
            logger.info(f"Audio file size: {file_size} bytes")
            
            if file_size == 0:
                logger.error(f"Generated audio file is empty!")
                raise ValueError(f"Generated audio file is empty: {output_path}")
            
            return output_path
            
        except requests.exceptions.Timeout:
            logger.error("LemonFox API request timed out")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"LemonFox API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                logger.error(f"API response: {e.response.text}")
                if e.response.status_code == 401:
                    logger.error("Invalid API key - please check your LEMONFOX_API_KEY environment variable")
            raise
        except Exception as e:
            logger.error(f"Unexpected error generating speech: {e}")
            raise
    
    def _sanitize_text_for_speech(self, text: str) -> str:
        """
        Enhanced text sanitization for LemonFox TTS.
        
        Removes special characters and normalizes text for better speech quality.
        
        Args:
            text: Raw text input
            
        Returns:
            Cleaned text suitable for speech synthesis
        """
        # Call parent implementation
        text = super()._sanitize_text_for_speech(text)
        
        # Additional LemonFox-specific cleaning
        # Remove underscores (common in expression names)
        text = text.replace('_', ' ')
        
        # Remove multiple spaces
        text = ' '.join(text.split())
        
        # Ensure text is not empty
        if not text.strip():
            logger.warning("Text is empty after sanitization")
            text = "expression"  # Fallback
        
        return text

