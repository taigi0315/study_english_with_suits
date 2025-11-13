"""
File management endpoints for LangFlix API.
"""

from datetime import datetime, timezone
import fnmatch
import logging
import mimetypes
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException

from langflix.api.dependencies import get_storage
from langflix.storage.base import StorageBackend
from langflix.storage.exceptions import StorageError


logger = logging.getLogger(__name__)
router = APIRouter()


PROTECTED_PATTERNS: List[str] = [
    "config.yaml",
    ".env",
    "*.log",
    "langflix.log",
    "requirements.txt",
]


def _normalize_file_id(file_id: str) -> str:
    """
    Validate and normalize file path identifiers.
    
    Args:
        file_id: Raw file identifier from request
    
    Returns:
        Normalized POSIX-style relative path
    """
    candidate = file_id.strip().replace("\\", "/")
    if not candidate:
        raise HTTPException(status_code=400, detail="File path must not be empty")
    
    path_obj = PurePosixPath(candidate)
    
    if path_obj.is_absolute():
        raise HTTPException(status_code=400, detail="Absolute paths are not allowed")
    
    if any(part in ("..", "") for part in path_obj.parts):
        raise HTTPException(status_code=400, detail="Path traversal patterns are not allowed")
    
    normalized = str(path_obj)
    if normalized == ".":
        raise HTTPException(status_code=400, detail="Invalid file path")
    
    return normalized


def _ensure_file_not_protected(file_id: str) -> None:
    """Raise HTTPException if file matches protected patterns."""
    file_name = Path(file_id).name
    for pattern in PROTECTED_PATTERNS:
        if fnmatch.fnmatch(file_id, pattern) or fnmatch.fnmatch(file_name, pattern):
            raise HTTPException(
                status_code=403,
                detail=f"Cannot delete protected file: {file_id}",
            )


def _guess_mime_type(name: str, fallback: str = "application/octet-stream") -> str:
    """Return MIME type based on filename."""
    mime_type, _ = mimetypes.guess_type(name)
    return mime_type or fallback


