#!/usr/bin/env python3
"""
Language Configuration for LangFlix
Provides language-specific settings for different target languages
"""

from typing import Dict, Any
from pathlib import Path

class LanguageConfig:
    """
    Language-specific configuration for different target languages
    """
    
    # Language configurations
    LANGUAGE_CONFIGS = {
        'ko': {
            'name': 'Korean',
            'font_path': '/System/Library/Fonts/AppleSDGothicNeo.ttc',
            'font_fallback': '/System/Library/Fonts/Supplemental/AppleGothic.ttf',
            'prompt_language': 'Korean',
            'translation_style': 'natural',
            'character_encoding': 'utf-8'
        },
        'ja': {
            'name': 'Japanese',
            'font_path': '/System/Library/Fonts/Hiragino Sans GB.ttc',
            'font_fallback': '/System/Library/Fonts/ヒラギノ角ゴシック W8.ttc',
            'prompt_language': 'Japanese',
            'translation_style': 'natural',
            'character_encoding': 'utf-8'
        },
        'zh': {
            'name': 'Chinese',
            'font_path': '/System/Library/Fonts/Hiragino Sans GB.ttc',
            'font_fallback': '/System/Library/Fonts/STHeiti Medium.ttc',
            'prompt_language': 'Chinese',
            'translation_style': 'natural',
            'character_encoding': 'utf-8'
        },
        'es': {
            'name': 'Spanish',
            'font_path': '/System/Library/Fonts/HelveticaNeue.ttc',
            'font_fallback': '/System/Library/Fonts/Arial.ttf',
            'prompt_language': 'Spanish',
            'translation_style': 'natural',
            'character_encoding': 'utf-8'
        },
        'fr': {
            'name': 'French',
            'font_path': '/System/Library/Fonts/HelveticaNeue.ttc',
            'font_fallback': '/System/Library/Fonts/Arial.ttf',
            'prompt_language': 'French',
            'translation_style': 'natural',
            'character_encoding': 'utf-8'
        }
    }
    
    @classmethod
    def get_config(cls, language_code: str) -> Dict[str, Any]:
        """
        Get language configuration
        
        Args:
            language_code: Language code (e.g., 'ko', 'ja', 'zh')
            
        Returns:
            Language configuration dictionary
        """
        if language_code not in cls.LANGUAGE_CONFIGS:
            # Fallback to Korean if language not supported
            language_code = 'ko'
        
        return cls.LANGUAGE_CONFIGS[language_code]
    
    @classmethod
    def get_font_path(cls, language_code: str) -> str:
        """
        Get font path for language
        
        Args:
            language_code: Language code
            
        Returns:
            Font file path
        """
        config = cls.get_config(language_code)
        
        # Check if primary font exists
        font_path = Path(config['font_path'])
        if font_path.exists():
            return str(font_path)
        
        # Fallback to secondary font
        fallback_path = Path(config['font_fallback'])
        if fallback_path.exists():
            return str(fallback_path)
        
        # Final fallback to system default
        return '/System/Library/Fonts/Arial.ttf'
    
    @classmethod
    def get_prompt_language(cls, language_code: str) -> str:
        """
        Get prompt language name
        
        Args:
            language_code: Language code
            
        Returns:
            Language name for prompts
        """
        config = cls.get_config(language_code)
        return config['prompt_language']
    
    @classmethod
    def get_supported_languages(cls) -> list:
        """
        Get list of supported language codes
        
        Returns:
            List of supported language codes
        """
        return list(cls.LANGUAGE_CONFIGS.keys())
    
    @classmethod
    def is_supported(cls, language_code: str) -> bool:
        """
        Check if language is supported
        
        Args:
            language_code: Language code to check
            
        Returns:
            True if language is supported
        """
        return language_code in cls.LANGUAGE_CONFIGS
