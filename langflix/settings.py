# Settings for the LangFlix application

import os
import platform
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union, List

from .config import ConfigLoader

logger = logging.getLogger(__name__)

def get_default_font():
    """Get appropriate default font based on platform"""
    system = platform.system()
    
    if system == "Darwin":  # macOS
        return "/System/Library/Fonts/AppleSDGothicNeo.ttc"
    elif system == "Linux":
        # Try common Korean fonts on Linux
        for font_path in [
            "/usr/share/fonts/truetype/nanum/NanumGothic.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
        ]:
            if os.path.exists(font_path):
                return font_path
        # Fallback to system default
        return ""
    elif system == "Windows":
        # Try common Korean fonts on Windows
        for font_path in [
            "C:/Windows/Fonts/malgun.ttf",  # Malgun Gothic
            "C:/Windows/Fonts/arial.ttf",   # Arial fallback
        ]:
            if os.path.exists(font_path):
                return font_path
        # Fallback to system default
        return ""
    else:
        return ""

# Initialize YAML configuration loader
config_loader = ConfigLoader()

# Get values from YAML config with fallbacks for backward compatibility
DEFAULT_FONT_FILE = get_default_font()

# Font sizes - loaded from YAML config
FONT_SIZE_DEFAULT = config_loader.get('font', 'sizes', 'default') or 32
FONT_SIZE_EXPRESSION = config_loader.get('font', 'sizes', 'expression') or 48
FONT_SIZE_TRANSLATION = config_loader.get('font', 'sizes', 'translation') or 40
FONT_SIZE_SIMILAR = config_loader.get('font', 'sizes', 'similar') or 32

# LLM settings - loaded from YAML config  
llm_config = config_loader.get('llm') or {}
MAX_LLM_INPUT_LENGTH = llm_config.get('max_input_length') or 8000
TARGET_LANGUAGE = llm_config.get('target_language') or "Korean"
DEFAULT_LANGUAGE_LEVEL = llm_config.get('default_language_level') or "intermediate"

# Language levels - loaded from YAML config with fallbacks
_language_levels_fallback = {
    "beginner": {
        "description": "A1-A2 level. Focus on basic everyday expressions, simple phrasal verbs, and common conversational phrases used in daily life. Avoid complex idioms or advanced vocabulary.",
        "examples": "Let's go, I'm sorry, How are you, Can you help me, What's up"
    },
    "intermediate": {
        "description": "B1-B2 level. Focus on commonly used idiomatic expressions, standard phrasal verbs, and colloquial phrases that appear frequently in casual and professional contexts.",
        "examples": "Get the ball rolling, Call it a day, Piece of cake, Break the ice, On the same page"
    },
    "advanced": {
        "description": "C1-C2 level. Focus on sophisticated idioms, nuanced expressions, professional jargon, and complex colloquialisms that native speakers use in various contexts.",
        "examples": "Read between the lines, Cut to the chase, Play devil's advocate, Bite off more than you can chew"
    },
    "mixed": {
        "description": "All levels. Extract valuable expressions regardless of difficulty level, but prioritize practical, commonly-used phrases that appear in authentic conversations.",
        "examples": "Any useful expression from basic to advanced"
    }
}
LANGUAGE_LEVELS = config_loader.get('language_levels') or _language_levels_fallback

# Video processing configuration - loaded from YAML config with fallbacks
_video_config_fallback = {
    "codec": "libx264",
    "audio_codec": "aac", 
    "preset": "fast",
    "crf": 23,
    "resolution": "1280x720",
    "fps": 30,
    "bitrate": "2000k",
    "audio_bitrate": "128k"
}
VIDEO_CONFIG = config_loader.get('video') or _video_config_fallback

