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
    # Keep: ASCII alphanumeric, spaces, hyphens, underscores
    # Dots in base name are removed (only extension dots are preserved)
    # Use ASCII-only regex: [a-zA-Z0-9_\s-]
    if replace_spaces:
        # Replace spaces with underscores, then remove invalid chars
        sanitized = re.sub(r'[^a-zA-Z0-9_\s-]', '', base_name)  # ASCII only
        sanitized = re.sub(r'[-\s]+', '_', sanitized)
    else:
        # Keep spaces but still remove invalid chars
        sanitized = re.sub(r'[^a-zA-Z0-9_\s-]', '', base_name)  # ASCII only
        sanitized = re.sub(r'\s+', ' ', sanitized).strip()
    
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

