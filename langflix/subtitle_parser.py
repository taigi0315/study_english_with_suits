import pysrt
from typing import List, Dict, Any
from . import settings

def parse_srt_file(file_path: str) -> List[Dict[str, Any]]:
    """
    Parses a .srt subtitle file into a list of dictionaries.
    
    Returns:
        List of dictionaries with 'start_time', 'end_time', 'text' keys
    """
    try:
        subs = pysrt.open(file_path)
        result = []
        
        for sub in subs:
            result.append({
                'start_time': str(sub.start.to_time()),
                'end_time': str(sub.end.to_time()),
                'text': sub.text
            })
        
        return result
    except Exception as e:
        print(f"Error parsing subtitle file: {e}")
        return []

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
        text_length = len(sub['text'])
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
