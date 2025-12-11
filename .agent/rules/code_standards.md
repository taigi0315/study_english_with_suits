# Code Standards

> Coding conventions and standards for LangFlix

---

## Language & Communication

| Context | Language |
|---------|----------|
| Code (variables, functions, comments) | English |
| User communication | Korean or English |
| Documentation files | Bilingual (`_eng.md`, `_kor.md`) |

---

## Python Conventions

### Type Hints

All functions must have type hints:

```python
def process_video(
    video_path: Path,
    subtitle_path: Path,
    output_dir: Optional[Path] = None
) -> VideoResult:
    """Process video and return result."""
    pass
```

### Naming

| Element | Convention | Example |
|---------|------------|---------|
| Functions | snake_case | `create_structured_video()` |
| Classes | PascalCase | `ExpressionAnalyzer` |
| Constants | UPPER_SNAKE | `MAX_EXPRESSIONS` |
| Private | _prefix | `_register_temp_file()` |

### Docstrings

```python
def create_structured_video(
    self,
    expression: ExpressionAnalysis,
    video_path: Path
) -> Path:
    """Create structured educational video for expression.
    
    Args:
        expression: Analyzed expression with timing info
        video_path: Path to source video
        
    Returns:
        Path to generated structured video
        
    Raises:
        VideoProcessingError: If FFmpeg operation fails
    """
```

---

## Error Handling

### Use Decorator Pattern

```python
from langflix.core.error_handler import handle_error_decorator, ErrorContext

@handle_error_decorator(
    ErrorContext(
        operation="method_name",
        component="core.module_name"
    ),
    retry=False,  # Video processing should not retry
    fallback=False
)
def method_name(self, ...):
    # Implementation
```

### No Silent Failures

```python
# ❌ BAD
try:
    process_video()
except Exception:
    pass  # Silent failure

# ✅ GOOD
try:
    process_video()
except VideoProcessingError as e:
    logger.error(f"Video processing failed: {e}")
    raise
```

---

## Configuration

### No Hardcoded Values

```python
# ❌ BAD
max_duration = 180
crf = 18

# ✅ GOOD
from langflix import settings
max_duration = settings.get_short_video_max_duration()
crf = settings.video.crf
```

### Configuration Location

| Type | Location |
|------|----------|
| Defaults | `langflix/config/default.yaml` |
| User overrides | `config/config.yaml` |
| Secrets | `.env` file |

---

## Imports

### Order

```python
# 1. Standard library
import os
from pathlib import Path

# 2. Third-party
import ffmpeg
from pydantic import BaseModel

# 3. Local
from langflix.core.models import ExpressionAnalysis
from langflix.services import video_pipeline_service
```
