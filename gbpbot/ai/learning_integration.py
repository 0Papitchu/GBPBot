#!/usr/bin/env python3
"""
Module d'intégration pour le système d'apprentissage continu - GBPBot

Ce module sert de pont entre le système d'apprentissage continu et les modules
opérationnels du GBPBot, permettant l'application automatique des stratégies
optimisées en fonction des performances historiques.
"""

import os
import time
import logging
import asyncio
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
from pathlib import Path

# Import local
from gbpbot.utils.logger import setup_logger
from gbpbot.ai.continuous_learning import get_continuous_learning, TradeRecord
from gbpbot.ai.learning_analyzer import get_learning_analyzer
from gbpbot.ai.parallel_analyzer import AnalysisTask, AnalysisPriority, get_parallel_analyzer

# Configuration du logger
logger = setup_logger("learning_integration", logging.INFO)

class LearningIntegration:
    """
    Intégration du système d'apprentissage continu avec les modules opérationnels.
    
    Cette classe permet d'appliquer les stratégies recommandées par le système
    d'apprentissage aux différents modules du GBPBot.
    """
    
    def __init__(self):
        """Initialise l'intégration avec le système d'apprentissage."""
        self.cl = get_continuous_learning()
        self.analyzer = get_learning_analyzer()
        self.parallel_analyzer = get_parallel_analyzer(max_workers=4)
        
        # Paramètres pour la mise à jour
        self.last_update_time = time.time()
        self.update_interval = 3600  # Par défaut: mise à jour toutes les heures
        self.min_trades_for_update = 10  # Nombre minimum de trades avant mise à jour
        
        # Modules intégrés (à remplir dynamiquement)
        self.integrated_modules = {}
        
        logger.info("Intégration du système d'apprentissage continu initialisée")
    
    def register_module(self, module_name: str, module_instance: Any) -> None:
        """
        Enregistre un module pour l'intégration avec le système d'apprentissage.
        
        Args:
            module_name: Identifiant du module (ex: "arbitrage", "sniping").
            module_instance: Instance du module à intégrer.
        """
        if hasattr(module_instance, 'update_parameters'):
            self.integrated_modules[module_name] = module_instance
            logger.info(f"Module '{module_name}' enregistré pour l'apprentissage continu")
        else:
            logger.warning(f"Le module '{module_name}' n'a pas de méthode 'update_parameters' et ne peut pas être intégré")
    
    def unregister_module(self, module_name: str) -> None:
        """
        Supprime un module de l'intégration.
        
        Args:
            module_name: Identifiant du module à supprimer.
        """
        if module_name in self.integrated_modules:
            del self.integrated_modules[module_name]
            logger.info(f"Module '{module_name}' supprimé de l'apprentissage continu")
    
    def record_trade(self, module_name: str, trade_data: Dict[str, Any]) -> None:
        """
        Enregistre un trade depuis un module opérationnel.
        
        Args:
            module_name: Identifiant du module source du trade.
            trade_data: Données du trade à enregistrer.
        """
        # Vérifier les données minimales requises
        required_fields = ['symbol', 'trade_type', 'quantity', 'price', 'profit']
        
        for field in required_fields:
            if field not in trade_data:
                logger.error(f"Champ requis '{field}' manquant dans les données du trade")
                return
        
        # Créer et enregistrer le trade
        trade = TradeRecord(
            trade_id=None,
            symbol=trade_data['symbol'],
            trade_type=trade_data['trade_type'],
            quantity=trade_data['quantity'],
            price=trade_data['price'],
            profit=trade_data['profit'],
            timestamp=trade_data.get('timestamp', time.time())
        )
        
        self.cl.record_trade(trade)
        logger.info(f"Trade enregistré pour le module '{module_name}': {trade.symbol} {trade.trade_type} profit={trade.profit}")
        
        # Vérifier si une mise à jour est nécessaire
        self._check_update_needed()
    
    def _check_update_needed(self) -> None:
        """Vérifie si une mise à jour des paramètres est nécessaire."""
        current_time = time.time()
        trades = self.cl.get_trade_history()
        
        # Mise à jour si (1) assez de temps s'est écoulé ET (2) assez de trades ont été effectués
        if (current_time - self.last_update_time > self.update_interval and
                len(trades) >= self.min_trades_for_update):
            self._update_all_modules()
    
    def _update_all_modules(self) -> None:
        """Met à jour les paramètres de tous les modules enregistrés."""
        if not self.integrated_modules:
            logger.warning("Aucun module enregistré pour la mise à jour des paramètres")
            return
        
        # Obtenir les paramètres recommandés
        strategy_params = self.analyzer.generate_strategy_parameters()
        
        # Mettre à jour chaque module avec les paramètres appropriés
        for module_name, module in self.integrated_modules.items():
            # Sélectionner les paramètres pertinents pour ce module
            params_to_update = {}
            
            if module_name == "arbitrage" and "arbitrage" in strategy_params:
                params_to_update = strategy_params["arbitrage"]
            elif module_name == "sniping" and "sniping" in strategy_params:
                params_to_update = strategy_params["sniping"]
            
            # Ajouter les préférences de tokens si disponibles
            if "token_preferences" in strategy_params:
                params_to_update["token_preferences"] = strategy_params["token_preferences"]
            
            # Ajouter les paramètres basés sur le timing si disponibles
            if "time_based" in strategy_params:
                params_to_update["timing"] = strategy_params["time_based"]
            
            # Mettre à jour les paramètres du module
            if params_to_update:
                try:
                    module.update_parameters(params_to_update)
                    logger.info(f"Paramètres du module '{module_name}' mis à jour: {params_to_update}")
                except Exception as e:
                    logger.error(f"Erreur lors de la mise à jour des paramètres du module '{module_name}': {e}")
        
        # Mettre à jour le timestamp de dernière mise à jour
        self.last_update_time = time.time()
        logger.info("Mise à jour des paramètres terminée pour tous les modules")
    
    def force_update(self) -> None:
        """Force une mise à jour immédiate des paramètres pour tous les modules."""
        logger.info("Mise à jour forcée des paramètres demandée")
        self._update_all_modules()
    
    def set_update_interval(self, interval_seconds: int) -> None:
        """
        Définit l'intervalle entre les mises à jour automatiques.
        
        Args:
            interval_seconds: Intervalle en secondes entre les mises à jour.
        """
        self.update_interval = max(300, interval_seconds)  # Minimum 5 minutes
        logger.info(f"Intervalle de mise à jour défini à {self.update_interval} secondes")
    
    def set_min_trades(self, min_trades: int) -> None:
        """
        Définit le nombre minimum de trades avant une mise à jour automatique.
        
        Args:
            min_trades: Nombre minimum de trades nécessaires.
        """
        self.min_trades_for_update = max(5, min_trades)
        logger.info(f"Nombre minimum de trades pour mise à jour défini à {self.min_trades_for_update}")
    
    async def start_auto_update_task(self) -> None:
        """Démarre une tâche asynchrone pour les mises à jour périodiques."""
        logger.info("Démarrage de la tâche de mise à jour périodique")
        while True:
            # Attendre l'intervalle défini
            await asyncio.sleep(self.update_interval)
            
            # Vérifier si une mise à jour est nécessaire
            trades = self.cl.get_trade_history()
            if len(trades) >= self.min_trades_for_update:
                logger.info("Mise à jour périodique des paramètres en cours...")
                self._update_all_modules()
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """
        Génère un résumé des performances basé sur l'apprentissage continu.
        
        Returns:
            Un dictionnaire contenant un résumé des performances.
        """
        # Analyser les performances
        overall_stats = self.cl.analyze_performance()
        token_stats = self.analyzer.analyze_token_performance()
        
        # Extraire les paires les plus et moins performantes
        top_pairs = []
        bottom_pairs = []
        
        for i, (symbol, stats) in enumerate(token_stats.items()):
            if i < 3 and stats['total_trades'] >= 5:  # Top 3 avec au moins 5 trades
                top_pairs.append({
                    'symbol': symbol,
                    'win_rate': stats['win_rate'],
                    'avg_profit': stats['avg_profit'],
                    'total_profit': stats['total_profit']
                })
            elif len(token_stats) - i <= 3 and stats['total_trades'] >= 5:  # Bottom 3 avec au moins 5 trades
                bottom_pairs.append({
                    'symbol': symbol,
                    'win_rate': stats['win_rate'],
                    'avg_profit': stats['avg_profit'],
                    'total_profit': stats['total_profit']
                })
        
        # Obtenir les recommandations
        recommendations = self.analyzer.generate_recommendations()
        
        # Construire le résumé
        summary = {
            'overall': {
                'total_trades': overall_stats.get('total_trades', 0),
                'total_profit': overall_stats.get('total_profit', 0.0),
                'avg_profit': overall_stats.get('average_profit', 0.0),
                'success_rate': len([t for t in self.cl.get_trade_history() if t.profit > 0]) / max(1, overall_stats.get('total_trades', 1))
            },
            'best_performers': top_pairs,
            'worst_performers': bottom_pairs,
            'recommendations': {
                'risk_level': recommendations.get('strategy_adjustments', {}).get('risk_level', 'moderate'),
                'focus_tokens': recommendations.get('tokens', {}).get('focus_on', []),
                'avoid_tokens': recommendations.get('tokens', {}).get('avoid', []),
                'best_hours': recommendations.get('timing', {}).get('best_hours', []),
                'best_days': recommendations.get('timing', {}).get('best_days', [])
            }
        }
        
        return summary

