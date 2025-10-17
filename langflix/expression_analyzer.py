import os
import json
import logging
from dotenv import load_dotenv
from typing import List, Dict, Any
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

def analyze_chunk(subtitle_chunk: List[dict]) -> List[Dict[str, Any]]:
    """
    Sends a chunk of subtitles to the LLM for analysis and returns the parsed JSON response.
    Uses structured output with Pydantic models for reliable JSON parsing.
    
    Args:
        subtitle_chunk: List of subtitle dictionaries with start_time, end_time, and text
        
    Returns:
        List of expression dictionaries with analysis results
    """
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
                result = [expr.model_dump() for expr in parsed_response.expressions]
            else:
                # Fallback to manual JSON parsing
                response_text = response.text.strip()
                
                # Remove markdown code blocks if present
                if response_text.startswith('```json'):
                    response_text = response_text.replace('```json', '').replace('```', '').strip()
                elif response_text.startswith('```'):
                    response_text = response_text.replace('```', '').strip()
                
                # Parse and validate with Pydantic
                json_data = json.loads(response_text)
                parsed_response = ExpressionAnalysisResponse.model_validate(json_data)
                result = [expr.model_dump() for expr in parsed_response.expressions]
            
            logger.info(f"Successfully analyzed chunk with structured output, found {len(result)} expressions")
            return result
            
        except Exception as parse_error:
            logger.error(f"Failed to parse structured response: {parse_error}")
            logger.error(f"Raw response: {response.text}")
            
            # Fallback to legacy parsing
            return _fallback_parse_response(response.text)
        
    except Exception as e:
        logger.error(f"Unexpected error in analyze_chunk: {e}")
        return []


def _fallback_parse_response(response_text: str) -> List[Dict[str, Any]]:
    """
    Fallback method for parsing responses when structured output fails.
    
    Args:
        response_text: Raw response text from Gemini API
        
    Returns:
        List of expression dictionaries
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
        result = json.loads(cleaned_text)
        
        # Validate that result is a list
        if not isinstance(result, list):
            logger.warning("LLM response is not a list, wrapping in list")
            result = [result] if result else []
        
        logger.info(f"Fallback parsing successful, found {len(result)} expressions")
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON in fallback: {e}")
        logger.error(f"Raw response: {response_text}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error in fallback parsing: {e}")
        return []
