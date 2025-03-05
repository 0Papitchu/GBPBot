from typing import Dict, List, Optional, Tuple
import numpy as np
from datetime import datetime, timedelta
from loguru import logger
from dataclasses import dataclass
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import joblib
import json
from pathlib import Path

@dataclass
class OptimizationResult:
    """Results of strategy optimization"""
    strategy_params: Dict
    expected_performance: Dict
    confidence_score: float
    market_conditions: Dict
    timestamp: datetime

class StrategyOptimizer:
    def __init__(self, db_connection, market_trends, performance_tracker):
        """
        Initialize strategy optimizer
        
        Args:
            db_connection: Database connection for historical data
            market_trends: Market trends analyzer instance
            performance_tracker: Performance tracking instance
        """
        self.db = db_connection
        self.market_trends = market_trends
        self.performance_tracker = performance_tracker
        
        # Initialize ML models
        self.profit_model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.risk_model = RandomForestRegressor(n_estimators=100, random_state=42)
        
        # Data preprocessing
        self.scaler = StandardScaler()
        
        # Store optimization results
        self.optimization_history: List[OptimizationResult] = []
        
        # Configuration
        self.config = {
            "min_data_points": 100,  # Minimum trades for optimization
            "optimization_interval": 24 * 3600,  # Optimize every 24 hours
            "performance_weight": 0.7,  # Weight for performance vs risk in optimization
            "min_confidence_score": 0.6,  # Minimum confidence score to apply changes
            "max_param_change": 0.3,  # Maximum parameter change in one optimization
            "market_regime_thresholds": {
                "bull_market": 0.7,  # Success rate threshold for bull market
                "bear_market": 0.3   # Success rate threshold for bear market
            }
        }
        
        # Load existing models if available
        self._load_models()
    
    async def optimize_strategies(self) -> Optional[OptimizationResult]:
        """
        Optimize trading strategies based on historical performance
        
        Returns:
            OptimizationResult if optimization successful, None otherwise
        """
        try:
            logger.info("🔄 Starting strategy optimization")
            
            # Get historical trade data
            trade_data = await self._get_historical_trades()
            
            if len(trade_data) < self.config["min_data_points"]:
                logger.warning(f"Insufficient data for optimization: {len(trade_data)} trades")
                return None
            
            # Analyze market conditions
            market_conditions = await self._analyze_market_conditions()
            
            # Prepare features and targets
            features, profit_targets, risk_targets = self._prepare_training_data(trade_data)
            
            if len(features) == 0:
                logger.warning("No valid features for optimization")
                return None
            
            # Train models
            self._train_models(features, profit_targets, risk_targets)
            
            # Generate and evaluate strategies
            best_strategy = await self._find_optimal_strategy(market_conditions)
            
            if not best_strategy:
                logger.warning("Could not find optimal strategy")
                return None
            
            # Save optimization result
            result = OptimizationResult(
                strategy_params=best_strategy["params"],
                expected_performance=best_strategy["performance"],
                confidence_score=best_strategy["confidence"],
                market_conditions=market_conditions,
                timestamp=datetime.now()
            )
            
            self.optimization_history.append(result)
            
            # Save models
            self._save_models()
            
            logger.success("✅ Strategy optimization completed")
            return result
            
        except Exception as e:
            logger.error(f"Error in strategy optimization: {str(e)}")
            return None
    
    async def get_optimal_parameters(self, token_address: str) -> Dict:
        """
        Get optimal parameters for a specific token
        
        Args:
            token_address: Token address to optimize for
            
        Returns:
            Dictionary of optimal parameters
        """
        try:
            # Get token-specific data
            token_data = await self._get_token_data(token_address)
            
            if not token_data:
                # Use general optimization if no token-specific data
                if self.optimization_history:
                    return self.optimization_history[-1].strategy_params
                return self._get_default_parameters()
            
            # Get current market conditions
            market_conditions = await self._analyze_market_conditions()
            
            # Prepare token features
            features = self._prepare_token_features(token_data, market_conditions)
            
            # Predict performance for different parameter sets
            best_params = await self._optimize_token_parameters(features)
            
            return best_params
            
        except Exception as e:
            logger.error(f"Error getting optimal parameters: {str(e)}")
            return self._get_default_parameters()
    
    def _get_default_parameters(self) -> Dict:
        """Get default strategy parameters"""
        return {
            "entry": {
                "min_liquidity": 10,  # Minimum liquidity in AVAX
                "max_price_impact": 2.0,  # Maximum price impact %
                "min_holder_count": 100  # Minimum number of holders
            },
            "exit": {
                "take_profit_tiers": [
                    {"multiplier": 2.0, "percentage": 30},
                    {"multiplier": 5.0, "percentage": 50},
                    {"multiplier": 10.0, "percentage": 20}
                ],
                "stop_loss": {
                    "initial": -15,
                    "trailing": 5,
                    "profit_threshold": 50,
                    "adjusted_stop_loss": 20
                }
            },
            "risk": {
                "max_position_size": 0.5,  # Maximum position size in AVAX
                "max_slippage": 1.0,  # Maximum allowed slippage %
                "min_volume": 5  # Minimum 24h volume in AVAX
            }
        }
    
    async def _get_historical_trades(self) -> List[Dict]:
        """Get historical trade data from database"""
        # TODO: Implement database query
        return []
    
    async def _analyze_market_conditions(self) -> Dict:
        """Analyze current market conditions"""
        try:
            # Get market trends
            trends = await self.market_trends.analyze_historical_trends()
            
            # Get recent performance
            performance = await self.performance_tracker.get_recent_performance()
            
            # Determine market regime
            success_rate = performance.get("success_rate", 0.5)
            
            if success_rate > self.config["market_regime_thresholds"]["bull_market"]:
                regime = "bull_market"
            elif success_rate < self.config["market_regime_thresholds"]["bear_market"]:
                regime = "bear_market"
            else:
                regime = "neutral_market"
            
            return {
                "regime": regime,
                "volatility": trends.get("volatility", "medium"),
                "average_pump_magnitude": trends.get("avg_pump_magnitude", 0),
                "average_dump_magnitude": trends.get("avg_dump_magnitude", 0),
                "whale_activity": trends.get("whale_activity", "normal"),
                "success_rate": success_rate
            }
            
        except Exception as e:
            logger.error(f"Error analyzing market conditions: {str(e)}")
            return {
                "regime": "neutral_market",
                "volatility": "medium",
                "average_pump_magnitude": 0,
                "average_dump_magnitude": 0,
                "whale_activity": "normal",
                "success_rate": 0.5
            }
    
    def _prepare_training_data(self, trade_data: List[Dict]) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Prepare training data for ML models
        
        Args:
            trade_data: List of historical trades
            
        Returns:
            Tuple of (features, profit_targets, risk_targets)
        """
        try:
            # Convert to DataFrame
            df = pd.DataFrame(trade_data)
            
            # Extract features
            features = np.array([
                df["initial_liquidity"].values,
                df["holder_count"].values,
                df["volume_24h"].values,
                df["price_impact"].values,
                df["whale_holdings_percent"].values,
                df["market_cap"].values
            ]).T
            
            # Scale features
            features = self.scaler.fit_transform(features)
            
            # Prepare targets
            profit_targets = df["profit_percent"].values
            risk_targets = df["max_drawdown"].values
            
            return features, profit_targets, risk_targets
            
        except Exception as e:
            logger.error(f"Error preparing training data: {str(e)}")
            return np.array([]), np.array([]), np.array([])
    
    def _train_models(self, features: np.ndarray, profit_targets: np.ndarray, risk_targets: np.ndarray):
        """Train ML models for prediction"""
        try:
            # Train profit prediction model
            self.profit_model.fit(features, profit_targets)
            
            # Train risk prediction model
            self.risk_model.fit(features, risk_targets)
            
        except Exception as e:
            logger.error(f"Error training models: {str(e)}")
    
    async def _find_optimal_strategy(self, market_conditions: Dict) -> Optional[Dict]:
        """
        Find optimal strategy parameters
        
        Args:
            market_conditions: Current market conditions
            
        Returns:
            Dictionary with optimal strategy parameters
        """
        try:
            # Generate parameter combinations
            param_sets = self._generate_parameter_sets(market_conditions)
            
            best_score = float("-inf")
            best_strategy = None
            
            for params in param_sets:
                # Prepare features for prediction
                features = self._prepare_strategy_features(params, market_conditions)
                
                # Predict performance
                predicted_profit = self.profit_model.predict([features])[0]
                predicted_risk = self.risk_model.predict([features])[0]
                
                # Calculate score
                score = self._calculate_strategy_score(
                    predicted_profit,
                    predicted_risk,
                    market_conditions
                )
                
                if score > best_score:
                    best_score = score
                    best_strategy = {
                        "params": params,
                        "performance": {
                            "expected_profit": predicted_profit,
                            "expected_risk": predicted_risk
                        },
                        "confidence": self._calculate_confidence_score(
                            predicted_profit,
                            predicted_risk,
                            market_conditions
                        )
                    }
            
            return best_strategy
            
        except Exception as e:
            logger.error(f"Error finding optimal strategy: {str(e)}")
            return None
    
    def _generate_parameter_sets(self, market_conditions: Dict) -> List[Dict]:
        """Generate different parameter combinations to evaluate"""
        param_sets = []
        
        # Base parameters
        base_params = self._get_default_parameters()
        
        # Generate variations based on market conditions
        if market_conditions["regime"] == "bull_market":
            # More aggressive parameters for bull market
            param_sets.append(self._adjust_parameters(base_params, {
                "entry.min_liquidity": 0.8,
                "exit.take_profit_tiers": [
                    {"multiplier": 3.0, "percentage": 30},
                    {"multiplier": 7.0, "percentage": 40},
                    {"multiplier": 15.0, "percentage": 30}
                ],
                "risk.max_position_size": 1.2
            }))
        elif market_conditions["regime"] == "bear_market":
            # More conservative parameters for bear market
            param_sets.append(self._adjust_parameters(base_params, {
                "entry.min_liquidity": 1.2,
                "exit.take_profit_tiers": [
                    {"multiplier": 1.5, "percentage": 40},
                    {"multiplier": 3.0, "percentage": 40},
                    {"multiplier": 5.0, "percentage": 20}
                ],
                "risk.max_position_size": 0.8
            }))
        
        # Add more variations based on volatility
        if market_conditions["volatility"] == "high":
            param_sets.append(self._adjust_parameters(base_params, {
                "exit.stop_loss.trailing": 8,
                "risk.max_slippage": 1.5
            }))
        
        return param_sets
    
    def _adjust_parameters(self, base_params: Dict, adjustments: Dict) -> Dict:
        """
        Adjust parameters with given changes
        
        Args:
            base_params: Base parameters
            adjustments: Parameter adjustments
            
        Returns:
            Adjusted parameters
        """
        import copy
        params = copy.deepcopy(base_params)
        
        for path, value in adjustments.items():
            keys = path.split(".")
            target = params
            for key in keys[:-1]:
                target = target[key]
            target[keys[-1]] = value
        
        return params
    
    def _prepare_strategy_features(self, params: Dict, market_conditions: Dict) -> np.ndarray:
        """Prepare features for strategy evaluation"""
        features = [
            params["entry"]["min_liquidity"],
            params["entry"]["max_price_impact"],
            params["risk"]["max_position_size"],
            params["risk"]["max_slippage"],
            float(market_conditions["success_rate"]),
            float(market_conditions["average_pump_magnitude"])
        ]
        
        return self.scaler.transform([features])[0]
    
    def _calculate_strategy_score(self, predicted_profit: float, predicted_risk: float,
                                market_conditions: Dict) -> float:
        """Calculate overall strategy score"""
        # Weight profit and risk based on market conditions
        if market_conditions["regime"] == "bull_market":
            profit_weight = 0.8
            risk_weight = 0.2
        elif market_conditions["regime"] == "bear_market":
            profit_weight = 0.4
            risk_weight = 0.6
        else:
            profit_weight = 0.6
            risk_weight = 0.4
        
        # Normalize predictions
        norm_profit = max(0, min(1, predicted_profit / 100))
        norm_risk = 1 - max(0, min(1, predicted_risk / 50))
        
        return (profit_weight * norm_profit + risk_weight * norm_risk)
    
    def _calculate_confidence_score(self, predicted_profit: float, predicted_risk: float,
                                  market_conditions: Dict) -> float:
        """Calculate confidence score for predictions"""
        try:
            # Base confidence on model uncertainty
            profit_std = np.std(self.profit_model.predict(
                self.scaler.transform([[predicted_profit] * 6])
            ))
            risk_std = np.std(self.risk_model.predict(
                self.scaler.transform([[predicted_risk] * 6])
            ))
            
            # Normalize uncertainty scores
            profit_confidence = 1 / (1 + profit_std)
            risk_confidence = 1 / (1 + risk_std)
            
            # Adjust based on market conditions
            market_factor = {
                "bull_market": 1.2,
                "bear_market": 0.8,
                "neutral_market": 1.0
            }[market_conditions["regime"]]
            
            confidence = (0.6 * profit_confidence + 0.4 * risk_confidence) * market_factor
            
            return max(0, min(1, confidence))
            
        except Exception as e:
            logger.error(f"Error calculating confidence score: {str(e)}")
            return 0.5
    
    async def _get_token_data(self, token_address: str) -> Optional[Dict]:
        """Get historical data for specific token"""
        # TODO: Implement token data retrieval
        return None
    
    def _prepare_token_features(self, token_data: Dict, market_conditions: Dict) -> np.ndarray:
        """Prepare features for token-specific optimization"""
        # TODO: Implement token feature preparation
        return np.array([])
    
    async def _optimize_token_parameters(self, features: np.ndarray) -> Dict:
        """Optimize parameters for specific token"""
        # TODO: Implement token-specific optimization
        return self._get_default_parameters()
    
    def _save_models(self):
        """Save trained models to disk"""
        try:
            model_dir = Path("models")
            model_dir.mkdir(exist_ok=True)
            
            joblib.dump(self.profit_model, model_dir / "profit_model.joblib")
            joblib.dump(self.risk_model, model_dir / "risk_model.joblib")
            joblib.dump(self.scaler, model_dir / "scaler.joblib")
            
        except Exception as e:
            logger.error(f"Error saving models: {str(e)}")
    
    def _load_models(self):
        """Load trained models from disk"""
        try:
            model_dir = Path("models")
            
            if (model_dir / "profit_model.joblib").exists():
                self.profit_model = joblib.load(model_dir / "profit_model.joblib")
                self.risk_model = joblib.load(model_dir / "risk_model.joblib")
                self.scaler = joblib.load(model_dir / "scaler.joblib")
                
        except Exception as e:
            logger.error(f"Error loading models: {str(e)}") 