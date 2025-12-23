"""
Dual Language Subtitle Support for LangFlix.

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


def is_dialogue_entry(text: str) -> bool:
    """
    Check if a subtitle entry is actual dialogue (not sound effects/annotations).
    
    Netflix-style subtitles often include:
    - Sound effects: [불안한 음악] (anxious music)
    - Actions: [마이크를 딸각 켠다] (clicks microphone)
    - Speaker tags: [신도들] (congregation)
    
    These should be filtered for translation matching.
    """
    text = text.strip()
    
    # Empty text
    if not text:
        return False
    
    # Remove Unicode LTR marks that Netflix adds
    text = text.replace('\u200e', '').replace('\u200f', '').strip()
    
    # If entire text is wrapped in brackets, it's a sound effect/annotation
    if text.startswith('[') and text.endswith(']'):
        return False
    
    # If text only contains bracketed content (possibly multi-line)
    lines = text.split('\n')
    all_bracketed = all(
        line.strip().startswith('[') and line.strip().endswith(']')
        for line in lines if line.strip()
    )
    if all_bracketed and lines:
        return False
    
    # If text starts with a bracketed tag followed by actual dialogue, keep it
    # e.g., "[사라 부] 예수께서 말씀하시길" -> This is dialogue
    
    return True


def filter_dialogue_entries(entries: list) -> list:
    """Filter subtitle entries to only include actual dialogue."""
    return [e for e in entries if is_dialogue_entry(e.text)]


def fuzzy_match_by_timestamp(
    source_entries: list,
    target_entries: list,
    tolerance_seconds: float = 1.0
) -> list:
    """
    Match source and target subtitle entries by overlapping timestamps.
    
    Args:
        source_entries: List of SubtitleEntry from source language
        target_entries: List of SubtitleEntry from target language
        tolerance_seconds: Maximum time difference to consider a match
        
    Returns:
        List of tuples (source_entry, target_entry) for matched pairs
    """
    matched_pairs = []
    used_target_indices = set()
    
    for source in source_entries:
        source_start = source.start_seconds
        source_end = source.end_seconds
        source_mid = (source_start + source_end) / 2
        
        best_match = None
        best_overlap = -1
        best_target_idx = -1
        
        for idx, target in enumerate(target_entries):
            if idx in used_target_indices:
                continue
                
            target_start = target.start_seconds
            target_end = target.end_seconds
            target_mid = (target_start + target_end) / 2
            
            # Calculate overlap
            overlap_start = max(source_start, target_start)
            overlap_end = min(source_end, target_end)
            overlap = max(0, overlap_end - overlap_start)
            
            # Also check midpoint distance for short subtitles
            mid_distance = abs(source_mid - target_mid)
            
            # Consider a match if there's overlap OR midpoints are close
            if overlap > 0 or mid_distance < tolerance_seconds:
                score = overlap if overlap > 0 else (1.0 / (mid_distance + 0.1))
                if score > best_overlap:
                    best_overlap = score
                    best_match = target
                    best_target_idx = idx
        
        if best_match is not None:
            matched_pairs.append((source, best_match))
            used_target_indices.add(best_target_idx)
    
    logger.info(
        f"Fuzzy timestamp matching: {len(matched_pairs)}/{len(source_entries)} source entries matched"
    )
    
    return matched_pairs

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
        use_fuzzy_matching: bool = True,
        tolerance_seconds: float = 1.0,
    ) -> DualSubtitle:
        """
        Load both source and target language subtitles for a media file.
        
        Args:
            media_path: Path to the media file
            source_lang: Source language name (e.g., "English")
            target_lang: Target language name (e.g., "Korean")
            source_variant: Which variant to use if multiple exist
            target_variant: Which variant to use if multiple exist
            use_fuzzy_matching: If True, use timestamp-based matching instead of index
            tolerance_seconds: Max time difference for fuzzy matching
            
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
        source_entries_raw = self._parse_subtitle_file(source_path)
        target_entries_raw = self._parse_subtitle_file(target_path)
        
        logger.info(
            f"Loaded raw subtitles: {source_lang}={len(source_entries_raw)}, "
            f"{target_lang}={len(target_entries_raw)}"
        )
        
        # Filter non-dialogue entries (sound effects, annotations)
        source_entries_filtered = filter_dialogue_entries(source_entries_raw)
        target_entries_filtered = filter_dialogue_entries(target_entries_raw)
        
        logger.info(
            f"After filtering non-dialogue: {source_lang}={len(source_entries_filtered)}, "
            f"{target_lang}={len(target_entries_filtered)} "
            f"(removed {len(source_entries_raw) - len(source_entries_filtered)} + "
            f"{len(target_entries_raw) - len(target_entries_filtered)} annotations)"
        )
        
        if use_fuzzy_matching:
            # Use fuzzy timestamp matching for misaligned subtitles
            matched_pairs = fuzzy_match_by_timestamp(
                source_entries_filtered,
                target_entries_filtered,
                tolerance_seconds=tolerance_seconds
            )
            
            # Build aligned entry lists from matched pairs
            source_entries = [pair[0] for pair in matched_pairs]
            target_entries = [pair[1] for pair in matched_pairs]
            
            # Re-index entries to be sequential (0-based for internal use)
            for i, (src, tgt) in enumerate(zip(source_entries, target_entries)):
                src.index = i + 1
                tgt.index = i + 1
            
            logger.info(
                f"Fuzzy matching created {len(matched_pairs)} aligned pairs from "
                f"{len(source_entries_filtered)} source / {len(target_entries_filtered)} target entries"
            )
        else:
            # Fall back to index-based matching (original behavior)
            source_entries = source_entries_filtered
            target_entries = target_entries_filtered
            
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
            media_path=str(media_path),  # Convert to string for Pydantic
        )
        
        logger.info(
            f"Loaded dual subtitles: {source_lang} ({len(source_entries)}) / "
            f"{target_lang} ({len(target_entries)}) - "
            f"{'fuzzy matched' if use_fuzzy_matching else 'index aligned'}"
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
