# Storage Module Documentation

## Overview

The `langflix/storage/` module provides an abstraction layer for storage backends, supporting both local filesystem and Google Cloud Storage.

**Last Updated:** 2025-01-30

## Purpose

This module provides:
- Unified storage interface for file operations
- Support for multiple storage backends (local, GCS)
- Factory pattern for backend creation
- Storage abstraction for API and CLI modes

## Key Components

### StorageBackend (Abstract Base)

**Location:** `langflix/storage/base.py`

Abstract interface that all storage backends must implement:

```python
class StorageBackend(ABC):
    def save_file(local_path, remote_path) -> str
    def load_file(remote_path, local_path) -> bool
    def delete_file(remote_path) -> bool
    def list_files(prefix) -> List[str]
    def file_exists(remote_path) -> bool
    def get_file_url(remote_path) -> str
```

### LocalStorage

**Location:** `langflix/storage/local.py`

Local filesystem storage backend:
- Uses local directory for storage
- Maintains backward compatibility with CLI
- File paths are relative to base directory

### GoogleCloudStorage

**Location:** `langflix/storage/gcs.py`

Google Cloud Storage backend:
- Uploads files to GCS bucket
- Downloads files from GCS
- Supports service account authentication

### StorageFactory

**Location:** `langflix/storage/factory.py`

Factory functions for creating storage backends:

```python
def create_storage_backend() -> StorageBackend:
    """Create storage backend based on configuration."""
    
def create_storage_backend_with_config(backend_type: str, **kwargs) -> StorageBackend:
    """Create storage backend with explicit configuration."""
```

## Usage Examples

### Create Storage Backend

```python
from langflix.storage.factory import create_storage_backend

# Uses configuration from settings
storage = create_storage_backend()

# Or with explicit config
from langflix.storage.local import LocalStorage
storage = LocalStorage(Path("output"))
```

### Save File

```python
storage.save_file(
    local_path=Path("local/video.mp4"),
    remote_path="episodes/s01e01/video.mp4"
)
```

### Load File

```python
storage.load_file(
    remote_path="episodes/s01e01/video.mp4",
    local_path=Path("download/video.mp4")
)
```

## Related Modules

- `langflix.config/`: Storage configuration
- `langflix.db/`: File path references in database

