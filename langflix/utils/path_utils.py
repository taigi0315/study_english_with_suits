"""
Path utilities for V2 dual-language subtitle file structure.

File Structure Convention:
    assets/media/
    ├── {media_name}.mp4                    # Media file
    └── {media_name}/                       # Subtitle folder (same base name without extension)
        ├── {index}_{Language}.srt          # Subtitle files
        ├── 3_Korean.srt
        ├── 6_English.srt
        └── ...
"""
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Pattern for subtitle filenames: {index}_{Language}.srt
SUBTITLE_FILENAME_PATTERN = re.compile(r'^(\d+)_([A-Za-z]+)\.srt$')


def get_subtitle_folder(media_path: str) -> Optional[Path]:
    """
    Get the subtitle folder for a given media file.
    
    The subtitle folder has the same name as the media file without extension.
    
    Args:
        media_path: Path to the media file (e.g., /path/to/video.mp4)
        
    Returns:
        Path to subtitle folder, or None if it doesn't exist
        
    Example:
        >>> get_subtitle_folder("/media/show.mp4")
        Path("/media/show")
    """
    media_file = Path(media_path)
    
    if not media_file.exists():
        logger.warning(f"Media file does not exist: {media_path}")
        return None
    
    # Subtitle folder has same name as media file without extension
    subtitle_folder = media_file.parent / media_file.stem
    
    if subtitle_folder.exists() and subtitle_folder.is_dir():
        return subtitle_folder
    
    logger.warning(f"Subtitle folder not found: {subtitle_folder}")
    return None


def parse_subtitle_filename(filename: str) -> Optional[Tuple[int, str]]:
    """
    Parse a subtitle filename to extract index and language.
    
    Args:
        filename: Subtitle filename (e.g., "3_Korean.srt")
        
    Returns:
        Tuple of (index, language) or None if pattern doesn't match
        
    Example:
        >>> parse_subtitle_filename("3_Korean.srt")
        (3, "Korean")
        >>> parse_subtitle_filename("invalid.srt")
        None
    """
    match = SUBTITLE_FILENAME_PATTERN.match(filename)
    if match:
        index = int(match.group(1))
        language = match.group(2)
        return (index, language)
    return None


def discover_subtitle_languages(media_path: str) -> Dict[str, List[str]]:
    """
    Discover all available subtitle languages for a media file.
    
    Args:
        media_path: Path to the media file
        
    Returns:
        Dictionary mapping language names to list of subtitle file paths.
        Multiple files per language are possible (e.g., CC, SDH variants).
        
    Example:
        >>> discover_subtitle_languages("/media/show.mp4")
        {
            "Korean": ["/media/show/3_Korean.srt", "/media/show/4_Korean.srt"],
            "English": ["/media/show/5_English.srt", "/media/show/6_English.srt"],
            ...
        }
    """
    subtitle_folder = get_subtitle_folder(media_path)
    
    if subtitle_folder is None:
        logger.warning(f"No subtitle folder found for: {media_path}")
        return {}
    
    languages: Dict[str, List[str]] = {}
    
    for srt_file in sorted(subtitle_folder.glob("*.srt")):
        parsed = parse_subtitle_filename(srt_file.name)
        if parsed:
            index, language = parsed
            if language not in languages:
                languages[language] = []
            languages[language].append(str(srt_file))
        else:
            logger.debug(f"Skipping non-standard subtitle file: {srt_file.name}")
    
    logger.info(f"Discovered {len(languages)} languages for {media_path}: {list(languages.keys())}")
    return languages


def get_available_language_names(media_path: str) -> List[str]:
    """
    Get list of available language names for a media file.
    
    Args:
        media_path: Path to the media file
        
    Returns:
        Sorted list of language names
        
    Example:
        >>> get_available_language_names("/media/show.mp4")
        ["Arabic", "Chinese", "English", "Korean", "Spanish", ...]
    """
    languages = discover_subtitle_languages(media_path)
    return sorted(languages.keys())


def get_subtitle_file(
    media_path: str, 
    language: str, 
    variant_index: int = 0
) -> Optional[str]:
    """
    Get the path to a specific language's subtitle file.
    
    Args:
        media_path: Path to the media file
        language: Language name (e.g., "Korean", "English")
        variant_index: Which variant to use if multiple exist (default: first)
        
    Returns:
        Path to subtitle file, or None if not found
        
    Example:
        >>> get_subtitle_file("/media/show.mp4", "Korean")
        "/media/show/3_Korean.srt"
    """
    languages = discover_subtitle_languages(media_path)
    
    if language not in languages:
        logger.warning(f"Language '{language}' not available for {media_path}")
        return None
    
    variants = languages[language]
    
    if variant_index >= len(variants):
        logger.warning(
            f"Variant index {variant_index} out of range for {language} "
            f"(only {len(variants)} variants available)"
        )
        variant_index = 0
    
    return variants[variant_index]


def find_media_subtitle_pairs(media_dir: str) -> List[Tuple[Path, Path]]:
    """
    Find all media files that have corresponding subtitle folders.
    
    Args:
        media_dir: Directory to search for media files
        
    Returns:
        List of (media_path, subtitle_folder_path) tuples
        
    Example:
        >>> find_media_subtitle_pairs("/assets/media/")
        [
            (Path("/assets/media/show1.mp4"), Path("/assets/media/show1")),
            (Path("/assets/media/show2.mkv"), Path("/assets/media/show2")),
        ]
    """
    media_dir_path = Path(media_dir)
    pairs: List[Tuple[Path, Path]] = []
    
    # Common video extensions
    video_extensions = {'.mp4', '.mkv', '.avi', '.mov', '.webm'}
    
    for media_file in media_dir_path.iterdir():
        if media_file.is_file() and media_file.suffix.lower() in video_extensions:
            subtitle_folder = media_file.parent / media_file.stem
            if subtitle_folder.exists() and subtitle_folder.is_dir():
                # Verify folder has subtitle files
                srt_files = list(subtitle_folder.glob("*.srt"))
                if srt_files:
                    pairs.append((media_file, subtitle_folder))
                    logger.debug(f"Found pair: {media_file.name} -> {len(srt_files)} subtitles")
    
    logger.info(f"Found {len(pairs)} media-subtitle pairs in {media_dir}")
    return pairs


def validate_dual_subtitle_availability(
    media_path: str, 
    source_lang: str, 
    target_lang: str
) -> Tuple[bool, Optional[str]]:
    """
    Validate that both source and target language subtitles are available.
    
    Args:
        media_path: Path to the media file
        source_lang: Source language name (e.g., "English")
        target_lang: Target language name (e.g., "Korean")
        
    Returns:
        Tuple of (is_valid, error_message)
        
    Example:
        >>> validate_dual_subtitle_availability("/media/show.mp4", "English", "Korean")
        (True, None)
        >>> validate_dual_subtitle_availability("/media/show.mp4", "English", "Klingon")
        (False, "Target language 'Klingon' not available. Available: ...")
    """
    if source_lang == target_lang:
        return (False, "Source and target languages must be different")
    
    available = discover_subtitle_languages(media_path)
    
    if not available:
        return (False, f"No subtitles found for {media_path}")
    
    missing = []
    if source_lang not in available:
        missing.append(f"source '{source_lang}'")
    if target_lang not in available:
        missing.append(f"target '{target_lang}'")
    
    if missing:
        available_list = ", ".join(sorted(available.keys()))
        return (False, f"Missing {' and '.join(missing)}. Available: {available_list}")
    
    return (True, None)
