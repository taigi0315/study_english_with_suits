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
from .cache_manager import get_cache_manager
from .error_handler import (
    retry_on_error,
    handle_error_decorator,
    ErrorContext,
    handle_error
)

import google.generativeai as genai

# Load environment variables
load_dotenv()

# Get logger (logging will be configured in main.py)
logger = logging.getLogger(__name__)

# Configure Gemini API - no timeout restrictions to let it take as long as needed
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    masked_key = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "***"
    logger.info(f"Configuring Gemini API with key: {masked_key}")
else:
    logger.error("GEMINI_API_KEY not found in environment variables!")

genai.configure(
    api_key=api_key,
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
                logger.warning(f"Expression {i+1}: '{expr.expression}' - "
                           f"Dialogue/translation count mismatch: {dialogues_count} dialogues vs {translation_count} translations. "
                           "Truncating to minimum length.")
                min_len = min(dialogues_count, translation_count)
                if expr.dialogues:
                    expr.dialogues = expr.dialogues[:min_len]
                if expr.translation:
                    expr.translation = expr.translation[:min_len]
            
            # Check required fields
            if not expr.expression or not expr.expression_translation:
                logger.error(f"Dropping expression {i+1}: '{expr.expression}' - Missing required expression or translation")
                continue
            
            # Check timestamps format (basic validation)
            import re
            timestamp_pattern = r'^\d{2}:\d{2}:\d{2}[.,]\d{3,6}$'
            
            if not expr.context_start_time:
                logger.error(f"Dropping expression {i+1}: '{expr.expression}' - Missing context_start_time")
                continue
                
            if not re.match(timestamp_pattern, expr.context_start_time):
                logger.error(f"Dropping expression {i+1}: '{expr.expression}' - Invalid context_start_time format: {expr.context_start_time}")
                continue
                
            if not expr.context_end_time:
                logger.error(f"Dropping expression {i+1}: '{expr.expression}' - Missing context_end_time")
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

@handle_error_decorator(
    ErrorContext(
        operation="analyze_chunk",
        component="expression_analyzer"
    ),
    retry=False,  # Retry is handled by _generate_content_with_retry
    fallback=False
)
def analyze_chunk(subtitle_chunk: List[dict], language_level: str = None, language_code: str = "ko", save_output: bool = False, output_dir: str = None, target_duration: float = 180.0, test_llm: bool = False, show_name: str = None) -> List[ExpressionAnalysis]:
    """
    Analyzes a chunk of subtitles using Gemini API with structured output (with caching).
    
    Args:
        subtitle_chunk: List of subtitle dictionaries
        language_level: Target language level (beginner, intermediate, advanced, mixed)
        language_code: Target language code for translation
        save_output: Whether to save LLM output to file
        output_dir: Directory to save LLM output
        test_llm: If True, use cached LLM response (for fast development iteration)
        show_name: Show/episode name for cache identification
        
    Returns:
        List of ExpressionAnalysis objects
    """
    try:
        # TEST_LLM MODE: Load from dev test cache if available
        if test_llm:
            from .llm_test_cache import load_llm_test_response, save_llm_test_response
            
            cache_id = show_name or "default"
            cached_data = load_llm_test_response("expression_analysis", cache_id)
            
            if cached_data:
                logger.info(f"🚀 TEST_LLM: Using cached LLM response (skipping API call)")
                try:
                    if isinstance(cached_data, list):
                        return [ExpressionAnalysis(**expr) for expr in cached_data]
                    elif isinstance(cached_data, dict) and "expressions" in cached_data:
                        return [ExpressionAnalysis(**expr) for expr in cached_data["expressions"]]
                    else:
                        logger.warning(f"Invalid test cache format, will call API")
                except Exception as e:
                    logger.warning(f"Failed to parse test cache: {e}, will call API")
            else:
                logger.info(f"🔄 TEST_LLM: No cache found, will call API and save response")
        
        # Check production cache first
        cache_manager = get_cache_manager()
        chunk_text = " ".join([sub.get('text', '') for sub in subtitle_chunk])
        # Add versioning to cache key to force re-analysis when prompt changes
        # Bumping version to invalidate cache with absolute vocab indices (TICKET-029)
        cache_version = "source_lang_vocab_fix"
        cache_key = cache_manager.get_expression_key(f"{chunk_text}_{cache_version}", language_code)
        cached_result = cache_manager.get(cache_key)
        
        if cached_result:
            logger.info(f"Found cached result for chunk, type: {type(cached_result)}")
            try:
                # Handle different cache formats
                if isinstance(cached_result, list):
                    # New format: list of expression dicts
                    logger.info(f"Using cached expression analysis for chunk with {len(cached_result)} expressions")
                    return [ExpressionAnalysis(**expr) for expr in cached_result]
                elif isinstance(cached_result, dict):
                    # Old format: might be wrapped in dict with "expressions" key
                    if "expressions" in cached_result:
                        expressions_list = cached_result["expressions"]
                        logger.info(f"Using cached expression analysis from dict format with {len(expressions_list)} expressions")
                        return [ExpressionAnalysis(**expr) for expr in expressions_list]
                    else:
                        logger.warning(f"Cached dict doesn't have 'expressions' key, keys: {list(cached_result.keys())}")
                        # Clear invalid cache and continue
                        cache_manager.delete(cache_key)
                        logger.warning("Cleared invalid cache, will re-analyze")
                else:
                    logger.warning(f"Unexpected cached result type: {type(cached_result)}")
                    cache_manager.delete(cache_key)
                    logger.warning("Cleared invalid cache, will re-analyze")
            except Exception as cache_error:
                import traceback
                logger.error(f"Error parsing cached expressions: {cache_error}")
                logger.error(f"Error type: {type(cache_error).__name__}")
                logger.error(f"Cached result type: {type(cached_result)}")
                if isinstance(cached_result, dict):
                    logger.error(f"Cached dict keys: {list(cached_result.keys())}")
                logger.debug(f"Full traceback: {traceback.format_exc()}")
                # Clear invalid cache and continue with fresh analysis
                cache_manager.delete(cache_key)
                logger.warning("Cleared invalid cache, will re-analyze")
        
        # Generate prompt
        prompt = get_prompt_for_chunk(subtitle_chunk, language_level, language_code, target_duration=target_duration)
        
        logger.info("Sending prompt to Gemini API with structured output...")
        logger.info(f"Prompt length: {len(prompt)} characters")
        
        # Save full prompt for debugging/testing
        _save_prompt_for_debugging(prompt, subtitle_chunk, language_level, output_dir)
        
        # Check if total prompt is too long (debug only - large chunks are intentional for cost optimization)
        if len(prompt) > 15000:
            logger.debug(f"Large prompt length ({len(prompt)} chars) - expected with optimized chunk size")
        
        # Configure model with settings from YAML config
        model_name = settings.get_llm_model_name()
        generation_config = settings.get_generation_config()
        
        model = genai.GenerativeModel(model_name=model_name)
        
        # Generate content with structured output using Pydantic model
        max_retries = settings.get_max_retries()
        logger.info(f"Using generation config: {generation_config}")
        
        try:
            # Use structured output with Pydantic model
            # Generate JSON schema from Pydantic model and remove unsupported fields
            json_schema = ExpressionAnalysisResponse.model_json_schema()
            
            # Helper function to recursively remove unsupported fields from schema
            def clean_schema(obj):
                """Remove fields that Gemini doesn't support."""
                if isinstance(obj, dict):
                    # Remove unsupported fields
                    # Gemini (via google-generativeai) doesn't support these validation keywords in Schema
                    unsupported_keys = [
                        'title', 'example', 'default', 
                        'minItems', 'maxItems', 'uniqueItems',
                        'minItems', 'maxItems', 'uniqueItems',
                        'minLength', 'maxLength', 'pattern',
                        'anyOf',  # Added anyOf to unsupported keys
                    ]
                    for field in unsupported_keys:
                        obj.pop(field, None)
                        
                    # Recursively clean nested objects
                    for key, value in list(obj.items()):
                        clean_schema(value)
                elif isinstance(obj, list):
                    for item in obj:
                        clean_schema(item)
            
            # Inline $defs references - Gemini API doesn't support $defs or $ref
            if '$defs' in json_schema:
                defs = json_schema['$defs']
                # Inline ExpressionAnalysis schema if it's referenced
                if 'properties' in json_schema and 'expressions' in json_schema['properties']:
                    expr_prop = json_schema['properties']['expressions']
                    if 'items' in expr_prop and '$ref' in expr_prop['items']:
                        ref_path = expr_prop['items']['$ref']
                        if ref_path.startswith('#/$defs/'):
                            def_name = ref_path.split('/')[-1]
                            if def_name in defs:
                                # Replace $ref with inline schema
                                expr_prop['items'] = defs[def_name].copy()
                                logger.debug(f"Inlined {def_name} schema from $defs")
                # Now remove $defs
                del json_schema['$defs']
                logger.debug("Removed $defs from JSON schema for Gemini compatibility")
            
            # Also check 'definitions' (older Pydantic versions)
            if 'definitions' in json_schema:
                del json_schema['definitions']
            
            # Clean all unsupported fields recursively (title, example, default)
            clean_schema(json_schema)
            logger.debug("Cleaned unsupported fields from JSON schema")
            
            # Create generation config dict
            gen_config_dict = {
                "response_mime_type": "application/json",
                "response_schema": json_schema,  # Use cleaned JSON schema instead of Pydantic model
            }
            if generation_config:
                gen_config_dict.update(generation_config)
            
            # Create model with response schema configuration
            model_with_schema = genai.GenerativeModel(
                model_name=model_name,
                generation_config=genai.types.GenerationConfig(**gen_config_dict)
            )
            
            response = model_with_schema.generate_content(prompt)
            
            # Extract structured response
            if hasattr(response, 'text') and response.text:
                # DEBUG: Save raw LLM response to file
                try:
                    import time
                    timestamp = int(time.time())
                    target_dir = Path(output_dir) if output_dir else Path("output")
                    debug_file = target_dir / f"llm_response_{timestamp}.json"
                    debug_file.parent.mkdir(parents=True, exist_ok=True)
                    debug_file.write_text(response.text, encoding='utf-8')
                    logger.info(f"Saved raw LLM response to {debug_file}")
                except Exception as e:
                    logger.warning(f"Failed to save debug LLM response: {e}")

                try:
                    # Parse the structured response
                    response_obj = ExpressionAnalysisResponse.model_validate_json(response.text)
                    expressions = response_obj.expressions
                    
                    # Validate and filter expressions
                    validated_expressions = _validate_and_filter_expressions(expressions)
                    
                    # Remove duplicates using fuzzy matching
                    validated_expressions = _remove_duplicates(validated_expressions)
                    
                    # Log expressions for debugging duplicate detection
                    if len(validated_expressions) < len(expressions):
                        logger.info(f"After deduplication: {len(validated_expressions)} unique expressions from {len(expressions)} total")
                    else:
                        logger.info(f"All {len(validated_expressions)} expressions are unique")
                    
                    logger.info(f"Successfully parsed {len(validated_expressions)} expressions from {len(expressions)} total")
                    
                    # DEBUG: Log vocabulary annotations from response
                    for i, expr in enumerate(expressions):
                        vocab = getattr(expr, 'vocabulary_annotations', [])
                        logger.info(f"DEBUG: Analyzed Expression {i+1} vocab raw: {vocab}")
                    
                    # Save to test cache if test_llm mode is enabled
                    if test_llm:
                        from .llm_test_cache import save_llm_test_response
                        cache_id = show_name or "default"
                        cache_data = [expr.dict() for expr in validated_expressions]
                        save_llm_test_response("expression_analysis", cache_data, cache_id, {
                            "language_code": language_code,
                            "language_level": language_level,
                            "expression_count": len(validated_expressions)
                        })
                    
                    return validated_expressions
                except Exception as validation_error:
                    # If structured output validation fails, log and fall through to text parsing
                    logger.warning(f"Structured output validation failed: {validation_error}")
                    logger.debug(f"Response text preview: {response.text[:500]}")
                    raise  # Re-raise to trigger fallback
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
                # First, try to parse as JSON to check if it's V8 format
                import json as json_module
                cleaned_text = response_text.strip()
                if cleaned_text.startswith("```json"):
                    cleaned_text = cleaned_text[7:]
                if cleaned_text.startswith("```"):
                    cleaned_text = cleaned_text[3:]
                if cleaned_text.endswith("```"):
                    cleaned_text = cleaned_text[:-3]
                cleaned_text = cleaned_text.strip()
                
                try:
                    raw_data = json_module.loads(cleaned_text)
                except json_module.JSONDecodeError:
                    # Fall back to _parse_response_text which has more robust parsing
                    raw_data = None
                
                # Detect V8 format: has context_start_index but no dialogues
                is_v8_format = False
                raw_expressions = None
                
                if raw_data:
                    if isinstance(raw_data, dict) and "expressions" in raw_data:
                        raw_expressions = raw_data["expressions"]
                    elif isinstance(raw_data, list):
                        raw_expressions = raw_data
                    
                    if raw_expressions and len(raw_expressions) > 0:
                        first_expr = raw_expressions[0]
                        # V8 format has indices but no dialogues array
                        if 'context_start_index' in first_expr and 'dialogues' not in first_expr:
                            is_v8_format = True
                            logger.info(f"🔄 Detected V8 index-based format, applying post-processing...")
                
                # Apply V8 post-processing if needed
                if is_v8_format and raw_expressions:
                    # Post-process to convert indices to full text
                    processed_expressions = _postprocess_v8_response(raw_expressions, subtitle_chunk)
                    response_obj = ExpressionAnalysisResponse(expressions=processed_expressions)
                else:
                    # Standard V7 format - use regular parsing
                    response_obj = _parse_response_text(response_text)
                
                expressions = response_obj.expressions

                
                # Validate and filter expressions
                validated_expressions = _validate_and_filter_expressions(expressions)
                
                # Remove duplicates using fuzzy matching
                validated_expressions = _remove_duplicates(validated_expressions)
                
                # Log expressions for debugging duplicate detection
                if len(validated_expressions) < len(expressions):
                    logger.info(f"After deduplication: {len(validated_expressions)} unique expressions from {len(expressions)} total")
                else:
                    logger.info(f"All {len(validated_expressions)} expressions are unique")
                
                # Cache the result
                cache_data = [expr.dict() for expr in validated_expressions]
                cache_manager.set(cache_key, cache_data, ttl=3600, persist_to_disk=True)  # 1 hour
                
                logger.info(f"Successfully parsed {len(validated_expressions)} expressions from {len(expressions)} total")
                return validated_expressions
                
            except Exception as parse_error:
                import traceback
                logger.error(f"Failed to parse response: {parse_error}")
                logger.error(f"Error type: {type(parse_error).__name__}")
                logger.error(f"Full traceback: {traceback.format_exc()}")
                # Log more details if it's a validation error
                if hasattr(parse_error, 'errors'):
                    try:
                        if callable(parse_error.errors):
                            logger.error(f"Validation errors: {parse_error.errors()}")
                        else:
                            logger.error(f"Validation errors: {parse_error.errors}")
                    except Exception:
                        logger.warning("Could not log validation errors")
                # Log first 500 chars of response for debugging
                response_preview = response_text[:500] if response_text else "No response text"
                logger.error(f"Raw response preview: {response_preview}")
                
                # If all parsing fails, return empty list
                logger.warning("All parsing methods failed, returning empty list")
                return []
        
    except Exception as e:
        import traceback
        logger.error(f"Unexpected error in analyze_chunk: {e}")
        logger.error(f"Error type: {type(e).__name__}")
        # Log the full traceback at debug level, but provide more context at error level
        error_msg = str(e)
        logger.error(f"Error message: {error_msg}")
        logger.debug(f"Full traceback: {traceback.format_exc()}")
        # Log more details if it's a validation error
        if hasattr(e, 'errors'):
            try:
                if callable(e.errors):
                    logger.error(f"Validation errors: {e.errors()}")
                else:
                    logger.error(f"Validation errors: {e.errors}")
            except Exception:
                logger.warning("Could not log validation errors")
        # Don't log as "No expressions found" - this is an actual error
        logger.warning(f"No expressions found in chunk due to error: {type(e).__name__}")
        return []


def _postprocess_v8_response(raw_expressions: List[Dict[str, Any]], subtitle_chunk: List[dict], target_dialogues: List[dict] = None) -> List[Dict[str, Any]]:
    """
    Post-processing: Convert V8 index-based LLM output to full ExpressionAnalysis format.
    
    The LLM only provides indices, and we look up actual text from the subtitle chunks.
    
    Args:
        raw_expressions: List of expression dicts from LLM with index-based fields
        subtitle_chunk: Source language subtitle chunk (list of dicts with 'text', 'start_time', 'end_time')
        target_dialogues: Target language subtitle chunk (if available, else use source)
        
    Returns:
        List of expression dicts with full text fields populated
    """
    processed = []
    
    for expr_data in raw_expressions:
        try:
            # Extract indices from LLM output
            context_start_idx = expr_data.get('context_start_index', 0)
            context_end_idx = expr_data.get('context_end_index', len(subtitle_chunk) - 1)
            expr_dialogue_idx = expr_data.get('expression_dialogue_index', context_start_idx)
            
            # Validate indices
            if context_start_idx < 0 or context_end_idx >= len(subtitle_chunk):
                logger.warning(f"Invalid context indices: {context_start_idx}-{context_end_idx}, max={len(subtitle_chunk)-1}")
                context_start_idx = max(0, context_start_idx)
                context_end_idx = min(len(subtitle_chunk) - 1, context_end_idx)
            
            if expr_dialogue_idx < context_start_idx or expr_dialogue_idx > context_end_idx:
                logger.warning(f"expression_dialogue_index {expr_dialogue_idx} outside context range, adjusting")
                expr_dialogue_idx = context_start_idx
            
            # Look up dialogues from source subtitles
            dialogues = []
            for i in range(context_start_idx, context_end_idx + 1):
                if i < len(subtitle_chunk):
                    dialogues.append(subtitle_chunk[i].get('text', ''))
            
            # Look up translations from target subtitles (or use source if not available)
            translations = []
            target_source = target_dialogues if target_dialogues and len(target_dialogues) > context_end_idx else subtitle_chunk
            for i in range(context_start_idx, context_end_idx + 1):
                if i < len(target_source):
                    translations.append(target_source[i].get('text', ''))
            
            # Get timestamps
            context_start_time = subtitle_chunk[context_start_idx].get('start_time', '00:00:00,000')
            context_end_time = subtitle_chunk[context_end_idx].get('end_time', '00:00:30,000')
            
            # Get expression dialogue
            expression_dialogue = subtitle_chunk[expr_dialogue_idx].get('text', '') if expr_dialogue_idx < len(subtitle_chunk) else ''
            expression_dialogue_translation = target_source[expr_dialogue_idx].get('text', '') if expr_dialogue_idx < len(target_source) else ''
            
            # Use LLM-provided expression_translation if available (preferred in V8 mode)
            # Fall back to looking up from target dialogues only if LLM didn't provide it
            llm_expression_translation = expr_data.get('expression_translation', '')
            expression_translation = llm_expression_translation if llm_expression_translation else expr_data.get('expression', '')
            
            # Process vocabulary annotations - use LLM-provided translations
            vocab_annotations = expr_data.get('vocabulary_annotations', [])
            for vocab in vocab_annotations:
                # FIX for Timestamp Drift (TICKET-029)
                # LLM returns dialogue_index relative to the CHUNK (0..N)
                # But 'dialogues' list is sliced from context_start_idx (M..P)
                # We must normalize dialogue_index to be relative to the sliced list (0..P-M)
                raw_idx = vocab.get('dialogue_index', 0)
                relative_idx = max(0, raw_idx - context_start_idx)
                vocab['dialogue_index'] = relative_idx
                
                if 'translation' not in vocab and target_dialogues:
                    # Look up translation from the target dialogue at the specified index
                    # Note: Need to look up in ORIGINAL target_dialogues using raw_idx
                    if raw_idx < len(target_dialogues):
                        # We don't have word-level translation, so leave blank or use placeholder
                        vocab['translation'] = f"({vocab.get('word', '')} translation)"
                elif 'translation' not in vocab:
                    vocab['translation'] = vocab.get('word', '')  # Fallback
            
            # Build the full expression dict
            full_expr = {
                'title': expr_data.get('title', ''),
                'dialogues': dialogues,
                'translation': translations,
                'expression_dialogue': expression_dialogue,
                'expression_dialogue_translation': expression_dialogue_translation,
                'expression': expr_data.get('expression', ''),
                'expression_translation': expression_translation,  # Use LLM-provided translation
                'intro_hook': expr_data.get('intro_hook', ''),
                'context_start_time': context_start_time,
                'context_end_time': context_end_time,
                'similar_expressions': expr_data.get('similar_expressions', []),
                'scene_type': expr_data.get('scene_type', 'drama'),
                'catchy_keywords': expr_data.get('catchy_keywords', []),
                'vocabulary_annotations': vocab_annotations,
            }
            
            processed.append(full_expr)
            logger.info(f"✅ V8 Post-processed: '{full_expr['expression']}' (indices {context_start_idx}-{context_end_idx})")
            
        except Exception as e:
            logger.error(f"Error post-processing V8 expression: {e}")
            continue
    
    return processed


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
            
            # Handle "Extra data" error (multiple JSON objects)
            if "Extra data" in str(json_error):
                try:
                    # Try to parse just up to the extra data position
                    # This often happens when LLM outputs multiple JSON blocks
                    # json_error.pos gives the position where parsing stopped (start of extra data)
                    if hasattr(json_error, 'pos'):
                        valid_json_part = cleaned_text[:json_error.pos]
                        data = json.loads(valid_json_part)
                        logger.info("Successfully parsed first JSON block from multiple blocks response")
                    else:
                        raise ValueError("JSON error missing position info")
                except Exception as inner_e:
                    logger.warning(f"Failed to recover from Extra data error: {inner_e}")
                    # Fallthrough to regex extraction
            
            if 'data' not in locals():
                # Try to extract JSON from within the text using regex
                import re
                # Look for the first valid JSON object or list
                # This pattern finds the first outermost {} or [] block
                json_match = re.search(r'(\{.*\}|\[.*\])', cleaned_text, re.DOTALL)
                
                if json_match:
                    json_text = json_match.group(0)
                    try:
                        data = json.loads(json_text)
                    except json.JSONDecodeError as regex_json_error:
                        # If regex match is also invalid (e.g. multiple objects inside), try to find just the first one
                        # If it starts with {, find matching closing }
                        if json_text.strip().startswith('{'):
                            count = 0
                            end_pos = 0
                            for i, char in enumerate(json_text):
                                if char == '{':
                                    count += 1
                                elif char == '}':
                                    count -= 1
                                    if count == 0:
                                        end_pos = i + 1
                                        break
                            if end_pos > 0:
                                data = json.loads(json_text[:end_pos])
                            else:
                                raise ValueError(f"Could not find matching closing brace in: {json_text[:100]}...")
                        else:
                             raise regex_json_error
                else:
                    raise ValueError(f"Could not extract valid JSON from response: {json_error}")
        
        # Validate using Pydantic
        # Handle different response formats
        if isinstance(data, dict):
            # Check what keys are available
            available_keys = list(data.keys())
            logger.debug(f"Parsed JSON has keys: {available_keys}")
            
            # Try to find expressions key (case-insensitive, handle quotes)
            expressions_data = None
            
            # Try exact match first
            if "expressions" in data:
                expressions_data = data["expressions"]
            # Try case variations
            elif "Expressions" in data:
                logger.warning("Found key 'Expressions' instead of 'expressions', attempting to use it")
                expressions_data = data["Expressions"]
            # Try other case variations
            elif "EXPRESSIONS" in data:
                logger.warning("Found key 'EXPRESSIONS' instead of 'expressions', attempting to use it")
                expressions_data = data["EXPRESSIONS"]
            else:
                # Log all keys for debugging
                logger.error(f"Response dict keys: {available_keys}")
                logger.error(f"Response dict sample: {str(data)[:500]}")
                raise ValueError(
                    f"Expected 'expressions' key in response, but found keys: {available_keys}. "
                    f"Response structure: {type(data)}"
                )
            
            if expressions_data is None:
                raise ValueError(f"'expressions' key found but value is None")
            
            response_obj = ExpressionAnalysisResponse(expressions=expressions_data)
        elif isinstance(data, list):
            # If response is directly a list, treat it as expressions
            logger.debug(f"Response is a list with {len(data)} items, treating as expressions")
            response_obj = ExpressionAnalysisResponse(expressions=data)
        else:
            logger.error(f"Invalid JSON structure type: {type(data)}, value: {str(data)[:500]}")
            raise ValueError(f"Invalid JSON structure: expected dict or list, got {type(data).__name__}")
        
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
    Now integrated with error_handler for structured error reporting.
    
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
    error_context = ErrorContext(
        operation="generate_content",
        component="expression_analyzer",
        additional_data={"max_retries": max_retries, "prompt_length": len(prompt)}
    )
    
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
            
            # Check for rate limit errors (429) - use longer backoff
            is_rate_limit = any(keyword in error_str.lower() for keyword in ['429', 'quota', 'resource exhausted', 'rate limit'])
            
            # Check for server errors that warrant retries
            is_server_error = any(keyword in error_str.lower() for keyword in ['timeout', '504', '503', '502', '500'])
            
            if is_rate_limit:
                # Rate limit: use longer backoff (30s, 60s, 120s)
                rate_limit_backoff = [30, 60, 120]
                wait_time = rate_limit_backoff[min(attempt, len(rate_limit_backoff) - 1)]
                logger.warning(f"Rate limit hit on attempt {attempt + 1}: {error_str}")
                logger.info(f"Waiting {wait_time}s before retry (rate limit backoff)...")
                
                error_context.additional_data["attempt"] = attempt + 1
                error_context.additional_data["error_type"] = "rate_limit"
                handle_error(e, error_context, retry=False, fallback=False)
                
                if attempt == max_retries:
                    logger.error(f"Max retries reached for rate limit. Final error: {error_str}")
                    break
                    
                time.sleep(wait_time)
                continue  # Skip to next iteration
                
            elif is_server_error:
                logger.warning(f"API error on attempt {attempt + 1}: {error_str}")
                
                # Report error to error handler (but don't raise yet if we can retry)
                error_context.additional_data["attempt"] = attempt + 1
                error_context.additional_data["max_retries"] = max_retries + 1
                handle_error(e, error_context, retry=False, fallback=False)
                
                if attempt == max_retries:
                    logger.error(f"Max retries reached. Final error: {error_str}")
                    break
            else:
                # Non-retryable error - report and raise immediately
                error_context.additional_data["attempt"] = attempt + 1
                handle_error(e, error_context, retry=False, fallback=False)
                logger.error(f"Non-retryable API error: {error_str}")
                raise e
    
    # If we get here, all retries failed - report final error
    if last_error:
        error_context.additional_data["final_attempt"] = max_retries + 1
        handle_error(last_error, error_context, retry=False, fallback=False)
        logger.error(f"All {max_retries + 1} API attempts failed. Last error: {last_error}")
        raise last_error
    else:
        raise RuntimeError("All API attempts failed with unknown error")


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
                # Also check if context is the same (exact match for timestamps)
                context_match = (expr.context_start_time == existing.context_start_time and 
                               expr.context_end_time == existing.context_end_time)
                
                if context_match:
                    logger.warning(
                        f"Removing duplicate: '{expr.expression}' "
                        f"(same expression AND context as '{existing.expression}', "
                        f"similarity: {similarity}%, context: {expr.context_start_time}-{expr.context_end_time})"
                    )
                else:
                    logger.info(
                        f"Removing duplicate expression text: '{expr.expression}' "
                        f"(similar to '{existing.expression}', similarity: {similarity}%, "
                        f"but different context: {expr.context_start_time}-{expr.context_end_time} vs "
                        f"{existing.context_start_time}-{existing.context_end_time})"
                    )
                is_duplicate = True
                break
        
        if not is_duplicate:
            unique.append(expr)
    
    removed_count = len(expressions) - len(unique)
    if removed_count > 0:
        logger.info(f"Removed {removed_count} duplicate expression(s)")
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
