# ADR-002: YAML-based Configuration Management

**Date:** 2025-10-19  
**Status:** Accepted  
**Deciders:** Development Team  

## Context

LangFlix requires extensive configuration for various aspects of the application:
- LLM parameters (temperature, max tokens, retry settings)
- Video processing settings (codecs, quality, resolution)
- Language-specific settings (target languages, proficiency levels)
- Processing parameters (chunk sizes, expression limits)

Initially, configuration was managed through a mix of hardcoded values scattered throughout the codebase and some environment variables. This approach led to several issues:

1. **Inconsistency**: Settings were defined in multiple places with no central source of truth
2. **Maintainability**: Changes required modifying source code and recompiling
3. **Deployment**: Different environments (dev, staging, prod) required code changes
4. **Documentation**: No clear way to document all available configuration options
5. **Validation**: No centralized validation of configuration values

## Decision

We will implement a centralized YAML-based configuration management system.

### Implementation

1. **Default Configuration**: Create `langflix/config/default.yaml` as the single source of truth for all configuration
2. **Configuration Loader**: Implement `ConfigLoader` class for loading and merging configurations
3. **Settings Module**: Update `langflix/settings.py` to use the configuration loader
4. **Environment Override**: Support for configuration override via environment variables when needed

### Configuration Structure

```yaml
# langflix/config/default.yaml
llm:
  max_input_length: 1680
  default_language_level: "intermediate"
  target_language: "Korean"
  max_retries: 3
  retry_backoff_seconds: [3, 6, 12]
  temperature: 0.1
  top_p: 0.8
  top_k: 40

language_levels:
  beginner:
    description: "A1-A2 level. Focus on basic everyday expressions..."
  intermediate:
    description: "B1-B2 level. Focus on commonly used idiomatic expressions..."
  advanced:
    description: "C1-C2 level. Focus on sophisticated idioms..."

video:
  codec: "libx264"
  preset: "fast"
  crf: 23
  resolution: "1280x720"

processing:
  min_expressions_per_chunk: 1
  max_expressions_per_chunk: 3
```

### Configuration Loader Implementation

```python
# langflix/config/config_loader.py
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

class ConfigLoader:
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or self._find_config_file()
        self._config = self._load_config()
    
    def _find_config_file(self) -> Path:
        """Find configuration file in order of precedence."""
        possible_paths = [
            Path("config.yaml"),  # Project root override
            Path(__file__).parent / "default.yaml"  # Default
        ]
        
        for path in possible_paths:
            if path.exists():
                return path
        
        raise FileNotFoundError("No configuration file found")
    
    def _load_config(self) -> Dict[str, Any]:
        """Load YAML configuration."""
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation."""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value

# Global instance
config_loader = ConfigLoader()
```

### Settings Module Integration

```python
# langflix/settings.py
from .config.config_loader import config_loader

# LLM Configuration
llm_config = config_loader.get('llm', {})
MAX_LLM_INPUT_LENGTH = llm_config.get('max_input_length', 4000)
DEFAULT_LANGUAGE_LEVEL = llm_config.get('default_language_level', "intermediate")

def get_generation_config() -> Dict[str, Any]:
    """Get LLM generation configuration from YAML."""
    return {
        'temperature': llm_config.get('temperature', 0.1),
        'top_p': llm_config.get('top_p', 0.8),
        'top_k': llm_config.get('top_k', 40)
    }

def get_min_expressions_per_chunk() -> int:
    """Get minimum expressions per chunk from config."""
    processing_config = config_loader.get('processing', {})
    return processing_config.get('min_expressions_per_chunk', 1)

# ... other configuration getters
```

## Consequences

### Positive

1. **Centralized Configuration**: All settings in one place with clear structure
2. **Environment Flexibility**: Easy override for different deployment environments
3. **Documentation**: YAML serves as living documentation of available options
4. **Type Safety**: Configuration loading with proper error handling and defaults
5. **Maintainability**: Changes don't require code modifications
6. **Validation**: Centralized validation of configuration values

### Negative

1. **Runtime Dependency**: Application depends on configuration files being present
2. **Additional Complexity**: More code to manage configuration loading
3. **Error Handling**: Need to handle missing/invalid configuration gracefully

### Risks

1. **Configuration File Missing**: Application startup failure
   - **Mitigation**: Fallback to default values and clear error messages

2. **Invalid YAML**: Malformed configuration causing crashes
   - **Mitigation**: YAML parsing error handling with helpful messages

3. **Performance**: Configuration loading on every startup
   - **Mitigation**: Cache loaded configuration in memory

## Alternatives Considered

1. **JSON Configuration**: 
   - **Rejected**: YAML is more readable for complex nested structures

2. **Environment Variables Only**:
   - **Rejected**: Too many variables, difficult to manage

3. **INI/TOML Files**:
   - **Rejected**: YAML provides better structure for nested configurations

4. **Configuration Classes with Pydantic**:
   - **Deferred**: Could be added later for validation, YAML loader is sufficient for now

## Implementation Details

- **Default Configuration**: `langflix/config/default.yaml`
- **Override Support**: `config.yaml` in project root takes precedence
- **API**: Functions in `settings.py` provide typed access to configuration
- **Error Handling**: Graceful fallbacks to sensible defaults
- **Documentation**: Configuration is self-documenting through YAML comments

This decision establishes a solid foundation for configuration management that scales with the application's complexity while remaining simple and maintainable.
