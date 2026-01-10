"""
File System Cleanup and Management

This package provides intelligent file system management for LangFlix video generation,
including automated cleanup, job tracking, and simplified output structures.
"""

from .models import (
    JobType,
    FileType,
    DirectoryType,
    JobStatus,
    JobContext,
    JobManifest,
    DirectoryStructure,
    CleanupPolicy,
    CleanupResult,
)

__all__ = [
    'JobType',
    'FileType', 
    'DirectoryType',
    'JobStatus',
    'JobContext',
    'JobManifest',
    'DirectoryStructure',
    'CleanupPolicy',
    'CleanupResult',
]