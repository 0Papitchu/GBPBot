#!/usr/bin/env python3
"""
Module de stratégie de base pour le backtesting de GBPBot.

Ce module fournit une classe de base pour implémenter des stratégies de trading
qui peuvent être utilisées avec le système de backtesting.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from abc import ABC, abstractmethod

# Configuration du logger
logger = logging.getLogger(__name__)

class BaseStrategy(ABC):
    """
    Classe de base pour les stratégies de trading.
    
    Cette classe définit l'interface que toutes les stratégies de trading
    doivent implémenter pour être utilisées avec le système de backtesting.
    """
    
    def __init__(self, market_simulator, **kwargs):
        """
        Initialise la stratégie de trading.
        
        Args:
            market_simulator: Simulateur de marché
            **kwargs: Paramètres spécifiques à la stratégie
        """
        self.market_simulator = market_simulator
        self.params = kwargs
        self.name = self.__class__.__name__
        
        # État de la stratégie
        self.positions = {}  # Positions actuelles
        self.orders = {}     # Ordres en cours
        self.trades = []     # Historique des trades
        
        # Initialisation des indicateurs
        self.indicators = {}
        
        logger.info(f"Stratégie {self.name} initialisée avec les paramètres: {kwargs}")
    
    @abstractmethod
    def on_tick(self, timestamp: datetime, symbol: str, data: Dict[str, Any]) -> None:
        """
        Méthode appelée à chaque tick du marché.
        
        Args:
            timestamp: Horodatage du tick
            symbol: Symbole du marché
            data: Données du tick (prix, volume, etc.)
        """
        pass
    
    @abstractmethod
    def on_bar(self, timestamp: datetime, symbol: str, data: pd.DataFrame) -> None:
        """
        Méthode appelée à chaque nouvelle barre (chandelier).
        
        Args:
            timestamp: Horodatage de la barre
            symbol: Symbole du marché
            data: Données de la barre (OHLCV)
        """
        pass
    
    def on_trade(self, trade: Dict[str, Any]) -> None:
        """
        Méthode appelée après l'exécution d'un trade.
        
        Args:
            trade: Informations sur le trade exécuté
        """
        self.trades.append(trade)
        logger.info(f"Trade exécuté: {trade}")
    
    def on_order_update(self, order: Dict[str, Any]) -> None:
        """
        Méthode appelée lors de la mise à jour d'un ordre.
        
        Args:
            order: Informations sur l'ordre mis à jour
        """
        self.orders[order["order_id"]] = order
        logger.debug(f"Ordre mis à jour: {order}")
    
    def on_position_update(self, position: Dict[str, Any]) -> None:
        """
        Méthode appelée lors de la mise à jour d'une position.
        
        Args:
            position: Informations sur la position mise à jour
        """
        self.positions[position["symbol"]] = position
        logger.debug(f"Position mise à jour: {position}")
    
    def place_market_order(self, symbol: str, side: str, quantity: float) -> Dict[str, Any]:
        """
        Place un ordre au marché.
        
        Args:
            symbol: Symbole du marché
            side: Côté de l'ordre ("buy" ou "sell")
            quantity: Quantité à acheter ou vendre
            
        Returns:
            Informations sur l'ordre placé
        """
        order = self.market_simulator.place_order(
            symbol=symbol,
            order_type="market",
            side=side,
            quantity=quantity
        )
        
        self.orders[order["order_id"]] = order
        logger.info(f"Ordre au marché placé: {order}")
        
        return order
    
    def place_limit_order(self, symbol: str, side: str, quantity: float, price: float) -> Dict[str, Any]:
        """
        Place un ordre limite.
        
        Args:
            symbol: Symbole du marché
            side: Côté de l'ordre ("buy" ou "sell")
            quantity: Quantité à acheter ou vendre
            price: Prix limite
            
        Returns:
            Informations sur l'ordre placé
        """
        order = self.market_simulator.place_order(
            symbol=symbol,
            order_type="limit",
            side=side,
            quantity=quantity,
            price=price
        )
        
        self.orders[order["order_id"]] = order
        logger.info(f"Ordre limite placé: {order}")
        
        return order
    
    def cancel_order(self, order_id: str) -> bool:
        """
        Annule un ordre.
        
        Args:
            order_id: ID de l'ordre à annuler
            
        Returns:
            True si l'annulation a réussi, False sinon
        """
        result = self.market_simulator.cancel_order(order_id)
        
        if result:
            if order_id in self.orders:
                del self.orders[order_id]
            logger.info(f"Ordre {order_id} annulé")
        else:
            logger.warning(f"Échec de l'annulation de l'ordre {order_id}")
        
        return result
    
    def get_position(self, symbol: str) -> Dict[str, Any]:
        """
        Récupère la position actuelle pour un symbole.
        
        Args:
            symbol: Symbole du marché
            
        Returns:
            Informations sur la position
        """
        return self.positions.get(symbol, {"symbol": symbol, "quantity": 0.0, "entry_price": 0.0})
    
    def get_balance(self, asset: str) -> float:
        """
        Récupère le solde actuel pour un actif.
        
        Args:
            asset: Actif (devise)
            
        Returns:
            Solde de l'actif
        """
        return self.market_simulator.get_balance(asset)
    
    def get_market_price(self, symbol: str) -> float:
        """
        Récupère le prix actuel du marché pour un symbole.
        
        Args:
            symbol: Symbole du marché
            
        Returns:
            Prix actuel du marché
        """
        return self.market_simulator.get_market_price(symbol)
    
    def get_historical_data(self, symbol: str, timeframe: str, limit: int = 100) -> pd.DataFrame:
        """
        Récupère les données historiques pour un symbole.
        
        Args:
            symbol: Symbole du marché
            timeframe: Intervalle de temps
            limit: Nombre de barres à récupérer
            
        Returns:
            DataFrame des données historiques
        """
        return self.market_simulator.get_historical_data(symbol, timeframe, limit)
    
    def calculate_indicators(self, data: pd.DataFrame) -> Dict[str, pd.Series]:
        """
        Calcule les indicateurs techniques sur les données.
        
        Args:
            data: DataFrame des données
            
        Returns:
            Dictionnaire des indicateurs calculés
        """
        # Cette méthode peut être surchargée par les sous-classes
        return {}
    
    def log_strategy_state(self) -> None:
        """
        Journalise l'état actuel de la stratégie.
        """
        logger.info(f"État de la stratégie {self.name}:")
        logger.info(f"Positions: {self.positions}")
        logger.info(f"Ordres en cours: {self.orders}")
        logger.info(f"Nombre de trades: {len(self.trades)}")


class MovingAverageStrategy(BaseStrategy):
    """
    Stratégie de trading basée sur les moyennes mobiles.
    
    Cette stratégie génère des signaux d'achat lorsque la moyenne mobile courte
    croise au-dessus de la moyenne mobile longue, et des signaux de vente
    lorsque la moyenne mobile courte croise en dessous de la moyenne mobile longue.
    """
    
    def __init__(self, market_simulator, **kwargs):
        """
        Initialise la stratégie de moyennes mobiles.
        
        Args:
            market_simulator: Simulateur de marché
            **kwargs: Paramètres de la stratégie
                - short_window: Fenêtre de la moyenne mobile courte (défaut: 20)
                - long_window: Fenêtre de la moyenne mobile longue (défaut: 50)
                - symbols: Liste des symboles à trader (défaut: [])
                - quantity: Quantité à trader (défaut: 1.0)
        """
        super().__init__(market_simulator, **kwargs)
        
        # Paramètres de la stratégie
        self.short_window = int(kwargs.get("short_window", 20))
        self.long_window = int(kwargs.get("long_window", 50))
        self.symbols = kwargs.get("symbols", [])
        self.quantity = float(kwargs.get("quantity", 1.0))
        
        # État de la stratégie
        self.signals = {}  # Signaux générés
        
        logger.info(f"Stratégie de moyennes mobiles initialisée: court={self.short_window}, long={self.long_window}")
    
    def on_tick(self, timestamp: datetime, symbol: str, data: Dict[str, Any]) -> None:
        """
        Méthode appelée à chaque tick du marché.
        
        Args:
            timestamp: Horodatage du tick
            symbol: Symbole du marché
            data: Données du tick (prix, volume, etc.)
        """
        # Cette stratégie n'utilise pas les ticks, mais seulement les barres
        pass
    
    def on_bar(self, timestamp: datetime, symbol: str, data: pd.DataFrame) -> None:
        """
        Méthode appelée à chaque nouvelle barre (chandelier).
        
        Args:
            timestamp: Horodatage de la barre
            symbol: Symbole du marché
            data: Données de la barre (OHLCV)
        """
        if symbol not in self.symbols:
            return
        
        # Récupérer les données historiques
        historical_data = self.get_historical_data(symbol, "1d", self.long_window + 10)
        
        # Calculer les moyennes mobiles
        if len(historical_data) >= self.long_window:
            short_ma = historical_data["close"].rolling(window=self.short_window).mean()
            long_ma = historical_data["close"].rolling(window=self.long_window).mean()
            
            # Générer les signaux
            signal = 0
            if short_ma.iloc[-1] > long_ma.iloc[-1] and short_ma.iloc[-2] <= long_ma.iloc[-2]:
                signal = 1  # Signal d'achat
            elif short_ma.iloc[-1] < long_ma.iloc[-1] and short_ma.iloc[-2] >= long_ma.iloc[-2]:
                signal = -1  # Signal de vente
            
            # Stocker le signal
            self.signals[symbol] = signal
            
            # Exécuter la stratégie
            self._execute_strategy(timestamp, symbol, signal)
    
    def _execute_strategy(self, timestamp: datetime, symbol: str, signal: int) -> None:
        """
        Exécute la stratégie en fonction du signal.
        
        Args:
            timestamp: Horodatage
            symbol: Symbole du marché
            signal: Signal généré (1: achat, -1: vente, 0: aucun)
        """
        position = self.get_position(symbol)
        current_quantity = position.get("quantity", 0.0)
        
        if signal == 1 and current_quantity <= 0:
            # Signal d'achat et pas de position longue
            logger.info(f"Signal d'achat pour {symbol}")
            
            # Fermer la position courte si elle existe
            if current_quantity < 0:
                self.place_market_order(symbol, "buy", abs(current_quantity))
            
            # Ouvrir une position longue
            self.place_market_order(symbol, "buy", self.quantity)
            
        elif signal == -1 and current_quantity >= 0:
            # Signal de vente et pas de position courte
            logger.info(f"Signal de vente pour {symbol}")
            
            # Fermer la position longue si elle existe
            if current_quantity > 0:
                self.place_market_order(symbol, "sell", current_quantity)
            
            # Ouvrir une position courte
            self.place_market_order(symbol, "sell", self.quantity)


class RSIStrategy(BaseStrategy):
    """
    Stratégie de trading basée sur l'indice de force relative (RSI).
    
    Cette stratégie génère des signaux d'achat lorsque le RSI est en dessous
    du niveau de survente, et des signaux de vente lorsque le RSI est au-dessus
    du niveau de surachat.
    """
    
    def __init__(self, market_simulator, **kwargs):
        """
        Initialise la stratégie RSI.
        
        Args:
            market_simulator: Simulateur de marché
            **kwargs: Paramètres de la stratégie
                - rsi_period: Période du RSI (défaut: 14)
                - oversold: Niveau de survente (défaut: 30)
                - overbought: Niveau de surachat (défaut: 70)
                - symbols: Liste des symboles à trader (défaut: [])
                - quantity: Quantité à trader (défaut: 1.0)
        """
        super().__init__(market_simulator, **kwargs)
        
        # Paramètres de la stratégie
        self.rsi_period = int(kwargs.get("rsi_period", 14))
        self.oversold = float(kwargs.get("oversold", 30))
        self.overbought = float(kwargs.get("overbought", 70))
        self.symbols = kwargs.get("symbols", [])
        self.quantity = float(kwargs.get("quantity", 1.0))
        
        # État de la stratégie
        self.rsi_values = {}  # Valeurs RSI
        self.signals = {}     # Signaux générés
        
        logger.info(f"Stratégie RSI initialisée: période={self.rsi_period}, survente={self.oversold}, surachat={self.overbought}")
    
    def on_tick(self, timestamp: datetime, symbol: str, data: Dict[str, Any]) -> None:
        """
        Méthode appelée à chaque tick du marché.
        
        Args:
            timestamp: Horodatage du tick
            symbol: Symbole du marché
            data: Données du tick (prix, volume, etc.)
        """
        # Cette stratégie n'utilise pas les ticks, mais seulement les barres
        pass
    
    def on_bar(self, timestamp: datetime, symbol: str, data: pd.DataFrame) -> None:
        """
        Méthode appelée à chaque nouvelle barre (chandelier).
        
        Args:
            timestamp: Horodatage de la barre
            symbol: Symbole du marché
            data: Données de la barre (OHLCV)
        """
        if symbol not in self.symbols:
            return
        
        # Récupérer les données historiques
        historical_data = self.get_historical_data(symbol, "1d", self.rsi_period + 50)
        
        # Calculer le RSI
        if len(historical_data) >= self.rsi_period + 1:
            rsi = self._calculate_rsi(historical_data["close"], self.rsi_period)
            
            # Stocker la valeur RSI
            self.rsi_values[symbol] = rsi.iloc[-1]
            
            # Générer les signaux
            signal = 0
            if rsi.iloc[-1] < self.oversold and rsi.iloc[-2] >= self.oversold:
                signal = 1  # Signal d'achat (RSI sort de la zone de survente)
            elif rsi.iloc[-1] > self.overbought and rsi.iloc[-2] <= self.overbought:
                signal = -1  # Signal de vente (RSI entre dans la zone de surachat)
            
            # Stocker le signal
            self.signals[symbol] = signal
            
            # Exécuter la stratégie
            self._execute_strategy(timestamp, symbol, signal)
    
    def _calculate_rsi(self, prices: pd.Series, period: int) -> pd.Series:
        """
        Calcule l'indice de force relative (RSI).
        
        Args:
            prices: Série des prix
            period: Période du RSI
            
        Returns:
            Série des valeurs RSI
        """
        # Calculer les variations de prix
        delta = prices.diff()
        
        # Séparer les variations positives et négatives
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        # Calculer la moyenne mobile des gains et des pertes
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        # Calculer le ratio
        rs = avg_gain / avg_loss
        
        # Calculer le RSI
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    
    def _execute_strategy(self, timestamp: datetime, symbol: str, signal: int) -> None:
        """
        Exécute la stratégie en fonction du signal.
        
        Args:
            timestamp: Horodatage
            symbol: Symbole du marché
            signal: Signal généré (1: achat, -1: vente, 0: aucun)
        """
        position = self.get_position(symbol)
        current_quantity = position.get("quantity", 0.0)
        
        if signal == 1 and current_quantity <= 0:
            # Signal d'achat et pas de position longue
            logger.info(f"Signal d'achat pour {symbol} (RSI = {self.rsi_values.get(symbol, 0):.2f})")
            
            # Fermer la position courte si elle existe
            if current_quantity < 0:
                self.place_market_order(symbol, "buy", abs(current_quantity))
            
            # Ouvrir une position longue
            self.place_market_order(symbol, "buy", self.quantity)
            
        elif signal == -1 and current_quantity >= 0:
            # Signal de vente et pas de position courte
            logger.info(f"Signal de vente pour {symbol} (RSI = {self.rsi_values.get(symbol, 0):.2f})")
            
            # Fermer la position longue si elle existe
            if current_quantity > 0:
                self.place_market_order(symbol, "sell", current_quantity)
            
            # Ouvrir une position courte
            self.place_market_order(symbol, "sell", self.quantity) 