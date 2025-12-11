#!/usr/bin/env python3
"""
Video Batcher for LangFlix
Handles batching and combining multiple videos into unified outputs

Extracted from video_editor.py as part of TICKET-090 refactoring.
"""

import json
import ffmpeg
import logging
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional

from langflix import settings

logger = logging.getLogger(__name__)


class VideoBatcher:
    """
    Handles video batching and combination operations.
    
    This class manages:
    - Combining short format videos into batches of target duration
    - Creating individual video batches
    - Combining multiple videos into single output
    """
    
    def __init__(
        self,
        output_dir: Path,
        language_code: str,
        episode_name: str,
        temp_manager,
        paths: Dict[str, Any] = None,
        video_editor_ref=None
    ):
        """
        Initialize VideoBatcher.
        
        Args:
            output_dir: Directory for output files
            language_code: Target language code
            episode_name: Episode name for file naming
            temp_manager: Temp file manager for cleanup
            paths: Path structure from OutputManager
            video_editor_ref: Reference to parent VideoEditor for shared methods
        """
        self.output_dir = Path(output_dir)
        self.language_code = language_code
        self.episode_name = episode_name or "Unknown_Episode"
        self.temp_manager = temp_manager
        self.paths = paths or {}
        self._video_editor = video_editor_ref
    
    def _register_temp_file(self, file_path: Path):
        """Register a temporary file for cleanup later"""
        self.temp_manager.register(file_path)
    
    def _get_shorts_dir(self) -> Path:
        """
        Determine the correct shorts directory from available paths.
        
        Returns:
            Path to shorts directory
        """
        shorts_dir = None
        
        if self.paths:
            if 'shorts' in self.paths:
                shorts_dir = Path(self.paths['shorts'])
            elif 'language' in self.paths and isinstance(self.paths['language'], dict):
                if 'shorts' in self.paths['language']:
                    shorts_dir = Path(self.paths['language']['shorts'])
                elif 'language_dir' in self.paths['language']:
                    shorts_dir = Path(self.paths['language']['language_dir']) / "shorts"
            elif 'language_dir' in self.paths:
                shorts_dir = Path(self.paths['language_dir']) / "shorts"
        
        # Fallback: derive from output_dir
        if shorts_dir is None:
            if hasattr(self.output_dir, 'parent'):
                lang_dir = self.output_dir.parent
                if lang_dir.name in ['ko', 'ja', 'zh', 'en', 'es', 'fr']:
                    shorts_dir = lang_dir / "shorts"
                else:
                    shorts_dir = self.output_dir.parent / "shorts"
            else:
                shorts_dir = Path(self.output_dir).parent / "shorts"
        
        shorts_dir.mkdir(parents=True, exist_ok=True)
        return shorts_dir
    
    def create_batched_short_videos(
        self,
        short_format_videos: List[Tuple[str, float]],
        target_duration: float = 120.0
    ) -> List[str]:
        """
        Combine short format videos into batches of ~target_duration seconds each.
        
        Args:
            short_format_videos: List of (video_path, duration) tuples
            target_duration: Target duration for each batch (default: 120 seconds)
        
        Returns:
            List of created batch video paths
        """
        # Delegate to VideoEditor's implementation for now
        if self._video_editor:
            return self._video_editor.create_batched_short_videos(
                short_format_videos, target_duration
            )
        
        raise RuntimeError("VideoBatcher requires VideoEditor reference for now")
    
    def combine_videos(self, video_paths: List[str], output_path: str) -> str:
        """
        Combine multiple videos into a single video file.

        Args:
            video_paths: List of paths to video files to combine.
            output_path: Path where the combined video should be saved.

        Returns:
            str: Path to the combined video.
        """
        # Delegate to VideoEditor's implementation for now
        if self._video_editor:
            return self._video_editor.combine_videos(video_paths, output_path)
        
        raise RuntimeError("VideoBatcher requires VideoEditor reference for now")
    
    def create_video_batch(
        self,
        video_paths: List[str],
        batch_number: int,
        metadata_entries: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Create a single batch video from a list of video paths.
        
        Args:
            video_paths: List of video file paths to batch
            batch_number: Batch sequence number
            metadata_entries: Optional metadata for the batch
            
        Returns:
            Path to the created batch video
        """
        # Delegate to VideoEditor's implementation for now
        if self._video_editor:
            return self._video_editor._create_video_batch(
                video_paths, batch_number, metadata_entries
            )
        
        raise RuntimeError("VideoBatcher requires VideoEditor reference for now")
