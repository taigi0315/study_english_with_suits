"""
Dual Language Subtitle Support for LangFlix V2.

This module provides models and services for working with dual-language
subtitles (source + target) from Netflix.

File Structure:
    {media_name}.mp4
    {media_name}/
        ├── 3_Korean.srt
        ├── 6_English.srt
        └── ...
"""
import logging
from typing import List, Optional, Tuple, Dict
from pathlib import Path
from pydantic import BaseModel, Field

from langflix.core.subtitle_parser import parse_srt_file
from langflix.utils.path_utils import (
    get_subtitle_file,
    discover_subtitle_languages,
    validate_dual_subtitle_availability,
)

logger = logging.getLogger(__name__)


class SubtitleEntry(BaseModel):
    """
    A single subtitle entry with timing and text.
    """
    index: int = Field(description="1-indexed position in the subtitle file")
    start_time: str = Field(description="Start timestamp (HH:MM:SS,mmm)")
    end_time: str = Field(description="End timestamp (HH:MM:SS,mmm)")
    text: str = Field(description="Subtitle text content")
    
    @property
    def start_seconds(self) -> float:
        """Convert start_time to seconds."""
        return self._time_to_seconds(self.start_time)
    
    @property
    def end_seconds(self) -> float:
        """Convert end_time to seconds."""
        return self._time_to_seconds(self.end_time)
    
    @staticmethod
    def _time_to_seconds(time_str: str) -> float:
        """Convert timestamp string to seconds."""
        # Handle both comma and period separators
        time_str = time_str.replace(',', '.')
        parts = time_str.split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
        return hours * 3600 + minutes * 60 + seconds


class AlignedSubtitlePair(BaseModel):
    """
    A pair of aligned source and target subtitle entries.
    """
    source: SubtitleEntry = Field(description="Source language subtitle")
    target: SubtitleEntry = Field(description="Target language subtitle")
    
    @property
    def source_text(self) -> str:
        """Get source subtitle text."""
        return self.source.text
    
    @property
    def target_text(self) -> str:
        """Get target subtitle text."""
        return self.target.text


class DualSubtitle(BaseModel):
    """
    Container for dual-language subtitles with alignment support.
    
    Provides access to both source and target language subtitles
    and utilities for finding aligned pairs.
    """
    source_language: str = Field(description="Source language name (e.g., 'English')")
    target_language: str = Field(description="Target language name (e.g., 'Korean')")
    source_entries: List[SubtitleEntry] = Field(default_factory=list)
    target_entries: List[SubtitleEntry] = Field(default_factory=list)
    media_path: Optional[str] = Field(default=None, description="Path to associated media file")
    
    @property
    def source_count(self) -> int:
        """Number of source subtitle entries."""
        return len(self.source_entries)
    
    @property
    def target_count(self) -> int:
        """Number of target subtitle entries."""
        return len(self.target_entries)
    
    @property
    def is_aligned(self) -> bool:
        """Check if source and target have same number of entries."""
        return self.source_count == self.target_count
    
    def get_aligned_pair(self, index: int) -> Optional[AlignedSubtitlePair]:
        """
        Get aligned source/target pair by index.
        
        Args:
            index: 0-indexed position
            
        Returns:
            AlignedSubtitlePair or None if index out of range
        """
        if 0 <= index < min(self.source_count, self.target_count):
            return AlignedSubtitlePair(
                source=self.source_entries[index],
                target=self.target_entries[index]
            )
        return None
    
    def get_pairs_in_range(
        self, 
        start_time: float, 
        end_time: float
    ) -> List[AlignedSubtitlePair]:
        """
        Get all aligned pairs that fall within a time range.
        
        Args:
            start_time: Start time in seconds
            end_time: End time in seconds
            
        Returns:
            List of AlignedSubtitlePair objects
        """
        pairs = []
        for i in range(min(self.source_count, self.target_count)):
            source = self.source_entries[i]
            if source.start_seconds >= start_time and source.end_seconds <= end_time:
                pair = self.get_aligned_pair(i)
                if pair:
                    pairs.append(pair)
        return pairs
    
    def to_dialogue_format(self) -> Tuple[List[Dict], List[Dict]]:
        """
        Convert to the dialogue format expected by the LLM prompt.
        
        Returns:
            Tuple of (source_dialogues, target_dialogues) where each is a list
            of dicts with 'index', 'text', 'start', 'end' keys.
        """
        source_dialogues = []
        target_dialogues = []
        
        for i in range(min(self.source_count, self.target_count)):
            source = self.source_entries[i]
            target = self.target_entries[i]
            
            source_dialogues.append({
                "index": i,
                "text": source.text,
                "start": source.start_time,
                "end": source.end_time,
            })
            target_dialogues.append({
                "index": i,
                "text": target.text,
                "start": target.start_time,
                "end": target.end_time,
            })
        
        return source_dialogues, target_dialogues


