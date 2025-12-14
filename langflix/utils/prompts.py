import re
import logging
from typing import List
from pathlib import Path
from langflix import settings
from langflix.core.language_config import LanguageConfig

logger = logging.getLogger(__name__)

def _load_prompt_template() -> str:
    """Load the prompt template from file"""
    template_filename = settings.get_template_file()
    # Templates are in langflix/templates/, not utils/templates/
    template_path = Path(__file__).parent.parent / "templates" / template_filename
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"Prompt template not found at {template_path}")
    except Exception as e:
        raise RuntimeError(f"Failed to load prompt template: {e}")

def get_prompt_for_chunk(subtitle_chunk: List[dict], language_level: str = None, language_code: str = "ko", target_duration: float = 180.0) -> str:
    """
    Generates the prompt for the LLM based on a chunk of subtitles.
    
    Args:
        subtitle_chunk: List of subtitle dictionaries
        language_level: Target language level (beginner, intermediate, advanced, mixed)
        language_code: Target language code (ko, ja, zh, es, fr)
        target_duration: Target duration for the context video (default: 180.0s)
    """
    # Use default language level if not specified
    if language_level is None:
        language_level = settings.DEFAULT_LANGUAGE_LEVEL
    
    # Get level description
    level_description = settings.LANGUAGE_LEVELS[language_level]["description"]
    
    # Get language-specific settings
    lang_config = LanguageConfig.get_config(language_code)
    target_language = lang_config['prompt_language']
    
    # Get source language from settings (default to English for learning Korean from English shows)
    # In V2 dual-subtitle mode, source is the language being learned
    # In V1 single-subtitle mode, we infer from the target language
    source_language = settings.get_source_language_name()  # e.g., "Korean", "English"
    if not source_language:
        # Fallback: if target is Korean, source is probably English (or vice versa)
        source_language = "English" if language_code == "ko" else "Korean"
    
    # Get expression limits from configuration
    min_expressions = settings.get_min_expressions_per_chunk()
    max_expressions = settings.get_max_expressions_per_chunk()
    
    # Get show name from configuration
    show_name = settings.get_show_name()
    
    # Clean HTML markup from subtitle text before including in prompt
    cleaned_dialogues = []
    for i, sub in enumerate(subtitle_chunk):
        clean_text = re.sub(r'<[^>]+>', '', sub['text'])  # Remove HTML tags
        clean_text = re.sub(r'\s+', ' ', clean_text)      # Normalize whitespace
        clean_text = clean_text.strip()
        cleaned_dialogues.append(f"[{sub['start_time']}-{sub['end_time']}] {clean_text}")
    
    dialogues = "\\n".join(cleaned_dialogues)
    
    # For V8+ prompts that use indexed format
    indexed_dialogues = []
    for i, sub in enumerate(subtitle_chunk):
        clean_text = re.sub(r'<[^>]+>', '', sub['text'])
        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
        indexed_dialogues.append(f"[{i}] {clean_text}")
    
    source_dialogues = "\\n".join(indexed_dialogues)
    target_dialogues = source_dialogues  # In V1 mode, use same (translation will be done by LLM)

    # Load prompt template from file
    template = _load_prompt_template()
    
    # Format the template with variables - include all possible placeholders
    # This supports both V7 (uses dialogues) and V8 (uses source_dialogues, target_dialogues)
    try:
        prompt = template.format(
            dialogues=dialogues,
            source_dialogues=source_dialogues,
            target_dialogues=target_dialogues,
            level_description=level_description,
            min_expressions=min_expressions,
            max_expressions=max_expressions,
            target_language=target_language,
            source_language=source_language,
            show_name=show_name,
            target_duration=target_duration
        )
    except KeyError as e:
        logger.error(f"Missing placeholder in prompt template: {e}")
        raise
    
    return prompt
