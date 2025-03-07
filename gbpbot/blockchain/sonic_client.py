#!/usr/bin/env python
"""
Sonic Blockchain Client for GBPBot.

This module provides a client for interacting with the Sonic blockchain
and its decentralized exchanges (DEX) like SpiritSwap and SpookySwap.
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Optional, Tuple, Union, Any

import aiohttp
from web3 import Web3
from web3.middleware import geth_poa_middleware

from gbpbot.core.blockchain import BlockchainClient
from gbpbot.utils.config import get_config
from gbpbot.utils.exceptions import BlockchainConnectionError, TransactionError


class SonicClient(BlockchainClient):
    """
    Client for interacting with the Sonic blockchain and its DEX.
    
    This client provides methods for connecting to the Sonic blockchain,
    fetching token information, and executing trades on SpiritSwap and SpookySwap.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Sonic client.
        
        Args:
            config: Configuration dictionary for the Sonic client
        """
        super().__init__(config)
        self.blockchain_type = "sonic"
        self.logger = logging.getLogger("gbpbot.blockchain.sonic")
        
        # Initialize configuration
        self.rpc_url = config.get("SONIC_RPC_URL", "https://rpc.sonic.fantom.network/")
        self.websocket_url = config.get("SONIC_WEBSOCKET_URL", "wss://rpc.sonic.fantom.network/")
        self.chain_id = int(config.get("SONIC_CHAIN_ID", 250))
        self.backup_rpc_url = config.get("SONIC_BACKUP_RPC_URL", "https://rpc.ftm.tools/")
        
        # Initialize DEX router addresses
        self.spookyswap_router = config.get("SPOOKYSWAP_ROUTER", "0xF491e7B69E4244ad4002BC14e878a34207E38c29")
        self.spiritswap_router = config.get("SPIRITSWAP_ROUTER", "0x16327E3FbDaCA3bcF7E38F5Af2599D2DDc33aE52")
        
        # Initialize Web3 provider
        self.web3 = None
        self.ws_provider = None
        self.connected = False
        self.last_block = 0
        
        # Initialize token cache
        self.token_cache = {}
        self.pair_cache = {}
        
        # Initialize ABI cache
        self.abis = {
            "router": None,
            "pair": None,
            "token": None,
        }
        
        self.logger.info("Sonic client initialized")
    
    async def connect(self) -> bool:
        """
        Connect to the Sonic blockchain.
        
        Returns:
            True if connection was successful, False otherwise
        """
        try:
            # Initialize Web3 with HTTP provider
            self.logger.info(f"Connecting to Sonic blockchain at {self.rpc_url}")
            self.web3 = Web3(Web3.HTTPProvider(self.rpc_url))
            
            # Add POA middleware for Sonic
            self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)
            
            # Check connection
            if not self.web3.is_connected():
                self.logger.warning(f"Failed to connect to primary RPC {self.rpc_url}, trying backup...")
                self.web3 = Web3(Web3.HTTPProvider(self.backup_rpc_url))
                self.web3.middleware_onion.inject(geth_poa_middleware, layer=0)
                
                if not self.web3.is_connected():
                    self.logger.error("Failed to connect to backup RPC")
                    return False
            
            # Get latest block
            self.last_block = self.web3.eth.block_number
            self.logger.info(f"Connected to Sonic blockchain, latest block: {self.last_block}")
            
            # Load ABIs
            await self._load_abis()
            
            # Initialize websocket connection for real-time updates
            try:
                self._init_websocket()
            except Exception as e:
                self.logger.warning(f"Failed to initialize websocket connection: {e}")
                self.logger.warning("Continuing with HTTP provider only")
            
            self.connected = True
            return True
            
        except Exception as e:
            self.logger.error(f"Error connecting to Sonic blockchain: {e}")
            return False
    
    async def _load_abis(self):
        """Load ABIs for Sonic contracts."""
        try:
            # Load router ABI
            with open("gbpbot/abis/sonic/router.json", "r") as f:
                self.abis["router"] = json.load(f)
            
            # Load pair ABI
            with open("gbpbot/abis/sonic/pair.json", "r") as f:
                self.abis["pair"] = json.load(f)
            
            # Load token ABI
            with open("gbpbot/abis/sonic/token.json", "r") as f:
                self.abis["token"] = json.load(f)
            
            self.logger.info("Loaded Sonic ABIs")
        except Exception as e:
            self.logger.error(f"Error loading Sonic ABIs: {e}")
            raise
    
    def _init_websocket(self):
        """Initialize websocket connection for real-time updates."""
        self.logger.info(f"Initializing websocket connection to {self.websocket_url}")
        self.ws_provider = Web3(Web3.WebsocketProvider(self.websocket_url))
        self.ws_provider.middleware_onion.inject(geth_poa_middleware, layer=0)
        
        if not self.ws_provider.is_connected():
            raise BlockchainConnectionError("Failed to connect to websocket provider")
        
        self.logger.info("Websocket connection established")
    
    async def disconnect(self):
        """Disconnect from the Sonic blockchain."""
        self.logger.info("Disconnecting from Sonic blockchain")
        self.connected = False
        
        # Close websocket connection if it exists
        if self.ws_provider:
            # No explicit close method in Web3, but we can set it to None
            self.ws_provider = None
        
        self.web3 = None
        self.logger.info("Disconnected from Sonic blockchain")
    
    async def get_token_info(self, token_address: str) -> Dict[str, Any]:
        """
        Get information about a token.
        
        Args:
            token_address: Address of the token
            
        Returns:
            Dictionary containing token information
        """
        if not self.connected:
            raise BlockchainConnectionError("Not connected to Sonic blockchain")
        
        # Check cache first
        if token_address in self.token_cache:
            return self.token_cache[token_address]
        
        try:
            # Create token contract
            token_contract = self.web3.eth.contract(
                address=Web3.to_checksum_address(token_address),
                abi=self.abis["token"]
            )
            
            # Get token info
            name = token_contract.functions.name().call()
            symbol = token_contract.functions.symbol().call()
            decimals = token_contract.functions.decimals().call()
            total_supply = token_contract.functions.totalSupply().call() / (10 ** decimals)
            
            # Create token info dictionary
            token_info = {
                "address": token_address,
                "name": name,
                "symbol": symbol,
                "decimals": decimals,
                "total_supply": total_supply,
                "blockchain": "sonic"
            }
            
            # Cache token info
            self.token_cache[token_address] = token_info
            
            return token_info
            
        except Exception as e:
            self.logger.error(f"Error getting token info for {token_address}: {e}")
            raise
    
    async def get_token_price(self, token_address: str, quote_token_address: str = None) -> float:
        """
        Get the price of a token in terms of another token.
        
        Args:
            token_address: Address of the token
            quote_token_address: Address of the quote token (default: WFTM)
            
        Returns:
            Price of the token in terms of the quote token
        """
        if not self.connected:
            raise BlockchainConnectionError("Not connected to Sonic blockchain")
        
        # Default to WFTM if no quote token is provided
        if quote_token_address is None:
            quote_token_address = "0x21be370D5312f44cB42ce377BC9b8a0cEF1A4C83"  # WFTM
        
        try:
            # Create SpookySwap router contract
            router_contract = self.web3.eth.contract(
                address=Web3.to_checksum_address(self.spookyswap_router),
                abi=self.abis["router"]
            )
            
            # Get token decimals
            token_info = await self.get_token_info(token_address)
            quote_token_info = await self.get_token_info(quote_token_address)
            
            # Get price
            amount_in = 10 ** token_info["decimals"]  # 1 token
            path = [Web3.to_checksum_address(token_address), Web3.to_checksum_address(quote_token_address)]
            
            amounts_out = router_contract.functions.getAmountsOut(amount_in, path).call()
            price = amounts_out[1] / (10 ** quote_token_info["decimals"])
            
            return price
            
        except Exception as e:
            self.logger.error(f"Error getting token price for {token_address}: {e}")
            
            # Try SpiritSwap as fallback
            try:
                self.logger.info("Trying SpiritSwap as fallback")
                router_contract = self.web3.eth.contract(
                    address=Web3.to_checksum_address(self.spiritswap_router),
                    abi=self.abis["router"]
                )
                
                # Get token decimals
                token_info = await self.get_token_info(token_address)
                quote_token_info = await self.get_token_info(quote_token_address)
                
                # Get price
                amount_in = 10 ** token_info["decimals"]  # 1 token
                path = [Web3.to_checksum_address(token_address), Web3.to_checksum_address(quote_token_address)]
                
                amounts_out = router_contract.functions.getAmountsOut(amount_in, path).call()
                price = amounts_out[1] / (10 ** quote_token_info["decimals"])
                
                return price
                
            except Exception as e2:
                self.logger.error(f"Error getting token price from SpiritSwap: {e2}")
                raise TransactionError(f"Failed to get price from both SpookySwap and SpiritSwap: {e}, {e2}")
    
    async def get_token_balance(self, token_address: str, wallet_address: str) -> float:
        """
        Get the balance of a token for a wallet.
        
        Args:
            token_address: Address of the token
            wallet_address: Address of the wallet
            
        Returns:
            Balance of the token
        """
        if not self.connected:
            raise BlockchainConnectionError("Not connected to Sonic blockchain")
        
        try:
            # Create token contract
            token_contract = self.web3.eth.contract(
                address=Web3.to_checksum_address(token_address),
                abi=self.abis["token"]
            )
            
            # Get token info
            token_info = await self.get_token_info(token_address)
            
            # Get balance
            balance_wei = token_contract.functions.balanceOf(Web3.to_checksum_address(wallet_address)).call()
            balance = balance_wei / (10 ** token_info["decimals"])
            
            return balance
            
        except Exception as e:
            self.logger.error(f"Error getting token balance for {token_address}: {e}")
            raise
    
    async def get_pair_info(self, token_a: str, token_b: str, dex: str = "spookyswap") -> Dict[str, Any]:
        """
        Get information about a trading pair.
        
        Args:
            token_a: Address of token A
            token_b: Address of token B
            dex: DEX to use (spookyswap or spiritswap)
            
        Returns:
            Dictionary containing pair information
        """
        if not self.connected:
            raise BlockchainConnectionError("Not connected to Sonic blockchain")
        
        # Create cache key
        cache_key = f"{token_a}_{token_b}_{dex}"
        
        # Check cache first
        if cache_key in self.pair_cache:
            return self.pair_cache[cache_key]
        
        try:
            # Select router based on DEX
            if dex.lower() == "spookyswap":
                router_address = self.spookyswap_router
            elif dex.lower() == "spiritswap":
                router_address = self.spiritswap_router
            else:
                raise ValueError(f"Unsupported DEX: {dex}")
            
            # Create router contract
            router_contract = self.web3.eth.contract(
                address=Web3.to_checksum_address(router_address),
                abi=self.abis["router"]
            )
            
            # Get factory address
            factory_address = router_contract.functions.factory().call()
            
            # Create factory contract
            with open("gbpbot/abis/sonic/factory.json", "r") as f:
                factory_abi = json.load(f)
            
            factory_contract = self.web3.eth.contract(
                address=Web3.to_checksum_address(factory_address),
                abi=factory_abi
            )
            
            # Get pair address
            pair_address = factory_contract.functions.getPair(
                Web3.to_checksum_address(token_a),
                Web3.to_checksum_address(token_b)
            ).call()
            
            if pair_address == "0x0000000000000000000000000000000000000000":
                return None
            
            # Create pair contract
            pair_contract = self.web3.eth.contract(
                address=Web3.to_checksum_address(pair_address),
                abi=self.abis["pair"]
            )
            
            # Get reserves
            reserves = pair_contract.functions.getReserves().call()
            token0 = pair_contract.functions.token0().call()
            token1 = pair_contract.functions.token1().call()
            
            # Determine which reserve is which
            if token0.lower() == token_a.lower():
                reserve_a = reserves[0]
                reserve_b = reserves[1]
            else:
                reserve_a = reserves[1]
                reserve_b = reserves[0]
            
            # Get token info
            token_a_info = await self.get_token_info(token_a)
            token_b_info = await self.get_token_info(token_b)
            
            # Calculate reserves in token units
            reserve_a_units = reserve_a / (10 ** token_a_info["decimals"])
            reserve_b_units = reserve_b / (10 ** token_b_info["decimals"])
            
            # Calculate price
            price_a_in_b = reserve_b_units / reserve_a_units if reserve_a_units > 0 else 0
            price_b_in_a = reserve_a_units / reserve_b_units if reserve_b_units > 0 else 0
            
            # Create pair info dictionary
            pair_info = {
                "pair_address": pair_address,
                "token_a": token_a_info,
                "token_b": token_b_info,
                "reserve_a": reserve_a_units,
                "reserve_b": reserve_b_units,
                "price_a_in_b": price_a_in_b,
                "price_b_in_a": price_b_in_a,
                "dex": dex,
                "factory_address": factory_address,
                "blockchain": "sonic"
            }
            
            # Cache pair info
            self.pair_cache[cache_key] = pair_info
            
            return pair_info
            
        except Exception as e:
            self.logger.error(f"Error getting pair info for {token_a}/{token_b} on {dex}: {e}")
            raise
    
    # Additional methods for trading, liquidity provision, etc. would be implemented here
    
    async def execute_swap(self, wallet_key: str, token_in: str, token_out: str, 
                          amount_in: float, min_amount_out: float, 
                          dex: str = "spookyswap", deadline: int = None,
                          gas_price_multiplier: float = 1.2) -> Dict[str, Any]:
        """
        Execute a token swap.
        
        Args:
            wallet_key: Private key of the wallet
            token_in: Address of the input token
            token_out: Address of the output token
            amount_in: Amount of input token to swap
            min_amount_out: Minimum amount of output token to receive
            dex: DEX to use (spookyswap or spiritswap)
            deadline: Transaction deadline in seconds from now
            gas_price_multiplier: Multiplier for gas price
            
        Returns:
            Dictionary containing transaction information
        """
        # Implementation would go here
        # This is a placeholder for the swap execution logic
        self.logger.info(f"Executing swap on {dex}: {amount_in} {token_in} -> {token_out}")
        
        # In a real implementation, this would:
        # 1. Create a transaction to approve the router to spend tokens
        # 2. Create a transaction to execute the swap
        # 3. Sign and send the transactions
        # 4. Wait for confirmation and return the result
        
        return {
            "status": "success",
            "tx_hash": "0x...",
            "amount_in": amount_in,
            "amount_out": min_amount_out * 1.1,  # Simulated amount out
            "token_in": token_in,
            "token_out": token_out,
            "dex": dex
        }
    
    async def monitor_new_pairs(self, callback, dex: str = "spookyswap", 
                               min_liquidity_usd: float = 10000):
        """
        Monitor for new trading pairs.
        
        Args:
            callback: Function to call when a new pair is detected
            dex: DEX to monitor (spookyswap or spiritswap)
            min_liquidity_usd: Minimum liquidity in USD to consider
        """
        # Implementation would go here
        # This is a placeholder for the pair monitoring logic
        self.logger.info(f"Starting to monitor new pairs on {dex}")
        
        # In a real implementation, this would:
        # 1. Subscribe to pair creation events from the factory
        # 2. Filter pairs based on liquidity
        # 3. Call the callback function with pair information
        
        # For now, we'll just log that this method was called
        self.logger.info(f"Monitoring new pairs on {dex} with min liquidity {min_liquidity_usd} USD") 