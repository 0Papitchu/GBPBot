#!/usr/bin/env python
"""
Test script to verify that GBPBot can be run correctly.
"""

import sys
import logging
import asyncio
import os

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

async def main_async():
    """Test running GBPBot"""
    try:
        logger.info("Testing running of GBPBot...")
        from gbpbot.main import GBPBot
        
        # Configuration de l'event loop pour Windows (résout le problème aiodns)
        if os.name == 'nt':  # Windows
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
        # Create an instance with simulation mode enabled
        bot = GBPBot(debug=True, simulation_mode=True, is_testnet=True)
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