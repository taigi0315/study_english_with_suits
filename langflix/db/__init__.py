"""
Database module for LangFlix.

This module provides database integration for storing metadata and structured data
alongside the existing file-based system.
"""

from .session import db_manager, DatabaseManager
from .models import Media, Expression, ProcessingJob, Base
from .crud import MediaCRUD, ExpressionCRUD, ProcessingJobCRUD

__all__ = [
    'db_manager',
    'DatabaseManager', 
    'Media',
    'Expression', 
    'ProcessingJob',
    'Base',
    'MediaCRUD',
    'ExpressionCRUD',
    'ProcessingJobCRUD'
]
