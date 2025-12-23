import pysrt
import re
import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import timedelta
from langflix import settings
from langflix.core.subtitle_exceptions import (
    SubtitleNotFoundError,
    SubtitleFormatError,
    SubtitleEncodingError,
    SubtitleParseError
)

logger = logging.getLogger(__name__)

# Supported subtitle formats
SUPPORTED_FORMATS = {'.srt', '.vtt', '.ass', '.ssa', '.smi'}


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
            # Read file content first to normalize timestamps
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()

            # Normalize timestamps:
            # 1. Replace dot with comma (00:00:00.000 -> 00:00:00,000)
            # 2. Truncate microseconds to milliseconds (000000 -> 000)
            # Pattern matches: 00:00:00 followed by DOT or COMMA, then 3 digits, then optional extra digits
            import re
            def normalize_timestamp(match):
                # group(1): HH:MM:SS
                # group(2): mmm (first 3 digits)
                return f"{match.group(1)},{match.group(2)}"
            
            # Regex: (HH:MM:SS)[.,](\d{3})\d*
            # We look for lines starting with digit or arrow to be safe, but global replacement on timestamp-like patterns is usually safe in SRT
            # Standard SRT timestamp: 00:00:00,000 --> 00:00:00,000
            content = re.sub(r'(\d{2}:\d{2}:\d{2})[.,](\d{3})\d*', normalize_timestamp, content)
            
            subs = pysrt.from_string(content)
        except UnicodeDecodeError:
            # Fallback to common encodings
            fallback_encodings = ['utf-8', 'cp949', 'euc-kr', 'latin-1']
            logger.warning(f"Failed with {encoding}, trying fallback encodings")
            
            for fallback in fallback_encodings:
                try:
                    with open(file_path, 'r', encoding=fallback) as f:
                        content = f.read()
                    
                    # Apply normalization to fallback content
                    content = re.sub(r'(\d{2}:\d{2}:\d{2})[.,](\d{3})\d*', normalize_timestamp, content)
                    
                    subs = pysrt.from_string(content)
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

