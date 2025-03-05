#!/usr/bin/env python3
"""
Example of using the Solana blockchain client.

This example demonstrates how to use the Solana client to:
1. Connect to the Solana blockchain
2. Get SOL and token balances
3. Execute a transaction
4. Check transaction status
"""

import asyncio
import base64
import logging
import os
import sys
from dotenv import load_dotenv

# Add the parent directory to the path so we can import the gbpbot package
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gbpbot.core.blockchain.base import BlockchainClientFactory
from gbpbot.utils.exceptions import BlockchainError
from gbpbot.utils.solana_imports import (
    check_solana_dependencies, get_dependency_status, 
    TransactionInstruction, PublicKey
)

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
    logger.warning("Install required packages with: pip install solana-py solders anchorpy")

# Solana configuration
SOLANA_CONFIG = {
    "rpc_url": os.getenv("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com"),
    "private_key": os.getenv("SOLANA_PRIVATE_KEY"),
    "default_compute_units": int(os.getenv("SOLANA_COMPUTE_UNITS", "200000"))
}

# Token addresses
USDC_MINT = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
WRAPPED_SOL_MINT = "So11111111111111111111111111111111111111112"


async def main():
    """Run the Solana client example."""
    try:
        # Create a Solana client
        logger.info("Creating Solana client...")
        client = BlockchainClientFactory.get_client("solana", SOLANA_CONFIG)
        
        # Connect to the Solana blockchain
        logger.info("Connecting to Solana...")
        connected = await client.connect()
        if not connected:
            logger.error("Failed to connect to Solana")
            return
        
        logger.info("Connected to Solana")
        
        try:
            # Get SOL balance
            sol_balance = await client.get_balance("SOL")
            logger.info(f"SOL balance: {sol_balance}")
            
            # Get USDC balance (if we have a wallet configured)
            try:
                usdc_balance = await client.get_balance(USDC_MINT)
                logger.info(f"USDC balance: {usdc_balance}")
            except Exception as e:
                logger.warning(f"Could not get USDC balance: {e}")
            
            # Check if we have enough SOL to continue with examples
            if sol_balance < 0.01:
                logger.warning("Not enough SOL to continue with transaction examples")
                return
            
            # Example: Create and execute a simple transaction
            # This example creates a transaction that transfers a small amount of SOL
            logger.info("Creating a simple SOL transfer transaction...")
            
            # Check if we have the required dependencies for this example
            if not all([SOLANA_DEPS.get("solana"), SOLANA_DEPS.get("solders")]):
                logger.warning("Missing required dependencies for transaction example")
                return
            
            try:
                # Create a simple transfer instruction
                # This is just an example - in a real application, you would use
                # the appropriate program instructions for your use case
                
                # Example recipient address
                recipient = PublicKey("9B5XszUGdMaxCZ7uSQhPzdks5ZQSmWxrmzCSvtJ6Ns6g")
                
                # Create a System Program transfer instruction
                # In a real application, you would import the SystemProgram from solana.system_program
                system_program_id = PublicKey("11111111111111111111111111111111")
                
                # We're using a simplified approach here for the example
                # Normally you would use the proper instruction builders from solana-py
                
                # Execute the transaction
                logger.info("Executing the transaction...")
                tx_params = {
                    "instructions": [
                        # This is a placeholder - in a real application you would
                        # create a proper transfer instruction
                        TransactionInstruction(
                            keys=[
                                {"pubkey": client.public_key, "is_signer": True, "is_writable": True},
                                {"pubkey": recipient, "is_signer": False, "is_writable": True},
                                {"pubkey": system_program_id, "is_signer": False, "is_writable": False}
                            ],
                            program_id=system_program_id,
                            data=bytes([2, 0, 0, 0]) + (1000000).to_bytes(8, byteorder="little")  # 0.001 SOL
                        )
                    ],
                    "wait_for_confirmation": True
                }
                
                tx_result = await client.execute_transaction(tx_params)
                logger.info(f"Transaction result: {tx_result}")
                
                # Check transaction status
                if "tx_hash" in tx_result:
                    status = await client.get_transaction_status(tx_result["tx_hash"])
                    logger.info(f"Transaction status: {status}")
            
            except Exception as e:
                logger.error(f"Error executing transaction: {e}")
            
        finally:
            # Disconnect from Solana
            logger.info("Disconnecting from Solana...")
            await client.disconnect()
            logger.info("Disconnected from Solana")
    
    except BlockchainError as e:
        logger.error(f"Blockchain error: {e}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")


if __name__ == "__main__":
    asyncio.run(main()) 