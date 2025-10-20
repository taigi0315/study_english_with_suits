"""
Text-to-Speech (TTS) module for LangFlix
Provides swappable TTS client architecture for multiple providers
"""

from .factory import create_tts_client
from .base import TTSClient

__all__ = ['create_tts_client', 'TTSClient']

