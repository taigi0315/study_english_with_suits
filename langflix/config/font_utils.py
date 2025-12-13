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


def get_font_file_for_language(language_code: Optional[str] = None, use_case: str = "default") -> str:
    """
    Get font file path for the given language or default.
    Prioritizes TTF/TTC files that work with FFmpeg drawtext filter.
    
    Args:
        language_code: Optional language code (e.g., 'ko', 'ja', 'zh', 'es')
        use_case: Specific use case ('default', 'dialogue', 'keywords', 'expression', 'translation', 'vocabulary', 'educational_slide', 'title')
        
    Returns:
        str: Path to appropriate font file
    """
    # Import here to avoid circular imports
    try:
        from ..core.language_config import LanguageConfig
        from langflix import settings
        
        # Priority 0: For target languages that need to display mixed content (Korean source + translated text),
        # we need a font that supports BOTH CJK (Korean) AND Latin accents (Spanish é, ó, etc.)
        # AppleSDGothicNeo supports BOTH - Korean chars + Latin Extended including accents
        if language_code == 'es' and platform.system() == "Darwin":
             try:
                # AppleSDGothicNeo is ideal: supports Korean (CJK) + Spanish accents (Latin Extended)
                # Tested: é (U+E9), ó (U+F3), ñ (U+F1), ¿ (U+BF), ¡ (U+A1) all render correctly
                mixed_content_fonts = [
                    "/System/Library/Fonts/AppleSDGothicNeo.ttc",  # Supports Korean + Spanish accents
                    "/System/Library/Fonts/Supplemental/Arial Unicode MS.ttf",  # Universal fallback
                ]
                for safe_font in mixed_content_fonts:
                    if os.path.exists(safe_font):
                        logger.debug(f"Using {safe_font} for Spanish (mixed Korean+Spanish content)")
                        return safe_font
             except Exception:
                 pass
        
        # Retrieve per-language font configuration
        try:
            language_fonts_config = settings.get_language_fonts_config()
            
            # Helper to check and resolve font path
            def resolve_font(config_section, key):
                if not config_section or key not in config_section:
                    return None
                
                font_rel_path = config_section[key]
                # If path contains 'assets/fonts', verify it relative to project root
                if "assets/fonts" in font_rel_path:
                    # Construct absolute path: current_file -> config -> langflix -> ROOT
                    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                    abs_path = os.path.join(project_root, font_rel_path)
                    if os.path.exists(abs_path):
                        return abs_path
                    else:
                        logger.warning(f"Configured font path not found: {abs_path}")
                
                # If just a direct path, check it
                if os.path.exists(font_rel_path):
                    return font_rel_path
                return None

            # 1. Lookup: language_code -> use_case
            if language_code and language_code in language_fonts_config:
                font = resolve_font(language_fonts_config[language_code], use_case)
                if font: 
                    logger.debug(f"Using configured font for {language_code}/{use_case}: {font}")
                    return font

                # 2. Lookup: language_code -> default
                font = resolve_font(language_fonts_config[language_code], "default")
                if font: 
                    logger.debug(f"Using configured default font for {language_code}: {font}")
                    return font

            # 3. Lookup: default -> use_case
            if "default" in language_fonts_config:
                font = resolve_font(language_fonts_config["default"], use_case)
                if font: 
                    logger.debug(f"Using global default font for {use_case}: {font}")
                    return font
            
            # 4. Lookup: default -> default
            if "default" in language_fonts_config:
                font = resolve_font(language_fonts_config["default"], "default")
                if font: return font

        except Exception as e:
            logger.warning(f"Error accessing per-language font config: {e}")

        # Fallback to existing logic if config lookup fails
        # Priority 1: Check if educational slide font is configured and available (Maplestory Bold)
        # This is the "safe" font that supports both Source (Korean) and Target (English)
        try:
            edu_font = settings.get_educational_slide_font_path()
            if edu_font and os.path.exists(edu_font):
                logger.debug(f"Using configured educational font as priority: {edu_font}")
                return edu_font
        except Exception as e:
            logger.warning(f"Error checking educational font: {e}")
        
        # If language code is provided, try to get language-specific font
        if language_code:
            try:
                font_path = LanguageConfig.get_font_path(language_code)
                if font_path and os.path.exists(font_path):
                    logger.info(f"Using language-specific font for {language_code}: {font_path}")
                    return font_path
                else:
                    logger.warning(f"Language-specific font not found for {language_code}, trying platform-specific fonts")
                    
                    # For Linux/Docker, try to find CJK fonts directly
                    if platform.system() == "Linux":
                        if language_code in ['ko', 'ja', 'zh']:
                            # Try Noto Sans CJK (installed in Dockerfile)
                            cjk_fonts = [
                                "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                                "/usr/share/fonts/truetype/nanum/NanumGothic.ttc",
                                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                            ]
                            for font_path in cjk_fonts:
                                if os.path.exists(font_path):
                                    logger.info(f"Using Linux CJK font for {language_code}: {font_path}")
                                    return font_path
                    
                    # Special handling for Spanish - try recommended fonts
                    if language_code == 'es':
                        spanish_fonts = LanguageConfig.get_spanish_font_recommendations()
                        if spanish_fonts:
                            logger.info(f"Using Spanish-compatible font: {spanish_fonts[0]}")
                            return spanish_fonts[0]
                        
            except Exception as e:
                logger.warning(f"Error getting font for language {language_code}: {e}")
    except ImportError:
        logger.warning("LanguageConfig not available, using platform default")
    
    # Fallback to platform default
    return get_platform_default_font()

