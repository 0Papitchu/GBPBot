#!/usr/bin/env python3
"""
Example of using multiple blockchain clients simultaneously.

This example demonstrates how to:
1. Connect to multiple blockchains (Ethereum and Solana)
2. Get balances across different chains
3. Execute operations in parallel
4. Handle blockchain-specific configurations
"""

import asyncio
import logging
import os
import sys
from dotenv import load_dotenv
from typing import Dict, List, Any

# Add the parent directory to the path so we can import the gbpbot package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gbpbot.core.blockchain.base import BlockchainClientFactory, BaseBlockchainClient
from gbpbot.utils.exceptions import BlockchainError
from gbpbot.utils.solana_imports import check_solana_dependencies, get_dependency_status

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Check Solana dependencies
SOLANA_DEPS = check_solana_dependencies()
if not all(SOLANA_DEPS.values()):
    logger.warning(f"Some Solana dependencies are missing: {get_dependency_status()}")

# Blockchain configurations
BLOCKCHAIN_CONFIGS = {
    "ethereum": {
        "rpc_url": os.getenv("ETHEREUM_RPC_URL", "https://mainnet.infura.io/v3/your-api-key"),
        "private_key": os.getenv("ETHEREUM_PRIVATE_KEY"),
        "chain_id": int(os.getenv("ETHEREUM_CHAIN_ID", "1")),
        "gas_limit": int(os.getenv("ETHEREUM_GAS_LIMIT", "200000")),
        "gas_price_strategy": os.getenv("ETHEREUM_GAS_PRICE_STRATEGY", "medium")
    },
    "polygon": {
        "rpc_url": os.getenv("POLYGON_RPC_URL", "https://polygon-rpc.com"),
        "private_key": os.getenv("ETHEREUM_PRIVATE_KEY"),  # Same key for EVM chains
        "chain_id": int(os.getenv("POLYGON_CHAIN_ID", "137")),
        "gas_limit": int(os.getenv("POLYGON_GAS_LIMIT", "200000")),
        "gas_price_strategy": os.getenv("POLYGON_GAS_PRICE_STRATEGY", "medium")
    },
    "solana": {
        "rpc_url": os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com"),
        "private_key": os.getenv("SOLANA_PRIVATE_KEY"),
        "default_compute_units": int(os.getenv("SOLANA_COMPUTE_UNITS", "200000"))
    }
}

# Token addresses by chain
TOKEN_ADDRESSES = {
    "ethereum": {
        "native": "ETH",
        "usdc": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
        "usdt": "0xdAC17F958D2ee523a2206206994597C13D831ec7"
    },
    "polygon": {
        "native": "MATIC",
        "usdc": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174",
        "usdt": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F"
    },
    "solana": {
        "native": "SOL",
        "usdc": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
        "usdt": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"
    }
}


