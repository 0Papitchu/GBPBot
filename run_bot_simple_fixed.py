#!/usr/bin/env python
"""
Script simple pour exécuter GBPBot avec une configuration minimale.
Version corrigée qui fournit les paires de tokens à la stratégie d'arbitrage.
"""

import sys
import logging
import asyncio
import os
import yaml
from typing import Dict, List, Any

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
            },
            "pairs": [
                ["WAVAX", "USDC"],
                ["WAVAX", "USDT"],
                ["USDC", "USDT"]
            ]
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

class GBPBotWrapper:
    """Wrapper class for GBPBot to handle token pairs for arbitrage strategy"""
    
    def __init__(self, config_path, debug=False, simulation_mode=False, is_testnet=False):
        from gbpbot.main import GBPBot
        self.bot = GBPBot(
            config_path=config_path,
            debug=debug,
            simulation_mode=simulation_mode,
            is_testnet=is_testnet
        )
        self.config = CONFIG
        
    async def initialize(self):
        """Initialize the bot"""
        await self.bot.initialize()
        
    async def run(self):
        """Run the bot with token pairs for arbitrage strategy"""
        try:
            logger.info("Starting GBPBot...")
            
            # Prepare token pairs for arbitrage strategy
            token_pairs = self._prepare_token_pairs()
            
            # Start all strategies
            tasks = []
            for strategy_name, strategy in self.bot.active_strategies.items():
                if strategy_name == "arbitrage":
                    tasks.append(asyncio.create_task(strategy.run(token_pairs)))
                else:
                    tasks.append(asyncio.create_task(strategy.run()))
            
            # Wait for all strategies to complete or for shutdown
            while self.bot.running:
                # Check if any tasks have completed or failed
                for task in tasks:
                    if task.done():
                        if task.exception():
                            logger.error(f"Strategy task failed: {task.exception()}")
                        tasks.remove(task)
                
                if not tasks:
                    logger.warning("All strategy tasks have completed or failed")
                    break
                
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"Error running GBPBot: {e}")
            import traceback
            logger.error(traceback.format_exc())
        finally:
            await self.bot.shutdown()
    
    def _prepare_token_pairs(self) -> List[Dict[str, Any]]:
        """Prepare token pairs for arbitrage strategy"""
        pairs_config = self.config["strategies"]["arbitrage"].get("pairs", [])
        token_pairs = []
        
        for pair in pairs_config:
            if len(pair) == 2:
                token_in, token_out = pair
                token_pairs.append({
                    "token_in": token_in,
                    "token_out": token_out,
                    "amount_in": 1000000,  # Default amount
                    "symbol": f"{token_in}/{token_out}"
                })
        
        logger.info(f"Prepared {len(token_pairs)} token pairs for arbitrage strategy")
        return token_pairs
    
    async def start(self):
        """Start the bot"""
        await self.initialize()
        await self.run()
        
    async def shutdown(self):
        """Shutdown the bot"""
        await self.bot.shutdown()

async def main_async():
    """Run GBPBot with minimal configuration"""
    try:
        logger.info("Starting GBPBot with minimal configuration...")
        
        # Configuration de l'event loop pour Windows (résout le problème aiodns)
        if os.name == 'nt':  # Windows
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        # Create test configuration file
        config_path = create_config_file()
        
        # Create an instance with simulation mode enabled
        bot = GBPBotWrapper(
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
        import traceback
        logger.error(traceback.format_exc())
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