#!/usr/bin/env python3
"""
Module de continuous learning pour GBPBot

Ce module implémente un système basique d'apprentissage continu pour GBPBot.
Il enregistre les résultats des trades, analyse ces données et ajuste
les paramètres de trading selon les performances passées.
Conçu pour fonctionner sur une configuration modeste (i5-12400F, RTX 3060, 16Go RAM).
"""

import os
import time
import logging
import sqlite3
from typing import Any, Dict, Optional, List
from pathlib import Path
from dataclasses import dataclass, asdict

from gbpbot.utils.logger import setup_logger

logger = setup_logger("continuous_learning", logging.INFO)

# Définir le nom de la base de données
DATABASE_NAME = "continuous_learning.db"

@dataclass
class TradeRecord:
    """Représente un enregistrement de trade."""
    trade_id: Optional[int]  # ID auto-incrémenté dans la base
    symbol: str              # Nom du token
    trade_type: str          # 'buy' ou 'sell'
    quantity: float          # Quantité échangée
    price: float             # Prix au moment du trade
    profit: float            # Profit (positif) ou perte (négatif)
    timestamp: float         # Timestamp du trade

class ContinuousLearning:
    """
    Système d'apprentissage continu pour ajuster les stratégies de trading.
    
    Ce module stocke les résultats des trades dans une base de données SQLite,
    puis analyse ces données pour ajuster des paramètres de trading.
    """

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or os.path.join(str(Path.home()), ".gbpbot", DATABASE_NAME)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialise la base de données pour stocker les enregistrements de trades."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS trades (
                trade_id INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol TEXT NOT NULL,
                trade_type TEXT NOT NULL,
                quantity REAL NOT NULL,
                price REAL NOT NULL,
                profit REAL NOT NULL,
                timestamp REAL NOT NULL
            )
            ''')
            conn.commit()
            conn.close()
            logger.info("Base de données d'apprentissage continu initialisée.")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de la base de données: {e}")

    def record_trade(self, trade: TradeRecord) -> None:
        """Enregistre un trade dans la base de données."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
            INSERT INTO trades (symbol, trade_type, quantity, price, profit, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            ''', (trade.symbol, trade.trade_type, trade.quantity, trade.price, trade.profit, trade.timestamp))
            conn.commit()
            conn.close()
            logger.info(f"Trade enregistré: {trade.symbol} {trade.trade_type} {trade.quantity} au prix {trade.price}, profit: {trade.profit}")
        except Exception as e:
            logger.error(f"Erreur lors de l'enregistrement du trade: {e}")

    def get_trade_history(self, symbol: Optional[str] = None) -> List[TradeRecord]:
        """Récupère l'historique des trades, éventuellement filtré par symbole."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            if symbol:
                cursor.execute("SELECT trade_id, symbol, trade_type, quantity, price, profit, timestamp FROM trades WHERE symbol = ?", (symbol,))
            else:
                cursor.execute("SELECT trade_id, symbol, trade_type, quantity, price, profit, timestamp FROM trades")
            rows = cursor.fetchall()
            conn.close()
            return [TradeRecord(*row) for row in rows]
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'historique des trades: {e}")
            return []

    def analyze_performance(self) -> Dict[str, Any]:
        """Analyse les trades enregistrés pour déterminer les performances."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*), SUM(profit), AVG(profit) FROM trades")
            count, total_profit, avg_profit = cursor.fetchone()
            conn.close()
            metrics = {
                "total_trades": count,
                "total_profit": total_profit if total_profit is not None else 0.0,
                "average_profit": avg_profit if avg_profit is not None else 0.0
            }
            logger.info(f"Analyse de performance: {metrics}")
            return metrics
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse des performances: {e}")
            return {}

    def update_parameters(self) -> Dict[str, Any]:
        """Analyse les performances et ajuste certains paramètres de trading.
        
        Returns:
            Un dictionnaire contenant les nouveaux paramètres recommandés.
        """
        metrics = self.analyze_performance()
        # Si le profit moyen est négatif, recommander une approche plus conservatrice
        if metrics.get("average_profit", 0.0) < 0:
            new_params = {"risk_adjustment": 0.8, "trade_threshold": 0.95}
        else:
            new_params = {"risk_adjustment": 1.0, "trade_threshold": 1.05}
        logger.info(f"Nouveaux paramètres recommandés: {new_params}")
        return new_params

# Instance singleton pour une utilisation globale
_continuous_learning_instance: Optional[ContinuousLearning] = None

def get_continuous_learning() -> ContinuousLearning:
    """Récupère l'instance singleton du système d'apprentissage continu."""
    global _continuous_learning_instance
    if _continuous_learning_instance is None:
        _continuous_learning_instance = ContinuousLearning()
    return _continuous_learning_instance

if __name__ == "__main__":
    # Exemple d'utilisation
    cl = get_continuous_learning()
    
    # Enregistrer un trade fictif
    record = TradeRecord(
        trade_id=None,
        symbol="MEME",
        trade_type="buy",
        quantity=1000.0,
        price=0.001,
        profit=-20.0,
        timestamp=time.time()
    )
    cl.record_trade(record)
    
    # Récupérer et afficher l'historique des trades
    history = cl.get_trade_history()
    print("Historique des trades:")
    for trade in history:
        print(trade)
    
    # Analyser les performances
    performance = cl.analyze_performance()
    print("Performances:", performance)
    
    # Mettre à jour et afficher les paramètres recommandés
    new_params = cl.update_parameters()
    print("Nouveaux paramètres:", new_params) 