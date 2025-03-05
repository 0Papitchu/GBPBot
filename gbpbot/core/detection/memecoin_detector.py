"""
Advanced Memecoin Detection Module for High-Performance Sniping

This module specializes in detecting new memecoin tokens across multiple blockchains,
with primary focus on Solana due to its higher volume and frequency of new token launches.
The detector implements multiple data sources and advanced filtering techniques to
identify promising opportunities while filtering out potential scams.
"""

import asyncio
import time
import json
import re
from typing import Dict, List, Set, Optional, Union, Any
from datetime import datetime, timedelta
import logging
from loguru import logger
import aiohttp
from collections import deque, defaultdict

from gbpbot.core.blockchain_factory import BlockchainFactory
from gbpbot.api_adapters.dexscreener_adapter import DexScreenerAdapter
from gbpbot.api_adapters.raydium_adapter import RaydiumAdapter
from gbpbot.api_adapters.pump_fun_adapter import PumpFunAdapter
from gbpbot.api_adapters.jupiter_adapter import JupiterAdapter
from gbpbot.core.token_analyzer import TokenAnalyzer
from gbpbot.utils.events import EventEmitter
from gbpbot.utils.cache_manager import CacheManager
from gbpbot.utils.config_loader import ConfigLoader
from gbpbot.database.wallet_tracker import WalletTracker
from gbpbot.utils.logger import setup_logger

