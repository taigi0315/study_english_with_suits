#!/usr/bin/env python3
"""
Language Configuration for LangFlix
Provides language-specific settings for different target languages
"""

from typing import Dict, Any, List
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
            'font_fallback': [
                '/System/Library/Fonts/Arial.ttf',
                '/System/Library/Fonts/Helvetica.ttc',
                '/System/Library/Fonts/Times.ttc',
                '/System/Library/Fonts/Supplemental/Arial Unicode MS.ttf'
            ],
            'prompt_language': 'Spanish',
            'translation_style': 'natural',
            'character_encoding': 'utf-8',
            'special_characters': 'ñáéíóúüÑÁÉÍÓÚÜ¿¡'
        },
        'fr': {
            'name': 'French',
            'font_path': '/System/Library/Fonts/HelveticaNeue.ttc',
            'font_fallback': '/System/Library/Fonts/Arial.ttf',
            'prompt_language': 'French',
            'translation_style': 'natural',
            'character_encoding': 'utf-8'
        },
        'en': {
            'name': 'English',
            'font_path': '/System/Library/Fonts/HelveticaNeue.ttc',
            'font_fallback': '/System/Library/Fonts/Arial.ttf',
            'prompt_language': 'English',
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
        Get font path for language with fallback support
        
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
        
        # Handle fallback fonts (can be string or list)
        fallback = config.get('font_fallback')
        if fallback:
            if isinstance(fallback, list):
                # Try each fallback font in order
                for fallback_font in fallback:
                    fallback_path = Path(fallback_font)
                    if fallback_path.exists():
                        return str(fallback_path)
            else:
                # Single fallback font (backward compatibility)
                fallback_path = Path(fallback)
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
    def validate_font_for_language(cls, language_code: str) -> Dict[str, Any]:
        """
        Validate font support for language-specific characters
        
        Args:
            language_code: Language code
            
        Returns:
            Dictionary with validation results
        """
        config = cls.get_config(language_code)
        font_path = cls.get_font_path(language_code)
        special_chars = config.get('special_characters', '')
        
        result = {
            'language_code': language_code,
            'font_path': font_path,
            'font_exists': Path(font_path).exists(),
            'special_characters': special_chars,
            'validation_status': 'unknown'
        }
        
        if not result['font_exists']:
            result['validation_status'] = 'font_missing'
            result['error'] = f"Font file not found: {font_path}"
            return result
        
        # For now, assume font is valid if it exists
        # TODO: Add actual character support validation using fonttools or similar
        result['validation_status'] = 'valid'
        
        return result
    
    @classmethod
    def get_spanish_font_recommendations(cls) -> List[str]:
        """
        Get recommended fonts for Spanish language support
        
        Returns:
            List of recommended font paths
        """
        recommendations = [
            '/System/Library/Fonts/HelveticaNeue.ttc',
            '/System/Library/Fonts/Arial.ttf', 
            '/System/Library/Fonts/Helvetica.ttc',
            '/System/Library/Fonts/Times.ttc',
            '/System/Library/Fonts/Supplemental/Arial Unicode MS.ttf',
            '/System/Library/Fonts/Avenir.ttc',
            '/System/Library/Fonts/San Francisco/SF-Pro-Text-Regular.otf'
        ]
        
        # Filter to only existing fonts
        existing_fonts = []
        for font_path in recommendations:
            if Path(font_path).exists():
                existing_fonts.append(font_path)
        
        return existing_fonts
    
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
