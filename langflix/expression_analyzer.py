import os
import json
import logging
import time
from datetime import datetime, timedelta
from enum import Enum
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional
from . import settings
from .prompts import get_prompt_for_chunk
from .models import ExpressionAnalysisResponse, ExpressionAnalysis

import google.generativeai as genai

# Load environment variables
load_dotenv()

# Get logger (logging will be configured in main.py)
logger = logging.getLogger(__name__)

# Configure Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def _validate_and_filter_expressions(expressions: List[ExpressionAnalysis]) -> List[ExpressionAnalysis]:
    """
    Validate expressions and filter out those with validation issues.
    
    Args:
        expressions: List of ExpressionAnalysis objects from LLM response
        
    Returns:
        List of valid ExpressionAnalysis objects
    """
    validated_expressions = []
    
    for i, expr in enumerate(expressions):
        try:
            # Check dialogues and translation count mismatch
            dialogues_count = len(expr.dialogues) if expr.dialogues else 0
            translation_count = len(expr.translation) if expr.translation else 0
            
            if dialogues_count != translation_count:
                logger.error(f"Dropping expression {i+1}: '{expr.expression}' - "
                           f"Dialogue/translation count mismatch: {dialogues_count} dialogues vs {translation_count} translations")
                continue
            
            # Check required fields
            if not expr.expression or not expr.expression_translation:
                logger.error(f"Dropping expression {i+1}: '{expr.expression}' - Missing required expression or translation")
                continue
            
            # Check timestamps format (basic validation)
            import re
            timestamp_pattern = r'^\d{2}:\d{2}:\d{2}[.,]\d{3,6}$'
            
            if not re.match(timestamp_pattern, expr.context_start_time):
                logger.error(f"Dropping expression {i+1}: '{expr.expression}' - Invalid context_start_time format: {expr.context_start_time}")
                continue
                
            if not re.match(timestamp_pattern, expr.context_end_time):
                logger.error(f"Dropping expression {i+1}: '{expr.expression}' - Invalid context_end_time format: {expr.context_end_time}")
                continue
            
            # Check similar expressions is a list
            if not isinstance(expr.similar_expressions, list):
                logger.error(f"Dropping expression {i+1}: '{expr.expression}' - Similar expressions must be a list")
                continue
            
            # All validations passed
            validated_expressions.append(expr)
            logger.info(f"✅ Expression {i+1} validated: '{expr.expression}' ({dialogues_count} dialogues/translations)")
            
        except Exception as e:
            logger.error(f"Dropping expression {i+1} due to validation error: {e}")
            continue
    
    return validated_expressions

def analyze_chunk(subtitle_chunk: List[dict], language_level: str = None, language_code: str = "ko", save_output: bool = False, output_dir: str = None) -> List[ExpressionAnalysis]:
    """
    Analyzes a chunk of subtitles using Gemini API with structured output.
    
    Args:
        subtitle_chunk: List of subtitle dictionaries
        language_level: Target language level (beginner, intermediate, advanced, mixed)
        language_code: Target language code for translation
        save_output: Whether to save LLM output to file
        output_dir: Directory to save LLM output
        
    Returns:
        List of ExpressionAnalysis objects
    """
    try:
        # Generate prompt
        prompt = get_prompt_for_chunk(subtitle_chunk, language_level, language_code)
        
        logger.info("Sending prompt to Gemini API with structured output...")
        
        # Configure model
        model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        model = genai.GenerativeModel(model_name)
        
        # Generate content with retry logic
        response = _generate_content_with_retry(model, prompt, max_retries=3)
        
        if not response.text:
            logger.error("Empty response from Gemini API")
            return []
        
        # Save LLM output if requested
        if save_output and output_dir:
            _save_llm_output(response.text, subtitle_chunk, language_level, output_dir)
        
        # Parse JSON response
        try:
            # Parse response text with Pydantic validation
            parsed_response = _parse_response_text(response.text)
            logger.info(f"Successfully analyzed chunk, found {len(parsed_response.expressions)} expressions")
            
            # Validate and filter expressions
            validated_expressions = _validate_and_filter_expressions(parsed_response.expressions)
            logger.info(f"After validation: {len(validated_expressions)} valid expressions (dropped {len(parsed_response.expressions) - len(validated_expressions)} invalid)")
            
            return validated_expressions
            
        except Exception as parse_error:
            logger.error(f"Failed to parse response: {parse_error}")
            logger.error(f"Raw response: {response.text}")
            
            # If all parsing fails, return empty list
            logger.warning("All parsing methods failed, returning empty list")
            return []
        
    except Exception as e:
        logger.error(f"Unexpected error in analyze_chunk: {e}")
        return []


