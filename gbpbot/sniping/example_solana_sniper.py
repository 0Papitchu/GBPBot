#!/usr/bin/env python3
"""
Example script demonstrating how to use the SolanaMemecoinSniper
"""

import os
import sys
import asyncio
import argparse
import json
import signal
import time
from typing import Dict, List, Optional

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from gbpbot.sniping.memecoin_sniper import SolanaMemecoinSniper
from gbpbot.utils.config_utils import load_config, save_config
from gbpbot.utils.logging_utils import setup_logger

# Global variables
sniper = None
logger = setup_logger("SniperExample")

async def run_sniper(config_path: str, duration_minutes: int = 0, test_mode: bool = False):
    """
    Run the Solana memecoin sniper
    
    Args:
        config_path: Path to the configuration file
        duration_minutes: Run duration in minutes (0 = run until stopped)
        test_mode: Whether to run in test mode (no real transactions)
    """
    global sniper
    
    try:
        # Load and modify config if test mode is enabled
        if test_mode:
            logger.info("Running in TEST MODE - No real transactions will be executed")
            config = load_config(config_path)
            
            # Set test wallet and limits
            if "solana" in config:
                if "security" in config["solana"]:
                    config["solana"]["security"]["max_allocation_per_token_usd"] = 10
                
                if "sniping" in config["solana"]:
                    if "execution" in config["solana"]["sniping"]:
                        config["solana"]["sniping"]["execution"]["simulation_mode"] = True
            
            # Save modified config to a temporary file
            temp_config_path = "config/temp_test_config.json"
            save_config(config, temp_config_path)
            config_path = temp_config_path
        
        # Initialize the sniper
        sniper = SolanaMemecoinSniper(config_path)
        
        # Start the sniper
        await sniper.start()
        logger.info(f"Solana Memecoin Sniper started successfully")
        
        # Register signal handlers
        register_signal_handlers()
        
        if duration_minutes > 0:
            # Run for specified duration
            logger.info(f"Running for {duration_minutes} minutes...")
            await asyncio.sleep(duration_minutes * 60)
            logger.info(f"Duration completed. Stopping sniper...")
            await sniper.stop()
        else:
            # Run until manually stopped
            logger.info("Running until manually stopped. Press Ctrl+C to stop.")
            
            # Keep the main task alive
            while True:
                # Print performance stats every minute
                await asyncio.sleep(60)
                stats = sniper.get_performance_stats()
                
                logger.info(f"Performance stats: "
                          f"{stats['tokens_analyzed']} tokens analyzed, "
                          f"{stats['tokens_sniped']} tokens sniped, "
                          f"{stats['successful_trades']} successful trades, "
                          f"{stats['profitable_trades']} profitable trades")
                
                # Print active positions
                active_positions = sniper.get_active_positions()
                if active_positions:
                    logger.info(f"Active positions: {len(active_positions)}")
                    for token_addr, position in active_positions.items():
                        profit_loss = position.get("profit_loss_pct", 0)
                        symbol = position.get("symbol", token_addr)
                        value = position.get("current_value_usd", 0)
                        logger.info(f"  {symbol}: ${value:.2f} ({profit_loss:.2f}%)")
    
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Stopping sniper...")
        if sniper:
            await sniper.stop()
    
    except Exception as e:
        logger.error(f"Error running sniper: {str(e)}")
        if sniper:
            await sniper.stop()
        raise

def signal_handler(sig, frame):
    """Handle termination signals"""
    logger.info(f"Signal {sig} received. Shutting down...")
    
    # Create and run a new event loop to stop the sniper
    if sniper:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(sniper.stop())
        finally:
            loop.close()
    
    sys.exit(0)

def register_signal_handlers():
    """Register signal handlers for graceful shutdown"""
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Solana Memecoin Sniper Example")
    
    parser.add_argument(
        "--config", 
        type=str, 
        default="config/solana_config.json",
        help="Path to configuration file"
    )
    
    parser.add_argument(
        "--duration", 
        type=int, 
        default=0,
        help="Run duration in minutes (0 = run until stopped)"
    )
    
    parser.add_argument(
        "--test", 
        action="store_true",
        help="Run in test mode (no real transactions)"
    )
    
    return parser.parse_args()

async def main():
    """Main function"""
    args = parse_arguments()
    
    # Run the sniper
    await run_sniper(
        config_path=args.config,
        duration_minutes=args.duration,
        test_mode=args.test
    )

if __name__ == "__main__":
    asyncio.run(main()) 