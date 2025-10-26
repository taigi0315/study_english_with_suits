"""
Settings management for LangFlix application.

This module provides simple accessor functions for configuration values.
All configuration is stored in YAML files (default.yaml, config.yaml).
"""

import logging
from typing import Dict, Any, Optional, List

from .config import ConfigLoader
from .config.font_utils import get_platform_default_font, get_font_file_for_language

logger = logging.getLogger(__name__)

# Single source of configuration
_config_loader = ConfigLoader()


# ============================================================================
# Section Accessors - Get entire configuration sections
# ============================================================================

def get_app_config() -> Dict[str, Any]:
    """Get application settings"""
    return _config_loader.get_section('app') or {}


def get_llm_config() -> Dict[str, Any]:
    """Get LLM configuration"""
    return _config_loader.get_section('llm') or {}


def get_video_config() -> Dict[str, Any]:
    """Get video processing configuration"""
    return _config_loader.get_section('video') or {}


def get_font_config() -> Dict[str, Any]:
    """Get font configuration"""
    return _config_loader.get_section('font') or {}


def get_processing_config() -> Dict[str, Any]:
    """Get processing configuration"""
    return _config_loader.get_section('processing') or {}


def get_tts_config() -> Dict[str, Any]:
    """Get TTS configuration"""
    return _config_loader.get_section('tts') or {}


def get_short_video_config() -> Dict[str, Any]:
    """Get short video configuration"""
    return _config_loader.get_section('short_video') or {}


def get_transitions_config() -> Dict[str, Any]:
    """Get transitions configuration"""
    return _config_loader.get_section('transitions') or {}


def get_language_levels() -> Dict[str, Any]:
    """Get language proficiency levels"""
    return _config_loader.get_section('language_levels') or {}


def get_expression_config() -> Dict[str, Any]:
    """Get expression configuration section"""
    return _config_loader.get_section('expression') or {}


def get_expression_repeat_count() -> int:
    """
    Get unified expression repeat count for all video types.
    
    This setting controls how many times expressions are repeated
    for educational purposes across all video types:
    - TTS audio generation
    - Original audio extraction
    - Short video loops
    - Educational video playback
    
    Returns:
        int: Number of times to repeat expressions (default: 3)
    """
    return int(get_expression_config().get('repeat_count', 3))


def get_expression_subtitle_styling() -> Dict[str, Any]:
    """Get expression subtitle styling configuration"""
    return _config_loader.get('expression', 'subtitle_styling', default={})


def get_expression_playback() -> Dict[str, Any]:
    """Get expression playback configuration"""
    return _config_loader.get('expression', 'playback', default={})


def get_expression_layout() -> Dict[str, Any]:
    """Get expression layout configuration"""
    return _config_loader.get('expression', 'layout', default={})


def get_expression_llm() -> Dict[str, Any]:
    """Get expression LLM configuration"""
    return _config_loader.get('expression', 'llm', default={})


# ============================================================================
# App Settings
# ============================================================================

def get_show_name() -> str:
    """Get the TV show name from configuration"""
    return get_app_config().get('show_name', 'Suits')


def get_template_file() -> str:
    """Get the template file name from configuration"""
    return get_app_config().get('template_file', 'expression_analysis_prompt.txt')


# ============================================================================
# LLM Settings
# ============================================================================

def get_generation_config() -> Dict[str, Any]:
    """Get generation configuration for LLM API calls"""
    llm_cfg = get_llm_config()
    return {
        "temperature": llm_cfg.get('temperature', 0.1),
        "top_p": llm_cfg.get('top_p', 0.8),
        "top_k": llm_cfg.get('top_k', 40),
    }


def get_max_retries() -> int:
    """Get maximum retries for API calls"""
    return get_llm_config().get('max_retries', 3)


def get_retry_backoff_seconds() -> list:
    """Get retry backoff times"""
    return get_llm_config().get('retry_backoff_seconds', [3, 6, 12])


# ============================================================================
# Font Settings
# ============================================================================

def get_font_size(size_type: str = "default") -> int:
    """
    Get font size for different text types.
    
    Args:
        size_type: Type of font size ('default', 'expression', 'translation', 'similar')
        
    Returns:
        int: Font size in pixels
    """
    font_cfg = get_font_config()
    sizes = font_cfg.get('sizes', {})
    
    # Default fallbacks if not in config (updated with larger sizes)
    default_sizes = {
        'default': 36,
        'expression_dialogue': 48,      # Full dialogue line containing expression
        'expression': 72,               # Main expression/phrase (emphasized)
        'expression_dialogue_trans': 44, # Translation of dialogue line
        'expression_trans': 60,         # Translation of expression (emphasized)
        'translation': 48,              # Legacy: Translation text (for backward compatibility)
        'similar': 38                   # Similar expressions text
    }
    
    return sizes.get(size_type, default_sizes.get(size_type, 32))


