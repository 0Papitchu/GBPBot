#!/usr/bin/env python3
"""
Module de simulation de marché pour le backtesting de GBPBot.

Ce module fournit des fonctionnalités pour simuler les conditions de marché
et exécuter des stratégies de trading dans un environnement contrôlé.
"""

import os
import json
import time
import logging
import asyncio
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from datetime import datetime, timedelta
from decimal import Decimal

from gbpbot.utils.config import get_config
from gbpbot.utils.exceptions import ConfigurationError

# Configuration du logger
logger = logging.getLogger(__name__)

class MarketSimulator:
    """
    Classe pour simuler les conditions de marché pour le backtesting.
    
    Cette classe fournit des méthodes pour simuler l'exécution d'ordres,
    le calcul de slippage, les frais de transaction, et d'autres aspects
    du trading en conditions réelles.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialise le simulateur de marché.
        
        Args:
            config: Configuration pour le simulateur de marché
        """
        self.config = config
        
        # Paramètres de simulation
        self.slippage_model = config.get("SLIPPAGE_MODEL", "fixed")
        self.fixed_slippage = float(config.get("FIXED_SLIPPAGE", 0.001))  # 0.1% par défaut
        self.maker_fee = float(config.get("MAKER_FEE", 0.001))  # 0.1% par défaut
        self.taker_fee = float(config.get("TAKER_FEE", 0.002))  # 0.2% par défaut
        self.latency = int(config.get("LATENCY_MS", 500))  # Latence en millisecondes
        self.execution_probability = float(config.get("EXECUTION_PROBABILITY", 0.99))  # 99% par défaut
        self.price_impact_factor = float(config.get("PRICE_IMPACT_FACTOR", 0.0001))  # Facteur d'impact sur le prix
        self.realistic_fills = config.get("REALISTIC_FILLS", "true").lower() == "true"
        self.partial_fills = config.get("PARTIAL_FILLS", "true").lower() == "true"
        self.max_partial_fills = int(config.get("MAX_PARTIAL_FILLS", 3))
        
        # État du simulateur
        self.current_timestamp = None
        self.balances = {}
        self.open_orders = []
        self.filled_orders = []
        self.canceled_orders = []
        self.order_id_counter = 0
        
        # Données de marché
        self.market_data = {}
        self.order_books = {}
        
        logger.info("Simulateur de marché initialisé")
    
    def initialize_balance(self, asset: str, amount: float):
        """
        Initialise le solde d'un actif.
        
        Args:
            asset: Nom de l'actif
            amount: Montant initial
        """
        self.balances[asset] = amount
        logger.info(f"Solde initialisé: {amount} {asset}")
    
    def initialize_balances(self, balances: Dict[str, float]):
        """
        Initialise les soldes de plusieurs actifs.
        
        Args:
            balances: Dictionnaire des soldes initiaux
        """
        self.balances.update(balances)
        logger.info(f"Soldes initialisés: {balances}")
    
    def get_balance(self, asset: str) -> float:
        """
        Récupère le solde d'un actif.
        
        Args:
            asset: Nom de l'actif
            
        Returns:
            Solde de l'actif
        """
        return self.balances.get(asset, 0.0)
    
    def load_market_data(self, symbol: str, data: pd.DataFrame):
        """
        Charge des données de marché pour un symbole.
        
        Args:
            symbol: Symbole du marché
            data: DataFrame contenant les données OHLCV
        """
        self.market_data[symbol] = data
        logger.info(f"Données de marché chargées pour {symbol}: {len(data)} points")
    
    def load_order_book(self, symbol: str, data: Dict[str, Any]):
        """
        Charge un carnet d'ordres pour un symbole.
        
        Args:
            symbol: Symbole du marché
            data: Données du carnet d'ordres
        """
        self.order_books[symbol] = data
        logger.info(f"Carnet d'ordres chargé pour {symbol}")
    
    def set_current_timestamp(self, timestamp: Union[int, datetime]):
        """
        Définit le timestamp courant pour la simulation.
        
        Args:
            timestamp: Timestamp à définir
        """
        if isinstance(timestamp, datetime):
            self.current_timestamp = timestamp
        else:
            self.current_timestamp = datetime.fromtimestamp(timestamp / 1000)
        
        logger.debug(f"Timestamp courant défini: {self.current_timestamp}")
    
    def get_current_price(self, symbol: str) -> float:
        """
        Récupère le prix actuel d'un symbole.
        
        Args:
            symbol: Symbole du marché
            
        Returns:
            Prix actuel
        """
        if symbol not in self.market_data:
            raise ValueError(f"Données de marché non disponibles pour {symbol}")
        
        # Trouver la ligne correspondant au timestamp courant
        df = self.market_data[symbol]
        
        # Si le timestamp est exactement dans l'index, utiliser cette ligne
        if self.current_timestamp in df.index:
            return df.loc[self.current_timestamp, "close"]
        
        # Sinon, trouver la ligne la plus proche
        idx = df.index.get_indexer([self.current_timestamp], method="nearest")[0]
        if idx < 0 or idx >= len(df):
            raise ValueError(f"Timestamp {self.current_timestamp} hors des limites des données")
        
        return df.iloc[idx]["close"]
    
    def get_ohlcv(self, symbol: str) -> Dict[str, float]:
        """
        Récupère les données OHLCV actuelles d'un symbole.
        
        Args:
            symbol: Symbole du marché
            
        Returns:
            Données OHLCV
        """
        if symbol not in self.market_data:
            raise ValueError(f"Données de marché non disponibles pour {symbol}")
        
        # Trouver la ligne correspondant au timestamp courant
        df = self.market_data[symbol]
        
        # Si le timestamp est exactement dans l'index, utiliser cette ligne
        if self.current_timestamp in df.index:
            row = df.loc[self.current_timestamp]
        else:
            # Sinon, trouver la ligne la plus proche
            idx = df.index.get_indexer([self.current_timestamp], method="nearest")[0]
            if idx < 0 or idx >= len(df):
                raise ValueError(f"Timestamp {self.current_timestamp} hors des limites des données")
            row = df.iloc[idx]
        
        return {
            "open": row["open"],
            "high": row["high"],
            "low": row["low"],
            "close": row["close"],
            "volume": row["volume"],
            "timestamp": self.current_timestamp
        }
    
    def place_order(self, symbol: str, side: str, order_type: str, 
                   amount: float, price: Optional[float] = None) -> Dict[str, Any]:
        """
        Place un ordre simulé.
        
        Args:
            symbol: Symbole du marché
            side: Côté de l'ordre ("buy" ou "sell")
            order_type: Type d'ordre ("limit" ou "market")
            amount: Quantité à acheter/vendre
            price: Prix pour les ordres limit
            
        Returns:
            Informations sur l'ordre placé
        """
        # Vérifier les paramètres
        if side not in ["buy", "sell"]:
            raise ValueError(f"Côté d'ordre invalide: {side}")
        
        if order_type not in ["limit", "market"]:
            raise ValueError(f"Type d'ordre invalide: {order_type}")
        
        if order_type == "limit" and price is None:
            raise ValueError("Le prix est requis pour les ordres limit")
        
        # Générer un ID d'ordre
        self.order_id_counter += 1
        order_id = f"sim_{self.order_id_counter}"
        
        # Créer l'ordre
        order = {
            "id": order_id,
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "amount": amount,
            "price": price if order_type == "limit" else self.get_current_price(symbol),
            "status": "open",
            "timestamp": self.current_timestamp,
            "filled": 0.0,
            "remaining": amount,
            "cost": 0.0,
            "fee": 0.0
        }
        
        # Ajouter l'ordre à la liste des ordres ouverts
        self.open_orders.append(order)
        
        logger.info(f"Ordre placé: {order_id} {side} {order_type} {amount} {symbol} @ {price}")
        
        # Si c'est un ordre market, l'exécuter immédiatement
        if order_type == "market":
            self._execute_order(order_id)
        
        return order
    
    def cancel_order(self, order_id: str) -> bool:
        """
        Annule un ordre simulé.
        
        Args:
            order_id: ID de l'ordre à annuler
            
        Returns:
            True si l'annulation a réussi, False sinon
        """
        # Trouver l'ordre
        order_idx = None
        for i, order in enumerate(self.open_orders):
            if order["id"] == order_id:
                order_idx = i
                break
        
        if order_idx is None:
            logger.warning(f"Ordre {order_id} non trouvé pour annulation")
            return False
        
        # Annuler l'ordre
        order = self.open_orders.pop(order_idx)
        order["status"] = "canceled"
        self.canceled_orders.append(order)
        
        logger.info(f"Ordre {order_id} annulé")
        
        return True
    
    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère les informations sur un ordre.
        
        Args:
            order_id: ID de l'ordre
            
        Returns:
            Informations sur l'ordre ou None si non trouvé
        """
        # Chercher dans les ordres ouverts
        for order in self.open_orders:
            if order["id"] == order_id:
                return order
        
        # Chercher dans les ordres exécutés
        for order in self.filled_orders:
            if order["id"] == order_id:
                return order
        
        # Chercher dans les ordres annulés
        for order in self.canceled_orders:
            if order["id"] == order_id:
                return order
        
        logger.warning(f"Ordre {order_id} non trouvé")
        return None
    
    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Récupère la liste des ordres ouverts.
        
        Args:
            symbol: Filtrer par symbole (optionnel)
            
        Returns:
            Liste des ordres ouverts
        """
        if symbol:
            return [order for order in self.open_orders if order["symbol"] == symbol]
        return self.open_orders
    
    def process_orders(self):
        """
        Traite les ordres ouverts en fonction des conditions de marché actuelles.
        """
        # Copier la liste des ordres ouverts pour éviter les problèmes de modification pendant l'itération
        open_orders = self.open_orders.copy()
        
        for order in open_orders:
            # Vérifier si l'ordre peut être exécuté
            if order["type"] == "limit":
                current_price = self.get_current_price(order["symbol"])
                
                # Pour les ordres d'achat, le prix doit être supérieur ou égal au prix de l'ordre
                if order["side"] == "buy" and current_price <= order["price"]:
                    self._execute_order(order["id"])
                
                # Pour les ordres de vente, le prix doit être inférieur ou égal au prix de l'ordre
                elif order["side"] == "sell" and current_price >= order["price"]:
                    self._execute_order(order["id"])
    
    def advance_time(self, delta: Union[timedelta, int]):
        """
        Avance le temps de simulation.
        
        Args:
            delta: Durée à avancer (timedelta ou secondes)
        """
        if isinstance(delta, int):
            delta = timedelta(seconds=delta)
        
        self.current_timestamp += delta
        logger.debug(f"Temps avancé à {self.current_timestamp}")
        
        # Traiter les ordres avec le nouveau timestamp
        self.process_orders()
    
    def run_simulation(self, start_time: datetime, end_time: datetime, 
                      time_step: timedelta, callback: Optional[Callable] = None):
        """
        Exécute une simulation complète sur une période donnée.
        
        Args:
            start_time: Heure de début
            end_time: Heure de fin
            time_step: Pas de temps
            callback: Fonction de rappel à appeler à chaque pas de temps
        """
        # Initialiser le timestamp courant
        self.set_current_timestamp(start_time)
        
        # Boucle principale de simulation
        while self.current_timestamp <= end_time:
            # Traiter les ordres
            self.process_orders()
            
            # Appeler la fonction de rappel si fournie
            if callback:
                callback(self)
            
            # Avancer le temps
            self.advance_time(time_step)
        
        logger.info(f"Simulation terminée: {start_time} -> {end_time}")
    
    def calculate_pnl(self, initial_balances: Dict[str, float]) -> Dict[str, float]:
        """
        Calcule le profit/perte de la simulation.
        
        Args:
            initial_balances: Soldes initiaux
            
        Returns:
            Profit/perte pour chaque actif
        """
        pnl = {}
        
        for asset, initial_balance in initial_balances.items():
            current_balance = self.get_balance(asset)
            pnl[asset] = current_balance - initial_balance
        
        return pnl
    
    def _execute_order(self, order_id: str):
        """
        Exécute un ordre simulé.
        
        Args:
            order_id: ID de l'ordre à exécuter
        """
        # Trouver l'ordre
        order_idx = None
        for i, order in enumerate(self.open_orders):
            if order["id"] == order_id:
                order_idx = i
                break
        
        if order_idx is None:
            logger.warning(f"Ordre {order_id} non trouvé pour exécution")
            return
        
        # Récupérer l'ordre
        order = self.open_orders[order_idx]
        
        # Vérifier si l'ordre a une chance d'être exécuté (probabilité d'exécution)
        if np.random.random() > self.execution_probability:
            logger.info(f"Ordre {order_id} non exécuté (probabilité)")
            return
        
        # Calculer le prix d'exécution avec slippage
        execution_price = self._calculate_execution_price(order)
        
        # Calculer la quantité à exécuter
        if self.realistic_fills and self.partial_fills and np.random.random() < 0.3:
            # Exécution partielle
            fill_ratio = np.random.uniform(0.1, 0.9)
            fill_amount = order["remaining"] * fill_ratio
        else:
            # Exécution complète
            fill_amount = order["remaining"]
        
        # Calculer le coût et les frais
        cost = fill_amount * execution_price
        fee = cost * self.taker_fee
        
        # Mettre à jour l'ordre
        order["filled"] += fill_amount
        order["remaining"] -= fill_amount
        order["cost"] += cost
        order["fee"] += fee
        
        # Mettre à jour les soldes
        if order["side"] == "buy":
            # Vérifier si l'utilisateur a assez de fonds
            quote_asset = order["symbol"].split("/")[1]
            base_asset = order["symbol"].split("/")[0]
            
            if self.get_balance(quote_asset) < cost + fee:
                logger.warning(f"Fonds insuffisants pour exécuter l'ordre {order_id}")
                return
            
            # Déduire le coût et les frais
            self.balances[quote_asset] = self.get_balance(quote_asset) - cost - fee
            
            # Ajouter les tokens achetés
            self.balances[base_asset] = self.get_balance(base_asset) + fill_amount
            
        else:  # sell
            # Vérifier si l'utilisateur a assez de tokens
            base_asset = order["symbol"].split("/")[0]
            quote_asset = order["symbol"].split("/")[1]
            
            if self.get_balance(base_asset) < fill_amount:
                logger.warning(f"Tokens insuffisants pour exécuter l'ordre {order_id}")
                return
            
            # Déduire les tokens vendus
            self.balances[base_asset] = self.get_balance(base_asset) - fill_amount
            
            # Ajouter le produit de la vente moins les frais
            self.balances[quote_asset] = self.get_balance(quote_asset) + cost - fee
        
        # Si l'ordre est complètement exécuté, le déplacer vers les ordres exécutés
        if order["remaining"] <= 0:
            order["status"] = "closed"
            self.open_orders.pop(order_idx)
            self.filled_orders.append(order)
            logger.info(f"Ordre {order_id} exécuté complètement: {fill_amount} @ {execution_price}")
        else:
            logger.info(f"Ordre {order_id} exécuté partiellement: {fill_amount} @ {execution_price}")
    
    def _calculate_execution_price(self, order: Dict[str, Any]) -> float:
        """
        Calcule le prix d'exécution avec slippage.
        
        Args:
            order: Ordre à exécuter
            
        Returns:
            Prix d'exécution
        """
        base_price = order["price"]
        
        # Appliquer le slippage en fonction du modèle
        if self.slippage_model == "fixed":
            # Slippage fixe
            if order["side"] == "buy":
                execution_price = base_price * (1 + self.fixed_slippage)
            else:  # sell
                execution_price = base_price * (1 - self.fixed_slippage)
                
        elif self.slippage_model == "variable":
            # Slippage variable en fonction de la taille de l'ordre
            impact = self.price_impact_factor * order["amount"]
            if order["side"] == "buy":
                execution_price = base_price * (1 + impact)
            else:  # sell
                execution_price = base_price * (1 - impact)
                
        elif self.slippage_model == "orderbook":
            # Slippage basé sur le carnet d'ordres
            if order["symbol"] in self.order_books:
                execution_price = self._calculate_orderbook_execution_price(order)
            else:
                # Fallback sur le slippage fixe
                if order["side"] == "buy":
                    execution_price = base_price * (1 + self.fixed_slippage)
                else:  # sell
                    execution_price = base_price * (1 - self.fixed_slippage)
        else:
            # Modèle non reconnu, pas de slippage
            execution_price = base_price
        
        return execution_price
    
    def _calculate_orderbook_execution_price(self, order: Dict[str, Any]) -> float:
        """
        Calcule le prix d'exécution basé sur le carnet d'ordres.
        
        Args:
            order: Ordre à exécuter
            
        Returns:
            Prix d'exécution
        """
        symbol = order["symbol"]
        amount = order["amount"]
        side = order["side"]
        
        # Récupérer le carnet d'ordres
        order_book = self.order_books[symbol]
        
        if side == "buy":
            # Pour un achat, on utilise les asks (offres de vente)
            book_side = order_book["asks"]
        else:  # sell
            # Pour une vente, on utilise les bids (offres d'achat)
            book_side = order_book["bids"]
        
        # Calculer le prix moyen pondéré
        remaining = amount
        total_cost = 0.0
        
        for price, size in book_side:
            if remaining <= 0:
                break
                
            # Quantité à prendre à ce niveau de prix
            take = min(remaining, size)
            
            # Ajouter au coût total
            total_cost += take * price
            
            # Mettre à jour la quantité restante
            remaining -= take
        
        # S'il reste de la quantité, utiliser le dernier prix
        if remaining > 0:
            total_cost += remaining * book_side[-1][0]
        
        # Calculer le prix moyen
        avg_price = total_cost / amount
        
        return avg_price
    
    def get_simulation_summary(self) -> Dict[str, Any]:
        """
        Génère un résumé de la simulation.
        
        Returns:
            Résumé de la simulation
        """
        return {
            "start_time": self.market_data[list(self.market_data.keys())[0]].index[0],
            "end_time": self.current_timestamp,
            "balances": self.balances,
            "filled_orders": len(self.filled_orders),
            "canceled_orders": len(self.canceled_orders),
            "open_orders": len(self.open_orders),
            "total_volume": sum(order["cost"] for order in self.filled_orders),
            "total_fees": sum(order["fee"] for order in self.filled_orders)
        } 