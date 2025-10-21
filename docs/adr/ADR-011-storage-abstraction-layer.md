# ADR-011: Storage Abstraction Layer

**Date:** 2025-10-21  
**Status:** Draft  
**Deciders:** Development Team  
**Related ADRs:** ADR-009 (Service Architecture Foundation), ADR-010 (Database Schema)

## Context

LangFlix needs to support multiple storage backends to separate CLI (local development) from API (cloud production) usage. The current system uses local file system exclusively, but the API will need cloud storage (Google Cloud Storage).

## Decision

We will create a storage abstraction layer that supports multiple backends (LocalStorage and GoogleCloudStorage) with a unified interface, making storage backend selection configurable.

## Storage Abstraction Design

### Abstract Interface: `StorageBackend`

```python
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Union

class StorageBackend(ABC):
    """Abstract base class for storage backends."""
    
    @abstractmethod
    def save_file(self, local_path: Path, remote_path: str) -> str:
        """
        Save file to storage.
        
        Args:
            local_path: Path to local file
            remote_path: Destination path in storage
            
        Returns:
            URL or path to stored file
        """
        pass
    
    @abstractmethod
    def load_file(self, remote_path: str, local_path: Path) -> bool:
        """
        Load file from storage to local filesystem.
        
        Args:
            remote_path: Path in storage
            local_path: Destination local path
            
        Returns:
            True if successful, False otherwise
        """
        pass
    
    @abstractmethod
    def delete_file(self, remote_path: str) -> bool:
        """Delete file from storage."""
        pass
    
    @abstractmethod
    def list_files(self, prefix: str) -> List[str]:
        """List files with given prefix."""
        pass
    
    @abstractmethod
    def file_exists(self, remote_path: str) -> bool:
        """Check if file exists in storage."""
        pass
    
    @abstractmethod
    def get_file_url(self, remote_path: str) -> str:
        """
        Get public URL for file (if applicable).
        
        Args:
            remote_path: Path in storage
            
        Returns:
            Public URL or local path
        """
        pass
```

### Backend Implementations

#### LocalStorage Implementation
```python
class LocalStorage(StorageBackend):
    """Local filesystem storage backend."""
    
    def __init__(self, base_path: Path):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def save_file(self, local_path: Path, remote_path: str) -> str:
        """Copy file to local storage directory."""
        dest_path = self.base_path / remote_path
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(local_path, dest_path)
        return str(dest_path)
    
    def load_file(self, remote_path: str, local_path: Path) -> bool:
        """Copy file from local storage to destination."""
        source_path = self.base_path / remote_path
        if not source_path.exists():
            return False
        shutil.copy2(source_path, local_path)
        return True
    
    def delete_file(self, remote_path: str) -> bool:
        """Delete file from local storage."""
        file_path = self.base_path / remote_path
        if file_path.exists():
            file_path.unlink()
            return True
        return False
    
    def list_files(self, prefix: str) -> List[str]:
        """List files with given prefix."""
        search_path = self.base_path / prefix
        if not search_path.exists():
            return []
        return [str(p.relative_to(self.base_path)) 
                   for p in search_path.rglob('*') if p.is_file()]
    
    def file_exists(self, remote_path: str) -> bool:
        """Check if file exists in local storage."""
        return (self.base_path / remote_path).exists()
    
    def get_file_url(self, remote_path: str) -> str:
        """Return local file path."""
        return str(self.base_path / remote_path)
```

