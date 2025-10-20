"""Font utility functions for platform-specific font detection."""

import os
import platform
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def get_platform_default_font() -> str:
    """
    Get appropriate default font based on platform.
    
    Returns:
        str: Path to platform-specific default font, or empty string if not found
    """
    system = platform.system()
    
    if system == "Darwin":  # macOS
        font_path = "/System/Library/Fonts/AppleSDGothicNeo.ttc"
        if os.path.exists(font_path):
            logger.debug(f"Using macOS default font: {font_path}")
            return font_path
        logger.warning("macOS default font not found")
        return ""
        
    elif system == "Linux":
        # Try common Korean fonts on Linux
        linux_fonts = [
            "/usr/share/fonts/truetype/nanum/NanumGothic.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
        ]
        for font_path in linux_fonts:
            if os.path.exists(font_path):
                logger.debug(f"Using Linux font: {font_path}")
                return font_path
        logger.warning("No suitable Linux fonts found, falling back to system default")
        return ""
        
    elif system == "Windows":
        # Try common Korean fonts on Windows
        windows_fonts = [
            "C:/Windows/Fonts/malgun.ttf",  # Malgun Gothic
            "C:/Windows/Fonts/arial.ttf",   # Arial fallback
        ]
        for font_path in windows_fonts:
            if os.path.exists(font_path):
                logger.debug(f"Using Windows font: {font_path}")
                return font_path
        logger.warning("No suitable Windows fonts found, falling back to system default")
        return ""
        
    else:
        logger.warning(f"Unknown platform: {system}, cannot detect default font")
        return ""


def get_font_file_for_language(language_code: Optional[str] = None) -> str:
    """
    Get font file path for the given language or default.
    
    Args:
        language_code: Optional language code (e.g., 'ko', 'ja', 'zh')
        
    Returns:
        str: Path to appropriate font file
    """
    # Import here to avoid circular imports
    try:
        from ..language_config import LanguageConfig
        
        # If language code is provided, try to get language-specific font
        if language_code:
            try:
                font_path = LanguageConfig.get_font_path(language_code)
                if font_path and os.path.exists(font_path):
                    logger.info(f"Using language-specific font for {language_code}: {font_path}")
                    return font_path
                else:
                    logger.warning(f"Language-specific font not found for {language_code}, falling back to default")
            except Exception as e:
                logger.warning(f"Error getting font for language {language_code}: {e}")
    except ImportError:
        logger.warning("LanguageConfig not available, using platform default")
    
    # Fallback to platform default
    return get_platform_default_font()