def validate_spanish_font_support() -> dict:
    """
    Validate Spanish font support on the current system.
    
    Returns:
        Dictionary with validation results
    """
    try:
        from ..core.language_config import LanguageConfig
        return LanguageConfig.validate_font_for_language('es')
    except ImportError:
        return {
            'validation_status': 'error',
            'error': 'LanguageConfig not available'
        }


def get_fonts_dir() -> str:
    """
    Get platform-specific fonts directory for FFmpeg subtitles filter.
    
    Returns:
        str: Path to fonts directory for the current platform
    """
    system = platform.system()
    
    if system == "Darwin":  # macOS
        return "/System/Library/Fonts"
    elif system == "Linux":
        return "/usr/share/fonts"
    elif system == "Windows":
        return "C:/Windows/Fonts"
    else:
        # Fallback to Linux path (most common for Docker)
        logger.warning(f"Unknown platform: {system}, using Linux fonts directory")
        return "/usr/share/fonts"


def get_font_name_for_ffmpeg(font_path: Optional[str] = None, language_code: Optional[str] = None) -> str:
    """
    Get font name for FFmpeg FontName parameter.
    
    Args:
        font_path: Optional font file path
        language_code: Optional language code (e.g., 'ko', 'ja', 'zh')
        
    Returns:
        str: Font name for FFmpeg
    """
    system = platform.system()
    
    # If font path is provided, try to determine font name from path
    if font_path:
        if 'AppleSDGothicNeo' in font_path or 'Apple SD Gothic Neo' in font_path:
            return "Apple SD Gothic Neo"
        elif 'NanumGothic' in font_path or 'Nanum Gothic' in font_path:
            return "NanumGothic"
        elif 'NotoSansCJK' in font_path or 'Noto Sans CJK' in font_path:
            return "Noto Sans CJK"
        elif 'Hiragino' in font_path:
            return "Hiragino Sans"
        elif 'HelveticaNeue' in font_path:
            return "Helvetica Neue"
        elif 'malgun' in font_path.lower():
            return "Malgun Gothic"
    
    # Platform-specific defaults
    if system == "Darwin":  # macOS
        return "Apple SD Gothic Neo"
    elif system == "Linux":
        # Check if Noto or Nanum fonts are available
        if os.path.exists("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"):
            return "Noto Sans CJK"
        elif os.path.exists("/usr/share/fonts/truetype/nanum/NanumGothic.ttc"):
            return "NanumGothic"
        else:
            return "DejaVu Sans"  # Fallback
    elif system == "Windows":
        return "Malgun Gothic"
    else:
        return "Arial"  # Ultimate fallback

