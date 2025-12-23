"""
LLM Client: Unified interface for Gemini API
"""
import os
import google.generativeai as genai
import logging
from dotenv import load_dotenv
from langflix import settings

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Configure API on module load
_api_configured = False


def configure_api():
    """Configure Gemini API with key from environment."""
    global _api_configured
    if not _api_configured:
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            _api_configured = True
            logger.info(f"Configured Gemini API with key: {api_key[:4]}...{api_key[-4:]}")
        else:
            logger.warning("GEMINI_API_KEY not found in environment variables")


def get_gemini_client(model_name: str = None) -> genai.GenerativeModel:
    """
    Get a configured Gemini GenerativeModel instance.
    
    Args:
        model_name: Model name to use, defaults to settings
        
    Returns:
        Configured GenerativeModel instance
    """
    configure_api()
    
    if not model_name:
        model_name = settings.get_llm_model_name()
    
    return genai.GenerativeModel(model_name=model_name)


def get_model_with_schema(model_name: str, response_schema: dict) -> genai.GenerativeModel:
    """
    Get a Gemini model configured for structured output.
    
    Args:
        model_name: Model name to use
        response_schema: JSON schema for response
        
    Returns:
        Configured GenerativeModel instance
    """
    configure_api()
    
    return genai.GenerativeModel(
        model_name=model_name,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            response_schema=response_schema
        )
    )