class MultiChainManager:
    """Manager for handling multiple blockchain clients."""
    
    def __init__(self, configs: Dict[str, Dict[str, Any]]):
        """
        Initialize the multi-chain manager.
        
        Args:
            configs: Dictionary of blockchain configurations
        """
        self.configs = configs
        self.clients: Dict[str, BaseBlockchainClient] = {}
    
    async def connect_all(self) -> Dict[str, bool]:
        """
        Connect to all configured blockchains.
        
        Returns:
            Dictionary of connection results by blockchain
        """
        results = {}
        
        # Connect to each blockchain
        for blockchain, config in self.configs.items():
            try:
                logger.info(f"Connecting to {blockchain}...")
                client = BlockchainClientFactory.get_client(blockchain, config)
                connected = await client.connect()
                
                if connected:
                    self.clients[blockchain] = client
                    results[blockchain] = True
                    logger.info(f"Connected to {blockchain}")
                else:
                    results[blockchain] = False
                    logger.error(f"Failed to connect to {blockchain}")
            
            except Exception as e:
                results[blockchain] = False
                logger.error(f"Error connecting to {blockchain}: {e}")
        
        return results
    
    async def disconnect_all(self) -> None:
        """Disconnect from all connected blockchains."""
        for blockchain, client in self.clients.items():
            try:
                logger.info(f"Disconnecting from {blockchain}...")
                await client.disconnect()
                logger.info(f"Disconnected from {blockchain}")
            
            except Exception as e:
                logger.error(f"Error disconnecting from {blockchain}: {e}")
    
    async def get_balances(self, tokens: List[str] = ["native", "usdc"]) -> Dict[str, Dict[str, float]]:
        """
        Get balances for specified tokens across all connected blockchains.
        
        Args:
            tokens: List of token types to check (e.g., "native", "usdc")
            
        Returns:
            Dictionary of balances by blockchain and token
        """
        balances = {}
        
        # Get balances for each blockchain
        for blockchain, client in self.clients.items():
            balances[blockchain] = {}
            
            for token in tokens:
                if token in TOKEN_ADDRESSES.get(blockchain, {}):
                    token_address = TOKEN_ADDRESSES[blockchain][token]
                    
                    try:
                        balance = await client.get_balance(token_address)
                        balances[blockchain][token] = balance
                    
                    except Exception as e:
                        balances[blockchain][token] = None
                        logger.error(f"Error getting {token} balance on {blockchain}: {e}")
        
        return balances
    
    async def execute_parallel_operations(self) -> Dict[str, Any]:
        """
        Execute operations in parallel across all connected blockchains.
        
        Returns:
            Dictionary of results by blockchain
        """
        results = {}
        
        # Create tasks for parallel execution
        tasks = []
        for blockchain, client in self.clients.items():
            # Example: Get native token balance
            task = asyncio.create_task(
                self._get_balance_with_metadata(blockchain, client, "native")
            )
            tasks.append(task)
        
        # Wait for all tasks to complete
        completed_tasks = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for result in completed_tasks:
            if isinstance(result, Exception):
                logger.error(f"Error in parallel operation: {result}")
            elif isinstance(result, dict) and "blockchain" in result:
                blockchain = result.pop("blockchain")
                results[blockchain] = result
        
        return results
    
    async def _get_balance_with_metadata(self, blockchain: str, client: BaseBlockchainClient, token_type: str) -> Dict[str, Any]:
        """
        Get balance with metadata for a specific blockchain and token.
        
        Args:
            blockchain: Blockchain name
            client: Blockchain client
            token_type: Type of token (e.g., "native", "usdc")
            
        Returns:
            Dictionary with balance and metadata
        """
        try:
            token_address = TOKEN_ADDRESSES.get(blockchain, {}).get(token_type)
            if not token_address:
                return {
                    "blockchain": blockchain,
                    "token": token_type,
                    "balance": None,
                    "error": "Token address not found"
                }
            
            balance = await client.get_balance(token_address)
            
            return {
                "blockchain": blockchain,
                "token": token_type,
                "token_address": token_address,
                "balance": balance,
                "timestamp": asyncio.get_event_loop().time()
            }
        
        except Exception as e:
            return {
                "blockchain": blockchain,
                "token": token_type,
                "balance": None,
                "error": str(e)
            }


async def main():
    """Run the multi-chain example."""
    try:
        # Create multi-chain manager
        manager = MultiChainManager(BLOCKCHAIN_CONFIGS)
        
        # Connect to all blockchains
        connection_results = await manager.connect_all()
        logger.info(f"Connection results: {connection_results}")
        
        if not any(connection_results.values()):
            logger.error("Failed to connect to any blockchain")
            return
        
        try:
            # Get balances across all chains
            logger.info("Getting balances across all chains...")
            balances = await manager.get_balances(["native", "usdc", "usdt"])
            
            # Display balances
            for blockchain, tokens in balances.items():
                logger.info(f"--- {blockchain.upper()} Balances ---")
                for token, balance in tokens.items():
                    if balance is not None:
                        logger.info(f"{token}: {balance}")
                    else:
                        logger.info(f"{token}: Error retrieving balance")
            
            # Execute parallel operations
            logger.info("Executing parallel operations...")
            parallel_results = await manager.execute_parallel_operations()
            logger.info(f"Parallel operation results: {parallel_results}")
            
        finally:
            # Disconnect from all blockchains
            await manager.disconnect_all()
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}")


if __name__ == "__main__":
    asyncio.run(main()) 