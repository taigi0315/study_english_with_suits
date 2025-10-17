import os
import json
import logging
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional
from . import config
from .prompts import get_prompt_for_chunk
from .models import ExpressionAnalysisResponse, ExpressionAnalysis

import google.generativeai as genai

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def analyze_chunk(subtitle_chunk: List[dict]) -> List[ExpressionAnalysis]:
    """
    Analyzes a chunk of subtitles using Gemini API with structured output.
    
    Uses Pydantic models for reliable JSON parsing and type safety.
    Returns validated ExpressionAnalysis objects instead of raw dictionaries.
    
    Args:
        subtitle_chunk: List of subtitle dictionaries with start_time, end_time, and text
        
    Returns:
        List of ExpressionAnalysis objects with validated analysis results
        
    Raises:
        ValueError: If subtitle_chunk is empty or invalid
        RuntimeError: If API key is not configured
    """
    # Input validation
    if not subtitle_chunk:
        raise ValueError("Subtitle chunk cannot be empty")
    
    if not os.getenv("GEMINI_API_KEY"):
        raise RuntimeError("GEMINI_API_KEY environment variable not set")
    
    try:
        prompt = get_prompt_for_chunk(subtitle_chunk)
        
        logger.info("Sending prompt to Gemini API with structured output...")
        logger.debug(f"Prompt: {prompt[:200]}...")  # Log first 200 chars

        # Get model name from environment or use default
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        
        # Initialize the model
        model = genai.GenerativeModel(model_name)
        
        # Generate content with structured output
        response = model.generate_content(
            prompt,
            generation_config={
                "response_mime_type": "application/json",
                "response_schema": ExpressionAnalysisResponse
            }
        )
        
        if not response.text:
            logger.error("Empty response from Gemini API")
            return []
        
        # Parse structured JSON response
        try:
            # Use the parsed response directly
            if hasattr(response, 'parsed') and response.parsed:
                parsed_response: ExpressionAnalysisResponse = response.parsed
                logger.info(f"Successfully analyzed chunk with structured output, found {len(parsed_response.expressions)} expressions")
                return parsed_response.expressions
            else:
                # Fallback to manual JSON parsing
                parsed_response = _parse_response_text(response.text)
                logger.info(f"Successfully analyzed chunk with fallback parsing, found {len(parsed_response.expressions)} expressions")
                return parsed_response.expressions
            
        except Exception as parse_error:
            logger.error(f"Failed to parse structured response: {parse_error}")
            logger.error(f"Raw response: {response.text}")
            
            # Final fallback to legacy parsing
            return _fallback_parse_response(response.text)
        
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
        if cleaned_text.startswith('```json'):
            cleaned_text = cleaned_text.replace('```json', '').replace('```', '').strip()
        elif cleaned_text.startswith('```'):
            cleaned_text = cleaned_text.replace('```', '').strip()
        
        # Parse JSON and validate with Pydantic
        json_data = json.loads(cleaned_text)
        return ExpressionAnalysisResponse.model_validate(json_data)
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in response: {e}")
    except Exception as e:
        raise ValueError(f"Failed to validate response: {e}")


def _fallback_parse_response(response_text: str) -> List[ExpressionAnalysis]:
    """
    Final fallback method for parsing responses when all other methods fail.
    Attempts to parse as raw JSON and convert to ExpressionAnalysis objects.
    
    Args:
        response_text: Raw response text from Gemini API
        
    Returns:
        List of ExpressionAnalysis objects (may be empty if parsing fails)
    """
    try:
        # Clean response text
        cleaned_text = response_text.strip()
        
        # Remove markdown code blocks if present
        if cleaned_text.startswith('```json'):
            cleaned_text = cleaned_text.replace('```json', '').replace('```', '').strip()
        elif cleaned_text.startswith('```'):
            cleaned_text = cleaned_text.replace('```', '').strip()
        
        # Parse JSON
        json_data = json.loads(cleaned_text)
        
        # Handle different response formats
        if isinstance(json_data, list):
            # Direct list of expressions
            expressions = []
            for item in json_data:
                try:
                    expr = ExpressionAnalysis.model_validate(item)
                    expressions.append(expr)
                except Exception as e:
                    logger.warning(f"Failed to validate expression: {e}")
                    continue
            return expressions
        elif isinstance(json_data, dict) and 'expressions' in json_data:
            # Wrapped in response format
            try:
                response = ExpressionAnalysisResponse.model_validate(json_data)
                return response.expressions
            except Exception as e:
                logger.warning(f"Failed to validate response format: {e}")
                return []
        else:
            # Single expression
            try:
                expr = ExpressionAnalysis.model_validate(json_data)
                return [expr]
            except Exception as e:
                logger.warning(f"Failed to validate single expression: {e}")
                return []
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON in fallback: {e}")
        logger.error(f"Raw response: {response_text}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error in fallback parsing: {e}")
        return []
