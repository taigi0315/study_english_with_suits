"""
Expression utility functions - centralized helpers for expression data access.

This module consolidates duplicate helper functions that were scattered across:
- subtitle_processor.py
- video_factory.py
- short_form_creator.py
- video_editor.py
"""

from typing import Any, Optional



def clean_display_text(text: str) -> str:
    """
    Clean text for display (remove sound effects [..] and technical artifacts).
    Preserves speaker labels (..) and punctuation in speech.
    
    Args:
        text: Raw text to clean
        
    Returns:
        Cleaned text string
    """
    if not text:
        return ""
        
    import re
    # Pattern to match content inside square brackets, including the brackets
    bracket_pattern = re.compile(r'\[.*?\]', re.DOTALL)
    
    # Pattern for invisible characters (LTR/RTL marks, ZWSP, BOM, etc.)
    invisible_chars = re.compile(r'[\u200b\u200c\u200d\u200e\u200f\ufeff]')
    
    # Remove content in brackets
    cleaned_text = bracket_pattern.sub('', text)
    
    # Remove invisible characters
    cleaned_text = invisible_chars.sub('', cleaned_text)
    
    # Clean up extra whitespace
    cleaned_text = ' '.join(cleaned_text.split())
    
    return cleaned_text


def get_expr_attr(expression: Any, attr_name: str, default: Any = None) -> Any:
    """
    Safely get attribute from expression object or dict.

    Handles both dict-style and object-style expression data structures.

    Args:
        expression: ExpressionAnalysis object or dict
        attr_name: Attribute/key name to retrieve
        default: Default value if attribute doesn't exist

    Returns:
        Attribute value or default

    Examples:
        >>> expr_dict = {'expression': 'get screwed', 'translation': '망하다'}
        >>> get_expr_attr(expr_dict, 'expression')
        'get screwed'

        >>> expr_obj = ExpressionAnalysis(expression='get screwed')
        >>> get_expr_attr(expr_obj, 'expression')
        'get screwed'
    """
    if isinstance(expression, dict):
        return expression.get(attr_name, default)
    return getattr(expression, attr_name, default)


def clean_text_for_matching(text: str) -> str:
    """
    Clean text for consistent subtitle-to-dialogue matching.

    Normalizes text by:
    - Converting to lowercase
    - Removing extra whitespace
    - Removing punctuation
    - Keeping only alphanumeric characters and spaces

    Args:
        text: Raw text to clean

    Returns:
        Cleaned text string

    Examples:
        >>> clean_text_for_matching("Hello,  World!")
        'hello world'

        >>> clean_text_for_matching("  What's   up?  ")
        'whats up'
    """
    if not text:
        return ""

    # Remove content in brackets and parentheses (e.g., [Sound], (Speaker))
    import re
    cleaned = re.sub(r'\[.*?\]', '', text)
    cleaned = re.sub(r'\(.*?\)', '', cleaned)

    # Normalize whitespace and case
    cleaned = " ".join(cleaned.strip().lower().split())

    # Remove punctuation - keep only alphanumeric and spaces
    cleaned = ''.join(c for c in cleaned if c.isalnum() or c.isspace())

    return cleaned


def is_non_speech_subtitle(text: str) -> bool:
    """
    Detect if subtitle text is non-speech (sound effects, metadata).

    Identifies:
    - Sound effects: [phone rings], [door slams]
    - Music: ♪ lyrics ♪
    - Metadata: == sync, corrected by ==
    - Technical artifacts: <font color="...">

    Args:
        text: Subtitle text to check

    Returns:
        True if subtitle is non-speech, False otherwise

    Examples:
        >>> is_non_speech_subtitle("[Cell phone rings]")
        True

        >>> is_non_speech_subtitle("Hello, world")
        False

        >>> is_non_speech_subtitle("== sync, corrected by elderman ==")
        True
    """
    if not text:
        return False

    # Check if text becomes empty after cleaning (e.g., only brackets/parens)
    if not clean_text_for_matching(text):
        return True

    # Check for common non-speech indicators
    indicators = [
        '[', ']',           # Sound effects: [phone rings]
        '♪',                # Music notation
        '==',               # Metadata markers
        '<font',            # HTML/formatting tags
    ]

    # Check case-insensitive keywords
    text_lower = text.lower()
    keywords = ['sync', 'corrected', 'subtitle', 'caption']

    for indicator in indicators:
        if indicator in text:
            return True

    for keyword in keywords:
        if keyword in text_lower:
            return True

    return False
