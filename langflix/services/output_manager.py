"""
Output Manager for LangFlix
Manages organized output structure for scalable multi-language support
Includes permission handling for TrueNAS environments
"""

import os
import re
import logging
import stat
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
from datetime import datetime

logger = logging.getLogger(__name__)

def sanitize_path_component(name: str, fallback: str = "Unknown") -> str:
    """
    Make directory-friendly string: collapse whitespace, remove illegal chars.
    """
    if not name:
        return fallback

    sanitized = re.sub(r'[\\/]+', '_', name)
    sanitized = re.sub(r'\s+', '_', sanitized)
    sanitized = re.sub(r'[<>:"|?*]+', '', sanitized)
    sanitized = re.sub(r'\.{2,}', '.', sanitized)
    sanitized = sanitized.strip(' _-.')
    return sanitized or fallback


def parse_series_episode_from_string(filename: str) -> Tuple[str, str]:
    """
    Extract normalized series/episode identifiers from a filename.
    """
    base = Path(filename).stem
    if base.endswith('.en'):
        base = base[:-3]

    patterns = [
        r'^(.+?)\s*-\s*(\d+x\d+)\s*-\s*(.+)$',
        r'^(.+?)\.S(\d+)E(\d+)(?:\..+)?$',
        r'^(.+?)\.S(\d+)E(\d+)$',
        r'^(.+?)_(\d+x\d+)_(.+)$'
    ]

    for pattern in patterns:
        match = re.match(pattern, base, re.IGNORECASE)
        if not match:
            continue

        if 'S(\\d+)E(\\d+)' in pattern:
            raw_series = match.group(1)
            series_name = re.sub(r'\.\d+p\..*$', '', raw_series, flags=re.IGNORECASE)
            series_name = re.sub(r'\.(HDTV|WEB-DL|BluRay|DVDRip).*$', '', series_name, flags=re.IGNORECASE)
            season, episode = match.group(2), match.group(3)
            episode_name = f"S{int(season):02d}E{int(episode):02d}"
        else:
            series_name = match.group(1)
            episode_num = match.group(2)
            if len(match.groups()) > 2:
                episode_title = re.sub(r'\.\d+p\..*$', '', match.group(3), flags=re.IGNORECASE)
                episode_name = f"{episode_num}_{episode_title}"
            else:
                episode_name = episode_num

        return sanitize_path_component(series_name, "Unknown_Series"), sanitize_path_component(episode_name, "Unknown_Episode")

    return "Unknown_Series", "Unknown_Episode"


