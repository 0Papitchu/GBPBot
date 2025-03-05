#!/usr/bin/env python3
import os
import sys
import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

# Ensure the package can be imported
script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(script_dir)
sys.path.append(parent_dir)

from gbpbot.core.blockchain_factory import BlockchainFactory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"sonic_client_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)
logger = logging.getLogger("sonic_example")


async def display_account_info(client):
    """Display connected account information and balances"""
    logger.info("=========== ACCOUNT INFORMATION ===========")
    logger.info(f"Connected to Sonic network")
    logger.info(f"Wallet address: {client.wallet_address}")
    
    # Get native token balance (ICP)
    icp_balance = await client.get_token_balance(client.token_addresses.get("ICP"))
    logger.info(f"ICP Balance: {icp_balance}")
    
    # Get wrapped token balance (WICP)
    wicp_balance = await client.get_token_balance(client.token_addresses.get("WICP"))
    logger.info(f"WICP Balance: {wicp_balance}")
    
    # Get some token prices
    icp_price_usd = await client.get_token_price(client.token_addresses.get("ICP"), client.token_addresses.get("USDC"))
    logger.info(f"Current ICP price (USD): ${icp_price_usd}")
    
    return {"icp_balance": icp_balance, "wicp_balance": wicp_balance}


async def check_token_approval_example(client, token_address, amount=None):
    """Check and approve a token if needed"""
    logger.info("=========== TOKEN APPROVAL EXAMPLE ===========")
    
    # Check if the token is already approved
    is_approved = await client.check_token_approval(
        token_address, 
        client.dex_router_address, 
        amount
    )
    
    if is_approved:
        logger.info(f"Token {token_address} is already approved for {'unlimited' if amount is None else amount} tokens")
        return True
    
    logger.info(f"Token needs approval. Approving now...")
    approval_result = await client.approve_token(
        token_address,
        client.dex_router_address,
        amount
    )
    
    if approval_result["success"]:
        logger.info(f"Successfully approved {approval_result['amount']} tokens")
        logger.info(f"Transaction hash: {approval_result['tx_hash']}")
        return True
    else:
        logger.error(f"Failed to approve token: {approval_result['error']}")
        return False


async def token_swap_example(client, token_in, token_out, amount, slippage=0.5):
    """Execute a token swap example"""
    logger.info("=========== TOKEN SWAP EXAMPLE ===========")
    
    # First check and approve if needed
    token_in_address = client.token_addresses.get(token_in, token_in)
    token_out_address = client.token_addresses.get(token_out, token_out)
    
    # Get current price and balance before swap
    price_before = await client.get_token_price(token_in_address, token_out_address)
    balance_before = await client.get_token_balance(token_in_address)
    
    logger.info(f"Current price of {token_in} in {token_out}: {price_before}")
    logger.info(f"Current {token_in} balance: {balance_before}")
    logger.info(f"Attempting to swap {amount} {token_in} for {token_out}")
    
    # Check approval first
    approved = await check_token_approval_example(client, token_in_address, amount)
    if not approved:
        logger.error("Cannot execute swap without approval")
        return
    
    # Execute the swap
    swap_result = await client.execute_swap(
        token_in_address,
        token_out_address,
        amount,
        slippage=slippage
    )
    
    if swap_result["success"]:
        logger.info(f"Swap executed successfully")
        logger.info(f"Transaction hash: {swap_result['tx_hash']}")
        logger.info(f"Amount in: {swap_result['amount_in']} {token_in}")
        logger.info(f"Amount out: {swap_result['amount_out']} {token_out}")
        
        # Check new balances
        balance_after = await client.get_token_balance(token_out_address)
        logger.info(f"New {token_out} balance: {balance_after}")
    else:
        logger.error(f"Swap failed: {swap_result.get('error', 'Unknown error')}")