#### GoogleCloudStorage Implementation
```python
class GoogleCloudStorage(StorageBackend):
    """Google Cloud Storage backend."""
    
    def __init__(self, bucket_name: str, credentials_path: Optional[str] = None):
        from google.cloud import storage
        
        self.bucket_name = bucket_name
        self.client = storage.Client.from_service_account_json(
            credentials_path
        ) if credentials_path else storage.Client()
        self.bucket = self.client.bucket(bucket_name)
    
    def save_file(self, local_path: Path, remote_path: str) -> str:
        """Upload file to GCS bucket."""
        blob = self.bucket.blob(remote_path)
        blob.upload_from_filename(str(local_path))
        return f"gcs://{self.bucket_name}/{remote_path}"
    
    def load_file(self, remote_path: str, local_path: Path) -> bool:
        """Download file from GCS bucket."""
        try:
            blob = self.bucket.blob(remote_path)
            blob.download_to_filename(str(local_path))
            return True
        except Exception:
            return False
    
    def delete_file(self, remote_path: str) -> bool:
        """Delete file from GCS bucket."""
        try:
            blob = self.bucket.blob(remote_path)
            blob.delete()
            return True
        except Exception:
            return False
    
    def list_files(self, prefix: str) -> List[str]:
        """List files with given prefix in GCS bucket."""
        blobs = self.bucket.list_blobs(prefix=prefix)
        return [blob.name for blob in blobs]
    
    def file_exists(self, remote_path: str) -> bool:
        """Check if file exists in GCS bucket."""
        blob = self.bucket.blob(remote_path)
        return blob.exists()
    
    def get_file_url(self, remote_path: str) -> str:
        """Get public URL for GCS file."""
        blob = self.bucket.blob(remote_path)
        return blob.public_url
```

### Storage Factory

```python
from langflix.storage.base import StorageBackend
from langflix.storage.local import LocalStorage
from langflix.storage.gcs import GoogleCloudStorage
from langflix.config import settings

def create_storage_backend() -> StorageBackend:
    """Create storage backend based on configuration."""
    backend_type = settings.get_storage_backend()
    
    if backend_type == "local":
        base_path = settings.get_storage_local_path()
        return LocalStorage(Path(base_path))
    
    elif backend_type == "gcs":
        bucket_name = settings.get_storage_gcs_bucket()
        credentials_path = settings.get_storage_gcs_credentials()
        return GoogleCloudStorage(bucket_name, credentials_path)
    
    else:
        raise ValueError(f"Unknown storage backend: {backend_type}")
```

### Configuration

#### default.yaml
```yaml
storage:
  backend: "local"  # "local" | "gcs"
  local:
    base_path: "output"
  gcs:
    bucket_name: "langflix-storage"
    credentials_path: null  # Path to service account JSON
```

#### settings.py
```python
def get_storage_backend() -> str:
    """Get storage backend type."""
    return settings.get("storage.backend", "local")

def get_storage_local_path() -> str:
    """Get local storage base path."""
    return settings.get("storage.local.base_path", "output")

def get_storage_gcs_bucket() -> str:
    """Get GCS bucket name."""
    return settings.get("storage.gcs.bucket_name")

def get_storage_gcs_credentials() -> Optional[str]:
    """Get GCS credentials path."""
    return settings.get("storage.gcs.credentials_path")
```

## Integration Strategy

### Current File Operations to Abstract

#### Video Processing
```python
# Before (direct file operations)
output_path = Path("output") / "video.mp4"
video.save(str(output_path))

# After (storage abstraction)
storage = create_storage_backend()
remote_path = storage.save_file(local_path, "videos/video.mp4")
```

#### Subtitle Processing
```python
# Before
subtitle_path = output_dir / "subtitles.srt"
subtitle_file.write_text(content)

# After
storage = create_storage_backend()
remote_path = storage.save_file(subtitle_path, "subtitles/subtitles.srt")
```

#### Educational Slides
```python
# Before
slide_path = output_dir / "slide.mp4"
slide_video.save(str(slide_path))

# After
storage = create_storage_backend()
remote_path = storage.save_file(slide_path, "slides/slide.mp4")
```

### Backward Compatibility

#### CLI Mode (Default)
- Uses `LocalStorage` backend
- Files saved to local `output/` directory
- No change in user experience
- All existing functionality preserved

#### API Mode
- Uses `GoogleCloudStorage` backend
- Files uploaded to GCS bucket
- URLs stored in database
- Cloud-accessible results

## File Path Strategy

### Path Format
```
{backend}://{bucket}/{path}
```

### Examples
```
# LocalStorage
local://output/Suits/S01E01/context_video.mkv
local://output/Suits/S01E01/slides/expression_01.mp4

# GoogleCloudStorage
gcs://langflix-bucket/Suits/S01E01/context_video.mkv
gcs://langflix-bucket/Suits/S01E01/slides/expression_01.mp4
```

