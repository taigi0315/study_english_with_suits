"""
API module for LangFlix.

This module provides RESTful API endpoints for video processing,
job management, and result retrieval using FastAPI.
"""

from .main import app, create_app

__all__ = ['app', 'create_app']
