# Configuration Module Documentation

## Overview

The `langflix/config/` module provides configuration management for LangFlix, handling YAML configuration files with environment variable overrides and expression-based learning settings.

**Last Updated:** 2025-01-30

## Purpose

This module is responsible for:
- Loading and merging configuration from multiple sources
- Managing expression-based learning configuration
- Providing font utilities for platform-specific font detection
- Handling configuration cascading (default → user → environment)

## Key Components

### ConfigLoader

**Location:** `langflix/config/config_loader.py`

Manages configuration loading with cascading priority:
1. Default configuration (`langflix/config/default.yaml`)
2. User configuration (`config.yaml` at project root)
3. Environment variable overrides (`LANGFLIX_SECTION_KEY` format)

**Key Methods:**

```python
def get(self, *keys, default: Any = None) -> Any:
    """
    Get configuration value using dot notation or multiple keys.
    
    Examples:
        config.get('llm', 'max_input_length')
        config.get('llm.max_input_length')
        config.get('video', 'codec', default='libx264')
    """
```

```python
def get_section(self, section: str) -> Dict[str, Any]:
    """Get entire configuration section."""
```

**Environment Variable Overrides:**

Environment variables should be in format: `LANGFLIX_SECTION_KEY`

Example: `LANGFLIX_LLM_MAX_INPUT_LENGTH=5000`

The loader automatically:
- Parses nested keys (e.g., `LANGFLIX_LLM_MAX_INPUT_LENGTH`)
- Converts string values to appropriate types (int, float, bool)
- Merges with existing configuration

**Example Usage:**

```python
from langflix.config.config_loader import ConfigLoader

loader = ConfigLoader()
max_length = loader.get('llm', 'max_input_length', default=4000)
llm_config = loader.get_section('llm')
```

### ExpressionConfig

**Location:** `langflix/config/expression_config.py`

Dataclass-based configuration for expression-based learning features.

**Configuration Classes:**

```python
@dataclass
class SubtitleStylingConfig:
    """Subtitle styling configuration for expressions"""
    default: Dict[str, Any]
    expression_highlight: Dict[str, Any]
```

```python
@dataclass
class PlaybackConfig:
    """Video playback configuration for expressions"""
    expression_repeat_count: int = 2
    context_play_count: int = 1
    repeat_delay_ms: int = 200
    transition_effect: str = 'fade'
    transition_duration_ms: int = 150
```

```python
@dataclass
class LayoutConfig:
    """Layout configuration for different video formats"""
    landscape: Dict[str, Any]
    portrait: Dict[str, Any]
```

**Example Usage:**

```python
from langflix.config.expression_config import ExpressionConfig

config_dict = {
    'subtitle_styling': {...},
    'playback': {'expression_repeat_count': 3},
    'layout': {...}
}

expr_config = ExpressionConfig.from_dict(config_dict)
repeat_count = expr_config.playback.expression_repeat_count
```

### FontUtils

**Location:** `langflix/config/font_utils.py`

Platform-specific font detection and selection utilities.

**Key Functions:**

```python
def get_platform_default_font() -> str:
    """
    Get appropriate default font based on platform.
    
    Returns:
        Path to platform-specific default font, or empty string if not found
        
    Supported platforms:
    - macOS: /System/Library/Fonts/AppleSDGothicNeo.ttc
    - Linux: Tries common Korean fonts (NanumGothic, DejaVuSans, NotoSansCJK)
    - Windows: Tries Malgun Gothic, Arial
    """
```

```python
def get_font_file_for_language(language_code: Optional[str] = None) -> str:
    """
    Get font file path for the given language or default.
    
    Args:
        language_code: Optional language code (e.g., 'ko', 'ja', 'zh', 'es')
        
    Returns:
        Path to appropriate font file
    """
```

**Example Usage:**

```python
from langflix.config.font_utils import get_font_file_for_language

font_path = get_font_file_for_language('ko')
# Returns platform-specific Korean font path

default_font = get_font_file_for_language()
# Returns platform default font
```

## Configuration Structure

### Default Configuration (`default.yaml`)

The default configuration includes:

