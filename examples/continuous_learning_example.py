#!/usr/bin/env python3
"""
Exemple d'utilisation du système d'apprentissage continu de GBPBot

Ce script démontre comment utiliser le système d'apprentissage continu
pour optimiser des modules d'arbitrage et de sniping fictifs.
"""

import os
import time
import random
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

# Créer le dossier examples/ s'il n'existe pas
os.makedirs('examples', exist_ok=True)

# Ajuster le sys.path pour inclure le répertoire parent
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importer les modules d'apprentissage
from gbpbot.ai.continuous_learning import get_continuous_learning, TradeRecord
from gbpbot.ai.learning_analyzer import get_learning_analyzer
from gbpbot.ai.learning_integration import get_learning_integration

# Classe fictive de module d'arbitrage
class ArbitrageModule:
    """Module fictif d'arbitrage pour démontrer l'intégration avec l'apprentissage continu."""
    
    def __init__(self, name="arbitrage"):
        """Initialise le module d'arbitrage."""
        self.name = name
        self.params = {
            "min_profit_threshold": 0.5,  # %
            "max_slippage": 0.3,          # %
            "gas_priority": 1.0,          # multiplicateur
            "execution_timeout": 30,       # secondes
            "max_routes": 3
        }
        print(f"[{self.name}] Module initialisé avec paramètres par défaut")
    
    def update_parameters(self, new_params: Dict[str, Any]) -> None:
        """Met à jour les paramètres du module."""
        for key, value in new_params.items():
            if key in self.params:
                old_value = self.params[key]
                self.params[key] = value
                print(f"[{self.name}] Paramètre '{key}' mis à jour: {old_value} -> {value}")
            else:
                # Pour les sections spéciales comme token_preferences
                if key == "token_preferences":
                    print(f"[{self.name}] Préférences de tokens mises à jour: {value.get('preferred_tokens', [])}")
                elif key == "timing":
                    print(f"[{self.name}] Paramètres de timing mis à jour: heures optimales: {value.get('optimal_hours', [])}")
        
        print(f"[{self.name}] Paramètres mis à jour: {self.params}")
    
    def execute_trade(self, symbol: str, take_profit: float = 20.0) -> Dict[str, Any]:
        """Simule l'exécution d'un trade d'arbitrage."""
        # Simuler un résultat de trade aléatoire
        quantity = random.uniform(50, 500)
        price = random.uniform(0.0001, 0.1)
        profit_factor = random.uniform(-1.0, 2.0)  # 2/3 des trades sont gagnants
        
        # Appliquer l'impact du min_profit_threshold sur le résultat
        # Plus le seuil est élevé, plus les trades sont sélectifs et ont de meilleures chances de profit
        if self.params["min_profit_threshold"] > 0.7:
            profit_factor += 0.5  # Bonus pour les seuils élevés
        
        profit = price * quantity * profit_factor * (self.params["min_profit_threshold"] / 0.5)
        
        # Arrondir pour plus de lisibilité
        profit = round(profit, 2)
        quantity = round(quantity, 2)
        price = round(price, 6)
        
        # Créer le résultat du trade
        result = {
            'symbol': symbol,
            'trade_type': 'arbitrage',
            'quantity': quantity,
            'price': price,
            'profit': profit,
            'timestamp': time.time()
        }
        
        print(f"[{self.name}] Trade exécuté: {symbol}, Profit: {profit}")
        return result

