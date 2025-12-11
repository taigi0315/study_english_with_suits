#!/usr/bin/env python3
"""
Transition Generator for LangFlix
Creates transition videos between clips

Extracted from video_editor.py as part of TICKET-090 refactoring.
"""

import ffmpeg
import logging
from pathlib import Path
from typing import Optional

from langflix import settings

logger = logging.getLogger(__name__)


class TransitionGenerator:
    """
    Generates transition videos between video clips.
    
    This class handles:
    - Creating transition videos from static images
    - Adding sound effects to transitions
    - Matching source video codec/resolution parameters
    """
    
    def __init__(
        self,
        output_dir: Path,
        temp_manager,
        video_editor_ref=None
    ):
        """
        Initialize TransitionGenerator.
        
        Args:
            output_dir: Directory for output files
            temp_manager: Temp file manager for cleanup
            video_editor_ref: Reference to parent VideoEditor
        """
        self.output_dir = Path(output_dir)
        self.temp_manager = temp_manager
        self._video_editor = video_editor_ref
    
    def _register_temp_file(self, file_path: Path):
        """Register a temporary file for cleanup later"""
        self.temp_manager.register(file_path)
    
    def create_transition_video(
        self,
        duration: float,
        image_path: str,
        sound_effect_path: str,
        source_video_path: str,
        aspect_ratio: str = "16:9"
    ) -> Optional[Path]:
        """
        Create transition video from static image with sound effect.

        Args:
            duration: Transition duration in seconds (e.g., 0.3s)
            image_path: Path to transition image
            sound_effect_path: Path to sound effect MP3
            source_video_path: Source video to match codec/resolution/params
            aspect_ratio: "16:9" for long-form or "9:16" for short-form

        Returns:
            Path to created transition video, or None if creation failed
        """
        # Delegate to VideoEditor's implementation for now
        if self._video_editor:
            return self._video_editor._create_transition_video(
                duration, image_path, sound_effect_path,
                source_video_path, aspect_ratio
            )
        
        raise RuntimeError("TransitionGenerator requires VideoEditor reference for now")
