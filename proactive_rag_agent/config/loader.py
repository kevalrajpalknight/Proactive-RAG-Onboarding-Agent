"""Configuration loading and saving utilities."""

import os
import yaml
import json
from pathlib import Path
from typing import Dict, Any, Optional

from .settings import AgentConfig


def load_config(
    config_path: Optional[str] = None,
    config_dict: Optional[Dict[str, Any]] = None
) -> AgentConfig:
    """
    Load configuration from file or dictionary.
    
    Args:
        config_path: Path to configuration file (YAML or JSON)
        config_dict: Configuration dictionary
        
    Returns:
        Loaded configuration
        
    Raises:
        FileNotFoundError: If config file doesn't exist
        ValueError: If configuration is invalid
    """
    
    if config_dict:
        return AgentConfig(**config_dict)
    
    if not config_path:
        # Try default locations
        default_paths = [
            "config.yaml",
            "config.yml", 
            "config.json",
            "proactive_rag_config.yaml",
            "proactive_rag_config.yml",
            "proactive_rag_config.json"
        ]
        
        for path in default_paths:
            if os.path.exists(path):
                config_path = path
                break
        
        if not config_path:
            # Return default configuration
            return AgentConfig()
    
    config_path = Path(config_path)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    # Load configuration based on file extension
    with open(config_path, 'r', encoding='utf-8') as f:
        if config_path.suffix.lower() in ['.yaml', '.yml']:
            config_data = yaml.safe_load(f)
        elif config_path.suffix.lower() == '.json':
            config_data = json.load(f)
        else:
            raise ValueError(f"Unsupported configuration format: {config_path.suffix}")
    
    if not config_data:
        config_data = {}
    
    try:
        return AgentConfig(**config_data)
    except Exception as e:
        raise ValueError(f"Invalid configuration: {e}")


def save_config(
    config: AgentConfig,
    config_path: str,
    format: str = "yaml",
    include_defaults: bool = False
) -> None:
    """
    Save configuration to file.
    
    Args:
        config: Configuration to save
        config_path: Path to save configuration file
        format: File format ('yaml' or 'json')
        include_defaults: Whether to include default values
        
    Raises:
        ValueError: If format is not supported
    """
    
    config_path = Path(config_path)
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert to dictionary
    if include_defaults:
        config_dict = config.dict()
    else:
        config_dict = config.dict(exclude_defaults=True)
    
    # Remove sensitive information
    config_dict = _sanitize_config(config_dict)
    
    # Save configuration
    with open(config_path, 'w', encoding='utf-8') as f:
        if format.lower() == "yaml":
            yaml.dump(
                config_dict, 
                f, 
                default_flow_style=False,
                indent=2,
                sort_keys=True
            )
        elif format.lower() == "json":
            json.dump(
                config_dict, 
                f, 
                indent=2,
                sort_keys=True,
                ensure_ascii=False
            )
        else:
            raise ValueError(f"Unsupported format: {format}")


def _sanitize_config(config_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Remove sensitive information from configuration."""
    
    sanitized = config_dict.copy()
    
    # Remove API keys and other sensitive data
    sensitive_keys = [
        "api_key",
        "password", 
        "secret",
        "token",
        "key"
    ]
    
    def remove_sensitive(obj, path=""):
        if isinstance(obj, dict):
            result = {}
            for key, value in obj.items():
                current_path = f"{path}.{key}" if path else key
                
                # Check if key contains sensitive information
                if any(sensitive in key.lower() for sensitive in sensitive_keys):
                    if value:  # Only mask if value exists
                        result[key] = "***MASKED***"
                    else:
                        result[key] = value
                else:
                    result[key] = remove_sensitive(value, current_path)
            return result
        elif isinstance(obj, list):
            return [remove_sensitive(item, f"{path}[{i}]") for i, item in enumerate(obj)]
        else:
            return obj
    
    return remove_sensitive(sanitized)


def create_example_config(output_path: str = "config.example.yaml") -> None:
    """Create an example configuration file."""
    
    example_config = AgentConfig()
    
    # Add some example values
    example_config.llm.api_key = "your-openai-api-key-here"
    example_config.documents_path = "./data/documents"
    example_config.index_path = "./data/indices"
    
    save_config(
        example_config,
        output_path,
        format="yaml",
        include_defaults=True
    )
    
    print(f"Example configuration saved to: {output_path}")


def validate_config_file(config_path: str) -> Dict[str, Any]:
    """
    Validate a configuration file and return validation results.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Dictionary with validation results
    """
    
    try:
        config = load_config(config_path)
        issues = config.validate_config()
        
        return {
            'valid': len(issues['errors']) == 0,
            'config': config,
            'issues': issues
        }
    
    except Exception as e:
        return {
            'valid': False,
            'config': None,
            'issues': {
                'errors': [str(e)],
                'warnings': []
            }
        }