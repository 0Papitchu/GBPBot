#!/usr/bin/env python3
"""
Demo du système de continuous learning avec contournement des importations circulaires
"""

import asyncio
import sys
import os
from pathlib import Path
import importlib
import json
import datetime
import random

# Exemple de données simulées pour démontrer le système
class SimulatedData:
    """Classe pour générer des données de trading simulées"""
    
    def __init__(self):
        self.tokens = ["AVAX", "ETH", "BTC", "SOL", "MEME", "PEPE", "DOGE"]
        self.dexs = ["TraderJoe", "Pangolin", "Raydium", "SushiSwap"]
        
    def generate_trade(self, success=None):
        """Génère une transaction simulée avec résultat aléatoire"""
        token = random.choice(self.tokens)
        buy_dex = random.choice(self.dexs)
        sell_dex = random.choice([d for d in self.dexs if d != buy_dex])
        
        # Prix d'achat et de vente avec une petite variation
        entry_price = round(random.uniform(0.5, 1000.0), 6)
        
        # Si success est None, générer aléatoirement, sinon utiliser la valeur fournie
        is_successful = random.choice([True, False]) if success is None else success
        
        # Pour les transactions réussies, le prix de sortie est supérieur
        if is_successful:
            exit_price = round(entry_price * random.uniform(1.01, 1.2), 6)
        else:
            exit_price = round(entry_price * random.uniform(0.8, 0.99), 6)
            
        amount = round(random.uniform(0.1, 10.0), 4)
        
        # Calcul du profit ou de la perte
        profit_loss = round((exit_price - entry_price) * amount, 6)
        profit_percent = round((exit_price / entry_price - 1) * 100, 2)
        
        # Timestamp actuel avec une variation aléatoire dans les dernières 24h
        now = datetime.datetime.now()
        random_hours = random.randint(0, 24)
        timestamp = int((now - datetime.timedelta(hours=random_hours)).timestamp())
        
        # Construction du trade
        trade = {
            "id": f"trade_{int(timestamp)}_{token}",
            "token": token,
            "token_address": f"0x{random.randint(1000000, 9999999):x}",
            "buy_dex": buy_dex,
            "sell_dex": sell_dex,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "amount": amount,
            "gas_cost": round(random.uniform(0.001, 0.05), 6),
            "entry_timestamp": timestamp,
            "exit_timestamp": timestamp + random.randint(60, 3600),  # 1min à 1h après
            "successful": is_successful,
            "profit_loss": profit_loss,
            "profit_percent": profit_percent,
            "strategy": random.choice(["arbitrage", "sniping", "frontrunning"]),
            "market_conditions": {
                "volatility": random.choice(["high", "medium", "low"]),
                "trend": random.choice(["bullish", "bearish", "sideways"]),
                "liquidity": random.randint(10000, 10000000)
            },
            "execution_metrics": {
                "slippage": round(random.uniform(0, 3.0), 2),
                "latency_ms": random.randint(50, 500),
                "tx_confirmations": random.randint(1, 20)
            }
        }
        return trade