```yaml
expression:
  subtitle_styling:
    default:
      color: '#FFFFFF'
      font_size: 24
      font_weight: 'normal'
      background_color: '#000000'
    expression_highlight:
      color: '#FFD700'
      font_size: 28
      font_weight: 'bold'
      
  playback:
    expression_repeat_count: 2
    context_play_count: 1
    repeat_delay_ms: 200
    
  layout:
    landscape:
      resolution: [1920, 1080]
      expression_video:
        width_percent: 50
    portrait:
      resolution: [1080, 1920]
      context_video:
        height_percent: 75

llm:
  max_input_length: 4000
  temperature: 0.7
```

## Implementation Details

### Configuration Merging

The `ConfigLoader` uses recursive dictionary merging:

1. **Base Config**: Load from `default.yaml`
2. **User Override**: Merge user `config.yaml` (if exists)
3. **Environment Override**: Apply environment variables with `LANGFLIX_` prefix

Nested dictionaries are merged recursively, while simple values are replaced.

### Environment Variable Parsing

Environment variables are parsed as follows:

1. Remove `LANGFLIX_` prefix
2. Split remaining by `_` to get section path
3. Navigate to nested section
4. Set final key value
5. Auto-convert types (int, float, bool, string)

Example: `LANGFLIX_LLM_MAX_INPUT_LENGTH=5000`
- Becomes: `config['llm']['max_input_length'] = 5000`

### Font Detection

Font detection works by:
1. Checking platform-specific font locations
2. Verifying file existence
3. Falling back to system defaults
4. For language-specific fonts, checking `LanguageConfig` module

## Dependencies

- `yaml`: YAML file parsing
- `pathlib`: Path handling
- `os`: Environment variable access
- `platform`: Platform detection
- `langflix.core.language_config`: Language-specific font configuration

## Common Tasks

### Load Configuration

```python
from langflix.config.config_loader import ConfigLoader

loader = ConfigLoader(user_config_path="custom_config.yaml")
value = loader.get('section', 'key', default='default_value')
```

### Override with Environment Variables

```bash
# Set environment variable
export LANGFLIX_LLM_MAX_INPUT_LENGTH=6000

# Configuration will use this value
python your_script.py
```

### Get Expression Configuration

```python
from langflix.config.expression_config import ExpressionConfig

# Load from ConfigLoader
loader = ConfigLoader()
expr_config_dict = loader.get_section('expression')

# Create ExpressionConfig object
expr_config = ExpressionConfig.from_dict(expr_config_dict)
repeat_count = expr_config.playback.expression_repeat_count
```

### Get Font Path

```python
from langflix.config.font_utils import get_font_file_for_language

# Get language-specific font
font_path = get_font_file_for_language('ko')

# Or platform default
default_font = get_font_file_for_language()
```

### Save User Configuration

```python
loader = ConfigLoader()
config = loader.config.copy()
config['llm']['max_input_length'] = 5000
loader.save_user_config(config)
```

## Configuration Files

### Project Structure

```
project_root/
├── config.yaml              # User configuration (optional)
├── langflix/
│   └── config/
│       ├── default.yaml     # Default configuration
│       ├── config_loader.py
│       ├── expression_config.py
│       └── font_utils.py
```

### Configuration Precedence

1. **Environment Variables** (Highest priority)
2. **User Config** (`config.yaml`)
3. **Default Config** (`default.yaml`) (Lowest priority)

## Gotchas and Notes

1. **Environment Variable Format**: Must start with `LANGFLIX_` prefix
2. **Type Conversion**: Environment variables are auto-converted (int, float, bool)
3. **Nested Keys**: Use underscores to separate nested sections (`LANGFLIX_SECTION_SUBSECTION_KEY`)
4. **Font Paths**: Font utilities return empty string if font not found - check before use
5. **Configuration Reload**: Call `loader.reload()` to reload configuration from files
6. **Platform Fonts**: Font detection varies by platform - may return empty string on some systems

## Related Modules

- `langflix.settings`: Global settings wrapper around ConfigLoader
- `langflix.core.language_config`: Language-specific font configuration
- `langflix/core/`: Uses configuration for video processing