# Classe fictive de module de sniping
class SnipingModule:
    """Module fictif de sniping pour démontrer l'intégration avec l'apprentissage continu."""
    
    def __init__(self, name="sniping"):
        """Initialise le module de sniping."""
        self.name = name
        self.params = {
            "max_buy_slippage": 2.0,      # %
            "max_gas_price": 50,           # gwei
            "confidence_threshold": 0.7,   # 0-1
            "take_profit": 20.0,           # %
            "stop_loss": 10.0,             # %
            "auto_sell_timeout": 3600      # secondes
        }
        self.preferred_tokens = []
        self.avoid_tokens = []
        print(f"[{self.name}] Module initialisé avec paramètres par défaut")
    
    def update_parameters(self, new_params: Dict[str, Any]) -> None:
        """Met à jour les paramètres du module."""
        for key, value in new_params.items():
            if key in self.params:
                old_value = self.params[key]
                self.params[key] = value
                print(f"[{self.name}] Paramètre '{key}' mis à jour: {old_value} -> {value}")
            elif key == "token_preferences":
                self.preferred_tokens = value.get('preferred_tokens', [])
                self.avoid_tokens = value.get('avoid_tokens', [])
                print(f"[{self.name}] Préférences de tokens mises à jour:")
                print(f"  - À privilégier: {self.preferred_tokens}")
                print(f"  - À éviter: {self.avoid_tokens}")
            elif key == "timing":
                print(f"[{self.name}] Paramètres de timing mis à jour: heures optimales: {value.get('optimal_hours', [])}")
        
        print(f"[{self.name}] Paramètres mis à jour: {self.params}")
    
    def execute_trade(self, symbol: str) -> Dict[str, Any]:
        """Simule l'exécution d'un trade de sniping."""
        # Simuler un résultat de trade aléatoire
        quantity = random.uniform(100, 1000)
        price = random.uniform(0.00001, 0.01)
        
        # Vérifier si le token est dans les préférés ou à éviter
        profit_factor = random.uniform(-2.0, 3.0)  # Base aléatoire
        
        if symbol in self.preferred_tokens:
            profit_factor += 1.0  # Bonus pour les tokens préférés
        elif symbol in self.avoid_tokens:
            profit_factor -= 1.0  # Malus pour les tokens à éviter
        
        # Appliquer l'impact du take_profit/stop_loss
        # Un take_profit plus élevé peut donner de meilleurs résultats, mais moins fréquemment
        profit_impact = (self.params["take_profit"] / 20.0) * (1.0 - self.params["stop_loss"] / 20.0)
        profit = price * quantity * profit_factor * profit_impact
        
        # Arrondir pour plus de lisibilité
        profit = round(profit, 2)
        quantity = round(quantity, 2)
        price = round(price, 8)
        
        # Créer le résultat du trade
        result = {
            'symbol': symbol,
            'trade_type': 'buy' if profit > 0 else 'sell',
            'quantity': quantity,
            'price': price,
            'profit': profit,
            'timestamp': time.time()
        }
        
        print(f"[{self.name}] Trade exécuté: {symbol}, Profit: {profit}")
        return result

