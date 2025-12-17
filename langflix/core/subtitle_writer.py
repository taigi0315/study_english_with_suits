"""
Utility module for writing subtitle files.

This module provides functions to write SubtitleEntry objects to SRT format files.
"""

from pathlib import Path
from typing import List
import logging

from langflix.core.dual_subtitle import SubtitleEntry

logger = logging.getLogger(__name__)


def write_srt_file(entries: List[SubtitleEntry], output_path: str) -> None:
    """
    Write SubtitleEntry objects to an SRT file.

    Args:
        entries: List of SubtitleEntry objects to write
        output_path: Path to output SRT file

    Raises:
        ValueError: If entries list is empty
        IOError: If file cannot be written
    """
    if not entries:
        raise ValueError("Cannot write empty subtitle list")

    logger.info(f"Writing {len(entries)} subtitle entries to {output_path}")

    srt_lines = []

    for entry in entries:
        # Entry index (1-based)
        srt_lines.append(str(entry.index))

        # Timestamp line (start --> end)
        srt_lines.append(f"{entry.start_time} --> {entry.end_time}")

        # Text content
        srt_lines.append(entry.text)

        # Empty line separator
        srt_lines.append("")

    # Write to file with UTF-8 encoding
    try:
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text("\n".join(srt_lines), encoding='utf-8')
        logger.info(f"Successfully wrote subtitle file: {output_path}")
    except Exception as e:
        logger.error(f"Failed to write subtitle file {output_path}: {e}")
        raise IOError(f"Failed to write subtitle file: {e}")


def seconds_to_srt_timestamp(seconds: float) -> str:
    """
    Convert seconds to SRT timestamp format (HH:MM:SS,mmm).

    Args:
        seconds: Time in seconds

    Returns:
        Formatted timestamp string (e.g., "00:01:23,456")
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millisecs = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millisecs:03d}"


def validate_subtitle_structure(entries: List[SubtitleEntry]) -> bool:
    """
    Validate that subtitle entries have proper structure.

    Args:
        entries: List of SubtitleEntry objects to validate

    Returns:
        True if valid, False otherwise
    """
    if not entries:
        return False

    for i, entry in enumerate(entries):
        # Check required fields
        if not entry.text or not entry.start_time or not entry.end_time:
            logger.warning(f"Entry {i+1} missing required fields")
            return False

        # Check index is sequential (1-based)
        if entry.index != i + 1:
            logger.warning(f"Entry {i+1} has incorrect index: {entry.index}")
            return False

    return True
