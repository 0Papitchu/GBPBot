"""
Ethereum blockchain client implementation.

This module provides an implementation of the BaseBlockchainClient for the
Ethereum blockchain, using web3.py to interact with Ethereum nodes.
"""

import asyncio
import logging
import time
from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Union, Any

from web3 import Web3
from web3.exceptions import TransactionNotFound
from gbpbot.core.blockchain.compat import get_geth_poa_middleware
from eth_account import Account
from eth_typing import ChecksumAddress

from gbpbot.core.blockchain.base import BaseBlockchainClient
from gbpbot.utils.blockchain_utils import (
    wei_to_eth, eth_to_wei, format_token_amount, parse_token_amount,
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

# ERC20 ABI for token interactions
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function"
    },
    {
        "constant": False,
        "inputs": [
            {"name": "_spender", "type": "address"},
            {"name": "_value", "type": "uint256"}
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function"
    },
    {
        "constant": True,
        "inputs": [
            {"name": "_owner", "type": "address"},
            {"name": "_spender", "type": "address"}
        ],
        "name": "allowance",
        "outputs": [{"name": "", "type": "uint256"}],
        "type": "function"
    }
]

# Uniswap V2 Router ABI for swaps
UNISWAP_ROUTER_ABI = [
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
            {"internalType": "address[]", "name": "path", "type": "address[]"},
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"}
        ],
        "name": "swapExactTokensForTokens",
        "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
            {"internalType": "address[]", "name": "path", "type": "address[]"},
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"}
        ],
        "name": "swapExactETHForTokens",
        "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
        "stateMutability": "payable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountIn", "type": "uint256"},
            {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
            {"internalType": "address[]", "name": "path", "type": "address[]"},
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"}
        ],
        "name": "swapExactTokensForETH",
        "outputs": [{"internalType": "uint256[]", "name": "amounts", "type": "uint256[]"}],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [
            {"internalType": "uint256", "name": "amountOutMin", "type": "uint256"},
            {"internalType": "address[]", "name": "path", "type": "address[]"},
            {"internalType": "address", "name": "to", "type": "address"},
            {"internalType": "uint256", "name": "deadline", "type": "uint256"}
        ],
        "name": "swapExactETHForTokensSupportingFeeOnTransferTokens",
        "outputs": [],
        "stateMutability": "payable",
        "type": "function"
    }
]

# Common addresses
WETH_ADDRESS = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
UNISWAP_ROUTER_ADDRESS = "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"


