"""
Path utilities for V2 dual-language subtitle file structure.

File Structure Convention (NEW - Netflix-style):
    assets/media/
    ├── {media_name}.mp4                    # Media file
    └── Subs/                               # Subs folder
        └── {media_name}/                   # Subtitle folder (same base name without extension)
            ├── {index}_{Language}.srt      # Subtitle files
            ├── 3_Korean.srt
            ├── 6_English.srt
            └── ...

Legacy Structure (still supported):
    assets/media/
    ├── {media_name}.mp4
    └── {media_name}/                       # Subtitle folder directly next to media
        ├── 3_Korean.srt
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
    Get the subtitle folder for a given media file or folder path.
    
    Checks both new and legacy folder structures:
    1. NEW: Subs/{media_name}/  (Netflix-style downloads)
    2. LEGACY: {media_name}/    (original structure)
    
    Args:
        media_path: Path to the media file (e.g., /path/to/video.mp4) or 
                    directly to the subtitle folder (e.g., /path/to/video/)
        
    Returns:
        Path to subtitle folder, or None if it doesn't exist
        
    Example:
        >>> get_subtitle_folder("/media/show.mp4")
        Path("/media/Subs/show")  # If new structure exists
        >>> get_subtitle_folder("/media/show.mp4")
        Path("/media/show")  # Fallback to legacy structure
    """
    media_file = Path(media_path)
    
    if not media_file.exists():
        logger.warning(f"Media file does not exist: {media_path}")
        return None
    
    # If it's already a directory with .srt files, return it directly
    if media_file.is_dir():
        srt_files = list(media_file.glob("*.srt"))
        if srt_files:
            return media_file
    
    media_base_name = media_file.stem
    
    # NEW STRUCTURE: Check Subs/{media_name}/ first
    subs_folder = media_file.parent / "Subs" / media_base_name
    if subs_folder.exists() and subs_folder.is_dir():
        srt_files = list(subs_folder.glob("*.srt"))
        if srt_files:
            logger.debug(f"Found subtitle folder (new structure): {subs_folder}")
            return subs_folder
    
    # LEGACY STRUCTURE: {media_name}/ directly next to media file
    legacy_folder = media_file.parent / media_base_name
    if legacy_folder.exists() and legacy_folder.is_dir():
        srt_files = list(legacy_folder.glob("*.srt"))
        if srt_files:
            logger.debug(f"Found subtitle folder (legacy structure): {legacy_folder}")
            return legacy_folder
    
    logger.warning(f"Subtitle folder not found for: {media_path} (checked Subs/{media_base_name}/ and {media_base_name}/)")
    return None


def parse_subtitle_filename(filename: str) -> Optional[Tuple[int, str]]:
    """
    Parse a subtitle filename to extract index and language.

    Args:
        filename: Subtitle filename (e.g., "3_Korean.srt" or "3_korean.srt")

    Returns:
        Tuple of (index, language) or None if pattern doesn't match
        Language name is normalized to Title Case (e.g., "Korean", "English")

    Example:
        >>> parse_subtitle_filename("3_Korean.srt")
        (3, "Korean")
        >>> parse_subtitle_filename("3_korean.srt")
        (3, "Korean")
        >>> parse_subtitle_filename("invalid.srt")
        None
    """
    match = SUBTITLE_FILENAME_PATTERN.match(filename)
    if match:
        index = int(match.group(1))
        language = match.group(2)
        # Normalize language name to Title Case (Korean, not korean or KOREAN)
        language = language.title()
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
    
    # Pattern for simple language filenames: {Language}.srt (e.g., "Korean.srt")
    simple_pattern = re.compile(r'^([A-Za-z]+)\.srt$')
    
    for srt_file in sorted(subtitle_folder.glob("*.srt")):
        parsed = parse_subtitle_filename(srt_file.name)
        if parsed:
            # Indexed filename: "3_Korean.srt"
            index, language = parsed
            if language not in languages:
                languages[language] = []
            languages[language].append(str(srt_file))
        else:
            # Try simple filename pattern: "Korean.srt"
            simple_match = simple_pattern.match(srt_file.name)
            if simple_match:
                language = simple_match.group(1)
                # Normalize language name to Title Case (Korean, not korean or KOREAN)
                language = language.title()
                if language not in languages:
                    languages[language] = []
                # Insert at beginning (priority over indexed variants)
                languages[language].insert(0, str(srt_file))
                logger.debug(f"Found simple subtitle: {srt_file.name} -> {language}")
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
    
    Checks both new and legacy folder structures:
    1. NEW: Subs/{media_name}/  (Netflix-style downloads)
    2. LEGACY: {media_name}/    (original structure)
    
    Args:
        media_dir: Directory to search for media files
        
    Returns:
        List of (media_path, subtitle_folder_path) tuples
        
    Example:
        >>> find_media_subtitle_pairs("/assets/media/")
        [
            (Path("/assets/media/show1.mp4"), Path("/assets/media/Subs/show1")),
            (Path("/assets/media/show2.mkv"), Path("/assets/media/show2")),
        ]
    """
    media_dir_path = Path(media_dir)
    pairs: List[Tuple[Path, Path]] = []
    
    # Common video extensions
    video_extensions = {'.mp4', '.mkv', '.avi', '.mov', '.webm'}
    
    for media_file in media_dir_path.iterdir():
        if media_file.is_file() and media_file.suffix.lower() in video_extensions:
            media_base_name = media_file.stem
            
            # Check NEW structure first: Subs/{media_name}/
            subs_folder = media_file.parent / "Subs" / media_base_name
            if subs_folder.exists() and subs_folder.is_dir():
                srt_files = list(subs_folder.glob("*.srt"))
                if srt_files:
                    pairs.append((media_file, subs_folder))
                    logger.debug(f"Found pair (new structure): {media_file.name} -> {len(srt_files)} subtitles")
                    continue
            
            # Check LEGACY structure: {media_name}/
            legacy_folder = media_file.parent / media_base_name
            if legacy_folder.exists() and legacy_folder.is_dir():
                srt_files = list(legacy_folder.glob("*.srt"))
                if srt_files:
                    pairs.append((media_file, legacy_folder))
                    logger.debug(f"Found pair (legacy structure): {media_file.name} -> {len(srt_files)} subtitles")
    
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
