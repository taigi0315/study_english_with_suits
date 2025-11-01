# Filename Sanitization Utilities

**Last Updated:** 2025-01-30  
**Location:** `langflix/utils/filename_utils.py`

## Overview

The `filename_utils` module provides standardized filename sanitization utilities for safe file system operations across all platforms (Windows, macOS, Linux). This module consolidates all filename sanitization logic that was previously duplicated across multiple files in the codebase.

## Purpose

- **Security**: Prevent filename injection attacks
- **Cross-platform compatibility**: Ensure filenames work on Windows, macOS, and Linux
- **Consistency**: Single source of truth for filename sanitization
- **Maintainability**: Update sanitization logic in one place

## Functions

### `sanitize_filename()`

Main function for sanitizing text into safe filenames.

```python
from langflix.utils.filename_utils import sanitize_filename

# Basic usage
safe_name = sanitize_filename("Hello World!")
# Returns: "Hello_World"

# With extension preservation
safe_name = sanitize_filename("test.file.mp4", allowed_extensions=['.mp4'])
# Returns: "testfile.mp4"

# Custom max length
safe_name = sanitize_filename("very long filename", max_length=50)
# Returns: truncated to 50 characters
```

**Parameters:**
- `text` (str): Input text to sanitize
- `max_length` (int, optional): Maximum length of output (default: 100)
- `replace_spaces` (bool, optional): If True, replace spaces with underscores (default: True)
- `allowed_extensions` (list[str], optional): List of allowed file extensions to preserve

**Returns:**
- `str`: Sanitized filename-safe string

**Behavior:**
- Removes all non-ASCII alphanumeric characters
- Replaces spaces with underscores (if `replace_spaces=True`)
- Removes dots from base name (only extension dots are preserved)
- Enforces maximum length limit
- Returns "untitled" for empty or invalid input

### `sanitize_for_expression_filename()`

Convenience wrapper specifically for expression text sanitization.

```python
from langflix.utils.filename_utils import sanitize_for_expression_filename

# Default usage (max_length=50)
safe_name = sanitize_for_expression_filename("How are you?")
# Returns: "How_are_you"

# Custom max length
safe_name = sanitize_for_expression_filename("long expression text", max_length=30)
# Returns: truncated to 30 characters
```

**Parameters:**
- `expression` (str): Expression text to sanitize
- `max_length` (int, optional): Maximum length (default: 50)

**Returns:**
- `str`: Sanitized filename

### `sanitize_for_context_video_name()`

Convenience wrapper for context video filename sanitization.

```python
from langflix.utils.filename_utils import sanitize_for_context_video_name

safe_name = sanitize_for_context_video_name("How are you?")
# Returns: "How_are_you" (max_length=50, no extension)
```

**Parameters:**
- `expression` (str): Expression text

**Returns:**
- `str`: Sanitized filename (no extension)

## Constants

### `MAX_FILENAME_LENGTH`
Standard filesystem limit: `255` characters

### `DEFAULT_MAX_LENGTH`
Reasonable default for most use cases: `100` characters

## Usage Examples

### Basic Expression Filename

```python
from langflix.utils.filename_utils import sanitize_for_expression_filename

expression = "I'm gonna get screwed"
filename = sanitize_for_expression_filename(expression)
# filename = "Im_gonna_get_screwed"
```

### Context Video Filename

```python
from langflix.utils.filename_utils import sanitize_for_context_video_name

expression = "What's up?"
filename = sanitize_for_context_video_name(expression)
# filename = "Whats_up"
video_path = f"context_{filename}.mkv"
```

### With Extension Preservation

```python
from langflix.utils.filename_utils import sanitize_filename

text = "my video file.mkv"
filename = sanitize_filename(text, allowed_extensions=['.mkv'])
# filename = "my_video_file.mkv"
```

### Custom Length Limit

```python
from langflix.utils.filename_utils import sanitize_filename

long_text = "this is a very long expression that needs truncation"
filename = sanitize_filename(long_text, max_length=30)
# filename = "this_is_a_very_long_expres" (truncated to 30)
```

## Cross-Platform Compatibility

The sanitization function ensures compatibility across platforms:

- **Windows**: Removes reserved characters (`<>:"/\|?*`)
- **macOS**: Handles case-insensitive filesystem issues
- **Linux**: Follows POSIX filename standards
- **ASCII-only**: Removes Unicode characters for maximum compatibility

## Character Handling

**Allowed characters:**
- Letters (a-z, A-Z)
- Numbers (0-9)
- Underscores (_)
- Hyphens (-)
- Dots (only in extensions)

**Removed characters:**
- Special characters (`@#$%^&*()[]{}`, etc.)
- Spaces (replaced with underscores)
- Unicode characters (removed)
- Reserved filesystem characters

## Migration Notes

This utility replaces the following duplicate implementations:

- `LangFlixPipeline._sanitize_filename()` in `langflix/main.py`
- `VideoEditor._sanitize_filename()` in `langflix/core/video_editor.py`
- `sanitize_expression_for_filename()` in `langflix/subtitles/overlay.py`
- Various inline sanitization logic in `langflix/api/routes/jobs.py`

All existing code has been migrated to use these utilities, ensuring consistent behavior across the codebase.

## Testing

Comprehensive unit tests are available in `tests/unit/test_filename_utils.py`, covering:
- Basic sanitization
- Special character handling
- Length limits
- Extension preservation
- Cross-platform compatibility
- Edge cases (empty strings, Unicode, etc.)

## Related Documentation

- [TempFileManager](./temp_file_manager_eng.md) - Temporary file management
- [Core Video Editor](../core/README_eng.md) - Video editing utilities
- [TICKET-004](../tickets/approved/TICKET-004-consolidate-filename-sanitization.md) - Consolidation ticket