# Configuration management - Updated to use YAML loader
class ConfigManager:
    """Configuration manager for LangFlix settings - Updated to use YAML"""
    
    def __init__(self, config_file: Optional[str] = None):
        # Use the global config_loader for backward compatibility
        self.config_loader = config_loader
        
    def get(self, section: str, key: Optional[str] = None, default: Optional[Union[str, int, float, bool, Dict, List]] = None) -> Union[str, int, float, bool, Dict, List, None]:
        """Get a configuration value
        
        Maintains backward compatibility with old get(section, key, default) API
        but also supports get(section) for full section access
        """
        if key is None:
            # Return entire section
            return self.config_loader.get_section(section)
        else:
            # Return specific key from section
            return self.config_loader.get(section, key, default=default)
    
    def set(self, section: str, key: str, value: Union[str, int, float, bool, Dict, List]) -> None:
        """Set a configuration value - Note: This modifies runtime config only"""
        # For now, we'll update the config_loader's internal config
        # In a full implementation, this would update the user config file
        current_section = self.config_loader.get_section(section)
        current_section[key] = value
        logger.warning("Runtime config changes via set() are not persisted to YAML files")
    
    def save_config(self):
        """Save current configuration to file"""
        # This would need to be implemented to save back to config.yaml
        logger.warning("save_config() not fully implemented for YAML config - use YAML files directly")

# Global configuration instance - maintains backward compatibility
config = ConfigManager()

# Export commonly used settings with fallbacks to config
def get_video_config(attribute: str = None):
    """Get video processing configuration"""
    video_config = config.get("video")
    return video_config.get(attribute) if attribute and isinstance(video_config, dict) else video_config

def get_font_size(size_type: str = "default") -> int:
    """Get font size for different text types"""
    try:
        # Try to get from YAML config first
        font_sizes = config_loader.get('font', 'sizes')
        if isinstance(font_sizes, dict) and size_type in font_sizes:
            return int(font_sizes[size_type])
    except Exception as e:
        logger.debug(f"Error getting font size from config: {e}")
    
    # Fallback to constants for backward compatibility
    fallbacks = {
        'default': FONT_SIZE_DEFAULT,
        'expression': FONT_SIZE_EXPRESSION,
        'translation': FONT_SIZE_TRANSLATION,
        'similar': FONT_SIZE_SIMILAR
    }
    return fallbacks.get(size_type, FONT_SIZE_DEFAULT)

def get_font_file(language_code: str = None) -> str:
    """Get font file path for the given language or default"""
    try:
        # Import language_config here to avoid circular imports
        from .language_config import LanguageConfig
        
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
        
        # Fallback to default font configuration
        font_config = config.get("font")
        if isinstance(font_config, dict):
            font_file = font_config.get("default_file", DEFAULT_FONT_FILE)
        else:
            font_file = DEFAULT_FONT_FILE
        
        # Ensure we return a string
        if isinstance(font_file, str):
            return font_file
        else:
            return str(font_file) if font_file else DEFAULT_FONT_FILE
    except Exception as e:
        logger.warning(f"Error getting font file: {e}")
        return DEFAULT_FONT_FILE

def get_llm_config(key: str = None):
    """Get LLM configuration"""
    llm_config = config.get("llm")
    return llm_config.get(key) if key and isinstance(llm_config, dict) else llm_config

def get_generation_config():
    """Get generation configuration for LLM API calls"""
    llm_cfg = config.get("llm") or {}
    return {
        "temperature": llm_cfg.get('temperature', 0.1),
        "top_p": llm_cfg.get('top_p', 0.8),
        "top_k": llm_cfg.get('top_k', 40),
    }

def get_max_retries():
    """Get maximum retries for API calls"""
    llm_cfg = config.get("llm") or {}
    return llm_cfg.get('max_retries', 3)

def get_retry_backoff_seconds():
    """Get retry backoff times"""
    llm_cfg = config.get("llm") or {}
    return llm_cfg.get('retry_backoff_seconds', [3, 6, 12])

def get_min_expressions_per_chunk():
    """Get minimum expressions per chunk"""
    proc_cfg = config.get("processing") or {}
    return proc_cfg.get('min_expressions_per_chunk', 1)

def get_max_expressions_per_chunk():
    """Get maximum expressions per chunk"""
    proc_cfg = config.get("processing") or {}
    return proc_cfg.get('max_expressions_per_chunk', 3)

def get_tts_config() -> Dict[str, Any]:
    """Get TTS configuration from YAML"""
    tts_cfg = config.get("tts") or {}
    return tts_cfg

def get_tts_provider() -> str:
    """Get TTS provider name"""
    tts_cfg = get_tts_config()
    return tts_cfg.get('provider', 'lemonfox')

def is_tts_enabled() -> bool:
    """Check if TTS is enabled"""
    tts_cfg = get_tts_config()
    return tts_cfg.get('enabled', True)