"""
Google Cloud Text-to-Speech client implementation
"""

import os
import logging
import tempfile
import json
import requests
from pathlib import Path
from typing import Optional

try:
    from google.cloud import texttospeech
except ImportError:
    texttospeech = None

from .base import TTSClient

logger = logging.getLogger(__name__)


class GoogleTTSClient(TTSClient):
    """
    Text-to-Speech client for Google Cloud TTS API.
    
    Generates speech audio using the Google Cloud Text-to-Speech service.
    """
    
    def __init__(self, api_key: str = None, voice_name: str = "en-US-Standard-A", 
                 language_code: str = "en-US", speaking_rate: float = 0.8):
        """
        Initialize Google Cloud TTS client.
        
        Args:
            api_key: Google Cloud API key (for REST API)
            voice_name: Voice name to use (default: "en-US-Standard-A")
            language_code: Language code (default: "en-US")
            speaking_rate: Speaking rate (default: 0.8 for 80% speed)
        """
        self.api_key = api_key
        self.voice_name = voice_name
        self.language_code = language_code
        self.speaking_rate = speaking_rate
        
        # Use REST API endpoint for Google Cloud TTS
        self.url = "https://texttospeech.googleapis.com/v1/text:synthesize"
        
        if not api_key:
            logger.warning("No API key provided for Google Cloud TTS")
        
        logger.info(f"Initialized Google Cloud TTS client with voice: {voice_name}, language: {language_code}, rate: {speaking_rate}")
        logger.info(f"Using REST API endpoint: {self.url}")
    
    def validate_config(self) -> bool:
        """
        Validate Google Cloud TTS client configuration.
        
        Returns:
            True if configuration is valid
        """
        if not self.api_key:
            logger.error("Google Cloud TTS API key is missing")
            return False
        
        if not self.voice_name:
            logger.error("Google Cloud TTS voice name is not specified")
            return False
        
        if not self.language_code:
            logger.error("Google Cloud TTS language code is not specified")
            return False
        
        return True
    
    def generate_speech(self, text: str, output_path: Path = None) -> Path:
        """
        Generate speech from text using Google Cloud TTS API.
        
        Args:
            text: Text to convert to speech
            output_path: Optional custom output path
            
        Returns:
            Path to generated audio file
            
        Raises:
            Exception: If speech generation fails
        """
        # Validate configuration first
        if not self.validate_config():
            raise ValueError("Invalid Google Cloud TTS configuration")
        
        # Validate text input
        if not text or not text.strip():
            raise ValueError("Text input is empty or invalid")
        
        logger.info(f"Google TTS Input validation:")
        logger.info(f"  Original text: '{text}'")
        logger.info(f"  Text length: {len(text)} characters")
        logger.info(f"  Voice: '{self.voice_name}'")
        logger.info(f"  Language: '{self.language_code}'")
        
        # Clean and prepare text for speech
        clean_text = self._sanitize_text_for_speech(text)
        clean_text = self._convert_numbers_to_words(clean_text)
        
        logger.info(f"Google TTS Processing:")
        logger.info(f"  Cleaned text: '{clean_text}'")
        
        try:
            # Prepare the request payload for Google Cloud TTS REST API
            payload = {
                "input": {
                    "text": clean_text
                },
                "voice": {
                    "languageCode": self.language_code,
                    "name": self.voice_name
                },
                "audioConfig": {
                    "audioEncoding": "MP3",
                    "speakingRate": self.speaking_rate,
                    "pitch": 0.0
                }
            }

            # Prepare headers
            headers = {
                "Content-Type": "application/json",
                "X-Goog-Api-Key": self.api_key
            }

            logger.info("Making request to Google Cloud TTS REST API...")
            logger.info(f"Request URL: {self.url}")
            logger.info(f"Request payload: {payload}")
            
            # Make the request
            response = requests.post(
                self.url,
                headers=headers,
                json=payload,
                timeout=30
            )

            logger.info(f"Response status code: {response.status_code}")
            logger.info(f"Response headers: {dict(response.headers)}")

            if response.status_code != 200:
                logger.error(f"Google Cloud TTS API request failed with status {response.status_code}")
                try:
                    error_data = response.json()
                    logger.error(f"Error response: {error_data}")
                except:
                    logger.error(f"Error response text: {response.text}")
                response.raise_for_status()

            # Parse the response
            response_data = response.json()
            
            if "audioContent" not in response_data:
                raise ValueError("No audioContent in response from Google Cloud TTS API")

            # Decode the base64 audio content
            import base64
            audio_content = base64.b64decode(response_data["audioContent"])
            
            logger.info(f"Google Cloud TTS response received: {len(audio_content)} bytes")

            # Determine output path
            if output_path is None:
                # Create temporary file with MP3 extension using temp file manager
                from langflix.utils.temp_file_manager import get_temp_manager
                temp_manager = get_temp_manager()
                # Create temp file with delete=False since it may be used after function returns
                with temp_manager.create_temp_file(suffix=".mp3", prefix="langflix_google_tts_", delete=False) as temp_path:
                    output_path = temp_path
                # Register for cleanup
                temp_manager.register_file(output_path)
            else:
                output_path = Path(output_path)
                # Ensure directory exists
                output_path.parent.mkdir(parents=True, exist_ok=True)

            # Write the decoded audio content to the output file
            with open(output_path, "wb") as out:
                out.write(audio_content)

            # Verify the saved file
            file_size = output_path.stat().st_size
            logger.info(f"Successfully generated Google Cloud TTS audio: {output_path}")
            logger.info(f"Audio file size: {file_size} bytes")

            if file_size == 0:
                raise ValueError(f"Generated audio file is empty: {output_path}")

            return output_path
            
        except Exception as e:
            logger.error(f"Error generating Google Cloud TTS speech: {e}")
            raise
    
    def _sanitize_text_for_speech(self, text: str) -> str:
        """
        Enhanced text sanitization for Google Cloud TTS.
        
        Args:
            text: Raw text input
            
        Returns:
            Cleaned text suitable for speech synthesis
        """
        # Call parent implementation
        text = super()._sanitize_text_for_speech(text)
        
        # Additional Google Cloud TTS specific cleaning
        # Google Cloud TTS handles most characters well, but we can still clean up
        text = text.replace('_', ' ')  # Replace underscores with spaces
        
        # Remove multiple spaces
        text = ' '.join(text.split())
        
        # Ensure text is not empty
        if not text.strip():
            logger.warning("Text is empty after sanitization")
            text = "expression"  # Fallback
        
        return text
