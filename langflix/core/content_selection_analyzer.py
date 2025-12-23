"""
Content Selection Analyzer for LangFlix.

Analyzes dual-language subtitles to select engaging educational content.
Translations are sourced from Netflix subtitles.
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
    ContentSelection,
    ContentSelectionResponse,
    enrich_from_subtitles,
    convert_to_legacy_format,
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
    """Load the prompt template from prompts folder (supports YAML and TXT formats)."""
    import yaml
    template_name = settings.get_template_file()
    prompts_dir = Path(__file__).parent.parent / "prompts"
    
    # Try YAML first (preferred), then TXT
    yaml_path = prompts_dir / template_name.replace('.txt', '.yaml')
    txt_path = prompts_dir / template_name
    
    if yaml_path.exists():
        with open(yaml_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            if isinstance(data, dict) and 'prompt' in data:
                return data['prompt']
            else:
                raise ValueError(f"YAML file must contain a 'prompt' key: {yaml_path}")
    elif txt_path.exists():
        return txt_path.read_text(encoding='utf-8')
    else:
        raise FileNotFoundError(f"Prompt template not found at {yaml_path} or {txt_path}")


def _format_dialogues_for_prompt(dialogues: List[dict], include_timestamps: bool = False) -> str:
    """
    Format dialogue list for the prompt.
    
    Optimization: By default, excludes timestamps to reduce token usage.
    The LLM returns indices, and timestamps are looked up post-processing.
    
    Args:
        dialogues: List of dialogue dicts with 'text', 'start', 'end'
        include_timestamps: If True, include timestamps (higher token usage). Default False.
        
    Returns:
        Formatted string for prompt
    """
    lines = []
    for i, d in enumerate(dialogues):
        text = d.get('text', '')
        if include_timestamps:
            # Include timestamps (higher token usage)
            lines.append(f"[{i}] ({d.get('start', '')} - {d.get('end', '')}): {text}")
        else:
            # Optimized mode: index + text only (optimized token usage)
            lines.append(f"[{i}] {text}")
    return "\n".join(lines)


def analyze_with_dual_subtitles(
    dual_subtitle: DualSubtitle,
    show_name: str = "Unknown Show",
    language_level: str = "intermediate",
    min_expressions: int = 1,
    max_expressions: int = 3,
    target_duration: float = 45.0,
    test_llm: bool = False,  # Dev: Use cached LLM response
    output_dir: Optional[str] = None,  # Directory to save LLM response
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
        test_llm: If True, use cached LLM response (for fast development iteration)

    Returns:
        List of expression dicts
    """
    # TEST_LLM MODE: Load from dev test cache if available
    if test_llm:
        from .llm_test_cache import load_llm_test_response, save_llm_test_response
        
        cache_id = show_name or "default"
        cached_data = load_llm_test_response("content_selection", cache_id)
        
        if cached_data:
            logger.info(f"🚀 TEST_LLM: Using cached LLM response (skipping API call)")
            # Return cached expressions, BUT respect max_expressions limit!
            result = cached_data[:max_expressions] if isinstance(cached_data, list) else cached_data
            logger.info(f"🚀 TEST_LLM: Returning {len(result)} expressions (max_expressions={max_expressions})")
            return result
        else:
            logger.info(f"🔄 TEST_LLM: No cache found, will call API and save response")
    
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
        
        logger.info(f"Calling Gemini API for content selection ({len(source_dialogues)} dialogues)")
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
            # Save in episode directory if provided, otherwise fallback to output/
            debug_dir = Path(output_dir) if output_dir else Path("output")
            debug_dir.mkdir(parents=True, exist_ok=True)
            debug_file = debug_dir / f"llm_response_{timestamp}_{min_expressions}-{max_expressions}.json"
            debug_file.write_text(response_text, encoding='utf-8')
            logger.info(f"Saved raw LLM response to {debug_file}")
        except Exception as e:
            logger.warning(f"Failed to save debug LLM response: {e}")

        # Log first 500 chars of response for debugging
        logger.debug(f"LLM response preview: {response_text[:500]}")

        # Parse JSON response
        try:
            selections = _parse_response(response_text)
        except Exception as parse_error:
            logger.error(f"Failed to parse LLM response: {parse_error}", exc_info=True)
            logger.error(f"Raw response text: {response_text}")
            raise
        
        # Enrich and convert to legacy format for compatibility
        results = []
        for selection in selections:
            # Enrich with subtitle data
            enriched = enrich_from_subtitles(selection, source_dialogues, target_dialogues)

            # Convert to legacy format for compatibility
            legacy_format = convert_to_legacy_format(enriched, source_dialogues, target_dialogues)
            results.append(legacy_format)
        
        # Save to test cache if test_llm mode is enabled
        if test_llm:
            from .llm_test_cache import save_llm_test_response
            cache_id = show_name or "default"
            save_llm_test_response("content_selection", results, cache_id, {
                "language_level": language_level,
                "expression_count": len(results)
            })
            logger.info(f"💾 TEST_LLM: Saved {len(results)} expressions to cache")
        
        # CRITICAL: Enforce max_expressions limit (for test_mode=1)
        if max_expressions and len(results) > max_expressions:
            logger.info(f"Limiting expressions from {len(results)} to {max_expressions} (test_mode active)")
            results = results[:max_expressions]
        
        logger.info(f"content selection found {len(results)} expressions")
        return results
        
    except Exception as e:
        logger.error(f"Error in content selection: {e}", exc_info=True)
        raise


def _parse_response(response_text: str) -> List[ContentSelection]:
    """Parse LLM response into ContentSelection objects."""
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
                selection = ContentSelection(**expr_data)
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


class ContentAnalyzer:
    """
    Service class for content selection analysis.
    
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

        Returns list of expression dicts.
        """
        return analyze_with_dual_subtitles(
            dual_subtitle=dual_subtitle,
            show_name=self.show_name,
            language_level=language_level,
            min_expressions=min_expressions,
            max_expressions=max_expressions,
            target_duration=target_duration,
        )