# Instance singleton
_learning_integration_instance = None

def get_learning_integration() -> LearningIntegration:
    """Récupère l'instance singleton de l'intégration d'apprentissage."""
    global _learning_integration_instance
    if _learning_integration_instance is None:
        _learning_integration_instance = LearningIntegration()
    return _learning_integration_instance

# Exemple d'utilisation
if __name__ == "__main__":
    import asyncio
    
    async def test_integration():
        # Obtenir l'instance d'intégration
        integration = get_learning_integration()
        
        # Simuler l'enregistrement de quelques trades
        for i in range(15):
            profit = 10.0 if i % 3 == 0 else -5.0  # 1/3 de trades gagnants
            
            integration.record_trade("arbitrage", {
                'symbol': f"MEME{i%5}",  # 5 tokens différents
                'trade_type': 'buy' if i % 2 == 0 else 'sell',
                'quantity': 100.0,
                'price': 0.001 * (i + 1),
                'profit': profit
            })
        
        # Forcer une mise à jour
        integration.force_update()
        
        # Obtenir un résumé des performances
        summary = integration.get_performance_summary()
        print("\n=== Résumé des Performances ===")
        print(f"Total des trades: {summary['overall']['total_trades']}")
        print(f"Profit total: {summary['overall']['total_profit']:.2f}")
        print(f"Profit moyen: {summary['overall']['avg_profit']:.2f}")
        print(f"Taux de réussite: {summary['overall']['success_rate']:.2f}")
        
        print("\n=== Meilleures Paires ===")
        for pair in summary['best_performers']:
            print(f"{pair['symbol']}: Win Rate {pair['win_rate']:.2f}, Profit Moyen {pair['avg_profit']:.2f}")
        
        print("\n=== Recommandations ===")
        print(f"Niveau de risque: {summary['recommendations']['risk_level']}")
        print(f"Tokens à privilégier: {', '.join(summary['recommendations']['focus_tokens'])}")
        
        # Démarrer la tâche de mise à jour automatique (pour démonstration)
        integration.set_update_interval(5)  # 5 secondes pour la démo
        update_task = asyncio.create_task(integration.start_auto_update_task())
        
        # Laisser tourner pendant 10 secondes
        await asyncio.sleep(10)
        
        # Annuler la tâche
        update_task.cancel()
        try:
            await update_task
        except asyncio.CancelledError:
            print("Tâche de mise à jour annulée")
    
    # Exécuter le test
    asyncio.run(test_integration()) 