def get_font_file(language_code: Optional[str] = None) -> str:
    """
    Get font file path for the given language or default.
    
    Args:
        language_code: Optional language code (e.g., 'ko', 'ja', 'zh')
        
    Returns:
        str: Path to appropriate font file
    """
    # Check if font config specifies a file
    font_cfg = get_font_config()
    if 'default_file' in font_cfg:
        return str(font_cfg['default_file'])
    
    # Use font_utils for platform detection and language-specific fonts
    return get_font_file_for_language(language_code)


# ============================================================================
# Processing Settings
# ============================================================================

def get_min_expressions_per_chunk() -> int:
    """Get minimum expressions per chunk"""
    return get_processing_config().get('min_expressions_per_chunk', 1)


def get_max_expressions_per_chunk() -> int:
    """Get maximum expressions per chunk"""
    return get_processing_config().get('max_expressions_per_chunk', 3)


# ============================================================================
# TTS Settings
# ============================================================================

def get_tts_provider() -> str:
    """Get TTS provider name"""
    return get_tts_config().get('provider', 'google')


def is_tts_enabled() -> bool:
    """Check if TTS is enabled"""
    return get_tts_config().get('enabled', True)


def get_tts_repeat_count() -> int:
    """
    Get number of times to repeat TTS audio.
    
    DEPRECATED: Use get_expression_repeat_count() instead.
    This function now returns the unified expression repeat count.
    """
    return get_expression_repeat_count()


# ============================================================================
# Database Configuration Accessors
# ============================================================================

def get_database_enabled() -> bool:
    """Check if database is enabled."""
    return _config_loader.get('database', 'enabled', default=False)


def get_database_url() -> str:
    """Get database URL."""
    return _config_loader.get('database', 'url', default='postgresql://user:password@localhost:5432/langflix')


def get_database_pool_size() -> int:
    """Get database pool size."""
    return _config_loader.get('database', 'pool_size', default=5)


def get_database_max_overflow() -> int:
    """Get database max overflow."""
    return _config_loader.get('database', 'max_overflow', default=10)


def get_database_echo() -> bool:
    """Get database echo setting."""
    return _config_loader.get('database', 'echo', default=False)


# ============================================================================
# Short Video Settings
# ============================================================================

def is_short_video_enabled() -> bool:
    """Check if short video generation is enabled"""
    return get_short_video_config().get('enabled', True)


def get_short_video_target_duration() -> float:
    """Get target duration for short video batches"""
    return float(get_short_video_config().get('target_duration', 120.0))


def get_short_video_resolution() -> str:
    """Get short video resolution"""
    return get_short_video_config().get('resolution', '1080x1920')


def get_short_video_expression_repeat_count() -> int:
    """
    Get number of times to repeat expression video in short videos.
    
    DEPRECATED: Use get_expression_repeat_count() instead.
    This function now returns the unified expression repeat count.
    """
    return get_expression_repeat_count()


# ============================================================================
# Storage Configuration Accessors
# ============================================================================

def get_storage_backend() -> str:
    """Get storage backend type."""
    return _config_loader.get('storage.backend', 'local')


def get_storage_local_path() -> str:
    """Get local storage base path."""
    return _config_loader.get('storage.local.base_path', 'output')


def get_storage_gcs_bucket() -> str:
    """Get GCS bucket name."""
    return _config_loader.get('storage.gcs.bucket_name')


def get_storage_gcs_credentials() -> Optional[str]:
    """Get GCS credentials path."""
    return _config_loader.get('storage.gcs.credentials_path')


# ============================================================================
# Backward Compatibility - Deprecated but maintained for compatibility
# ============================================================================

# Legacy constants - use get_* functions instead
DEFAULT_FONT_FILE = get_platform_default_font()
FONT_SIZE_DEFAULT = get_font_size('default')
FONT_SIZE_EXPRESSION = get_font_size('expression')
FONT_SIZE_TRANSLATION = get_font_size('translation')
FONT_SIZE_SIMILAR = get_font_size('similar')
MAX_LLM_INPUT_LENGTH = get_llm_config().get('max_input_length', 1680)
TARGET_LANGUAGE = get_llm_config().get('target_language', 'Korean')
DEFAULT_LANGUAGE_LEVEL = get_llm_config().get('default_language_level', 'intermediate')
LANGUAGE_LEVELS = get_language_levels()
VIDEO_CONFIG = get_video_config()