class DualSubtitleService:
    """
    Service for loading and managing dual-language subtitles.
    """
    
    def __init__(self):
        self._cache: Dict[str, DualSubtitle] = {}
    
    def load_dual_subtitles(
        self,
        media_path: str,
        source_lang: str,
        target_lang: str,
        source_variant: int = 0,
        target_variant: int = 0,
    ) -> DualSubtitle:
        """
        Load both source and target language subtitles for a media file.
        
        Args:
            media_path: Path to the media file
            source_lang: Source language name (e.g., "English")
            target_lang: Target language name (e.g., "Korean")
            source_variant: Which variant to use if multiple exist
            target_variant: Which variant to use if multiple exist
            
        Returns:
            DualSubtitle object with both languages loaded
            
        Raises:
            ValueError: If languages are the same or not available
        """
        # Validate availability
        is_valid, error = validate_dual_subtitle_availability(
            media_path, source_lang, target_lang
        )
        if not is_valid:
            raise ValueError(error)
        
        # Get subtitle file paths
        source_path = get_subtitle_file(media_path, source_lang, source_variant)
        target_path = get_subtitle_file(media_path, target_lang, target_variant)
        
        if not source_path or not target_path:
            raise ValueError(f"Could not find subtitle files for {source_lang}/{target_lang}")
        
        # Parse subtitles
        source_entries = self._parse_subtitle_file(source_path)
        target_entries = self._parse_subtitle_file(target_path)
        
        # Log alignment info
        if len(source_entries) != len(target_entries):
            logger.warning(
                f"Subtitle count mismatch: {source_lang}={len(source_entries)}, "
                f"{target_lang}={len(target_entries)}. Using min count."
            )
        
        dual_subtitle = DualSubtitle(
            source_language=source_lang,
            target_language=target_lang,
            source_entries=source_entries,
            target_entries=target_entries,
            media_path=media_path,
        )
        
        logger.info(
            f"Loaded dual subtitles: {source_lang} ({len(source_entries)}) / "
            f"{target_lang} ({len(target_entries)})"
        )
        
        return dual_subtitle
    
    def _parse_subtitle_file(self, path: str) -> List[SubtitleEntry]:
        """
        Parse a subtitle file into SubtitleEntry objects.
        
        Args:
            path: Path to the .srt file
            
        Returns:
            List of SubtitleEntry objects
        """
        try:
            parsed = parse_srt_file(path)
            entries = []
            
            for i, item in enumerate(parsed, start=1):
                entry = SubtitleEntry(
                    index=i,
                    start_time=item.get('start_time', '00:00:00,000'),
                    end_time=item.get('end_time', '00:00:00,000'),
                    text=item.get('text', ''),
                )
                entries.append(entry)
            
            return entries
            
        except Exception as e:
            logger.error(f"Failed to parse subtitle file {path}: {e}")
            raise
    
    def discover_languages(self, media_path: str) -> List[str]:
        """
        Get list of available languages for a media file.
        
        Args:
            media_path: Path to the media file
            
        Returns:
            Sorted list of language names
        """
        languages = discover_subtitle_languages(media_path)
        return sorted(languages.keys())


# Singleton instance for convenience
_service_instance: Optional[DualSubtitleService] = None


def get_dual_subtitle_service() -> DualSubtitleService:
    """Get the singleton DualSubtitleService instance."""
    global _service_instance
    if _service_instance is None:
        _service_instance = DualSubtitleService()
    return _service_instance
