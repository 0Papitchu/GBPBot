#!/usr/bin/env python3
"""
Example of using the Ethereum blockchain client.

This example demonstrates how to use the Ethereum client to:
1. Connect to the Ethereum blockchain
2. Get ETH and token balances
3. Execute a transaction
4. Execute a token swap
5. Check and approve token spending
"""

import asyncio
import logging
import os
import sys
from dotenv import load_dotenv

# Add the parent directory to the path so we can import the gbpbot package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gbpbot.core.blockchain.base import BlockchainClientFactory
from gbpbot.utils.exceptions import BlockchainError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Ethereum configuration
ETHEREUM_CONFIG = {
    "rpc_url": os.getenv("ETHEREUM_RPC_URL", "https://mainnet.infura.io/v3/your-api-key"),
    "private_key": os.getenv("ETHEREUM_PRIVATE_KEY"),
    "chain_id": int(os.getenv("ETHEREUM_CHAIN_ID", "1")),
    "gas_limit": int(os.getenv("ETHEREUM_GAS_LIMIT", "200000")),
    "gas_price_strategy": os.getenv("ETHEREUM_GAS_PRICE_STRATEGY", "medium")
}

# Token addresses
WETH_ADDRESS = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
USDC_ADDRESS = "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
UNISWAP_ROUTER = "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D"


async def main():
    """Run the Ethereum client example."""
    try:
        # Create an Ethereum client
        logger.info("Creating Ethereum client...")
        client = BlockchainClientFactory.get_client("ethereum", ETHEREUM_CONFIG)
        
        # Connect to the Ethereum blockchain
        logger.info("Connecting to Ethereum...")
        connected = await client.connect()
        if not connected:
            logger.error("Failed to connect to Ethereum")
            return
        
        logger.info("Connected to Ethereum")
        
        try:
            # Get ETH balance
            eth_balance = await client.get_balance("ETH")
            logger.info(f"ETH balance: {eth_balance}")
            
            # Get USDC balance
            usdc_balance = await client.get_balance(USDC_ADDRESS)
            logger.info(f"USDC balance: {usdc_balance}")
            
            # Get token price
            eth_price = await client.get_token_price(WETH_ADDRESS, USDC_ADDRESS)
            logger.info(f"ETH price in USDC: {eth_price}")
            
            # Check if we have enough ETH to continue with examples
            if eth_balance < 0.01:
                logger.warning("Not enough ETH to continue with transaction examples")
                return
            
            # Example: Send a small amount of ETH
            logger.info("Executing a small ETH transaction...")
            tx_params = {
                "to": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",  # Example address
                "value": 0.001 * 10**18,  # 0.001 ETH in wei
                "gas_priority": "normal"
            }
            
            tx_result = await client.execute_transaction(tx_params)
            logger.info(f"Transaction result: {tx_result}")
            
            # Example: Check token approval
            logger.info("Checking USDC approval for Uniswap...")
            is_approved = await client.check_token_approval(
                USDC_ADDRESS, 
                UNISWAP_ROUTER,
                1000 * 10**6  # 1000 USDC (6 decimals)
            )
            logger.info(f"USDC approved for Uniswap: {is_approved}")
            
            # Example: Approve token if not already approved
            if not is_approved and usdc_balance > 0:
                logger.info("Approving USDC for Uniswap...")
                approval_result = await client.approve_token(
                    USDC_ADDRESS,
                    UNISWAP_ROUTER,
                    2**256 - 1,  # Infinite approval
                    "normal"
                )
                logger.info(f"Approval result: {approval_result}")
                
                # Wait for approval to be confirmed
                if "tx_hash" in approval_result:
                    await client.wait_for_transaction(approval_result["tx_hash"])
                    logger.info("Approval confirmed")
            
            # Example: Execute a token swap (if we have USDC)
            if usdc_balance > 10:
                logger.info("Executing a USDC to ETH swap...")
                swap_result = await client.execute_swap(
                    USDC_ADDRESS,  # Token in
                    "ETH",         # Token out
                    10,            # Amount in (10 USDC)
                    0.5,           # 0.5% slippage
                    300,           # 5 minutes deadline
                    "normal"       # Gas priority
                )
                logger.info(f"Swap result: {swap_result}")
            
        finally:
            # Disconnect from Ethereum
            logger.info("Disconnecting from Ethereum...")
            await client.disconnect()
            logger.info("Disconnected from Ethereum")
    
    except BlockchainError as e:
        logger.error(f"Blockchain error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")


if __name__ == "__main__":
    asyncio.run(main()) 