# Legacy ConfigManager class - use get_* functions instead
class ConfigManager:
    """
    Legacy configuration manager for backward compatibility.
    
    Deprecated: Use get_* functions directly instead.
    """
    
    def __init__(self, config_file: Optional[str] = None):
        logger.warning("ConfigManager is deprecated. Use get_* functions directly.")
        self.config_loader = _config_loader
        
    def get(self, section: str, key: Optional[str] = None, default: Any = None) -> Any:
        """Get a configuration value"""
        if key is None:
            return self.config_loader.get_section(section)
        else:
            return self.config_loader.get(section, key, default=default)
    
    def set(self, section: str, key: str, value: Any) -> None:
        """Set a configuration value (runtime only, not persisted)"""
        logger.warning("ConfigManager.set() does not persist changes. Edit YAML files directly.")
        
    def save_config(self):
        """Save configuration (not implemented)"""
        logger.warning("ConfigManager.save_config() not implemented. Edit YAML files directly.")


# Global config instance for backward compatibility
config = ConfigManager()


# ============================================================================
# Phase 4: Media Processing & Slide Generation Settings
# ============================================================================

def get_media_config() -> Dict[str, Any]:
    """Get media processing configuration"""
    return _config_loader.get('expression.media', {})


def get_media_slicing_config() -> Dict[str, Any]:
    """Get media slicing configuration"""
    return _config_loader.get('expression.media.slicing', {})


def get_media_subtitles_config() -> Dict[str, Any]:
    """Get media subtitles configuration"""
    return _config_loader.get('expression.media.subtitles', {})


def get_slides_config() -> Dict[str, Any]:
    """Get slides configuration"""
    return _config_loader.get('expression.slides', {})


def get_slides_templates_config() -> Dict[str, Any]:
    """Get slides templates configuration"""
    return _config_loader.get('expression.slides.templates', {})


def get_slides_generation_config() -> Dict[str, Any]:
    """Get slides generation configuration"""
    return _config_loader.get('expression.slides.generation', {})


def get_media_slicing_quality() -> str:
    """Get media slicing quality setting"""
    return get_media_slicing_config().get('quality', 'high')


def get_media_slicing_buffer_start() -> float:
    """Get media slicing buffer start time"""
    return get_media_slicing_config().get('buffer_start', 0.2)


def get_media_slicing_buffer_end() -> float:
    """Get media slicing buffer end time"""
    return get_media_slicing_config().get('buffer_end', 0.2)


def get_media_slicing_crf() -> int:
    """Get media slicing CRF setting"""
    return get_media_slicing_config().get('crf', 18)


def get_media_slicing_preset() -> str:
    """Get media slicing preset"""
    return get_media_slicing_config().get('preset', 'slow')


def get_media_slicing_audio_bitrate() -> str:
    """Get media slicing audio bitrate"""
    return get_media_slicing_config().get('audio_bitrate', '256k')


def get_subtitles_style() -> str:
    """Get subtitles style"""
    return get_media_subtitles_config().get('style', 'expression_highlight')


def get_subtitles_font_size() -> int:
    """Get subtitles font size"""
    return get_media_subtitles_config().get('font_size', 24)


def get_subtitles_font_color() -> str:
    """Get subtitles font color"""
    return get_media_subtitles_config().get('font_color', '#FFFFFF')


def get_subtitles_background_color() -> str:
    """Get subtitles background color"""
    return get_media_subtitles_config().get('background_color', '#000000')


def get_subtitles_highlight_color() -> str:
    """Get subtitles highlight color"""
    return get_media_subtitles_config().get('highlight_color', '#FFD700')


def get_slides_max_examples() -> int:
    """Get maximum examples per slide"""
    return get_slides_generation_config().get('max_examples', 4)


def get_slides_max_similar_expressions() -> int:
    """Get maximum similar expressions per slide"""
    return get_slides_generation_config().get('max_similar_expressions', 5)


def get_slides_include_cultural_notes() -> bool:
    """Check if cultural notes should be included"""
    return get_slides_generation_config().get('include_cultural_notes', True)


def get_slides_include_grammar_notes() -> bool:
    """Check if grammar notes should be included"""
    return get_slides_generation_config().get('include_grammar_notes', True)


def get_slides_include_pronunciation() -> bool:
    """Check if pronunciation should be included"""
    return get_slides_generation_config().get('include_pronunciation', True)


def get_slides_size() -> List[int]:
    """Get slide dimensions"""
    return get_slides_generation_config().get('slide_size', [1920, 1080])


def get_slides_output_format() -> str:
    """Get slide output format"""
    return get_slides_generation_config().get('output_format', 'PNG')


def get_slides_quality() -> int:
    """Get slide quality"""
    return get_slides_generation_config().get('quality', 95)


# Legacy functions - maintained for compatibility
def get_video_config(attribute: str = None):
    """Legacy: Get video processing configuration"""
    video_cfg = get_video_config()
    if attribute and isinstance(video_cfg, dict):
        return video_cfg.get(attribute)
    return video_cfg
