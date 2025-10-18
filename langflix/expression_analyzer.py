import os
import json
import logging
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional
from . import settings
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

def analyze_chunk(subtitle_chunk: List[dict], language_level: str = None, save_output: bool = False, output_dir: str = None) -> List[ExpressionAnalysis]:
    """
    Analyzes a chunk of subtitles using Gemini API with structured output.
    
    Uses Pydantic models for reliable JSON parsing and type safety.
    Returns validated ExpressionAnalysis objects instead of raw dictionaries.
    
    Args:
        subtitle_chunk: List of subtitle dictionaries with start_time, end_time, and text
        language_level: Target language level (beginner, intermediate, advanced, mixed)
        save_output: If True, save LLM response to file for review
        output_dir: Directory to save LLM output files
        
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
        prompt = get_prompt_for_chunk(subtitle_chunk, language_level)
        
        logger.info("Sending prompt to Gemini API with structured output...")
        logger.debug(f"Prompt: {prompt[:200]}...")  # Log first 200 chars

        # Get model name from environment or use default
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        
        # Initialize the model
        model = genai.GenerativeModel(model_name)
        
        # Generate content (fallback to text parsing)
        response = model.generate_content(prompt)
        
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
            return parsed_response.expressions
            
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
        if cleaned_text.startswith('```json'):
            cleaned_text = cleaned_text.replace('```json', '').replace('```', '').strip()
        elif cleaned_text.startswith('```'):
            cleaned_text = cleaned_text.replace('```', '').strip()
        
        # Find JSON array in the response (look for [ or {)
        json_start = -1
        for i, char in enumerate(cleaned_text):
            if char in '[{':
                json_start = i
                break
        
        if json_start != -1:
            cleaned_text = cleaned_text[json_start:]
            
            # Find the end of JSON (look for matching closing bracket/brace)
            bracket_count = 0
            json_end = len(cleaned_text)
            for i, char in enumerate(cleaned_text):
                if char in '[{':
                    bracket_count += 1
                elif char in ']}':
                    bracket_count -= 1
                    if bracket_count == 0:
                        json_end = i + 1
                        break
            
            cleaned_text = cleaned_text[:json_end]
    
        # Parse JSON
        json_data = json.loads(cleaned_text)
        
        # Handle both array and object responses
        if isinstance(json_data, list):
            # If it's an array, wrap it in the expected format
            return ExpressionAnalysisResponse(expressions=json_data)
        elif isinstance(json_data, dict) and 'expressions' in json_data:
            # If it's already in the expected format
            return ExpressionAnalysisResponse.model_validate(json_data)
        else:
            raise ValueError("Unexpected JSON format")
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in response: {e}")
    except Exception as e:
        raise ValueError(f"Failed to validate response: {e}")


def _save_llm_output(response_text: str, subtitle_chunk: List[dict], language_level: str, output_dir: str) -> None:
    """
    Save LLM response to file for review.
    
    Args:
        response_text: Raw response from LLM
        subtitle_chunk: Original subtitle chunk
        language_level: Language level used
        output_dir: Directory to save the file
    """
    try:
        from datetime import datetime
        import os
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"llm_output_{language_level}_{timestamp}.txt"
        filepath = os.path.join(output_dir, filename)
        
        # Prepare content
        content = f"""LLM Output Review
==================
Language Level: {language_level}
Timestamp: {datetime.now().isoformat()}
Chunk Size: {len(subtitle_chunk)} subtitles

Original Subtitle Chunk:
{'-' * 50}
"""
        
        for i, sub in enumerate(subtitle_chunk):
            content += f"{i+1}. [{sub['start_time']}-{sub['end_time']}] {sub['text']}\n"
        
        content += f"""
LLM Response:
{'-' * 50}
{response_text}
"""
        
        # Write to file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"LLM output saved to: {filepath}")
        
    except Exception as e:
        logger.error(f"Failed to save LLM output: {e}")


