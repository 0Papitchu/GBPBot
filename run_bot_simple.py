#!/usr/bin/env python
"""
Script simple pour exécuter GBPBot avec une configuration minimale.
"""

import sys
import logging
import asyncio
import os
import yaml

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# Configuration minimale pour le bot
CONFIG = {
    "blockchains": {
        "avalanche": {
            "enabled": True,
            "rpc": {
                "providers": [
                    {
                        "url": "https://api.avax.network/ext/bc/C/rpc",
                        "weight": 1.0
                    }
                ]
            },
            "tokens": {
                "WAVAX": "0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7",
                "USDT": "0x9702230A8Ea53601f5cD2dc00fDBc13d4dF4A8c7",
                "USDC": "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E"
            }
        }
    },
    "strategies": {
        "arbitrage": {
            "enabled": True,
            "blockchain": "avalanche",
            "settings": {
                "min_profit_threshold": 0.5,
                "max_slippage": 1.0,
                "gas_boost": 1.2
            }
        }
    }
}

def create_config_file():
    """Create a minimal configuration file for testing"""
    config_dir = os.path.join(os.getcwd(), "config")
    os.makedirs(config_dir, exist_ok=True)
    
    config_path = os.path.join(config_dir, "test_config.yaml")
    with open(config_path, "w") as f:
        yaml.dump(CONFIG, f)
    
    logger.info(f"Created test configuration file at {config_path}")
    return config_path

async def main_async():
    """Run GBPBot with minimal configuration"""
    try:
        logger.info("Starting GBPBot with minimal configuration...")
        from gbpbot.main import GBPBot
        
        # Configuration de l'event loop pour Windows (résout le problème aiodns)
        if os.name == 'nt':  # Windows
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        # Create test configuration file
        config_path = create_config_file()
        
        # Create an instance with simulation mode enabled
        bot = GBPBot(
            config_path=config_path,
            debug=True,
            simulation_mode=True,
            is_testnet=True
        )
        logger.info("Successfully created GBPBot instance!")
        
        # Start the bot (will initialize and run)
        logger.info("Starting the bot...")
        await bot.start()
        
        return 0
    except ImportError as e:
        logger.error(f"Import error: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1

def main():
    """Main entry point"""
    try:
        return asyncio.run(main_async())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 130
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 