class EthereumClient(BaseBlockchainClient):
    """Ethereum blockchain client implementation."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Ethereum client.
        
        Args:
            config: Configuration dictionary with Ethereum-specific settings
        """
        self.config = config
        
        # Extract RPC URL from config
        self.rpc_url = None
        if "rpc" in config and "providers" in config["rpc"] and len(config["rpc"]["providers"]) > 0:
            # Use the first provider by default
            self.rpc_url = config["rpc"]["providers"][0]["url"]
        
        # Fallback to direct rpc_url if provided
        if not self.rpc_url:
            self.rpc_url = config.get("rpc_url")
        
        # Use default if still not set
        if not self.rpc_url:
            self.rpc_url = "https://api.avax.network/ext/bc/C/rpc"  # Default Avalanche C-Chain
            
        logger.info(f"Using RPC URL: {self.rpc_url}")
        
        self.private_key = config.get("private_key")
        self.web3 = None
        self.account = None
        self.address = None
        self.connected = False
        
        # Default gas settings
        self.default_gas_limit = int(config.get("default_gas_limit", 250000))
        
        # Contract instances
        self.token_contracts = {}
        self.router_contract = None
    
    async def connect(self) -> bool:
        """
        Connect to the Ethereum blockchain.
        
        Returns:
            True if the connection is successful, False otherwise
        """
        try:
            # Initialize Web3
            self.web3 = Web3(Web3.HTTPProvider(self.rpc_url))
            
            # Add middleware for POA chains (like Polygon)
            self.web3.middleware_onion.inject(get_geth_poa_middleware(), layer=0)
            
            # Check connection
            if not self.web3.is_connected():
                logger.error("Failed to connect to Ethereum node")
                return False
            
            # Set up account
            if self.private_key:
                self.account = Account.from_key(self.private_key)
                self.address = self.account.address
                logger.info(f"Using account: {self.address}")
            
            # Initialize router contract
            self.router_contract = self.web3.eth.contract(
                address=Web3.to_checksum_address(UNISWAP_ROUTER_ADDRESS),
                abi=UNISWAP_ROUTER_ABI
            )
            
            self.connected = True
            logger.info(f"Connected to Ethereum node: {self.rpc_url}")
            return True
        
        except Exception as e:
            logger.error(f"Error connecting to Ethereum: {e}")
            self.connected = False
            raise ConnectionError(f"Failed to connect to Ethereum: {e}")
    
    async def disconnect(self) -> bool:
        """
        Disconnect from the Ethereum blockchain.
        
        Returns:
            True if the disconnection is successful, False otherwise
        """
        self.connected = False
        self.web3 = None
        self.account = None
        self.address = None
        self.token_contracts = {}
        self.router_contract = None
        logger.info("Disconnected from Ethereum")
        return True
    
    async def get_balance(self, token_address: str, wallet_address: Optional[str] = None) -> float:
        """
        Get the balance of a token for a wallet.
        
        Args:
            token_address: Address of the token (use "ETH" for native ETH)
            wallet_address: Address of the wallet (default: the client's address)
            
        Returns:
            Token balance as a float
        """
        if not self.connected:
            raise ConnectionError("Not connected to Ethereum")
        
        try:
            address = wallet_address or self.address
            if not address:
                raise BalanceError("No wallet address provided")
            
            checksum_address = Web3.to_checksum_address(address)
            
            # Handle native ETH
            if token_address.upper() == "ETH":
                wei_balance = self.web3.eth.get_balance(checksum_address)
                return float(wei_to_eth(wei_balance))
            
            # Handle ERC20 tokens
            token_contract = await self._get_token_contract(token_address)
            decimals = await self._get_token_decimals(token_address)
            
            raw_balance = token_contract.functions.balanceOf(checksum_address).call()
            balance = format_token_amount(raw_balance, decimals)
            
            return float(balance)
        
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            raise BalanceError(f"Failed to get balance: {e}")
    
    async def get_token_price(self, token_address: str, base_token: Optional[str] = None) -> float:
        """
        Get the price of a token in terms of another token.
        
        Args:
            token_address: Address of the token to get the price for
            base_token: Address of the base token (default: WETH)
            
        Returns:
            Token price as a float
        """
        if not self.connected:
            raise ConnectionError("Not connected to Ethereum")
        
        try:
            # Default to WETH as base token
            base_token_address = base_token or WETH_ADDRESS
            
            # TODO: Implement price fetching from a price oracle or DEX
            # This is a simplified implementation that would need to be expanded
            # with actual price fetching logic from Uniswap or a price oracle
            
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
        if not self.connected:
            raise ConnectionError("Not connected to Ethereum")
        
        if not self.private_key:
            raise TransactionError("Private key not provided")
        
        try:
            # Ensure we have the required parameters
            if "to" not in tx_params:
                raise TransactionError("Transaction 'to' address not provided")
            
            # Set default values if not provided
            if "gas" not in tx_params:
                tx_params["gas"] = self.default_gas_limit
            
            # Set gas price if not provided
            if "gasPrice" not in tx_params and "maxFeePerGas" not in tx_params:
                # Use EIP-1559 gas parameters if supported
                if self._supports_eip1559():
                    gas_price = get_gas_price_level("ethereum", "normal")
                    tx_params["maxFeePerGas"] = self.web3.to_wei(gas_price["max_fee_per_gas"], "gwei")
                    tx_params["maxPriorityFeePerGas"] = self.web3.to_wei(gas_price["max_priority_fee_per_gas"], "gwei")
                else:
                    # Fall back to legacy gas price
                    tx_params["gasPrice"] = self.web3.eth.gas_price
            
            # Set nonce if not provided
            if "nonce" not in tx_params:
                tx_params["nonce"] = self.web3.eth.get_transaction_count(self.address)
            
            # Sign transaction
            signed_tx = self.web3.eth.account.sign_transaction(tx_params, self.private_key)
            
            # Send transaction
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.rawTransaction)
            tx_hash_hex = tx_hash.hex()
            
            logger.info(f"Transaction sent: {tx_hash_hex}")
            
            # Wait for transaction receipt
            tx_receipt = await self.wait_for_transaction(tx_hash_hex)
            
            return {
                "tx_hash": tx_hash_hex,
                "status": "success" if tx_receipt["status"] == 1 else "failed",
                "block_number": tx_receipt["blockNumber"],
                "gas_used": tx_receipt["gasUsed"],
                "receipt": tx_receipt
            }
        
        except Exception as e:
            logger.error(f"Error executing transaction: {e}")
            raise handle_blockchain_error(e, "ethereum")
    
    async def execute_swap(self, token_in: str, token_out: str, amount_in: float, 
                          slippage: float = 0.5, deadline_seconds: int = 300,
                          gas_priority: str = "normal") -> Dict[str, Any]:
        """
        Execute a token swap.
        
        Args:
            token_in: Address of the input token (use "ETH" for native ETH)
            token_out: Address of the output token (use "ETH" for native ETH)
            amount_in: Amount of input token to swap
            slippage: Maximum slippage percentage (default: 0.5%)
            deadline_seconds: Transaction deadline in seconds (default: 300)
            gas_priority: Gas priority level (slow, normal, fast)
            
        Returns:
            Swap transaction result
        """
        if not self.connected:
            raise ConnectionError("Not connected to Ethereum")
        
        if not self.private_key:
            raise SwapError("Private key not provided")
        
        try:
            # Convert ETH to WETH for routing
            is_eth_in = token_in.upper() == "ETH"
            is_eth_out = token_out.upper() == "ETH"
            
            path = []
            if is_eth_in:
                path.append(WETH_ADDRESS)
            else:
                path.append(Web3.to_checksum_address(token_in))
            
            if is_eth_out:
                path.append(WETH_ADDRESS)
            else:
                path.append(Web3.to_checksum_address(token_out))
            
            # Calculate deadline
            deadline = int(time.time() + deadline_seconds)
            
            # Calculate amount in (in smallest units)
            if is_eth_in:
                amount_in_wei = eth_to_wei(amount_in)
            else:
                token_decimals = await self._get_token_decimals(token_in)
                amount_in_wei = parse_token_amount(amount_in, token_decimals)
            
            # TODO: Get expected output amount from Uniswap
            # This would require calling getAmountsOut on the router
            # For now, we'll use a placeholder
            amount_out_min = 1  # This should be calculated based on price and slippage
            
            # Get gas price based on priority
            gas_price = get_gas_price_level("ethereum", gas_priority)
            
            # Prepare transaction parameters
            tx_params = {
                "from": self.address,
                "gas": self.default_gas_limit,
            }
            
            # Use EIP-1559 gas parameters if supported
            if self._supports_eip1559():
                tx_params["maxFeePerGas"] = self.web3.to_wei(gas_price["max_fee_per_gas"], "gwei")
                tx_params["maxPriorityFeePerGas"] = self.web3.to_wei(gas_price["max_priority_fee_per_gas"], "gwei")
            else:
                # Fall back to legacy gas price
                tx_params["gasPrice"] = self.web3.eth.gas_price
            
            # Execute the appropriate swap function based on token types
            if is_eth_in and not is_eth_out:
                # ETH to Token
                tx_params["to"] = self.router_contract.address
                tx_params["value"] = amount_in_wei
                
                swap_function = self.router_contract.functions.swapExactETHForTokens(
                    amount_out_min,
                    path,
                    self.address,
                    deadline
                )
                
                tx_params["data"] = swap_function._encode_transaction_data()
                
            elif not is_eth_in and is_eth_out:
                # Token to ETH
                # First, check and approve token if needed
                await self._ensure_token_approval(token_in, UNISWAP_ROUTER_ADDRESS, amount_in_wei)
                
                swap_function = self.router_contract.functions.swapExactTokensForETH(
                    amount_in_wei,
                    amount_out_min,
                    path,
                    self.address,
                    deadline
                )
                
                tx_params["to"] = self.router_contract.address
                tx_params["data"] = swap_function._encode_transaction_data()
                
            elif not is_eth_in and not is_eth_out:
                # Token to Token
                # First, check and approve token if needed
                await self._ensure_token_approval(token_in, UNISWAP_ROUTER_ADDRESS, amount_in_wei)
                
                swap_function = self.router_contract.functions.swapExactTokensForTokens(
                    amount_in_wei,
                    amount_out_min,
                    path,
                    self.address,
                    deadline
                )
                
                tx_params["to"] = self.router_contract.address
                tx_params["data"] = swap_function._encode_transaction_data()
                
            else:
                # ETH to ETH - doesn't make sense
                raise SwapError("Cannot swap ETH to ETH")
            
            # Execute the transaction
            result = await self.execute_transaction(tx_params)
            
            # Add swap-specific information to the result
            result["swap_info"] = {
                "token_in": token_in,
                "token_out": token_out,
                "amount_in": amount_in,
                "path": path,
                "slippage": slippage,
                "deadline": deadline
            }
            
            return result
        
        except Exception as e:
            logger.error(f"Error executing swap: {e}")
            if isinstance(e, TransactionError):
                raise SwapError(f"Swap failed: {e}")
            raise SwapError(f"Failed to execute swap: {e}")
    
    async def check_token_approval(self, token_address: str, spender_address: str, amount: Optional[int] = None) -> bool:
        """
        Check if a token is approved for spending by a spender.
        
        Args:
            token_address: Address of the token
            spender_address: Address of the spender
            amount: Amount to check approval for (default: None, checks any approval)
            
        Returns:
            True if the token is approved, False otherwise
        """
        if not self.connected:
            raise ConnectionError("Not connected to Ethereum")
        
        try:
            token_contract = await self._get_token_contract(token_address)
            
            # Get current allowance
            allowance = token_contract.functions.allowance(
                self.address,
                Web3.to_checksum_address(spender_address)
            ).call()
            
            # If amount is specified, check if allowance is sufficient
            if amount is not None:
                return allowance >= amount
            
            # Otherwise, check if there's any allowance
            return allowance > 0
        
        except Exception as e:
            logger.error(f"Error checking token approval: {e}")
            raise ApprovalError(f"Failed to check token approval: {e}")
    
    async def approve_token(self, token_address: str, spender_address: str, amount: int, 
                           gas_priority: str = "normal") -> Dict[str, Any]:
        """
        Approve a token for spending by a spender.
        
        Args:
            token_address: Address of the token
            spender_address: Address of the spender
            amount: Amount to approve
            gas_priority: Gas priority level (slow, normal, fast)
            
        Returns:
            Approval transaction result
        """
        if not self.connected:
            raise ConnectionError("Not connected to Ethereum")
        
        if not self.private_key:
            raise ApprovalError("Private key not provided")
        
        try:
            token_contract = await self._get_token_contract(token_address)
            
            # Get gas price based on priority
            gas_price = get_gas_price_level("ethereum", gas_priority)
            
            # Prepare transaction parameters
            tx_params = {
                "from": self.address,
                "to": token_contract.address,
                "gas": 100000,  # Gas limit for approval is typically lower
            }
            
            # Use EIP-1559 gas parameters if supported
            if self._supports_eip1559():
                tx_params["maxFeePerGas"] = self.web3.to_wei(gas_price["max_fee_per_gas"], "gwei")
                tx_params["maxPriorityFeePerGas"] = self.web3.to_wei(gas_price["max_priority_fee_per_gas"], "gwei")
            else:
                # Fall back to legacy gas price
                tx_params["gasPrice"] = self.web3.eth.gas_price
            
            # Encode approval function call
            approve_function = token_contract.functions.approve(
                Web3.to_checksum_address(spender_address),
                amount
            )
            
            tx_params["data"] = approve_function._encode_transaction_data()
            
            # Execute the transaction
            result = await self.execute_transaction(tx_params)
            
            # Add approval-specific information to the result
            result["approval_info"] = {
                "token_address": token_address,
                "spender_address": spender_address,
                "amount": amount
            }
            
            return result
        
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
        if not self.connected:
            raise ConnectionError("Not connected to Ethereum")
        
        try:
            # Convert string hash to bytes if needed
            if isinstance(tx_hash, str):
                tx_hash = Web3.to_bytes(hexstr=tx_hash)
            
            # Wait for transaction receipt with timeout
            start_time = time.time()
            while True:
                try:
                    receipt = self.web3.eth.get_transaction_receipt(tx_hash)
                    if receipt is not None:
                        return dict(receipt)
                except TransactionNotFound:
                    pass
                
                # Check timeout
                if time.time() - start_time > timeout_seconds:
                    raise TransactionTimeoutError(f"Transaction {tx_hash.hex()} timed out after {timeout_seconds} seconds")
                
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
        if not self.connected:
            raise ConnectionError("Not connected to Ethereum")
        
        try:
            # Convert string hash to bytes if needed
            if isinstance(tx_hash, str):
                tx_hash = Web3.to_bytes(hexstr=tx_hash)
            
            # Try to get transaction receipt
            try:
                receipt = self.web3.eth.get_transaction_receipt(tx_hash)
                if receipt is not None:
                    status = "confirmed" if receipt["status"] == 1 else "failed"
                    return {
                        "tx_hash": tx_hash.hex(),
                        "status": status,
                        "block_number": receipt["blockNumber"],
                        "gas_used": receipt["gasUsed"],
                        "receipt": dict(receipt)
                    }
            except TransactionNotFound:
                pass
            
            # If no receipt, try to get transaction
            try:
                tx = self.web3.eth.get_transaction(tx_hash)
                if tx is not None:
                    return {
                        "tx_hash": tx_hash.hex(),
                        "status": "pending",
                        "from": tx["from"],
                        "to": tx["to"],
                        "value": tx["value"],
                        "gas": tx["gas"],
                        "gas_price": tx["gasPrice"],
                        "nonce": tx["nonce"],
                        "transaction": dict(tx)
                    }
            except TransactionNotFound:
                pass
            
            # If neither found, transaction is unknown
            return {
                "tx_hash": tx_hash.hex(),
                "status": "unknown"
            }
        
        except Exception as e:
            logger.error(f"Error getting transaction status: {e}")
            raise TransactionError(f"Failed to get transaction status: {e}")
    
    # Helper methods
    
    async def _get_token_contract(self, token_address: str) -> Any:
        """
        Get a token contract instance.
        
        Args:
            token_address: Address of the token
            
        Returns:
            Token contract instance
        """
        if token_address in self.token_contracts:
            return self.token_contracts[token_address]
        
        checksum_address = Web3.to_checksum_address(token_address)
        contract = self.web3.eth.contract(address=checksum_address, abi=ERC20_ABI)
        self.token_contracts[token_address] = contract
        
        return contract
    
    async def _get_token_decimals(self, token_address: str) -> int:
        """
        Get the number of decimals for a token.
        
        Args:
            token_address: Address of the token
            
        Returns:
            Number of decimals
        """
        token_contract = await self._get_token_contract(token_address)
        return token_contract.functions.decimals().call()
    
    async def _ensure_token_approval(self, token_address: str, spender_address: str, amount: int) -> None:
        """
        Ensure a token is approved for spending by a spender.
        
        Args:
            token_address: Address of the token
            spender_address: Address of the spender
            amount: Amount to approve
        """
        is_approved = await self.check_token_approval(token_address, spender_address, amount)
        if not is_approved:
            logger.info(f"Approving {token_address} for {spender_address}")
            await self.approve_token(token_address, spender_address, amount)
    
    def _supports_eip1559(self) -> bool:
        """
        Check if the connected network supports EIP-1559.
        
        Returns:
            True if EIP-1559 is supported, False otherwise
        """
        try:
            # Check if the latest block has baseFeePerGas
            latest_block = self.web3.eth.get_block("latest")
            return "baseFeePerGas" in latest_block
        except Exception:
            return False 