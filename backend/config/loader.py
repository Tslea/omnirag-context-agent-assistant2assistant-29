"""
Configuration Loader

Handles YAML loading with environment variable substitution.
"""

import os
import re
from pathlib import Path
from typing import Any, Optional

import yaml


class ConfigLoader:
    """
    Loads configuration from YAML files with environment variable support.
    
    Features:
    - Environment variable substitution: ${VAR_NAME}
    - Default values: ${VAR_NAME:default}
    - Includes: !include other_file.yaml
    - Multiple config file merging
    
    Example:
        ```python
        loader = ConfigLoader()
        config = loader.load_yaml("config.yaml")
        
        # Or merge multiple files
        config = loader.load_multiple([
            "default.yaml",
            "local.yaml",
        ])
        ```
    """
    
    # Pattern for environment variable substitution
    ENV_PATTERN = re.compile(r'\$\{([^}:]+)(?::([^}]*))?\}')
    
    def __init__(self, base_path: Optional[str] = None):
        """
        Initialize the config loader.
        
        Args:
            base_path: Base directory for relative paths
        """
        self.base_path = Path(base_path) if base_path else Path.cwd()
    
    def load_yaml(self, path: str) -> dict[str, Any]:
        """
        Load a YAML configuration file.
        
        Args:
            path: Path to YAML file
            
        Returns:
            Parsed configuration dictionary
        """
        file_path = self._resolve_path(path)
        
        if not file_path.exists():
            raise FileNotFoundError(f"Config file not found: {file_path}")
        
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Substitute environment variables
        content = self._substitute_env_vars(content)
        
        # Parse YAML
        data = yaml.safe_load(content) or {}
        
        # Process includes
        data = self._process_includes(data, file_path.parent)
        
        return data
    
    def load_multiple(self, paths: list[str]) -> dict[str, Any]:
        """
        Load and merge multiple configuration files.
        
        Later files override earlier ones.
        
        Args:
            paths: List of config file paths
            
        Returns:
            Merged configuration dictionary
        """
        merged: dict[str, Any] = {}
        
        for path in paths:
            try:
                config = self.load_yaml(path)
                merged = self._deep_merge(merged, config)
            except FileNotFoundError:
                continue  # Skip missing files
        
        return merged
    
    def _resolve_path(self, path: str) -> Path:
        """Resolve a path relative to base_path."""
        p = Path(path)
        if p.is_absolute():
            return p
        return self.base_path / p
    
    def _substitute_env_vars(self, content: str) -> str:
        """
        Substitute environment variables in content.
        
        Supports:
        - ${VAR_NAME} - required variable
        - ${VAR_NAME:default} - variable with default
        """
        def replace(match):
            var_name = match.group(1)
            default = match.group(2)
            
            value = os.getenv(var_name)
            
            if value is not None:
                return value
            elif default is not None:
                return default
            else:
                # Return empty string for missing variables
                return ""
        
        return self.ENV_PATTERN.sub(replace, content)
    
    def _process_includes(
        self,
        data: dict[str, Any],
        base_dir: Path,
    ) -> dict[str, Any]:
        """
        Process !include directives in the config.
        
        Supports including other YAML files.
        """
        if not isinstance(data, dict):
            return data
        
        result = {}
        
        for key, value in data.items():
            if isinstance(value, str) and value.startswith("!include "):
                # Include another file
                include_path = base_dir / value[9:].strip()
                if include_path.exists():
                    with open(include_path, 'r') as f:
                        content = f.read()
                    content = self._substitute_env_vars(content)
                    result[key] = yaml.safe_load(content)
                else:
                    result[key] = None
            elif isinstance(value, dict):
                result[key] = self._process_includes(value, base_dir)
            elif isinstance(value, list):
                result[key] = [
                    self._process_includes(item, base_dir) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                result[key] = value
        
        return result
    
    def _deep_merge(
        self,
        base: dict[str, Any],
        override: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Deep merge two dictionaries.
        
        Override values take precedence.
        """
        result = base.copy()
        
        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def save_yaml(self, data: dict[str, Any], path: str) -> None:
        """
        Save configuration to a YAML file.
        
        Args:
            data: Configuration dictionary
            path: Output path
        """
        file_path = self._resolve_path(path)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(file_path, 'w') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
    
    def validate_config(self, config: dict[str, Any]) -> list[str]:
        """
        Validate configuration and return list of issues.
        
        Args:
            config: Configuration to validate
            
        Returns:
            List of validation error messages
        """
        errors = []
        
        # Check required sections
        required_sections = ["server", "llm"]
        for section in required_sections:
            if section not in config:
                errors.append(f"Missing required section: {section}")
        
        # Validate LLM config
        if "llm" in config:
            llm = config["llm"]
            provider = llm.get("provider", "openai")
            
            if provider == "openai" and not llm.get("openai", {}).get("api_key"):
                if not os.getenv("OPENAI_API_KEY"):
                    errors.append("OpenAI API key not configured")
            
            elif provider == "anthropic" and not llm.get("anthropic", {}).get("api_key"):
                if not os.getenv("ANTHROPIC_API_KEY"):
                    errors.append("Anthropic API key not configured")
        
        return errors


def get_config_loader(base_path: Optional[str] = None) -> ConfigLoader:
    """Get a ConfigLoader instance."""
    return ConfigLoader(base_path)