def _convert_datetime_to_timestamp(value: Optional[datetime]) -> Optional[float]:
    """Convert aware datetime to POSIX timestamp (seconds)."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.timestamp()


def _get_local_file_metadata(file_path: Path, file_id: str) -> Dict[str, Any]:
    """Build metadata payload for local files."""
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {file_id}")
    
    stat = file_path.stat()
    return {
        "file_id": file_id,
        "name": file_path.name,
        "path": file_id,
        "url": str(file_path),
        "size": stat.st_size,
        "type": _guess_mime_type(file_path.name),
        "modified": stat.st_mtime,
        "created": stat.st_ctime,
        "is_directory": file_path.is_dir(),
    }


def _get_gcs_file_metadata(storage: Any, file_id: str) -> Dict[str, Any]:
    """Build metadata payload for Google Cloud Storage objects."""
    blob = storage.bucket.blob(file_id)
    if not blob.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {file_id}")
    
    # Reload metadata for accurate values
    blob.reload()
    
    return {
        "file_id": file_id,
        "name": Path(file_id).name,
        "path": file_id,
        "url": blob.public_url,
        "size": blob.size,
        "type": blob.content_type or _guess_mime_type(file_id),
        "modified": _convert_datetime_to_timestamp(blob.updated),
        "created": _convert_datetime_to_timestamp(blob.time_created),
        "is_directory": False,
    }


def _get_file_metadata(storage: StorageBackend, file_id: str) -> Dict[str, Any]:
    """Retrieve storage-agnostic file metadata."""
    try:
        if hasattr(storage, "base_path"):
            # Local filesystem backend
            local_path = Path(storage.get_file_url(file_id))
            return _get_local_file_metadata(local_path, file_id)
        
        if hasattr(storage, "bucket"):
            # Google Cloud Storage backend
            return _get_gcs_file_metadata(storage, file_id)
        
        # Fallback to URL-only metadata
        url = storage.get_file_url(file_id)
        return {
            "file_id": file_id,
            "name": Path(file_id).name,
            "path": file_id,
            "url": url,
            "size": None,
            "type": _guess_mime_type(file_id),
            "modified": None,
            "created": None,
            "is_directory": False,
        }
    except HTTPException:
        raise
    except StorageError as exc:
        logger.error("Storage error retrieving metadata for %s: %s", file_id, exc)
        raise HTTPException(status_code=500, detail=f"Storage error retrieving file metadata: {exc}") from exc
    except Exception as exc:
        logger.error("Unexpected error retrieving metadata for %s: %s", file_id, exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error retrieving file metadata: {exc}") from exc


@router.get("/files")
async def list_files(storage: StorageBackend = Depends(get_storage)) -> Dict[str, Any]:
    """
    List all files available through the configured storage backend.
    """
    try:
        files: List[Dict[str, Any]] = []
        for file_path in storage.list_files(""):
            normalized = _normalize_file_id(file_path)

            # Skip directories if backend returns them
            metadata = _get_file_metadata(storage, normalized)
            if metadata.get("is_directory"):
                continue
            
            files.append(metadata)
        
        return {"files": files, "total": len(files)}
    except StorageError as exc:
        logger.error("Storage error while listing files: %s", exc)
        raise HTTPException(status_code=500, detail=f"Error listing files: {exc}") from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Unexpected error while listing files: %s", exc)
        raise HTTPException(status_code=500, detail=f"Error listing files: {exc}") from exc


@router.get("/files/{file_id:path}")
async def get_file_details(
    file_id: str,
    storage: StorageBackend = Depends(get_storage),
) -> Dict[str, Any]:
    """
    Retrieve metadata about a specific file using the storage backend.
    """
    normalized = _normalize_file_id(file_id)
    
    try:
        if not storage.file_exists(normalized):
            raise HTTPException(status_code=404, detail=f"File not found: {normalized}")
        
        metadata = _get_file_metadata(storage, normalized)
        if metadata.get("is_directory"):
            raise HTTPException(status_code=400, detail="Directories are not supported")
        
        return metadata
    except HTTPException:
        raise
    except StorageError as exc:
        logger.error("Storage error retrieving file details for %s: %s", normalized, exc)
        raise HTTPException(status_code=500, detail=f"Storage error retrieving file details: {exc}") from exc
    except Exception as exc:
        logger.exception("Unexpected error retrieving file details for %s: %s", normalized, exc)
        raise HTTPException(status_code=500, detail=f"Error retrieving file details: {exc}") from exc


@router.delete("/files/{file_id:path}")
async def delete_file(
    file_id: str,
    storage: StorageBackend = Depends(get_storage),
) -> Dict[str, Any]:
    """
    Delete a file through the configured storage backend.
    """
    normalized = _normalize_file_id(file_id)
    
    try:
        if not storage.file_exists(normalized):
            raise HTTPException(status_code=404, detail=f"File not found: {normalized}")
        
        metadata = _get_file_metadata(storage, normalized)
        if metadata.get("is_directory"):
            raise HTTPException(status_code=400, detail="Deleting directories is not supported")
        
        _ensure_file_not_protected(normalized)
        
        success = storage.delete_file(normalized)
        if not success:
            raise HTTPException(status_code=500, detail=f"Failed to delete file: {normalized}")
        
        logger.info("File deleted: %s", normalized)
        return {
            "message": f"File {normalized} deleted successfully",
            "file_id": normalized,
            "deleted": True,
        }
    except HTTPException:
        raise
    except StorageError as exc:
        logger.error("Storage error deleting file %s: %s", normalized, exc)
        raise HTTPException(status_code=500, detail=f"Storage error deleting file: {exc}") from exc
    except Exception as exc:
        logger.exception("Unexpected error deleting file %s: %s", normalized, exc)
        raise HTTPException(status_code=500, detail=f"Error deleting file: {exc}") from exc
