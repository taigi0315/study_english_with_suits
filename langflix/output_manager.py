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
        
        # Create shared resources directory
        shared_dir = episode_dir / "shared"
        shared_dir.mkdir(exist_ok=True)
        
        # Create shared subdirectories
        video_clips_dir = shared_dir / "video_clips"
        audio_clips_dir = shared_dir / "audio_clips"
        templates_dir = shared_dir / "templates"
        
        video_clips_dir.mkdir(exist_ok=True)
        audio_clips_dir.mkdir(exist_ok=True)
        templates_dir.mkdir(exist_ok=True)
        
        # Create translations directory
        translations_dir = episode_dir / "translations"
        translations_dir.mkdir(exist_ok=True)
        
        # Create metadata directory
        metadata_dir = episode_dir / "metadata"
        metadata_dir.mkdir(exist_ok=True)
        
        # Create llm_outputs subdirectory
        llm_outputs_dir = metadata_dir / "llm_outputs"
        llm_outputs_dir.mkdir(exist_ok=True)
        
        # Return path mappings
        paths = {
            'episode_dir': episode_dir,
            'shared': {
                'video_clips': video_clips_dir,
                'audio_clips': audio_clips_dir,
                'templates': templates_dir
            },
            'translations': translations_dir,
            'metadata': {
                'main': metadata_dir,
                'llm_outputs': llm_outputs_dir
            }
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
        # Create language directory
        lang_dir = episode_paths['translations'] / language_code
        lang_dir.mkdir(exist_ok=True)
        
        # Create language subdirectories
        subtitles_dir = lang_dir / "subtitles"
        context_videos_dir = lang_dir / "context_videos"
        slides_dir = lang_dir / "slides"
        final_videos_dir = lang_dir / "final_videos"
        
        subtitles_dir.mkdir(exist_ok=True)
        context_videos_dir.mkdir(exist_ok=True)
        slides_dir.mkdir(exist_ok=True)
        final_videos_dir.mkdir(exist_ok=True)
        
        # Return language-specific paths
        lang_paths = {
            'language_dir': lang_dir,
            'subtitles': subtitles_dir,
            'context_videos': context_videos_dir,
            'slides': slides_dir,
            'final_videos': final_videos_dir
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
            # Pattern 2: "Suits.S01E01.720p.HDTV.x264"
            r'^(.+?)\.S(\d+)E(\d+)\.(.+)$',
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
                    # Handle S01E01 format
                    series_name = match.group(1)
                    season = match.group(2)
                    episode = match.group(3)
                    episode_name = f"S{season}E{episode}"
                    if len(match.groups()) > 3:
                        episode_name += f"_{match.group(4)}"
                else:
                    # Handle other formats
                    series_name = match.group(1)
                    episode_num = match.group(2)
                    if len(match.groups()) > 2:
                        episode_title = match.group(3)
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
        
        metadata_file = episode_paths['metadata']['main'] / "expressions.json"
        
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
        log_file = episode_paths['metadata']['main'] / f"processing_log_{timestamp}.txt"
        
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(log_content)
        
        logger.info(f"Saved processing log: {log_file}")
        return log_file


def create_output_structure(subtitle_file_path: str, language_code: str = "ko", base_output_dir: str = "output") -> Dict[str, Path]:
    """
    Convenience function to create complete output structure
    
    Args:
        subtitle_file_path: Path to subtitle file
        language_code: Target language code
        base_output_dir: Base output directory (default: "output")
        
    Returns:
        Complete path mappings for the episode and language
    """
    manager = OutputManager(base_output_dir)
    
    # Extract series and episode names
    series_name, episode_name = manager.get_series_episode_name(subtitle_file_path)
    
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
