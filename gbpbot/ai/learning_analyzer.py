#!/usr/bin/env python3
"""
Module d'analyse avancée pour le système d'apprentissage continu de GBPBot

Ce module fournit des outils d'analyse des performances de trading
pour identifier des tendances, des motifs et des opportunités d'amélioration.
Conçu pour être léger et optimisé pour les ressources disponibles.
"""

import os
import time
import logging
import sqlite3
import numpy as np
import pandas as pd
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

# Import local
from gbpbot.utils.logger import setup_logger
from gbpbot.ai.continuous_learning import get_continuous_learning, TradeRecord
from gbpbot.ai.parallel_analyzer import AnalysisTask, AnalysisPriority, get_parallel_analyzer

# Configuration du logger
logger = setup_logger("learning_analyzer", logging.INFO)

class LearningAnalyzer:
    """
    Analyseur avancé des données de trading pour l'apprentissage continu.
    
    Cette classe utilise les données stockées par le module ContinuousLearning
    pour réaliser des analyses plus poussées et extraire des insights précieux.
    """
    
    def __init__(self):
        """Initialise l'analyseur avec le système d'apprentissage continu."""
        self.cl = get_continuous_learning()
        self.analyzer = get_parallel_analyzer(max_workers=4)  # Limité pour préserver les ressources
    
    def analyze_token_performance(self, min_trades: int = 5) -> Dict[str, Dict[str, Any]]:
        """
        Analyse les performances par token.
        
        Args:
            min_trades: Nombre minimum de trades pour inclure un token dans l'analyse.
            
        Returns:
            Un dictionnaire des métriques de performance par token.
        """
        trades = self.cl.get_trade_history()
        if not trades:
            logger.warning("Aucun trade à analyser.")
            return {}
        
        # Convertir en DataFrame pandas pour faciliter l'analyse
        df = pd.DataFrame([vars(trade) for trade in trades])
        
        # Grouper par symbole et calculer les métriques clés
        token_stats = {}
        for symbol, group in df.groupby('symbol'):
            if len(group) < min_trades:
                continue
                
            wins = len(group[group['profit'] > 0])
            losses = len(group[group['profit'] <= 0])
            total = len(group)
            win_rate = wins / total if total > 0 else 0
            
            total_profit = group['profit'].sum()
            avg_profit = group['profit'].mean()
            std_profit = group['profit'].std() if len(group) > 1 else 0
            
            # Calculer le ratio risque/récompense moyen
            avg_gain = group[group['profit'] > 0]['profit'].mean() if wins > 0 else 0
            avg_loss = abs(group[group['profit'] < 0]['profit'].mean()) if losses > 0 else 0
            risk_reward = avg_gain / avg_loss if avg_loss > 0 else float('inf')
            
            token_stats[symbol] = {
                'total_trades': total,
                'win_rate': win_rate,
                'total_profit': total_profit,
                'avg_profit': avg_profit,
                'volatility': std_profit,
                'risk_reward': risk_reward,
                'score': win_rate * avg_profit * (1 + risk_reward) if risk_reward < float('inf') else win_rate * avg_profit
            }
        
        # Trier par score (performance globale)
        return {k: v for k, v in sorted(token_stats.items(), key=lambda item: item[1]['score'], reverse=True)}
    
    def analyze_time_patterns(self) -> Dict[str, Any]:
        """
        Analyse les patterns de performance en fonction du temps (heure, jour de la semaine).
        
        Returns:
            Un dictionnaire des métriques de performance par période temporelle.
        """
        trades = self.cl.get_trade_history()
        if not trades:
            logger.warning("Aucun trade à analyser.")
            return {}
        
        # Convertir en DataFrame
        df = pd.DataFrame([vars(trade) for trade in trades])
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
        df['hour'] = df['datetime'].dt.hour
        df['day_of_week'] = df['datetime'].dt.dayofweek  # 0=Lundi, 6=Dimanche
        
        # Analyse par heure
        hourly_stats = {}
        for hour, group in df.groupby('hour'):
            total_profit = group['profit'].sum()
            avg_profit = group['profit'].mean()
            win_rate = len(group[group['profit'] > 0]) / len(group) if len(group) > 0 else 0
            
            hourly_stats[hour] = {
                'total_trades': len(group),
                'total_profit': total_profit,
                'avg_profit': avg_profit,
                'win_rate': win_rate
            }
        
        # Analyse par jour de la semaine
        daily_stats = {}
        day_names = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
        for day, group in df.groupby('day_of_week'):
            total_profit = group['profit'].sum()
            avg_profit = group['profit'].mean()
            win_rate = len(group[group['profit'] > 0]) / len(group) if len(group) > 0 else 0
            
            daily_stats[day_names[day]] = {
                'total_trades': len(group),
                'total_profit': total_profit,
                'avg_profit': avg_profit,
                'win_rate': win_rate
            }
        
        return {
            'hourly': hourly_stats,
            'daily': daily_stats
        }
    
    def identify_market_conditions(self) -> Dict[str, Any]:
        """
        Identifie les conditions de marché dans lesquelles le trading est le plus performant.
        
        Returns:
            Un dictionnaire des conditions de marché optimales.
        """
        trades = self.cl.get_trade_history()
        if not trades:
            logger.warning("Aucun trade à analyser.")
            return {}
        
        # Pour une analyse plus sophistiquée, nous aurions besoin de données de marché
        # mais nous pouvons faire une analyse simplifiée basée sur les trades existants
        df = pd.DataFrame([vars(trade) for trade in trades])
        df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
        df = df.sort_values('datetime')
        
        # Analyser les séquences de trades profitables
        df['cumulative_profit'] = df['profit'].cumsum()
        
        # Identifier les périodes de croissance et de déclin
        df['profit_change'] = df['cumulative_profit'].diff()
        df['trend'] = np.where(df['profit_change'] > 0, 'bullish', 'bearish')
        
        # Calculer la durée des tendances
        trend_changes = (df['trend'] != df['trend'].shift(1)).astype(int).cumsum()
        trends = df.groupby(trend_changes).agg({
            'trend': 'first',
            'datetime': ['min', 'max'],
            'profit': 'sum',
            'trade_id': 'count'
        })
        
        trends.columns = ['trend', 'start_time', 'end_time', 'total_profit', 'trade_count']
        trends['duration_hours'] = (trends['end_time'] - trends['start_time']).dt.total_seconds() / 3600
        
        # Caractériser les meilleures conditions
        best_bull_trend = trends[trends['trend'] == 'bullish'].sort_values('total_profit', ascending=False).iloc[0] if len(trends[trends['trend'] == 'bullish']) > 0 else None
        worst_bear_trend = trends[trends['trend'] == 'bearish'].sort_values('total_profit').iloc[0] if len(trends[trends['trend'] == 'bearish']) > 0 else None
        
        # Durée moyenne des tendances
        avg_bull_duration = trends[trends['trend'] == 'bullish']['duration_hours'].mean() if len(trends[trends['trend'] == 'bullish']) > 0 else 0
        avg_bear_duration = trends[trends['trend'] == 'bearish']['duration_hours'].mean() if len(trends[trends['trend'] == 'bearish']) > 0 else 0
        
        return {
            'best_bull_trend': {
                'start': best_bull_trend['start_time'].strftime('%Y-%m-%d %H:%M:%S') if best_bull_trend is not None else None,
                'end': best_bull_trend['end_time'].strftime('%Y-%m-%d %H:%M:%S') if best_bull_trend is not None else None,
                'profit': float(best_bull_trend['total_profit']) if best_bull_trend is not None else 0,
                'trades': int(best_bull_trend['trade_count']) if best_bull_trend is not None else 0,
                'duration_hours': float(best_bull_trend['duration_hours']) if best_bull_trend is not None else 0
            },
            'worst_bear_trend': {
                'start': worst_bear_trend['start_time'].strftime('%Y-%m-%d %H:%M:%S') if worst_bear_trend is not None else None,
                'end': worst_bear_trend['end_time'].strftime('%Y-%m-%d %H:%M:%S') if worst_bear_trend is not None else None,
                'profit': float(worst_bear_trend['total_profit']) if worst_bear_trend is not None else 0,
                'trades': int(worst_bear_trend['trade_count']) if worst_bear_trend is not None else 0,
                'duration_hours': float(worst_bear_trend['duration_hours']) if worst_bear_trend is not None else 0
            },
            'avg_bull_duration': avg_bull_duration,
            'avg_bear_duration': avg_bear_duration
        }
    
    async def run_parallel_analysis(self) -> Dict[str, Any]:
        """
        Exécute plusieurs analyses en parallèle pour optimiser les performances.
        
        Returns:
            Un dictionnaire des résultats d'analyse.
        """
        tasks = [
            AnalysisTask(
                name="token_performance",
                func=self.analyze_token_performance,
                priority=AnalysisPriority.HIGH,
                timeout=5.0
            ),
            AnalysisTask(
                name="time_patterns",
                func=self.analyze_time_patterns,
                priority=AnalysisPriority.NORMAL,
                timeout=3.0
            ),
            AnalysisTask(
                name="market_conditions",
                func=self.identify_market_conditions,
                priority=AnalysisPriority.LOW,
                timeout=4.0
            )
        ]
        
        results = await self.analyzer.run_tasks_async(tasks)
        
        # Extraire les résultats
        output = {}
        for name, result in results.items():
            if result.success:
                output[name] = result.result
            else:
                logger.error(f"L'analyse {name} a échoué: {result.error}")
                output[name] = None
        
        return output
    
    def generate_recommendations(self) -> Dict[str, Any]:
        """
        Génère des recommandations basées sur toutes les analyses disponibles.
        
        Returns:
            Un dictionnaire de recommandations.
        """
        token_perf = self.analyze_token_performance()
        time_patterns = self.analyze_time_patterns()
        market_cond = self.identify_market_conditions()
        
        recommendations = {
            "tokens": {},
            "timing": {},
            "strategy_adjustments": {}
        }
        
        # Recommandations pour les tokens
        if token_perf:
            best_tokens = list(token_perf.keys())[:3]  # Top 3 des tokens
            worst_tokens = list(token_perf.keys())[-3:] if len(token_perf) > 3 else []  # Bottom 3 des tokens
            
            recommendations["tokens"]["focus_on"] = best_tokens
            recommendations["tokens"]["avoid"] = worst_tokens
            recommendations["tokens"]["risk_levels"] = {
                token: "low" if stats['volatility'] < 0.5 else 
                      "medium" if stats['volatility'] < 1.0 else 
                      "high"
                for token, stats in token_perf.items()
            }
        
        # Recommandations pour le timing
        if time_patterns:
            hourly = time_patterns['hourly']
            daily = time_patterns['daily']
            
            # Meilleures heures (top 3)
            best_hours = sorted(hourly.items(), key=lambda x: x[1]['avg_profit'], reverse=True)[:3]
            recommendations["timing"]["best_hours"] = [int(hour) for hour, _ in best_hours]
            
            # Meilleurs jours
            best_days = sorted(daily.items(), key=lambda x: x[1]['avg_profit'], reverse=True)
            recommendations["timing"]["best_days"] = [day for day, _ in best_days[:3]]
            
            # Pires moments (à éviter)
            worst_hours = sorted(hourly.items(), key=lambda x: x[1]['avg_profit'])[:3]
            recommendations["timing"]["avoid_hours"] = [int(hour) for hour, _ in worst_hours]
        
        # Ajustements de stratégie
        overall_perf = self.cl.analyze_performance()
        avg_profit = overall_perf.get('average_profit', 0)
        
        if avg_profit < 0:
            recommendations["strategy_adjustments"]["risk_level"] = "conservative"
            recommendations["strategy_adjustments"]["position_size"] = "reduce"
            recommendations["strategy_adjustments"]["stop_loss"] = "tighter"
        elif avg_profit < 0.5:
            recommendations["strategy_adjustments"]["risk_level"] = "moderate"
            recommendations["strategy_adjustments"]["position_size"] = "maintain"
            recommendations["strategy_adjustments"]["stop_loss"] = "standard"
        else:
            recommendations["strategy_adjustments"]["risk_level"] = "aggressive"
            recommendations["strategy_adjustments"]["position_size"] = "increase"
            recommendations["strategy_adjustments"]["stop_loss"] = "wider"
        
        # Recommandations basées sur les conditions de marché
        if market_cond and 'avg_bull_duration' in market_cond:
            if market_cond['avg_bull_duration'] > market_cond['avg_bear_duration']:
                recommendations["strategy_adjustments"]["trend_bias"] = "bullish"
                recommendations["strategy_adjustments"]["hold_time"] = "longer"
            else:
                recommendations["strategy_adjustments"]["trend_bias"] = "bearish"
                recommendations["strategy_adjustments"]["hold_time"] = "shorter"
        
        return recommendations
    
    def generate_strategy_parameters(self) -> Dict[str, Any]:
        """
        Génère des paramètres de stratégie optimisés basés sur l'analyse.
        
        Returns:
            Un dictionnaire des paramètres optimisés pour les différentes stratégies.
        """
        recommendations = self.generate_recommendations()
        
        # Paramètres par défaut
        default_params = {
            "arbitrage": {
                "min_profit_threshold": 0.5,  # %
                "max_slippage": 0.3,          # %
                "gas_priority": 1.0,          # multiplicateur
                "execution_timeout": 30,       # secondes
                "max_routes": 3
            },
            "sniping": {
                "max_buy_slippage": 2.0,      # %
                "max_gas_price": 50,           # gwei
                "confidence_threshold": 0.7,   # 0-1
                "take_profit": 20.0,           # %
                "stop_loss": 10.0,             # %
                "auto_sell_timeout": 3600      # secondes
            },
            "market_condition": {
                "trend_sensitivity": 0.5,      # 0-1
                "volatility_threshold": 1.0,   # écart-type
                "volume_threshold": 100000     # USD
            }
        }
        
        # Ajuster les paramètres en fonction des recommandations
        adjusted_params = default_params.copy()
        
        risk_level = recommendations["strategy_adjustments"].get("risk_level", "moderate")
        
        # Ajuster en fonction du niveau de risque
        if risk_level == "conservative":
            adjusted_params["arbitrage"]["min_profit_threshold"] = 0.8
            adjusted_params["arbitrage"]["max_slippage"] = 0.2
            adjusted_params["sniping"]["max_buy_slippage"] = 1.0
            adjusted_params["sniping"]["confidence_threshold"] = 0.85
            adjusted_params["sniping"]["take_profit"] = 15.0
            adjusted_params["sniping"]["stop_loss"] = 5.0
            adjusted_params["market_condition"]["trend_sensitivity"] = 0.7
        elif risk_level == "aggressive":
            adjusted_params["arbitrage"]["min_profit_threshold"] = 0.3
            adjusted_params["arbitrage"]["max_slippage"] = 0.5
            adjusted_params["sniping"]["max_buy_slippage"] = 3.0
            adjusted_params["sniping"]["confidence_threshold"] = 0.6
            adjusted_params["sniping"]["take_profit"] = 30.0
            adjusted_params["sniping"]["stop_loss"] = 15.0
            adjusted_params["market_condition"]["trend_sensitivity"] = 0.3
        
        # Ajuster en fonction du timing recommandé
        if "timing" in recommendations:
            if len(recommendations["timing"].get("best_hours", [])) > 0:
                # Si nous avons des heures optimales, nous pouvons être plus agressifs pendant ces heures
                adjusted_params["time_based"] = {
                    "optimal_hours": recommendations["timing"]["best_hours"],
                    "optimal_days": recommendations["timing"].get("best_days", []),
                    "aggressive_hours_multiplier": 1.2,  # Plus agressif pendant les heures optimales
                    "conservative_hours_multiplier": 0.8  # Plus conservateur pendant les heures non optimales
                }
        
        # Ajuster en fonction des tokens recommandés
        if "tokens" in recommendations and "focus_on" in recommendations["tokens"]:
            adjusted_params["token_preferences"] = {
                "preferred_tokens": recommendations["tokens"]["focus_on"],
                "avoid_tokens": recommendations["tokens"].get("avoid", []),
                "token_risk_levels": recommendations["tokens"].get("risk_levels", {})
            }
        
        return adjusted_params