async def run_learning_example():
    """Fonction principale pour exécuter l'exemple d'apprentissage continu."""
    print("\n=== Exemple d'Apprentissage Continu GBPBot ===\n")
    
    # Initialiser les modules fictifs
    arbitrage_module = ArbitrageModule()
    sniping_module = SnipingModule()
    
    # Obtenir l'instance d'intégration d'apprentissage
    integration = get_learning_integration()
    
    # Enregistrer les modules auprès du système d'apprentissage
    integration.register_module("arbitrage", arbitrage_module)
    integration.register_module("sniping", sniping_module)
    
    # Configurer le système d'apprentissage pour une mise à jour rapide (pour la démo)
    integration.set_update_interval(5)  # 5 secondes au lieu de l'heure par défaut
    integration.set_min_trades(10)      # 10 trades au lieu des 20 par défaut
    
    # Liste de tokens fictifs pour la simulation
    tokens = ["MEME1", "MEME2", "MEME3", "MEME4", "MEME5", "DOGE", "SHIB", "PEPE"]
    
    # Simuler des trades sur une période de temps
    print("\n== Simulation de trades ==\n")
    print("Exécution de 20 trades (10 arbitrage, 10 sniping)...")
    
    # Simuler 10 trades d'arbitrage
    for i in range(10):
        token = random.choice(tokens)
        trade_result = arbitrage_module.execute_trade(token)
        integration.record_trade("arbitrage", trade_result)
        await asyncio.sleep(0.2)  # Pause pour la lisibilité des logs
    
    # Simuler 10 trades de sniping
    for i in range(10):
        token = random.choice(tokens)
        trade_result = sniping_module.execute_trade(token)
        integration.record_trade("sniping", trade_result)
        await asyncio.sleep(0.2)  # Pause pour la lisibilité des logs
    
    # Afficher un résumé des performances après les 20 premiers trades
    print("\n== Résumé Initial des Performances ==\n")
    summary = integration.get_performance_summary()
    print(f"Total des trades: {summary['overall']['total_trades']}")
    print(f"Profit total: {summary['overall']['total_profit']:.2f}")
    print(f"Profit moyen: {summary['overall']['avg_profit']:.2f}")
    print(f"Taux de réussite: {summary['overall']['success_rate'] * 100:.1f}%")
    
    if summary['best_performers']:
        print("\nMeilleures paires:")
        for pair in summary['best_performers']:
            print(f"  {pair['symbol']}: Win Rate {pair['win_rate'] * 100:.1f}%, Profit moyen {pair['avg_profit']:.2f}")
    
    # Forcer une mise à jour des paramètres
    print("\n== Application des Recommandations ==\n")
    integration.force_update()
    
    # Laisser le système appliquer les recommandations
    print("Attente de 2 secondes pour l'application des recommandations...")
    await asyncio.sleep(2)
    
    # Simuler une deuxième série de trades avec les paramètres optimisés
    print("\n== Nouvelle série de trades avec paramètres optimisés ==\n")
    print("Exécution de 20 nouveaux trades avec les paramètres optimisés...")
    
    # Simuler 10 nouveaux trades d'arbitrage
    for i in range(10):
        token = random.choice(tokens)
        trade_result = arbitrage_module.execute_trade(token)
        integration.record_trade("arbitrage", trade_result)
        await asyncio.sleep(0.2)  # Pause pour la lisibilité des logs
    
    # Simuler 10 nouveaux trades de sniping
    for i in range(10):
        token = random.choice(tokens)
        trade_result = sniping_module.execute_trade(token)
        integration.record_trade("sniping", trade_result)
        await asyncio.sleep(0.2)  # Pause pour la lisibilité des logs
    
    # Afficher un résumé final des performances
    print("\n== Résumé Final des Performances ==\n")
    final_summary = integration.get_performance_summary()
    print(f"Total des trades: {final_summary['overall']['total_trades']}")
    print(f"Profit total: {final_summary['overall']['total_profit']:.2f}")
    print(f"Profit moyen: {final_summary['overall']['avg_profit']:.2f}")
    print(f"Taux de réussite: {final_summary['overall']['success_rate'] * 100:.1f}%")
    
    # Analyser l'amélioration des performances
    initial_avg_profit = summary['overall']['avg_profit']
    final_avg_profit = final_summary['overall']['avg_profit']
    change_pct = ((final_avg_profit / initial_avg_profit) - 1) * 100 if initial_avg_profit != 0 else 0
    
    print(f"\nChangement du profit moyen: {change_pct:.1f}% ({initial_avg_profit:.2f} -> {final_avg_profit:.2f})")
    
    # Afficher les paramètres finaux recommandés
    print("\n== Paramètres Finaux Recommandés ==\n")
    
    params = get_learning_analyzer().generate_strategy_parameters()
    
    print("Arbitrage:")
    for param, value in params.get('arbitrage', {}).items():
        print(f"  {param}: {value}")
    
    print("\nSniping:")
    for param, value in params.get('sniping', {}).items():
        print(f"  {param}: {value}")
    
    if 'token_preferences' in params:
        print("\nPréférences de tokens:")
        token_prefs = params['token_preferences']
        print(f"  À privilégier: {', '.join(token_prefs.get('preferred_tokens', []))}")
        print(f"  À éviter: {', '.join(token_prefs.get('avoid_tokens', []))}")
    
    if 'time_based' in params:
        print("\nParamètres basés sur le timing:")
        for param, value in params['time_based'].items():
            print(f"  {param}: {value}")
    
    print("\n=== Fin de la Démonstration ===")

if __name__ == "__main__":
    asyncio.run(run_learning_example()) 