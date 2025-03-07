"""
Custom exceptions for the GBP Bot application.

This module defines custom exceptions that are used throughout the application
to handle specific error cases related to blockchain operations, configuration,
and other application-specific errors.
"""

class GBPBotError(Exception):
    """Base exception class for all GBP Bot errors."""
    pass


class ConfigurationError(GBPBotError):
    """Raised when there is an error in the configuration."""
    pass


class EnvironmentError(GBPBotError):
    """Raised when there is an error with the environment setup."""
    pass


class DependencyError(EnvironmentError):
    """Raised when a required dependency is missing."""
    def __init__(self, dependency_name, blockchain_type=None):
        self.dependency_name = dependency_name
        self.blockchain_type = blockchain_type
        message = f"Required dependency '{dependency_name}' is not installed"
        if blockchain_type:
            message += f" for blockchain '{blockchain_type}'"
        super().__init__(message)


class BlockchainError(GBPBotError):
    """Base class for blockchain-related errors."""
    pass


class ConnectionError(BlockchainError):
    """Raised when there is an error connecting to a blockchain."""
    pass


class TransactionError(BlockchainError):
    """Raised when there is an error with a blockchain transaction."""
    pass


class InsufficientFundsError(TransactionError):
    """Raised when there are insufficient funds for a transaction."""
    pass


class TransactionTimeoutError(TransactionError):
    """Raised when a transaction times out."""
    pass


class TransactionRejectedError(TransactionError):
    """Raised when a transaction is rejected by the blockchain."""
    pass


class ApprovalError(TransactionError):
    """Raised when there is an error with token approval."""
    pass


class SwapError(TransactionError):
    """Raised when there is an error with a token swap."""
    pass


class PriceError(BlockchainError):
    """Raised when there is an error getting a token price."""
    pass


class BalanceError(BlockchainError):
    """Raised when there is an error getting a token balance."""
    pass


class WalletError(GBPBotError):
    """Base class for wallet-related errors."""
    pass


class KeypairError(WalletError):
    """Raised when there is an error with a keypair."""
    pass


class SignatureError(WalletError):
    """Raised when there is an error with a signature."""
    pass


class UnsupportedBlockchainError(GBPBotError):
    """Raised when an unsupported blockchain is requested."""
    def __init__(self, blockchain_type):
        self.blockchain_type = blockchain_type
        super().__init__(f"Unsupported blockchain type: {blockchain_type}")


class RateLimitError(GBPBotError):
    """Raised when a rate limit is exceeded."""
    pass


class APIError(GBPBotError):
    """Raised when there is an error with an API call."""
    def __init__(self, message, status_code=None, response=None):
        self.status_code = status_code
        self.response = response
        super().__init__(message)


class ArbitrageError(GBPBotError):
    """Raised when there is an error with arbitrage operations."""
    pass


class ExchangeError(GBPBotError):
    """Base class for exchange-related errors."""
    pass


class ExchangeConnectionError(ExchangeError):
    """Raised when there is an error connecting to an exchange."""
    pass


class ExchangeAPIError(ExchangeError):
    """Raised when there is an error with an exchange API call."""
    def __init__(self, message, status_code=None, response=None):
        self.status_code = status_code
        self.response = response
        super().__init__(message)


def handle_blockchain_error(error, blockchain_type=None):
    """
    Handle common blockchain errors and convert them to our custom exceptions.
    
    Args:
        error: The original error
        blockchain_type: The type of blockchain (ethereum, solana, etc.)
        
    Returns:
        A custom exception
    """
    error_message = str(error).lower()
    
    # Handle insufficient funds errors
    if any(phrase in error_message for phrase in ["insufficient funds", "insufficient balance"]):
        return InsufficientFundsError(f"Insufficient funds: {error}")
    
    # Handle timeout errors
    if any(phrase in error_message for phrase in ["timeout", "timed out"]):
        return TransactionTimeoutError(f"Transaction timed out: {error}")
    
    # Handle rejection errors
    if any(phrase in error_message for phrase in ["rejected", "denied", "reverted"]):
        return TransactionRejectedError(f"Transaction rejected: {error}")
    
    # If no specific error is identified, return a generic blockchain error
    return BlockchainError(f"Blockchain error: {error}") 