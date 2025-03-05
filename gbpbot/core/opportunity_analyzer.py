from typing import Dict, List, Optional
from datetime import datetime, timedelta
import numpy as np
from loguru import logger
import asyncio
from .performance_tracker import PerformanceTracker, TransactionMetrics
from ..config.trading_config import TradingConfig

class OpportunityAnalyzer:
    """Analyseur d'opportunités en temps réel avec ajustements dynamiques"""
    
    def __init__(self, performance_tracker: PerformanceTracker):
        self.performance_tracker = performance_tracker
        
        # Charger la configuration
        config = TradingConfig.get_opportunity_config()
        
        # Configuration de base
        self.min_profit_threshold = config["min_profit_threshold"]
        self.max_slippage = config["max_slippage"]
        self.min_liquidity = config["min_liquidity"]
        
        # Fenêtres d'analyse
        self.short_window = config["short_window"]
        self.long_window = config["long_window"]
        
        # Scores de confiance
        self.confidence_weights = config["confidence_weights"]
        self.risk_levels = config["risk_levels"]
        
        # Configuration du slippage
        self.slippage_config = config["slippage"]
        
        # Métriques de marché
        self.market_volatility = {}
        self.token_liquidity = {}
        self.exchange_reliability = {}
        
    async def analyze_opportunity(self, opportunity: Dict) -> Dict:
        """Analyse une opportunité et retourne des recommandations détaillées"""
        try:
            # Get optimal parameters
            params = self.performance_tracker.get_optimal_trading_params()
            
            # Initialize analysis result
            analysis = {
                "timestamp": datetime.now(),
                "is_valid": False,
                "confidence_score": 0.0,
                "recommended_gas_strategy": params["gas_price_strategy"],
                "risk_level": "high",
                "expected_profit": 0.0,
                "execution_priority": "normal",
                "market_conditions": {},
                "validation_checks": {}
            }
            
            # Check if trading is active
            if not params["trading_active"]:
                analysis["reason"] = "Trading temporarily suspended"
                return analysis
            
            # Market condition analysis
            market_conditions = await self._analyze_market_conditions(opportunity)
            analysis["market_conditions"] = market_conditions
            
            # Validation checks with weighted scoring
            validation_checks = {
                "profit_threshold": {
                    "passed": opportunity["profit_percent"] >= self.min_profit_threshold,
                    "weight": 0.3,
                    "score": 1.0 if opportunity["profit_percent"] >= self.min_profit_threshold else 0.0
                },
                "liquidity": {
                    "passed": opportunity.get("liquidity", 0) >= self.min_liquidity,
                    "weight": 0.2,
                    "score": min(1.0, opportunity.get("liquidity", 0) / self.min_liquidity)
                },
                "volatility": {
                    "passed": market_conditions["volatility"] <= 0.5,
                    "weight": 0.15,
                    "score": max(0.0, 1.0 - market_conditions["volatility"])
                },
                "network_congestion": {
                    "passed": market_conditions["network_congestion"] <= 0.8,
                    "weight": 0.15,
                    "score": max(0.0, 1.0 - market_conditions["network_congestion"])
                },
                "exchange_reliability": {
                    "passed": market_conditions["exchange_reliability"] >= 0.95,
                    "weight": 0.2,
                    "score": market_conditions["exchange_reliability"]
                }
            }
            
            analysis["validation_checks"] = validation_checks
            
            # Calculate weighted confidence score
            confidence_score = sum(
                check["weight"] * check["score"]
                for check in validation_checks.values()
            )
            analysis["confidence_score"] = confidence_score
            
            # Determine risk level
            risk_level = self._determine_risk_level(validation_checks, market_conditions)
            analysis["risk_level"] = risk_level
            
            # Calculate expected profit with risk adjustment
            expected_profit = opportunity["profit_percent"] * confidence_score
            analysis["expected_profit"] = expected_profit
            
            # Determine execution priority
            execution_priority = self._determine_execution_priority(
                expected_profit,
                market_conditions,
                risk_level
            )
            analysis["execution_priority"] = execution_priority
            
            # Final validation
            analysis["is_valid"] = (
                confidence_score >= 0.7 and  # High confidence required
                risk_level in ["low", "medium"] and  # Acceptable risk
                all(check["passed"] for check in validation_checks.values())  # All checks pass
            )
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing opportunity: {str(e)}")
            return {
                "is_valid": False,
                "reason": f"Analysis error: {str(e)}"
            }
            
    async def _analyze_market_conditions(self, opportunity: Dict) -> Dict:
        """Analyze current market conditions for the trading pair"""
        try:
            # Get historical volatility
            volatility = await self._calculate_volatility(opportunity["token_pair"])
            
            # Get network congestion
            network_congestion = await self._get_network_congestion()
            
            # Get exchange reliability scores
            exchange_reliability = self._get_exchange_reliability(
                opportunity["buy_exchange"],
                opportunity["sell_exchange"]
            )
            
            # Get market depth and liquidity
            liquidity_data = await self._analyze_liquidity(opportunity)
            
            return {
                "volatility": volatility,
                "network_congestion": network_congestion,
                "exchange_reliability": exchange_reliability,
                "liquidity": liquidity_data["total_liquidity"],
                "market_depth": liquidity_data["market_depth"],
                "price_impact": liquidity_data["price_impact"],
                "timestamp": datetime.now()
            }
            
        except Exception as e:
            logger.error(f"Error analyzing market conditions: {str(e)}")
            return {
                "volatility": 0.5,  # Medium volatility
                "network_congestion": 0.5,  # Medium congestion
                "exchange_reliability": 0.95,  # High reliability
                "liquidity": self.min_liquidity,
                "market_depth": 0.5,
                "price_impact": 0.005,  # 0.5% impact
                "timestamp": datetime.now()
            }
            
    def _determine_risk_level(self, validation_checks: Dict, market_conditions: Dict) -> str:
        """Determine the risk level of the opportunity"""
        try:
            risk_score = 0.0
            
            # Weight different factors
            if market_conditions["volatility"] > 0.5:
                risk_score += 0.4
            if market_conditions["network_congestion"] > 0.8:
                risk_score += 0.3
            if market_conditions["liquidity"] < self.min_liquidity:
                risk_score += 0.3
                
            # Consider validation checks
            failed_checks = sum(1 for check in validation_checks.values() if not check["passed"])
            risk_score += failed_checks * 0.1
            
            # Determine risk level
            if risk_score < 0.3:
                return "low"
            elif risk_score < 0.6:
                return "medium"
            else:
                return "high"
                
        except Exception as e:
            logger.error(f"Error determining risk level: {str(e)}")
            return "high"  # Conservative default
            
    def _determine_execution_priority(self, expected_profit: float, market_conditions: Dict, risk_level: str) -> str:
        """Determine the execution priority based on profit and risk"""
        try:
            if risk_level == "low" and expected_profit > 2.0:  # >2% profit
                return "high"
            elif risk_level == "medium" and expected_profit > 3.0:  # >3% profit
                return "high"
            elif expected_profit > 5.0:  # >5% profit
                return "high"
            elif expected_profit > 1.0:  # >1% profit
                return "normal"
            else:
                return "low"
                
        except Exception as e:
            logger.error(f"Error determining execution priority: {str(e)}")
            return "normal"
            
    def _calculate_confidence_score(self, opportunity: Dict) -> float:
        """Calcule un score de confiance pour l'opportunité"""
        try:
            scores = []
            
            # Score basé sur le profit
            profit_score = min(opportunity["profit_percent"] / 5, 1.0)  # Max 5%
            scores.append(profit_score * self.confidence_weights["profit"])
            
            # Score basé sur la liquidité
            liquidity = opportunity.get("liquidity", 0)
            liquidity_score = min(liquidity / self.min_liquidity, 1.0)
            scores.append(liquidity_score * self.confidence_weights["liquidity"])
            
            # Score basé sur la fiabilité de l'exchange
            exchange = opportunity.get("exchange", "")
            reliability = self.exchange_reliability.get(exchange, 0.5)
            scores.append(reliability * self.confidence_weights["reliability"])
            
            # Score basé sur la volatilité
            token_pair = opportunity.get("token_pair", "")
            volatility = self.market_volatility.get(token_pair, 0.5)
            volatility_score = 1 - volatility  # Moins volatile = meilleur
            scores.append(volatility_score * self.confidence_weights["volatility"])
            
            return sum(scores)
            
        except Exception:
            return 0.0
            
    def _calculate_expected_profit(self, opportunity: Dict, gas_strategy: str) -> float:
        """Calcule le profit attendu en tenant compte des frais"""
        try:
            # Récupérer le profit brut
            profit = opportunity["profit_percent"]
            
            # Estimer les frais de gas
            gas_multiplier = self.performance_tracker.gas_price_multipliers[gas_strategy]
            estimated_gas_cost = opportunity.get("estimated_gas", 0) * gas_multiplier
            
            # Calculer le profit net
            net_profit = profit - estimated_gas_cost
            
            # Appliquer un facteur de risque
            risk_factor = self._calculate_risk_factor(opportunity)
            expected_profit = net_profit * risk_factor
            
            return max(0, expected_profit)
            
        except Exception:
            return 0.0
            
    def _calculate_risk_factor(self, opportunity: Dict) -> float:
        """Calcule un facteur de risque pour l'opportunité"""
        try:
            # Facteurs de base
            base_factor = 0.8  # 80% du profit attendu
            
            # Ajuster selon la volatilité
            token_pair = opportunity.get("token_pair", "")
            volatility = self.market_volatility.get(token_pair, 0.5)
            volatility_factor = 1 - (volatility * 0.5)  # Réduire jusqu'à 50%
            
            # Ajuster selon la liquidité
            liquidity = opportunity.get("liquidity", 0)
            liquidity_factor = min(liquidity / (self.min_liquidity * 2), 1.0)
            
            return base_factor * volatility_factor * liquidity_factor
            
        except Exception:
            return 0.5  # Valeur par défaut conservative
            
    def _calculate_optimal_slippage(self, opportunity: Dict) -> float:
        """Calcule le slippage optimal basé sur les conditions du marché"""
        try:
            # Slippage de base
            base_slippage = self.slippage_config["base"]
            
            # Ajuster selon la volatilité
            token_pair = opportunity.get("token_pair", "")
            volatility = self.market_volatility.get(token_pair, 0.5)
            
            # Plus de volatilité = plus de slippage
            adjusted_slippage = base_slippage * (1 + volatility * self.slippage_config["volatility_multiplier"])
            
            # Limiter le slippage maximum
            return min(adjusted_slippage, self.slippage_config["max"])
            
        except Exception:
            return self.max_slippage
            
    def update_market_metrics(self, token_pair: str, metrics: Dict):
        """Met à jour les métriques de marché pour une paire de tokens"""
        try:
            # Mettre à jour la volatilité
            if "volatility" in metrics:
                self.market_volatility[token_pair] = metrics["volatility"]
                
            # Mettre à jour la liquidité
            if "liquidity" in metrics:
                self.token_liquidity[token_pair] = metrics["liquidity"]
                
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour des métriques: {str(e)}")
            
    def update_exchange_reliability(self, exchange: str, success_rate: float):
        """Met à jour la fiabilité d'un exchange"""
        try:
            # Mettre à jour avec une moyenne mobile
            current = self.exchange_reliability.get(exchange, 0.5)
            self.exchange_reliability[exchange] = current * 0.7 + success_rate * 0.3
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour de la fiabilité: {str(e)}") 