class OutputManager:
    """
    Manages organized output structure for scalable multi-language support
    
    Structure:
    output/
    ├── Series/
    │   ├── Episode/
    │   │   ├── shared/           # Language-independent resources
    │   │   │   ├── video_clips/
    │   │   │   ├── audio_clips/
    │   │   │   └── templates/
    │   │   ├── translations/     # Language-specific content
    │   │   │   ├── ko/          # Korean
    │   │   │   ├── ja/          # Japanese
    │   │   │   └── zh/          # Chinese
    │   │   └── metadata/        # Common metadata
    """
    
    def __init__(self, base_output_dir: str = None):
        """
        Initialize OutputManager
        
        Args:
            base_output_dir: Base output directory (defaults to LANGFLIX_OUTPUT_DIR env or 'output')
        """
        if base_output_dir is None:
            base_output_dir = os.getenv('LANGFLIX_OUTPUT_DIR', 'output')
        self.base_output_dir = Path(base_output_dir)
        self.base_output_dir.mkdir(exist_ok=True)
        self.ensure_write_permissions(self.base_output_dir)

    @staticmethod
    def ensure_write_permissions(path: Union[str, Path], is_file: bool = False) -> None:
        """
        Ensure path has correct write permissions for TrueNAS/Docker environment.
        Directories: 775 (rwxrwxr-x)
        Files: 664 (rw-rw-r--)
        """
        try:
            path_obj = Path(path)
            if not path_obj.exists():
                return
                
            # Set permissions
            if is_file:
                # rw-rw-r-- (664)
                os.chmod(path_obj, 0o664)
            else:
                # rwxrwxr-x (775)
                os.chmod(path_obj, 0o775)
                
            # Explicitly try to set gid to 1000 if possible (often restricted, so ignore errors)
            try:
                # Get current uid/gid
                st = path_obj.stat()
                # Only try to change if not already correct (container user is usually 1000)
                if st.st_gid != 1000:
                    os.chown(path_obj, -1, 1000)
            except Exception:
                pass
                
        except Exception as e:
            logger.warning(f"Failed to set permissions for {path}: {e}")
        
    def create_episode_structure(self, series_name: str, episode_name: str) -> Dict[str, Path]:
        """
        Create organized folder structure for an episode
        
        Args:
            series_name: Name of the series (e.g., "Suits")
            episode_name: Name of the episode (e.g., "S01E01_Pilot")
            
        Returns:
            Dictionary with path mappings for different content types
        """
        normalized_series = sanitize_path_component(series_name or "Unknown_Series", fallback="Unknown_Series")
        normalized_episode = sanitize_path_component(episode_name or "Unknown_Episode", fallback="Unknown_Episode")

        # Create main episode directory
        episode_dir = self.base_output_dir / normalized_series / normalized_episode
        episode_dir.mkdir(parents=True, exist_ok=True)
        self.ensure_write_permissions(episode_dir)
        
        # Note: Removed translations/ directory - language folders go directly under episode
        # Structure: output/Series/Episode/{lang}/ instead of output/Series/Episode/translations/{lang}/
        # Removed shared/ and metadata/ directories as they are currently unused
        # If needed in future, these can be re-enabled:
        # - shared/: for language-independent intermediate files
        # - metadata/: for processing logs and LLM outputs
        
        # Return path mappings (simplified structure)
        paths = {
            'episode_dir': episode_dir,
            # Removed translations directory - language folders created directly under episode
            # Removed unused shared and metadata paths
            # 'shared': {...},
            # 'metadata': {...}
        }
        
        logger.info(f"Created episode structure: {episode_dir}")
        return paths
    
    def create_language_structure(self, episode_paths: Dict[str, Path], language_code: str) -> Dict[str, Path]:
        """
        Create language-specific folder structure
        
        Args:
            episode_paths: Episode path mappings from create_episode_structure
            language_code: Language code (e.g., 'ko', 'ja', 'zh')
            
        Returns:
            Dictionary with language-specific path mappings
        """
        # Create language directory directly under episode (no translations/ folder)
        # Structure: output/Series/Episode/{lang}/ instead of output/Series/Episode/translations/{lang}/
        lang_dir = episode_paths['episode_dir'] / language_code
        lang_dir.mkdir(exist_ok=True)
        self.ensure_write_permissions(lang_dir)
        
        # Simplified structure: only shorts/ and long/ directories
        # Removed: expressions/, videos/, slides/, subtitles/ (intermediate files not needed in final output)
        shorts_dir = lang_dir / "shorts"  # Short-form videos
        long_dir = lang_dir / "long"  # Combined long-form video
        
        # Restore separate directories for intermediates relative to language root
        # This prevents 'cleanup' from deleting the entire language folder
        subtitles_dir = lang_dir / "subtitles"
        slides_dir = lang_dir / "slides"
        videos_dir = lang_dir / "videos"
        expressions_dir = lang_dir / "expressions"

        for d in [shorts_dir, long_dir, subtitles_dir, slides_dir, videos_dir, expressions_dir]:
            d.mkdir(exist_ok=True)
            self.ensure_write_permissions(d)
        
        # Return language-specific paths
        # Legacy paths point to lang_dir for backward compatibility (files saved there if needed)
        lang_paths = {
            'language_dir': lang_dir,
            'subtitles': subtitles_dir,
            'slides': slides_dir,
            'videos': videos_dir,
            'expressions': expressions_dir,
            'shorts': shorts_dir,
            'long': long_dir,
            # Legacy path mappings for backward compatibility
            'final_videos': expressions_dir, # Educational videos go here
            'context_slide_combined': videos_dir,
            'short_videos': shorts_dir,
            'long_form_videos': long_dir
        }
        
        logger.info(f"Created language structure for {language_code}: {lang_dir}")
        return lang_paths
    
    def get_series_episode_name(self, subtitle_file_path: str) -> tuple[str, str]:
        """
        Extract series and episode names from subtitle file path
        
        Args:
            subtitle_file_path: Path to subtitle file
            
        Returns:
            Tuple of (series_name, episode_name)
        """
        return parse_series_episode_from_string(Path(subtitle_file_path).name)
    
    def save_metadata(self, episode_paths: Dict[str, Path], metadata: Dict) -> Path:
        """
        Save metadata to episode directory
        
        Args:
            episode_paths: Episode path mappings
            metadata: Metadata dictionary to save
            
        Returns:
            Path to saved metadata file
        """
        import json
        
        # Save metadata directly in episode directory since metadata folder is removed
        metadata_file = episode_paths['episode_dir'] / "expressions.json"
        
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved metadata: {metadata_file}")
        return metadata_file
    
    def save_processing_log(self, episode_paths: Dict[str, Path], log_content: str) -> Path:
        """
        Save processing log to episode directory
        
        Args:
            episode_paths: Episode path mappings
            log_content: Log content to save
            
        Returns:
            Path to saved log file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Save log directly in episode directory since metadata folder is removed
        log_file = episode_paths['episode_dir'] / f"processing_log_{timestamp}.txt"
        
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(log_content)
        
        logger.info(f"Saved processing log: {log_file}")
        return log_file


def create_output_structure(subtitle_file_path: str, language_code: str = "ko", base_output_dir: str = None, 
                            series_name: str = None, episode_name: str = None) -> Dict[str, Path]:
    """
    Convenience function to create complete output structure
    
    Args:
        subtitle_file_path: Path to subtitle file
        language_code: Target language code
        base_output_dir: Base output directory (defaults to LANGFLIX_OUTPUT_DIR env or 'output')
        series_name: Optional series name (if not provided, extracted from subtitle path)
        episode_name: Optional episode name (if not provided, extracted from subtitle path)
        
    Returns:
        Complete path mappings for the episode and language
    """
    if base_output_dir is None:
        base_output_dir = os.getenv('LANGFLIX_OUTPUT_DIR', 'output')
    manager = OutputManager(base_output_dir)
    
    # Extract series and episode names (use provided values if available)
    if series_name and episode_name:
        logger.info(f"Using provided series/episode names: {series_name}/{episode_name}")
    else:
        series_name, episode_name = manager.get_series_episode_name(subtitle_file_path)
        logger.info(f"Extracted series/episode names from path: {series_name}/{episode_name}")
    
    # Create episode structure
    episode_paths = manager.create_episode_structure(series_name, episode_name)
    
    # Create language structure
    lang_paths = manager.create_language_structure(episode_paths, language_code)
    
    # Combine paths
    complete_paths = {
        'episode': episode_paths,
        'language': lang_paths,
        'series_name': series_name,
        'episode_name': episode_name
    }
    
    return complete_paths
