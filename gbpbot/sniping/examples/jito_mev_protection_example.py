#!/usr/bin/env python3
"""
Jito MEV Protection Example

This example demonstrates how to use the SolanaMemecoinSniper with Jito MEV protection
for frontrunning protection when entering and exiting positions.
"""

import os
import asyncio
import argparse
import logging
from datetime import datetime

from gbpbot.sniping.memecoin_sniper import SolanaMemecoinSniper
from gbpbot.utils.logging_utils import setup_logger

async def run_jito_protection_example(config_path: str, token_address: str, amount_usdc: float):
    """
    Run the Jito MEV protection example.
    
    Args:
        config_path: Path to configuration file
        token_address: Token address to use for the example
        amount_usdc: Amount of USDC to use for entry
    """
    # Setup logging
    logger = setup_logger("JitoExample", logging.INFO)
    logger.info(f"Starting Jito MEV protection example at {datetime.now().isoformat()}")
    
    try:
        # Initialize the memecoin sniper
        logger.info(f"Initializing Solana Memecoin Sniper with config: {config_path}")
        sniper = SolanaMemecoinSniper(config_path)
        
        # Connect to the blockchain
        logger.info("Connecting to Solana blockchain...")
        await sniper.connect()
        logger.info("Connected to Solana blockchain")
        
        # Check if Jito is enabled in the config
        jito_enabled = sniper.solana_config.get("jito_enabled", False)
        logger.info(f"Jito MEV protection enabled in config: {jito_enabled}")
        
        if jito_enabled:
            # Verify Jito auth token is set
            jito_auth_token = sniper.solana_config.get("jito_auth_token", "")
            if jito_auth_token == "" or jito_auth_token == "${JITO_AUTH_TOKEN}":
                logger.warning("Jito auth token not set! Set JITO_AUTH_TOKEN environment variable.")
                # Try to get from environment
                jito_auth_token = os.environ.get("JITO_AUTH_TOKEN", "")
                if not jito_auth_token:
                    logger.error("No Jito auth token found. MEV protection will fall back to regular transactions.")
        
        # Execute entry transaction with MEV protection
        logger.info(f"Executing entry transaction for token {token_address} with {amount_usdc} USDC")
        logger.info("Using Jito bundles for MEV protection")
        
        entry_result = await sniper.execute_entry_transaction(
            token_address=token_address,
            amount_usdc=amount_usdc,
            slippage=1.5
        )
        
        if entry_result.get("success", False):
            signature = entry_result.get("signature", "N/A")
            position = entry_result.get("position", {})
            mev_protected = position.get("mev_protected", False)
            
            logger.info(f"Entry transaction successful with signature: {signature}")
            logger.info(f"MEV Protection: {'Enabled' if mev_protected else 'Disabled'}")
            logger.info(f"Position details: {position}")
            
            # Wait for a moment to simulate some price action
            logger.info("Waiting 10 seconds before exiting position...")
            await asyncio.sleep(10)
            
            # Execute exit transaction with MEV protection
            # This will use Jito if the position value is above jito_exit_threshold
            # or if use_jito_for_exit is enabled in the config
            logger.info(f"Executing exit transaction for token {token_address}")
            
            exit_result = await sniper.execute_exit_transaction(
                token_address=token_address,
                percentage=100,  # Exit entire position
                slippage=2.0
            )
            
            if exit_result.get("success", False):
                exit_signature = exit_result.get("signature", "N/A")
                logger.info(f"Exit transaction successful with signature: {exit_signature}")
                logger.info(f"Percentage exited: {exit_result.get('percentage_exited', 0)}%")
            else:
                logger.error(f"Exit transaction failed: {exit_result.get('error', 'Unknown error')}")
        else:
            logger.error(f"Entry transaction failed: {entry_result.get('error', 'Unknown error')}")
    
    except Exception as e:
        logger.error(f"Error in Jito MEV protection example: {str(e)}")
    finally:
        # Ensure to close connections
        if 'sniper' in locals():
            await sniper.disconnect()
            logger.info("Disconnected from Solana blockchain")
    
    logger.info(f"Jito MEV protection example completed at {datetime.now().isoformat()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Jito MEV Protection Example")
    parser.add_argument("--config", type=str, default="config/solana_sniper_config.yaml",
                        help="Path to configuration file")
    parser.add_argument("--token", type=str, required=True,
                        help="Token address to execute the example with")
    parser.add_argument("--amount", type=float, default=10.0,
                        help="Amount of USDC to use for entry")
    
    args = parser.parse_args()
    
    # Run the async example
    asyncio.run(run_jito_protection_example(args.config, args.token, args.amount)) 