#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module de génération de données de simulation pour tester le GBPBot.
Ce module permet de simuler des opportunités de trading, des transactions et des performances
pour tester l'interface utilisateur et l'API sans avoir besoin de connexion réelle aux marchés.
"""

import random
import time
import datetime
import math
import json
import os
from typing import List, Dict, Any, Optional

# Paires de trading courantes
TRADING_PAIRS = [
    "BTC/USDT", "ETH/USDT", "BNB/USDT", "SOL/USDT", "XRP/USDT",
    "ADA/USDT", "AVAX/USDT", "DOGE/USDT", "DOT/USDT", "MATIC/USDT",
    "LINK/USDT", "UNI/USDT", "ATOM/USDT", "LTC/USDT", "NEAR/USDT"
]

# Types de transactions
TRADE_TYPES = ["SPOT", "LIMIT", "MARKET", "STOP_LOSS", "TAKE_PROFIT"]

# Stratégies
STRATEGIES = ["Sniping", "Arbitrage", "MEV"]

class SimulationData:
    """Classe pour générer des données de simulation pour le GBPBot."""
    
    def __init__(self, seed: Optional[int] = None):
        """
        Initialiser le générateur de données de simulation.
        
        Args:
            seed: Graine pour le générateur de nombres aléatoires (pour la reproductibilité)
        """
        if seed is not None:
            random.seed(seed)
        
        self.start_time = time.time()
        self.opportunities_detected = 0
        self.trades_executed = 0
        self.total_profit = 0.0
        self.performance_history = []
        self.trades_history = []
        self.bot_status = "running"  # running, stopped
        self.bot_mode = "SIMULATION"  # TEST, SIMULATION, LIVE
        self.strategies = {
            "sniping": False,
            "arbitrage": False,
            "mev": False
        }
        
        # Paramètres de simulation
        self.opportunity_chance = 0.3  # 30% de chance de détecter une opportunité à chaque tick
        self.trade_execution_chance = 0.7  # 70% de chance d'exécuter un trade pour une opportunité
        self.trade_success_chance = 0.9  # 90% de chance qu'un trade soit réussi
        self.price_volatility = 0.02  # 2% de volatilité des prix
        
        # Charger les données sauvegardées si elles existent
        self._load_data()
    
    def _load_data(self):
        """Charger les données sauvegardées si elles existent."""
        try:
            if os.path.exists("simulation_data.json"):
                with open("simulation_data.json", "r") as f:
                    data = json.load(f)
                
                self.start_time = data.get("start_time", self.start_time)
                self.opportunities_detected = data.get("opportunities_detected", 0)
                self.trades_executed = data.get("trades_executed", 0)
                self.total_profit = data.get("total_profit", 0.0)
                self.performance_history = data.get("performance_history", [])
                self.trades_history = data.get("trades_history", [])
                self.bot_status = data.get("bot_status", "running")
                self.bot_mode = data.get("bot_mode", "SIMULATION")
                self.strategies = data.get("strategies", {
                    "sniping": False,
                    "arbitrage": False,
                    "mev": False
                })
        except Exception as e:
            print(f"Erreur lors du chargement des données: {e}")
    
    def _save_data(self):
        """Sauvegarder les données de simulation."""
        try:
            data = {
                "start_time": self.start_time,
                "opportunities_detected": self.opportunities_detected,
                "trades_executed": self.trades_executed,
                "total_profit": self.total_profit,
                "performance_history": self.performance_history,
                "trades_history": self.trades_history,
                "bot_status": self.bot_status,
                "bot_mode": self.bot_mode,
                "strategies": self.strategies
            }
            
            with open("simulation_data.json", "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Erreur lors de la sauvegarde des données: {e}")
    
    def get_runtime(self) -> float:
        """
        Obtenir le temps d'exécution du bot en secondes.
        
        Returns:
            float: Temps d'exécution en secondes
        """
        if self.bot_status == "running":
            return time.time() - self.start_time
        return 0
    
    def get_runtime_formatted(self) -> str:
        """
        Obtenir le temps d'exécution du bot formaté (HH:MM:SS).
        
        Returns:
            str: Temps d'exécution formaté
        """
        runtime = self.get_runtime()
        hours, remainder = divmod(int(runtime), 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    def simulate_tick(self):
        """Simuler un tick de données (appelé périodiquement)."""
        if self.bot_status != "running":
            return
        
        # Simuler la détection d'opportunités
        if random.random() < self.opportunity_chance:
            self._simulate_opportunity()
        
        # Mettre à jour les données de performance
        self._update_performance()
        
        # Sauvegarder les données
        self._save_data()
    
    def _simulate_opportunity(self):
        """Simuler la détection d'une opportunité de trading."""
        self.opportunities_detected += 1
        
        # Vérifier si une stratégie est active
        active_strategies = [s for s, active in self.strategies.items() if active]
        if not active_strategies:
            return
        
        # Simuler l'exécution d'un trade si la chance est favorable
        if random.random() < self.trade_execution_chance:
            self._simulate_trade(random.choice(active_strategies))
    
    def _simulate_trade(self, strategy: str):
        """
        Simuler l'exécution d'un trade.
        
        Args:
            strategy: La stratégie utilisée pour le trade
        """
        self.trades_executed += 1
        
        # Générer un profit/perte aléatoire
        is_success = random.random() < self.trade_success_chance
        
        # Le profit dépend du mode
        if self.bot_mode == "TEST":
            profit_factor = random.uniform(0.001, 0.01)
        elif self.bot_mode == "SIMULATION":
            profit_factor = random.uniform(0.01, 0.05)
        else:  # LIVE
            profit_factor = random.uniform(0.05, 0.2)
        
        # Ajuster le profit en fonction du succès
        if is_success:
            profit = profit_factor * random.uniform(1.0, 5.0)
        else:
            profit = -profit_factor * random.uniform(0.5, 2.0)
        
        # Ajuster le profit total
        self.total_profit += profit
        
        # Créer l'enregistrement de trade
        trade = {
            "id": len(self.trades_history) + 1,
            "timestamp": time.time(),
            "type": random.choice(TRADE_TYPES),
            "pair": random.choice(TRADING_PAIRS),
            "amount": round(random.uniform(0.01, 1.0), 4),
            "price": round(random.uniform(100, 50000), 2),
            "profit": round(profit, 4),
            "status": "success" if is_success else "failed",
            "strategy": strategy
        }
        
        # Ajouter à l'historique
        self.trades_history.append(trade)
        
        # Limiter l'historique à 100 trades
        if len(self.trades_history) > 100:
            self.trades_history = self.trades_history[-100:]
    
    def _update_performance(self):
        """Mettre à jour les données de performance."""
        # Ajouter un point de données toutes les 5 minutes environ
        if not self.performance_history or time.time() - self.performance_history[-1]["timestamp"] > 300:
            performance_point = {
                "timestamp": time.time(),
                "profit": round(self.total_profit, 4),
                "opportunities": self.opportunities_detected,
                "trades": self.trades_executed
            }
            self.performance_history.append(performance_point)
            
            # Limiter l'historique à 1000 points
            if len(self.performance_history) > 1000:
                self.performance_history = self.performance_history[-1000:]
    
    def get_status(self) -> Dict[str, Any]:
        """
        Obtenir le statut actuel du bot.
        
        Returns:
            Dict[str, Any]: Statut du bot
        """
        return {
            "status": self.bot_status,
            "mode": self.bot_mode,
            "runtime": self.get_runtime(),
            "runtime_formatted": self.get_runtime_formatted(),
            "opportunities_detected": self.opportunities_detected,
            "trades_executed": self.trades_executed,
            "total_profit": round(self.total_profit, 4),
            "sniping": self.strategies["sniping"],
            "arbitrage": self.strategies["arbitrage"],
            "mev": self.strategies["mev"]
        }
    
    def get_trades(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Obtenir l'historique des trades.
        
        Args:
            limit: Nombre maximum de trades à retourner
        
        Returns:
            List[Dict[str, Any]]: Liste des trades
        """
        # Convertir les timestamps en format lisible
        trades = []
        for trade in self.trades_history[-limit:]:
            trade_copy = trade.copy()
            trade_copy["timestamp"] = datetime.datetime.fromtimestamp(
                trade["timestamp"]
            ).strftime("%Y-%m-%d %H:%M:%S")
            trades.append(trade_copy)
        
        return trades
    
    def get_performance(self) -> List[Dict[str, Any]]:
        """
        Obtenir les données de performance.
        
        Returns:
            List[Dict[str, Any]]: Données de performance
        """
        # Convertir les timestamps en format lisible
        performance = []
        for point in self.performance_history:
            point_copy = point.copy()
            point_copy["timestamp"] = datetime.datetime.fromtimestamp(
                point["timestamp"]
            ).strftime("%Y-%m-%d %H:%M:%S")
            performance.append(point_copy)
        
        return performance
    
    def change_mode(self, mode: str) -> bool:
        """
        Changer le mode du bot.
        
        Args:
            mode: Nouveau mode (TEST, SIMULATION, LIVE)
        
        Returns:
            bool: True si le changement a réussi, False sinon
        """
        if mode not in ["TEST", "SIMULATION", "LIVE"]:
            return False
        
        self.bot_mode = mode
        self._save_data()
        return True
    
    def toggle_strategy(self, strategy: str, active: bool) -> bool:
        """
        Activer ou désactiver une stratégie.
        
        Args:
            strategy: Nom de la stratégie
            active: True pour activer, False pour désactiver
        
        Returns:
            bool: True si le changement a réussi, False sinon
        """
        if strategy not in self.strategies:
            return False
        
        self.strategies[strategy] = active
        self._save_data()
        return True
    
    def start_bot(self) -> bool:
        """
        Démarrer le bot.
        
        Returns:
            bool: True si le démarrage a réussi, False sinon
        """
        if self.bot_status == "running":
            return False
        
        self.bot_status = "running"
        self.start_time = time.time()
        self._save_data()
        return True
    
    def stop_bot(self) -> bool:
        """
        Arrêter le bot.
        
        Returns:
            bool: True si l'arrêt a réussi, False sinon
        """
        if self.bot_status == "stopped":
            return False
        
        self.bot_status = "stopped"
        self._save_data()
        return True
    
    def reset_bot(self) -> bool:
        """
        Réinitialiser les statistiques du bot.
        
        Returns:
            bool: True si la réinitialisation a réussi, False sinon
        """
        self.opportunities_detected = 0
        self.trades_executed = 0
        self.total_profit = 0.0
        self.performance_history = []
        self.trades_history = []
        self.start_time = time.time()
        self._save_data()
        return True

# Instance globale pour faciliter l'accès
simulation = SimulationData()

if __name__ == "__main__":
    # Test de la simulation
    sim = SimulationData(seed=42)
    
    print("Simulation de 100 ticks...")
    for _ in range(100):
        sim.simulate_tick()
        time.sleep(0.1)
    
    print(f"Opportunités détectées: {sim.opportunities_detected}")
    print(f"Trades exécutés: {sim.trades_executed}")
    print(f"Profit total: {sim.total_profit:.4f} USDT")
    print(f"Temps d'exécution: {sim.get_runtime_formatted()}")
    
    print("\nDerniers trades:")
    for trade in sim.get_trades(5):
        print(f"{trade['timestamp']} - {trade['pair']} - {trade['profit']:.4f} USDT") 