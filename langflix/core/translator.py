"""
Translation service for multi-language video generation.
Translates ExpressionAnalysis objects to multiple target languages.
"""
import os
import json
import logging
from typing import List, Dict, Optional
from pathlib import Path
from dotenv import load_dotenv

import google.generativeai as genai
from langflix.core.models import ExpressionAnalysis
from langflix.core.error_handler import (
    handle_error_decorator,
    ErrorContext,
    handle_error
)
from langflix import settings

# Load environment variables
load_dotenv()

# Get logger
logger = logging.getLogger(__name__)

# Configure Gemini API
genai.configure(
    api_key=os.getenv("GEMINI_API_KEY"),
    client_options={
        "api_endpoint": "generativelanguage.googleapis.com",
    }
)


def _load_translation_prompt_template() -> str:
    """Load translation prompt template from file"""
    try:
        template_path = Path(__file__).parent.parent / "templates" / "translation_prompt.txt"
        if template_path.exists():
            with open(template_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            logger.warning(f"Translation prompt template not found at {template_path}, using default")
            return _get_default_translation_prompt()
    except Exception as e:
        logger.error(f"Error loading translation prompt template: {e}")
        return _get_default_translation_prompt()


def _get_default_translation_prompt() -> str:
    """Default translation prompt if template file is not found"""
    return """Translate the following English learning content to {target_language}.
Provide natural, contextual translations (의역) that capture the meaning and emotion, not literal word-by-word translations (직역).

Context:
- Expression: {expression}
- Full Dialogue: {expression_dialogue}
- Scene Context: {dialogues}
- Scene Type: {scene_type}
- Catchy Keywords: {catchy_keywords}
- Similar Expressions: {similar_expressions}

Translate:
1. All dialogue lines (maintain same count, preserve timing)
2. Expression translation (natural, contextual)
3. Expression dialogue translation (natural, contextual)
4. Catchy keywords (3-6 words each, natural in target language)
5. Similar expressions (natural alternatives in target language)

Output JSON format:
{{
  "dialogues_translation": [...],
  "expression_translation": "...",
  "expression_dialogue_translation": "...",
  "catchy_keywords": [...],
  "similar_expressions": [...]
}}
"""


def _create_translation_prompt(expression: ExpressionAnalysis, target_language: str) -> str:
    """
    Create translation prompt for an expression.
    
    Args:
        expression: ExpressionAnalysis object to translate
        target_language: Target language code (e.g., 'ja', 'zh')
        
    Returns:
        Formatted prompt string
    """
    template = _load_translation_prompt_template()
    
    # Get language name from code
    language_names = {
        'ko': 'Korean',
        'ja': 'Japanese',
        'zh': 'Chinese',
        'es': 'Spanish',
        'fr': 'French',
        'en': 'English'
    }
    target_language_name = language_names.get(target_language, target_language)
    
    # Format dialogue lines
    dialogue_lines = "\n".join([f"- {dialogue}" for dialogue in expression.dialogues])
    
    # Format catchy keywords
    catchy_keywords_str = "\n".join([f"- {kw}" for kw in (expression.catchy_keywords or [])])
    if not catchy_keywords_str:
        catchy_keywords_str = "None"
    
    # Format similar expressions
    similar_expressions_str = "\n".join([f"- {expr}" for expr in (expression.similar_expressions or [])])
    if not similar_expressions_str:
        similar_expressions_str = "None"
    
    # Format the prompt
    prompt = template.format(
        target_language=target_language_name,
        expression=expression.expression,
        expression_dialogue=expression.expression_dialogue,
        dialogues=dialogue_lines,
        scene_type=expression.scene_type or "general",
        catchy_keywords=catchy_keywords_str,
        similar_expressions=similar_expressions_str,
        dialogue_lines=dialogue_lines
    )
    
    return prompt


def _parse_translation_response(response_text: str) -> Dict[str, any]:
    """
    Parse translation response from LLM.
    
    Args:
        response_text: Raw response text from LLM
        
    Returns:
        Dictionary with translated content
    """
    try:
        # Try to extract JSON from response
        # Remove markdown code blocks if present
        cleaned_text = response_text.strip()
        if cleaned_text.startswith("```json"):
            cleaned_text = cleaned_text[7:]
        elif cleaned_text.startswith("```"):
            cleaned_text = cleaned_text[3:]
        if cleaned_text.endswith("```"):
            cleaned_text = cleaned_text[:-3]
        cleaned_text = cleaned_text.strip()
        
        # Parse JSON
        data = json.loads(cleaned_text)
        
        # Validate required fields
        required_fields = ['dialogues_translation', 'expression_translation', 
                          'expression_dialogue_translation', 'catchy_keywords', 'similar_expressions']
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field in translation response: {field}")
        
        return data
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse translation response as JSON: {e}")
        logger.error(f"Response text: {response_text[:500]}...")
        raise ValueError(f"Invalid JSON in translation response: {e}")
    except Exception as e:
        logger.error(f"Error parsing translation response: {e}")
        raise


@handle_error_decorator(
    ErrorContext(
        operation="translate_expression",
        component="translator"
    ),
    retry=False,
    fallback=False
)
def translate_expression_to_language(
    expression: ExpressionAnalysis,
    target_language: str
) -> ExpressionAnalysis:
    """
    Translate a single ExpressionAnalysis object to target language.
    
    Reuses (copies from original):
    - expression (English text)
    - context_start_time, context_end_time
    - expression_start_time, expression_end_time
    - scene_type, difficulty, category
    - educational_value, usage_notes
    
    Translates (new values):
    - dialogues → translated dialogues
    - translation → translated dialogue translations
    - expression_translation → translated expression
    - expression_dialogue_translation → translated expression dialogue
    - catchy_keywords → translated keywords
    - similar_expressions → translated similar expressions
    
    Args:
        expression: Original ExpressionAnalysis object
        target_language: Target language code (e.g., 'ja', 'zh')
        
    Returns:
        New ExpressionAnalysis object with translated content
    """
    try:
        logger.info(f"Translating expression '{expression.expression}' to {target_language}")
        
        # Create translation prompt
        prompt = _create_translation_prompt(expression, target_language)
        
        # Configure model
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        generation_config = settings.get_generation_config()
        
        model = genai.GenerativeModel(model_name=model_name)
        
        # Generate translation
        logger.info(f"Sending translation request to Gemini API for {target_language}...")
        
        if generation_config:
            config_obj = genai.types.GenerationConfig(**generation_config)
            response = model.generate_content(prompt, generation_config=config_obj)
        else:
            response = model.generate_content(prompt)
        
        # Extract response text
        response_text = ""
        if hasattr(response, 'text') and response.text:
            response_text = response.text
        elif hasattr(response, 'candidates') and response.candidates:
            if response.candidates[0].content.parts:
                response_text = response.candidates[0].content.parts[0].text
        
        if not response_text:
            raise ValueError("Empty response from translation API")
        
        # Parse translation response
        translation_data = _parse_translation_response(response_text)
        
        # Create new ExpressionAnalysis with translated content
        # Reuse language-agnostic fields, translate text fields
        translated_expression = ExpressionAnalysis(
            # Reused fields (language-agnostic)
            expression=expression.expression,  # Keep English
            context_start_time=expression.context_start_time,
            context_end_time=expression.context_end_time,
            expression_start_time=expression.expression_start_time,
            expression_end_time=expression.expression_end_time,
            scene_type=expression.scene_type,
            difficulty=expression.difficulty,
            category=expression.category,
            educational_value=expression.educational_value,
            usage_notes=expression.usage_notes,
            educational_value_score=expression.educational_value_score,
            frequency=expression.frequency,
            context_relevance=expression.context_relevance,
            ranking_score=expression.ranking_score,
            
            # Translated fields
            dialogues=expression.dialogues,  # Keep original English dialogues
            translation=translation_data['dialogues_translation'],  # Translated dialogues
            expression_translation=translation_data['expression_translation'],
            expression_dialogue=expression.expression_dialogue,  # Keep original English
            expression_dialogue_translation=translation_data['expression_dialogue_translation'],
            catchy_keywords=translation_data['catchy_keywords'],
            similar_expressions=translation_data['similar_expressions']
        )
        
        logger.info(f"Successfully translated expression to {target_language}")
        return translated_expression
        
    except Exception as e:
        logger.error(f"Error translating expression to {target_language}: {e}")
        raise


def translate_expression_to_languages(
    expression: ExpressionAnalysis,
    target_languages: List[str]
) -> Dict[str, ExpressionAnalysis]:
    """
    Translate an ExpressionAnalysis object to multiple target languages.
    
    Args:
        expression: Original ExpressionAnalysis object
        target_languages: List of target language codes (e.g., ['ja', 'zh'])
        
    Returns:
        Dictionary mapping language_code to translated ExpressionAnalysis objects
    """
    translated_expressions = {}
    
    for lang in target_languages:
        try:
            translated = translate_expression_to_language(expression, lang)
            translated_expressions[lang] = translated
        except Exception as e:
            logger.error(f"Failed to translate expression to {lang}: {e}")
            # Continue with other languages even if one fails
            continue
    
    return translated_expressions

