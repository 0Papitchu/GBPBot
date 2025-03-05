"""
Environment utilities for checking dependencies and system requirements.

This module provides functions to check if all required dependencies are installed
and properly configured for the different blockchain clients supported by the bot.
"""

import importlib
import logging
import sys
import platform
from typing import Dict, List, Optional, Set, Tuple

# Configure logging
logger = logging.getLogger(__name__)

# Define dependency groups
CORE_DEPENDENCIES = [
    "aiohttp",
    "pydantic",
    "python-dotenv",
]

ETHEREUM_DEPENDENCIES = [
    "web3",
    "eth_account",
    "eth_typing",
]

SOLANA_DEPENDENCIES = [
    "solana",
    "solders",
    "anchorpy",
]

POLYGON_DEPENDENCIES = [
    "web3",  # Shares with Ethereum
]

AVALANCHE_DEPENDENCIES = [
    "web3",  # Shares with Ethereum
]

ARBITRUM_DEPENDENCIES = [
    "web3",  # Shares with Ethereum
]

ALL_DEPENDENCIES = list(set(
    CORE_DEPENDENCIES +
    ETHEREUM_DEPENDENCIES +
    SOLANA_DEPENDENCIES +
    POLYGON_DEPENDENCIES +
    AVALANCHE_DEPENDENCIES +
    ARBITRUM_DEPENDENCIES
))

def check_dependency(package_name: str) -> Tuple[bool, Optional[str]]:
    """
    Check if a dependency is installed and return its version.
    
    Args:
        package_name: Name of the package to check
        
    Returns:
        Tuple of (is_installed, version)
    """
    try:
        module = importlib.import_module(package_name)
        version = getattr(module, "__version__", "unknown")
        return True, version
    except ImportError:
        return False, None
    except Exception as e:
        logger.warning(f"Error checking {package_name}: {str(e)}")
        return False, None

def check_dependencies(dependencies: List[str]) -> Dict[str, Dict[str, str]]:
    """
    Check a list of dependencies and return their status.
    
    Args:
        dependencies: List of package names to check
        
    Returns:
        Dictionary with package status information
    """
    results = {}
    for package in dependencies:
        installed, version = check_dependency(package)
        results[package] = {
            "installed": installed,
            "version": version if installed else "not installed"
        }
    return results

def check_system_info() -> Dict[str, str]:
    """
    Get system information.
    
    Returns:
        Dictionary with system information
    """
    return {
        "python_version": sys.version,
        "platform": platform.platform(),
        "architecture": platform.architecture()[0],
        "processor": platform.processor(),
    }

def check_blockchain_dependencies(blockchain_type: str) -> Dict[str, Dict[str, str]]:
    """
    Check dependencies for a specific blockchain.
    
    Args:
        blockchain_type: Type of blockchain (ethereum, solana, etc.)
        
    Returns:
        Dictionary with dependency status for the specified blockchain
    """
    blockchain_type = blockchain_type.lower()
    
    if blockchain_type == "ethereum":
        return check_dependencies(ETHEREUM_DEPENDENCIES)
    elif blockchain_type == "solana":
        return check_dependencies(SOLANA_DEPENDENCIES)
    elif blockchain_type == "polygon":
        return check_dependencies(POLYGON_DEPENDENCIES)
    elif blockchain_type == "avalanche":
        return check_dependencies(AVALANCHE_DEPENDENCIES)
    elif blockchain_type == "arbitrum":
        return check_dependencies(ARBITRUM_DEPENDENCIES)
    elif blockchain_type == "all":
        return check_dependencies(ALL_DEPENDENCIES)
    else:
        logger.warning(f"Unknown blockchain type: {blockchain_type}")
        return {}

def get_missing_dependencies(blockchain_type: str) -> List[str]:
    """
    Get a list of missing dependencies for a specific blockchain.
    
    Args:
        blockchain_type: Type of blockchain (ethereum, solana, etc.)
        
    Returns:
        List of missing dependency names
    """
    deps = check_blockchain_dependencies(blockchain_type)
    return [pkg for pkg, info in deps.items() if not info["installed"]]

def check_environment_ready(blockchain_type: str) -> Tuple[bool, List[str]]:
    """
    Check if the environment is ready for a specific blockchain.
    
    Args:
        blockchain_type: Type of blockchain (ethereum, solana, etc.)
        
    Returns:
        Tuple of (is_ready, missing_dependencies)
    """
    missing = get_missing_dependencies(blockchain_type)
    return len(missing) == 0, missing

def print_environment_report() -> None:
    """
    Print a complete environment report to the console.
    """
    system_info = check_system_info()
    all_deps = check_dependencies(ALL_DEPENDENCIES)
    
    print("\n=== System Information ===")
    for key, value in system_info.items():
        print(f"{key}: {value}")
    
    print("\n=== Dependency Status ===")
    for package, info in all_deps.items():
        status = "✓" if info["installed"] else "✗"
        version = info["version"]
        print(f"{status} {package}: {version}")
    
    print("\n=== Blockchain Support ===")
    blockchains = ["ethereum", "solana", "polygon", "avalanche", "arbitrum"]
    for blockchain in blockchains:
        ready, missing = check_environment_ready(blockchain)
        status = "Ready" if ready else f"Missing: {', '.join(missing)}"
        print(f"{blockchain}: {status}")
    
    print("\n")

if __name__ == "__main__":
    print_environment_report() 