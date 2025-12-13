"""
Media management endpoints for LangFlix API.

V2 endpoints for dual-language subtitle support.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException

from langflix.utils.path_utils import (
    discover_subtitle_languages,
    get_available_language_names,
    validate_dual_subtitle_availability,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/media/{media_path:path}/languages")
async def get_media_languages(media_path: str) -> Dict[str, Any]:
    """
    Get available subtitle languages for a media file.
    
    V2 endpoint for dual-language subtitle support.
    
    Args:
        media_path: Relative path to the media file (e.g., "assets/media/show.mp4")
        
    Returns:
        Dictionary with available languages and suggested defaults
    """
    try:
        # Validate media file exists
        media_file = Path(media_path)
        if not media_file.exists():
            raise HTTPException(status_code=404, detail=f"Media file not found: {media_path}")
        
        # Discover languages
        languages = discover_subtitle_languages(media_path)
        
        if not languages:
            return {
                "media_path": media_path,
                "available_languages": [],
                "language_variants": {},
                "suggested_source": None,
                "suggested_target": None,
                "message": "No subtitle folder found or no subtitles available",
            }
        
        # Get sorted language list
        available = sorted(languages.keys())
        
        # Suggest defaults
        suggested_source = "English" if "English" in available else (available[0] if available else None)
        suggested_target = "Korean" if "Korean" in available else (available[1] if len(available) > 1 else None)
        
        # Count variants per language
        variants = {lang: len(files) for lang, files in languages.items()}
        
        return {
            "media_path": media_path,
            "available_languages": available,
            "language_variants": variants,
            "total_languages": len(available),
            "suggested_source": suggested_source,
            "suggested_target": suggested_target,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error discovering languages for {media_path}: {e}")
        raise HTTPException(status_code=500, detail=f"Error discovering languages: {str(e)}")


@router.get("/media/{media_path:path}/validate-languages")
async def validate_language_pair(
    media_path: str,
    source_lang: str,
    target_lang: str,
) -> Dict[str, Any]:
    """
    Validate that a source/target language pair is available for a media file.
    
    Args:
        media_path: Path to the media file
        source_lang: Source language name (e.g., "English")
        target_lang: Target language name (e.g., "Korean")
        
    Returns:
        Validation result with is_valid and any error message
    """
    try:
        # Validate media file exists
        media_file = Path(media_path)
        if not media_file.exists():
            raise HTTPException(status_code=404, detail=f"Media file not found: {media_path}")
        
        is_valid, error = validate_dual_subtitle_availability(media_path, source_lang, target_lang)
        
        return {
            "media_path": media_path,
            "source_language": source_lang,
            "target_language": target_lang,
            "is_valid": is_valid,
            "error": error,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error validating languages for {media_path}: {e}")
        raise HTTPException(status_code=500, detail=f"Error validating languages: {str(e)}")
