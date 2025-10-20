"""
Base TTS client interface for swappable text-to-speech providers
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)


class TTSClient(ABC):
    """
    Abstract base class for Text-to-Speech clients.
    
    All TTS provider implementations should inherit from this class
    and implement the required abstract methods.
    """
    
    @abstractmethod
    def generate_speech(self, text: str, output_path: Path = None) -> Path:
        """
        Generate speech audio from text.
        
        Args:
            text: The text to convert to speech
            output_path: Optional output path for the audio file
            
        Returns:
            Path to the generated audio file
            
        Raises:
            Exception: If speech generation fails
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
    
    def _sanitize_text_for_speech(self, text: str) -> str:
        """
        Clean and prepare text for speech synthesis.
        Base implementation that can be overridden by subclasses.
        
        Args:
            text: Raw text input
            
        Returns:
            Cleaned text suitable for speech synthesis
        """
        # Remove leading/trailing whitespace
        text = text.strip()
        
        # Remove special characters that might cause issues
        # Keep alphanumeric, spaces, basic punctuation
        allowed_chars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .,!?'-")
        text = ''.join(c for c in text if c in allowed_chars)
        
        # Normalize whitespace
        text = ' '.join(text.split())
        
        return text
    
    def _convert_numbers_to_words(self, text: str) -> str:
        """
        Convert numbers in text to words.
        
        Args:
            text: Text containing numbers
            
        Returns:
            Text with numbers converted to words
        """
        try:
            import inflect
            p = inflect.engine()
            
            # Split text into words
            words = text.split()
            result = []
            
            for word in words:
                # Check if word is a number
                if word.isdigit():
                    # Convert to words
                    word_form = p.number_to_words(word)
                    result.append(word_form)
                else:
                    # Check for numbers in mixed format (e.g., "2nd", "1st")
                    cleaned_word = word
                    for char in word:
                        if char.isdigit():
                            # Try to convert parts with numbers
                            try:
                                num_str = ''.join(c for c in word if c.isdigit())
                                if num_str:
                                    word_form = p.number_to_words(num_str)
                                    cleaned_word = word.replace(num_str, word_form)
                                    break
                            except:
                                pass
                    result.append(cleaned_word)
            
            return ' '.join(result)
            
        except ImportError:
            logger.warning("inflect library not available, skipping number-to-word conversion")
            return text
        except Exception as e:
            logger.warning(f"Error converting numbers to words: {e}")
            return text

