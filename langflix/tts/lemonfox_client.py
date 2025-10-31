"""
LemonFox TTS Client implementation
"""

import os
import logging
import tempfile
import requests
from pathlib import Path
from typing import Optional

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

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
        
        # Validate text input
        if not text or not text.strip():
            raise ValueError("Text input is empty or invalid")
        
        logger.info(f"TTS Input validation:")
        logger.info(f"  Original text: '{text}'")
        logger.info(f"  Text length: {len(text)} characters")
        logger.info(f"  Text type: {type(text)}")
        
        # Clean and prepare text for speech
        clean_text = self._sanitize_text_for_speech(text)
        clean_text = self._convert_numbers_to_words(clean_text)
        
        logger.info(f"TTS Processing:")
        logger.info(f"  Cleaned text: '{clean_text}'")
        logger.info(f"  Cleaned length: {len(clean_text)} characters")
        logger.info(f"  Voice: '{self.voice}'")
        logger.info(f"  Format: '{self.response_format}'")
        
        # Prepare API request headers with proper API key format
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "LangFlix-TTS/1.0"
        }
        
        # Prepare request data with proper field names for LemonFox API
        data = {
            "input": clean_text,
            "voice": self.voice,
            "response_format": self.response_format
            # Remove model parameter as it might not be supported
        }
        
        try:
            # Make API request with better error handling
            logger.info(f"Making API request to: {self.url}")
            logger.info(f"Using API key (first 10 chars): {self.api_key[:10]}...")
            logger.info(f"Full API key length: {len(self.api_key)} characters")
            logger.info(f"API key ends with: ...{self.api_key[-4:]}")
            logger.info(f"Request data: {data}")
            logger.info(f"Request headers: {headers}")
            
            # Validate API key format before making request
            if len(self.api_key) < 20:
                logger.warning(f"API key seems too short ({len(self.api_key)} chars) - this might cause authentication issues")
            
            response = requests.post(
                self.url, 
                headers=headers, 
                json=data, 
                timeout=60,  # Increased timeout for TTS generation
                stream=False  # Don't stream the response for audio
            )
            
            # Debug response details
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response headers: {dict(response.headers)}")
            logger.info(f"Response content length: {len(response.content)} bytes")
            
            # Handle non-successful responses
            if response.status_code != 200:
                logger.error(f"API request failed with status {response.status_code}")
                try:
                    error_data = response.json()
                    logger.error(f"Error details: {error_data}")
                except:
                    logger.error(f"Error response text: {response.text[:500]}")
                
                if response.status_code == 401:
                    raise ValueError("Invalid API key - please check your LEMONFOX_API_KEY environment variable")
                elif response.status_code == 429:
                    raise ValueError("API rate limit exceeded - please try again later")
                else:
                    response.raise_for_status()
            
            # Verify we got binary audio content
            content_type = response.headers.get('content-type', '').lower()
            logger.info(f"Content-Type: {content_type}")
            
            # Check if response is likely audio content
            expected_content_types = [
                'audio/mpeg', 'audio/mp3', 'audio/wav', 'audio/wave',
                'application/octet-stream', 'binary/octet-stream'
            ]
            
            if not any(ct in content_type for ct in expected_content_types) and len(response.content) > 0:
                # Check if it's an error response in JSON format
                try:
                    error_data = response.json()
                    logger.error(f"Received JSON error response: {error_data}")
                    raise ValueError(f"API returned error: {error_data}")
                except ValueError:
                    # Not JSON, might be plain text error
                    if len(response.content) < 500:
                        error_text = response.text[:500]
                        logger.error(f"Non-audio response: {error_text}")
                        raise ValueError(f"API returned non-audio response: {error_text}")
            
            # Validate minimum content size (very small responses are likely errors)
            min_size = 1000  # 1KB minimum for audio
            if len(response.content) < min_size:
                logger.warning(f"Response content very small ({len(response.content)} bytes)")
                if len(response.content) < 200:
                    # Show first 200 chars for debugging
                    content_preview = response.content[:200]
                    try:
                        preview_text = content_preview.decode('utf-8')
                        logger.error(f"Content preview (likely error): {preview_text}")
                    except:
                        logger.error(f"Content preview (bytes): {content_preview}")
                    raise ValueError(f"Response too small to be valid audio ({len(response.content)} bytes)")
            
            # Determine output path
            if output_path is None:
                # Create temporary file with proper extension using temp file manager
                from langflix.utils.temp_file_manager import get_temp_manager
                temp_manager = get_temp_manager()
                suffix = f".{self.response_format}"
                # Create temp file with delete=False since it may be used after function returns
                with temp_manager.create_temp_file(suffix=suffix, prefix="langflix_tts_", delete=False) as temp_path:
                    output_path = temp_path
                # Register for cleanup
                temp_manager.register_file(output_path)
            else:
                output_path = Path(output_path)
                # Ensure directory exists
                output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save audio content with atomic write
            temp_output = output_path.with_suffix(f".tmp{output_path.suffix}")
            
            try:
                with open(temp_output, "wb") as f:
                    f.write(response.content)
                
                # Verify written content before moving
                temp_size = temp_output.stat().st_size
                if temp_size != len(response.content):
                    raise ValueError(f"File write size mismatch: expected {len(response.content)}, got {temp_size}")
                
                # Atomically move to final destination
                temp_output.replace(output_path)
                logger.info(f"Audio content written to: {output_path}")
                
            except Exception as write_error:
                # Clean up temporary file on error
                if temp_output.exists():
                    temp_output.unlink()
                raise write_error
            
            # Final verification
            if not output_path.exists():
                raise ValueError(f"Output file was not created: {output_path}")
            
            file_size = output_path.stat().st_size
            logger.info(f"Successfully generated speech audio: {output_path}")
            logger.info(f"Audio file size: {file_size} bytes")
            
            # Validate final file size
            if file_size == 0:
                raise ValueError(f"Generated audio file is empty: {output_path}")
            
            if file_size < min_size:
                logger.warning(f"Generated audio file is very small: {file_size} bytes")
            
            return output_path
            
        except requests.exceptions.Timeout:
            logger.error("LemonFox API request timed out")
            raise ValueError("TTS API request timed out - please try again")
        except requests.exceptions.RequestException as e:
            logger.error(f"LemonFox API request failed: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response status: {e.response.status_code}")
                try:
                    logger.error(f"API response: {e.response.text}")
                except:
                    logger.error(f"API response (bytes): {e.response.content[:500]}")
            raise ValueError(f"TTS API request failed: {e}")
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

