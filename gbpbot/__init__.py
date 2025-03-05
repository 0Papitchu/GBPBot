"""
GBP Bot - Blockchain Client Interface

A flexible and extensible blockchain client interface for interacting with
multiple blockchains through a unified API.
"""

__version__ = "0.1.0"
__author__ = "GBP Bot Team"
__email__ = "contact@example.com"
__license__ = "MIT"

# Import commonly used modules for easier access
from gbpbot.core.blockchain.base import BaseBlockchainClient, BlockchainClientFactory

# Define what should be imported with "from gbpbot import *"
__all__ = [
    "BaseBlockchainClient",
    "BlockchainClientFactory",
] 