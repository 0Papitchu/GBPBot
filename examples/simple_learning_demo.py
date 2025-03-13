#!/usr/bin/env python3
"""
Exemple simplifié du système d'apprentissage continu - GBPBot

Ce script démontre les fonctionnalités de base du système d'apprentissage continu
sans dépendre des modules opérationnels existants de GBPBot.
"""

import os
import sys
import time
import random
import asyncio
from datetime import datetime
from typing import Dict, Any, List

# S'assurer que les modules GBPBot sont dans le chemin d'importation
script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(script_dir)
sys.path.append(root_dir)

# Importations des modules d'apprentissage
try:
    from gbpbot.ai.continuous_learning import get_continuous_learning, TradeRecord
    from gbpbot.ai.learning_analyzer import get_learning_analyzer
    from gbpbot.ai.learning_integration import get_learning_integration
except ImportError as e:
    print(f"Erreur d'importation: {e}")
    print("Assurez-vous d'avoir créé les modules d'apprentissage continu.")
    sys.exit(1)

async def record_simulated_trades(num_trades=30):
    """Enregistre un ensemble de trades simulés."""
    print(f"\n[+] Enregistrement de {num_trades} trades simulés...\n")
    
    # Obtenir l'instance d'apprentissage continu
    cl = get_continuous_learning()
    
    # Liste de tokens fictifs
    tokens = ["MEME1", "MEME2", "MEME3", "DOGE", "SHIB", "PEPE"]
    
    # Enregistrer des trades avec des résultats aléatoires
    for i in range(num_trades):
        symbol = random.choice(tokens)
        trade_type = "buy" if i % 3 == 0 else "sell"
        quantity = random.uniform(100, 1000)
        price = random.uniform(0.0001, 0.01)
        
        # Générer un profit aléatoire avec une tendance pour certains tokens
        if symbol in ["MEME1", "DOGE"]:
            # Ces tokens ont tendance à être plus rentables
            profit_factor = random.uniform(-0.5, 2.0)  # Plus de chances d'être positif
        elif symbol in ["MEME3", "PEPE"]:
            # Ces tokens ont tendance à être moins rentables
            profit_factor = random.uniform(-2.0, 1.0)  # Plus de chances d'être négatif
        else:
            # Les autres tokens sont neutres
            profit_factor = random.uniform(-1.0, 1.0)
        
        profit = price * quantity * profit_factor
        profit = round(profit, 2)  # Arrondir pour plus de lisibilité
        
        # Créer et enregistrer le trade
        trade = TradeRecord(
            trade_id=None,
            symbol=symbol,
            trade_type=trade_type,
            quantity=quantity,
            price=price,
            profit=profit,
            timestamp=time.time() - (num_trades - i) * 3600  # Répartir les trades sur plusieurs heures
        )
        
        cl.record_trade(trade)
        print(f"  Trade {i+1}/{num_trades}: {symbol} {trade_type} - Profit: {profit:.2f}")
        
        # Petite pause pour ne pas submerger la sortie
        await asyncio.sleep(0.1)
    
    print("\n[+] Tous les trades simulés ont été enregistrés avec succès!")

