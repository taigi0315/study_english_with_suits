import re
from typing import List
from pathlib import Path
from . import settings
from .language_config import LanguageConfig

def _load_prompt_template() -> str:
    """Load the prompt template from file"""
    template_filename = settings.get_template_file()
    template_path = Path(__file__).parent / "templates" / template_filename
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"Prompt template not found at {template_path}")
    except Exception as e:
        raise RuntimeError(f"Failed to load prompt template: {e}")

def get_prompt_for_chunk(subtitle_chunk: List[dict], language_level: str = None, language_code: str = "ko") -> str:
    """
    Generates the prompt for the LLM based on a chunk of subtitles.
    
    Args:
        subtitle_chunk: List of subtitle dictionaries
        language_level: Target language level (beginner, intermediate, advanced, mixed)
        language_code: Target language code (ko, ja, zh, es, fr)
    """
    # Use default language level if not specified
    if language_level is None:
        language_level = settings.DEFAULT_LANGUAGE_LEVEL
    
    # Get level description
    level_description = settings.LANGUAGE_LEVELS[language_level]["description"]
    
    # Get language-specific settings
    lang_config = LanguageConfig.get_config(language_code)
    target_language = lang_config['prompt_language']
    
    # Get expression limits from configuration
    min_expressions = settings.get_min_expressions_per_chunk()
    max_expressions = settings.get_max_expressions_per_chunk()
    
    # Get show name from configuration
    show_name = settings.get_show_name()
    
    # Clean HTML markup from subtitle text before including in prompt
    cleaned_dialogues = []
    for sub in subtitle_chunk:
        clean_text = re.sub(r'<[^>]+>', '', sub['text'])  # Remove HTML tags
        clean_text = re.sub(r'\s+', ' ', clean_text)      # Normalize whitespace
        clean_text = clean_text.strip()
        cleaned_dialogues.append(f"[{sub['start_time']}-{sub['end_time']}] {clean_text}")
    
    dialogues = "\\n".join(cleaned_dialogues)

    # Load prompt template from file
    template = _load_prompt_template()
    
    # Format the template with variables
    prompt = template.format(
        dialogues=dialogues,
        level_description=level_description,
        min_expressions=min_expressions,
        max_expressions=max_expressions,
        target_language=target_language,
        show_name=show_name
    )
    return prompt
