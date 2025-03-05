import asyncio
import logging
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import json
import uuid
import random

from gbpbot.core.clients.solana_client import SolanaBlockchainClient
from gbpbot.core.detection.memecoin_detector import MemecoinDetector
from gbpbot.database.wallet_tracker import WalletTracker
from gbpbot.utils.logging_utils import setup_logger
from gbpbot.utils.config_utils import load_config
from gbpbot.core.transaction.transaction_status import TransactionStatus
from gbpbot.api_adapters.dexscreener_adapter import DexScreenerAdapter

class SolanaMemecoinSniper:
    """
    Advanced Solana memecoin sniper designed for ultra-fast execution
    and precision entry/exit strategies. Optimized for Jito MEV bundles
    and high-priority transaction submission.
    
    Features:
    - Real-time token detection and analysis
    - Smart money wallet tracking
    - Advanced scoring and filtering algorithms
    - Multi-stage entry/exit strategy
    - MEV protection via Jito bundles
    - Risk management with position sizing
    - Jito tip priority fee mechanism
    - Auto stop-loss and take-profit execution
    """
    
    def __init__(self, config_path: str = "config/solana_config.json"):
        """
        Initialize the Solana memecoin sniper with configuration
        
        Args:
            config_path: Path to the configuration file
        """
        # Load config
        self.config = load_config(config_path)
        self.solana_config = self.config.get("solana", {})
        self.sniping_config = self.solana_config.get("sniping", {})
        
        # Configure logger
        self.logger = setup_logger("SolanaMemecoinSniper", logging.INFO)
        self.logger.info("Initializing Solana Memecoin Sniper")
        
        # Initialize components
        self.blockchain_client = None
        self.memecoin_detector = None
        self.wallet_tracker = None
        self.dex_adapter = None
        
        # Performance tracking
        self.start_time = time.time()
        self.tokens_analyzed = 0
        self.tokens_sniped = 0
        self.successful_trades = 0
        self.failed_trades = 0
        self.profitable_trades = 0
        
        # Active positions tracking
        self.active_positions = {}  # token_address -> position_data
        self.pending_transactions = {}  # tx_hash -> transaction_data
        
        # Initialize components
        self._initialize_components()
        
        # Flags
        self.is_running = False
        self.paused = False
        
    def _initialize_components(self):
        """Initialize all required components for the sniper"""
        try:
            # Initialize blockchain client
            self.blockchain_client = SolanaBlockchainClient(self.config)
            
            # Initialize memecoin detector
            self.memecoin_detector = MemecoinDetector(self.config)
            
            # Initialize wallet tracker
            self.wallet_tracker = WalletTracker(self.config)
            
            # Initialize DexScreener adapter
            self.dex_adapter = DexScreenerAdapter(self.config)
            
            self.logger.info("All components initialized successfully")
        except Exception as e:
            self.logger.error(f"Error initializing components: {str(e)}")
            raise
    
    async def start(self):
        """Start the memecoin sniper"""
        if self.is_running:
            self.logger.warning("Sniper is already running")
            return
        
        self.is_running = True
        self.paused = False
        
        try:
            # Connect to blockchain
            await self.blockchain_client.connect()
            
            # Start detection
            await self.memecoin_detector.start()
            
            # Start monitoring loop
            self.logger.info("Starting monitoring loop")
            asyncio.create_task(self._monitoring_loop())
            
            # Start position management loop
            asyncio.create_task(self._position_management_loop())
            
            # Register event handlers
            self._register_event_handlers()
            
            self.logger.info("Solana Memecoin Sniper started successfully")
        except Exception as e:
            self.is_running = False
            self.logger.error(f"Error starting sniper: {str(e)}")
            raise
    
    async def stop(self):
        """Stop the memecoin sniper"""
        if not self.is_running:
            self.logger.warning("Sniper is not running")
            return
        
        self.is_running = False
        
        try:
            # Stop detection
            await self.memecoin_detector.stop()
            
            # Close connections and cleanup
            # Wait for pending transactions to complete
            self.logger.info("Waiting for pending transactions to complete...")
            await self._wait_for_pending_transactions(timeout=60)
            
            self.logger.info("Solana Memecoin Sniper stopped successfully")
        except Exception as e:
            self.logger.error(f"Error stopping sniper: {str(e)}")
            raise
    
    def _register_event_handlers(self):
        """Register event handlers for token detection and analysis"""
        # Listen for potential opportunities from the detector
        self.memecoin_detector.on("potential_opportunity", self._handle_potential_opportunity)
        
        # Listen for completed analysis
        self.memecoin_detector.on("token_analysis_complete", self._handle_token_analysis)
        
        # Listen for rug pull detection
        self.memecoin_detector.on("rug_pull_detected", self._handle_rug_pull)
    
    async def _monitoring_loop(self):
        """Main monitoring loop for the sniper"""
        while self.is_running:
            try:
                if not self.paused:
                    # Check for new high-potential tokens
                    high_potential_tokens = self.memecoin_detector.get_detected_tokens(
                        min_score=self.sniping_config.get("min_score_to_buy", 70),
                        blockchain="solana",
                        count=5
                    )
                    
                    for token in high_potential_tokens:
                        if token["address"] not in self.active_positions and not self._is_blacklisted(token["address"]):
                            await self._evaluate_token_for_sniping(token)
                
                # Check active positions for exit conditions
                await self._check_exit_conditions()
                
                # Update performance metrics
                self._update_performance_metrics()
                
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {str(e)}")
            
            # Sleep interval
            await asyncio.sleep(self.sniping_config.get("scan_interval_ms", 500) / 1000)
    
    async def _position_management_loop(self):
        """Loop for managing active positions"""
        while self.is_running:
            try:
                # Check for completed transactions
                for tx_hash, tx_data in list(self.pending_transactions.items()):
                    if time.time() - tx_data["timestamp"] > tx_data.get("timeout", 60):
                        # Transaction timed out
                        self.logger.warning(f"Transaction timed out: {tx_hash}")
                        self.pending_transactions.pop(tx_hash, None)
                        self.failed_trades += 1
                        continue
                    
                    # Check transaction status
                    tx_status = await self.blockchain_client.wait_for_transaction(
                        tx_hash, timeout=1
                    )
                    
                    if tx_status["status"] == TransactionStatus.CONFIRMED:
                        # Transaction confirmed
                        self.logger.info(f"Transaction confirmed: {tx_hash}")
                        
                        # Handle confirmed transaction
                        await self._handle_confirmed_transaction(tx_hash, tx_data, tx_status)
                        
                        # Remove from pending
                        self.pending_transactions.pop(tx_hash, None)
                    
                    elif tx_status["status"] == TransactionStatus.FAILED:
                        # Transaction failed
                        self.logger.warning(f"Transaction failed: {tx_hash} - {tx_status.get('error', 'Unknown error')}")
                        self.pending_transactions.pop(tx_hash, None)
                        self.failed_trades += 1
            
            except Exception as e:
                self.logger.error(f"Error in position management loop: {str(e)}")
            
            # Sleep interval
            await asyncio.sleep(2)
    
    async def _evaluate_token_for_sniping(self, token: Dict):
        """
        Evaluate a token for sniping opportunity
        
        Args:
            token: Token data dictionary
        """
        self.tokens_analyzed += 1
        token_address = token["address"]
        
        try:
            # Get additional token information
            token_info = await self.dex_adapter.get_token_info(token_address, "solana")
            
            # Check if smart money wallets are involved
            is_smart_money = await self.wallet_tracker.check_smart_money_involvement(token_address, "solana")
            
            # Calculate opportunity score
            opportunity_score = self._calculate_opportunity_score(token, token_info, is_smart_money)
            
            self.logger.info(f"Token {token['symbol']} opportunity score: {opportunity_score}")
            
            # Check if score meets threshold
            min_score = self.sniping_config.get("min_score_to_buy", 70)
            if opportunity_score >= min_score:
                # Check honeypot and liquidity
                analysis = await self.blockchain_client.analyze_contract(token_address)
                
                if not analysis["is_honeypot"] and analysis["liquidity"]["usd"] >= self.sniping_config.get("trade_settings", {}).get("min_liquidity_usd", 50000):
                    # Execute snipe
                    await self._execute_snipe(token, token_info, analysis, opportunity_score)
            
        except Exception as e:
            self.logger.error(f"Error evaluating token {token.get('symbol', token_address)}: {str(e)}")
    
    async def _execute_snipe(self, token: Dict, token_info: Dict, analysis: Dict, score: int):
        """
        Execute a token snipe
        
        Args:
            token: Token data dictionary
            token_info: Additional token information
            analysis: Contract analysis data
            score: Opportunity score
        """
        token_address = token["address"]
        symbol = token["symbol"]
        
        # Calculate position size based on confidence score
        position_size = self._calculate_position_size(score, analysis["risk_level"])
        
        # Default to USDC (EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v)
        usdc_address = self.solana_config.get("tokens", {}).get("usdc", "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v")
        
        try:
            self.logger.info(f"Executing snipe for {symbol} with position size: {position_size} USDC")
            
            # Get transaction settings
            slippage = self.sniping_config.get("trade_settings", {}).get("default_slippage", 0.5)
            gas_priority = self.sniping_config.get("gas_priority", {}).get("default", "high")
            
            # Execute swap
            tx_result = await self.blockchain_client.execute_swap(
                token_in=usdc_address,  # USDC
                token_out=token_address,  # Target token
                amount_in=position_size,
                slippage=slippage,
                gas_priority=gas_priority
            )
            
            if tx_result and "transaction_hash" in tx_result:
                tx_hash = tx_result["transaction_hash"]
                self.logger.info(f"Snipe executed for {symbol}. Transaction hash: {tx_hash}")
                
                # Record transaction
                entry_timestamp = datetime.now().isoformat()
                
                # Add to pending transactions
                self.pending_transactions[tx_hash] = {
                    "type": "buy",
                    "token_address": token_address,
                    "symbol": symbol,
                    "amount_in": position_size,
                    "timestamp": time.time(),
                    "timeout": 60,
                    "score": score,
                    "entry_time": entry_timestamp
                }
                
                # Add to active positions
                self.active_positions[token_address] = {
                    "symbol": symbol,
                    "entry_transaction": tx_hash,
                    "entry_price_usd": token_info.get("price_usd", 0),
                    "entry_time": entry_timestamp,
                    "position_size_usd": position_size,
                    "amount_in": position_size,
                    "token_amount": 0,  # Will be updated when transaction confirms
                    "current_price_usd": token_info.get("price_usd", 0),
                    "current_value_usd": position_size,
                    "profit_loss_pct": 0,
                    "take_profit_targets": self._calculate_take_profit_targets(token_info.get("price_usd", 0)),
                    "stop_loss_price": self._calculate_stop_loss_price(token_info.get("price_usd", 0)),
                    "score": score,
                    "last_updated": time.time()
                }
                
                self.tokens_sniped += 1
                
                # Record in wallet tracker
                await self.wallet_tracker.record_transaction(
                    wallet_address=self.blockchain_client.wallet.public_key,
                    blockchain="solana",
                    token_address=token_address,
                    transaction_type="buy",
                    amount=position_size,
                    usd_value=position_size,
                    timestamp=entry_timestamp,
                    tx_hash=tx_hash
                )
                
            else:
                self.logger.error(f"Failed to execute snipe for {symbol}")
                self.failed_trades += 1
                
        except Exception as e:
            self.logger.error(f"Error executing snipe for {symbol}: {str(e)}")
            self.failed_trades += 1
    
    async def _check_exit_conditions(self):
        """Check exit conditions for all active positions"""
        for token_address, position in list(self.active_positions.items()):
            try:
                # Skip if there's a pending transaction for this token
                if any(tx_data["token_address"] == token_address and tx_data["type"] == "sell" 
                       for tx_data in self.pending_transactions.values()):
                    continue
                
                # Get current price
                current_price = await self.blockchain_client.get_token_price(token_address, "usdc")
                
                if current_price <= 0:
                    continue
                
                # Update position data
                position["current_price_usd"] = current_price
                position["current_value_usd"] = position["token_amount"] * current_price
                
                entry_price = position["entry_price_usd"]
                if entry_price > 0:
                    position["profit_loss_pct"] = ((current_price / entry_price) - 1) * 100
                
                position["last_updated"] = time.time()
                
                # Check take profit targets
                for i, target in enumerate(position["take_profit_targets"]):
                    if not target.get("triggered", False) and current_price >= target["price"]:
                        # Take profit triggered
                        target_pct = target["percentage"]
                        if target_pct > 0:
                            await self._execute_partial_exit(token_address, position, target_pct, "take_profit")
                            target["triggered"] = True
                
                # Check stop loss
                if current_price <= position["stop_loss_price"]:
                    # Stop loss triggered
                    await self._execute_full_exit(token_address, position, "stop_loss")
                
                # Check time-based exit
                holding_time = time.time() - datetime.fromisoformat(position["entry_time"]).timestamp()
                max_holding_time = self.sniping_config.get("max_holding_time_minutes", 120) * 60
                
                if holding_time > max_holding_time:
                    # Time-based exit
                    await self._execute_full_exit(token_address, position, "time_based")
                
            except Exception as e:
                self.logger.error(f"Error checking exit conditions for {position.get('symbol', token_address)}: {str(e)}")
    
    async def _execute_partial_exit(self, token_address: str, position: Dict, percentage: float, reason: str):
        """
        Execute a partial exit for a position
        
        Args:
            token_address: Token address
            position: Position data
            percentage: Percentage to sell (0-100)
            reason: Reason for exit
        """
        if percentage <= 0 or percentage > 100:
            self.logger.error(f"Invalid exit percentage: {percentage}")
            return
        
        symbol = position["symbol"]
        sell_amount = position["token_amount"] * (percentage / 100)
        
        self.logger.info(f"Executing {percentage}% exit for {symbol} due to {reason}")
        
        # Check if min_amount_to_sell is configured and sell_amount is less
        min_sell_amount_usd = self.sniping_config.get("min_exit_amount_usd", 5)
        estimated_sell_value = sell_amount * position["current_price_usd"]
        
        if estimated_sell_value < min_sell_amount_usd:
            self.logger.info(f"Skipping partial exit for {symbol}: estimated value ${estimated_sell_value:.2f} below minimum ${min_sell_amount_usd}")
            return
        
        try:
            # Get USDC address
            usdc_address = self.solana_config.get("tokens", {}).get("usdc", "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v")
            
            # Execute swap
            tx_result = await self.blockchain_client.execute_swap(
                token_in=token_address,
                token_out=usdc_address,
                amount_in=sell_amount,
                slippage=1.0,  # Higher slippage for exits
                gas_priority="high"  # High gas priority for exits
            )
            
            if tx_result and "transaction_hash" in tx_result:
                tx_hash = tx_result["transaction_hash"]
                self.logger.info(f"Partial exit ({percentage}%) executed for {symbol}. Transaction hash: {tx_hash}")
                
                # Record transaction
                exit_timestamp = datetime.now().isoformat()
                
                # Add to pending transactions
                self.pending_transactions[tx_hash] = {
                    "type": "sell",
                    "token_address": token_address,
                    "symbol": symbol,
                    "amount": sell_amount,
                    "percentage": percentage,
                    "timestamp": time.time(),
                    "timeout": 60,
                    "reason": reason,
                    "exit_time": exit_timestamp
                }
                
                # Update position data (will be fully updated when transaction confirms)
                position["token_amount"] -= sell_amount
                
                # Record in wallet tracker
                estimated_usd_value = sell_amount * position["current_price_usd"]
                await self.wallet_tracker.record_transaction(
                    wallet_address=self.blockchain_client.wallet.public_key,
                    blockchain="solana",
                    token_address=token_address,
                    transaction_type="sell",
                    amount=sell_amount,
                    usd_value=estimated_usd_value,
                    timestamp=exit_timestamp,
                    tx_hash=tx_hash
                )
                
            else:
                self.logger.error(f"Failed to execute partial exit for {symbol}")
                
        except Exception as e:
            self.logger.error(f"Error executing partial exit for {symbol}: {str(e)}")
    
    async def _execute_full_exit(self, token_address: str, position: Dict, reason: str):
        """
        Execute a full exit for a position
        
        Args:
            token_address: Token address
            position: Position data
            reason: Reason for exit
        """
        symbol = position["symbol"]
        
        self.logger.info(f"Executing full exit for {symbol} due to {reason}")
        
        try:
            # Get USDC address
            usdc_address = self.solana_config.get("tokens", {}).get("usdc", "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v")
            
            # Execute swap
            tx_result = await self.blockchain_client.execute_swap(
                token_in=token_address,
                token_out=usdc_address,
                amount_in=0,  # 0 means sell all
                slippage=2.0,  # Higher slippage for emergency exits
                gas_priority="urgent"  # Urgent gas priority for full exits
            )
            
            if tx_result and "transaction_hash" in tx_result:
                tx_hash = tx_result["transaction_hash"]
                self.logger.info(f"Full exit executed for {symbol}. Transaction hash: {tx_hash}")
                
                # Record transaction
                exit_timestamp = datetime.now().isoformat()
                
                # Add to pending transactions
                self.pending_transactions[tx_hash] = {
                    "type": "sell",
                    "token_address": token_address,
                    "symbol": symbol,
                    "amount": position["token_amount"],
                    "percentage": 100,
                    "timestamp": time.time(),
                    "timeout": 60,
                    "reason": reason,
                    "exit_time": exit_timestamp,
                    "is_full_exit": True
                }
                
                # Remove from active positions when transaction confirms
                # This will happen in _handle_confirmed_transaction
                
                # Record in wallet tracker
                estimated_usd_value = position["token_amount"] * position["current_price_usd"]
                await self.wallet_tracker.record_transaction(
                    wallet_address=self.blockchain_client.wallet.public_key,
                    blockchain="solana",
                    token_address=token_address,
                    transaction_type="sell",
                    amount=position["token_amount"],
                    usd_value=estimated_usd_value,
                    timestamp=exit_timestamp,
                    tx_hash=tx_hash
                )
                
            else:
                self.logger.error(f"Failed to execute full exit for {symbol}")
                
        except Exception as e:
            self.logger.error(f"Error executing full exit for {symbol}: {str(e)}")
    
    async def _handle_confirmed_transaction(self, tx_hash: str, tx_data: Dict, tx_status: Dict):
        """
        Handle a confirmed transaction
        
        Args:
            tx_hash: Transaction hash
            tx_data: Transaction data
            tx_status: Transaction status
        """
        token_address = tx_data["token_address"]
        transaction_type = tx_data["type"]
        
        if transaction_type == "buy":
            # Buy transaction confirmed
            # Update token amount in active position
            if token_address in self.active_positions:
                # Get token balance
                token_balance = await self.blockchain_client.get_token_balance(token_address)
                
                # Update position data
                self.active_positions[token_address]["token_amount"] = token_balance
                self.active_positions[token_address]["current_value_usd"] = token_balance * self.active_positions[token_address]["current_price_usd"]
                
                self.logger.info(f"Buy confirmed for {tx_data['symbol']}. Token amount: {token_balance}")
                
                # Increment successful trades counter
                self.successful_trades += 1
        
        elif transaction_type == "sell":
            # Sell transaction confirmed
            percentage = tx_data.get("percentage", 100)
            is_full_exit = tx_data.get("is_full_exit", False) or percentage >= 100
            
            if is_full_exit:
                # Full exit - remove from active positions
                if token_address in self.active_positions:
                    position = self.active_positions.pop(token_address)
                    
                    # Calculate profit/loss
                    entry_value = position["amount_in"]
                    exit_value = tx_status.get("value_out", 0)
                    
                    profit_loss = exit_value - entry_value
                    profit_loss_pct = ((exit_value / entry_value) - 1) * 100 if entry_value > 0 else 0
                    
                    self.logger.info(f"Full exit confirmed for {tx_data['symbol']}. " +
                                   f"P/L: ${profit_loss:.2f} ({profit_loss_pct:.2f}%)")
                    
                    # Record profit/loss
                    if profit_loss > 0:
                        self.profitable_trades += 1
                    
                    # Increment successful trades counter
                    self.successful_trades += 1
            else:
                # Partial exit - update position
                if token_address in self.active_positions:
                    # Recalculate token amount based on blockchain data
                    token_balance = await self.blockchain_client.get_token_balance(token_address)
                    
                    # Update position data
                    self.active_positions[token_address]["token_amount"] = token_balance
                    self.active_positions[token_address]["current_value_usd"] = token_balance * self.active_positions[token_address]["current_price_usd"]
                    
                    self.logger.info(f"Partial exit ({percentage}%) confirmed for {tx_data['symbol']}. Remaining: {token_balance}")
                    
                    # Increment successful trades counter
                    self.successful_trades += 1
    
    async def _wait_for_pending_transactions(self, timeout: int = 60):
        """
        Wait for all pending transactions to complete
        
        Args:
            timeout: Maximum time to wait in seconds
        """
        start_time = time.time()
        
        while self.pending_transactions and time.time() - start_time < timeout:
            # Check for completed transactions
            for tx_hash, tx_data in list(self.pending_transactions.items()):
                try:
                    # Check transaction status
                    tx_status = await self.blockchain_client.wait_for_transaction(
                        tx_hash, timeout=1
                    )
                    
                    if tx_status["status"] in [TransactionStatus.CONFIRMED, TransactionStatus.FAILED]:
                        # Transaction completed (confirmed or failed)
                        self.pending_transactions.pop(tx_hash, None)
                except Exception:
                    pass
            
            # Sleep briefly
            await asyncio.sleep(1)
        
        # Timeout - clear remaining pending transactions
        if self.pending_transactions:
            self.logger.warning(f"Timed out waiting for {len(self.pending_transactions)} pending transactions")
            self.pending_transactions.clear()
    
    async def _handle_potential_opportunity(self, token_data: Dict):
        """
        Handle a potential opportunity detected by the memecoin detector
        
        Args:
            token_data: Token data
        """
        if not self.is_running or self.paused:
            return
        
        token_address = token_data["address"]
        
        # Skip if already in active positions
        if token_address in self.active_positions:
            return
        
        # Skip if blacklisted
        if self._is_blacklisted(token_address):
            return
        
        # Evaluate for sniping
        await self._evaluate_token_for_sniping(token_data)
    
    async def _handle_token_analysis(self, analysis: Dict):
        """
        Handle a completed token analysis
        
        Args:
            analysis: Token analysis data
        """
        # This method can be used to update any existing positions
        # based on new analysis data
        token_address = analysis["token_address"]
        
        if token_address in self.active_positions:
            # Update position data with new analysis
            self.active_positions[token_address]["risk_level"] = analysis.get("risk_level", "high")
            self.active_positions[token_address]["analysis_score"] = analysis.get("score", 0)
    
    async def _handle_rug_pull(self, token_data: Dict):
        """
        Handle a rug pull detection
        
        Args:
            token_data: Token data
        """
        token_address = token_data["address"]
        
        if token_address in self.active_positions:
            # Emergency exit on rug pull detection
            self.logger.warning(f"RUG PULL DETECTED for {token_data['symbol']}! Executing emergency exit")
            await self._execute_full_exit(token_address, self.active_positions[token_address], "rug_pull")
    
    def _calculate_opportunity_score(self, token: Dict, token_info: Dict, is_smart_money: bool) -> int:
        """
        Calculate an opportunity score for a token
        
        Args:
            token: Token basic data
            token_info: Detailed token information
            is_smart_money: Whether smart money wallets are involved
            
        Returns:
            Opportunity score (0-100)
        """
        base_score = 50
        
        # Smart money involvement is a strong signal
        if is_smart_money:
            base_score += 20
        
        # Token age
        token_age_hours = token_info.get("age_hours", 0)
        if token_age_hours < 1:
            base_score += 15  # Very new tokens get a boost
        elif token_age_hours < 6:
            base_score += 10
        elif token_age_hours < 24:
            base_score += 5
        
        # Liquidity
        liquidity_usd = token_info.get("liquidity", {}).get("usd", 0)
        min_liquidity = self.sniping_config.get("trade_settings", {}).get("min_liquidity_usd", 50000)
        
        if liquidity_usd > min_liquidity * 2:
            base_score += 10
        elif liquidity_usd > min_liquidity:
            base_score += 5
        else:
            base_score -= 30  # Penalize low liquidity heavily
        
        # Price change
        price_change_24h = token_info.get("price_change", {}).get("h24", 0)
        if price_change_24h > 100:
            base_score += 10  # Strong momentum
        elif price_change_24h > 50:
            base_score += 5
        elif price_change_24h < -50:
            base_score -= 20  # Downtrend
        
        # Holders count (if available)
        holders = token_info.get("holders", 0)
        if holders > 1000:
            base_score += 5
        elif holders > 500:
            base_score += 3
        elif holders < 50:
            base_score -= 5
        
        # Trading volume
        volume_usd_24h = token_info.get("volume", {}).get("h24", 0)
        min_volume = self.sniping_config.get("trade_settings", {}).get("min_volume_usd", 100000)
        
        if volume_usd_24h > min_volume:
            base_score += 10
        elif volume_usd_24h > min_volume / 2:
            base_score += 5
        elif volume_usd_24h < min_volume / 10:
            base_score -= 10
        
        # Ensure score is within 0-100 range
        return max(0, min(100, base_score))
    
    def _calculate_position_size(self, score: int, risk_level: str) -> float:
        """
        Calculate position size based on opportunity score and risk level
        
        Args:
            score: Opportunity score (0-100)
            risk_level: Risk level (low, medium, high)
            
        Returns:
            Position size in USDC
        """
        max_allocation = self.solana_config.get("security", {}).get("max_allocation_per_token_usd", 1000)
        
        # Base allocation percentage based on score
        if score >= 90:
            allocation_pct = 1.0  # 100% of max allocation
        elif score >= 80:
            allocation_pct = 0.8  # 80% of max allocation
        elif score >= 70:
            allocation_pct = 0.6  # 60% of max allocation
        elif score >= 60:
            allocation_pct = 0.4  # 40% of max allocation
        else:
            allocation_pct = 0.2  # 20% of max allocation
        
        # Adjust based on risk level
        if risk_level == "high":
            allocation_pct *= 0.5  # Reduce allocation for high risk
        elif risk_level == "medium":
            allocation_pct *= 0.75  # Slightly reduce for medium risk
        
        # Calculate final position size
        position_size = max_allocation * allocation_pct
        
        # Ensure minimum position size
        min_position_size = 10  # Minimum $10 USDC
        return max(min_position_size, position_size)
    
    def _calculate_take_profit_targets(self, entry_price: float) -> List[Dict]:
        """
        Calculate take profit targets based on entry price
        
        Args:
            entry_price: Entry price in USD
            
        Returns:
            List of take profit targets
        """
        take_profit_levels = self.sniping_config.get("profitability", {}).get("take_profit_levels", [
            {"multiplier": 2.0, "percentage": 25},
            {"multiplier": 5.0, "percentage": 50},
            {"multiplier": 10.0, "percentage": 100}
        ])
        
        targets = []
        for level in take_profit_levels:
            multiplier = level.get("multiplier", 2.0)
            percentage = level.get("percentage", 50)
            
            targets.append({
                "price": entry_price * multiplier,
                "percentage": percentage,
                "triggered": False
            })
        
        return targets
    
    def _calculate_stop_loss_price(self, entry_price: float) -> float:
        """
        Calculate stop loss price based on entry price
        
        Args:
            entry_price: Entry price in USD
            
        Returns:
            Stop loss price
        """
        stop_loss_pct = self.sniping_config.get("profitability", {}).get("stop_loss", {}).get("percentage", 30)
        stop_loss_multiplier = 1 - (stop_loss_pct / 100)
        
        return entry_price * stop_loss_multiplier
    
    def _is_blacklisted(self, token_address: str) -> bool:
        """
        Check if a token is blacklisted
        
        Args:
            token_address: Token address
            
        Returns:
            True if blacklisted, False otherwise
        """
        blacklisted_tokens = self.config.get("blacklist", {}).get("tokens", [])
        return token_address in blacklisted_tokens
    
    def _update_performance_metrics(self):
        """Update performance metrics"""
        runtime_seconds = time.time() - self.start_time
        runtime_minutes = runtime_seconds / 60
        
        if runtime_minutes > 0:
            tokens_per_minute = self.tokens_analyzed / runtime_minutes
            self.logger.debug(f"Performance: {tokens_per_minute:.1f} tokens/minute, " +
                           f"{self.tokens_sniped} sniped, {self.successful_trades} successful, " +
                           f"{self.profitable_trades} profitable")
    
    def get_performance_stats(self) -> Dict:
        """
        Get performance statistics
        
        Returns:
            Dictionary of performance statistics
        """
        runtime_seconds = time.time() - self.start_time
        
        return {
            "runtime_seconds": runtime_seconds,
            "tokens_analyzed": self.tokens_analyzed,
            "tokens_sniped": self.tokens_sniped,
            "successful_trades": self.successful_trades,
            "failed_trades": self.failed_trades,
            "profitable_trades": self.profitable_trades,
            "active_positions": len(self.active_positions),
            "pending_transactions": len(self.pending_transactions),
            "tokens_per_minute": self.tokens_analyzed / (runtime_seconds / 60) if runtime_seconds > 0 else 0
        }
    
    def get_active_positions(self) -> Dict:
        """
        Get active positions
        
        Returns:
            Dictionary of active positions
        """
        return self.active_positions
    
    async def execute_entry_transaction(self, token_address: str, amount_usdc: float,
                                    slippage: float = 1.5) -> Dict:
        """
        Execute an entry transaction for a token opportunity.
        
        Args:
            token_address: Token address to enter
            amount_usdc: Amount of USDC to use for entry
            slippage: Maximum slippage percentage
            
        Returns:
            Dict: Transaction result with status
        """
        try:
            self.logger.info(f"Executing entry transaction for {token_address} with {amount_usdc} USDC")
            
            # Use Jito bundles for MEV protection on entry transactions for best execution
            use_jito = self.sniping_config.get("use_jito_for_entry", True)
            if use_jito:
                self.logger.info("Using Jito bundles for MEV protection on entry transaction")
            
            # Execute swap from USDC to token
            usdc_address = self.solana_config.get("token_addresses", {}).get("USDC")
            
            tx_result = await self.blockchain_client.execute_swap(
                token_in=usdc_address,
                token_out=token_address,
                amount_in=amount_usdc,
                slippage=slippage,
                use_jito_bundle=use_jito,
                priority_fee=None,  # Use optimal fee determined by client
                deadline_seconds=30  # Shorter deadline for entries
            )
            
            if tx_result.get("success"):
                tx_signature = tx_result.get("signature")
                self.logger.info(f"Entry transaction successful: {tx_signature}")
                
                # Wait for transaction confirmation
                tx_status = await self.blockchain_client.wait_for_transaction(
                    tx_signature, timeout=60
                )
                
                # Record the position in active positions
                if tx_status.get("confirmed", False):
                    self.active_positions[token_address] = {
                        "entry_time": time.time(),
                        "entry_price": await self._get_token_price(token_address),
                        "amount_spent": amount_usdc,
                        "token_address": token_address,
                        "entry_tx": tx_signature,
                        "mev_protected": tx_result.get("mev_protected", False)
                    }
                    
                    # Update position with token balance
                    await self._update_position_balances(token_address)
                    
                    return {
                        "success": True,
                        "signature": tx_signature,
                        "position": self.active_positions[token_address]
                    }
                else:
                    return {
                        "success": False,
                        "error": "Transaction failed to confirm",
                        "details": tx_status
                    }
            else:
                self.logger.error(f"Entry transaction failed: {tx_result.get('error')}")
                return {
                    "success": False,
                    "error": tx_result.get("error", "Unknown error"),
                    "details": tx_result
                }
        except Exception as e:
            self.logger.error(f"Error executing entry transaction: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def execute_exit_transaction(self, token_address: str, percentage: float = 100,
                                      slippage: float = 2.0) -> Dict:
        """
        Execute an exit transaction for a token position.
        
        Args:
            token_address: Token address to exit
            percentage: Percentage of position to exit (0-100)
            slippage: Maximum slippage percentage
            
        Returns:
            Dict: Transaction result with status
        """
        try:
            if token_address not in self.active_positions:
                return {
                    "success": False,
                    "error": "No active position for this token"
                }
                
            self.logger.info(f"Executing exit transaction for {token_address} ({percentage}%)")
            
            # Determine whether to use Jito for exit
            # For larger positions or volatile exits, MEV protection is more important
            position = self.active_positions[token_address]
            position_value = position.get("current_value", 0)
            use_jito = False
            
            # Use Jito for exits if:
            # 1. Position is large (over threshold)
            # 2. Token is volatile (high volume/liquidity ratio)
            # 3. Explicitly configured to use Jito for exits
            jito_exit_threshold = self.sniping_config.get("jito_exit_threshold", 100)  # USDC
            if (position_value > jito_exit_threshold or 
                self.sniping_config.get("use_jito_for_exit", False)):
                use_jito = True
                self.logger.info(f"Using Jito bundles for MEV protection on exit transaction (position value: {position_value} USDC)")
            
            # Get token balance
            token_balance = await self.blockchain_client.get_token_balance(token_address)
            
            # Calculate amount to sell based on percentage
            amount_to_sell = token_balance * (percentage / 100)
            
            # Execute swap from token to USDC
            usdc_address = self.solana_config.get("token_addresses", {}).get("USDC")
            
            tx_result = await self.blockchain_client.execute_swap(
                token_in=token_address,
                token_out=usdc_address,
                amount_in=amount_to_sell,
                slippage=slippage,
                use_jito_bundle=use_jito,
                priority_fee=None,  # Use optimal fee determined by client
                deadline_seconds=60  # Longer deadline for exits to ensure they complete
            )
            
            if tx_result.get("success"):
                tx_signature = tx_result.get("signature")
                self.logger.info(f"Exit transaction successful: {tx_signature}")
                
                # Update position status
                if percentage >= 100:
                    # Remove position if fully exited
                    position = self.active_positions.pop(token_address)
                    self.closed_positions.append({
                        **position,
                        "exit_time": time.time(),
                        "exit_price": await self._get_token_price(token_address),
                        "exit_tx": tx_signature,
                        "mev_protected_exit": tx_result.get("mev_protected", False),
                        "exited": True
                    })
                else:
                    # Update position if partially exited
                    await self._update_position_balances(token_address)
                    self.active_positions[token_address]["partial_exits"] = \
                        self.active_positions[token_address].get("partial_exits", []) + [
                            {
                                "time": time.time(),
                                "percentage": percentage,
                                "tx": tx_signature,
                                "mev_protected": tx_result.get("mev_protected", False)
                            }
                        ]
                
                return {
                    "success": True,
                    "signature": tx_signature,
                    "percentage_exited": percentage
                }
            else:
                self.logger.error(f"Exit transaction failed: {tx_result.get('error')}")
                return {
                    "success": False,
                    "error": tx_result.get("error", "Unknown error"),
                    "details": tx_result
                }
        except Exception as e:
            self.logger.error(f"Error executing exit transaction: {str(e)}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def _update_position_balances(self, token_address: str) -> None:
        """
        Update token balances and value for a position
        
        Args:
            token_address: Token address to update
        """
        if token_address not in self.active_positions:
            return
            
        try:
            # Get current token balance
            token_balance = await self.blockchain_client.get_token_balance(token_address)
            
            # Get current token price
            current_price = await self._get_token_price(token_address)
            
            # Calculate current value
            current_value = token_balance * current_price
            
            # Update position data
            self.active_positions[token_address].update({
                "token_balance": token_balance,
                "current_price": current_price,
                "current_value": current_value,
                "last_updated": time.time()
            })
            
            # Calculate profit/loss
            entry_price = self.active_positions[token_address].get("entry_price", 0)
            if entry_price > 0:
                price_change_pct = (current_price - entry_price) / entry_price * 100
                self.active_positions[token_address]["pnl_percentage"] = price_change_pct
                
            amount_spent = self.active_positions[token_address].get("amount_spent", 0)
            if amount_spent > 0:
                value_change = current_value - amount_spent
                self.active_positions[token_address]["pnl_value"] = value_change
                self.active_positions[token_address]["pnl_percentage"] = (value_change / amount_spent) * 100
                
            self.logger.debug(f"Updated position for {token_address}: {self.active_positions[token_address]}")
            
        except Exception as e:
            self.logger.error(f"Error updating position balances for {token_address}: {str(e)}")
    
    async def _get_token_price(self, token_address: str) -> float:
        """
        Get the current price of a token in USDC
        
        Args:
            token_address: Token address to get price for
            
        Returns:
            float: Current token price in USDC
        """
        try:
            # Try to get price from blockchain client
            current_price = await self.blockchain_client.get_token_price(token_address, "usdc")
            if current_price is not None and current_price > 0:
                return current_price
                
            # If blockchain client doesn't have price, try DexScreener API
            if self.dex_adapter:
                dex_price = await self.dex_adapter.get_token_price(token_address)
                if dex_price is not None and dex_price > 0:
                    return dex_price
            
            self.logger.warning(f"Could not find price for token {token_address}")
            return 0
            
        except Exception as e:
            self.logger.error(f"Error getting token price for {token_address}: {str(e)}")
            return 0 