#!/usr/bin/env python
"""
Main entry point for the GBP Bot application.

This module provides the main entry point for the application, including
command-line argument parsing and initialization of the application components.
"""

import argparse
import asyncio
import logging
import sys
import os
import time
from typing import Dict, List, Optional, Any, Union

from gbpbot.core.blockchain.base import BlockchainClientFactory
from gbpbot.utils.config import get_config
from gbpbot.utils.environment import print_environment_report, check_environment_ready
from gbpbot.utils.exceptions import GBPBotError, ConfigurationError


class GBPBot:
    """
    Main class for the GBP Bot application.
    
    This class manages the lifecycle of the bot, including initialization,
    running strategies, and cleanup.
    """
    
    def __init__(self, config_path: Optional[str] = None, debug: bool = False, 
                 simulation_mode: bool = False, is_testnet: bool = False):
        """
        Initialize the GBP Bot.
        
        Args:
            config_path: Path to configuration file (optional)
            debug: Enable debug logging
            simulation_mode: Run in simulation mode without real transactions
            is_testnet: Use testnet instead of mainnet
        """
        # Configure logging
        self._setup_logging(debug)
        
        # Set mode flags
        self.simulation_mode = simulation_mode
        self.is_testnet = is_testnet
        
        # Load configuration
        self.config = get_config(config_path)
        logging.info(f"GBPBot initialized with configuration (simulation_mode={simulation_mode}, is_testnet={is_testnet})")
        
        # Initialize blockchain clients
        self.blockchain_clients = {}
        self.active_strategies = {}
        self.running = False
        
        # For compatibility with existing code
        self.blockchain = None
    
    def _setup_logging(self, debug: bool = False):
        """
        Set up logging configuration.
        
        Args:
            debug: Enable debug logging
        """
        log_level = logging.DEBUG if debug else logging.INFO
        
        # Configure root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        
        # Clear existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Add console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ))
        root_logger.addHandler(console_handler)
        
        # Add file logging
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        
        file_handler = logging.FileHandler(
            os.path.join(log_dir, f"gbpbot_{time.strftime('%Y-%m-%d')}.log")
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ))
        
        root_logger.addHandler(file_handler)
        logging.info(f"Logging configured with level {logging.getLevelName(log_level)}")
    
    async def initialize(self) -> bool:
        """
        Initialize the bot and connect to blockchains.
        
        Returns:
            True if initialization was successful, False otherwise
        """
        try:
            # Get enabled blockchains from config
            enabled_blockchains = self._get_enabled_blockchains()
            
            if not enabled_blockchains:
                logging.error("No blockchains enabled in configuration")
                return False
            
            # Initialize blockchain clients
            for blockchain_type in enabled_blockchains:
                try:
                    # Check if blockchain is ready
                    ready, missing = check_environment_ready(blockchain_type)
                    if not ready:
                        logging.error(f"Missing dependencies for {blockchain_type}: {', '.join(missing)}")
                        continue
                    
                    # Get blockchain configuration
                    blockchain_config = self._get_blockchain_config(blockchain_type)
                    
                    # Create blockchain client
                    client = BlockchainClientFactory.get_client(blockchain_type, blockchain_config)
                    
                    # Connect to blockchain
                    logging.info(f"Connecting to {blockchain_type}...")
                    connected = await client.connect()
                    
                    if connected:
                        logging.info(f"Successfully connected to {blockchain_type}")
                        self.blockchain_clients[blockchain_type] = client
                    else:
                        logging.error(f"Failed to connect to {blockchain_type}")
                
                except Exception as e:
                    logging.exception(f"Error initializing {blockchain_type}: {e}")
            
            if not self.blockchain_clients:
                logging.error("Failed to initialize any blockchain clients")
                return False
            
            # Initialize strategies
            await self._initialize_strategies()
            
            logging.info("GBPBot initialization complete")
            return True
        
        except Exception as e:
            logging.exception(f"Error during initialization: {e}")
            return False
    
    def _get_enabled_blockchains(self) -> List[str]:
        """
        Get list of enabled blockchains from configuration.
        
        Returns:
            List of enabled blockchain types
        """
        try:
            blockchains = self.config.get("blockchains", {})
            return [name for name, config in blockchains.items() if config.get("enabled", False)]
        except Exception as e:
            logging.error(f"Error getting enabled blockchains: {e}")
            return []
    
    def _get_blockchain_config(self, blockchain_type: str) -> Dict:
        """
        Get configuration for a specific blockchain.
        
        Args:
            blockchain_type: Type of blockchain
            
        Returns:
            Configuration dictionary for the blockchain
        """
        try:
            return self.config.get("blockchains", {}).get(blockchain_type, {})
        except Exception as e:
            logging.error(f"Error getting blockchain config for {blockchain_type}: {e}")
            return {}
    
    async def _initialize_strategies(self):
        """Initialize trading strategies based on configuration"""
        try:
            # Get enabled strategies from config
            enabled_strategies = self._get_enabled_strategies()
            
            if not enabled_strategies:
                logging.warning("No strategies enabled in configuration")
                return
            
            # Initialize each strategy
            for strategy_name in enabled_strategies:
                try:
                    strategy_config = self._get_strategy_config(strategy_name)
                    
                    # Import the strategy class dynamically
                    module_path = f"gbpbot.strategies.{strategy_name}"
                    strategy_class_name = "".join(word.capitalize() for word in strategy_name.split("_")) + "Strategy"
                    
                    try:
                        module = __import__(module_path, fromlist=[strategy_class_name])
                        strategy_class = getattr(module, strategy_class_name)
                    except (ImportError, AttributeError) as e:
                        logging.error(f"Failed to import strategy {strategy_name}: {e}")
                        continue
                    
                    # Create strategy instance
                    blockchain_type = strategy_config.get("blockchain", "avalanche")
                    if blockchain_type not in self.blockchain_clients:
                        logging.error(f"Strategy {strategy_name} requires {blockchain_type} but client is not initialized")
                        continue
                    
                    strategy = strategy_class(
                        self.blockchain_clients[blockchain_type],
                        strategy_config
                    )
                    
                    # Initialize strategy
                    await strategy.initialize()
                    self.active_strategies[strategy_name] = strategy
                    logging.info(f"Strategy {strategy_name} initialized")
                
                except Exception as e:
                    logging.exception(f"Error initializing strategy {strategy_name}: {e}")
            
            logging.info(f"Initialized {len(self.active_strategies)} strategies")
        
        except Exception as e:
            logging.exception(f"Error initializing strategies: {e}")
    
    def _get_enabled_strategies(self) -> List[str]:
        """
        Get list of enabled strategies from configuration.
        
        Returns:
            List of enabled strategy names
        """
        try:
            strategies = self.config.get("strategies", {})
            return [name for name, config in strategies.items() if config.get("enabled", False)]
        except Exception as e:
            logging.error(f"Error getting enabled strategies: {e}")
            return []
    
    def _get_strategy_config(self, strategy_name: str) -> Dict:
        """
        Get configuration for a specific strategy.
        
        Args:
            strategy_name: Name of the strategy
            
        Returns:
            Configuration dictionary for the strategy
        """
        try:
            return self.config.get("strategies", {}).get(strategy_name, {})
        except Exception as e:
            logging.error(f"Error getting strategy config for {strategy_name}: {e}")
            return {}
    
    async def run(self):
        """Run the bot and all active strategies"""
        if not self.blockchain_clients:
            logging.error("No blockchain clients initialized")
            return
        
        if not self.active_strategies:
            logging.warning("No active strategies to run")
            return
        
        try:
            self.running = True
            logging.info("Starting GBPBot...")
            
            # Start all strategies
            tasks = []
            for strategy_name, strategy in self.active_strategies.items():
                tasks.append(asyncio.create_task(strategy.run()))
            
            # Wait for all strategies to complete or for shutdown
            while self.running:
                # Check if any tasks have completed or failed
                for task in tasks:
                    if task.done():
                        if task.exception():
                            logging.error(f"Strategy {task.get_name()} failed with error: {task.exception()}")
                        else:
                            logging.info(f"Strategy {task.get_name()} completed: {task.result()}")
                
                # Sleep to avoid high CPU usage
                await asyncio.sleep(1)
        
        except asyncio.CancelledError:
            logging.info("GBPBot run cancelled")
        except Exception as e:
            logging.exception(f"Error running GBPBot: {e}")
        finally:
            self.running = False
            await self.shutdown()
    
    async def shutdown(self):
        """Shutdown the bot and clean up resources"""
        logging.info("Shutting down GBPBot...")
        
        # Stop all strategies
        for strategy_name, strategy in self.active_strategies.items():
            try:
                await strategy.stop()
                logging.info(f"Strategy {strategy_name} stopped")
            except Exception as e:
                logging.error(f"Error stopping strategy {strategy_name}: {e}")
        
        # Disconnect from blockchains
        for blockchain_type, client in self.blockchain_clients.items():
            try:
                await client.disconnect()
                logging.info(f"Disconnected from {blockchain_type}")
            except Exception as e:
                logging.error(f"Error disconnecting from {blockchain_type}: {e}")
        
        logging.info("GBPBot shutdown complete")
    
    async def start(self):
        """
        Start the bot - main entry point for running the bot.
        This method initializes the bot and runs it.
        """
        try:
            logging.info("Starting GBPBot...")
            
            # Initialize the bot
            success = await self.initialize()
            if not success:
                logging.error("Failed to initialize GBPBot")
                return
            
            # Run the bot
            await self.run()
            
        except KeyboardInterrupt:
            logging.info("GBPBot interrupted by user")
        except Exception as e:
            logging.exception(f"Error starting GBPBot: {e}")
        finally:
            # Make sure we shut down properly
            await self.shutdown()