class ContinuousLearningSystem:
    """
    Version simplifiée du système d'apprentissage continu pour démonstration
    Simule les fonctionnalités sans dépendre des modules problématiques
    """
    
    def __init__(self):
        self.trades_db = []
        self.performance_metrics = {}
        self.recommendations = []
        self.simulator = SimulatedData()
        
    def record_trade(self, trade):
        """Enregistre une transaction et ses résultats"""
        self.trades_db.append(trade)
        print(f"✅ Trade enregistré: {trade['token']} ({trade['strategy']}) - {'Succès' if trade['successful'] else 'Échec'}")
        return True
        
    def analyze_performance(self):
        """Analyse les performances des transactions enregistrées"""
        if not self.trades_db:
            print("⚠️ Aucune donnée à analyser")
            return {}
            
        # Calcul des métriques de performance
        total_trades = len(self.trades_db)
        successful_trades = sum(1 for t in self.trades_db if t["successful"])
        success_rate = round(successful_trades / total_trades * 100, 2) if total_trades > 0 else 0
        
        total_profit = sum(t["profit_loss"] for t in self.trades_db)
        avg_profit_per_trade = round(total_profit / total_trades, 6) if total_trades > 0 else 0
        
        # Analyse par stratégie
        strategies = {}
        for trade in self.trades_db:
            strat = trade["strategy"]
            if strat not in strategies:
                strategies[strat] = {"count": 0, "success": 0, "profit": 0}
            
            strategies[strat]["count"] += 1
            if trade["successful"]:
                strategies[strat]["success"] += 1
            strategies[strat]["profit"] += trade["profit_loss"]
        
        # Calculer le taux de réussite et le profit moyen par stratégie
        for strat, data in strategies.items():
            data["success_rate"] = round(data["success"] / data["count"] * 100, 2) if data["count"] > 0 else 0
            data["avg_profit"] = round(data["profit"] / data["count"], 6) if data["count"] > 0 else 0
        
        # Analyse par token
        tokens = {}
        for trade in self.trades_db:
            token = trade["token"]
            if token not in tokens:
                tokens[token] = {"count": 0, "success": 0, "profit": 0}
            
            tokens[token]["count"] += 1
            if trade["successful"]:
                tokens[token]["success"] += 1
            tokens[token]["profit"] += trade["profit_loss"]
        
        # Meilleures conditions de marché
        market_conditions = {
            "volatility": {},
            "trend": {}
        }
        
        for trade in self.trades_db:
            for condition_type in ["volatility", "trend"]:
                condition_value = trade["market_conditions"][condition_type]
                if condition_value not in market_conditions[condition_type]:
                    market_conditions[condition_type][condition_value] = {"count": 0, "success": 0, "profit": 0}
                
                market_conditions[condition_type][condition_value]["count"] += 1
                if trade["successful"]:
                    market_conditions[condition_type][condition_value]["success"] += 1
                market_conditions[condition_type][condition_value]["profit"] += trade["profit_loss"]
        
        # Résumé de performance
        metrics = {
            "total_trades": total_trades,
            "successful_trades": successful_trades,
            "success_rate": success_rate,
            "total_profit": round(total_profit, 6),
            "avg_profit_per_trade": avg_profit_per_trade,
            "strategies": strategies,
            "tokens": tokens,
            "market_conditions": market_conditions
        }
        
        self.performance_metrics = metrics
        return metrics
        
    def generate_recommendations(self):
        """Génère des recommandations basées sur l'analyse de performance"""
        if not self.performance_metrics:
            print("⚠️ Aucune métrique disponible pour générer des recommandations")
            self.recommendations = []
            return []
        
        recommendations = []
        
        # Recommandations basées sur les stratégies
        strategies = self.performance_metrics["strategies"]
        best_strategy = max(strategies.items(), key=lambda x: x[1]["avg_profit"])
        worst_strategy = min(strategies.items(), key=lambda x: x[1]["avg_profit"])
        
        recommendations.append({
            "type": "strategy",
            "action": "prioritize",
            "target": best_strategy[0],
            "reason": f"Meilleure rentabilité moyenne ({best_strategy[1]['avg_profit']})",
            "confidence": 0.8
        })
        
        if worst_strategy[1]["avg_profit"] < 0:
            recommendations.append({
                "type": "strategy",
                "action": "avoid",
                "target": worst_strategy[0],
                "reason": f"Rentabilité négative ({worst_strategy[1]['avg_profit']})",
                "confidence": 0.7
            })
        
        # Recommandations basées sur les tokens
        tokens = self.performance_metrics["tokens"]
        # Vérifier s'il y a des tokens et calculer la métrique success_rate
        for token_data in tokens.values():
            if "success_rate" not in token_data:
                # Calculer le taux de réussite
                token_data["success_rate"] = round(token_data["success"] / token_data["count"] * 100, 2) if token_data["count"] > 0 else 0
        
        # Sélectionner le meilleur token s'il y en a
        if tokens:
            best_token = max(tokens.items(), key=lambda x: x[1]["success_rate"])
            
            if best_token[1]["success_rate"] > 70:
                recommendations.append({
                    "type": "token",
                    "action": "focus",
                    "target": best_token[0],
                    "reason": f"Taux de réussite élevé ({best_token[1]['success_rate']}%)",
                    "confidence": 0.75
                })
        
        # Recommandations basées sur les conditions de marché
        volatility = self.performance_metrics["market_conditions"]["volatility"]
        trend = self.performance_metrics["market_conditions"]["trend"]
        
        best_volatility = max(volatility.items(), key=lambda x: x[1]["success"] / x[1]["count"] if x[1]["count"] > 0 else 0) if volatility else None
        best_trend = max(trend.items(), key=lambda x: x[1]["success"] / x[1]["count"] if x[1]["count"] > 0 else 0) if trend else None
        
        if best_volatility:
            recommendations.append({
                "type": "market_condition",
                "action": "target",
                "target": f"volatility_{best_volatility[0]}",
                "reason": f"Meilleure condition de volatilité pour le succès",
                "confidence": 0.65
            })
        
        if best_trend:
            recommendations.append({
                "type": "market_condition",
                "action": "target",
                "target": f"trend_{best_trend[0]}",
                "reason": f"Meilleure tendance de marché pour le succès",
                "confidence": 0.7
            })
        
        # Paramètres d'exécution
        avg_slippage = sum(t["execution_metrics"]["slippage"] for t in self.trades_db) / len(self.trades_db) if self.trades_db else 0
        
        if avg_slippage > 1.5:
            recommendations.append({
                "type": "execution",
                "action": "adjust",
                "target": "slippage_tolerance",
                "value": round(avg_slippage + 0.5, 1),
                "reason": f"Slippage moyen élevé: {round(avg_slippage, 2)}%",
                "confidence": 0.85
            })
        
        self.recommendations = recommendations
        return recommendations
    
    def apply_recommendation(self, recommendation):
        """Simule l'application d'une recommandation aux paramètres du système"""
        if recommendation["type"] == "strategy":
            print(f"📊 Application de la recommandation: {recommendation['action']} stratégie {recommendation['target']}")
            return True
        elif recommendation["type"] == "token":
            print(f"📊 Application de la recommandation: {recommendation['action']} sur le token {recommendation['target']}")
            return True
        elif recommendation["type"] == "market_condition":
            print(f"📊 Application de la recommandation: {recommendation['action']} condition {recommendation['target']}")
            return True
        elif recommendation["type"] == "execution":
            print(f"📊 Application de la recommandation: {recommendation['action']} paramètre {recommendation['target']} à {recommendation.get('value', 'N/A')}")
            return True
        else:
            print(f"⚠️ Type de recommandation inconnu: {recommendation['type']}")
            return False
    
    def simulate_trades(self, count=10, apply_recommendations=False):
        """Simule une série de transactions pour démontrer le système"""
        print(f"\n📈 Simulation de {count} transactions...")
        
        for i in range(count):
            # Si des recommandations ont été appliquées, augmenter le taux de réussite
            success_bias = 0.7 if apply_recommendations else None
            trade = self.simulator.generate_trade(success=success_bias if random.random() < 0.8 else None)
            self.record_trade(trade)
            
        print(f"\n✅ {count} transactions simulées.")
        return self.trades_db[-count:]

