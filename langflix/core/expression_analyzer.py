import os
import json
import logging
import time
from datetime import datetime, timedelta
from enum import Enum
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional
from langflix import settings
from langflix.utils.prompts import get_prompt_for_chunk
from .models import ExpressionAnalysisResponse, ExpressionAnalysis

import google.generativeai as genai

# Load environment variables
load_dotenv()

# Get logger (logging will be configured in main.py)
logger = logging.getLogger(__name__)

# Configure Gemini API - no timeout restrictions to let it take as long as needed
genai.configure(
    api_key=os.getenv("GEMINI_API_KEY"),
    client_options={
        "api_endpoint": "generativelanguage.googleapis.com",
    }
)

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
        logger.info(f"Prompt length: {len(prompt)} characters")
        
        # Save full prompt for debugging/testing
        _save_prompt_for_debugging(prompt, subtitle_chunk, language_level, output_dir)
        
        # Check if total prompt is too long and warn
        if len(prompt) > 15000:  # Warn if total prompt exceeds reasonable size
            logger.warning(f"Total prompt length ({len(prompt)}) is very large. Consider reducing chunk size.")
        
        # Configure model with settings from YAML config
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        generation_config = settings.get_generation_config()
        
        model = genai.GenerativeModel(model_name=model_name)
        
        # Generate content with structured output using Pydantic model
        max_retries = settings.get_max_retries()
        logger.info(f"Using generation config: {generation_config}")
        
        try:
            # Use structured output with Pydantic model
            response = model.generate_content(
                prompt,
                response_schema=ExpressionAnalysisResponse,
                generation_config=genai.types.GenerationConfig(**generation_config) if generation_config else None
            )
            
            # Extract structured response
            if hasattr(response, 'text') and response.text:
                # Parse the structured response
                response_obj = ExpressionAnalysisResponse.model_validate_json(response.text)
                expressions = response_obj.expressions
                
                # Validate and filter expressions
                validated_expressions = _validate_and_filter_expressions(expressions)
                
                logger.info(f"Successfully parsed {len(validated_expressions)} expressions from {len(expressions)} total")
                return validated_expressions
            else:
                logger.error("Empty or invalid structured response from Gemini API")
                return []
                
        except Exception as e:
            logger.error(f"Structured output failed: {e}")
            logger.warning("Falling back to text parsing...")
            
            # Fallback to text parsing if structured output fails
            response = _generate_content_with_retry(model, prompt, max_retries=max_retries, generation_config=generation_config)
            response_text = _extract_response_text(response)
            
            if not response_text:
                logger.error("Empty response from Gemini API")
                return []
            
            # Save LLM output if requested
            if save_output and output_dir:
                _save_llm_output(response_text, subtitle_chunk, language_level, output_dir)
            
            # Parse response using Pydantic validation
            try:
                response_obj = _parse_response_text(response_text)
                expressions = response_obj.expressions
                
                # Validate and filter expressions
                validated_expressions = _validate_and_filter_expressions(expressions)
                
                logger.info(f"Successfully parsed {len(validated_expressions)} expressions from {len(expressions)} total")
                return validated_expressions
                
            except Exception as parse_error:
                logger.error(f"Failed to parse response: {parse_error}")
                logger.error(f"Raw response: {response_text}")
                
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
            # First try parsing the whole response as JSON
            data = json.loads(cleaned_text)
        except json.JSONDecodeError as json_error:
            logger.warning(f"JSON parsing failed: {json_error}")
            # Try to extract JSON from within the text
            import re
            json_match = re.search(r'\{.*\}', cleaned_text, re.DOTALL)
            if json_match:
                json_text = json_match.group(0)
                data = json.loads(json_text)
            else:
                raise ValueError(f"Could not extract valid JSON from response: {json_error}")
        
        # Validate using Pydantic
        if isinstance(data, dict) and "expressions" in data:
            response_obj = ExpressionAnalysisResponse(expressions=data["expressions"])
        elif isinstance(data, list):
            response_obj = ExpressionAnalysisResponse(expressions=data)
        else:
            raise ValueError(f"Invalid JSON structure: {data}")
        
        return response_obj
        
    except Exception as e:
        logger.error(f"Error parsing response text: {e}")
        raise ValueError(f"Failed to parse and validate response: {e}")


