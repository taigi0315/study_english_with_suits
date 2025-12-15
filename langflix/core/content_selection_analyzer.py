"""
V2 Content Selection Analyzer for LangFlix.

Analyzes dual-language subtitles to select engaging educational content.
Unlike V1, this does NOT handle translation - translations come from Netflix subtitles.
"""
import os
import json
import logging
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv

import google.generativeai as genai

from langflix.core.dual_subtitle import DualSubtitle
from langflix.core.content_selection_models import (
    V2ContentSelection,
    V2ContentSelectionResponse,
    enrich_content_selection,
    convert_v2_to_v1_format,
)
from langflix import settings

logger = logging.getLogger(__name__)

# Load API key
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(
        api_key=api_key,
        client_options={"api_endpoint": "generativelanguage.googleapis.com"}
    )


def _load_prompt_template() -> str:
    """Load the prompt template from settings."""
    template_name = settings.get_template_file()
    template_path = Path(__file__).parent.parent / "templates" / template_name
    
    if not template_path.exists():
        raise FileNotFoundError(f"Prompt template not found: {template_path}")
    
    return template_path.read_text(encoding='utf-8')


def _format_dialogues_for_prompt(dialogues: List[dict], include_timestamps: bool = False) -> str:
    """
    Format dialogue list for the prompt.
    
    V2 Optimization: By default, excludes timestamps to reduce token usage.
    The LLM returns indices, and timestamps are looked up post-processing.
    
    Args:
        dialogues: List of dialogue dicts with 'text', 'start', 'end'
        include_timestamps: If True, include timestamps (V1 mode). Default False.
        
    Returns:
        Formatted string for prompt
    """
    lines = []
    for i, d in enumerate(dialogues):
        text = d.get('text', '')
        if include_timestamps:
            # V1 mode: include timestamps (higher token usage)
            lines.append(f"[{i}] ({d.get('start', '')} - {d.get('end', '')}): {text}")
        else:
            # V2 mode: index + text only (optimized token usage)
            lines.append(f"[{i}] {text}")
    return "\n".join(lines)


