#!/usr/bin/env python
"""
Test script to verify that GBPBot can be imported correctly.
"""

import sys
import logging

# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

def main():
    """Test importing GBPBot"""
    try:
        logger.info("Testing import of GBPBot...")
        from gbpbot.main import GBPBot
        logger.info("Successfully imported GBPBot!")
        
        # Create an instance to verify the class works
        bot = GBPBot(debug=True)
        logger.info("Successfully created GBPBot instance!")
        
        return 0
    except ImportError as e:
        logger.error(f"Import error: {e}")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 