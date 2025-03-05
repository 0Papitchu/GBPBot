from typing import Dict, List, Optional, Tuple
import numpy as np
from datetime import datetime, timedelta
from loguru import logger
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import joblib
from pathlib import Path
import json
from dataclasses import dataclass

@dataclass
class TradeResult:
    """Result of a completed trade"""
    token_address: str
    entry_time: datetime
    exit_time: datetime
    entry_price: float
    exit_price: float
    amount: float
    profit_loss: float
    strategy_params: Dict
    market_conditions: Dict
    transaction_params: Dict

class SelfLearning:
    def __init__(self, db_connection, model_path: str = "models"):
        """
        Initialize self-learning system
        
        Args:
            db_connection: Database connection for storing trade history
            model_path: Path to save/load ML models
        """
        self.db = db_connection
        self.model_path = Path(model_path)
        self.model_path.mkdir(exist_ok=True)
        
        # Initialize ML models
        self.entry_model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.exit_model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.profit_model = RandomForestRegressor(n_estimators=100, random_state=42)
        
        # Data preprocessing
        self.scaler = StandardScaler()
        
        # Performance tracking
        self.performance_history: List[TradeResult] = []
        self.strategy_performance: Dict[str, List[float]] = {}
        
        # Configuration
        self.config = {
            "min_trades_for_learning": 50,
            "training_interval": 24 * 3600,  # Train every 24 hours
            "success_threshold": 0.2,  # 20% profit for successful trade
            "max_loss_threshold": -0.15,  # 15% max loss
            "feature_importance_threshold": 0.1,  # Min feature importance
            "adaptation_rate": 0.1  # Rate of strategy parameter adjustment
        }
        
        # Load existing models
        self._load_models()
    
    async def record_trade(self, trade_result: TradeResult):
        """
        Record completed trade result
        
        Args:
            trade_result: Trade result data
        """
        try:
            # Store in memory
            self.performance_history.append(trade_result)
            
            # Update strategy performance
            strategy_key = self._get_strategy_key(trade_result.strategy_params)
            if strategy_key not in self.strategy_performance:
                self.strategy_performance[strategy_key] = []
            self.strategy_performance[strategy_key].append(trade_result.profit_loss)
            
            # Store in database
            await self._save_trade_to_db(trade_result)
            
            # Train models if enough data
            if len(self.performance_history) >= self.config["min_trades_for_learning"]:
                await self.train_models()
            
        except Exception as e:
            logger.error(f"Error recording trade: {str(e)}")
    
    async def train_models(self):
        """Train ML models on historical data"""
        try:
            logger.info("🧠 Training ML models")
            
            # Prepare training data
            features, entry_targets, exit_targets, profit_targets = await self._prepare_training_data()
            
            if len(features) < self.config["min_trades_for_learning"]:
                logger.warning("Insufficient data for training")
                return
            
            # Scale features
            scaled_features = self.scaler.fit_transform(features)
            
            # Train models
            self.entry_model.fit(scaled_features, entry_targets)
            self.exit_model.fit(scaled_features, exit_targets)
            self.profit_model.fit(scaled_features, profit_targets)
            
            # Save models
            self._save_models()
            
            # Analyze feature importance
            self._analyze_feature_importance()
            
            logger.success("✅ Model training completed")
            
        except Exception as e:
            logger.error(f"Error training models: {str(e)}")
    
    async def predict_entry(self, market_data: Dict) -> Tuple[bool, float]:
        """
        Predict whether to enter a trade
        
        Args:
            market_data: Current market data
            
        Returns:
            Tuple of (should_enter, confidence)
        """
        try:
            features = self._prepare_prediction_features(market_data)
            scaled_features = self.scaler.transform([features])
            
            # Get prediction and probability
            prediction = self.entry_model.predict(scaled_features)[0]
            confidence = max(self.entry_model.predict_proba(scaled_features)[0])
            
            return bool(prediction), confidence
            
        except Exception as e:
            logger.error(f"Error predicting entry: {str(e)}")
            return False, 0.0
    
    async def predict_exit(self, position_data: Dict) -> Tuple[bool, float]:
        """
        Predict whether to exit a trade
        
        Args:
            position_data: Current position data
            
        Returns:
            Tuple of (should_exit, confidence)
        """
        try:
            features = self._prepare_prediction_features(position_data)
            scaled_features = self.scaler.transform([features])
            
            # Get prediction and probability
            prediction = self.exit_model.predict(scaled_features)[0]
            confidence = max(self.exit_model.predict_proba(scaled_features)[0])
            
            return bool(prediction), confidence
            
        except Exception as e:
            logger.error(f"Error predicting exit: {str(e)}")
            return True, 1.0  # Conservative default
    
    async def optimize_strategy(self, current_params: Dict) -> Dict:
        """
        Optimize strategy parameters based on performance
        
        Args:
            current_params: Current strategy parameters
            
        Returns:
            Optimized parameters
        """
        try:
            if not self.strategy_performance:
                return current_params
            
            # Find best performing strategies
            best_strategies = self._get_best_strategies()
            
            if not best_strategies:
                return current_params
            
            # Calculate parameter adjustments
            optimized_params = self._calculate_parameter_adjustments(
                current_params,
                best_strategies
            )
            
            return optimized_params
            
        except Exception as e:
            logger.error(f"Error optimizing strategy: {str(e)}")
            return current_params
    
    def _get_strategy_key(self, strategy_params: Dict) -> str:
        """Generate unique key for strategy parameters"""
        return json.dumps(strategy_params, sort_keys=True)
    
    async def _prepare_training_data(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Prepare data for model training"""
        try:
            # Get historical trades
            trades = await self._get_historical_trades()
            
            if not trades:
                return np.array([]), np.array([]), np.array([]), np.array([])
            
            # Extract features and targets
            features = []
            entry_targets = []
            exit_targets = []
            profit_targets = []
            
            for trade in trades:
                # Extract features
                trade_features = self._extract_features(trade)
                features.append(trade_features)
                
                # Determine if entry was good
                entry_success = trade.profit_loss > self.config["success_threshold"]
                entry_targets.append(entry_success)
                
                # Determine if exit was good
                exit_timing = self._evaluate_exit_timing(trade)
                exit_targets.append(exit_timing)
                
                # Record profit/loss
                profit_targets.append(trade.profit_loss)
            
            return (
                np.array(features),
                np.array(entry_targets),
                np.array(exit_targets),
                np.array(profit_targets)
            )
            
        except Exception as e:
            logger.error(f"Error preparing training data: {str(e)}")
            return np.array([]), np.array([]), np.array([]), np.array([])
    
    def _extract_features(self, trade: TradeResult) -> List[float]:
        """Extract features from trade data"""
        features = []
        
        # Market condition features
        features.extend([
            trade.market_conditions.get("volatility", 0),
            trade.market_conditions.get("volume", 0),
            trade.market_conditions.get("trend", 0)
        ])
        
        # Strategy parameter features
        features.extend([
            trade.strategy_params.get("entry_threshold", 0),
            trade.strategy_params.get("exit_threshold", 0),
            trade.strategy_params.get("stop_loss", 0)
        ])
        
        # Transaction features
        features.extend([
            trade.transaction_params.get("slippage", 0),
            trade.transaction_params.get("gas_price", 0)
        ])
        
        return features
    
    def _evaluate_exit_timing(self, trade: TradeResult) -> bool:
        """Evaluate if exit timing was good"""
        # Consider exit good if:
        # 1. Profit was taken near peak
        # 2. Loss was minimized
        if trade.profit_loss > 0:
            return trade.profit_loss >= self.config["success_threshold"]
        else:
            return trade.profit_loss > self.config["max_loss_threshold"]
    
    def _get_best_strategies(self) -> List[Dict]:
        """Get best performing strategy configurations"""
        try:
            # Calculate average performance for each strategy
            avg_performance = {
                strategy: np.mean(profits)
                for strategy, profits in self.strategy_performance.items()
                if len(profits) >= 5  # Minimum trades for consideration
            }
            
            if not avg_performance:
                return []
            
            # Sort by performance
            sorted_strategies = sorted(
                avg_performance.items(),
                key=lambda x: x[1],
                reverse=True
            )
            
            # Return top 3 strategies
            return [
                json.loads(strategy)
                for strategy, _ in sorted_strategies[:3]
            ]
            
        except Exception as e:
            logger.error(f"Error getting best strategies: {str(e)}")
            return []
    
    def _calculate_parameter_adjustments(self, current_params: Dict,
                                      best_strategies: List[Dict]) -> Dict:
        """Calculate optimal parameter adjustments"""
        try:
            # Initialize optimized parameters
            optimized_params = current_params.copy()
            
            # Calculate weighted average of best strategies
            weights = [0.5, 0.3, 0.2]  # Weights for top 3 strategies
            
            for param_key in current_params:
                if param_key in best_strategies[0]:
                    weighted_value = sum(
                        strategy[param_key] * weight
                        for strategy, weight in zip(best_strategies, weights)
                        if param_key in strategy
                    )
                    
                    # Apply gradual adjustment
                    current_value = current_params[param_key]
                    adjustment = (weighted_value - current_value) * self.config["adaptation_rate"]
                    optimized_params[param_key] = current_value + adjustment
            
            return optimized_params
            
        except Exception as e:
            logger.error(f"Error calculating parameter adjustments: {str(e)}")
            return current_params
    
    def _analyze_feature_importance(self):
        """Analyze and log important features"""
        try:
            feature_names = [
                "volatility", "volume", "trend",
                "entry_threshold", "exit_threshold", "stop_loss",
                "slippage", "gas_price"
            ]
            
            # Get feature importance from models
            entry_importance = self.entry_model.feature_importances_
            exit_importance = self.exit_model.feature_importances_
            profit_importance = self.profit_model.feature_importances_
            
            # Log important features
            logger.info("📊 Feature Importance Analysis:")
            for name, entry_imp, exit_imp, profit_imp in zip(
                feature_names,
                entry_importance,
                exit_importance,
                profit_importance
            ):
                if max(entry_imp, exit_imp, profit_imp) > self.config["feature_importance_threshold"]:
                    logger.info(
                        f"{name}: Entry={entry_imp:.3f}, "
                        f"Exit={exit_imp:.3f}, Profit={profit_imp:.3f}"
                    )
            
        except Exception as e:
            logger.error(f"Error analyzing feature importance: {str(e)}")
    
    def _save_models(self):
        """Save trained models to disk"""
        try:
            joblib.dump(self.entry_model, self.model_path / "entry_model.joblib")
            joblib.dump(self.exit_model, self.model_path / "exit_model.joblib")
            joblib.dump(self.profit_model, self.model_path / "profit_model.joblib")
            joblib.dump(self.scaler, self.model_path / "scaler.joblib")
            
        except Exception as e:
            logger.error(f"Error saving models: {str(e)}")
    
    def _load_models(self):
        """Load trained models from disk"""
        try:
            if (self.model_path / "entry_model.joblib").exists():
                self.entry_model = joblib.load(self.model_path / "entry_model.joblib")
                self.exit_model = joblib.load(self.model_path / "exit_model.joblib")
                self.profit_model = joblib.load(self.model_path / "profit_model.joblib")
                self.scaler = joblib.load(self.model_path / "scaler.joblib")
                
        except Exception as e:
            logger.error(f"Error loading models: {str(e)}")
    
    async def _get_historical_trades(self) -> List[TradeResult]:
        """Get historical trades from database"""
        # TODO: Implement database query
        return self.performance_history
    
    async def _save_trade_to_db(self, trade_result: TradeResult):
        """Save trade result to database"""
        # TODO: Implement database save
        pass
    
    def _prepare_prediction_features(self, data: Dict) -> List[float]:
        """Prepare features for prediction"""
        # TODO: Implement feature preparation
        return [0.0] * 8  # Placeholder 