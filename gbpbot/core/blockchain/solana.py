"""
Solana blockchain client implementation.

This module provides an implementation of the BaseBlockchainClient for the
Solana blockchain, using solana-py to interact with Solana nodes.
"""

import asyncio
import base64
import logging
import time
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Union, Any, cast

# Import Solana dependencies through our adapter
from gbpbot.utils.solana_imports import (
    AsyncClient, Keypair, PublicKey, Transaction, TransactionInstruction,
    check_solana_dependencies, get_dependency_status, convert_pubkey_types
)
from gbpbot.core.blockchain.base import BaseBlockchainClient
from gbpbot.utils.blockchain_utils import (
    lamports_to_sol, sol_to_lamports, format_token_amount, parse_token_amount,
    get_gas_price_level
)
from gbpbot.utils.exceptions import (
    BlockchainError, ConnectionError, TransactionError,
    InsufficientFundsError, TransactionTimeoutError,
    TransactionRejectedError, ApprovalError, SwapError,
    PriceError, BalanceError, handle_blockchain_error
)

# Configure logging
logger = logging.getLogger(__name__)

# Check if Solana dependencies are available
SOLANA_DEPS = check_solana_dependencies()
if not all(SOLANA_DEPS.values()):
    logger.warning(f"Some Solana dependencies are missing: {get_dependency_status()}")

# Common addresses and constants
WRAPPED_SOL_MINT = "So11111111111111111111111111111111111111112"
SERUM_DEX_PROGRAM_ID = "9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin"
ORCA_SWAP_PROGRAM_ID = "DjVE6JNiYqPL2QXyCUUh8rNjHrbz9hXHNYt99MQ59qw1"
RAYDIUM_SWAP_PROGRAM_ID = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"
JUPITER_AGGREGATOR_PROGRAM_ID = "JUP2jxvXaqu7NQY1GmNF4m1vodw12LVXYxbFL2uJvfo"