async def monitor_new_tokens(client, duration_seconds=60):
    """Monitor for new tokens for a specified duration"""
    logger.info("=========== NEW TOKEN MONITORING ===========")
    logger.info(f"Monitoring for new tokens for {duration_seconds} seconds...")
    
    end_time = datetime.now().timestamp() + duration_seconds
    new_tokens_found = []
    
    while datetime.now().timestamp() < end_time:
        try:
            # Get new tokens added recently
            new_tokens = await client.get_new_tokens()
            
            # Process each new token
            for token in new_tokens:
                if token["address"] not in [t["address"] for t in new_tokens_found]:
                    new_tokens_found.append(token)
                    
                    logger.info(f"New token detected: {token['name']} ({token['symbol']})")
                    logger.info(f"Address: {token['address']}")
                    logger.info(f"Created at block: {token['block_number']}")
                    logger.info(f"Timestamp: {token['timestamp']}")
                    
                    # Analyze the contract
                    analysis = await client.analyze_contract(token["address"])
                    logger.info(f"Contract analysis:")
                    logger.info(f"  Safe: {analysis['is_safe']}")
                    if len(analysis["risks"]) > 0:
                        logger.info(f"  Risks detected: {', '.join(analysis['risks'])}")
                    else:
                        logger.info(f"  No risks detected")
                    
                    # Get pricing information if possible
                    try:
                        price = await client.get_token_price(
                            token["address"],
                            client.token_addresses.get("WICP")
                        )
                        logger.info(f"  Initial price (in WICP): {price}")
                    except Exception as e:
                        logger.warning(f"  Could not get price: {str(e)}")
                    
                    logger.info("------------------------------------")
            
            # Wait a bit before the next check
            await asyncio.sleep(5)
            
        except Exception as e:
            logger.error(f"Error during monitoring: {str(e)}")
            await asyncio.sleep(5)
    
    logger.info(f"Monitoring complete. Found {len(new_tokens_found)} new tokens.")
    return new_tokens_found


async def main():
    """Main execution function"""
    logger.info("Starting Sonic blockchain client example")
    
    # Load configuration (or use hardcoded for example)
    config_path = Path(parent_dir) / "config" / "sonic_config.json"
    
    if config_path.exists():
        with open(config_path, "r") as f:
            config = json.load(f)
    else:
        logger.warning(f"Config file {config_path} not found, using default configuration")
        # Default example configuration - REPLACE WITH REAL VALUES FOR ACTUAL USE
        config = {
            "rpc": {
                "providers": {
                    "sonic": {
                        "mainnet": [
                            {"name": "Sonic RPC", "url": "YOUR_SONIC_RPC_URL", "weight": 1}
                        ]
                    }
                },
                "timeout": 30
            },
            "tokens": {
                "icp": "0x4943502D6C6567650000000000000000",  # Example ICP address (replace with real one)
                "wicp": "0x5749435000000000000000000000000000",  # Example WICP address (replace with real one)
                "usdc": "0x5553444300000000000000000000000000",  # Example USDC address (replace with real one)
                "whitelist": []
            },
            "dex": {
                "sonic": {
                    "router_address": "0x536F6E69635F526F75746572000000000000000000",  # Example Sonic Router
                    "factory_address": "0x536F6E69635F466163746F727900000000000000"  # Example Sonic Factory
                }
            },
            "wallet": {
                "private_key": "YOUR_PRIVATE_KEY"  # NEVER HARDCODE IN PRODUCTION
            },
            "notifications": {
                "enabled": False
            }
        }
    
    # Check for private key in environment if not in config
    if config["wallet"]["private_key"] == "YOUR_PRIVATE_KEY":
        config["wallet"]["private_key"] = os.environ.get("SONIC_PRIVATE_KEY", "")
        if not config["wallet"]["private_key"]:
            logger.error("Private key not found in config or environment. Please set SONIC_PRIVATE_KEY.")
            return
    
    try:
        # Get the Sonic blockchain client instance
        client = BlockchainFactory.get_blockchain_client("sonic", config)
        
        # Connect to the network
        connected = await client.connect()
        if not connected:
            logger.error("Failed to connect to Sonic network")
            return
        
        logger.info("Successfully connected to Sonic network")
        
        # Example 1: Display Account Information
        account_info = await display_account_info(client)
        
        # Example 2: Check and approve a token (using WICP as example)
        wicp_address = client.token_addresses.get("WICP")
        if wicp_address:
            await check_token_approval_example(client, wicp_address, 10.0)  # Approve 10 WICP
        
        # Example 3: Execute a token swap (small amount to test)
        # Only execute if we have enough balance
        if account_info["wicp_balance"] > 0.01:
            await token_swap_example(
                client,
                "WICP",  # From WICP
                "USDC",  # To USDC
                0.01,    # Small amount for testing
                slippage=1.0  # 1% slippage
            )
        
        # Example 4: Monitor for new tokens (short duration for demo)
        await monitor_new_tokens(client, 30)  # Monitor for 30 seconds
        
        logger.info("Sonic blockchain client example completed successfully")
        
    except Exception as e:
        logger.error(f"Error in main execution: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    asyncio.run(main()) 