### Path Generation
```python
def generate_storage_path(
    show_name: str,
    episode_name: str,
    file_type: str,
    filename: str
) -> str:
    """Generate consistent storage path."""
    return f"{show_name}/{episode_name}/{file_type}/{filename}"
```

## Error Handling

### Storage Errors
```python
class StorageError(Exception):
    """Base storage error."""
    pass

class StorageNotFoundError(StorageError):
    """File not found in storage."""
    pass

class StoragePermissionError(StorageError):
    """Permission denied."""
    pass

class StorageQuotaError(StorageError):
    """Storage quota exceeded."""
    pass
```

### Retry Logic
```python
import time
from functools import wraps

def retry_storage_operation(max_retries: int = 3, delay: float = 1.0):
    """Decorator for retrying storage operations."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except StorageError as e:
                    if attempt == max_retries - 1:
                        raise
                    time.sleep(delay * (2 ** attempt))  # Exponential backoff
            return None
        return wrapper
    return decorator
```

## Testing Strategy

### Unit Tests
```python
# Test LocalStorage
def test_local_storage_save_file():
    storage = LocalStorage(Path("/tmp/test"))
    result = storage.save_file(Path("input.txt"), "test/input.txt")
    assert result == "/tmp/test/test/input.txt"
    assert storage.file_exists("test/input.txt")

# Test GoogleCloudStorage (mocked)
@patch('google.cloud.storage.Client')
def test_gcs_storage_save_file(mock_client):
    storage = GoogleCloudStorage("test-bucket")
    result = storage.save_file(Path("input.txt"), "test/input.txt")
    assert result == "gcs://test-bucket/test/input.txt"
```

### Integration Tests
```python
# Test CLI with LocalStorage
def test_cli_with_local_storage():
    # Run CLI command
    # Verify files saved to local storage
    # Verify database entries have local paths

# Test API with GCS (mocked)
def test_api_with_gcs_storage():
    # Mock GCS operations
    # Test file upload
    # Verify database entries have GCS paths
```

## Dependencies

### LocalStorage
- No additional dependencies (uses standard library)

### GoogleCloudStorage
```txt
google-cloud-storage>=2.10.0
```

### Optional Dependencies
```txt
# For development/testing
google-cloud-storage[testing]>=2.10.0
```

## Consequences

### Positive
- **Flexibility**: Support multiple storage backends
- **Scalability**: Cloud storage for production
- **Backward Compatibility**: CLI unchanged
- **Unified Interface**: Same code for all backends
- **Configuration**: Easy backend switching

### Negative
- **Complexity**: Additional abstraction layer
- **Dependencies**: GCS client library
- **Testing**: More complex test scenarios
- **Configuration**: Additional setup for cloud storage

### Risks and Mitigations

**Risk: Storage Backend Failures**
- Mitigation: Error handling, retry logic, fallback strategies

**Risk: Performance Issues**
- Mitigation: Connection pooling, async operations (future)

**Risk: Configuration Errors**
- Mitigation: Validation, clear error messages, documentation

## Success Criteria

### Phase 1b Complete When:
- [ ] Storage abstraction interface defined
- [ ] LocalStorage backend implemented and tested
- [ ] GoogleCloudStorage backend implemented and tested
- [ ] Storage factory working
- [ ] CLI uses LocalStorage by default
- [ ] API can use GCS backend
- [ ] All existing tests passing
- [ ] New storage tests passing

## References

- [ADR-009: Service Architecture Foundation](ADR-009-service-architecture-foundation.md)
- [Google Cloud Storage Python Client](https://cloud.google.com/storage/docs/reference/libraries#client-libraries-install-python)
- [Python pathlib Documentation](https://docs.python.org/3/library/pathlib.html)

## Next Steps

1. Get this ADR approved
2. Create `phase-1b-storage-abstraction` branch
3. Implement storage abstraction interface
4. Implement LocalStorage backend
5. Implement GoogleCloudStorage backend
6. Begin integration with existing code