class SolanaClient(BaseBlockchainClient):
    """Solana blockchain client implementation."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Solana client.
        
        Args:
            config: Configuration dictionary with Solana-specific settings
        """
        self.config = config
        self.rpc_url = config.get("rpc_url")
        self.private_key = config.get("private_key")
        self.client = None
        self.keypair = None
        self.public_key = None
        self.connected = False
        
        # Default compute unit settings
        self.default_compute_units = int(config.get("default_compute_units", 200000))
        
        # Token account cache
        self.token_accounts_cache = {}
    
    async def connect(self) -> bool:
        """
        Connect to the Solana blockchain.
        
        Returns:
            True if the connection is successful, False otherwise
        """
        try:
            # Initialize AsyncClient
            self.client = AsyncClient(self.rpc_url)
            
            # Set up keypair if private key is provided
            if self.private_key:
                # Handle different private key formats
                if isinstance(self.private_key, str):
                    # Check if it's a base58 encoded string or a list of bytes
                    try:
                        if self.private_key.startswith("[") and self.private_key.endswith("]"):
                            # Convert string representation of array to bytes
                            key_bytes = bytes(eval(self.private_key))
                        else:
                            # Assume base58 encoded
                            key_bytes = base64.b64decode(self.private_key)
                        
                        self.keypair = Keypair.from_secret_key(key_bytes)
                    except Exception as e:
                        logger.error(f"Error parsing private key: {e}")
                        return False
                elif isinstance(self.private_key, list):
                    # Direct list of integers
                    self.keypair = Keypair.from_secret_key(bytes(self.private_key))
                else:
                    logger.error(f"Unsupported private key format: {type(self.private_key)}")
                    return False
                
                self.public_key = self.keypair.public_key
                logger.info(f"Using account: {self.public_key}")
            
            # Test connection
            version = await self.client.get_version()
            if not version:
                logger.error("Failed to connect to Solana node")
                return False
            
            self.connected = True
            logger.info(f"Connected to Solana node: {self.rpc_url}, version: {version['solana-core']}")
            return True
        
        except Exception as e:
            logger.error(f"Error connecting to Solana: {e}")
            self.connected = False
            raise ConnectionError(f"Failed to connect to Solana: {e}")
    
    async def disconnect(self) -> bool:
        """
        Disconnect from the Solana blockchain.
        
        Returns:
            True if the disconnection is successful, False otherwise
        """
        if self.client:
            await self.client.close()
        
        self.client = None
        self.connected = False
        self.token_accounts_cache = {}
        logger.info("Disconnected from Solana")
        return True
    
    async def get_balance(self, token_address: str, wallet_address: Optional[str] = None) -> float:
        """
        Get the balance of a token for a wallet.
        
        Args:
            token_address: Address of the token (use "SOL" for native SOL)
            wallet_address: Address of the wallet (default: the client's address)
            
        Returns:
            Token balance as a float
        """
        if not self.connected or not self.client:
            raise ConnectionError("Not connected to Solana")
        
        try:
            address = wallet_address or (self.public_key.to_base58() if self.public_key else None)
            if not address:
                raise BalanceError("No wallet address provided")
            
            # Convert address to PublicKey
            pubkey = PublicKey(address)
            
            # Handle native SOL
            if token_address.upper() == "SOL":
                response = await self.client.get_balance(pubkey)
                if "result" not in response or "value" not in response["result"]:
                    raise BalanceError("Invalid response from Solana node")
                
                lamports = response["result"]["value"]
                return float(lamports_to_sol(lamports))
            
            # Handle SPL tokens
            token_pubkey = PublicKey(token_address)
            
            # Find token accounts owned by the wallet
            response = await self.client.get_token_accounts_by_owner(
                pubkey,
                {"mint": str(token_pubkey)}
            )
            
            if "result" not in response or "value" not in response["result"]:
                raise BalanceError("Invalid response from Solana node")
            
            # Sum up balances from all accounts for this token
            total_balance = 0
            for account in response["result"]["value"]:
                account_data = account["account"]["data"]
                if isinstance(account_data, list) and len(account_data) > 1:
                    # Parse token account data
                    data = base64.b64decode(account_data[0])
                    # Token account data format: 
                    # - mint (32 bytes)
                    # - owner (32 bytes)
                    # - amount (8 bytes)
                    # - ... other fields
                    if len(data) >= 72:
                        amount = int.from_bytes(data[64:72], byteorder="little")
                        total_balance += amount
            
            # Get token decimals (default to 9 for SPL tokens)
            decimals = 9  # Default for most SPL tokens
            
            # Format balance with correct decimals
            balance = format_token_amount(total_balance, decimals)
            
            return float(balance)
        
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            raise BalanceError(f"Failed to get balance: {e}")
    
    async def get_token_price(self, token_address: str, base_token: Optional[str] = None) -> float:
        """
        Get the price of a token in terms of another token.
        
        Args:
            token_address: Address of the token to get the price for
            base_token: Address of the base token (default: SOL)
            
        Returns:
            Token price as a float
        """
        if not self.connected or not self.client:
            raise ConnectionError("Not connected to Solana")
        
        try:
            # Default to SOL as base token
            base_token_address = base_token or WRAPPED_SOL_MINT
            
            # TODO: Implement price fetching from a price oracle or DEX
            # This is a simplified implementation that would need to be expanded
            # with actual price fetching logic from Jupiter, Orca, or another source
            
            # For now, return a placeholder price
            logger.warning("Token price fetching not fully implemented")
            return 0.0
        
        except Exception as e:
            logger.error(f"Error getting token price: {e}")
            raise PriceError(f"Failed to get token price: {e}")
    
    async def execute_transaction(self, tx_params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a transaction on the blockchain.
        
        Args:
            tx_params: Transaction parameters
            
        Returns:
            Transaction result
        """
        if not self.connected or not self.client:
            raise ConnectionError("Not connected to Solana")
        
        if not self.keypair:
            raise TransactionError("Keypair not provided")
        
        try:
            # Check if we have a pre-built transaction or instructions
            transaction = tx_params.get("transaction")
            instructions = tx_params.get("instructions", [])
            
            if not transaction and not instructions:
                raise TransactionError("No transaction or instructions provided")
            
            # If we have instructions but no transaction, build the transaction
            if not transaction and instructions:
                transaction = Transaction()
                for instruction in instructions:
                    transaction.add(instruction)
            
            # Set recent blockhash if not already set
            if not transaction.recent_blockhash:
                response = await self.client.get_recent_blockhash()
                if "result" not in response or "value" not in response["result"]:
                    raise TransactionError("Failed to get recent blockhash")
                
                transaction.recent_blockhash = response["result"]["value"]["blockhash"]
            
            # Set fee payer if not already set
            if not transaction.fee_payer:
                transaction.fee_payer = self.public_key
            
            # Sign transaction
            transaction.sign(self.keypair)
            
            # Send transaction
            response = await self.client.send_raw_transaction(
                transaction.serialize(),
                tx_params.get("opts", {})
            )
            
            if "result" not in response:
                raise TransactionError(f"Failed to send transaction: {response}")
            
            tx_hash = response["result"]
            logger.info(f"Transaction sent: {tx_hash}")
            
            # Wait for transaction confirmation if requested
            if tx_params.get("wait_for_confirmation", True):
                confirmation_timeout = tx_params.get("confirmation_timeout", 60)
                tx_receipt = await self.wait_for_transaction(tx_hash, confirmation_timeout)
                
                return {
                    "tx_hash": tx_hash,
                    "status": "success" if tx_receipt.get("confirmed", False) else "failed",
                    "slot": tx_receipt.get("slot"),
                    "receipt": tx_receipt
                }
            
            return {
                "tx_hash": tx_hash,
                "status": "sent"
            }
        
        except Exception as e:
            logger.error(f"Error executing transaction: {e}")
            raise handle_blockchain_error(e, "solana")
    
    async def execute_swap(self, token_in: str, token_out: str, amount_in: float, 
                          slippage: float = 0.5, deadline_seconds: int = 300,
                          gas_priority: str = "normal") -> Dict[str, Any]:
        """
        Execute a token swap.
        
        Args:
            token_in: Address of the input token (use "SOL" for native SOL)
            token_out: Address of the output token (use "SOL" for native SOL)
            amount_in: Amount of input token to swap
            slippage: Maximum slippage percentage (default: 0.5%)
            deadline_seconds: Transaction deadline in seconds (default: 300)
            gas_priority: Gas priority level (slow, normal, fast)
            
        Returns:
            Swap transaction result
        """
        if not self.connected or not self.client:
            raise ConnectionError("Not connected to Solana")
        
        if not self.keypair:
            raise SwapError("Keypair not provided")
        
        try:
            # Convert SOL to Wrapped SOL for routing
            is_sol_in = token_in.upper() == "SOL"
            is_sol_out = token_out.upper() == "SOL"
            
            token_in_address = WRAPPED_SOL_MINT if is_sol_in else token_in
            token_out_address = WRAPPED_SOL_MINT if is_sol_out else token_out
            
            # Calculate amount in (in smallest units)
            if is_sol_in:
                amount_in_lamports = sol_to_lamports(amount_in)
            else:
                # For SPL tokens, default to 9 decimals
                decimals = 9  # This should be fetched from the token's metadata
                amount_in_lamports = parse_token_amount(amount_in, decimals)
            
            # TODO: Implement swap logic using Jupiter Aggregator or another DEX
            # This is a placeholder implementation that would need to be expanded
            # with actual swap logic
            
            logger.warning("Token swap not fully implemented")
            raise SwapError("Token swap not implemented yet")
            
            # The following is pseudocode for how the implementation might look
            """
            # Get swap quote from Jupiter
            quote = await self._get_jupiter_quote(
                token_in_address,
                token_out_address,
                amount_in_lamports,
                slippage
            )
            
            # Build swap transaction
            swap_tx = await self._build_jupiter_swap_tx(quote)
            
            # Execute transaction
            result = await self.execute_transaction({
                "transaction": swap_tx,
                "wait_for_confirmation": True
            })
            
            # Add swap-specific information to the result
            result["swap_info"] = {
                "token_in": token_in,
                "token_out": token_out,
                "amount_in": amount_in,
                "expected_amount_out": quote["outAmount"],
                "slippage": slippage
            }
            
            return result
            """
        
        except Exception as e:
            logger.error(f"Error executing swap: {e}")
            if isinstance(e, TransactionError):
                raise SwapError(f"Swap failed: {e}")
            raise SwapError(f"Failed to execute swap: {e}")
    
    async def check_token_approval(self, token_address: str, spender_address: str, amount: Optional[int] = None) -> bool:
        """
        Check if a token is approved for spending by a spender.
        
        Note: Solana doesn't use the same approval model as Ethereum.
        This method checks if a token account delegate exists.
        
        Args:
            token_address: Address of the token
            spender_address: Address of the spender
            amount: Amount to check approval for (default: None, checks any approval)
            
        Returns:
            True if the token is approved, False otherwise
        """
        if not self.connected or not self.client:
            raise ConnectionError("Not connected to Solana")
        
        try:
            # Solana uses a different model for token approvals
            # This is a simplified implementation
            logger.warning("Token approval checking not fully implemented for Solana")
            
            # In Solana, you typically create a token account and set a delegate
            # This would require fetching the token account and checking its delegate
            return False
        
        except Exception as e:
            logger.error(f"Error checking token approval: {e}")
            raise ApprovalError(f"Failed to check token approval: {e}")
    
    async def approve_token(self, token_address: str, spender_address: str, amount: int, 
                           gas_priority: str = "normal") -> Dict[str, Any]:
        """
        Approve a token for spending by a spender.
        
        Note: Solana doesn't use the same approval model as Ethereum.
        This method sets a delegate for a token account.
        
        Args:
            token_address: Address of the token
            spender_address: Address of the spender
            amount: Amount to approve
            gas_priority: Gas priority level (slow, normal, fast)
            
        Returns:
            Approval transaction result
        """
        if not self.connected or not self.client:
            raise ConnectionError("Not connected to Solana")
        
        if not self.keypair:
            raise ApprovalError("Keypair not provided")
        
        try:
            # Solana uses a different model for token approvals
            # This is a simplified implementation
            logger.warning("Token approval not fully implemented for Solana")
            
            # In Solana, you would create a token account and set a delegate
            # This would require building a transaction with the appropriate instructions
            raise ApprovalError("Token approval not implemented yet for Solana")
        
        except Exception as e:
            logger.error(f"Error approving token: {e}")
            if isinstance(e, TransactionError):
                raise ApprovalError(f"Approval failed: {e}")
            raise ApprovalError(f"Failed to approve token: {e}")
    
    async def wait_for_transaction(self, tx_hash: str, timeout_seconds: int = 60) -> Dict[str, Any]:
        """
        Wait for a transaction to be confirmed.
        
        Args:
            tx_hash: Transaction hash
            timeout_seconds: Timeout in seconds
            
        Returns:
            Transaction receipt
        """
        if not self.connected or not self.client:
            raise ConnectionError("Not connected to Solana")
        
        try:
            # Wait for transaction confirmation with timeout
            start_time = time.time()
            while True:
                try:
                    response = await self.client.get_signature_statuses([tx_hash])
                    if "result" in response and "value" in response["result"]:
                        status = response["result"]["value"][0]
                        if status is not None:
                            if status.get("confirmationStatus") == "finalized":
                                return {
                                    "tx_hash": tx_hash,
                                    "confirmed": True,
                                    "slot": status.get("slot"),
                                    "confirmations": status.get("confirmations"),
                                    "status": status
                                }
                except Exception as e:
                    logger.warning(f"Error checking transaction status: {e}")
                
                # Check timeout
                if time.time() - start_time > timeout_seconds:
                    raise TransactionTimeoutError(f"Transaction {tx_hash} timed out after {timeout_seconds} seconds")
                
                # Wait before checking again
                await asyncio.sleep(1)
        
        except TransactionTimeoutError:
            raise
        except Exception as e:
            logger.error(f"Error waiting for transaction: {e}")
            raise TransactionError(f"Failed to wait for transaction: {e}")
    
    async def get_transaction_status(self, tx_hash: str) -> Dict[str, Any]:
        """
        Get the status of a transaction.
        
        Args:
            tx_hash: Transaction hash
            
        Returns:
            Transaction status information
        """
        if not self.connected or not self.client:
            raise ConnectionError("Not connected to Solana")
        
        try:
            response = await self.client.get_signature_statuses([tx_hash])
            if "result" in response and "value" in response["result"]:
                status = response["result"]["value"][0]
                if status is not None:
                    confirmation_status = status.get("confirmationStatus", "unknown")
                    return {
                        "tx_hash": tx_hash,
                        "status": confirmation_status,
                        "slot": status.get("slot"),
                        "confirmations": status.get("confirmations"),
                        "confirmed": confirmation_status == "finalized",
                        "details": status
                    }
            
            # If no status found, transaction is unknown
            return {
                "tx_hash": tx_hash,
                "status": "unknown"
            }
        
        except Exception as e:
            logger.error(f"Error getting transaction status: {e}")
            raise TransactionError(f"Failed to get transaction status: {e}")
    
    # Helper methods
    
    async def _get_token_account(self, token_address: str, owner_address: Optional[str] = None) -> Optional[str]:
        """
        Get the token account address for a token owned by an address.
        
        Args:
            token_address: Address of the token
            owner_address: Address of the owner (default: the client's address)
            
        Returns:
            Token account address or None if not found
        """
        if not self.client:
            return None
        
        owner = owner_address or (self.public_key.to_base58() if self.public_key else None)
        if not owner:
            return None
        
        # Check cache first
        cache_key = f"{token_address}:{owner}"
        if cache_key in self.token_accounts_cache:
            return self.token_accounts_cache[cache_key]
        
        # Convert addresses to PublicKey
        token_pubkey = PublicKey(token_address)
        owner_pubkey = PublicKey(owner)
        
        # Find token accounts owned by the wallet
        response = await self.client.get_token_accounts_by_owner(
            owner_pubkey,
            {"mint": str(token_pubkey)}
        )
        
        if "result" in response and "value" in response["result"] and response["result"]["value"]:
            # Use the first account found
            account_address = response["result"]["value"][0]["pubkey"]
            self.token_accounts_cache[cache_key] = account_address
            return account_address
        
        return None
    
    async def _get_token_decimals(self, token_address: str) -> int:
        """
        Get the number of decimals for a token.
        
        Args:
            token_address: Address of the token
            
        Returns:
            Number of decimals
        """
        # For Solana tokens, we would need to fetch the mint account data
        # and extract the decimals field
        # This is a simplified implementation
        return 9  # Default for most SPL tokens 