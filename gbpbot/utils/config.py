"""
Configuration utilities for the GBP Bot application.

This module provides functions to load, validate, and manage configuration settings
for the application. It supports loading configuration from environment variables,
configuration files, and command-line arguments.
"""

import os
import json
import logging
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dotenv import load_dotenv

from gbpbot.utils.exceptions import ConfigurationError

# Configure logging
logger = logging.getLogger(__name__)

# Default configuration paths
DEFAULT_CONFIG_PATHS = [
    "./config.yaml",
    "./config.yml",
    "./config.json",
    "~/.gbpbot/config.yaml",
    "~/.gbpbot/config.yml",
    "~/.gbpbot/config.json",
]

# Required configuration keys for each blockchain
REQUIRED_CONFIG_KEYS = {
    "ethereum": ["rpc_url", "private_key"],
    "solana": ["rpc_url", "private_key"],
    "polygon": ["rpc_url", "private_key"],
    "avalanche": ["rpc_url", "private_key"],
    "arbitrum": ["rpc_url", "private_key"],
}

class Config:
    """Configuration manager for the GBP Bot application."""
    
    def __init__(self, config_path: Optional[str] = None, load_env: bool = True):
        """
        Initialize the configuration manager.
        
        Args:
            config_path: Path to the configuration file
            load_env: Whether to load environment variables
        """
        self.config: Dict[str, Any] = {}
        self.config_path = config_path
        
        # Load environment variables
        if load_env:
            self._load_env()
        
        # Load configuration file
        if config_path:
            self._load_config_file(config_path)
        else:
            self._load_default_config()
    
    def _load_env(self) -> None:
        """Load environment variables."""
        # Load from .env file if it exists
        env_path = os.getenv("GBPBOT_ENV_FILE", ".env")
        if os.path.exists(env_path):
            load_dotenv(env_path)
            logger.info(f"Loaded environment variables from {env_path}")
    
    def _load_config_file(self, config_path: str) -> None:
        """
        Load configuration from a file.
        
        Args:
            config_path: Path to the configuration file
        
        Raises:
            ConfigurationError: If the configuration file cannot be loaded
        """
        path = Path(config_path).expanduser()
        
        if not path.exists():
            raise ConfigurationError(f"Configuration file not found: {path}")
        
        try:
            if path.suffix in ['.yaml', '.yml']:
                with open(path, 'r') as f:
                    self.config = yaml.safe_load(f)
            elif path.suffix == '.json':
                with open(path, 'r') as f:
                    self.config = json.load(f)
            else:
                raise ConfigurationError(f"Unsupported configuration file format: {path.suffix}")
            
            logger.info(f"Loaded configuration from {path}")
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration file: {e}")
    
    def _load_default_config(self) -> None:
        """
        Load configuration from default paths.
        
        Tries to load configuration from the default paths in order.
        """
        for path_str in DEFAULT_CONFIG_PATHS:
            path = Path(path_str).expanduser()
            if path.exists():
                try:
                    self._load_config_file(str(path))
                    return
                except Exception as e:
                    logger.warning(f"Failed to load configuration from {path}: {e}")
        
        logger.warning("No configuration file found, using environment variables only")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.
        
        Args:
            key: Configuration key
            default: Default value if the key is not found
            
        Returns:
            Configuration value
        """
        # First check environment variables
        env_key = f"GBPBOT_{key.upper()}"
        env_value = os.getenv(env_key)
        if env_value is not None:
            return env_value
        
        # Then check configuration file
        keys = key.split('.')
        value = self.config
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """
        Set a configuration value.
        
        Args:
            key: Configuration key
            value: Configuration value
        """
        keys = key.split('.')
        config = self.config
        
        for i, k in enumerate(keys[:-1]):
            if k not in config:
                config[k] = {}
            elif not isinstance(config[k], dict):
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def get_blockchain_config(self, blockchain_type: str) -> Dict[str, Any]:
        """
        Get configuration for a specific blockchain.
        
        Args:
            blockchain_type: Type of blockchain (ethereum, solana, etc.)
            
        Returns:
            Configuration for the specified blockchain
            
        Raises:
            ConfigurationError: If the blockchain configuration is invalid
        """
        blockchain_type = blockchain_type.lower()
        
        # Get blockchain configuration from config file
        blockchain_config = self.get(f"blockchains.{blockchain_type}", {})
        
        # Override with environment variables
        for key in REQUIRED_CONFIG_KEYS.get(blockchain_type, []):
            env_key = f"GBPBOT_{blockchain_type.upper()}_{key.upper()}"
            env_value = os.getenv(env_key)
            if env_value is not None:
                blockchain_config[key] = env_value
        
        # Validate configuration
        self._validate_blockchain_config(blockchain_type, blockchain_config)
        
        return blockchain_config
    
    def _validate_blockchain_config(self, blockchain_type: str, config: Dict[str, Any]) -> None:
        """
        Validate blockchain configuration.
        
        Args:
            blockchain_type: Type of blockchain
            config: Blockchain configuration
            
        Raises:
            ConfigurationError: If the configuration is invalid
        """
        if blockchain_type not in REQUIRED_CONFIG_KEYS:
            raise ConfigurationError(f"Unsupported blockchain type: {blockchain_type}")
        
        missing_keys = []
        for key in REQUIRED_CONFIG_KEYS[blockchain_type]:
            if key not in config or not config[key]:
                missing_keys.append(key)
        
        if missing_keys:
            raise ConfigurationError(
                f"Missing required configuration for {blockchain_type}: {', '.join(missing_keys)}"
            )
    
    def save(self, config_path: Optional[str] = None) -> None:
        """
        Save configuration to a file.
        
        Args:
            config_path: Path to save the configuration file
            
        Raises:
            ConfigurationError: If the configuration cannot be saved
        """
        path = Path(config_path or self.config_path or DEFAULT_CONFIG_PATHS[0]).expanduser()
        
        try:
            # Create directory if it doesn't exist
            path.parent.mkdir(parents=True, exist_ok=True)
            
            if path.suffix in ['.yaml', '.yml']:
                with open(path, 'w') as f:
                    yaml.dump(self.config, f, default_flow_style=False)
            elif path.suffix == '.json':
                with open(path, 'w') as f:
                    json.dump(self.config, f, indent=2)
            else:
                raise ConfigurationError(f"Unsupported configuration file format: {path.suffix}")
            
            logger.info(f"Saved configuration to {path}")
        except Exception as e:
            raise ConfigurationError(f"Failed to save configuration: {e}")
    
    def get_supported_blockchains(self) -> List[str]:
        """
        Get a list of supported blockchains.
        
        Returns:
            List of supported blockchain types
        """
        return list(REQUIRED_CONFIG_KEYS.keys())
    
    def is_blockchain_configured(self, blockchain_type: str) -> bool:
        """
        Check if a blockchain is configured.
        
        Args:
            blockchain_type: Type of blockchain
            
        Returns:
            True if the blockchain is configured, False otherwise
        """
        try:
            self.get_blockchain_config(blockchain_type)
            return True
        except ConfigurationError:
            return False


# Global configuration instance
_config_instance = None

def get_config(config_path: Optional[str] = None, load_env: bool = True) -> Config:
    """
    Get the global configuration instance.
    
    Args:
        config_path: Path to the configuration file
        load_env: Whether to load environment variables
        
    Returns:
        Global configuration instance
    """
    global _config_instance
    
    if _config_instance is None or config_path is not None:
        _config_instance = Config(config_path, load_env)
    
    return _config_instance 