def analyze_with_dual_subtitles(
    dual_subtitle: DualSubtitle,
    show_name: str = "Unknown Show",
    language_level: str = "intermediate",
    min_expressions: int = 1,
    max_expressions: int = 3,
    target_duration: float = 45.0,
) -> List[dict]:
    """
    Analyze dual subtitles to select engaging content.
    
    Args:
        dual_subtitle: DualSubtitle with source and target languages loaded
        show_name: Name of the TV show
        language_level: Difficulty level (beginner, intermediate, advanced)
        min_expressions: Minimum expressions to find
        max_expressions: Maximum expressions to find
        target_duration: Target duration for context clips in seconds
        
    Returns:
        List of expression dicts in V1-compatible format
    """
    # Get dialogues in prompt format
    source_dialogues, target_dialogues = dual_subtitle.to_dialogue_format()
    
    if not source_dialogues or not target_dialogues:
        logger.warning("No dialogues available for analysis")
        return []
    
    # Load and format prompt
    template = _load_prompt_template()
    
    # Get level description
    level_descriptions = {
        'beginner': "A1-A2 level. Focus on basic everyday expressions.",
        'intermediate': "B1-B2 level. Focus on common idiomatic expressions and phrasal verbs.",
        'advanced': "C1-C2 level. Focus on sophisticated idioms and nuanced expressions.",
    }
    level_desc = level_descriptions.get(language_level, level_descriptions['intermediate'])
    
    prompt = template.format(
        show_name=show_name,
        source_language=dual_subtitle.source_language,
        target_language=dual_subtitle.target_language,
        source_dialogues=_format_dialogues_for_prompt(source_dialogues),
        target_dialogues=_format_dialogues_for_prompt(target_dialogues),
        level_description=level_desc,
        min_expressions=min_expressions,
        max_expressions=max_expressions,
        target_duration=target_duration,
    )
    
    # Call Gemini API
    try:
        model_name = settings.get_llm_model_name() or "gemini-2.5-flash"
        model = genai.GenerativeModel(model_name)
        
        generation_config = settings.get_generation_config()
        
        logger.info(f"Calling Gemini API for V2 content selection ({len(source_dialogues)} dialogues)")
        response = model.generate_content(prompt, generation_config=generation_config)
        
        # Extract response text
        response_text = ""
        if hasattr(response, 'text'):
            response_text = response.text
        elif hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                response_text = " ".join(p.text for p in candidate.content.parts if hasattr(p, 'text'))
        
        if not response_text:
            logger.warning("Empty response from Gemini API")
            return []

        # DEBUG: Save LLM response to file (TICKET-029)
        try:
            import time
            timestamp = int(time.time())
            debug_dir = Path("output")
            debug_dir.mkdir(exist_ok=True)
            debug_file = debug_dir / f"llm_response_v2_{timestamp}_{min_expressions}-{max_expressions}.json"
            debug_file.write_text(response_text, encoding='utf-8')
            logger.info(f"Saved raw V2 LLM response to {debug_file}")
        except Exception as e:
            logger.warning(f"Failed to save debug V2 LLM response: {e}")

        # Log first 500 chars of response for debugging
        logger.debug(f"LLM response preview: {response_text[:500]}")

        # Parse JSON response
        try:
            selections = _parse_response(response_text)
        except Exception as parse_error:
            logger.error(f"Failed to parse LLM response: {parse_error}", exc_info=True)
            logger.error(f"Raw response text: {response_text}")
            raise
        
        # Enrich and convert to V1 format
        results = []
        for selection in selections:
            # Enrich with subtitle data
            enriched = enrich_content_selection(selection, source_dialogues, target_dialogues)
            
            # Convert to V1-compatible dict
            v1_format = convert_v2_to_v1_format(enriched, source_dialogues, target_dialogues)
            results.append(v1_format)
        
        logger.info(f"V2 content selection found {len(results)} expressions")
        return results
        
    except Exception as e:
        logger.error(f"Error in V2 content selection: {e}", exc_info=True)
        raise


def _parse_response(response_text: str) -> List[V2ContentSelection]:
    """Parse LLM response into V2ContentSelection objects."""
    # Clean up response text
    text = response_text.strip()

    # Remove markdown code blocks if present
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])

    logger.debug(f"Parsing JSON (length: {len(text)} chars)")

    try:
        data = json.loads(text)
        logger.debug(f"JSON parsed successfully, type: {type(data)}")
        
        # Handle both direct list and wrapped format
        expressions_data = data.get('expressions', data) if isinstance(data, dict) else data
        
        if not isinstance(expressions_data, list):
            expressions_data = [expressions_data]
        
        selections = []
        for expr_data in expressions_data:
            try:
                selection = V2ContentSelection(**expr_data)
                selections.append(selection)
            except Exception as e:
                logger.error(f"Failed to parse expression: {e}")
                logger.error(f"Expression data: {json.dumps(expr_data, ensure_ascii=False, indent=2)}")
                continue
        
        return selections
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response: {e}")
        logger.debug(f"Response text: {text[:500]}")
        return []


class V2ContentAnalyzer:
    """
    Service class for V2 content selection analysis.
    
    Provides a higher-level interface for analyzing media with dual subtitles.
    """
    
    def __init__(self, show_name: str = "Unknown Show"):
        self.show_name = show_name
    
    def analyze(
        self,
        dual_subtitle: DualSubtitle,
        language_level: str = "intermediate",
        min_expressions: int = 1,
        max_expressions: int = 3,
        target_duration: float = 45.0,
    ) -> List[dict]:
        """
        Analyze dual subtitles for content selection.
        
        Returns list of V1-compatible expression dicts.
        """
        return analyze_with_dual_subtitles(
            dual_subtitle=dual_subtitle,
            show_name=self.show_name,
            language_level=language_level,
            min_expressions=min_expressions,
            max_expressions=max_expressions,
            target_duration=target_duration,
        )
