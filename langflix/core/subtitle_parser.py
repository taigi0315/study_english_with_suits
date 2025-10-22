import pysrt
import re
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from langflix import settings
from langflix.core.subtitle_exceptions import (
    SubtitleNotFoundError,
    SubtitleFormatError,
    SubtitleEncodingError,
    SubtitleParseError
)

logger = logging.getLogger(__name__)

# Supported subtitle formats
SUPPORTED_FORMATS = {'.srt', '.vtt', '.ass', '.ssa'}


def validate_subtitle_file(file_path: str) -> tuple[bool, Optional[str]]:
    """
    Validate subtitle file existence and format.
    
    Args:
        file_path: Path to the subtitle file
        
    Returns:
        Tuple of (is_valid, error_message)
        
    Raises:
        SubtitleNotFoundError: If file doesn't exist
        SubtitleFormatError: If file format is not supported
    """
    path = Path(file_path)
    
    # Check file existence
    if not path.exists():
        raise SubtitleNotFoundError(str(path))
    
    # Check if it's a file (not a directory)
    if not path.is_file():
        raise SubtitleFormatError(
            format_type="unknown",
            reason=f"Path exists but is not a file: {path}"
        )
    
    # Check file extension
    file_extension = path.suffix.lower()
    if file_extension not in SUPPORTED_FORMATS:
        supported = ", ".join(SUPPORTED_FORMATS)
        raise SubtitleFormatError(
            format_type=file_extension,
            reason=f"Unsupported format. Supported formats: {supported}"
        )
    
    logger.info(f"✅ Subtitle file validated: {path}")
    return True, None


def detect_encoding(file_path: str) -> str:
    """
    Detect file encoding using chardet library.
    
    Args:
        file_path: Path to the subtitle file
        
    Returns:
        Detected encoding (e.g., 'utf-8', 'cp949', 'euc-kr')
        
    Raises:
        SubtitleEncodingError: If encoding cannot be detected
    """
    try:
        import chardet
    except ImportError:
        logger.warning("chardet not installed, assuming UTF-8 encoding")
        return 'utf-8'
    
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read()
            result = chardet.detect(raw_data)
            
            if result['encoding'] is None:
                raise SubtitleEncodingError(
                    path=file_path,
                    attempted_encodings=['auto-detection failed']
                )
            
            encoding = result['encoding']
            confidence = result['confidence']
            
            logger.info(f"Detected encoding: {encoding} (confidence: {confidence:.2%})")
            return encoding
            
    except Exception as e:
        logger.error(f"Encoding detection failed: {e}")
        raise SubtitleEncodingError(
            path=file_path,
            attempted_encodings=['chardet']
        )


def parse_srt_file(file_path: str, validate: bool = True) -> List[Dict[str, Any]]:
    """
    Parses a .srt subtitle file into a list of dictionaries.
    
    Args:
        file_path: Path to the subtitle file
        validate: Whether to validate file before parsing (default: True)
    
    Returns:
        List of dictionaries with 'start_time', 'end_time', 'text' keys
        
    Raises:
        SubtitleNotFoundError: If file doesn't exist
        SubtitleFormatError: If format is invalid
        SubtitleParseError: If parsing fails
    """
    try:
        # Validate file if requested
        if validate:
            validate_subtitle_file(file_path)
        
        # Detect encoding
        try:
            encoding = detect_encoding(file_path)
        except SubtitleEncodingError:
            logger.warning(f"Failed to detect encoding, trying UTF-8")
            encoding = 'utf-8'
        
        # Parse with detected encoding
        try:
            subs = pysrt.open(file_path, encoding=encoding)
        except UnicodeDecodeError:
            # Fallback to common encodings
            fallback_encodings = ['utf-8', 'cp949', 'euc-kr', 'latin-1']
            logger.warning(f"Failed with {encoding}, trying fallback encodings")
            
            for fallback in fallback_encodings:
                try:
                    subs = pysrt.open(file_path, encoding=fallback)
                    logger.info(f"Successfully parsed with fallback encoding: {fallback}")
                    break
                except UnicodeDecodeError:
                    continue
            else:
                raise SubtitleEncodingError(
                    path=file_path,
                    attempted_encodings=[encoding] + fallback_encodings
                )
        
        result = []
        for sub in subs:
            result.append({
                'start_time': str(sub.start.to_time()),
                'end_time': str(sub.end.to_time()),
                'text': sub.text
            })
        
        logger.info(f"Parsed {len(result)} subtitle entries from {file_path}")
        return result
        
    except (SubtitleNotFoundError, SubtitleFormatError, SubtitleEncodingError):
        # Re-raise our custom exceptions
        raise
    except Exception as e:
        logger.error(f"Error parsing subtitle file: {e}")
        raise SubtitleParseError(
            path=file_path,
            reason=str(e)
        )

def parse_subtitle_file(file_path: str) -> List[pysrt.SubRipItem]:
    """
    Parses a .srt subtitle file into a list of SubRipItem objects.
    (Legacy function for backward compatibility)
    """
    try:
        subs = pysrt.open(file_path)
        return subs
    except Exception as e:
        print(f"Error parsing subtitle file: {e}")
        return []

def chunk_subtitles(subtitles: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    """
    Chunks a list of subtitles into smaller lists, ensuring each chunk's
    total text length does not exceed MAX_LLM_INPUT_LENGTH.
    """
    chunks = []
    current_chunk = []
    current_length = 0

    for sub in subtitles:
        # Clean HTML markup for more accurate length calculation
        clean_text = re.sub(r'<[^>]+>', '', sub['text'])  # Remove HTML tags
        clean_text = re.sub(r'\s+', ' ', clean_text)      # Normalize whitespace
        text_length = len(clean_text)
        
        if current_length + text_length > settings.MAX_LLM_INPUT_LENGTH:
            chunks.append(current_chunk)
            current_chunk = [sub]
            current_length = text_length
        else:
            current_chunk.append(sub)
            current_length += text_length
    
    if current_chunk:
        chunks.append(current_chunk)
        
    return chunks
