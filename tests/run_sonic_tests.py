#!/usr/bin/env python3
import os
import sys
import unittest
import asyncio
import logging
from pathlib import Path

# Add parent directory to path
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.append(parent_dir)

# Import the test class
from unit.test_sonic_blockchain import TestSonicBlockchainClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("sonic_tests")


def run_unit_tests():
    """Run unit tests for the SonicBlockchainClient class"""
    logger.info("=====================================================")
    logger.info("Running Unit Tests for SonicBlockchainClient")
    logger.info("=====================================================")
    
    # Create a test suite
    test_suite = unittest.TestLoader().loadTestsFromTestCase(TestSonicBlockchainClient)
    
    # Run the tests
    test_result = unittest.TextTestRunner(verbosity=2).run(test_suite)
    
    # Return True if all tests passed
    return test_result.wasSuccessful()


async def run_example_script():
    """Run the example script for manual verification"""
    logger.info("=====================================================")
    logger.info("Running Example Script for Manual Verification")
    logger.info("=====================================================")
    
    try:
        # Get example script path
        example_script = Path(parent_dir) / "examples" / "sonic_client_example.py"
        
        if not example_script.exists():
            logger.error(f"Example script not found at {example_script}")
            return False
        
        logger.info(f"To run the example script manually, execute the following command:")
        logger.info(f"python {example_script}")
        logger.info("Note: You need to set a valid private key in config/sonic_config.json or")
        logger.info("set the SONIC_PRIVATE_KEY environment variable before running the example.")
        
        return True
        
    except Exception as e:
        logger.error(f"Error preparing to run example script: {str(e)}")
        return False


def main():
    """Main entry point"""
    success = True
    
    # Run unit tests
    if not run_unit_tests():
        logger.error("Unit tests failed. Please check the logs for details.")
        success = False
    else:
        logger.info("All unit tests passed successfully!")
    
    # Run example preparation (async)
    if not asyncio.run(run_example_script()):
        logger.warning("Failed to prepare example script. Manual testing may not be possible.")
    else:
        logger.info("Example script preparation complete.")
    
    if success:
        logger.info("All tests completed successfully!")
        return 0
    else:
        logger.error("Some tests failed. Please check the logs for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 