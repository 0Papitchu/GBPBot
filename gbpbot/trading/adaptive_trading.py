from typing import Dict, List, Optional
from datetime import datetime
from loguru import logger
import asyncio
from dataclasses import dataclass
from ..core.stealth_mode import StealthMode
from ..core.transaction_obfuscation import TransactionObfuscator, TransactionParams
from ..core.self_learning import SelfLearning, TradeResult

@dataclass
class TradePosition:
    """Active trade position"""
    token_address: str
    entry_price: float
    entry_time: datetime
    amount: float
    current_price: float
    peak_price: float
    current_profit: float
    stop_loss: float
    take_profit_levels: List[Dict]
    risk_level: str
    momentum_score: float
    sustainability_score: float

class AdaptiveTrading:
    def __init__(self, blockchain_client, market_trends, pump_monitor, 
                 whale_tracker, strategy_optimizer, db_connection):
        """
        Initialize adaptive trading module
        
        Args:
            blockchain_client: Blockchain client instance
            market_trends: Market trends analyzer instance
            pump_monitor: Pump monitoring instance
            whale_tracker: Whale tracking instance
            strategy_optimizer: Strategy optimization instance
            db_connection: Database connection
        """
        self.blockchain = blockchain_client
        self.market_trends = market_trends
        self.pump_monitor = pump_monitor
        self.whale_tracker = whale_tracker
        self.strategy_optimizer = strategy_optimizer
        
        # Initialize new components
        self.stealth_mode = StealthMode()
        self.tx_obfuscator = TransactionObfuscator()
        self.self_learning = SelfLearning(db_connection)
        
        # Store active positions
        self.active_positions: Dict[str, TradePosition] = {}
        
        # Configuration
        self.config = {
            "max_active_positions": 5,
            "max_position_size": 1.0,  # Max position size in AVAX
            "min_profit_threshold": 20,  # Minimum profit % to consider success
            "max_loss_threshold": -15,  # Maximum loss % before forced exit
            "momentum_threshold": 0.6,  # Minimum momentum score
            "sustainability_threshold": 0.5,  # Minimum sustainability score
            "risk_levels": {
                "low": {"max_position": 1.0, "stop_loss": -10},
                "medium": {"max_position": 0.7, "stop_loss": -15},
                "high": {"max_position": 0.4, "stop_loss": -20}
            }
        }
    
    async def start(self):
        """Start adaptive trading"""
        logger.info("🚀 Starting adaptive trading system")
        
        # Start monitoring systems
        await asyncio.gather(
            self.market_trends.analyze_historical_trends(),
            self.pump_monitor.start_monitoring(),
            self.whale_tracker.start_monitoring(),
            self._manage_positions()
        )
    
    async def evaluate_trade_opportunity(self, token_address: str) -> Optional[Dict]:
        """
        Evaluate a potential trade opportunity
        
        Args:
            token_address: Token address to evaluate
            
        Returns:
            Trade parameters if opportunity is valid, None otherwise
        """
        try:
            # Check if we can take new positions
            if len(self.active_positions) >= self.config["max_active_positions"]:
                logger.warning("Maximum active positions reached")
                return None
            
            # Get market analysis
            market_conditions = await self.market_trends.analyze_historical_trends()
            
            # Get pump metrics
            pump_metrics = await self.pump_monitor.get_pump_metrics(token_address)
            
            if not pump_metrics:
                logger.warning(f"No pump metrics available for {token_address}")
                return None
            
            # Get whale sentiment
            whale_sentiment = await self.whale_tracker.get_whale_sentiment(token_address)
            
            # Get optimal parameters
            strategy_params = await self.strategy_optimizer.get_optimal_parameters(token_address)
            
            # Use self-learning to predict entry
            should_enter, confidence = await self.self_learning.predict_entry({
                "market_conditions": market_conditions,
                "pump_metrics": pump_metrics,
                "whale_sentiment": whale_sentiment,
                "strategy_params": strategy_params
            })
            
            if not should_enter or confidence < 0.7:
                logger.info(f"Self-learning model suggests skipping trade (confidence: {confidence:.2f})")
                return None
            
            # Calculate entry score
            entry_score = self._calculate_entry_score(
                pump_metrics,
                whale_sentiment,
                market_conditions
            )
            
            if entry_score < self.config["momentum_threshold"]:
                logger.info(f"Entry score too low for {token_address}: {entry_score:.2f}")
                return None
            
            # Determine risk level
            risk_level = self._determine_risk_level(
                pump_metrics,
                whale_sentiment,
                market_conditions
            )
            
            # Calculate position size
            position_size = self._calculate_position_size(
                risk_level,
                strategy_params,
                market_conditions
            )
            
            # Generate trade parameters
            trade_params = {
                "token_address": token_address,
                "position_size": position_size,
                "entry_price": pump_metrics["current_price"],
                "stop_loss": self.config["risk_levels"][risk_level]["stop_loss"],
                "take_profit_levels": strategy_params["exit"]["take_profit_tiers"],
                "risk_level": risk_level,
                "momentum_score": pump_metrics["momentum_score"],
                "sustainability_score": pump_metrics["sustainability_score"]
            }
            
            return trade_params
            
        except Exception as e:
            logger.error(f"Error evaluating trade opportunity: {str(e)}")
            return None
    
    async def execute_trade(self, trade_params: Dict) -> bool:
        """
        Execute a trade with given parameters
        
        Args:
            trade_params: Trade parameters
            
        Returns:
            bool: True if trade executed successfully
        """
        try:
            token_address = trade_params["token_address"]
            
            # Get active wallet for chain
            wallet = await self.stealth_mode.get_active_wallet("avax")
            if not wallet:
                logger.error("No available wallet for trading")
                return False
            
            # Prepare transaction parameters
            base_tx_params = TransactionParams(
                amount=trade_params["position_size"],
                slippage=0.01,  # 1% slippage
                gas_price=await self.blockchain.get_gas_price(),
                gas_limit=300000,  # Standard gas limit
                nonce=await self.blockchain.get_nonce(wallet.address),
                deadline=int(datetime.now().timestamp()) + 300  # 5 minutes
            )
            
            # Obfuscate transaction
            tx_params_list = self.tx_obfuscator.obfuscate_transaction(base_tx_params)
            
            # Execute transactions
            success = True
            for tx_params in tx_params_list:
                # Add random delay
                await self.stealth_mode.add_transaction_delay()
                
                # Execute buy order
                tx_hash = await self._execute_buy_order(
                    token_address,
                    tx_params.amount,
                    trade_params["entry_price"],
                    wallet,
                    tx_params
                )
                
                if not tx_hash:
                    success = False
                    break
                
                # Update wallet stats
                self.stealth_mode.update_wallet_stats(wallet.address)
            
            if not success:
                logger.error(f"Failed to execute buy order for {token_address}")
                return False
            
            # Create trade position
            position = TradePosition(
                token_address=token_address,
                entry_price=trade_params["entry_price"],
                entry_time=datetime.now(),
                amount=trade_params["position_size"],
                current_price=trade_params["entry_price"],
                peak_price=trade_params["entry_price"],
                current_profit=0,
                stop_loss=trade_params["stop_loss"],
                take_profit_levels=trade_params["take_profit_levels"],
                risk_level=trade_params["risk_level"],
                momentum_score=trade_params["momentum_score"],
                sustainability_score=trade_params["sustainability_score"]
            )
            
            # Add to active positions
            self.active_positions[token_address] = position
            
            logger.success(f"✅ Trade executed for {token_address}")
            return True
            
        except Exception as e:
            logger.error(f"Error executing trade: {str(e)}")
            return False
    
    async def _manage_positions(self):
        """Manage active trading positions"""
        while True:
            try:
                for token_address, position in list(self.active_positions.items()):
                    # Update position metrics
                    await self._update_position_metrics(position)
                    
                    # Check exit conditions
                    should_exit = await self._should_exit_position(position)
                    
                    if should_exit:
                        # Execute exit
                        if await self._execute_exit(position):
                            # Record trade result
                            await self._record_trade_result(position)
                            del self.active_positions[token_address]
                    
                # Wait before next update
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Error managing positions: {str(e)}")
                await asyncio.sleep(5)
    
    async def _update_position_metrics(self, position: TradePosition):
        """Update metrics for a position"""
        try:
            # Get current price
            current_price = await self._get_current_price(position.token_address)
            
            if not current_price:
                return
            
            # Update position data
            position.current_price = current_price
            position.peak_price = max(current_price, position.peak_price)
            position.current_profit = ((current_price / position.entry_price) - 1) * 100
            
            # Update momentum and sustainability scores
            pump_metrics = await self.pump_monitor.get_pump_metrics(position.token_address)
            if pump_metrics:
                position.momentum_score = pump_metrics["momentum_score"]
                position.sustainability_score = pump_metrics["sustainability_score"]
            
        except Exception as e:
            logger.error(f"Error updating position metrics: {str(e)}")
    
    async def _should_exit_position(self, position: TradePosition) -> bool:
        """
        Determine if we should exit a position
        
        Args:
            position: Trade position to check
            
        Returns:
            bool: True if should exit
        """
        try:
            # Use self-learning to predict exit
            should_exit, confidence = await self.self_learning.predict_exit({
                "current_profit": position.current_profit,
                "peak_profit": ((position.peak_price / position.entry_price) - 1) * 100,
                "momentum_score": position.momentum_score,
                "sustainability_score": position.sustainability_score
            })
            
            if should_exit and confidence > 0.8:
                logger.info(f"Self-learning model suggests exit (confidence: {confidence:.2f})")
                return True
            
            # Check stop loss
            if position.current_profit <= position.stop_loss:
                logger.warning(f"Stop loss triggered for {position.token_address}")
                return True
            
            # Check take profit levels
            for level in position.take_profit_levels:
                if position.current_profit >= (level["multiplier"] - 1) * 100:
                    logger.info(f"Take profit level reached for {position.token_address}")
                    return True
            
            # Check momentum loss
            if position.momentum_score < self.config["momentum_threshold"]:
                logger.info(f"Momentum lost for {position.token_address}")
                return True
            
            # Check sustainability
            if position.sustainability_score < self.config["sustainability_threshold"]:
                logger.info(f"Sustainability dropped for {position.token_address}")
                return True
            
            # Check whale sentiment
            whale_sentiment = await self.whale_tracker.get_whale_sentiment(position.token_address)
            if whale_sentiment["sentiment"] == "bearish" and whale_sentiment["confidence"] > 0.7:
                logger.warning(f"Bearish whale sentiment for {position.token_address}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking exit conditions: {str(e)}")
            return False
    
    async def _execute_exit(self, position: TradePosition) -> bool:
        """Execute position exit"""
        try:
            # Get active wallet
            wallet = await self.stealth_mode.get_active_wallet("avax")
            if not wallet:
                logger.error("No available wallet for exit")
                return False
            
            # Prepare transaction parameters
            base_tx_params = TransactionParams(
                amount=position.amount,
                slippage=0.02,  # 2% slippage for exit
                gas_price=await self.blockchain.get_gas_price(),
                gas_limit=300000,
                nonce=await self.blockchain.get_nonce(wallet.address),
                deadline=int(datetime.now().timestamp()) + 300
            )
            
            # Obfuscate transaction
            tx_params_list = self.tx_obfuscator.obfuscate_transaction(base_tx_params)
            
            # Execute transactions
            success = True
            for tx_params in tx_params_list:
                # Add random delay
                await self.stealth_mode.add_transaction_delay()
                
                # Execute sell order
                tx_hash = await self._execute_sell_order(
                    position.token_address,
                    tx_params.amount,
                    wallet,
                    tx_params
                )
                
                if not tx_hash:
                    success = False
                    break
                
                # Update wallet stats
                self.stealth_mode.update_wallet_stats(wallet.address)
            
            return success
            
        except Exception as e:
            logger.error(f"Error executing exit: {str(e)}")
            return False
    
    async def _record_trade_result(self, position: TradePosition):
        """Record trade result for self-learning"""
        try:
            trade_result = TradeResult(
                token_address=position.token_address,
                entry_time=position.entry_time,
                exit_time=datetime.now(),
                entry_price=position.entry_price,
                exit_price=position.current_price,
                amount=position.amount,
                profit_loss=position.current_profit,
                strategy_params={
                    "stop_loss": position.stop_loss,
                    "take_profit_levels": position.take_profit_levels,
                    "risk_level": position.risk_level
                },
                market_conditions=await self.market_trends.analyze_historical_trends(),
                transaction_params={}  # Add relevant transaction parameters
            )
            
            await self.self_learning.record_trade(trade_result)
            
        except Exception as e:
            logger.error(f"Error recording trade result: {str(e)}")
    
    async def _execute_buy_order(self, token_address: str, amount: float, price: float,
                               wallet: Dict, tx_params: TransactionParams) -> Optional[str]:
        """Execute a buy order"""
        # TODO: Implement buy order execution
        return None
    
    async def _execute_sell_order(self, token_address: str, amount: float,
                                wallet: Dict, tx_params: TransactionParams) -> Optional[str]:
        """Execute a sell order"""
        # TODO: Implement sell order execution
        return None
    
    async def _get_current_price(self, token_address: str) -> Optional[float]:
        """Get current token price"""
        # TODO: Implement price retrieval
        return None
    
    def _calculate_entry_score(self, pump_metrics: Dict, whale_sentiment: Dict,
                             market_conditions: Dict) -> float:
        """Calculate entry score for a trade opportunity"""
        try:
            # Weight different factors
            weights = {
                "momentum": 0.3,
                "sustainability": 0.2,
                "whale_sentiment": 0.3,
                "market_regime": 0.2
            }
            
            # Calculate individual scores
            momentum_score = pump_metrics["momentum_score"]
            sustainability_score = pump_metrics["sustainability_score"]
            
            whale_score = 0.5  # Neutral default
            if whale_sentiment["sentiment"] == "bullish":
                whale_score = 0.5 + (whale_sentiment["confidence"] * 0.5)
            elif whale_sentiment["sentiment"] == "bearish":
                whale_score = 0.5 - (whale_sentiment["confidence"] * 0.5)
            
            market_score = 0.5  # Neutral default
            if market_conditions["regime"] == "bull_market":
                market_score = 0.8
            elif market_conditions["regime"] == "bear_market":
                market_score = 0.2
            
            # Calculate weighted score
            entry_score = (
                weights["momentum"] * momentum_score +
                weights["sustainability"] * sustainability_score +
                weights["whale_sentiment"] * whale_score +
                weights["market_regime"] * market_score
            )
            
            return max(0, min(1, entry_score))
            
        except Exception as e:
            logger.error(f"Error calculating entry score: {str(e)}")
            return 0
    
    def _determine_risk_level(self, pump_metrics: Dict, whale_sentiment: Dict,
                            market_conditions: Dict) -> str:
        """Determine risk level for a trade"""
        try:
            # Calculate risk factors
            risk_factors = {
                "momentum": 1 - pump_metrics["momentum_score"],
                "sustainability": 1 - pump_metrics["sustainability_score"],
                "whale_risk": 0.5
            }
            
            if whale_sentiment["sentiment"] == "bearish":
                risk_factors["whale_risk"] = 0.8
            elif whale_sentiment["sentiment"] == "bullish":
                risk_factors["whale_risk"] = 0.2
            
            # Add market regime factor
            if market_conditions["regime"] == "bear_market":
                risk_factors["market"] = 0.8
            elif market_conditions["regime"] == "bull_market":
                risk_factors["market"] = 0.2
            else:
                risk_factors["market"] = 0.5
            
            # Calculate average risk
            avg_risk = sum(risk_factors.values()) / len(risk_factors)
            
            # Determine risk level
            if avg_risk < 0.3:
                return "low"
            elif avg_risk < 0.6:
                return "medium"
            else:
                return "high"
            
        except Exception as e:
            logger.error(f"Error determining risk level: {str(e)}")
            return "high"  # Conservative default
    
    def _calculate_position_size(self, risk_level: str, strategy_params: Dict,
                               market_conditions: Dict) -> float:
        """Calculate position size based on risk level and market conditions"""
        try:
            # Get base position size from risk level
            base_size = self.config["risk_levels"][risk_level]["max_position"]
            
            # Adjust based on market conditions
            if market_conditions["regime"] == "bull_market":
                base_size *= 1.2
            elif market_conditions["regime"] == "bear_market":
                base_size *= 0.8
            
            # Apply strategy-specific adjustments
            max_position = strategy_params["risk"]["max_position_size"]
            base_size = min(base_size, max_position)
            
            # Ensure within global limits
            return min(base_size, self.config["max_position_size"])
            
        except Exception as e:
            logger.error(f"Error calculating position size: {str(e)}")
            return 0.1  # Conservative default 