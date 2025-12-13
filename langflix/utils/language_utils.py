"""
Language utilities for LangFlix.

Maps language names (from Netflix subtitle filenames) to ISO 639-1 codes
for font selection and i18n.
"""

from typing import Optional

# Language name to ISO 639-1 code mapping
# Netflix uses full English names in subtitle filenames
LANGUAGE_NAME_TO_CODE = {
    # Common languages
    "English": "en",
    "Korean": "ko",
    "Spanish": "es",
    "Japanese": "ja",
    "Chinese": "zh",
    "French": "fr",
    "German": "de",
    "Portuguese": "pt",
    "Italian": "it",
    "Russian": "ru",
    "Arabic": "ar",
    "Hindi": "hi",
    "Thai": "th",
    "Vietnamese": "vi",
    "Indonesian": "id",
    "Malay": "ms",
    "Dutch": "nl",
    "Polish": "pl",
    "Turkish": "tr",
    "Swedish": "sv",
    "Norwegian": "no",
    "Danish": "da",
    "Finnish": "fi",
    "Greek": "el",
    "Hebrew": "he",
    "Czech": "cs",
    "Hungarian": "hu",
    "Romanian": "ro",
    "Ukrainian": "uk",
    
    # Variants
    "Simplified Chinese": "zh",
    "Traditional Chinese": "zh-TW",
    "Brazilian Portuguese": "pt-BR",
    "Latin American Spanish": "es-419",
    "Castilian Spanish": "es",
    "European Spanish": "es",
    "Mexican Spanish": "es-MX",
}

# Reverse mapping for code to name
CODE_TO_LANGUAGE_NAME = {v: k for k, v in LANGUAGE_NAME_TO_CODE.items()}


def language_name_to_code(name: str) -> str:
    """
    Convert language name to ISO 639-1 code.
    
    Args:
        name: Language name from Netflix subtitle filename (e.g., "Korean", "Spanish")
        
    Returns:
        ISO 639-1 code (e.g., "ko", "es") or "en" as default
    """
    if not name:
        return "en"
    
    # Try exact match first
    if name in LANGUAGE_NAME_TO_CODE:
        return LANGUAGE_NAME_TO_CODE[name]
    
    # Try case-insensitive match
    name_lower = name.lower()
    for lang_name, code in LANGUAGE_NAME_TO_CODE.items():
        if lang_name.lower() == name_lower:
            return code
    
    # Default to English
    return "en"


def language_code_to_name(code: str) -> str:
    """
    Convert ISO 639-1 code to language name.
    
    Args:
        code: ISO 639-1 code (e.g., "ko", "es")
        
    Returns:
        Language name (e.g., "Korean", "Spanish") or the code itself if not found
    """
    if not code:
        return "English"
    
    # Normalize code
    code_normalized = code.lower().split("-")[0]  # Handle "zh-TW" -> "zh"
    
    # Direct lookup
    for lang_name, lang_code in LANGUAGE_NAME_TO_CODE.items():
        if lang_code.lower().split("-")[0] == code_normalized:
            return lang_name
    
    return code  # Return code if no match


def get_font_language_code(language_name: str) -> str:
    """
    Get the language code suitable for font selection.
    
    Some languages share fonts, so we map to the font-relevant code.
    
    Args:
        language_name: Language name (e.g., "Korean", "Spanish")
        
    Returns:
        Language code for font lookup (e.g., "ko", "es")
    """
    code = language_name_to_code(language_name)
    
    # CJK languages use their specific fonts
    if code in ("zh", "zh-TW", "ja"):
        return code.split("-")[0]  # Normalize to base code
    
    # European languages with Latin script can fall back to default
    # But Spanish, Portuguese, French have accents -> use their specific fonts if configured
    if code in ("es", "pt", "fr", "de", "it", "pl", "cs", "hu", "ro"):
        return code
    
    return code