async def analyze_trading_data():
    """Analyse les données de trading enregistrées."""
    print("\n[+] Analyse des données de trading...\n")
    
    # Obtenir l'instance d'analyseur
    analyzer = get_learning_analyzer()
    
    # Analyser les performances par token
    token_stats = analyzer.analyze_token_performance()
    
    print("  --- Performances par Token ---")
    if token_stats:
        for token, stats in token_stats.items():
            profit_symbol = "+" if stats['avg_profit'] > 0 else ""
            print(f"  {token}: {stats['total_trades']} trades, " 
                  f"Win rate: {stats['win_rate']*100:.1f}%, "
                  f"Profit moyen: {profit_symbol}{stats['avg_profit']:.2f}")
    else:
        print("  Pas assez de données pour analyser les performances par token.")
    
    # Analyser les patterns temporels
    time_patterns = analyzer.analyze_time_patterns()
    
    print("\n  --- Patterns Temporels ---")
    if time_patterns and 'hourly' in time_patterns and time_patterns['hourly']:
        # Trouver les meilleures heures de trading
        best_hours = sorted(time_patterns['hourly'].items(), 
                           key=lambda x: x[1]['avg_profit'], 
                           reverse=True)[:3]
        
        print("  Meilleures heures de trading:")
        for hour, stats in best_hours:
            print(f"  {hour}h: Profit moyen {stats['avg_profit']:.2f}, "
                  f"Win rate: {stats['win_rate']*100:.1f}%")
    else:
        print("  Pas assez de données pour analyser les patterns temporels.")
    
    # Générer des recommandations
    recommendations = analyzer.generate_recommendations()
    
    print("\n  --- Recommandations ---")
    if recommendations:
        if 'tokens' in recommendations and 'focus_on' in recommendations['tokens']:
            print(f"  Tokens à privilégier: {', '.join(recommendations['tokens']['focus_on'])}")
        
        if 'tokens' in recommendations and 'avoid' in recommendations['tokens']:
            print(f"  Tokens à éviter: {', '.join(recommendations['tokens']['avoid'])}")
        
        if 'strategy_adjustments' in recommendations:
            risk_level = recommendations['strategy_adjustments'].get('risk_level', 'moderate')
            print(f"  Niveau de risque recommandé: {risk_level}")
            
            position_size = recommendations['strategy_adjustments'].get('position_size', 'maintain')
            print(f"  Taille de position: {position_size}")
            
            stop_loss = recommendations['strategy_adjustments'].get('stop_loss', 'standard')
            print(f"  Stop-loss: {stop_loss}")
    else:
        print("  Pas assez de données pour générer des recommandations.")
    
    # Générer des paramètres optimisés
    params = analyzer.generate_strategy_parameters()
    
    print("\n  --- Paramètres Optimisés ---")
    if 'arbitrage' in params:
        print("  Paramètres d'arbitrage:")
        for param, value in params['arbitrage'].items():
            print(f"    {param}: {value}")
    
    if 'sniping' in params:
        print("\n  Paramètres de sniping:")
        for param, value in params['sniping'].items():
            print(f"    {param}: {value}")
    
    return analyzer

async def run_parallel_analysis():
    """Exécute plusieurs analyses en parallèle."""
    print("\n[+] Exécution d'analyses en parallèle...\n")
    
    # Obtenir l'instance d'analyseur
    analyzer = get_learning_analyzer()
    
    # Exécuter toutes les analyses en parallèle
    start_time = time.time()
    results = await analyzer.run_parallel_analysis()
    duration = time.time() - start_time
    
    print(f"  Analyses terminées en {duration:.2f} secondes")
    
    # Vérifier les résultats
    for name, result in results.items():
        status = "SUCCÈS" if result.success else f"ÉCHEC: {result.error}"
        print(f"  Analyse '{name}': {status} en {result.execution_time:.2f}s")
    
    # Obtenir l'analyseur parallèle pour les statistiques
    from gbpbot.ai.parallel_analyzer import get_parallel_analyzer
    parallel_analyzer = get_parallel_analyzer()
    stats = parallel_analyzer.get_stats()
    
    print("\n  --- Statistiques d'Exécution ---")
    print(f"  Taux de réussite: {stats['success_rate']*100:.1f}%")
    print(f"  Temps d'exécution moyen: {stats['avg_execution_time']:.3f}s")
    print(f"  Tâches terminées: {stats['successful_tasks']}/{stats['total_tasks']}")

async def main():
    """Fonction principale."""
    print("\n=== DÉMONSTRATION DU SYSTÈME D'APPRENTISSAGE CONTINU ===\n")
    print("Cette démonstration montre les capacités du système d'apprentissage")
    print("continu de GBPBot sans dépendre des modules opérationnels existants.")
    
    # 1. Enregistrer des trades simulés
    await record_simulated_trades(30)
    
    # 2. Analyser les données de trading
    analyzer = await analyze_trading_data()
    
    # 3. Exécuter des analyses en parallèle
    await run_parallel_analysis()
    
    print("\n=== Démonstration terminée avec succès! ===\n")

if __name__ == "__main__":
    asyncio.run(main()) 