def _parse_response_text(response_text: str) -> ExpressionAnalysisResponse:
    """
    Parse response text using Pydantic validation.
    
    Args:
        response_text: Raw response text from Gemini API
        
    Returns:
        Validated ExpressionAnalysisResponse object
        
    Raises:
        ValueError: If response cannot be parsed or validated
    """
    try:
        # Clean response text
        cleaned_text = response_text.strip()
        
        # Remove markdown code blocks if present
        if cleaned_text.startswith("```json"):
            cleaned_text = cleaned_text[7:]  # Remove ```json
        if cleaned_text.startswith("```"):
            cleaned_text = cleaned_text[3:]   # Remove ```
        if cleaned_text.endswith("```"):
            cleaned_text = cleaned_text[:-3]  # Remove trailing ```
        
        cleaned_text = cleaned_text.strip()
        
        # Try to extract JSON from the response
        try:
            # Look for JSON array at the start
            if cleaned_text.startswith("["):
                bracket_count = 0
                json_end = 0
                for i, char in enumerate(cleaned_text):
                    if char == '[':
                        bracket_count += 1
                    elif char == ']':
                        bracket_count -= 1
                        if bracket_count == 0:
                            json_end = i + 1
                            break
                
                if json_end > 0:
                    json_text = cleaned_text[:json_end]
                    data = json.loads(json_text)
                else:
                    raise ValueError("Unmatched brackets in response")
            else:
                # Try parsing the whole response as JSON
                data = json.loads(cleaned_text)
                
        except json.JSONDecodeError as json_error:
            logger.warning(f"JSON parsing failed: {json_error}")
            # Try to extract JSON from within the text
            import re
            json_match = re.search(r'\[.*\]', cleaned_text, re.DOTALL)
            if json_match:
                json_text = json_match.group(0)
                data = json.loads(json_text)
            else:
                raise ValueError(f"Could not extract valid JSON from response: {json_error}")
        
        # Validate using Pydantic
        if isinstance(data, list):
            response_obj = ExpressionAnalysisResponse(expressions=data)
        else:
            # Handle single object case
            response_obj = ExpressionAnalysisResponse(expressions=[data])
        
        return response_obj
        
    except Exception as e:
        logger.error(f"Error parsing response text: {e}")
        raise ValueError(f"Failed to parse and validate response: {e}")


def _save_llm_output(response_text: str, subtitle_chunk: List[dict], language_level: str, output_dir: str):
    """Save LLM output to file for review"""
    try:
        from pathlib import Path
        import os
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"llm_output_{language_level}_{timestamp}.txt"
        filepath = output_path / filename
        
        # Prepare content
        content = f"""LLM Output Review
==================
Language Level: {language_level}
Timestamp: {datetime.now().isoformat()}
Chunk Size: {len(subtitle_chunk)} subtitles

Original Subtitle Chunk:
--------------------------------------------------
"""
        
        for i, sub in enumerate(subtitle_chunk[:10]):  # Show first 10 subtitles for context
            content += f"{i+1}. [{sub.get('start_time', 'N/A')}-{sub.get('end_time', 'N/A')}] {sub.get('text', 'N/A')}\n"
        
        if len(subtitle_chunk) > 10:
            content += f"... and {len(subtitle_chunk) - 10} more subtitles\n"
        
        content += f"""
LLM Response:
==========================================================
{response_text}
"""
        
        # Write to file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"LLM output saved to: {filepath}")
        
    except Exception as e:
        logger.error(f"Failed to save LLM output: {e}")


def _generate_content_with_retry(model, prompt: str, max_retries: int = 3) -> Any:
    """
    Generate content with exponential backoff retry logic for API failures.
    
    Args:
        model: Gemini GenerativeModel instance
        prompt: The prompt to send to the API
        max_retries: Maximum number of retry attempts
        
    Returns:
        API response object
        
    Raises:
        Exception: If all retry attempts fail
    """
    last_error = None
    
    for attempt in range(max_retries + 1):  # +1 for initial attempt
        try:
            if attempt > 0:
                wait_time = 2 ** attempt  # Exponential backoff: 2, 4, 8 seconds
                logger.info(f"Retrying API call (attempt {attempt + 1}/{max_retries + 1}) after {wait_time}s delay...")
                time.sleep(wait_time)
            
            response = model.generate_content(prompt)
            
            if response.text:
                logger.info(f"API call successful on attempt {attempt + 1}")
                return response
            else:
                logger.warning(f"Empty response on attempt {attempt + 1}")
                last_error = ValueError("Empty response from API")
                
        except Exception as e:
            last_error = e
            error_str = str(e)
            
            # Check for specific error types that warrant retries
            if any(keyword in error_str.lower() for keyword in ['timeout', '504', '503', '502', '500']):
                logger.warning(f"API error on attempt {attempt + 1}: {error_str}")
                if attempt == max_retries:
                    logger.error(f"Max retries reached. Final error: {error_str}")
                    break
            else:
                # Non-retryable error
                logger.error(f"Non-retryable API error: {error_str}")
                raise e
    
    # If we get here, all retries failed
    logger.error(f"All {max_retries + 1} API attempts failed. Last error: {last_error}")
    raise last_error
