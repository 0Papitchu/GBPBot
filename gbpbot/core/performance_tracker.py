from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from collections import deque
import json
from loguru import logger
import asyncio
from dataclasses import dataclass
from statistics import mean, median, stdev
from ..config.trading_config import TradingConfig

@dataclass
class TransactionMetrics:
    """Métriques d'une transaction"""
    timestamp: datetime
    gas_price: float
    gas_used: int
    execution_time: float
    profit: float
    success: bool
    network_congestion: float
    amount: float
    token_pair: str
    exchange: str

class PerformanceTracker:
    """Gestionnaire de suivi des performances et ajustements dynamiques"""
    
    def __init__(self):
        # Charger la configuration
        config = TradingConfig.get_performance_config()
        
        # Stockage en mémoire avec taille limitée
        self.transactions = deque(maxlen=config["window_size"])
        self.hourly_stats = {}
        self.daily_stats = {}
        
        # Métriques de performance
        self.total_profit = 0.0
        self.total_gas_spent = 0.0
        self.success_rate = 0.0
        
        # Configuration dynamique
        self.gas_price_multipliers = config["gas_multipliers"]
        self.min_success_rate = config["min_success_rate"]
        self.max_loss_percent = config["max_loss_percent"]
        self.profit_target = config["profit_target"]
        
        # Périodes d'analyse
        self.time_windows = config["time_windows"]
        
        # Volume quotidien
        self.daily_volume = 0.0
        
    def get_daily_volume(self) -> float:
        """Retourne le volume quotidien total des transactions"""
        try:
            # Calculer le volume des dernières 24 heures
            now = datetime.now()
            yesterday = now - timedelta(days=1)
            
            # Filtrer les transactions des dernières 24 heures
            recent_txs = [tx for tx in self.transactions if tx.timestamp >= yesterday]
            
            # Calculer le volume total
            volume = sum(tx.amount for tx in recent_txs)
            
            # Mettre à jour le volume quotidien
            self.daily_volume = volume
            
            return volume
        except Exception as e:
            logger.error(f"Erreur lors du calcul du volume quotidien: {str(e)}")
            return self.daily_volume  # Retourner la dernière valeur connue
        
    def add_transaction(self, metrics: TransactionMetrics):
        """Ajoute une transaction à l'historique et met à jour les statistiques"""
        self.transactions.append(metrics)
        
        # Mettre à jour les métriques globales
        if metrics.success:
            self.total_profit += metrics.profit
            self.total_gas_spent += metrics.gas_price * metrics.gas_used
            
        # Mettre à jour les statistiques horaires
        hour_key = metrics.timestamp.strftime("%Y-%m-%d %H:00")
        if hour_key not in self.hourly_stats:
            self.hourly_stats[hour_key] = {
                "transactions": [],
                "gas_prices": [],
                "profits": [],
                "congestion": []
            }
        
        self.hourly_stats[hour_key]["transactions"].append(metrics)
        self.hourly_stats[hour_key]["gas_prices"].append(metrics.gas_price)
        self.hourly_stats[hour_key]["profits"].append(metrics.profit)
        self.hourly_stats[hour_key]["congestion"].append(metrics.network_congestion)
        
        # Mettre à jour le taux de succès
        total_tx = len(self.transactions)
        successful_tx = sum(1 for tx in self.transactions if tx.success)
        self.success_rate = (successful_tx / total_tx) * 100 if total_tx > 0 else 0
        
    def get_optimal_gas_multiplier(self, congestion: float, hour: int) -> float:
        """Calcule le multiplicateur optimal pour les frais de gas"""
        try:
            # Analyser les performances historiques pour cette heure
            hour_stats = self._get_hour_stats(hour)
            
            # Si pas assez de données, utiliser le multiplicateur par défaut
            if not hour_stats or len(hour_stats["gas_prices"]) < 10:
                return self._get_congestion_based_multiplier(congestion)
                
            # Calculer le multiplicateur basé sur les performances historiques
            success_rate = hour_stats["success_rate"]
            avg_profit = hour_stats["avg_profit"]
            
            if success_rate > 90 and avg_profit > 0:
                # Réduire les frais si tout va bien
                return max(
                    self.gas_price_multipliers["low"],
                    self._get_congestion_based_multiplier(congestion) * 0.9
                )
            elif success_rate < 70 or avg_profit < 0:
                # Augmenter les frais si les performances sont mauvaises
                return min(
                    self.gas_price_multipliers["high"] * 1.5,
                    self._get_congestion_based_multiplier(congestion) * 1.2
                )
                
            return self._get_congestion_based_multiplier(congestion)
            
        except Exception as e:
            logger.error(f"Erreur lors du calcul du multiplicateur de gas: {str(e)}")
            return self.gas_price_multipliers["normal"]
            
    def _get_congestion_based_multiplier(self, congestion: float) -> float:
        """Calcule le multiplicateur de base selon la congestion"""
        if congestion > 0.8:
            return self.gas_price_multipliers["high"]
        elif congestion > 0.5:
            return self.gas_price_multipliers["normal"]
        return self.gas_price_multipliers["low"]
        
    def _get_hour_stats(self, hour: int) -> Optional[Dict]:
        """Récupère les statistiques pour une heure donnée"""
        try:
            # Filtrer les transactions pour cette heure
            relevant_txs = [tx for tx in self.transactions if tx.timestamp.hour == hour]
            
            if not relevant_txs:
                return None
                
            return {
                "success_rate": sum(1 for tx in relevant_txs if tx.success) / len(relevant_txs) * 100,
                "avg_profit": mean([tx.profit for tx in relevant_txs]),
                "avg_gas": mean([tx.gas_price for tx in relevant_txs]),
                "count": len(relevant_txs)
            }
        except Exception:
            return None
            
    def analyze_performance(self, window: str = "24h") -> Dict:
        """Analyse détaillée des performances sur une période donnée"""
        try:
            # Get transactions for the specified window
            period_txs = self._get_period_transactions(window)
            if not period_txs:
                return {}
                
            # Basic metrics
            total_tx = len(period_txs)
            success_count = sum(1 for tx in period_txs if tx.success)
            success_rate = (success_count / total_tx) * 100 if total_tx > 0 else 0
            
            # Profit analysis
            profits = [tx.profit for tx in period_txs]
            total_profit = sum(profits)
            avg_profit = mean(profits) if profits else 0
            profit_std = stdev(profits) if len(profits) > 1 else 0
            
            # Gas analysis
            gas_prices = [tx.gas_price for tx in period_txs]
            avg_gas = mean(gas_prices) if gas_prices else 0
            gas_std = stdev(gas_prices) if len(gas_prices) > 1 else 0
            
            # Performance by token pair
            pair_performance = self._analyze_pair_performance(period_txs)
            
            # Network analysis
            network_metrics = self._analyze_network_metrics(period_txs)
            
            # Time-based analysis
            time_metrics = self._analyze_time_metrics(period_txs)
            
            # Risk analysis
            risk_metrics = self._calculate_risk_metrics(period_txs)
            
            return {
                "period": window,
                "total_transactions": total_tx,
                "success_rate": success_rate,
                "profit_metrics": {
                    "total_profit": total_profit,
                    "average_profit": avg_profit,
                    "profit_std": profit_std,
                    "profit_sharpe": (avg_profit / profit_std) if profit_std > 0 else 0,
                    "cumulative_returns": self._calculate_cumulative_returns(period_txs)
                },
                "gas_metrics": {
                    "average_gas": avg_gas,
                    "gas_std": gas_std,
                    "total_gas_spent": sum(tx.gas_price * tx.gas_used for tx in period_txs),
                    "gas_efficiency": self._calculate_gas_efficiency(period_txs)
                },
                "pair_performance": pair_performance,
                "network_metrics": network_metrics,
                "time_metrics": time_metrics,
                "risk_metrics": risk_metrics,
                "optimization_recommendations": self._generate_optimization_recommendations(
                    pair_performance,
                    network_metrics,
                    time_metrics,
                    risk_metrics
                )
            }
            
        except Exception as e:
            logger.error(f"Error analyzing performance: {str(e)}")
            return {}
            
    def _analyze_pair_performance(self, transactions: List[TransactionMetrics]) -> Dict:
        """Analyze performance by token pair"""
        pair_stats = {}
        
        for tx in transactions:
            if tx.token_pair not in pair_stats:
                pair_stats[tx.token_pair] = {
                    "total_trades": 0,
                    "successful_trades": 0,
                    "total_profit": 0,
                    "total_volume": 0,
                    "avg_execution_time": [],
                    "success_rate": 0
                }
                
            stats = pair_stats[tx.token_pair]
            stats["total_trades"] += 1
            if tx.success:
                stats["successful_trades"] += 1
                stats["total_profit"] += tx.profit
            stats["total_volume"] += tx.amount
            stats["avg_execution_time"].append(tx.execution_time)
            
        # Calculate final metrics
        for pair, stats in pair_stats.items():
            stats["success_rate"] = (stats["successful_trades"] / stats["total_trades"]) * 100
            stats["avg_execution_time"] = mean(stats["avg_execution_time"])
            stats["profit_per_trade"] = stats["total_profit"] / stats["total_trades"]
            
        return pair_stats
        
    def _analyze_network_metrics(self, transactions: List[TransactionMetrics]) -> Dict:
        """Analyze network performance metrics"""
        congestion_levels = [tx.network_congestion for tx in transactions]
        execution_times = [tx.execution_time for tx in transactions]
        
        return {
            "avg_congestion": mean(congestion_levels) if congestion_levels else 0,
            "avg_execution_time": mean(execution_times) if execution_times else 0,
            "congestion_correlation": self._calculate_correlation(
                congestion_levels,
                [tx.profit for tx in transactions]
            ) if congestion_levels else 0
        }
        
    def _analyze_time_metrics(self, transactions: List[TransactionMetrics]) -> Dict:
        """Analyze time-based performance patterns"""
        hourly_stats = {}
        daily_stats = {}
        
        for tx in transactions:
            hour = tx.timestamp.hour
            day = tx.timestamp.strftime("%A")
            
            # Update hourly stats
            if hour not in hourly_stats:
                hourly_stats[hour] = []
            hourly_stats[hour].append(tx.profit)
            
            # Update daily stats
            if day not in daily_stats:
                daily_stats[day] = []
            daily_stats[day].append(tx.profit)
            
        # Calculate averages
        hourly_avg = {
            hour: mean(profits) if profits else 0
            for hour, profits in hourly_stats.items()
        }
        
        daily_avg = {
            day: mean(profits) if profits else 0
            for day, profits in daily_stats.items()
        }
        
        return {
            "hourly_performance": hourly_avg,
            "daily_performance": daily_avg,
            "best_trading_hours": sorted(
                hourly_avg.items(),
                key=lambda x: x[1],
                reverse=True
            )[:3],
            "best_trading_days": sorted(
                daily_avg.items(),
                key=lambda x: x[1],
                reverse=True
            )[:3]
        }
        
    def _calculate_risk_metrics(self, transactions: List[TransactionMetrics]) -> Dict:
        """Calculate risk-adjusted performance metrics"""
        profits = [tx.profit for tx in transactions]
        if not profits or len(profits) < 2:
            return {}
            
        returns = np.array(profits)
        avg_return = np.mean(returns)
        std_return = np.std(returns)
        
        return {
            "sharpe_ratio": (avg_return / std_return) if std_return > 0 else 0,
            "max_drawdown": self._calculate_max_drawdown(returns),
            "win_rate": sum(1 for p in profits if p > 0) / len(profits),
            "profit_factor": abs(sum(p for p in profits if p > 0) / sum(p for p in profits if p < 0)) if sum(p for p in profits if p < 0) != 0 else float('inf'),
            "risk_reward_ratio": self._calculate_risk_reward_ratio(profits)
        }
        
    def _generate_optimization_recommendations(self, pair_perf: Dict, network_metrics: Dict, time_metrics: Dict, risk_metrics: Dict) -> Dict:
        """Generate trading parameter optimization recommendations"""
        recommendations = {
            "trading_pairs": [],
            "timing": {},
            "risk_management": {},
            "gas_strategy": {}
        }
        
        # Recommend best performing pairs
        sorted_pairs = sorted(
            pair_perf.items(),
            key=lambda x: x[1]["profit_per_trade"],
            reverse=True
        )
        recommendations["trading_pairs"] = [
            {
                "pair": pair,
                "recommended_volume": stats["total_volume"] / stats["total_trades"],
                "optimal_execution_time": stats["avg_execution_time"]
            }
            for pair, stats in sorted_pairs[:3]
        ]
        
        # Timing recommendations
        best_hours = time_metrics["best_trading_hours"]
        recommendations["timing"] = {
            "optimal_hours": [hour for hour, _ in best_hours],
            "optimal_days": [day for day, _ in time_metrics["best_trading_days"]],
            "recommended_intervals": self._calculate_optimal_intervals(time_metrics)
        }
        
        # Risk management recommendations
        recommendations["risk_management"] = {
            "position_size": self._calculate_optimal_position_size(risk_metrics),
            "stop_loss": self._calculate_optimal_stop_loss(risk_metrics),
            "profit_target": self._calculate_optimal_profit_target(risk_metrics)
        }
        
        # Gas strategy recommendations
        recommendations["gas_strategy"] = {
            "base_multiplier": self._calculate_optimal_gas_multiplier(network_metrics),
            "congestion_thresholds": {
                "high": 0.8,
                "medium": 0.5,
                "low": 0.3
            }
        }
        
        return recommendations
        
    def _calculate_optimal_intervals(self, time_metrics: Dict) -> Dict:
        """Calculate optimal trading intervals based on historical performance"""
        try:
            hourly_perf = time_metrics["hourly_performance"]
            
            # Find clusters of profitable hours
            profitable_hours = [
                hour for hour, profit in hourly_perf.items()
                if profit > 0
            ]
            
            # Group consecutive hours
            intervals = []
            current_interval = [profitable_hours[0]]
            
            for hour in profitable_hours[1:]:
                if hour == current_interval[-1] + 1:
                    current_interval.append(hour)
                else:
                    intervals.append(current_interval)
                    current_interval = [hour]
                    
            intervals.append(current_interval)
            
            return {
                "trading_windows": [
                    {
                        "start": interval[0],
                        "end": interval[-1],
                        "duration": len(interval)
                    }
                    for interval in intervals
                ],
                "recommended_frequency": self._calculate_trading_frequency(time_metrics)
            }
            
        except Exception as e:
            logger.error(f"Error calculating optimal intervals: {str(e)}")
            return {}
            
    def _calculate_trading_frequency(self, time_metrics: Dict) -> int:
        """Calculate optimal trading frequency in minutes"""
        try:
            hourly_volatility = np.std(list(time_metrics["hourly_performance"].values()))
            
            # Adjust frequency based on volatility
            if hourly_volatility > 0.5:  # High volatility
                return 5  # Check every 5 minutes
            elif hourly_volatility > 0.3:  # Medium volatility
                return 10  # Check every 10 minutes
            else:
                return 15  # Check every 15 minutes
                
        except Exception:
            return 10  # Default to 10 minutes
            
    def get_optimal_trading_params(self) -> Dict:
        """Calcule les paramètres optimaux de trading basés sur l'analyse"""
        try:
            # Analyser les performances récentes
            stats_24h = self.analyze_performance("24h")
            stats_4h = self.analyze_performance("4h")
            
            # Ajuster les paramètres en fonction des performances
            params = {
                "min_profit_threshold": self._calculate_min_profit_threshold(stats_24h, stats_4h),
                "gas_price_strategy": self._determine_gas_strategy(stats_24h),
                "optimal_pairs": self._get_optimal_pairs(stats_24h),
                "trading_active": self._should_continue_trading(stats_4h)
            }
            
            return params
            
        except Exception as e:
            logger.error(f"Erreur lors du calcul des paramètres optimaux: {str(e)}")
            return {
                "min_profit_threshold": self.profit_target,
                "gas_price_strategy": "normal",
                "optimal_pairs": [],
                "trading_active": True
            }
            
    def _calculate_min_profit_threshold(self, stats_24h: Dict, stats_4h: Dict) -> float:
        """Calcule le seuil minimal de profit basé sur les performances"""
        try:
            if not stats_24h or not stats_4h:
                return self.profit_target
                
            # Utiliser une moyenne pondérée des profits récents
            recent_threshold = stats_4h.get("avg_gas_price", 0) * 2
            daily_threshold = stats_24h.get("avg_gas_price", 0) * 1.5
            
            # Ajuster en fonction du taux de succès
            if stats_4h.get("success_rate", 0) < self.min_success_rate:
                recent_threshold *= 1.2
                
            return max(self.profit_target, (recent_threshold * 0.7 + daily_threshold * 0.3))
            
        except Exception:
            return self.profit_target
            
    def _determine_gas_strategy(self, stats: Dict) -> str:
        """Détermine la stratégie de gas optimale"""
        try:
            if not stats:
                return "normal"
                
            success_rate = stats.get("success_rate", 0)
            congestion = stats.get("network_congestion", 0.5)
            
            if success_rate < self.min_success_rate or congestion > 0.8:
                return "high"
            elif success_rate > 90 and congestion < 0.5:
                return "low"
            return "normal"
            
        except Exception:
            return "normal"
            
    def _get_optimal_pairs(self, stats: Dict) -> List[str]:
        """Identifie les paires de tokens les plus performantes"""
        try:
            if not stats or "best_performing_pairs" not in stats:
                return []
                
            return [pair[0] for pair in stats["best_performing_pairs"]
                   if pair[1]["profit"] > self.profit_target]
                   
        except Exception:
            return []
            
    def _should_continue_trading(self, stats: Dict) -> bool:
        """Détermine si le trading doit continuer basé sur les performances récentes"""
        try:
            if not stats:
                return True
                
            # Arrêter si les pertes sont trop importantes
            if stats.get("total_profit", 0) < self.max_loss_percent:
                return False
                
            # Arrêter si le taux de succès est trop bas
            if stats.get("success_rate", 100) < self.min_success_rate:
                return False
                
            return True
            
        except Exception:
            return True  # Par défaut, continuer le trading 