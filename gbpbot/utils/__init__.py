"""
Utility modules for the GBP Bot application.

This package contains various utility modules that provide common functionality
used throughout the application, such as configuration management, blockchain
utilities, environment checking, and exception handling.
"""

from typing import Any, Dict, NoReturn, Tuple

# Import commonly used utilities for easier access
from gbpbot.utils.config import Config, get_config
from gbpbot.utils.exceptions import (
    GBPBotError, ConfigurationError, BlockchainError,
    TransactionError, InsufficientFundsError, UnsupportedBlockchainError,
    handle_blockchain_error
)
from gbpbot.utils.environment import (
    check_dependency, check_dependencies, check_blockchain_dependencies,
    check_environment_ready, print_environment_report
)
from gbpbot.utils.blockchain_utils import (
    wei_to_eth, eth_to_wei, lamports_to_sol, sol_to_lamports,
    format_token_amount, parse_token_amount,
    is_valid_ethereum_address, is_valid_solana_address,
    get_token_decimals, get_gas_price_level,
    truncate_address, normalize_blockchain_name
)

# Import Solana-specific utilities if available
try:
    from gbpbot.utils.solana_imports import (
        check_solana_dependencies, get_dependency_status,
        convert_pubkey_types
    )
except ImportError:
    # Solana imports not available, provide dummy functions
    def check_solana_dependencies() -> Dict[str, bool]:
        """Dummy function for checking Solana dependencies."""
        return {"solana": False, "solders": False, "anchorpy": False}
    
    def get_dependency_status() -> str:
        """Dummy function for getting dependency status."""
        return "Solana dependencies not available"
    
    def convert_pubkey_types(*args: Any, **kwargs: Any) -> NoReturn:
        """Dummy function for converting pubkey types."""
        raise ImportError("Solana dependencies not available")

# Define what should be imported with "from gbpbot.utils import *"
__all__ = [
    # Configuration
    'Config', 'get_config',
    
    # Exceptions
    'GBPBotError', 'ConfigurationError', 'BlockchainError',
    'TransactionError', 'InsufficientFundsError', 'UnsupportedBlockchainError',
    'handle_blockchain_error',
    
    # Environment
    'check_dependency', 'check_dependencies', 'check_blockchain_dependencies',
    'check_environment_ready', 'print_environment_report',
    
    # Blockchain utilities
    'wei_to_eth', 'eth_to_wei', 'lamports_to_sol', 'sol_to_lamports',
    'format_token_amount', 'parse_token_amount',
    'is_valid_ethereum_address', 'is_valid_solana_address',
    'get_token_decimals', 'get_gas_price_level',
    'truncate_address', 'normalize_blockchain_name',
    
    # Solana utilities
    'check_solana_dependencies', 'get_dependency_status',
    'convert_pubkey_types',
] 