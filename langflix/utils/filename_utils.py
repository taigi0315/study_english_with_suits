"""
Filename sanitization utilities for safe file system operations.
"""
import re
from typing import Optional

# Maximum filename length (conservative for cross-platform compatibility)
MAX_FILENAME_LENGTH = 255  # Standard filesystem limit
DEFAULT_MAX_LENGTH = 100  # Reasonable default for our use case


def sanitize_filename(
    text: str,
    max_length: int = DEFAULT_MAX_LENGTH,
    replace_spaces: bool = True,
    allowed_extensions: Optional[list[str]] = None
) -> str:
    """
    Sanitize text to create a safe filename.
    
    Args:
        text: Input text to sanitize
        max_length: Maximum length of output (default: 100)
        replace_spaces: If True, replace spaces with underscores
        allowed_extensions: Optional list of allowed file extensions to preserve
    
    Returns:
        Sanitized filename-safe string
    
    Examples:
        >>> sanitize_filename("Hello World!")
        'Hello_World'
        >>> sanitize_filename("test.mp4", allowed_extensions=['.mp4'])
        'test.mp4'
        >>> sanitize_filename("very long filename that exceeds limit" * 10, max_length=50)
        'very_long_filename_that_exceeds_limit'
    """
    if not text:
        return "untitled"
    
    # Extract extension if preserving
    extension = ""
    base_name = text
    if allowed_extensions:
        # Check extensions in order (first match wins)
        # Match longest extension first to handle cases like .mkv.mp4
        sorted_extensions = sorted(allowed_extensions, key=len, reverse=True)
        for ext in sorted_extensions:
            if text.lower().endswith(ext.lower()):
                extension = ext  # Keep original case from allowed_extensions
                base_name = text[:-len(ext)]
                break
    
    # Remove or replace invalid characters
    # Support Unicode characters (Korean, etc) by removing only specific unsafe characters
    # unsafe chars: / \ : * ? " < > | and control chars
    # We also keep spaces (if configured), underscores, and hyphens.
    
    if replace_spaces:
        base_name = re.sub(r'[-\s]+', '_', base_name)
    else:
        base_name = re.sub(r'\s+', ' ', base_name).strip()
        
    # Remove filesystem unsafe characters
    # This regex removes anything that IS one of the forbidden chars
    sanitized = re.sub(r'[\\/*?:"<>|]', '', base_name)
    
    # Remove control characters
    sanitized = "".join(c for c in sanitized if c.isprintable())
    
    # Remove leading/trailing dots and underscores (invalid in some filesystems)
    sanitized = sanitized.strip('._-')
    
    # Remove any remaining dots (they should only be in extensions)
    sanitized = sanitized.replace('.', '')
    
    # Enforce length limit (accounting for extension)
    max_base_length = max_length - len(extension)
    if len(sanitized) > max_base_length:
        sanitized = sanitized[:max_base_length]
    
    # Ensure not empty
    if not sanitized:
        sanitized = "untitled"
    
    return sanitized + extension


def sanitize_for_expression_filename(expression: str, max_length: int = 50) -> str:
    """
    Sanitize expression text specifically for use in filenames.
    
    This is a convenience wrapper for common expression filename use case.
    
    Args:
        expression: Expression text to sanitize
        max_length: Maximum length (default: 50 for expressions)
    
    Returns:
        Sanitized filename
    """
    return sanitize_filename(
        expression,
        max_length=max_length,
        replace_spaces=True
    )


def sanitize_for_context_video_name(expression: str) -> str:
    """
    Sanitize expression for context video filename.
    
    Consistent naming for context videos across the codebase.
    
    Args:
        expression: Expression text
    
    Returns:
        Sanitized filename (no extension)
    """
    return sanitize_for_expression_filename(expression, max_length=50)


def extract_show_name(filename: str) -> str:
    """
    Extract show name from filename using common naming conventions.
    
    Handles patterns like:
    - Show.Name.S01E01... -> Show Name
    - Show Name - S01E01... -> Show Name
    - [Group] Show Name - 01... -> Show Name
    
    Args:
        filename: Input filename (with or without extension)
        
    Returns:
        Extracted show name, or sanitized filename if no pattern found.
    """
    if not filename:
        return "Unknown Show"
        
    # Remove extension
    base_name = filename.rsplit('.', 1)[0] if '.' in filename else filename
    
    # Remove release group tags at start like [Group] or (Group)
    base_name = re.sub(r'^[\[\(].*?[\]\)]\s*', '', base_name)
    
    # Pattern 1: Standard S01E01 or S01 patterns
    # Matches: "Show.Name.S01", "Show Name S01", "Show_Name_S01"
    match = re.search(r'(.+?)[._\s-]+S\d{1,2}(?:E\d{1,2})?', base_name, re.IGNORECASE)
    if match:
        raw_name = match.group(1)
        # Replace dots/underscores with spaces
        return raw_name.replace('.', ' ').replace('_', ' ').strip()
        
    # Pattern 2: Anime/Cartoon style " - 01" or " - 01 "
    # Matches: "Show Name - 01", "Show Name - 105"
    match = re.search(r'(.+?)\s+-\s+\d{2,3}', base_name)
    if match:
        return match.group(1).strip()
        
    # Fallback: Use the base name, replacing dots/underscores
    cleaned = base_name.replace('.', ' ').replace('_', ' ').strip()
    
    # Remove common release tags (Year, Resolution, Source, Codec)
    # e.g., "2025", "1080p", "WEBRip", "x264", "AAC"
    # Regex to match year (parentheses or not), resolution, source, codec
    # Matches: (2025), 2025, 1080p, 720p, WEBRip, BluRay, x264, h264, etc.
    tags_pattern = r'\b(19\d{2}|20\d{2}|2100)\b|\b\d{3,4}p\b|\b(?:WEB|HD)?Rip\b|\bBluRay\b|\bHDTV\b|\b[xh]26[45]\b|\bAAC\b|\bAC3\b|\bHEVC\b'
    cleaned = re.sub(tags_pattern, '', cleaned, flags=re.IGNORECASE).strip()
    
    # Clean up multiple spaces and trailing junk characters
    cleaned = re.sub(r'\s+', ' ', cleaned)
    cleaned = cleaned.strip(' -,.')
    
    return cleaned


