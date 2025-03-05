import json
import yaml
import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("ConfigUtils")

def load_config(config_path: str) -> Dict[str, Any]:
    """
    Load configuration from a file.
    Supports JSON and YAML formats.
    
    Args:
        config_path: Path to the configuration file
        
    Returns:
        Dict: Configuration dictionary
    """
    if not os.path.exists(config_path):
        logger.error(f"Configuration file not found: {config_path}")
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    try:
        # Determine file format based on extension
        _, ext = os.path.splitext(config_path)
        
        if ext.lower() in ['.yaml', '.yml']:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
        elif ext.lower() == '.json':
            with open(config_path, 'r') as f:
                config = json.load(f)
        else:
            logger.error(f"Unsupported configuration file format: {ext}")
            raise ValueError(f"Unsupported configuration file format: {ext}")
        
        logger.info(f"Configuration loaded from {config_path}")
        return config
    
    except Exception as e:
        logger.error(f"Error loading configuration: {str(e)}")
        raise

def save_config(config: Dict[str, Any], config_path: str) -> None:
    """
    Save configuration to a file.
    
    Args:
        config: Configuration dictionary
        config_path: Path to save the configuration file
    """
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        # Determine file format based on extension
        _, ext = os.path.splitext(config_path)
        
        if ext.lower() in ['.yaml', '.yml']:
            with open(config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)
        elif ext.lower() == '.json':
            with open(config_path, 'w') as f:
                json.dump(config, f, indent=2)
        else:
            logger.error(f"Unsupported configuration file format: {ext}")
            raise ValueError(f"Unsupported configuration file format: {ext}")
        
        logger.info(f"Configuration saved to {config_path}")
    
    except Exception as e:
        logger.error(f"Error saving configuration: {str(e)}")
        raise

def merge_configs(base_config: Dict[str, Any], override_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge two configuration dictionaries, with override_config taking precedence.
    
    Args:
        base_config: Base configuration dictionary
        override_config: Override configuration dictionary
        
    Returns:
        Dict: Merged configuration dictionary
    """
    result = base_config.copy()
    
    for key, value in override_config.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = value
    
    return result

def get_config_value(config: Dict[str, Any], key_path: str, default: Any = None) -> Any:
    """
    Get a value from a nested configuration dictionary using dot notation.
    
    Args:
        config: Configuration dictionary
        key_path: Path to the value using dot notation (e.g., "solana.wallet.keyfile_path")
        default: Default value if the key is not found
        
    Returns:
        Any: Value at the specified path or default if not found
    """
    keys = key_path.split('.')
    result = config
    
    try:
        for key in keys:
            result = result[key]
        return result
    except (KeyError, TypeError):
        return default 