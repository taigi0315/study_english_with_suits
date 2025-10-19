# Settings for the LangFlix application

import os
import platform
import json
from pathlib import Path
from typing import Dict, Any, Optional, Union, List

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

# Default font configuration
DEFAULT_FONT_FILE = get_default_font()
FONT_SIZE_DEFAULT = 32
FONT_SIZE_EXPRESSION = 48  # For main expression text
FONT_SIZE_TRANSLATION = 40  # For translation text
FONT_SIZE_SIMILAR = 32  # For similar expressions

# The maximum number of characters to include in a single prompt to the LLM.
# Gemini 2.5 Flash supports up to 1,048,576 tokens (~4M characters)
# We use a conservative limit to ensure prompt + dialogue fits comfortably
MAX_LLM_INPUT_LENGTH = 3000  # Even smaller for test mode to avoid API timeouts

# The target language for translation.
TARGET_LANGUAGE = "Korean"

# Default language level for expression analysis
DEFAULT_LANGUAGE_LEVEL = "intermediate"

LANGUAGE_LEVELS = {
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

# Video processing configuration
VIDEO_CONFIG = {
    "codec": "libx264",
    "audio_codec": "aac", 
    "preset": "fast",
    "crf": 23,  # Constant Rate Factor (lower = higher quality)
    "resolution": "1280x720",
    "fps": 30,
    "bitrate": "2000k",
    "audio_bitrate": "128k"
}

# Configuration management
class ConfigManager:
    """Configuration manager for LangFlix settings"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = Path(config_file) if config_file else Path("langflix_config.json")
        self.config = self._load_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            "video": VIDEO_CONFIG,
            "font": {
                "default_file": get_default_font(),
                "sizes": {
                    "default": 32,
                    "expression": 48,
                    "translation": 40,
                    "similar": 32
                }
            },
            "llm": {
                "max_input_length": MAX_LLM_INPUT_LENGTH,
                "default_language_level": DEFAULT_LANGUAGE_LEVEL,
                "target_language": TARGET_LANGUAGE
            },
            "processing": {
                "chunk_size": 5000,
                "max_expressions_per_chunk": 5,
                "temp_file_cleanup": True
            }
        }
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    default_config = self._get_default_config()
                    return self._merge_config(default_config, config)
            except Exception as e:
                print(f"Warning: Could not load config file {self.config_file}: {e}")
                return self._get_default_config()
        else:
            return self._get_default_config()
    
    def _merge_config(self, default: Dict[str, Any], user: Dict[str, Any]) -> Dict[str, Any]:
        """Merge user config with defaults"""
        result = default.copy()
        for key, value in user.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_config(result[key], value)
            else:
                result[key] = value
        return result
    
    def save_config(self):
        """Save current configuration to file"""
        try:
            self.config_file.parent.mkdir(exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Could not save config file {self.config_file}: {e}")
    
    def get(self, section: str, key: str, default: Optional[Union[str, int, float, bool, Dict, List]] = None) -> Union[str, int, float, bool, Dict, List, None]:
        """Get a configuration value"""
        return self.config.get(section, {}).get(key, default)
    
    def set(self, section: str, key: str, value: Union[str, int, float, bool, Dict, List]) -> None:
        """Set a configuration value"""
        if section not in self.config:
            self.config[section] = {}
        self.config[section][key] = value

# Global configuration instance
config = ConfigManager()

# Export commonly used settings with fallbacks to config
def get_video_config(attribute: str = None):
    """Get video processing configuration"""
    video_config = config.get("video", {})
    return video_config.get(attribute) if attribute else video_config

def get_font_size(size_type: str = "default") -> int:
    """Get font size for different text types"""
    return config.get("font", {}).get("sizes", {}).get(size_type, FONT_SIZE_DEFAULT)

def get_font_file() -> str:
    """Get default font file path"""
    try:
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
    except Exception:
        return DEFAULT_FONT_FILE

def get_llm_config(key: str = None):
    """Get LLM configuration"""
    llm_config = config.get("llm", {})
    return llm_config.get(key) if key else llm_config