def parse_smi_file(file_path: str, validate: bool = True) -> List[Dict[str, Any]]:
    """
    Parses a .smi subtitle file into a list of dictionaries.
    
    Args:
        file_path: Path to the subtitle file
        validate: Whether to validate file before parsing (default: True)
    
    Returns:
        List of dictionaries with 'start_time', 'end_time', 'text' keys
        Times are in "HH:MM:SS.mmm" format (compatible with SRT format)
        
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
        
        # Parse SMI file using regex (more tolerant of malformed XML)
        # Many SMI files have complex HTML structures that break XML parsers
        # So we use regex to extract SYNC blocks and text content directly
        try:
            # Read file with detected encoding
            with open(file_path, 'r', encoding=encoding) as f:
                content = f.read()
        except (UnicodeDecodeError, ValueError):
            # Try common Korean encodings
            fallback_encodings = ['euc-kr', 'cp949', 'utf-8', 'latin-1']
            logger.warning(f"Failed with {encoding}, trying fallback encodings")
            
            for fallback in fallback_encodings:
                try:
                    with open(file_path, 'r', encoding=fallback) as f:
                        content = f.read()
                    logger.info(f"Successfully read with fallback encoding: {fallback}")
                    break
                except (UnicodeDecodeError, ValueError):
                    continue
            else:
                raise SubtitleEncodingError(
                    path=file_path,
                    attempted_encodings=[encoding] + fallback_encodings
                )
        
        # Extract SYNC blocks using regex
        # Pattern: <SYNC Start=123><P Class=...>text</P></SYNC>
        # More tolerant of malformed XML
        import re
        
        # Find all SYNC blocks
        sync_pattern = r'<SYNC\s+Start=(\d+)>(.*?)</SYNC>'
        sync_matches = re.findall(sync_pattern, content, re.DOTALL | re.IGNORECASE)
        
        if not sync_matches:
            # Try alternative pattern without closing tag
            sync_pattern_alt = r'<SYNC\s+Start=(\d+)>(.*?)(?=<SYNC|</BODY>|$)'
            sync_matches = re.findall(sync_pattern_alt, content, re.DOTALL | re.IGNORECASE)
        
        result = []
        
        for i, (start_attr, sync_content) in enumerate(sync_matches):
            try:
                start_time_ms = int(start_attr)
            except ValueError:
                logger.warning(f"Invalid Start attribute: {start_attr}, skipping")
                continue
            
            start_time_seconds = start_time_ms / 1000.0
            
            # Calculate end_time from next sync or use default duration
            if i + 1 < len(sync_matches):
                next_start_attr = sync_matches[i + 1][0]
                try:
                    next_start_ms = int(next_start_attr)
                    end_time_seconds = next_start_ms / 1000.0
                except ValueError:
                    end_time_seconds = start_time_seconds + 2.0
            else:
                # Default duration for last subtitle
                end_time_seconds = start_time_seconds + 2.0
            
            # Extract text from P tags using regex
            # Remove all HTML tags and extract text
            # Handle HTML entities
            html_entities = {
                '&nbsp;': ' ',
                '&amp;': '&',
                '&lt;': '<',
                '&gt;': '>',
                '&quot;': '"',
                '&apos;': "'",
            }
            
            # Extract P tag content
            p_pattern = r'<P[^>]*>(.*?)</P>'
            p_matches = re.findall(p_pattern, sync_content, re.DOTALL | re.IGNORECASE)
            
            text_parts = []
            for p_content in p_matches:
                # Remove HTML tags
                text = re.sub(r'<[^>]+>', '', p_content)
                # Replace HTML entities
                for entity, char in html_entities.items():
                    text = text.replace(entity, char)
                # Replace <br> tags with newline
                text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
                text = text.strip()
                if text:
                    text_parts.append(text)
            
            # If no P tags found, try to extract any text content
            if not text_parts:
                # Remove all tags and extract text
                text = re.sub(r'<[^>]+>', '', sync_content)
                for entity, char in html_entities.items():
                    text = text.replace(entity, char)
                text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
                text = text.strip()
                if text:
                    text_parts.append(text)
            
            if text_parts:
                # Join multiple P tags with newline
                text = '\n'.join(text_parts)
                
                # Convert seconds to "HH:MM:SS.mmm" format (compatible with SRT)
                start_time_str = _seconds_to_time_string(start_time_seconds)
                end_time_str = _seconds_to_time_string(end_time_seconds)
                
                result.append({
                    'start_time': start_time_str,
                    'end_time': end_time_str,
                    'text': text
                })
        
        logger.info(f"Parsed {len(result)} SMI subtitle entries from {file_path}")
        return result
        
    except (SubtitleNotFoundError, SubtitleFormatError, SubtitleEncodingError):
        # Re-raise our custom exceptions
        raise
    except Exception as e:
        logger.error(f"Error parsing SMI file: {e}")
        raise SubtitleParseError(
            path=file_path,
            reason=f"Failed to parse SMI file: {e}"
        )


def _seconds_to_time_string(seconds: float) -> str:
    """
    Convert seconds to "HH:MM:SS.mmm" format (compatible with SRT format).
    
    Args:
        seconds: Time in seconds as float
        
    Returns:
        Time string in "HH:MM:SS.mmm" format
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


def parse_subtitle_file_by_extension(file_path: str) -> List[Dict[str, Any]]:
    """
    Parse subtitle file based on extension.
    Supports SRT, VTT, ASS, SSA, and SMI formats.
    
    Args:
        file_path: Path to subtitle file
        
    Returns:
        List of dictionaries with 'start_time', 'end_time', 'text' keys
        
    Raises:
        SubtitleFormatError: If format is not supported
        SubtitleParseError: If parsing fails
    """
    path = Path(file_path)
    extension = path.suffix.lower()
    
    if extension == '.srt':
        return parse_srt_file(file_path)
    elif extension == '.smi':
        return parse_smi_file(file_path)
    elif extension in {'.vtt', '.ass', '.ssa'}:
        # TODO: Implement parsers for VTT, ASS, SSA if not already done
        raise NotImplementedError(f"Parser for {extension} not yet implemented")
    else:
        raise SubtitleFormatError(
            format_type=extension,
            reason=f"Unsupported format: {extension}. Supported formats: {', '.join(SUPPORTED_FORMATS)}"
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
        
        if settings.MAX_LLM_INPUT_LENGTH > 0 and current_length + text_length > settings.MAX_LLM_INPUT_LENGTH:
            chunks.append(current_chunk)
            current_chunk = [sub]
            current_length = text_length
        else:
            current_chunk.append(sub)
            current_length += text_length
    
    if current_chunk:
        chunks.append(current_chunk)
        
    return chunks