# Configure logging (for standalone usage)
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )
    logger = logging.getLogger(__name__)


async def check_blockchain(blockchain_type: str) -> bool:
    """
    Check if a blockchain is properly configured and dependencies are installed.
    
    Args:
        blockchain_type: Type of blockchain to check
        
    Returns:
        True if the blockchain is ready to use, False otherwise
    """
    # Check if dependencies are installed
    ready, missing = check_environment_ready(blockchain_type)
    if not ready:
        logging.error(f"Missing dependencies for {blockchain_type}: {', '.join(missing)}")
        return False
    
    # Check if configuration is valid
    config = get_config()
    try:
        blockchain_config = config.get_blockchain_config(blockchain_type)
        logging.info(f"Configuration for {blockchain_type} is valid")
        return True
    except ConfigurationError as e:
        logging.error(f"Configuration error for {blockchain_type}: {e}")
        return False


async def test_connection(blockchain_type: str) -> bool:
    """
    Test connection to a blockchain.
    
    Args:
        blockchain_type: Type of blockchain to test
        
    Returns:
        True if the connection is successful, False otherwise
    """
    config = get_config()
    try:
        # Get blockchain configuration
        blockchain_config = config.get_blockchain_config(blockchain_type)
        
        # Create blockchain client
        client = BlockchainClientFactory.get_client(blockchain_type, blockchain_config)
        
        # Connect to blockchain
        logging.info(f"Connecting to {blockchain_type}...")
        connected = await client.connect()
        
        if connected:
            logging.info(f"Successfully connected to {blockchain_type}")
            
            # Get native token balance if possible
            try:
                # For Ethereum-based chains, get ETH balance
                if blockchain_type in ["ethereum", "polygon", "avalanche", "arbitrum"]:
                    balance = await client.get_balance("ETH")
                    logging.info(f"Native token balance: {balance}")
                # For Solana, get SOL balance
                elif blockchain_type == "solana":
                    balance = await client.get_balance("SOL")
                    logging.info(f"Native token balance: {balance}")
            except Exception as e:
                logging.warning(f"Could not get balance: {e}")
            
            # Disconnect
            await client.disconnect()
            return True
        else:
            logging.error(f"Failed to connect to {blockchain_type}")
            return False
    except Exception as e:
        logging.error(f"Error testing connection to {blockchain_type}: {e}")
        return False


