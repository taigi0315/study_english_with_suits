"""
Configuration module for LangFlix

Provides YAML-based configuration management with cascading configs:
1. Default configuration (default.yaml)
2. User configuration (config.yaml at root)
3. Environment variable overrides
"""

from .config_loader import ConfigLoader

__all__ = ['ConfigLoader']

