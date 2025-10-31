# TempFileManager - Temporary File Management Utility

## Overview

The `TempFileManager` provides centralized temporary file management with automatic cleanup using Python context managers. This ensures that temporary files are properly cleaned up even when exceptions occur, preventing disk space leaks and maintaining system stability.

## Features

- **Automatic Cleanup**: Files are automatically deleted when context exits, even on exceptions
- **Cross-platform**: Uses Python's standard `tempfile` module for compatibility
- **Global Singleton**: Single instance manages all temporary files across the application
- **Manual Registration**: Supports registering externally created files for cleanup
- **Directory Support**: Can create and manage temporary directories as well
- **Exit Handler**: Automatically cleans up all files on application exit via `atexit`

## Usage

### Basic File Creation

```python
from langflix.utils.temp_file_manager import get_temp_manager

manager = get_temp_manager()

# Create a temporary file (automatically cleaned up)
with manager.create_temp_file(suffix='.mkv') as temp_path:
    # Use temp_path for file operations
    temp_path.write_bytes(b"video content")
    # File is automatically deleted when context exits
```

### Custom Prefix and Suffix

```python
with manager.create_temp_file(suffix='.srt', prefix='subtitle_') as temp_path:
    temp_path.write_text("subtitle content")
```

### Persisting Files (delete=False)

```python
# Create file that persists after context exits
with manager.create_temp_file(suffix='.mkv', delete=False) as temp_path:
    temp_path.write_bytes(b"content")
    # File still exists after context exits
    output_path = temp_path  # Can be used elsewhere

# Later, manually register for cleanup
manager.register_file(output_path)
# Will be cleaned up by cleanup_all() or on exit
```

### Temporary Directories

```python
with manager.create_temp_dir() as temp_dir:
    # Create files in the directory
    (temp_dir / "file1.txt").write_text("content1")
    (temp_dir / "file2.txt").write_text("content2")
    # Directory and all contents automatically deleted when context exits
```

### Manual File Registration

```python
# Register an externally created file for cleanup
external_file = Path("/some/path/file.txt")
external_file.write_text("content")

manager.register_file(external_file)
# Will be cleaned up by cleanup_all() or on exit
```

### Cleanup All Files

```python
# Manually trigger cleanup of all registered files
manager.cleanup_all()
```

## API Reference

### `get_temp_manager() -> TempFileManager`

Get the global singleton instance of TempFileManager.

**Returns:** `TempFileManager` - The global instance

### `TempFileManager.__init__(prefix: str = "langflix_", base_dir: Optional[Path] = None)`

Initialize a temp file manager.

**Parameters:**
- `prefix` (str): Prefix for temporary files and directories (default: "langflix_")
- `base_dir` (Optional[Path]): Base directory for temp files (default: system temp dir)

### `TempFileManager.create_temp_file(suffix: str = "", prefix: Optional[str] = None, delete: bool = True) -> Generator[Path, None, None]`

Create a temporary file with automatic cleanup.

**Parameters:**
- `suffix` (str): File suffix (e.g., '.mkv', '.srt')
- `prefix` (Optional[str]): Optional override for prefix
- `delete` (bool): If True, delete file when context exits (default: True)

**Yields:** `Path` - Path to temporary file

**Example:**
```python
with manager.create_temp_file(suffix='.mkv') as temp_path:
    # Use temp_path
    pass
# File automatically deleted
```

### `TempFileManager.create_temp_dir(prefix: Optional[str] = None) -> Generator[Path, None, None]`

Create a temporary directory with automatic cleanup.

**Parameters:**
- `prefix` (Optional[str]): Optional override for prefix

**Yields:** `Path` - Path to temporary directory

**Example:**
```python
with manager.create_temp_dir() as temp_dir:
    # Use temp_dir
    pass
# Directory automatically deleted
```

### `TempFileManager.register_file(file_path: Path) -> None`

Manually register a file for cleanup.

**Parameters:**
- `file_path` (Path): Path to file to register

### `TempFileManager.cleanup_all() -> None`

Clean up all registered temporary files and directories.

## Migration Guide

