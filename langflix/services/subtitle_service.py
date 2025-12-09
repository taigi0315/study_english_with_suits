from pathlib import Path
from typing import List, Dict, Any, Union
import logging
from langflix.core.subtitle_parser import parse_subtitle_file_by_extension, chunk_subtitles

logger = logging.getLogger(__name__)

class SubtitleService:
    """Service for parsing and processing subtitles."""
    
    def parse(self, subtitle_path: Union[str, Path]) -> List[Dict[str, Any]]:
        """
        Parse subtitle file (supports SRT, VTT, SMI, ASS, SSA formats).
        
        Args:
            subtitle_path: Path to the subtitle file.
            
        Returns:
            List of subtitle entries (index, start, end, text).
        """
        try:
            path_str = str(subtitle_path)
            logger.info(f"Parsing subtitles from: {path_str}")
            subtitles = parse_subtitle_file_by_extension(path_str)
            logger.info(f"Parsed {len(subtitles)} subtitle entries")
            return subtitles
        except Exception as e:
            logger.error(f"Error parsing subtitles: {e}")
            raise

    def chunk(self, subtitles: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """
        Chunk subtitles into manageable groups for LLM processing.
        
        Args:
            subtitles: List of subtitle entries.
            
        Returns:
            List of subtitle chunks.
        """
        try:
            chunks = chunk_subtitles(subtitles)
            logger.info(f"Created {len(chunks)} chunks from {len(subtitles)} subtitles")
            return chunks
        except Exception as e:
            logger.error(f"Error chunking subtitles: {e}")
            raise