def _save_prompt_for_debugging(prompt: str, subtitle_chunk: List[dict], language_level: str, output_dir: str):
    """Save the full prompt to file for debugging and manual testing"""
    try:
        from pathlib import Path
        import os
        
        if not output_dir:
            return
            
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"full_prompt_debug_{language_level}_{timestamp}.txt"
        filepath = output_path / filename
        
        # Save the complete prompt
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("=== FULL PROMPT SENT TO GEMINI API ===\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"Language Level: {language_level}\n")
            f.write(f"Chunk Size: {len(subtitle_chunk)} subtitles\n")
            f.write(f"Prompt Length: {len(prompt)} characters\n")
            f.write("=" * 50 + "\n\n")
            f.write(prompt)
        
        logger.info(f"Full prompt saved for debugging: {filepath}")
        
    except Exception as e:
        logger.warning(f"Failed to save prompt for debugging: {e}")


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


def _extract_response_text(response) -> str:
    """
    Extract text from Gemini API response, handling different response formats.
    
    Args:
        response: Gemini API response object
        
    Returns:
        Extracted text string or empty string if no text found
    """
    try:
        # Try the simple text accessor first
        result = response.text
        if result:
            logger.info(f"Successfully extracted text via response.text, length: {len(result)}")
            return result
        else:
            logger.warning("response.text returned empty string")
    except Exception as e:
        logger.warning(f"Failed to extract text via response.text: {e}")
        
    try:
        # Fall back to accessing parts directly
        if hasattr(response, 'candidates') and response.candidates:
            logger.info(f"Trying to extract via candidates, count: {len(response.candidates)}")
            candidate = response.candidates[0]
            
            # Check finish_reason first
            finish_reason = getattr(candidate, 'finish_reason', None)
            logger.info(f"Candidate finish_reason: {finish_reason}")
            
            # Handle different finish reasons
            if finish_reason == 2 or str(finish_reason) == 'MAX_TOKENS':
                logger.error("Response truncated due to max_output_tokens limit")
                return ""
            elif finish_reason == 3 or str(finish_reason) == 'SAFETY':
                logger.warning("Response blocked due to safety concerns")
                return ""
            elif finish_reason == 4 or str(finish_reason) == 'RECITATION':
                logger.warning("Response blocked due to recitation concerns")
                return ""
                
            if hasattr(candidate, 'content') and candidate.content:
                if hasattr(candidate.content, 'parts') and candidate.content.parts:
                    logger.info(f"Found {len(candidate.content.parts)} parts in content")
                    text_parts = []
                    for i, part in enumerate(candidate.content.parts):
                        if hasattr(part, 'text') and part.text:
                            text_parts.append(part.text)
                            logger.info(f"Part {i} has text, length: {len(part.text)}")
                        else:
                            logger.warning(f"Part {i} has no text: {part}")
                    result = "".join(text_parts)
                    logger.info(f"Extracted text via parts, total length: {len(result)}")
                    return result
                else:
                    logger.warning("Content has no parts")
            else:
                logger.warning("Candidate has no content")
        else:
            logger.warning("Response has no candidates")
    except Exception as e:
        logger.warning(f"Could not extract text from response via parts: {e}")
    
    return ""


def _generate_content_with_retry(model, prompt: str, max_retries: int = 3, generation_config: dict = None) -> Any:
    """
    Generate content with exponential backoff retry logic for API failures.
    
    Args:
        model: Gemini GenerativeModel instance
        prompt: The prompt to send to the API
        max_retries: Maximum number of retry attempts
        generation_config: Generation configuration to use
        
    Returns:
        API response object
        
    Raises:
        Exception: If all retry attempts fail
    """
    last_error = None
    
    for attempt in range(max_retries + 1):  # +1 for initial attempt
        try:
            if attempt > 0:
                # Use configured backoff times from YAML config
                backoff_times = settings.get_retry_backoff_seconds()
                wait_time = backoff_times[min(attempt - 1, len(backoff_times) - 1)]
                logger.info(f"Retrying API call (attempt {attempt + 1}/{max_retries + 1}) after {wait_time}s delay...")
                time.sleep(wait_time)
            
            # Time the API call to understand response times
            start_time = time.time()
            logger.info(f"Making API call (attempt {attempt + 1}/{max_retries + 1})...")
            
            # Use model's pre-configured generation config or pass explicit config
            if generation_config:
                # Create GenerationConfig object
                config_obj = genai.types.GenerationConfig(**generation_config)
                response = model.generate_content(prompt, generation_config=config_obj)
            else:
                response = model.generate_content(prompt)
            
            call_duration = time.time() - start_time
            logger.info(f"API call completed in {call_duration:.1f}s")
            
            # Check if response has content
            response_text = _extract_response_text(response)
            
            # Debug: Log response structure to understand what we're getting
            logger.info(f"Response object type: {type(response)}")
            logger.info(f"Response has candidates: {hasattr(response, 'candidates') and response.candidates}")
            if hasattr(response, 'candidates') and response.candidates:
                logger.info(f"Number of candidates: {len(response.candidates)}")
                candidate = response.candidates[0]
                logger.info(f"Candidate finish_reason: {getattr(candidate, 'finish_reason', 'Unknown')}")
                if hasattr(candidate, 'content') and candidate.content:
                    logger.info(f"Content has parts: {hasattr(candidate.content, 'parts') and candidate.content.parts}")
                    if hasattr(candidate.content, 'parts') and candidate.content.parts:
                        logger.info(f"Number of parts: {len(candidate.content.parts)}")
                        
            logger.info(f"Extracted response text length: {len(response_text) if response_text else 0}")
            
            if response_text:
                logger.info(f"API call successful on attempt {attempt + 1}")
                return response
            else:
                logger.warning(f"Empty response on attempt {attempt + 1}")
                # Log raw response for debugging
                logger.warning(f"Raw response object: {response}")
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


def _remove_duplicates(expressions: List[ExpressionAnalysis]) -> List[ExpressionAnalysis]:
    """
    Remove duplicate expressions using fuzzy string matching.
    
    Args:
        expressions: List of ExpressionAnalysis objects
        
    Returns:
        List of unique expressions
    """
    try:
        from rapidfuzz import fuzz
    except ImportError:
        logger.warning("rapidfuzz not installed, skipping duplicate removal")
        return expressions
    
    # Get fuzzy match threshold from settings (default: 85)
    llm_config = settings.get_llm_config()
    ranking_config = llm_config.get('ranking', {})
    threshold = ranking_config.get('fuzzy_match_threshold', 85)
    
    unique = []
    for expr in expressions:
        is_duplicate = False
        for existing in unique:
            # Compare expressions using fuzzy matching
            similarity = fuzz.ratio(expr.expression.lower(), existing.expression.lower())
            if similarity > threshold:
                logger.info(f"Removing duplicate: '{expr.expression}' (similar to '{existing.expression}', similarity: {similarity}%)")
                is_duplicate = True
                break
        
        if not is_duplicate:
            unique.append(expr)
    
    logger.info(f"Removed {len(expressions) - len(unique)} duplicate expressions")
    return unique


def calculate_expression_score(
    expression: ExpressionAnalysis,
    difficulty_weight: float = 0.4,
    frequency_weight: float = 0.3,
    educational_value_weight: float = 0.3
) -> float:
    """
    Calculate ranking score for an expression.
    
    Score formula: difficulty × w1 + frequency × w2 + educational_value × w3
    
    Args:
        expression: ExpressionAnalysis object
        difficulty_weight: Weight for difficulty (default: 0.4)
        frequency_weight: Weight for frequency (default: 0.3)
        educational_value_weight: Weight for educational value (default: 0.3)
        
    Returns:
        Calculated score (0-10)
    """
    # Normalize difficulty (1-10 to 0-10)
    normalized_difficulty = (expression.difficulty - 1) / 9.0 * 10.0 if expression.difficulty else 5.0
    
    # Normalize frequency (log scale for better distribution)
    import math
    normalized_frequency = min(10.0, math.log(expression.frequency + 1) * 2.0)
    
    # Educational value score is already 0-10
    educational_score = expression.educational_value_score
    
    # Calculate weighted score
    score = (
        normalized_difficulty * difficulty_weight +
        normalized_frequency * frequency_weight +
        educational_score * educational_value_weight
    )
    
    return round(score, 2)


def rank_expressions(
    expressions: List[ExpressionAnalysis],
    max_count: int = 5,
    remove_duplicates: bool = True
) -> List[ExpressionAnalysis]:
    """
    Rank and filter expressions by educational value.
    
    Process:
    1. Remove duplicates using fuzzy matching (if enabled)
    2. Calculate ranking scores for each expression
    3. Sort by score (highest first)
    4. Return top N expressions
    
    Args:
        expressions: List of ExpressionAnalysis objects
        max_count: Maximum number of expressions to return
        remove_duplicates: Whether to remove duplicate expressions (default: True)
        
    Returns:
        List of ranked expressions (top N)
    """
    if not expressions:
        return []
    
    logger.info(f"Ranking {len(expressions)} expressions...")
    
    # Step 1: Remove duplicates
    if remove_duplicates:
        expressions = _remove_duplicates(expressions)
    
    # Step 2: Calculate scores
    llm_config = settings.get_llm_config()
    ranking_config = llm_config.get('ranking', {})
    
    difficulty_weight = ranking_config.get('difficulty_weight', 0.4)
    frequency_weight = ranking_config.get('frequency_weight', 0.3)
    educational_value_weight = ranking_config.get('educational_value_weight', 0.3)
    
    for expr in expressions:
        expr.ranking_score = calculate_expression_score(
            expr,
            difficulty_weight=difficulty_weight,
            frequency_weight=frequency_weight,
            educational_value_weight=educational_value_weight
        )
        logger.info(f"Expression '{expr.expression}' score: {expr.ranking_score:.2f}")
    
    # Step 3: Sort by score (highest first)
    ranked = sorted(expressions, key=lambda x: x.ranking_score, reverse=True)
    
    # Step 4: Return top N
    result = ranked[:max_count]
    
    logger.info(f"Top {len(result)} expressions selected:")
    for i, expr in enumerate(result, 1):
        logger.info(f"  {i}. '{expr.expression}' (score: {expr.ranking_score:.2f})")
    
    return result
