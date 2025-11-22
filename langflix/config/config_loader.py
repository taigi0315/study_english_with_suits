"""
Configuration loader for LangFlix

Handles loading and merging of YAML configuration files with environment variable overrides.
"""

import os
import yaml
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union, List

logger = logging.getLogger(__name__)


class ConfigLoader:
    """
    Loads and manages configuration from YAML files with cascading priority:
    1. Default configuration (langflix/config/default.yaml)
    2. User configuration (config.yaml at project root)
    3. Environment variable overrides (LANGFLIX_SECTION_KEY format)
    """
    
    def __init__(self, user_config_path: Optional[str] = None):
        """
        Initialize configuration loader
        
        Args:
            user_config_path: Path to user config file (default: config.yaml at project root)
        """
        # Get paths
        self.package_dir = Path(__file__).parent
        self.default_config_path = self.package_dir / "default.yaml"
        
        # User config in config/ directory
        if user_config_path:
            self.user_config_path = Path(user_config_path)
        else:
            # Go up two levels from langflix/config/ to project root, then into config/
            project_root = self.package_dir.parent.parent
            self.user_config_path = project_root / "config" / "config.yaml"
        
        # Load configuration
        self.config = self._load_config()
    
    def _load_yaml(self, file_path: Path) -> Dict[str, Any]:
        """Load YAML file and return as dictionary"""
        try:
            if not file_path.exists():
                logger.debug(f"Config file not found: {file_path}")
                return {}
            
            with open(file_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                if config is None:
                    return {}
                return config
        except Exception as e:
            logger.warning(f"Error loading config from {file_path}: {e}")
            return {}
    
    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively merge two configuration dictionaries
        
        Args:
            base: Base configuration
            override: Configuration to merge on top
            
        Returns:
            Merged configuration
        """
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # Recursively merge nested dictionaries
                result[key] = self._merge_configs(result[key], value)
            else:
                # Override value
                result[key] = value
        
        return result
    
    def _apply_env_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply environment variable overrides to configuration
        
        Environment variables should be in format: LANGFLIX_SECTION_KEY
        Example: LANGFLIX_LLM_MAX_INPUT_LENGTH=5000
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Configuration with environment overrides applied
        """
        result = config.copy()
        
        # Check for environment variables with LANGFLIX_ prefix
        for env_key, env_value in os.environ.items():
            if not env_key.startswith('LANGFLIX_'):
                continue
            
            # Parse environment variable
            # Format: LANGFLIX_SECTION_KEY or LANGFLIX_SECTION_SUBSECTION_KEY
            parts = env_key[9:].lower().split('_')  # Remove LANGFLIX_ prefix
            
            if len(parts) < 2:
                continue
            
            # Navigate to the correct section
            current = result
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                elif not isinstance(current[part], dict):
                    # Can't override non-dict value with nested structure
                    break
                current = current[part]
            else:
                # Set the value (try to parse as int, float, bool, or keep as string)
                key = parts[-1]
                try:
                    # Try to parse as number
                    if '.' in env_value:
                        current[key] = float(env_value)
                    else:
                        current[key] = int(env_value)
                except ValueError:
                    # Try to parse as boolean
                    if env_value.lower() in ('true', 'yes', '1'):
                        current[key] = True
                    elif env_value.lower() in ('false', 'no', '0'):
                        current[key] = False
                    else:
                        # Keep as string
                        current[key] = env_value
                
                logger.debug(f"Applied env override: {env_key} = {env_value}")
        
        return result
    
    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration with cascading priority
        
        Returns:
            Merged configuration dictionary
        """
        # Start with default configuration
        logger.debug(f"Loading default config from: {self.default_config_path}")
        config = self._load_yaml(self.default_config_path)
        
        # Merge user configuration if it exists
        if self.user_config_path.exists():
            logger.info(f"Loading user config from: {self.user_config_path}")
            user_config = self._load_yaml(self.user_config_path)
            config = self._merge_configs(config, user_config)
        else:
            logger.debug(f"No user config found at: {self.user_config_path}")
        
        # Apply environment variable overrides
        config = self._apply_env_overrides(config)
        
        return config
    
    def get(self, *keys, default: Any = None) -> Any:
        """
        Get configuration value using dot notation or multiple keys
        
        Args:
            *keys: Configuration keys (e.g., 'llm', 'max_input_length' or 'llm.max_input_length')
            default: Default value if key not found
            
        Returns:
            Configuration value or default
            
        Examples:
            config.get('llm', 'max_input_length')
            config.get('llm.max_input_length')
            config.get('video', 'codec', default='libx264')
        """
        # If single key with dots, split it
        if len(keys) == 1 and isinstance(keys[0], str) and '.' in keys[0]:
            keys = keys[0].split('.')
        
        current = self.config
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        
        return current
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """
        Get entire configuration section
        
        Args:
            section: Section name (e.g., 'llm', 'video')
            
        Returns:
            Section dictionary or empty dict if not found
        """
        return self.get(section, default={})
    
    def save_user_config(self, config: Dict[str, Any]) -> None:
        """
        Save user configuration to file
        
        Args:
            config: Configuration dictionary to save
        """
        try:
            self.user_config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.user_config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
            
            logger.info(f"User configuration saved to: {self.user_config_path}")
        except Exception as e:
            logger.error(f"Failed to save user configuration: {e}")
            raise
    
    def reload(self) -> None:
        """Reload configuration from files"""
        self.config = self._load_config()
        logger.info("Configuration reloaded")
    
    def __repr__(self) -> str:
        return f"ConfigLoader(default={self.default_config_path}, user={self.user_config_path})"

