"""
Solana client wrapper to abstract solana-py and solders functionality.

This module provides a wrapper around the Solana client libraries to handle
common operations with proper error handling and type safety.
"""
import json
import logging
from typing import Any, Dict, List, Optional, Tuple, Union, cast

from gbpbot.utils.solana_imports import (
    AsyncClient, Keypair, PublicKey, TxOpts, 
    Pubkey, Signature, SoldersTransaction, Message, Instruction,
    GetBalanceResp, GetSignatureStatusesResp, GetTransactionResp, 
    SendTransactionResp, GetTokenAccountsByOwnerResp, TransactionStatus,
    to_pubkey, to_signature, public_key_to_pubkey, safe_get_item,
    SOLANA_AVAILABLE, SOLDERS_AVAILABLE, SPL_TOKEN_AVAILABLE,
    check_solana_availability
)

logger = logging.getLogger(__name__)

class SolanaClientWrapper:
    """
    Wrapper around Solana client libraries to provide a simplified interface
    with proper error handling and type safety.
    """
    
    def __init__(self, rpc_url: str, commitment: str = "confirmed"):
        """
        Initialize the Solana client wrapper.
        
        Args:
            rpc_url: The URL of the Solana RPC endpoint
            commitment: The commitment level to use for transactions
        
        Raises:
            ImportError: If required Solana packages are not installed
        """
        if not check_solana_availability():
            raise ImportError(
                "Solana packages are not properly installed. Please run: "
                "pip install solana-py==0.30.2 solders==0.18.1 anchorpy==0.18.0"
            )
        
        self._client = AsyncClient(rpc_url, commitment=commitment)
        self._keypair = None
        self._timeout = 60  # Default timeout in seconds
        
    async def connect(self) -> bool:
        """
        Connect to the Solana network and verify connection.
        
        Returns:
            True if connection is successful, False otherwise
        """
        try:
            # Test the connection by getting the latest blockhash
            await self._client.get_latest_blockhash()
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Solana: {str(e)}")
            return False
            
    async def close(self) -> None:
        """Close the connection to the Solana network."""
        if self._client:
            await self._client.close()
    
    def set_keypair(self, keypair: Union[Keypair, str]) -> None:
        """
        Set the keypair to use for signing transactions.
        
        Args:
            keypair: The keypair object or a base58 encoded private key string
        """
        if isinstance(keypair, str):
            self._keypair = Keypair.from_secret_key(bytes.fromhex(keypair))
        else:
            self._keypair = keypair
    
    @property
    def keypair(self) -> Optional[Keypair]:
        """Get the current keypair."""
        return self._keypair
    
    @property
    def public_key(self) -> Optional[Pubkey]:
        """Get the public key of the current keypair."""
        if self._keypair:
            return public_key_to_pubkey(self._keypair.public_key)
        return None
    
    async def get_balance(self, pubkey: Union[str, Pubkey] = None) -> float:
        """
        Get the SOL balance of an account.
        
        Args:
            pubkey: The public key to check, or None to use the current keypair
            
        Returns:
            The balance in SOL (lamports / 10^9)
            
        Raises:
            ValueError: If no keypair is set and no pubkey is provided
        """
        if pubkey is None:
            if self._keypair is None:
                raise ValueError("No keypair set and no pubkey provided")
            pubkey = public_key_to_pubkey(self._keypair.public_key)
            
        if isinstance(pubkey, str):
            pubkey = to_pubkey(pubkey)
            
        response = await self._client.get_balance(pubkey)
        
        # Convert from lamports to SOL
        balance = safe_get_item(response.value, "amount", 0) / 1_000_000_000
        return balance
    
    async def get_token_accounts(self, pubkey: Union[str, Pubkey] = None) -> List[Dict[str, Any]]:
        """
        Get all token accounts owned by an address.
        
        Args:
            pubkey: The public key to check, or None to use the current keypair
            
        Returns:
            List of token account data
            
        Raises:
            ValueError: If no keypair is set and no pubkey is provided
        """
        if pubkey is None:
            if self._keypair is None:
                raise ValueError("No keypair set and no pubkey provided")
            pubkey = public_key_to_pubkey(self._keypair.public_key)
            
        if isinstance(pubkey, str):
            pubkey = to_pubkey(pubkey)
            
        opts = {
            "encoding": "jsonParsed"
        }
            
        response = await self._client.get_token_accounts_by_owner(pubkey, opts)
        
        accounts = []
        if "value" in response:
            for account in safe_get_item(response, "value", []):
                if account and "account" in account and "data" in account["account"]:
                    accounts.append(account["account"]["data"]["parsed"]["info"])
                    
        return accounts
    
    async def get_token_balance(self, token_address: str, pubkey: Union[str, Pubkey] = None) -> float:
        """
        Get the balance of a specific token for an address.
        
        Args:
            token_address: The token mint address
            pubkey: The public key to check, or None to use the current keypair
            
        Returns:
            The token balance as a float
            
        Raises:
            ValueError: If no keypair is set and no pubkey is provided
        """
        accounts = await self.get_token_accounts(pubkey)
        
        for account in accounts:
            if account.get("mint") == token_address:
                # Get the token decimals and amount
                decimals = int(account.get("tokenAmount", {}).get("decimals", 0))
                amount = account.get("tokenAmount", {}).get("amount", "0")
                
                # Convert to float based on decimals
                return float(amount) / (10 ** decimals)
                
        return 0.0  # Return 0 if no token account found
    
    async def sign_transaction(self, transaction: SoldersTransaction) -> SoldersTransaction:
        """
        Sign a transaction with the current keypair.
        
        Args:
            transaction: The transaction to sign
            
        Returns:
            The signed transaction
            
        Raises:
            ValueError: If no keypair is set
        """
        if self._keypair is None:
            raise ValueError("No keypair set for signing")
            
        # Add the keypair as a signer
        return transaction.sign([self._keypair])
    
    async def send_transaction(self, transaction: SoldersTransaction) -> str:
        """
        Send a transaction to the Solana network.
        
        Args:
            transaction: The transaction to send
            
        Returns:
            The transaction signature (txid)
        """
        response = await self._client.send_transaction(transaction)
        
        # Return the transaction signature
        if hasattr(response, "value"):
            return response.value
        return str(response)  # Fallback in case value is not accessible
    
    async def confirm_transaction(self, signature: Union[str, Signature], timeout: int = None) -> bool:
        """
        Wait for a transaction to be confirmed.
        
        Args:
            signature: The transaction signature to confirm
            timeout: Optional timeout in seconds (overrides default)
            
        Returns:
            True if transaction is confirmed, False if timed out
        """
        if isinstance(signature, str):
            signature = to_signature(signature)
            
        if timeout is None:
            timeout = self._timeout
            
        try:
            # Confirm the transaction with the specified timeout
            await self._client.confirm_transaction(signature, timeout=timeout)
            return True
        except Exception as e:
            logger.error(f"Transaction confirmation failed: {str(e)}")
            return False
    
    async def get_transaction_status(self, signature: Union[str, Signature]) -> Dict[str, Any]:
        """
        Get the status of a transaction.
        
        Args:
            signature: The transaction signature to check
            
        Returns:
            Dictionary with transaction status
        """
        if isinstance(signature, str):
            signature = to_signature(signature)
            
        response = await self._client.get_signature_statuses([signature])
        
        if "value" in response and response["value"]:
            status = response["value"][0]
            if status:
                # Format the status data for easier consumption
                return {
                    "confirmed": status.get("confirmationStatus") == "confirmed",
                    "finalized": status.get("confirmationStatus") == "finalized",
                    "confirmations": status.get("confirmations", 0),
                    "err": status.get("err")
                }
        
        # Transaction not found or no status
        return {
            "confirmed": False,
            "finalized": False,
            "confirmations": 0,
            "err": "Transaction not found"
        }
    
    async def get_transaction(self, signature: Union[str, Signature]) -> Dict[str, Any]:
        """
        Get the details of a transaction.
        
        Args:
            signature: The transaction signature
            
        Returns:
            Dictionary with transaction details
        """
        if isinstance(signature, str):
            signature = to_signature(signature)
            
        response = await self._client.get_transaction(signature)
        
        if response and hasattr(response, "value") and response.value:
            return json.loads(json.dumps(response.value))
        
        return {}  # Return empty dict if transaction not found 