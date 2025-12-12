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


def get_clip_extraction_config() -> Dict[str, Any]:
    """Get clip extraction configuration"""
    video_cfg = get_video_config()
    return video_cfg.get('clip_extraction', {})


def get_clip_extraction_strategy() -> str:
    """
    Get clip extraction strategy.
    
    Returns:
        str: 'auto' (try copy, fallback to encode), 'copy' (copy only), or 'encode' (always re-encode)
        Default: 'auto'
    """
    return get_clip_extraction_config().get('strategy', 'auto')


def get_clip_copy_threshold_seconds() -> float:
    """
    Get threshold for attempting stream copy (seconds).
    
    Clips shorter than this will attempt stream copy first (if strategy allows).
    Longer clips will directly use re-encode for better accuracy.
    
    Returns:
        float: Threshold in seconds (default: 30.0)
    """
    return float(get_clip_extraction_config().get('copy_threshold_seconds', 30.0))


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


def get_expression_slicing_config() -> Dict[str, Any]:
    """Get expression slicing configuration"""
    expr_cfg = get_expression_config()
    media_cfg = expr_cfg.get('media', {})
    return media_cfg.get('slicing', {})


def get_max_concurrent_slicing() -> int:
    """
    Get maximum concurrent slicing operations.
    
    Controls how many FFmpeg processes can run simultaneously during
    expression slicing. This prevents resource exhaustion on limited servers.
    
    Returns:
        int: Maximum concurrent operations (default: CPU count // 2, min 1)
    """
    import os
    slicing_cfg = get_expression_slicing_config()
    configured = slicing_cfg.get('max_concurrent', None)
    
    if configured is not None:
        return max(1, int(configured))
    
    # Default: half of CPU cores, minimum 1
    cpu_count = os.cpu_count() or 2
    return max(1, cpu_count // 2)


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


def get_parallel_llm_processing_enabled() -> bool:
    """Check if parallel LLM processing is enabled"""
    expression_llm = get_expression_llm()
    parallel_config = expression_llm.get('parallel_processing', {})
    return parallel_config.get('enabled', True)


def get_parallel_llm_max_workers() -> Optional[int]:
    """Get max workers for parallel LLM processing"""
    expression_llm = get_expression_llm()
    parallel_config = expression_llm.get('parallel_processing', {})
    max_workers = parallel_config.get('max_workers')
    if max_workers is None:
        # Auto-detect based on CPU count, capped at 5 for Gemini API
        import multiprocessing
        return min(multiprocessing.cpu_count(), 5)
    return max_workers


def get_parallel_llm_timeout() -> float:
    """Get timeout per chunk for parallel processing"""
    expression_llm = get_expression_llm()
    parallel_config = expression_llm.get('parallel_processing', {})
    return parallel_config.get('timeout_per_chunk', 300)




def get_allow_multiple_expressions() -> bool:
    """Check if multiple expressions per context is enabled"""
    expression_llm = get_expression_llm()
    return expression_llm.get('allow_multiple_expressions', True)


def get_educational_video_mode() -> str:
    """Get educational video generation mode (separate or combined)"""
    expression_config = get_expression_config()
    return expression_config.get('educational_video_mode', 'separate')


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


def get_llm_model_name() -> str:
    """Get the Gemini model name for LLM operations"""
    # Check environment variable first
    import os
    env_model = os.getenv("GEMINI_MODEL")
    if env_model:
        return env_model
    return get_llm_config().get('model_name', 'gemini-2.5-flash')


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
    # Check environment variable first (for Docker/container deployments)
    import os
    env_enabled = os.getenv('DATABASE_ENABLED')
    if env_enabled is not None:
        return env_enabled.lower() in ('true', '1', 'yes', 'on')
    # Fall back to config file
    return _config_loader.get('database', 'enabled', default=False)


def get_database_url() -> str:
    """Get database URL."""
    # Check environment variable first (for Docker/container deployments)
    import os
    env_url = os.getenv('DATABASE_URL')
    if env_url:
        return env_url
    # Fall back to config file
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


def get_short_video_max_duration() -> float:
    """Get maximum duration for short video batches (seconds)"""
    return float(get_short_video_config().get('max_duration', 180.0))


def get_short_video_expression_repeat_count() -> int:
    """
    Get number of times to repeat expression video in short videos.

    DEPRECATED: Use get_expression_repeat_count() instead.
    This function now returns the unified expression repeat count.
    """
    return get_expression_repeat_count()


def get_short_video_layout_config() -> Dict[str, Any]:
    """Get short-form video layout configuration"""
    return get_short_video_config().get('layout', {})


def get_short_video_dimensions() -> tuple[int, int]:
    """
    Get short-form video dimensions (width, height).

    Returns:
        tuple: (width, height) in pixels (default: 1080x1920)
    """
    layout = get_short_video_layout_config()
    width = layout.get('target_width', 1080)
    height = layout.get('target_height', 1920)
    return (width, height)


def get_long_form_video_height() -> int:
    """
    Get long-form video height in short-form layout.

    Returns:
        int: Height in pixels (default: 960)
    """
    layout = get_short_video_layout_config()
    return layout.get('long_form_video_height', 960)


def get_short_video_padding_heights() -> tuple[int, int]:
    """
    Get top and bottom padding heights for short-form video.

    Returns:
        tuple: (top_padding, bottom_padding) in pixels (default: 480, 480)
    """
    layout = get_short_video_layout_config()
    top = layout.get('top_padding_height', 480)
    bottom = layout.get('bottom_padding_height', 480)
    return (top, bottom)


def get_keywords_config() -> Dict[str, Any]:
    """Get catchy keywords display configuration"""
    layout = get_short_video_layout_config()
    return layout.get('keywords', {})


def get_keywords_font_size() -> int:
    """Get keywords font size (default: 42)"""
    return get_keywords_config().get('font_size', 42)


def get_keywords_y_position() -> int:
    """Get keywords starting Y position (default: 350)"""
    return get_keywords_config().get('y_position', 350)


def get_keywords_line_height_factor() -> float:
    """Get keywords line height as multiple of font size (default: 1.2)"""
    return get_keywords_config().get('line_height_factor', 1.2)


def get_keywords_max_width_percent() -> float:
    """Get keywords maximum width as percentage of video width (default: 0.9)"""
    return get_keywords_config().get('max_width_percent', 0.9)


def get_keywords_text_color() -> str:
    """Get keywords text color (default: 'white')"""
    return get_keywords_config().get('text_color', 'white')


def get_keywords_border_width() -> int:
    """Get keywords border width (default: 2)"""
    return get_keywords_config().get('border_width', 2)


def get_keywords_border_color() -> str:
    """Get keywords border color (default: 'black')"""
    return get_keywords_config().get('border_color', 'black')


def get_expression_text_config() -> Dict[str, Any]:
    """Get expression text display configuration"""
    layout = get_short_video_layout_config()
    return layout.get('expression', {})


def get_expression_font_size() -> int:
    """Get expression font size (default: 35)"""
    return get_expression_text_config().get('font_size', 35)


def get_expression_y_position() -> int:
    """Get expression Y position (default: 1500)"""
    return get_expression_text_config().get('y_position', 1500)


def get_expression_text_color() -> str:
    """Get expression text color (default: 'yellow')"""
    return get_expression_text_config().get('text_color', 'yellow')


def get_expression_border_width() -> int:
    """Get expression border width (default: 2)"""
    return get_expression_text_config().get('border_width', 2)


def get_expression_border_color() -> str:
    """Get expression border color (default: 'black')"""
    return get_expression_text_config().get('border_color', 'black')


def get_translation_text_config() -> Dict[str, Any]:
    """Get translation text display configuration"""
    layout = get_short_video_layout_config()
    return layout.get('translation', {})


def get_translation_font_size() -> int:
    """Get translation font size (default: 32)"""
    return get_translation_text_config().get('font_size', 32)


def get_translation_y_position() -> int:
    """Get translation Y position (default: 1560)"""
    return get_translation_text_config().get('y_position', 1560)


def get_translation_gap_from_expression() -> int:
    """Get gap between expression and translation (default: 60)"""
    return get_translation_text_config().get('gap_from_expression', 60)


def get_translation_text_color() -> str:
    """Get translation text color (default: 'yellow')"""
    return get_translation_text_config().get('text_color', 'yellow')


def get_translation_border_width() -> int:
    """Get translation border width (default: 2)"""
    return get_translation_text_config().get('border_width', 2)


def get_translation_border_color() -> str:
    """Get translation border color (default: 'black')"""
    return get_translation_text_config().get('border_color', 'black')


def get_dialogue_subtitle_config() -> Dict[str, Any]:
    """Get dialogue subtitle display configuration"""
    layout = get_short_video_layout_config()
    return layout.get('dialogue_subtitle', {})


def get_dialogue_subtitle_font_size() -> int:
    """Get dialogue subtitle font size (default: 21)"""
    return get_dialogue_subtitle_config().get('font_size', 21)


def get_dialogue_subtitle_margin_v() -> int:
    """Get dialogue subtitle margin from bottom (default: 170)"""
    return get_dialogue_subtitle_config().get('margin_v', 170)


def get_dialogue_subtitle_text_color() -> str:
    """Get dialogue subtitle text color (default: 'white')"""
    return get_dialogue_subtitle_config().get('text_color', 'white')


def get_dialogue_subtitle_outline_width() -> int:
    """Get dialogue subtitle outline width (default: 2)"""
    return get_dialogue_subtitle_config().get('outline_width', 2)


def get_dialogue_subtitle_outline_color() -> str:
    """Get dialogue subtitle outline color (default: 'black')"""
    return get_dialogue_subtitle_config().get('outline_color', 'black')


def get_dialogue_subtitle_background_opacity() -> float:
    """Get dialogue subtitle background opacity (default: 0.5 for 50%)"""
    return get_dialogue_subtitle_config().get('background_opacity', 0.5)


def get_layout_fonts_config() -> Dict[str, Any]:
    """Get fonts configuration for short video layout"""
    layout = get_short_video_layout_config()
    return layout.get('fonts', {})


def get_custom_font_path(font_type: str) -> Optional[str]:
    """
    Get custom font path for a specific text type.
    
    Args:
        font_type: Type of font ('keywords', 'expression', 'translation', 'title', 'vocabulary')
        
    Returns:
        Absolute path to font file, or None if not configured/not found
    """
    import os
    from pathlib import Path
    
    fonts_config = get_layout_fonts_config()
    relative_path = fonts_config.get(font_type)
    
    if not relative_path:
        return None
    
    # Build absolute path from assets/fonts directory
    # Get project root (assuming settings.py is in langflix/)
    project_root = Path(__file__).parent.parent
    font_path = project_root / "assets" / "fonts" / relative_path
    
    if font_path.exists():
        return str(font_path)
    
    # Log warning if configured but not found
    logger.warning(f"Custom font not found for {font_type}: {font_path}")
    return None


def get_keywords_font_path() -> Optional[str]:
    """Get font path for catchy keywords (hashtags at top)"""
    return get_custom_font_path('keywords')


def get_expression_font_path() -> Optional[str]:
    """Get font path for expression text (bottom)"""
    return get_custom_font_path('expression')


def get_translation_font_path() -> Optional[str]:
    """Get font path for translation text (bottom)"""
    return get_custom_font_path('translation')


def get_title_font_path() -> Optional[str]:
    """Get font path for title overlay"""
    return get_custom_font_path('title')


def get_vocabulary_font_path() -> Optional[str]:
    """Get font path for vocabulary annotations"""
    return get_custom_font_path('vocabulary')


def get_vocabulary_annotations_config() -> Dict[str, Any]:
    """Get vocabulary annotations display configuration"""
    layout = get_short_video_layout_config()
    return layout.get('vocabulary_annotations', {})


def get_vocabulary_font_size() -> int:
    """Get vocabulary annotation font size (default: 28)"""
    return get_vocabulary_annotations_config().get('font_size', 28)


def get_vocabulary_text_color() -> str:
    """Get vocabulary annotation text color (default: 'yellow')"""
    return get_vocabulary_annotations_config().get('text_color', 'yellow')


def get_vocabulary_border_width() -> int:
    """Get vocabulary annotation border width (default: 2)"""
    return get_vocabulary_annotations_config().get('border_width', 2)


def get_vocabulary_border_color() -> str:
    """Get vocabulary annotation border color (default: 'black')"""
    return get_vocabulary_annotations_config().get('border_color', 'black')


def get_vocabulary_x_position() -> int:
    """Get vocabulary annotation X position (default: 20)"""
    return get_vocabulary_annotations_config().get('x_position', 20)


def get_vocabulary_y_offset() -> int:
    """Get vocabulary annotation Y offset from video area top (default: 20)"""
    return get_vocabulary_annotations_config().get('y_offset', 20)


def get_vocabulary_duration() -> float:
    """Get vocabulary annotation display duration in seconds (default: 4.0)"""
    return get_vocabulary_annotations_config().get('duration', 4.0)


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
    result = _config_loader.get('expression.media', {})
    return result if result is not None else {}


def get_media_ffprobe_config() -> Dict[str, Any]:
    """Get ffprobe-related media configuration"""
    return get_media_config().get('ffprobe', {})


def get_ffprobe_timeout_seconds() -> int:
    """Get ffprobe timeout in seconds (minimum 1, default 30)"""
    config_timeout = get_media_ffprobe_config().get('timeout_seconds', 30)
    try:
        timeout_value = int(config_timeout)
    except (TypeError, ValueError):
        logger.warning(
            "Invalid ffprobe timeout value '%s' in configuration. "
            "Falling back to default 30 seconds.",
            config_timeout,
        )
        return 30

    if timeout_value < 1:
        logger.warning(
            "Configured ffprobe timeout (%s) is less than 1 second. "
            "Clamping to minimum value of 1.",
            timeout_value,
        )
        return 1

    return timeout_value


def get_media_slicing_config() -> Dict[str, Any]:
    """Get media slicing configuration"""
    return _config_loader.get('expression.media.slicing', {})


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
    # Use the module-level function, not self-recursion
    video_cfg = _config_loader.get_section('video') or {}
    if attribute and isinstance(video_cfg, dict):
        return video_cfg.get(attribute)
    return video_cfg