# Instance singleton
_learning_analyzer_instance = None

def get_learning_analyzer() -> LearningAnalyzer:
    """Récupère l'instance singleton du LearningAnalyzer."""
    global _learning_analyzer_instance
    if _learning_analyzer_instance is None:
        _learning_analyzer_instance = LearningAnalyzer()
    return _learning_analyzer_instance

if __name__ == "__main__":
    import asyncio
    
    async def test_analyzer():
        analyzer = get_learning_analyzer()
        
        # Exécuter l'analyse parallèle
        print("Exécution de l'analyse parallèle...")
        results = await analyzer.run_parallel_analysis()
        
        print("\n=== Performances des Tokens ===")
        if results.get('token_performance'):
            for token, stats in results['token_performance'].items():
                print(f"{token}: Win Rate {stats['win_rate']:.2f}, Profit Moyen {stats['avg_profit']:.2f}")
        
        print("\n=== Patterns Temporels ===")
        if results.get('time_patterns') and 'hourly' in results['time_patterns']:
            best_hour = max(results['time_patterns']['hourly'].items(), key=lambda x: x[1]['avg_profit'])
            print(f"Meilleure heure: {best_hour[0]}h, Profit Moyen: {best_hour[1]['avg_profit']:.2f}")
        
        print("\n=== Recommandations ===")
        recs = analyzer.generate_recommendations()
        print(f"Niveau de risque recommandé: {recs['strategy_adjustments'].get('risk_level', 'N/A')}")
        print(f"Tokens à privilégier: {', '.join(recs['tokens'].get('focus_on', ['Aucun']))}")
        
        print("\n=== Paramètres de stratégie optimisés ===")
        params = analyzer.generate_strategy_parameters()
        print(f"Seuil de profit minimum (arbitrage): {params['arbitrage']['min_profit_threshold']}%")
        print(f"Take profit (sniping): {params['sniping']['take_profit']}%")
        print(f"Stop loss (sniping): {params['sniping']['stop_loss']}%")
    
    # Exécuter le test
    asyncio.run(test_analyzer()) 