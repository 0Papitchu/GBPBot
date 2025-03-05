"""
Environment checker utility for the GBPBot application.

This script checks if all required dependencies are installed and
provides guidance on how to install missing packages.
"""
import sys
import importlib.util
from typing import Dict, List, Tuple, Optional

# Define required packages with their versions
REQUIRED_PACKAGES = {
    "solana-py": "0.30.2",
    "solders": "0.18.1",
    "anchorpy": "0.18.0",
    "aiohttp": "3.8.0",
    "pyyaml": "6.0"
}

def check_package(package_name: str, required_version: str = None) -> Tuple[bool, Optional[str]]:
    """
    Check if a package is installed and optionally verify its version.
    
    Args:
        package_name: Name of the package to check
        required_version: Optional required version string
        
    Returns:
        Tuple of (is_installed, installed_version)
    """
    # Handle packages with hyphens
    module_name = package_name.replace('-', '_')
    
    # Check if package is installed
    spec = importlib.util.find_spec(module_name)
    if spec is None:
        return False, None
        
    # If no version check is needed
    if required_version is None:
        return True, None
        
    # Check version
    try:
        package = importlib.import_module(module_name)
        if hasattr(package, '__version__'):
            installed_version = package.__version__
            return True, installed_version
        elif hasattr(package, 'version'):
            installed_version = package.version
            return True, installed_version
        else:
            # Package is installed but couldn't determine version
            return True, "unknown"
    except ImportError:
        # Package is installed but couldn't be imported
        return True, "unknown"

def check_environment() -> Dict[str, Dict[str, str]]:
    """
    Check if all required packages are installed.
    
    Returns:
        Dictionary with package status information
    """
    status = {}
    
    for package, required_version in REQUIRED_PACKAGES.items():
        is_installed, installed_version = check_package(package, required_version)
        
        if is_installed:
            if installed_version == required_version:
                status[package] = {
                    "status": "ok", 
                    "installed_version": installed_version,
                    "required_version": required_version
                }
            else:
                status[package] = {
                    "status": "version_mismatch",
                    "installed_version": installed_version,
                    "required_version": required_version
                }
        else:
            status[package] = {
                "status": "missing",
                "installed_version": None,
                "required_version": required_version
            }
    
    return status

def generate_install_commands(status: Dict[str, Dict[str, str]]) -> List[str]:
    """
    Generate pip commands to install or update required packages.
    
    Args:
        status: Package status dictionary from check_environment()
        
    Returns:
        List of pip commands to run
    """
    commands = []
    
    for package, info in status.items():
        if info["status"] == "missing" or info["status"] == "version_mismatch":
            commands.append(f"pip install {package}=={info['required_version']}")
    
    return commands

def print_status(status: Dict[str, Dict[str, str]]) -> None:
    """
    Print the status of required packages in a readable format.
    
    Args:
        status: Package status dictionary from check_environment()
    """
    print("\n=== GBPBot Environment Check ===\n")
    
    all_ok = True
    for package, info in status.items():
        if info["status"] == "ok":
            print(f"✅ {package} {info['installed_version']}")
        elif info["status"] == "version_mismatch":
            all_ok = False
            print(f"⚠️ {package} {info['installed_version']} (required: {info['required_version']})")
        else:  # missing
            all_ok = False
            print(f"❌ {package} (not installed, required: {info['required_version']})")
    
    if not all_ok:
        print("\nSome required packages are missing or have incorrect versions.")
        print("Run the following commands to install the required packages:\n")
        for cmd in generate_install_commands(status):
            print(f"  {cmd}")
    else:
        print("\nAll required packages are installed with correct versions! ✨")

if __name__ == "__main__":
    # If run as a script, check the environment and print status
    status = check_environment()
    print_status(status)
    
    # Exit with non-zero code if any packages are missing or have wrong versions
    if any(info["status"] != "ok" for info in status.values()):
        sys.exit(1)
    sys.exit(0) 