### Before (Hardcoded Paths)

```python
import tempfile
import os

temp_video_path = f"/tmp/{job_id}_video.mkv"
with open(temp_video_path, 'wb') as f:
    f.write(video_content)

# ... use file ...

# Manual cleanup (easy to forget)
try:
    os.unlink(temp_video_path)
except Exception as e:
    logger.warning(f"Error cleaning up: {e}")
```

### After (TempFileManager)

```python
from langflix.utils.temp_file_manager import get_temp_manager

manager = get_temp_manager()

with manager.create_temp_file(suffix='.mkv', prefix=f'{job_id}_video_') as temp_video_path:
    temp_video_path.write_bytes(video_content)
    # ... use file ...
    # Automatically cleaned up when context exits
```

### Before (NamedTemporaryFile)

```python
import tempfile

temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mkv')
output_path = Path(temp_file.name)
temp_file.close()

# ... use file ...

# Manual cleanup needed
if output_path.exists():
    output_path.unlink()
```

### After (TempFileManager)

```python
from langflix.utils.temp_file_manager import get_temp_manager

manager = get_temp_manager()

with manager.create_temp_file(suffix='.mkv', delete=False) as temp_path:
    output_path = temp_path
    # ... use file ...

# Register for cleanup
manager.register_file(output_path)
# Will be cleaned up on exit or by cleanup_all()
```

## Best Practices

1. **Always use context managers**: Prefer `with` statements for automatic cleanup
2. **Use delete=False sparingly**: Only when file needs to persist beyond context
3. **Register external files**: If creating files outside the manager, register them
4. **Don't access files after cleanup**: Files are deleted when context exits
5. **Nested contexts work**: You can nest multiple context managers safely

## Examples in Codebase

### API Route (jobs.py)

```python
from langflix.utils.temp_file_manager import get_temp_manager

async def process_video_task(...):
    temp_manager = get_temp_manager()
    
    with temp_manager.create_temp_file(suffix='.mkv', prefix=f'{job_id}_video_') as temp_video_path:
        with temp_manager.create_temp_file(suffix='.srt', prefix=f'{job_id}_subtitle_') as temp_subtitle_path:
            temp_video_path.write_bytes(video_content)
            temp_subtitle_path.write_bytes(subtitle_content)
            
            # Process files
            result = service.process_video(...)
            
            # Files automatically cleaned up when context exits
```

### VideoEditor (video_editor.py)

```python
class VideoEditor:
    def __init__(self, ...):
        from langflix.utils.temp_file_manager import get_temp_manager
        self.temp_manager = get_temp_manager()
    
    def _register_temp_file(self, file_path: Path) -> None:
        """Register a temporary file for cleanup later"""
        self.temp_manager.register_file(file_path)
```

### TTS Client (lemonfox_client.py)

```python
from langflix.utils.temp_file_manager import get_temp_manager

if output_path is None:
    temp_manager = get_temp_manager()
    with temp_manager.create_temp_file(suffix='.mp3', prefix="langflix_tts_", delete=False) as temp_path:
        output_path = temp_path
    temp_manager.register_file(output_path)
```

## Testing

Unit and integration tests are available:
- `tests/unit/test_temp_file_manager.py` - Unit tests for TempFileManager
- `tests/integration/test_temp_file_cleanup.py` - Integration tests for cleanup workflows

Run tests:
```bash
pytest tests/unit/test_temp_file_manager.py -v
pytest tests/integration/test_temp_file_cleanup.py -v
```

## Benefits

- **Prevents Disk Leaks**: Automatic cleanup ensures no files are left behind
- **Exception Safety**: Files are cleaned up even when exceptions occur
- **Consistent Pattern**: All code uses the same approach for temp files
- **Easy Migration**: Simple to replace existing temp file code
- **Global Tracking**: Single manager tracks all temporary files

## Related

- [ADR-002: Temporary File Management](./adr/ADR-002-temp-file-management.md) (if exists)
- Python `tempfile` module: https://docs.python.org/3/library/tempfile.html
- Context Manager Pattern: https://docs.python.org/3/library/stdtypes.html#context-manager-types

