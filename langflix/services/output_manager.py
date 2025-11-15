#!/usr/bin/env python3
"""
Output Manager for LangFlix
Manages organized output structure for scalable multi-language support
"""

import os
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

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
    
    def __init__(self, base_output_dir: str = "output"):
        """
        Initialize OutputManager
        
        Args:
            base_output_dir: Base output directory
        """
        self.base_output_dir = Path(base_output_dir)
        self.base_output_dir.mkdir(exist_ok=True)
        
    def create_episode_structure(self, series_name: str, episode_name: str) -> Dict[str, Path]:
        """
        Create organized folder structure for an episode
        
        Args:
            series_name: Name of the series (e.g., "Suits")
            episode_name: Name of the episode (e.g., "S01E01_Pilot")
            
        Returns:
            Dictionary with path mappings for different content types
        """
        # Create main episode directory
        episode_dir = self.base_output_dir / series_name / episode_name
        episode_dir.mkdir(parents=True, exist_ok=True)
        
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
        
        # Create language subdirectories
        subtitles_dir = lang_dir / "subtitles"
        context_videos_dir = lang_dir / "context_videos"
        slides_dir = lang_dir / "slides"
        videos_dir = lang_dir / "videos"  # Unified videos directory for all video outputs
        
        subtitles_dir.mkdir(exist_ok=True)
        context_videos_dir.mkdir(exist_ok=True)
        slides_dir.mkdir(exist_ok=True)
        videos_dir.mkdir(exist_ok=True)
        
        # Return language-specific paths
        lang_paths = {
            'language_dir': lang_dir,
            'subtitles': subtitles_dir,
            'context_videos': context_videos_dir,
            'slides': slides_dir,
            'videos': videos_dir,
            # Legacy path mappings for backward compatibility (all point to videos/)
            'final_videos': videos_dir,
            'context_slide_combined': videos_dir,
            'short_videos': videos_dir,
            'structured_videos': videos_dir
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
        subtitle_path = Path(subtitle_file_path)
        filename = subtitle_path.stem
        
        # Remove language suffix
        if filename.endswith('.en'):
            filename = filename[:-3]
        
        # Try different parsing patterns
        patterns = [
            # Pattern 1: "Suits - 1x01 - Pilot.720p.WEB-DL"
            r'^(.+?)\s*-\s*(\d+x\d+)\s*-\s*(.+)$',
            # Pattern 2: "Suits.S01E01.720p.HDTV.x264" - Extract only S01E01, ignore quality/resolution
            r'^(.+?)\.S(\d+)E(\d+)(?:\..+)?$',
            # Pattern 3: "Suits.S01E01"
            r'^(.+?)\.S(\d+)E(\d+)$',
            # Pattern 4: "Suits_1x01_Pilot"
            r'^(.+?)_(\d+x\d+)_(.+)$'
        ]
        
        import re
        
        for pattern in patterns:
            match = re.match(pattern, filename)
            if match:
                if 'S(\\d+)E(\\d+)' in pattern:
                    # Handle S01E01 format - extract only season/episode, ignore quality/resolution
                    series_name = match.group(1)
                    season = match.group(2)
                    episode = match.group(3)
                    # Use only S01E01 format, don't include quality/resolution info
                    episode_name = f"S{season}E{episode}"
                else:
                    # Handle other formats
                    series_name = match.group(1)
                    episode_num = match.group(2)
                    if len(match.groups()) > 2:
                        episode_title = match.group(3)
                        # Remove quality/resolution from episode title if present
                        episode_title = re.sub(r'\.\d+p\..*$', '', episode_title)  # Remove .720p.HDTV.x264 etc
                        episode_name = f"{episode_num}_{episode_title}"
                    else:
                        episode_name = episode_num
                
                return series_name, episode_name
        
        # Fallback naming
        series_name = "Unknown_Series"
        episode_name = "Unknown_Episode"
        
        return series_name, episode_name
    
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


def create_output_structure(subtitle_file_path: str, language_code: str = "ko", base_output_dir: str = "output", 
                            series_name: str = None, episode_name: str = None) -> Dict[str, Path]:
    """
    Convenience function to create complete output structure
    
    Args:
        subtitle_file_path: Path to subtitle file
        language_code: Target language code
        base_output_dir: Base output directory (default: "output")
        series_name: Optional series name (if not provided, extracted from subtitle path)
        episode_name: Optional episode name (if not provided, extracted from subtitle path)
        
    Returns:
        Complete path mappings for the episode and language
    """
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