async def run_command(args: argparse.Namespace) -> int:
    """
    Run the command specified by the command-line arguments.
    
    Args:
        args: Command-line arguments
        
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    # Check environment
    if args.check_env:
        print_environment_report()
        return 0
    
    # Test connection
    if args.test_connection:
        if args.blockchain:
            success = await test_connection(args.blockchain)
            return 0 if success else 1
        else:
            logging.error("No blockchain specified for connection test")
            return 1
    
    # Default behavior: print help
    logging.info("No command specified. Use --help to see available commands.")
    return 0


def parse_args() -> argparse.Namespace:
    """
    Parse command-line arguments.
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(
        description="GBP Bot - Blockchain Client Interface",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    
    # General options
    parser.add_argument(
        "--config", "-c",
        help="Path to configuration file",
        default=None,
    )
    parser.add_argument(
        "--debug", "-d",
        help="Enable debug logging",
        action="store_true",
    )
    
    # Commands
    parser.add_argument(
        "--check-env",
        help="Check environment and dependencies",
        action="store_true",
    )
    parser.add_argument(
        "--test-connection",
        help="Test connection to blockchain",
        action="store_true",
    )
    
    # Blockchain options
    parser.add_argument(
        "--blockchain", "-b",
        help="Blockchain to use (ethereum, solana, etc.)",
        choices=["ethereum", "solana", "polygon", "avalanche", "arbitrum"],
        default=None,
    )
    
    return parser.parse_args()


async def main_async() -> int:
    """
    Asynchronous main function.
    
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    # Parse command-line arguments
    args = parse_args()
    
    # Configure logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
        logging.debug("Debug logging enabled")
    
    # Initialize configuration
    try:
        config = get_config(args.config)
        logging.debug("Configuration loaded")
    except ConfigurationError as e:
        logging.error(f"Configuration error: {e}")
        return 1
    
    # Run the command
    try:
        return await run_command(args)
    except GBPBotError as e:
        logging.error(f"Error: {e}")
        return 1
    except Exception as e:
        logging.exception(f"Unexpected error: {e}")
        return 1


def main() -> int:
    """
    Main entry point.
    
    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        return asyncio.run(main_async())
    except KeyboardInterrupt:
        logging.info("Interrupted by user")
        return 130  # Standard exit code for SIGINT
    except Exception as e:
        logging.exception(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 