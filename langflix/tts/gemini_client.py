"""
Gemini Text-to-Speech client implementation using Google GenAI API
Based on: https://ai.google.dev/gemini-api/docs/speech-generation
"""

import os
import logging
import tempfile
import wave
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Google GenAI not available: {e}")
    genai = None
    types = None
    GENAI_AVAILABLE = False

from .base import TTSClient


def wave_file(filename, pcm, channels=1, rate=24000, sample_width=2):
    """Helper function to save PCM data as WAV file"""
    with wave.open(filename, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(rate)
        wf.writeframes(pcm)


class GeminiTTSClient(TTSClient):
    """
    Text-to-Speech client for Gemini TTS API using Google GenAI.
    
    Uses the gemini-2.5-flash-preview-tts model for more natural-sounding speech generation.
    Based on: https://ai.google.dev/gemini-api/docs/speech-generation
    """
    
    def __init__(self, api_key: str = None, voice_name: str = "Kore", 
                 language_code: str = "en-us", speaking_rate: str = "medium",
                 pitch: str = "0st", model_name: str = "gemini-2.5-flash-preview-tts"):
        """
        Initialize Gemini TTS client using Google GenAI library.
        
        Args:
            api_key: Google API key (GEMINI_API_KEY)
            voice_name: Voice name to use (default: "Kore")
            language_code: Language code (default: "en-us")
            speaking_rate: SSML speaking rate (default: "medium", options: x-slow, slow, medium, fast, x-fast, or percentage like "0.8")
            pitch: SSML pitch (default: "0st", options: x-low, low, medium, high, x-high, percentage like "+10%", or semitones like "-2st")
            model_name: Gemini model name (default: "gemini-2.5-flash-preview-tts")
        """
        if not GENAI_AVAILABLE:
            raise ImportError("Google GenAI library not available. Please install: pip install google-genai")
        
        self.api_key = api_key
        self.voice_name = voice_name
        self.language_code = language_code
        self.speaking_rate = speaking_rate
        self.pitch = pitch
        self.model_name = model_name
        
        if not api_key:
            logger.warning("No API key provided for Gemini TTS")
        
        # Initialize the GenAI client with API key
        self.client = genai.Client(api_key=api_key)
        
        logger.info(f"Initialized Gemini TTS client with:")
        logger.info(f"  Voice: {voice_name}")
        logger.info(f"  Model: {model_name}")
        logger.info(f"  Language: {language_code}")
        logger.info(f"  Rate: {speaking_rate}")
        logger.info(f"  Pitch: {pitch}")
        logger.info(f"Using Google GenAI library with model: {model_name}")
    
    def validate_config(self) -> bool:
        """
        Validate Gemini TTS client configuration.
        
        Returns:
            True if configuration is valid
        """
        if not self.api_key:
            logger.error("Gemini TTS API key is missing")
            return False
        
        if not self.voice_name:
            logger.error("Gemini TTS voice name is not specified")
            return False
        
        if not self.language_code:
            logger.error("Gemini TTS language code is not specified")
            return False
        
        if not self.model_name:
            logger.error("Gemini TTS model name is not specified")
            return False
        
        return True
    
    def generate_speech(self, text: str, output_path: Path = None) -> Path:
        """
        Generate speech from text using Gemini TTS API via Google GenAI library.
        
        Args:
            text: Text to convert to speech
            output_path: Optional custom output path
            
        Returns:
            Path to generated audio file (WAV format)
            
        Raises:
            Exception: If speech generation fails
        """
        # Validate configuration first
        if not self.validate_config():
            raise ValueError("Invalid Gemini TTS configuration")
        
        # Validate text input
        if not text or not text.strip():
            raise ValueError("Text input is empty or invalid")
        
        logger.info(f"Gemini TTS Input validation:")
        logger.info(f"  Original text: '{text}'")
        logger.info(f"  Text length: {len(text)} characters")
        logger.info(f"  Voice: '{self.voice_name}'")
        logger.info(f"  Model: '{self.model_name}'")
        logger.info(f"  Language: '{self.language_code}'")
        
        # Try to convert numbers to words if inflect is available
        try:
            import inflect
            p = inflect.engine()
            words = text.split()
            converted_words = []
            for word in words:
                if word.isdigit():
                    converted_words.append(p.number_to_words(word))
                else:
                    converted_words.append(word)
            text = " ".join(converted_words)
            logger.info(f"  Converted numbers to words: '{text}'")
        except ImportError:
            logger.warning("inflect library not available, skipping number-to-word conversion")
        except Exception as e:
            logger.warning(f"Failed to convert numbers to words: {e}")
        
        # Clean text
        text_cleaned = text.strip()
        
        # Apply SSML formatting if rate or pitch are not default
        if self.speaking_rate != "medium" or self.pitch != "0st":
            ssml_text = f'<speak><prosody rate="{self.speaking_rate}" pitch="{self.pitch}">{text_cleaned}</prosody></speak>'
            logger.info(f"Applied SSML formatting with rate='{self.speaking_rate}' and pitch='{self.pitch}'")
            contents_text = ssml_text
        else:
            contents_text = text_cleaned
        
        logger.info(f"Gemini TTS Processing:")
        logger.info(f"  Text: '{text_cleaned}'")
        logger.info(f"  Rate: {self.speaking_rate}, Pitch: {self.pitch}")
        
        # Generate output path
        if output_path is None:
            output_path = Path(tempfile.mktemp(suffix='.wav', prefix='langflix_gemini_tts_'))
        else:
            output_path = Path(output_path)
            # Ensure we have .wav extension for the new API
            if output_path.suffix.lower() != '.wav':
                output_path = output_path.with_suffix('.wav')
        
        try:
            logger.info(f"Making request to Gemini TTS API...")
            logger.info(f"Model: {self.model_name}, Voice: {self.voice_name}")
            
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=contents_text,
                config=types.GenerateContentConfig(
                    response_modalities=["AUDIO"],
                    speech_config=types.SpeechConfig(
                        voice_config=types.VoiceConfig(
                            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                voice_name=self.voice_name,
                            )
                        )
                    ),
                )
            )
            
            logger.info(f"Response received from Gemini TTS API")
            
            # Extract audio data from response
            if not response.candidates:
                raise Exception("No candidates in response")
            
            candidate = response.candidates[0]
            if not candidate.content or not candidate.content.parts:
                raise Exception("No content parts in response")
            
            part = candidate.content.parts[0]
            if not part.inline_data or not part.inline_data.data:
                raise Exception("No audio data in response")
            
            audio_data = part.inline_data.data
            logger.info(f"Gemini TTS response received: {len(audio_data)} bytes of PCM data")
            
            # Save as WAV file using the wave_file helper
            wave_file(str(output_path), audio_data)
            
            # Verify file was created and has content
            if not output_path.exists():
                raise Exception(f"Failed to create audio file: {output_path}")
            
            file_size = output_path.stat().st_size
            if file_size == 0:
                raise Exception(f"Generated audio file is empty: {output_path}")
            
            logger.info(f"Successfully generated Gemini TTS audio: {output_path}")
            logger.info(f"Audio file size: {file_size} bytes")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error in Gemini TTS generate_speech: {e}")
            raise Exception(f"Gemini TTS generation failed: {e}")

