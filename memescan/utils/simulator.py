import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from loguru import logger
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

from memescan.utils.config import Config
from memescan.storage.database import Database
from memescan.collectors.token_detector import TokenDetector
from memescan.analyzers.auto_sniping import AutoSniper
from memescan.ml.ml_predictor import MLPredictor

class TradingSimulator:
    """Simulateur de trading pour tester la rentabilité du système"""
    
    def __init__(self, config: Config, db: Database, ml_predictor: MLPredictor):
        self.config = config
        self.db = db
        self.ml_predictor = ml_predictor
        
        # Paramètres de simulation
        self.initial_balance = 5.0  # 5 AVAX
        self.current_balance = self.initial_balance
        self.simulation_days = 7  # Durée de simulation en jours
        self.simulation_speed = 1  # 1 = temps réel, >1 = accéléré
        
        # Portefeuille simulé
        self.portfolio = {}  # {token_address: {amount, buy_price, buy_time}}
        self.trade_history = []  # Liste des trades effectués
        self.profit_history = []  # Historique des profits
        
        # Paramètres de stratégie
        self.take_profit = 2.0  # Vendre à +100%
        self.stop_loss = 0.5  # Vendre à -50%
        self.max_hold_time = 48  # Heures maximum de détention
        
        # Métriques de performance
        self.total_trades = 0
        self.profitable_trades = 0
        self.total_profit = 0.0
        self.max_drawdown = 0.0
        
        # Répertoire pour les résultats
        self.results_dir = Path("simulation_results")
        self.results_dir.mkdir(exist_ok=True)
        
    async def start_simulation(self):
        """Démarre la simulation de trading"""
        logger.info(f"Starting trading simulation with {self.initial_balance} AVAX")
        
        # Enregistrer l'état initial
        self.profit_history.append({
            "timestamp": datetime.now(),
            "balance": self.current_balance,
            "portfolio_value": 0,
            "total_value": self.current_balance
        })
        
        # Simuler le temps qui passe
        start_time = datetime.now()
        end_time = start_time + timedelta(days=self.simulation_days)
        
        current_sim_time = start_time
        
        while current_sim_time < end_time:
            try:
                # Simuler la détection de nouveaux tokens
                detected_tokens = await self._simulate_token_detection(current_sim_time)
                
                for token in detected_tokens:
                    # Analyser le token avec le ML
                    ml_score = await self._get_ml_prediction(token)
                    
                    # Décider si on achète
                    if ml_score >= 0.7 and self.current_balance > 0.1:
                        await self._simulate_buy(token, ml_score)
                
                # Vérifier le portefeuille pour les prises de profit / stop loss
                await self._check_portfolio(current_sim_time)
                
                # Mettre à jour les métriques
                await self._update_metrics(current_sim_time)
                
                # Avancer le temps simulé
                time_step = timedelta(minutes=5 / self.simulation_speed)
                current_sim_time += time_step
                
                # Attendre un peu pour ne pas surcharger le système
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error in simulation: {str(e)}")
                await asyncio.sleep(1)
        
        # Générer le rapport final
        await self._generate_report()
        
    async def _simulate_token_detection(self, current_time: datetime) -> List[Dict]:
        """Simule la détection de nouveaux tokens"""
        # Dans une simulation réelle, on utiliserait des données historiques
        # ou on générerait des tokens synthétiques avec des caractéristiques réalistes
        
        # Pour cette simulation, générons quelques tokens aléatoires
        detected_tokens = []
        
        # Probabilité de détecter un nouveau token (environ 1 toutes les 2 heures)
        detection_probability = 0.05 * self.simulation_speed
        
        if np.random.random() < detection_probability:
            # Générer un token avec des caractéristiques aléatoires
            token = {
                "address": f"0x{np.random.randint(0, 16**40):040x}",
                "symbol": f"MEME{np.random.randint(1000, 9999)}",
                "name": f"MemeCoin {np.random.randint(1000, 9999)}",
                "chain": "avalanche",
                "dex": "trader_joe",
                "price": np.random.uniform(0.00001, 0.001),
                "liquidity_usd": np.random.uniform(1000, 5000),
                "market_cap": np.random.uniform(2000, 10000),
                "is_meme": True,
                "detection_time": current_time.isoformat(),
                "created_at": current_time.isoformat(),
                "holders": np.random.randint(10, 100),
                "transactions_24h": np.random.randint(5, 50)
            }
            
            # Ajouter des caractéristiques pour le ML
            token["volume_24h"] = token["market_cap"] * np.random.uniform(0.1, 0.5)
            token["volume_1h"] = token["volume_24h"] / np.random.uniform(20, 24)
            token["token_age_days"] = 0.01
            
            detected_tokens.append(token)
            logger.info(f"Detected new token: {token['symbol']} at {current_time}")
        
        return detected_tokens
    
    async def _get_ml_prediction(self, token: Dict) -> float:
        """Obtient une prédiction ML pour le token"""
        try:
            # Dans une simulation réelle, on utiliserait le vrai modèle ML
            # Pour cette simulation, générons un score basé sur les caractéristiques du token
            
            # Facteurs positifs
            positive_factors = [
                token["liquidity_usd"] / 5000,  # Plus de liquidité = mieux
                min(1.0, 10000 / token["market_cap"]),  # Plus petite market cap = mieux
                token["volume_24h"] / token["market_cap"],  # Ratio volume/mcap élevé = mieux
                token["holders"] / 100,  # Plus de holders = mieux
                token["transactions_24h"] / 50  # Plus de transactions = mieux
            ]
            
            # Calculer un score basé sur ces facteurs
            base_score = sum(positive_factors) / len(positive_factors)
            
            # Ajouter un peu d'aléatoire pour simuler l'incertitude du ML
            ml_score = min(1.0, max(0.0, base_score + np.random.normal(0, 0.1)))
            
            logger.debug(f"ML prediction for {token['symbol']}: {ml_score:.2f}")
            return ml_score
            
        except Exception as e:
            logger.error(f"Error in ML prediction simulation: {str(e)}")
            return 0.0
    
    async def _simulate_buy(self, token: Dict, ml_score: float):
        """Simule l'achat d'un token"""
        try:
            # Déterminer le montant à acheter (entre 0.1 et 0.5 AVAX)
            buy_amount = min(self.current_balance, np.random.uniform(0.1, 0.5))
            
            if buy_amount < 0.1:
                logger.debug(f"Insufficient balance to buy {token['symbol']}")
                return
            
            # Simuler l'achat
            self.current_balance -= buy_amount
            
            # Calculer la quantité de tokens achetés
            token_amount = buy_amount / token["price"]
            
            # Enregistrer dans le portefeuille
            self.portfolio[token["address"]] = {
                "symbol": token["symbol"],
                "amount": token_amount,
                "buy_price": token["price"],
                "buy_time": datetime.fromisoformat(token["detection_time"]),
                "buy_amount_avax": buy_amount,
                "ml_score": ml_score
            }
            
            # Enregistrer le trade
            self.trade_history.append({
                "type": "buy",
                "token": token["symbol"],
                "token_address": token["address"],
                "price": token["price"],
                "amount": token_amount,
                "value_avax": buy_amount,
                "time": datetime.fromisoformat(token["detection_time"]),
                "ml_score": ml_score
            })
            
            self.total_trades += 1
            
            logger.info(f"Bought {token_amount:.2f} {token['symbol']} for {buy_amount:.4f} AVAX")
            
        except Exception as e:
            logger.error(f"Error in buy simulation: {str(e)}")
    
    async def _check_portfolio(self, current_time: datetime):
        """Vérifie le portefeuille pour les prises de profit / stop loss"""
        tokens_to_sell = []
        
        for address, token_data in self.portfolio.items():
            # Simuler l'évolution du prix
            hours_since_buy = (current_time - token_data["buy_time"]).total_seconds() / 3600
            
            # Modèle simple d'évolution de prix:
            # - 20% des tokens explosent (x3-x10)
            # - 30% des tokens font un petit profit (x1.2-x2)
            # - 50% des tokens perdent de la valeur (x0.1-x0.9)
            
            # Déterminer le type de token basé sur le score ML
            token_type = np.random.choice(
                ["moon", "profit", "loss"], 
                p=[0.2 + token_data["ml_score"] * 0.2, 0.3, 0.5 - token_data["ml_score"] * 0.2]
            )
            
            # Calculer le multiplicateur de prix basé sur le temps écoulé et le type
            if token_type == "moon":
                # Croissance exponentielle pour les tokens qui explosent
                max_mult = np.random.uniform(3, 10)
                price_mult = min(max_mult, 1 + (max_mult - 1) * (hours_since_buy / 48))
            elif token_type == "profit":
                # Croissance modérée
                max_mult = np.random.uniform(1.2, 2)
                price_mult = min(max_mult, 1 + (max_mult - 1) * (hours_since_buy / 24))
            else:
                # Décroissance
                min_mult = np.random.uniform(0.1, 0.9)
                price_mult = max(min_mult, 1 - (1 - min_mult) * (hours_since_buy / 12))
            
            # Ajouter un peu de volatilité
            price_mult *= np.random.uniform(0.9, 1.1)
            
            # Calculer le nouveau prix
            current_price = token_data["buy_price"] * price_mult
            
            # Calculer la valeur actuelle
            current_value = token_data["amount"] * current_price
            
            # Calculer le profit/perte en pourcentage
            profit_loss_pct = (current_price / token_data["buy_price"]) - 1
            
            # Vérifier les conditions de vente
            sell_reason = None
            
            if profit_loss_pct >= (self.take_profit - 1):
                sell_reason = "take_profit"
            elif profit_loss_pct <= (self.stop_loss - 1):
                sell_reason = "stop_loss"
            elif hours_since_buy >= self.max_hold_time:
                sell_reason = "max_hold_time"
            
            if sell_reason:
                # Préparer les données pour la vente
                token = {
                    "address": address,
                    "symbol": token_data["symbol"],
                    "price": current_price,
                    "amount": token_data["amount"],
                    "current_value": current_value,
                    "buy_price": token_data["buy_price"],
                    "buy_time": token_data["buy_time"],
                    "profit_loss_pct": profit_loss_pct * 100,
                    "detection_time": token_data["buy_time"].isoformat(),
                    "time": current_time
                }
                
                # Ajouter à la liste des tokens à vendre
                tokens_to_sell.append((token, sell_reason))
        
        # Vendre les tokens
        for token, reason in tokens_to_sell:
            await self._simulate_sell(token, reason)
    
    async def _simulate_sell(self, token: Dict, reason: str):
        """Simule la vente d'un token"""
        try:
            # Mettre à jour le solde
            self.current_balance += token["current_value"]
            
            # Calculer le profit
            profit = token["current_value"] - token["buy_amount_avax"]
            
            # Mettre à jour les métriques
            if profit > 0:
                self.profitable_trades += 1
            
            self.total_profit += profit
            
            # Enregistrer le trade
            self.trade_history.append({
                "type": "sell",
                "token": token["symbol"],
                "token_address": token["address"],
                "price": token["price"],
                "amount": token["amount"],
                "value_avax": token["current_value"],
                "profit_loss": profit,
                "profit_loss_pct": token["profit_loss_pct"],
                "reason": reason,
                "time": token["time"]
            })
            
            # Retirer du portefeuille
            del self.portfolio[token["address"]]
            
            logger.info(f"Sold {token['amount']:.2f} {token['symbol']} for {token['current_value']:.4f} AVAX " +
                       f"({token['profit_loss_pct']:+.2f}%, {profit:+.4f} AVAX) - Reason: {reason}")
            
        except Exception as e:
            logger.error(f"Error in sell simulation: {str(e)}")
    
    async def _update_metrics(self, current_time: datetime):
        """Met à jour les métriques de performance"""
        try:
            # Calculer la valeur du portefeuille
            portfolio_value = 0.0
            
            for address, token_data in self.portfolio.items():
                # Simuler le prix actuel
                hours_since_buy = (current_time - token_data["buy_time"]).total_seconds() / 3600
                price_mult = np.random.uniform(0.5, 2.0) * (1 + 0.1 * hours_since_buy)
                current_price = token_data["buy_price"] * price_mult
                
                # Calculer la valeur
                token_value = token_data["amount"] * current_price
                portfolio_value += token_value
            
            # Calculer la valeur totale
            total_value = self.current_balance + portfolio_value
            
            # Calculer le drawdown
            max_value = max([p["total_value"] for p in self.profit_history], default=self.initial_balance)
            current_drawdown = (max_value - total_value) / max_value
            self.max_drawdown = max(self.max_drawdown, current_drawdown)
            
            # Enregistrer l'historique
            self.profit_history.append({
                "timestamp": current_time,
                "balance": self.current_balance,
                "portfolio_value": portfolio_value,
                "total_value": total_value,
                "drawdown": current_drawdown * 100
            })
            
        except Exception as e:
            logger.error(f"Error updating metrics: {str(e)}")
    
    async def _generate_report(self):
        """Génère un rapport de performance de la simulation"""
        try:
            # Créer un DataFrame pour l'historique des profits
            profit_df = pd.DataFrame(self.profit_history)
            
            # Créer un DataFrame pour l'historique des trades
            trades_df = pd.DataFrame(self.trade_history)
            
            # Calculer les métriques finales
            final_value = profit_df["total_value"].iloc[-1]
            total_return = (final_value / self.initial_balance - 1) * 100
            win_rate = (self.profitable_trades / self.total_trades * 100) if self.total_trades > 0 else 0
            
            # Générer le rapport textuel
            report = f"""
            ===== RAPPORT DE SIMULATION =====
            
            Période: {profit_df["timestamp"].iloc[0]} à {profit_df["timestamp"].iloc[-1]}
            
            PERFORMANCE:
            - Balance initiale: {self.initial_balance:.4f} AVAX
            - Valeur finale: {final_value:.4f} AVAX
            - Rendement total: {total_return:+.2f}%
            - Profit total: {self.total_profit:.4f} AVAX
            
            TRADES:
            - Nombre total de trades: {self.total_trades}
            - Trades profitables: {self.profitable_trades}
            - Taux de réussite: {win_rate:.2f}%
            - Drawdown maximum: {self.max_drawdown*100:.2f}%
            
            STRATÉGIE:
            - Take profit: {(self.take_profit-1)*100:.0f}%
            - Stop loss: {(1-self.stop_loss)*100:.0f}%
            - Temps de détention max: {self.max_hold_time} heures
            
            ================================
            """
            
            logger.info(report)
            
            # Sauvegarder le rapport
            with open(self.results_dir / "simulation_report.txt", "w") as f:
                f.write(report)
            
            # Sauvegarder les données
            profit_df.to_csv(self.results_dir / "profit_history.csv", index=False)
            trades_df.to_csv(self.results_dir / "trade_history.csv", index=False)
            
            # Générer des graphiques
            await self._generate_charts(profit_df, trades_df)
            
        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
    
    async def _generate_charts(self, profit_df: pd.DataFrame, trades_df: pd.DataFrame):
        """Génère des graphiques pour visualiser les résultats"""
        try:
            # Configurer matplotlib
            plt.style.use('ggplot')
            
            # 1. Évolution de la valeur totale
            plt.figure(figsize=(12, 6))
            plt.plot(profit_df["timestamp"], profit_df["total_value"], label="Valeur totale")
            plt.plot(profit_df["timestamp"], profit_df["balance"], label="Balance disponible", linestyle="--")
            plt.plot(profit_df["timestamp"], profit_df["portfolio_value"], label="Valeur du portefeuille", linestyle=":")
            
            # Ajouter une ligne pour la balance initiale
            plt.axhline(y=self.initial_balance, color='r', linestyle='-', alpha=0.3, label="Balance initiale")
            
            plt.title("Évolution de la valeur du portefeuille")
            plt.xlabel("Date")
            plt.ylabel("Valeur (AVAX)")
            plt.legend()
            plt.grid(True)
            plt.tight_layout()
            plt.savefig(self.results_dir / "portfolio_value.png")
            plt.close()
            
            # 2. Drawdown
            plt.figure(figsize=(12, 6))
            plt.plot(profit_df["timestamp"], profit_df["drawdown"])
            plt.title("Drawdown")
            plt.xlabel("Date")
            plt.ylabel("Drawdown (%)")
            plt.grid(True)
            plt.tight_layout()
            plt.savefig(self.results_dir / "drawdown.png")
            plt.close()
            
            # 3. Distribution des profits par trade
            if not trades_df.empty and "profit_loss_pct" in trades_df.columns:
                sell_trades = trades_df[trades_df["type"] == "sell"]
                
                if not sell_trades.empty:
                    plt.figure(figsize=(12, 6))
                    plt.hist(sell_trades["profit_loss_pct"], bins=20, alpha=0.7)
                    plt.title("Distribution des profits par trade")
                    plt.xlabel("Profit/Perte (%)")
                    plt.ylabel("Nombre de trades")
                    plt.grid(True)
                    plt.tight_layout()
                    plt.savefig(self.results_dir / "profit_distribution.png")
                    plt.close()
                    
                    # 4. Profits par raison de vente
                    plt.figure(figsize=(12, 6))
                    reason_profit = sell_trades.groupby("reason")["profit_loss_pct"].mean()
                    reason_count = sell_trades.groupby("reason").size()
                    
                    plt.bar(reason_profit.index, reason_profit.values)
                    
                    # Ajouter le nombre de trades par raison
                    for i, (reason, count) in enumerate(reason_count.items()):
                        plt.text(i, reason_profit[reason] + 1, f"n={count}", ha='center')
                    
                    plt.title("Profit moyen par raison de vente")
                    plt.xlabel("Raison")
                    plt.ylabel("Profit moyen (%)")
                    plt.grid(True)
                    plt.tight_layout()
                    plt.savefig(self.results_dir / "profit_by_reason.png")
                    plt.close()
            
            logger.info(f"Charts generated and saved to {self.results_dir}")
            
        except Exception as e:
            logger.error(f"Error generating charts: {str(e)}")

    async def run_simulation(self):
        """Exécute la simulation complète"""
        logger.info(f"Running simulation with {self.initial_balance} AVAX for {self.simulation_days} days")
        await self.start_simulation()
        logger.info("Simulation completed")

# Fonction globale pour la compatibilité
async def run_simulation(config: Config, db: Database, initial_balance=5.0, simulation_days=7, simulation_speed=100):
    """Fonction pour exécuter la simulation"""
    simulator = TradingSimulator(config, db, initial_balance, simulation_days, simulation_speed)
    await simulator.start_simulation() 