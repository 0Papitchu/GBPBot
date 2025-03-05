"""
DexScreener API Adapter

This module provides an adapter for the DexScreener API to fetch data
about new memecoins and their performance metrics.
"""

import asyncio
import aiohttp
import json
import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from gbpbot.utils.logger import setup_logger
from gbpbot.utils.cache_manager import CacheManager
from gbpbot.api_adapters.base_adapter import BaseAPIAdapter

class DexScreenerAdapter(BaseAPIAdapter):
    """
    Adapter for the DexScreener API to fetch memecoin data.
    DexScreener provides comprehensive data about tokens across multiple blockchains.
    """
    
    BASE_URL = "https://api.dexscreener.com/latest"
    
    def __init__(self, config: Dict):
        """
        Initialize the DexScreener API adapter
        
        Args:
            config: Configuration dictionary
        """
        super().__init__(config)
        self.config = config
        
        # Configure logger
        self.logger = setup_logger("DexScreenerAdapter", logging.INFO)
        self.logger.info("Initializing DexScreener API Adapter")
        
        # Cache for API responses
        self.cache = CacheManager(
            max_size=100,
            ttl=config.get("api_adapters", {}).get("dexscreener", {}).get("cache_ttl", 60)
        )
        
        # Configure API settings
        self.rate_limit = config.get("api_adapters", {}).get("dexscreener", {}).get("rate_limit_per_min", 30)
        self.min_liquidity = config.get("sniping", {}).get("trade_settings", {}).get("min_liquidity_usd", 50000)
        self.min_volume = config.get("sniping", {}).get("trade_settings", {}).get("min_volume_usd", 100000)
        
        # Blockchain mappings
        self.blockchain_mappings = {
            "solana": "solana",
            "avalanche": "avalanche",
            "sonic": "icplite"  # Map Sonic to ICP Lite on DexScreener
        }
        
        # Track API calls for rate limiting
        self.last_api_calls = []
        
        self.logger.info("DexScreener API Adapter initialized")
        
    async def get_new_tokens(self, lookback_hours: int = 24) -> List[Dict]:
        """
        Get list of new tokens from DexScreener
        
        Args:
            lookback_hours: How many hours to look back
            
        Returns:
            List[Dict]: List of new tokens
        """
        # Prioritize blockchains according to config
        blockchain_priority = self.config.get("detection", {}).get("blockchain_priority", ["solana", "avalanche", "sonic"])
        
        # Sort blockchains by priority and filter to those with mappings
        blockchains = [b for b in blockchain_priority if b in self.blockchain_mappings]
        
        all_tokens = []
        for blockchain in blockchains:
            try:
                # Get tokens for this blockchain
                chain_tokens = await self._get_tokens_for_blockchain(blockchain, lookback_hours)
                all_tokens.extend(chain_tokens)
                
                # Short pause between blockchain requests to avoid rate limiting
                await asyncio.sleep(0.5)
                
            except Exception as e:
                self.logger.error(f"Error fetching tokens for {blockchain}: {str(e)}")
                
        return all_tokens
        
    async def _get_tokens_for_blockchain(self, blockchain: str, lookback_hours: int) -> List[Dict]:
        """
        Get new tokens for a specific blockchain
        
        Args:
            blockchain: Blockchain name
            lookback_hours: How many hours to look back
            
        Returns:
            List[Dict]: List of new tokens
        """
        # Check cache first
        cache_key = f"dexscreener_new_tokens_{blockchain}_{lookback_hours}"
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        # Ensure rate limit compliance
        await self._enforce_rate_limit()
        
        dex_chain = self.blockchain_mappings.get(blockchain, blockchain)
        
        # Calculate the minimum timestamp for new tokens
        min_timestamp = int((datetime.now() - timedelta(hours=lookback_hours)).timestamp())
        
        try:
            # Fetch trending tokens for this blockchain
            url = f"{self.BASE_URL}/dex/trending/{dex_chain}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        self.logger.error(f"Error fetching trending tokens for {blockchain}: {response.status}")
                        return []
                        
                    data = await response.json()
                    
            self._record_api_call()
            pairs = data.get("pairs", [])
            
            # Filter and transform the pairs
            new_tokens = []
            for pair in pairs:
                # Skip if not enough liquidity or volume
                if float(pair.get("liquidity", {}).get("usd", 0)) < self.min_liquidity:
                    continue
                    
                if float(pair.get("volume", {}).get("h24", 0)) < self.min_volume:
                    continue
                    
                # Get the created timestamp
                created_timestamp = pair.get("pairCreatedAt", 0)
                if created_timestamp < min_timestamp:
                    continue
                    
                # Get token data
                token_data = {
                    "address": pair.get("baseToken", {}).get("address"),
                    "name": pair.get("baseToken", {}).get("name"),
                    "symbol": pair.get("baseToken", {}).get("symbol"),
                    "blockchain": blockchain,
                    "created_at": datetime.fromtimestamp(created_timestamp).isoformat(),
                    "price_usd": float(pair.get("priceUsd", 0)),
                    "liquidity_usd": float(pair.get("liquidity", {}).get("usd", 0)),
                    "volume_24h": float(pair.get("volume", {}).get("h24", 0)),
                    "price_change_24h": float(pair.get("priceChange", {}).get("h24", 0)),
                    "pair_address": pair.get("pairAddress"),
                    "dex": pair.get("dexId"),
                    "detection_source": "dexscreener"
                }
                
                new_tokens.append(token_data)
                
            # Fetch recent tokens for this blockchain
            url = f"{self.BASE_URL}/dex/search?chain={dex_chain}&q=created%3A{min_timestamp}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        self.logger.error(f"Error fetching recent tokens for {blockchain}: {response.status}")
                        # Still return trending tokens if we have them
                        
                        # Cache the results
                        self.cache.set(cache_key, new_tokens, ttl=300)  # 5 minute cache
                        return new_tokens
                        
                    data = await response.json()
                    
            self._record_api_call()
            recent_pairs = data.get("pairs", [])
            
            # Process recent pairs
            for pair in recent_pairs:
                # Skip if already in trending
                if any(t["pair_address"] == pair.get("pairAddress") for t in new_tokens):
                    continue
                    
                # Skip if not enough liquidity or volume
                if float(pair.get("liquidity", {}).get("usd", 0)) < self.min_liquidity:
                    continue
                    
                # Volume might be low for very new tokens, so be more lenient
                if float(pair.get("volume", {}).get("h24", 0)) < self.min_volume / 2:
                    continue
                    
                # Get token data
                token_data = {
                    "address": pair.get("baseToken", {}).get("address"),
                    "name": pair.get("baseToken", {}).get("name"),
                    "symbol": pair.get("baseToken", {}).get("symbol"),
                    "blockchain": blockchain,
                    "created_at": datetime.fromtimestamp(pair.get("pairCreatedAt", 0)).isoformat(),
                    "price_usd": float(pair.get("priceUsd", 0)),
                    "liquidity_usd": float(pair.get("liquidity", {}).get("usd", 0)),
                    "volume_24h": float(pair.get("volume", {}).get("h24", 0)),
                    "price_change_24h": float(pair.get("priceChange", {}).get("h24", 0)),
                    "pair_address": pair.get("pairAddress"),
                    "dex": pair.get("dexId"),
                    "detection_source": "dexscreener"
                }
                
                new_tokens.append(token_data)
                
            # Sort by creation time (newest first)
            new_tokens.sort(key=lambda x: x["created_at"], reverse=True)
            
            # Cache the results
            self.cache.set(cache_key, new_tokens, ttl=300)  # 5 minute cache
            
            return new_tokens
            
        except Exception as e:
            self.logger.error(f"Error in _get_tokens_for_blockchain for {blockchain}: {str(e)}")
            return []
            
    async def get_token_info(self, token_address: str, blockchain: str) -> Dict:
        """
        Get detailed information about a specific token
        
        Args:
            token_address: Token address
            blockchain: Blockchain name
            
        Returns:
            Dict: Token information
        """
        # Check cache first
        cache_key = f"dexscreener_token_info_{blockchain}_{token_address}"
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            return cached_result
            
        # Ensure rate limit compliance
        await self._enforce_rate_limit()
        
        dex_chain = self.blockchain_mappings.get(blockchain, blockchain)
        
        try:
            url = f"{self.BASE_URL}/dex/tokens/{token_address}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        self.logger.error(f"Error fetching token info for {token_address}: {response.status}")
                        return {"error": f"API error: {response.status}"}
                        
                    data = await response.json()
                    
            self._record_api_call()
            
            pairs = data.get("pairs", [])
            # Filter pairs for the specific blockchain
            pairs = [p for p in pairs if p.get("chainId") == dex_chain]
            
            if not pairs:
                return {"error": "No pairs found for this token on the specified blockchain"}
                
            # Use the pair with the highest liquidity
            pair = max(pairs, key=lambda p: float(p.get("liquidity", {}).get("usd", 0)))
            
            # Get token data
            token_info = {
                "address": token_address,
                "name": pair.get("baseToken", {}).get("name"),
                "symbol": pair.get("baseToken", {}).get("symbol"),
                "blockchain": blockchain,
                "price_usd": float(pair.get("priceUsd", 0)),
                "liquidity_usd": float(pair.get("liquidity", {}).get("usd", 0)),
                "volume_24h": float(pair.get("volume", {}).get("h24", 0)),
                "price_change_24h": float(pair.get("priceChange", {}).get("h24", 0)),
                "created_at": datetime.fromtimestamp(pair.get("pairCreatedAt", 0)).isoformat(),
                "fdv": float(pair.get("fdv", 0)),
                "market_cap": float(pair.get("marketCap", 0)),
                "pair_address": pair.get("pairAddress"),
                "dex": pair.get("dexId"),
                "txns_24h": {
                    "buys": int(pair.get("txns", {}).get("h24", {}).get("buys", 0)),
                    "sells": int(pair.get("txns", {}).get("h24", {}).get("sells", 0))
                },
                "price_chart": pair.get("url")
            }
            
            # Cache the results
            self.cache.set(cache_key, token_info, ttl=300)  # 5 minute cache
            
            return token_info
            
        except Exception as e:
            self.logger.error(f"Error in get_token_info for {token_address}: {str(e)}")
            return {"error": str(e)}
            
    async def get_top_gainers(self, blockchain: str, timeframe: str = "h24", limit: int = 20) -> List[Dict]:
        """
        Get top gainers for a specific blockchain and timeframe
        
        Args:
            blockchain: Blockchain name
            timeframe: Timeframe (h1, h6, h24, d7)
            limit: Maximum number of tokens to return
            
        Returns:
            List[Dict]: List of top gainers
        """
        # Check cache first
        cache_key = f"dexscreener_top_gainers_{blockchain}_{timeframe}_{limit}"
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            return cached_result
            
        # Ensure rate limit compliance
        await self._enforce_rate_limit()
        
        dex_chain = self.blockchain_mappings.get(blockchain, blockchain)
        valid_timeframes = ["h1", "h6", "h24", "d7"]
        
        if timeframe not in valid_timeframes:
            self.logger.error(f"Invalid timeframe: {timeframe}")
            return []
            
        try:
            url = f"{self.BASE_URL}/dex/gainers-losers/{dex_chain}/{timeframe}?gainers=1&losers=0"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        self.logger.error(f"Error fetching top gainers for {blockchain}: {response.status}")
                        return []
                        
                    data = await response.json()
                    
            self._record_api_call()
            pairs = data.get("gainers", [])
            
            # Filter and transform the pairs
            top_gainers = []
            for pair in pairs[:limit]:
                # Get token data
                token_data = {
                    "address": pair.get("baseToken", {}).get("address"),
                    "name": pair.get("baseToken", {}).get("name"),
                    "symbol": pair.get("baseToken", {}).get("symbol"),
                    "blockchain": blockchain,
                    "price_usd": float(pair.get("priceUsd", 0)),
                    "liquidity_usd": float(pair.get("liquidity", {}).get("usd", 0)),
                    "volume_24h": float(pair.get("volume", {}).get("h24", 0)),
                    "price_change": float(pair.get("priceChange", {}).get(timeframe, 0)),
                    "pair_address": pair.get("pairAddress"),
                    "dex": pair.get("dexId")
                }
                
                top_gainers.append(token_data)
                
            # Cache the results
            self.cache.set(cache_key, top_gainers, ttl=300)  # 5 minute cache
            
            return top_gainers
            
        except Exception as e:
            self.logger.error(f"Error in get_top_gainers for {blockchain}: {str(e)}")
            return []
            
    async def get_top_volume(self, blockchain: str, timeframe: str = "h24", limit: int = 20) -> List[Dict]:
        """
        Get tokens with highest volume for a specific blockchain and timeframe
        
        Args:
            blockchain: Blockchain name
            timeframe: Timeframe (h1, h6, h24, d7)
            limit: Maximum number of tokens to return
            
        Returns:
            List[Dict]: List of tokens with highest volume
        """
        # Check cache first
        cache_key = f"dexscreener_top_volume_{blockchain}_{timeframe}_{limit}"
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            return cached_result
            
        # Ensure rate limit compliance
        await self._enforce_rate_limit()
        
        dex_chain = self.blockchain_mappings.get(blockchain, blockchain)
        valid_timeframes = ["h1", "h6", "h24", "d7"]
        
        if timeframe not in valid_timeframes:
            self.logger.error(f"Invalid timeframe: {timeframe}")
            return []
            
        try:
            # For volume, we use the trending endpoint and sort by volume
            url = f"{self.BASE_URL}/dex/pairs/{dex_chain}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        self.logger.error(f"Error fetching top volume for {blockchain}: {response.status}")
                        return []
                        
                    data = await response.json()
                    
            self._record_api_call()
            pairs = data.get("pairs", [])
            
            # Sort by volume and take the top limit
            time_key = timeframe
            if timeframe not in ["h24"]:  # DexScreener only has h24 volume in the standard response
                time_key = "h24"  # Fall back to h24
                
            pairs.sort(key=lambda p: float(p.get("volume", {}).get(time_key, 0)), reverse=True)
            pairs = pairs[:limit]
            
            # Filter and transform the pairs
            top_volume = []
            for pair in pairs:
                # Get token data
                token_data = {
                    "address": pair.get("baseToken", {}).get("address"),
                    "name": pair.get("baseToken", {}).get("name"),
                    "symbol": pair.get("baseToken", {}).get("symbol"),
                    "blockchain": blockchain,
                    "price_usd": float(pair.get("priceUsd", 0)),
                    "liquidity_usd": float(pair.get("liquidity", {}).get("usd", 0)),
                    "volume_24h": float(pair.get("volume", {}).get("h24", 0)),
                    "price_change_24h": float(pair.get("priceChange", {}).get("h24", 0)),
                    "pair_address": pair.get("pairAddress"),
                    "dex": pair.get("dexId")
                }
                
                top_volume.append(token_data)
                
            # Cache the results
            self.cache.set(cache_key, top_volume, ttl=300)  # 5 minute cache
            
            return top_volume
            
        except Exception as e:
            self.logger.error(f"Error in get_top_volume for {blockchain}: {str(e)}")
            return []
            
    def _record_api_call(self):
        """Record an API call for rate limiting"""
        now = time.time()
        self.last_api_calls.append(now)
        
        # Remove old calls
        self.last_api_calls = [t for t in self.last_api_calls if now - t < 60]
        
    async def _enforce_rate_limit(self):
        """Enforce rate limiting for API calls"""
        now = time.time()
        
        # Clean up old calls
        self.last_api_calls = [t for t in self.last_api_calls if now - t < 60]
        
        # Check if we've exceeded the rate limit
        if len(self.last_api_calls) >= self.rate_limit:
            # Calculate wait time
            oldest_call = min(self.last_api_calls)
            wait_time = 60 - (now - oldest_call)
            
            if wait_time > 0:
                self.logger.warning(f"Rate limit reached, waiting {wait_time:.2f} seconds")
                await asyncio.sleep(wait_time)
                
                # After waiting, clean up again
                now = time.time()
                self.last_api_calls = [t for t in self.last_api_calls if now - t < 60] 