async def demo_continuous_learning():
    """Fonction principale pour démontrer le fonctionnement du système"""
    print("\n" + "="*80)
    print("🔄 DÉMONSTRATION DU SYSTÈME D'APPRENTISSAGE CONTINU")
    print("="*80)
    
    # Initialiser le système
    learning_system = ContinuousLearningSystem()
    
    # Première série de transactions sans optimisation
    print("\n🔹 PHASE 1: Collecte de données initiales")
    learning_system.simulate_trades(20)
    
    # Analyse des performances et génération de recommandations
    print("\n🔹 PHASE 2: Analyse des performances")
    metrics = learning_system.analyze_performance()
    
    print("\nRésumé des performances:")
    print(f"  Transactions totales: {metrics['total_trades']}")
    print(f"  Taux de réussite: {metrics['success_rate']}%")
    print(f"  Profit total: {metrics['total_profit']}")
    print(f"  Profit moyen par transaction: {metrics['avg_profit_per_trade']}")
    
    print("\nPerformance par stratégie:")
    for strat, data in metrics["strategies"].items():
        print(f"  {strat}: {data['success_rate']}% réussite, profit moyen: {data['avg_profit']}")
    
    # Génération de recommandations
    print("\n🔹 PHASE 3: Génération de recommandations")
    recommendations = learning_system.generate_recommendations()
    
    print("\nRecommandations générées:")
    for i, rec in enumerate(recommendations):
        print(f"  {i+1}. {rec['action'].capitalize()} {rec['target']} - {rec['reason']} (Confiance: {rec['confidence']})")
    
    # Application des recommandations
    print("\n🔹 PHASE 4: Application des recommandations")
    for rec in recommendations:
        learning_system.apply_recommendation(rec)
    
    # Deuxième série de transactions avec optimisations
    print("\n🔹 PHASE 5: Nouvelles transactions avec optimisations appliquées")
    learning_system.simulate_trades(20, apply_recommendations=True)
    
    # Analyse finale
    print("\n🔹 PHASE 6: Analyse des résultats après optimisation")
    metrics = learning_system.analyze_performance()
    
    print("\nRésumé des performances après optimisation:")
    print(f"  Transactions totales: {metrics['total_trades']}")
    print(f"  Taux de réussite: {metrics['success_rate']}%")
    print(f"  Profit total: {metrics['total_profit']}")
    print(f"  Profit moyen par transaction: {metrics['avg_profit_per_trade']}")
    
    # Comparaison des stratégies après optimisation
    print("\nPerformance par stratégie après optimisation:")
    for strat, data in metrics["strategies"].items():
        print(f"  {strat}: {data['success_rate']}% réussite, profit moyen: {data['avg_profit']}")
    
    print("\n" + "="*80)
    print("✅ FIN DE LA DÉMONSTRATION")
    print("="*80)

if __name__ == "__main__":
    # Exécuter la démo
    asyncio.run(demo_continuous_learning()) 