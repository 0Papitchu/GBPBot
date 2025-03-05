from typing import Dict, List, Optional
import numpy as np
from datetime import datetime, timedelta
from loguru import logger
from dataclasses import dataclass
import asyncio
from collections import deque

@dataclass
class PumpMetrics:
    """Metrics for a token pump"""
    token_address: str
    start_time: datetime
    start_price: float
    current_price: float
    peak_price: float
    volume_profile: List[float]
    whale_activity: List[Dict]
    liquidity_changes: List[float]
    momentum_score: float
    sustainability_score: float

class PumpMonitor:
    def __init__(self, price_feed, whale_tracker, market_trends):
        """
        Initialize pump monitor
        
        Args:
            price_feed: Price feed instance
            whale_tracker: Whale tracker instance
            market_trends: Market trends analyzer instance
        """
        self.price_feed = price_feed
        self.whale_tracker = whale_tracker
        self.market_trends = market_trends
        
        # Store active pumps
        self.active_pumps: Dict[str, PumpMetrics] = {}
        
        # Historical pump data for pattern matching
        self.pump_history = deque(maxlen=1000)
        
        # Configurable thresholds
        self.config = {
            "min_pump_threshold": 20,  # Minimum % increase to consider as pump
            "volume_window": 5,        # Minutes to analyze volume
            "momentum_threshold": 0.7,  # Minimum momentum score
            "sustainability_threshold": 0.6,  # Minimum sustainability score
            "whale_impact_threshold": 0.3,  # Maximum whale selling impact
            "min_liquidity_ratio": 0.1  # Minimum liquidity to market cap ratio
        }
    
    async def start_monitoring(self):
        """Start monitoring for pumps"""
        logger.info("🔍 Starting pump monitoring")
        
        while True:
            try:
                # Update active pumps
                await self._update_active_pumps()
                
                # Detect new pumps
                await self._detect_new_pumps()
                
                # Clean up finished pumps
                self._cleanup_inactive_pumps()
                
                # Wait before next iteration
                await asyncio.sleep(1)  # Check every second
                
            except Exception as e:
                logger.error(f"Error in pump monitoring: {str(e)}")
                await asyncio.sleep(5)
    
    async def _update_active_pumps(self):
        """Update metrics for active pumps"""
        for token_address, pump_data in list(self.active_pumps.items()):
            try:
                # Get current price and metrics
                current_price = await self.price_feed.get_token_price(token_address)
                
                if not current_price:
                    continue
                
                # Update volume profile
                volume_data = await self._get_recent_volume(token_address)
                
                # Get whale activity
                whale_activity = await self.whale_tracker.get_recent_activity(token_address)
                
                # Update liquidity changes
                liquidity_changes = await self._get_liquidity_changes(token_address)
                
                # Calculate momentum and sustainability scores
                momentum_score = self._calculate_momentum_score(
                    current_price, 
                    pump_data.start_price,
                    volume_data
                )
                
                sustainability_score = self._calculate_sustainability_score(
                    whale_activity,
                    liquidity_changes,
                    volume_data
                )
                
                # Update pump metrics
                self.active_pumps[token_address] = PumpMetrics(
                    token_address=token_address,
                    start_time=pump_data.start_time,
                    start_price=pump_data.start_price,
                    current_price=current_price,
                    peak_price=max(current_price, pump_data.peak_price),
                    volume_profile=volume_data,
                    whale_activity=whale_activity,
                    liquidity_changes=liquidity_changes,
                    momentum_score=momentum_score,
                    sustainability_score=sustainability_score
                )
                
                # Check for exit signals
                if self._should_exit(self.active_pumps[token_address]):
                    await self._signal_exit(token_address, "momentum_loss")
                
            except Exception as e:
                logger.error(f"Error updating pump {token_address}: {str(e)}")
    
    async def _detect_new_pumps(self):
        """Detect new token pumps"""
        try:
            # Get all tracked tokens
            tokens = await self.price_feed.get_tracked_tokens()
            
            for token_address in tokens:
                # Skip if already tracking
                if token_address in self.active_pumps:
                    continue
                
                # Get price data
                price_data = await self._get_recent_price_data(token_address)
                
                if not price_data:
                    continue
                
                # Calculate price change
                price_change = ((price_data[-1] / price_data[0]) - 1) * 100
                
                if price_change > self.config["min_pump_threshold"]:
                    # Verify pump validity
                    if await self._validate_pump(token_address, price_data):
                        # Initialize pump tracking
                        await self._initialize_pump_tracking(token_address, price_data[0])
                
        except Exception as e:
            logger.error(f"Error detecting new pumps: {str(e)}")
    
    async def _validate_pump(self, token_address: str, price_data: List[float]) -> bool:
        """
        Validate if a price increase is a legitimate pump
        
        Args:
            token_address: Token address
            price_data: Recent price data
            
        Returns:
            bool: True if pump is valid
        """
        try:
            # Check volume increase
            volume_data = await self._get_recent_volume(token_address)
            volume_increase = (volume_data[-1] / volume_data[0]) - 1
            
            if volume_increase < 1.0:  # Require 100% volume increase
                return False
            
            # Check liquidity
            liquidity = await self._get_current_liquidity(token_address)
            market_cap = await self._get_market_cap(token_address)
            
            if market_cap > 0:
                liquidity_ratio = liquidity / market_cap
                if liquidity_ratio < self.config["min_liquidity_ratio"]:
                    return False
            
            # Check whale manipulation
            whale_activity = await self.whale_tracker.get_recent_activity(token_address)
            whale_buy_pressure = sum(tx["amount"] for tx in whale_activity if tx["type"] == "buy")
            total_volume = sum(volume_data)
            
            if total_volume > 0:
                whale_dominance = whale_buy_pressure / total_volume
                if whale_dominance > self.config["whale_impact_threshold"]:
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating pump for {token_address}: {str(e)}")
            return False
    
    async def _initialize_pump_tracking(self, token_address: str, start_price: float):
        """Initialize tracking for a new pump"""
        try:
            # Get initial metrics
            volume_data = await self._get_recent_volume(token_address)
            whale_activity = await self.whale_tracker.get_recent_activity(token_address)
            liquidity_changes = await self._get_liquidity_changes(token_address)
            
            # Calculate initial scores
            momentum_score = self._calculate_momentum_score(
                start_price,
                start_price,
                volume_data
            )
            
            sustainability_score = self._calculate_sustainability_score(
                whale_activity,
                liquidity_changes,
                volume_data
            )
            
            # Create pump metrics
            self.active_pumps[token_address] = PumpMetrics(
                token_address=token_address,
                start_time=datetime.now(),
                start_price=start_price,
                current_price=start_price,
                peak_price=start_price,
                volume_profile=volume_data,
                whale_activity=whale_activity,
                liquidity_changes=liquidity_changes,
                momentum_score=momentum_score,
                sustainability_score=sustainability_score
            )
            
            logger.info(f"🚀 Started tracking pump for {token_address}")
            
        except Exception as e:
            logger.error(f"Error initializing pump tracking for {token_address}: {str(e)}")
    
    def _calculate_momentum_score(self, current_price: float, start_price: float, volume_data: List[float]) -> float:
        """
        Calculate momentum score based on price and volume trends
        
        Args:
            current_price: Current token price
            start_price: Starting price
            volume_data: Recent volume data
            
        Returns:
            float: Momentum score between 0 and 1
        """
        try:
            # Price momentum
            price_momentum = (current_price / start_price) - 1
            
            # Volume momentum
            volume_momentum = 0
            if len(volume_data) > 1:
                volume_changes = np.diff(volume_data) / volume_data[:-1]
                volume_momentum = np.mean(volume_changes)
            
            # Combine scores
            momentum_score = (0.7 * price_momentum + 0.3 * volume_momentum)
            
            # Normalize between 0 and 1
            return max(0, min(1, momentum_score))
            
        except Exception as e:
            logger.error(f"Error calculating momentum score: {str(e)}")
            return 0
    
    def _calculate_sustainability_score(self, whale_activity: List[Dict], 
                                     liquidity_changes: List[float],
                                     volume_data: List[float]) -> float:
        """
        Calculate sustainability score based on various metrics
        
        Args:
            whale_activity: Recent whale transactions
            liquidity_changes: Recent liquidity changes
            volume_data: Recent volume data
            
        Returns:
            float: Sustainability score between 0 and 1
        """
        try:
            # Whale selling pressure
            whale_sells = sum(tx["amount"] for tx in whale_activity if tx["type"] == "sell")
            whale_buys = sum(tx["amount"] for tx in whale_activity if tx["type"] == "buy")
            whale_pressure = 1.0
            if whale_sells + whale_buys > 0:
                whale_pressure = whale_buys / (whale_sells + whale_buys)
            
            # Liquidity stability
            liquidity_stability = 1.0
            if liquidity_changes:
                liquidity_changes_pct = np.diff(liquidity_changes) / liquidity_changes[:-1]
                liquidity_stability = 1 - min(1, np.std(liquidity_changes_pct))
            
            # Volume stability
            volume_stability = 1.0
            if len(volume_data) > 1:
                volume_changes_pct = np.diff(volume_data) / volume_data[:-1]
                volume_stability = 1 - min(1, np.std(volume_changes_pct))
            
            # Combine scores
            sustainability_score = (
                0.4 * whale_pressure +
                0.3 * liquidity_stability +
                0.3 * volume_stability
            )
            
            return max(0, min(1, sustainability_score))
            
        except Exception as e:
            logger.error(f"Error calculating sustainability score: {str(e)}")
            return 0
    
    def _should_exit(self, pump_data: PumpMetrics) -> bool:
        """
        Determine if we should exit a pump
        
        Args:
            pump_data: Current pump metrics
            
        Returns:
            bool: True if should exit
        """
        try:
            # Check momentum loss
            if pump_data.momentum_score < self.config["momentum_threshold"]:
                return True
            
            # Check sustainability
            if pump_data.sustainability_score < self.config["sustainability_threshold"]:
                return True
            
            # Check price retracement from peak
            price_retracement = (pump_data.peak_price - pump_data.current_price) / pump_data.peak_price
            if price_retracement > 0.2:  # Exit if price drops 20% from peak
                return True
            
            # Check volume decay
            volume_decay = (pump_data.volume_profile[-1] / max(pump_data.volume_profile)) - 1
            if volume_decay < -0.5:  # Exit if volume drops 50% from peak
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking exit conditions: {str(e)}")
            return True  # Exit on error to be safe
    
    async def _signal_exit(self, token_address: str, reason: str):
        """Signal that we should exit a position"""
        try:
            pump_data = self.active_pumps[token_address]
            
            # Calculate profit
            profit_pct = ((pump_data.current_price / pump_data.start_price) - 1) * 100
            
            logger.info(f"📉 Exit signal for {token_address}: {reason} (Profit: {profit_pct:.2f}%)")
            
            # Save pump data to history
            self.pump_history.append({
                "token_address": token_address,
                "start_time": pump_data.start_time,
                "end_time": datetime.now(),
                "profit_pct": profit_pct,
                "peak_profit_pct": ((pump_data.peak_price / pump_data.start_price) - 1) * 100,
                "duration_minutes": (datetime.now() - pump_data.start_time).total_seconds() / 60,
                "exit_reason": reason
            })
            
            # Remove from active pumps
            del self.active_pumps[token_address]
            
        except Exception as e:
            logger.error(f"Error signaling exit for {token_address}: {str(e)}")
    
    def _cleanup_inactive_pumps(self):
        """Remove pumps that have been inactive for too long"""
        current_time = datetime.now()
        
        for token_address, pump_data in list(self.active_pumps.items()):
            # Remove pumps older than 24 hours
            if (current_time - pump_data.start_time).total_seconds() > 24 * 3600:
                logger.info(f"🧹 Removing inactive pump for {token_address}")
                del self.active_pumps[token_address]
    
    async def _get_recent_price_data(self, token_address: str) -> List[float]:
        """Get recent price data for a token"""
        # TODO: Implement price data retrieval
        return []
    
    async def _get_recent_volume(self, token_address: str) -> List[float]:
        """Get recent volume data for a token"""
        # TODO: Implement volume data retrieval
        return []
    
    async def _get_liquidity_changes(self, token_address: str) -> List[float]:
        """Get recent liquidity changes for a token"""
        # TODO: Implement liquidity data retrieval
        return []
    
    async def _get_current_liquidity(self, token_address: str) -> float:
        """Get current liquidity for a token"""
        # TODO: Implement liquidity retrieval
        return 0.0
    
    async def _get_market_cap(self, token_address: str) -> float:
        """Get current market cap for a token"""
        # TODO: Implement market cap retrieval
        return 0.0 