class MemecoinDetector:
    """
    Advanced detection system for new memecoins across multiple blockchains,
    with emphasis on Solana. Implements real-time detection, filtering, and
    analysis of potential targets for high-speed sniping.
    """
    
    def __init__(self, config: Dict):
        """
        Initialize the memecoin detector with configuration
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.detection_config = config.get("detection", {})
        self.blockchain_priority = ["solana", "avalanche", "sonic"] 
        
        # Configure logger
        self.logger = setup_logger("MemecoinDetector", logging.INFO)
        self.logger.info("Initializing Memecoin Detector")
        
        # Initialize blockchain clients
        self._initialize_blockchain_clients()
        
        # Initialize API adapters for token detection
        self._initialize_api_adapters()
        
        # Initialize token analyzer
        self.token_analyzer = TokenAnalyzer(config)
        
        # Initialize wallet tracker for identifying smart money
        self.wallet_tracker = WalletTracker(config)
        
        # Event emitter for notification system
        self.event_emitter = EventEmitter()
        
        # Token storage
        self.detected_tokens = deque(maxlen=1000)
        self.processed_tokens = set()
        self.blacklisted_tokens = set()
        
        # Load blacklisted tokens from config
        self._load_blacklisted_tokens()
        
        # Performance tracking
        self.detection_stats = {
            "total_tokens_detected": 0,
            "tokens_passed_filters": 0,
            "tokens_analyzed": 0,
            "potential_opportunities": 0,
            "detection_latency_ms": 0,
            "detection_count": 0
        }
        
        # Initialize caching system
        self.cache = CacheManager(
            max_size=1000,
            ttl=config.get("cache", {}).get("detection_cache_ttl", 300)
        )
        
        # Configuration for filtering
        self.min_liquidity = config.get("sniping", {}).get("trade_settings", {}).get("min_liquidity_usd", 50000)
        self.min_volume = config.get("sniping", {}).get("trade_settings", {}).get("min_volume_usd", 100000)
        self.max_holder_concentration = config.get("sniping", {}).get("trade_settings", {}).get("max_concentration_percent", 30)
        
        # Scan settings
        self.scan_interval = config.get("sniping", {}).get("detection", {}).get("scan_interval_ms", 500) / 1000
        self.is_running = False
        self.detection_tasks = {}
        
        # Register event handlers
        self._register_event_handlers()
        
        self.logger.info("Memecoin Detector initialized")
        
    def _initialize_blockchain_clients(self):
        """Initialize blockchain clients with focus on Solana"""
        self.blockchain_clients = {}
        
        try:
            # Prioritize Solana
            self.blockchain_clients["solana"] = BlockchainFactory.get_blockchain_client("solana", self.config)
            self.logger.info("Initialized Solana blockchain client")
            
            # Add other blockchains if configured
            if "avalanche" in self.config:
                self.blockchain_clients["avalanche"] = BlockchainFactory.get_blockchain_client("avalanche", self.config)
                self.logger.info("Initialized Avalanche blockchain client")
                
            if "sonic" in self.config:
                self.blockchain_clients["sonic"] = BlockchainFactory.get_blockchain_client("sonic", self.config)
                self.logger.info("Initialized Sonic blockchain client")
                
        except Exception as e:
            self.logger.error(f"Error initializing blockchain clients: {str(e)}")
            raise
            
    def _initialize_api_adapters(self):
        """Initialize API adapters for token detection from various sources"""
        self.api_adapters = {}
        
        # Initialize DexScreener adapter for all chains
        self.api_adapters["dexscreener"] = DexScreenerAdapter(self.config)
        
        # Solana-specific adapters
        if "solana" in self.blockchain_clients:
            if self.config.get("sniping", {}).get("detection", {}).get("sources", {}).get("raydium", True):
                self.api_adapters["raydium"] = RaydiumAdapter(self.config)
                
            if self.config.get("sniping", {}).get("detection", {}).get("sources", {}).get("pump_fun", True):
                self.api_adapters["pump_fun"] = PumpFunAdapter(self.config)
                
            if self.config.get("sniping", {}).get("detection", {}).get("sources", {}).get("jupiter", True):
                self.api_adapters["jupiter"] = JupiterAdapter(self.config)
                
        self.logger.info(f"Initialized {len(self.api_adapters)} API adapters for token detection")
        
    def _load_blacklisted_tokens(self):
        """Load blacklisted token addresses from config"""
        blacklist = self.config.get("security", {}).get("blacklisted_tokens", [])
        self.blacklisted_tokens = set(blacklist)
        self.logger.info(f"Loaded {len(self.blacklisted_tokens)} blacklisted token addresses")
        
    def _register_event_handlers(self):
        """Register event handlers for token detection and analysis"""
        self.event_emitter.on("new_token_detected", self._handle_new_token)
        self.event_emitter.on("token_analysis_complete", self._handle_token_analysis)
        self.event_emitter.on("potential_opportunity", self._handle_potential_opportunity)
        self.event_emitter.on("rug_pull_detected", self._handle_rug_pull)
        
    async def start(self):
        """Start the memecoin detection process"""
        if self.is_running:
            self.logger.warning("Memecoin Detector is already running")
            return
            
        self.is_running = True
        self.logger.info("Starting Memecoin Detector")
        
        # Connect blockchain clients
        for chain, client in self.blockchain_clients.items():
            connected = await client.connect()
            if not connected:
                self.logger.error(f"Failed to connect {chain} blockchain client")
            else:
                self.logger.info(f"Connected to {chain} blockchain client")
                
        # Start detection tasks for each blockchain in order of priority
        for chain in self.blockchain_priority:
            if chain in self.blockchain_clients:
                task = asyncio.create_task(self._run_detection_loop(chain))
                self.detection_tasks[chain] = task
                self.logger.info(f"Started detection task for {chain}")
                
        # Start API polling tasks
        for adapter_name, adapter in self.api_adapters.items():
            task = asyncio.create_task(self._run_api_polling(adapter_name, adapter))
            self.detection_tasks[f"api_{adapter_name}"] = task
            self.logger.info(f"Started API polling task for {adapter_name}")
            
    async def stop(self):
        """Stop the memecoin detection process"""
        if not self.is_running:
            return
            
        self.is_running = False
        self.logger.info("Stopping Memecoin Detector")
        
        # Cancel all detection tasks
        for task_name, task in self.detection_tasks.items():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
                
        self.detection_tasks = {}
        self.logger.info("Memecoin Detector stopped")
        
    async def _run_detection_loop(self, blockchain: str):
        """
        Run the detection loop for a specific blockchain
        
        Args:
            blockchain: Blockchain name
        """
        client = self.blockchain_clients[blockchain]
        lookback_blocks = self.config.get("sniping", {}).get("detection", {}).get("lookback_blocks", 1000)
        
        self.logger.info(f"Starting detection loop for {blockchain} with {lookback_blocks} block lookback")
        
        while self.is_running:
            try:
                start_time = time.time()
                
                # Get new tokens from blockchain
                new_tokens = await client.get_new_tokens(lookback_blocks)
                
                # Filter and process tokens
                for token in new_tokens:
                    if token["address"] not in self.processed_tokens and token["address"] not in self.blacklisted_tokens:
                        self.processed_tokens.add(token["address"])
                        token["blockchain"] = blockchain
                        token["detection_source"] = "blockchain"
                        token["detection_time"] = datetime.now().isoformat()
                        
                        # Add metadata about prioritization
                        token["priority_score"] = self._calculate_priority_score(token)
                        
                        # Emit new token event
                        self.event_emitter.emit("new_token_detected", token)
                        
                        # Update statistics
                        self.detection_stats["total_tokens_detected"] += 1
                
                # Calculate and update detection latency
                detection_time = (time.time() - start_time) * 1000
                self.detection_stats["detection_latency_ms"] = (
                    (self.detection_stats["detection_latency_ms"] * self.detection_stats["detection_count"] + detection_time) / 
                    (self.detection_stats["detection_count"] + 1)
                )
                self.detection_stats["detection_count"] += 1
                
                # Sleep before next detection cycle
                await asyncio.sleep(self.scan_interval)
                
            except Exception as e:
                self.logger.error(f"Error in {blockchain} detection loop: {str(e)}")
                await asyncio.sleep(self.scan_interval * 2)  # Sleep longer on error
                
    async def _run_api_polling(self, adapter_name: str, adapter):
        """
        Run API polling for new token detection
        
        Args:
            adapter_name: Name of the adapter
            adapter: API adapter instance
        """
        poll_interval = self.config.get("sniping", {}).get("detection", {}).get(f"{adapter_name}_poll_interval_ms", 1000) / 1000
        
        self.logger.info(f"Starting API polling for {adapter_name} with {poll_interval}s interval")
        
        while self.is_running:
            try:
                start_time = time.time()
                
                # Get new tokens from API
                new_tokens = await adapter.get_new_tokens()
                
                # Process new tokens
                for token in new_tokens:
                    if token["address"] not in self.processed_tokens and token["address"] not in self.blacklisted_tokens:
                        self.processed_tokens.add(token["address"])
                        
                        # Add metadata
                        token["detection_source"] = adapter_name
                        token["detection_time"] = datetime.now().isoformat()
                        token["priority_score"] = self._calculate_priority_score(token)
                        
                        # Emit new token event
                        self.event_emitter.emit("new_token_detected", token)
                        
                        # Update statistics
                        self.detection_stats["total_tokens_detected"] += 1
                
                # Calculate processing time
                processing_time = time.time() - start_time
                
                # Sleep for remaining interval time
                sleep_time = max(0.1, poll_interval - processing_time)
                await asyncio.sleep(sleep_time)
                
            except Exception as e:
                self.logger.error(f"Error in {adapter_name} API polling: {str(e)}")
                await asyncio.sleep(poll_interval * 2)  # Sleep longer on error
                
    async def _handle_new_token(self, token: Dict):
        """
        Handle a newly detected token
        
        Args:
            token: Token data dictionary
        """
        try:
            # Apply basic filtering
            if not await self._apply_basic_filters(token):
                return
                
            # Update statistics
            self.detection_stats["tokens_passed_filters"] += 1
            
            # Queue token for detailed analysis
            await self._analyze_token(token)
            
        except Exception as e:
            self.logger.error(f"Error handling new token {token.get('address')}: {str(e)}")
            
    async def _apply_basic_filters(self, token: Dict) -> bool:
        """
        Apply basic filters to token
        
        Args:
            token: Token data
            
        Returns:
            bool: True if token passes filters, False otherwise
        """
        # Skip if token is in blacklist
        if token["address"] in self.blacklisted_tokens:
            return False
            
        # Check if token name/symbol matches suspicious patterns
        suspicious_patterns = self.config.get("security", {}).get("suspicious_patterns", [])
        token_name = token.get("name", "").lower()
        token_symbol = token.get("symbol", "").lower()
        
        for pattern in suspicious_patterns:
            if pattern.lower() in token_name or pattern.lower() in token_symbol:
                self.logger.info(f"Skipping token {token['address']} due to suspicious name/symbol: {token_name}/{token_symbol}")
                
                # Add to blacklist if auto-blacklisting is enabled
                if self.config.get("security", {}).get("auto_blacklist", True):
                    self.blacklisted_tokens.add(token["address"])
                    
                return False
                
        # Apply blockchain-specific minimum age filter if available
        if "created_at" in token:
            min_age_sec = self.config.get("sniping", {}).get("detection", {}).get("minimum_token_age_sec", 0)
            max_age_sec = self.config.get("sniping", {}).get("detection", {}).get("maximum_token_age_sec", 3600)
            
            token_created_at = datetime.fromisoformat(token["created_at"])
            token_age_sec = (datetime.now() - token_created_at).total_seconds()
            
            if token_age_sec < min_age_sec:
                return False
                
            if token_age_sec > max_age_sec:
                return False
                
        return True
        
    async def _analyze_token(self, token: Dict):
        """
        Perform detailed analysis on a token
        
        Args:
            token: Token data
        """
        try:
            blockchain = token.get("blockchain")
            if not blockchain or blockchain not in self.blockchain_clients:
                self.logger.warning(f"Unable to analyze token {token['address']}: blockchain {blockchain} not available")
                return
                
            client = self.blockchain_clients[blockchain]
            
            # Start analysis
            self.logger.info(f"Analyzing token {token['address']} ({token.get('symbol', 'UNKNOWN')})")
            
            # Get contract analysis
            contract_analysis = await client.analyze_contract(token["address"])
            
            # Check token safety
            if not contract_analysis.get("is_safe", False):
                self.logger.warning(f"Token {token['address']} failed safety check: {contract_analysis.get('risks', [])}")
                
                # Add to blacklist if severe risks are detected
                severe_risks = ["honeypot", "rug pull", "malicious code"]
                detected_risks = contract_analysis.get("risks", [])
                
                for risk in severe_risks:
                    if any(risk.lower() in detected_risk.lower() for detected_risk in detected_risks):
                        self.blacklisted_tokens.add(token["address"])
                        self.logger.info(f"Added {token['address']} to blacklist due to severe risk: {risk}")
                        
                return
                
            # Check liquidity
            liquidity = contract_analysis.get("liquidity_usd", 0)
            if liquidity < self.min_liquidity:
                self.logger.info(f"Token {token['address']} has insufficient liquidity: ${liquidity} < ${self.min_liquidity}")
                return
                
            # Check holder concentration
            top_holder_percentage = contract_analysis.get("top_holder_percentage", 0)
            if top_holder_percentage > self.max_holder_concentration:
                self.logger.warning(f"Token {token['address']} has high concentration: {top_holder_percentage}% > {self.max_holder_concentration}%")
                return
                
            # Check if smart money wallets are involved
            is_smart_money_involved = await self.wallet_tracker.check_smart_money_involvement(token["address"], blockchain)
            
            # Calculate opportunity score
            opportunity_score = self._calculate_opportunity_score(token, contract_analysis, is_smart_money_involved)
            
            # Prepare full analysis
            full_analysis = {
                **token,
                **contract_analysis,
                "liquidity_usd": liquidity,
                "is_smart_money_involved": is_smart_money_involved,
                "opportunity_score": opportunity_score,
                "analyzed_at": datetime.now().isoformat()
            }
            
            # Update statistics
            self.detection_stats["tokens_analyzed"] += 1
            
            # Emit analysis complete event
            self.event_emitter.emit("token_analysis_complete", full_analysis)
            
            # Check if this is a potential opportunity
            min_score_to_buy = self.config.get("analysis", {}).get("token_scoring", {}).get("min_score_to_buy", 60)
            if opportunity_score >= min_score_to_buy:
                self.event_emitter.emit("potential_opportunity", full_analysis)
                
        except Exception as e:
            self.logger.error(f"Error analyzing token {token.get('address')}: {str(e)}")
            
    def _calculate_priority_score(self, token: Dict) -> int:
        """
        Calculate priority score for a token based on source and other factors
        
        Args:
            token: Token data
            
        Returns:
            int: Priority score (higher is better)
        """
        base_score = 50
        
        # Blockchain priority
        blockchain = token.get("blockchain", "unknown")
        if blockchain == "solana":
            base_score += 30  # Solana has highest priority
        elif blockchain == "avalanche":
            base_score += 20
        elif blockchain == "sonic":
            base_score += 10
            
        # Source priority
        source = token.get("detection_source", "unknown")
        if source == "pump_fun":
            base_score += 15  # Pump.fun is a high-quality source for Solana
        elif source == "raydium":
            base_score += 12
        elif source == "jupiter":
            base_score += 10
        elif source == "dexscreener":
            base_score += 8
            
        # Age priority - newer tokens get higher priority
        if "created_at" in token:
            token_created_at = datetime.fromisoformat(token["created_at"])
            token_age_sec = (datetime.now() - token_created_at).total_seconds()
            
            # Tokens under 10 minutes old get highest priority
            if token_age_sec < 600:
                age_score = 20
            # Tokens under 30 minutes old get medium priority
            elif token_age_sec < 1800:
                age_score = 10
            # Tokens under 1 hour old get some priority
            elif token_age_sec < 3600:
                age_score = 5
            else:
                age_score = 0
                
            base_score += age_score
            
        return base_score
        
    def _calculate_opportunity_score(self, token: Dict, analysis: Dict, is_smart_money_involved: bool) -> int:
        """
        Calculate opportunity score for a token based on comprehensive analysis
        
        Args:
            token: Token data
            analysis: Contract analysis data
            is_smart_money_involved: Whether smart money wallets are involved
            
        Returns:
            int: Opportunity score (0-100, higher is better)
        """
        # Initialize with priority score
        score = token.get("priority_score", 50)
        
        # Factors and their weights from config
        factors = self.config.get("analysis", {}).get("token_scoring", {}).get("factors", {})
        
        # Liquidity factor (0-20 points)
        liquidity_weight = factors.get("liquidity", 20)
        liquidity = analysis.get("liquidity_usd", 0)
        
        if liquidity >= 500000:
            liquidity_score = 1.0
        elif liquidity >= 200000:
            liquidity_score = 0.8
        elif liquidity >= 100000:
            liquidity_score = 0.6
        elif liquidity >= 50000:
            liquidity_score = 0.4
        else:
            liquidity_score = 0.2
            
        score += liquidity_weight * liquidity_score
        
        # Holder distribution factor (0-25 points)
        distribution_weight = factors.get("holders_distribution", 25)
        top_holder_pct = analysis.get("top_holder_percentage", 100)
        holders_count = analysis.get("holders_count", 1)
        
        # Lower top holder percentage is better
        if top_holder_pct <= 10:
            concentration_score = 1.0
        elif top_holder_pct <= 20:
            concentration_score = 0.8
        elif top_holder_pct <= 30:
            concentration_score = 0.6
        elif top_holder_pct <= 40:
            concentration_score = 0.4
        else:
            concentration_score = 0.2
            
        # More holders is better
        if holders_count >= 100:
            holders_score = 1.0
        elif holders_count >= 50:
            holders_score = 0.8
        elif holders_count >= 20:
            holders_score = 0.6
        elif holders_count >= 10:
            holders_score = 0.4
        else:
            holders_score = 0.2
            
        distribution_score = (concentration_score + holders_score) / 2
        score += distribution_weight * distribution_score
        
        # Smart money factor (bonus points)
        if is_smart_money_involved:
            score += 15  # Significant bonus for smart money involvement
            
        # Cap the score at 100
        return min(100, round(score))
        
    async def _handle_token_analysis(self, analysis: Dict):
        """
        Handle completed token analysis
        
        Args:
            analysis: Token analysis data
        """
        # Store analysis in cache
        self.cache.set(f"analysis_{analysis['address']}", analysis)
        
        # Add to detected tokens queue
        self.detected_tokens.append(analysis)
        
        self.logger.info(f"Completed analysis for {analysis['address']} ({analysis.get('symbol', 'UNKNOWN')})")
        self.logger.info(f"Opportunity score: {analysis.get('opportunity_score', 0)}/100")
        
    async def _handle_potential_opportunity(self, analysis: Dict):
        """
        Handle potential buying opportunity
        
        Args:
            analysis: Token analysis data
        """
        self.logger.info(f"🚀 POTENTIAL OPPORTUNITY: {analysis.get('symbol', 'UNKNOWN')} ({analysis['address']})")
        self.logger.info(f"Score: {analysis.get('opportunity_score', 0)}/100, Liquidity: ${analysis.get('liquidity_usd', 0)}")
        
        # Update statistics
        self.detection_stats["potential_opportunities"] += 1
        
        # Notify via configured channels
        if self.config.get("notifications", {}).get("enabled", True) and self.config.get("notifications", {}).get("new_token_alert", True):
            # Prepare notification message
            message = f"🚀 NEW MEMECOIN OPPORTUNITY:\n"
            message += f"Token: {analysis.get('name', 'Unknown')} ({analysis.get('symbol', 'UNKNOWN')})\n"
            message += f"Blockchain: {analysis.get('blockchain', 'Unknown')}\n"
            message += f"Address: {analysis['address']}\n"
            message += f"Opportunity Score: {analysis.get('opportunity_score', 0)}/100\n"
            message += f"Liquidity: ${analysis.get('liquidity_usd', 0)}\n"
            message += f"Smart Money Involved: {'Yes' if analysis.get('is_smart_money_involved', False) else 'No'}\n"
            message += f"Detected: {analysis.get('detection_time', 'Unknown')}"
            
            # Send to notification channels (through event system)
            self.event_emitter.emit("notification", {
                "type": "opportunity",
                "message": message,
                "token": analysis
            })
            
    async def _handle_rug_pull(self, token_data: Dict):
        """
        Handle detected rug pull
        
        Args:
            token_data: Token data
        """
        address = token_data.get("address", "Unknown")
        symbol = token_data.get("symbol", "UNKNOWN")
        
        self.logger.warning(f"🚨 RUG PULL DETECTED: {symbol} ({address})")
        
        # Add to blacklist
        self.blacklisted_tokens.add(address)
        
        # Send alert if notifications are enabled
        if self.config.get("notifications", {}).get("enabled", True) and self.config.get("notifications", {}).get("rug_pull_alert", True):
            message = f"🚨 RUG PULL DETECTED:\n"
            message += f"Token: {token_data.get('name', 'Unknown')} ({symbol})\n"
            message += f"Address: {address}\n"
            message += f"Blockchain: {token_data.get('blockchain', 'Unknown')}\n"
            message += f"Reason: {token_data.get('rug_pull_reason', 'Unknown')}"
            
            # Send to notification channels
            self.event_emitter.emit("notification", {
                "type": "rug_pull",
                "message": message,
                "token": token_data
            })
            
    def get_detected_tokens(self, count: int = 10, min_score: Optional[int] = None, blockchain: Optional[str] = None) -> List[Dict]:
        """
        Get recently detected tokens with optional filtering
        
        Args:
            count: Maximum number of tokens to return
            min_score: Minimum opportunity score filter
            blockchain: Filter by blockchain
            
        Returns:
            List[Dict]: List of detected tokens
        """
        tokens = list(self.detected_tokens)
        
        # Apply filters
        if min_score is not None:
            tokens = [t for t in tokens if t.get("opportunity_score", 0) >= min_score]
            
        if blockchain is not None:
            tokens = [t for t in tokens if t.get("blockchain") == blockchain]
            
        # Sort by opportunity score
        tokens.sort(key=lambda x: x.get("opportunity_score", 0), reverse=True)
        
        return tokens[:count]
        
    def get_detection_stats(self) -> Dict:
        """
        Get detection statistics
        
        Returns:
            Dict: Detection statistics
        """
        return self.detection_stats 