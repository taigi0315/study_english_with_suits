import os
import json
import logging
from dotenv import load_dotenv
from typing import List, Dict, Any
from . import config
from .prompts import get_prompt_for_chunk

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
    
    Args:
        subtitle_chunk: List of subtitle dictionaries with start_time, end_time, and text
        
    Returns:
        List of expression dictionaries with analysis results
    """
    try:
        prompt = get_prompt_for_chunk(subtitle_chunk)
        
        logger.info("Sending prompt to Gemini API...")
        logger.debug(f"Prompt: {prompt[:200]}...")  # Log first 200 chars

        # Get model name from environment or use default
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        
        # Initialize the model
        model = genai.GenerativeModel(model_name)
        
        # Generate content
        response = model.generate_content(prompt)
        
        if not response.text:
            logger.error("Empty response from Gemini API")
            return []
        
        # Clean and parse JSON response
        response_text = response.text.strip()
        
        # Remove markdown code blocks if present
        if response_text.startswith('```json'):
            response_text = response_text.replace('```json', '').replace('```', '').strip()
        elif response_text.startswith('```'):
            response_text = response_text.replace('```', '').strip()
        
        # Parse JSON
        result = json.loads(response_text)
        
        # Validate that result is a list
        if not isinstance(result, list):
            logger.warning("LLM response is not a list, wrapping in list")
            result = [result] if result else []
        
        logger.info(f"Successfully analyzed chunk, found {len(result)} expressions")
        return result
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON from LLM response: {e}")
        logger.error(f"Raw response: {response.text if 'response' in locals() else 'No response'}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error in analyze_chunk: {e}")
        return []
