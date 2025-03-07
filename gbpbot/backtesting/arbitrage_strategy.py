#!/usr/bin/env python3
"""
Module de stratégie d'arbitrage pour le backtesting de GBPBot.

Ce module fournit des stratégies d'arbitrage qui peuvent être utilisées
avec le système de backtesting pour tester et optimiser les stratégies
d'arbitrage entre différents marchés.
"""

import logging
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from gbpbot.backtesting.base_strategy import BaseStrategy

# Configuration du logger
logger = logging.getLogger(__name__)

class SimpleArbitrageStrategy(BaseStrategy):
    """
    Stratégie d'arbitrage simple entre deux marchés.
    
    Cette stratégie surveille les écarts de prix entre deux marchés pour le même actif
    et exécute des opérations d'arbitrage lorsque l'écart dépasse un seuil défini.
    """
    
    def __init__(self, market_simulator, **kwargs):
        """
        Initialise la stratégie d'arbitrage simple.
        
        Args:
            market_simulator: Simulateur de marché
            **kwargs: Paramètres de la stratégie
                - symbol: Symbole à trader (ex: "BTC/USDT")
                - market_a: Premier marché (ex: "binance")
                - market_b: Deuxième marché (ex: "kucoin")
                - min_spread_pct: Écart minimum en pourcentage pour déclencher l'arbitrage (défaut: 0.5)
                - trade_size: Taille de l'opération en unités de base (défaut: 0.1)
                - max_position: Position maximale autorisée (défaut: 1.0)
                - cooldown_minutes: Temps d'attente entre les opérations (défaut: 5)
        """
        super().__init__(market_simulator, **kwargs)
        
        # Paramètres de la stratégie
        self.symbol = kwargs.get("symbol", "BTC/USDT")
        self.market_a = kwargs.get("market_a", "binance")
        self.market_b = kwargs.get("market_b", "kucoin")
        self.min_spread_pct = float(kwargs.get("min_spread_pct", 0.5))
        self.trade_size = float(kwargs.get("trade_size", 0.1))
        self.max_position = float(kwargs.get("max_position", 1.0))
        self.cooldown_minutes = int(kwargs.get("cooldown_minutes", 5))
        
        # État de la stratégie
        self.last_trade_time = None
        self.current_position_a = 0.0
        self.current_position_b = 0.0
        self.opportunities = []
        
        # Symboles complets pour chaque marché
        self.symbol_a = f"{self.market_a}:{self.symbol}"
        self.symbol_b = f"{self.market_b}:{self.symbol}"
        
        logger.info(f"Stratégie d'arbitrage simple initialisée: {self.symbol} entre {self.market_a} et {self.market_b}")
        logger.info(f"Écart minimum: {self.min_spread_pct}%, Taille de trade: {self.trade_size}, Position max: {self.max_position}")
    
    def on_tick(self, timestamp: datetime, symbol: str, data: Dict[str, Any]) -> None:
        """
        Méthode appelée à chaque tick du marché.
        
        Args:
            timestamp: Horodatage du tick
            symbol: Symbole du marché
            data: Données du tick (prix, volume, etc.)
        """
        # Cette stratégie utilise les ticks pour détecter les opportunités d'arbitrage
        if symbol not in [self.symbol_a, self.symbol_b]:
            return
        
        # Vérifier si nous avons les prix pour les deux marchés
        price_a = self.get_market_price(self.symbol_a)
        price_b = self.get_market_price(self.symbol_b)
        
        if price_a is None or price_b is None:
            return
        
        # Calculer l'écart de prix
        spread_pct = abs(price_a - price_b) / min(price_a, price_b) * 100
        
        # Enregistrer l'opportunité
        opportunity = {
            "timestamp": timestamp,
            "symbol": self.symbol,
            "market_a": self.market_a,
            "market_b": self.market_b,
            "price_a": price_a,
            "price_b": price_b,
            "spread_pct": spread_pct
        }
        self.opportunities.append(opportunity)
        
        # Vérifier si l'écart est suffisant pour l'arbitrage
        if spread_pct >= self.min_spread_pct:
            # Vérifier le temps de recharge
            if self.last_trade_time is not None:
                cooldown = timestamp - self.last_trade_time
                if cooldown.total_seconds() < self.cooldown_minutes * 60:
                    return
            
            # Exécuter l'arbitrage
            self._execute_arbitrage(timestamp, price_a, price_b)
    
    def on_bar(self, timestamp: datetime, symbol: str, data: pd.DataFrame) -> None:
        """
        Méthode appelée à chaque nouvelle barre (chandelier).
        
        Args:
            timestamp: Horodatage de la barre
            symbol: Symbole du marché
            data: Données de la barre (OHLCV)
        """
        # Cette stratégie n'utilise pas les barres, mais seulement les ticks
        pass
    
    def _execute_arbitrage(self, timestamp: datetime, price_a: float, price_b: float) -> None:
        """
        Exécute une opération d'arbitrage.
        
        Args:
            timestamp: Horodatage
            price_a: Prix sur le marché A
            price_b: Prix sur le marché B
        """
        # Déterminer la direction de l'arbitrage
        if price_a < price_b:
            # Acheter sur A, vendre sur B
            buy_market = self.market_a
            sell_market = self.market_b
            buy_price = price_a
            sell_price = price_b
            buy_symbol = self.symbol_a
            sell_symbol = self.symbol_b
        else:
            # Acheter sur B, vendre sur A
            buy_market = self.market_b
            sell_market = self.market_a
            buy_price = price_b
            sell_price = price_a
            buy_symbol = self.symbol_b
            sell_symbol = self.symbol_a
        
        # Calculer la taille de l'opération en fonction des positions actuelles
        buy_size = min(self.trade_size, self.max_position - self.current_position_a)
        sell_size = min(self.trade_size, self.max_position - abs(self.current_position_b))
        trade_size = min(buy_size, sell_size)
        
        if trade_size <= 0:
            logger.info(f"Opportunité d'arbitrage détectée mais position maximale atteinte")
            return
        
        # Exécuter les ordres
        logger.info(f"Exécution d'arbitrage: Achat sur {buy_market} à {buy_price}, Vente sur {sell_market} à {sell_price}")
        logger.info(f"Écart: {((sell_price - buy_price) / buy_price * 100):.2f}%, Taille: {trade_size}")
        
        # Placer les ordres
        buy_order = self.place_market_order(buy_symbol, "buy", trade_size)
        sell_order = self.place_market_order(sell_symbol, "sell", trade_size)
        
        # Mettre à jour l'état
        if buy_market == self.market_a:
            self.current_position_a += trade_size
            self.current_position_b -= trade_size
        else:
            self.current_position_a -= trade_size
            self.current_position_b += trade_size
        
        self.last_trade_time = timestamp
        
        # Enregistrer l'opération d'arbitrage
        arbitrage_trade = {
            "timestamp": timestamp,
            "symbol": self.symbol,
            "buy_market": buy_market,
            "sell_market": sell_market,
            "buy_price": buy_price,
            "sell_price": sell_price,
            "spread_pct": ((sell_price - buy_price) / buy_price * 100),
            "trade_size": trade_size,
            "profit": (sell_price - buy_price) * trade_size
        }
        
        logger.info(f"Arbitrage exécuté: {arbitrage_trade}")


class TriangularArbitrageStrategy(BaseStrategy):
    """
    Stratégie d'arbitrage triangulaire sur un seul marché.
    
    Cette stratégie surveille les opportunités d'arbitrage triangulaire entre trois paires
    de trading (ex: BTC/USDT, ETH/BTC, ETH/USDT) et exécute des opérations lorsque
    l'écart est suffisant.
    """
    
    def __init__(self, market_simulator, **kwargs):
        """
        Initialise la stratégie d'arbitrage triangulaire.
        
        Args:
            market_simulator: Simulateur de marché
            **kwargs: Paramètres de la stratégie
                - market: Marché à utiliser (ex: "binance")
                - base_asset: Actif de base (ex: "USDT")
                - asset1: Premier actif (ex: "BTC")
                - asset2: Deuxième actif (ex: "ETH")
                - min_profit_pct: Profit minimum en pourcentage pour déclencher l'arbitrage (défaut: 0.5)
                - trade_size: Taille de l'opération en unités de base (défaut: 100)
                - cooldown_minutes: Temps d'attente entre les opérations (défaut: 5)
        """
        super().__init__(market_simulator, **kwargs)
        
        # Paramètres de la stratégie
        self.market = kwargs.get("market", "binance")
        self.base_asset = kwargs.get("base_asset", "USDT")
        self.asset1 = kwargs.get("asset1", "BTC")
        self.asset2 = kwargs.get("asset2", "ETH")
        self.min_profit_pct = float(kwargs.get("min_profit_pct", 0.5))
        self.trade_size = float(kwargs.get("trade_size", 100))
        self.cooldown_minutes = int(kwargs.get("cooldown_minutes", 5))
        
        # Paires de trading
        self.pair1 = f"{self.asset1}/{self.base_asset}"  # BTC/USDT
        self.pair2 = f"{self.asset2}/{self.asset1}"      # ETH/BTC
        self.pair3 = f"{self.asset2}/{self.base_asset}"  # ETH/USDT
        
        # Symboles complets pour le marché
        self.symbol1 = f"{self.market}:{self.pair1}"
        self.symbol2 = f"{self.market}:{self.pair2}"
        self.symbol3 = f"{self.market}:{self.pair3}"
        
        # État de la stratégie
        self.last_trade_time = None
        self.opportunities = []
        
        logger.info(f"Stratégie d'arbitrage triangulaire initialisée sur {self.market}")
        logger.info(f"Triangle: {self.base_asset} -> {self.asset1} -> {self.asset2} -> {self.base_asset}")
        logger.info(f"Profit minimum: {self.min_profit_pct}%, Taille de trade: {self.trade_size}")
    
    def on_tick(self, timestamp: datetime, symbol: str, data: Dict[str, Any]) -> None:
        """
        Méthode appelée à chaque tick du marché.
        
        Args:
            timestamp: Horodatage du tick
            symbol: Symbole du marché
            data: Données du tick (prix, volume, etc.)
        """
        # Vérifier si le symbole fait partie de notre triangle
        if symbol not in [self.symbol1, self.symbol2, self.symbol3]:
            return
        
        # Vérifier si nous avons les prix pour toutes les paires
        price1 = self.get_market_price(self.symbol1)  # BTC/USDT
        price2 = self.get_market_price(self.symbol2)  # ETH/BTC
        price3 = self.get_market_price(self.symbol3)  # ETH/USDT
        
        if price1 is None or price2 is None or price3 is None:
            return
        
        # Calculer les deux chemins possibles
        # Chemin 1: USDT -> BTC -> ETH -> USDT
        path1_result = (self.trade_size / price1) * price2 * price3
        path1_profit_pct = (path1_result - self.trade_size) / self.trade_size * 100
        
        # Chemin 2: USDT -> ETH -> BTC -> USDT
        path2_result = (self.trade_size / price3) * (1 / price2) * price1
        path2_profit_pct = (path2_result - self.trade_size) / self.trade_size * 100
        
        # Enregistrer l'opportunité
        opportunity = {
            "timestamp": timestamp,
            "market": self.market,
            "base_asset": self.base_asset,
            "asset1": self.asset1,
            "asset2": self.asset2,
            "price1": price1,
            "price2": price2,
            "price3": price3,
            "path1_profit_pct": path1_profit_pct,
            "path2_profit_pct": path2_profit_pct
        }
        self.opportunities.append(opportunity)
        
        # Vérifier si le profit est suffisant pour l'arbitrage
        best_profit_pct = max(path1_profit_pct, path2_profit_pct)
        best_path = 1 if path1_profit_pct > path2_profit_pct else 2
        
        if best_profit_pct >= self.min_profit_pct:
            # Vérifier le temps de recharge
            if self.last_trade_time is not None:
                cooldown = timestamp - self.last_trade_time
                if cooldown.total_seconds() < self.cooldown_minutes * 60:
                    return
            
            # Exécuter l'arbitrage
            self._execute_triangular_arbitrage(timestamp, price1, price2, price3, best_path)
    
    def on_bar(self, timestamp: datetime, symbol: str, data: pd.DataFrame) -> None:
        """
        Méthode appelée à chaque nouvelle barre (chandelier).
        
        Args:
            timestamp: Horodatage de la barre
            symbol: Symbole du marché
            data: Données de la barre (OHLCV)
        """
        # Cette stratégie n'utilise pas les barres, mais seulement les ticks
        pass
    
    def _execute_triangular_arbitrage(self, timestamp: datetime, price1: float, price2: float, price3: float, path: int) -> None:
        """
        Exécute une opération d'arbitrage triangulaire.
        
        Args:
            timestamp: Horodatage
            price1: Prix de la paire 1 (BTC/USDT)
            price2: Prix de la paire 2 (ETH/BTC)
            price3: Prix de la paire 3 (ETH/USDT)
            path: Chemin à suivre (1 ou 2)
        """
        if path == 1:
            # Chemin 1: USDT -> BTC -> ETH -> USDT
            logger.info(f"Exécution d'arbitrage triangulaire (chemin 1): {self.base_asset} -> {self.asset1} -> {self.asset2} -> {self.base_asset}")
            
            # Étape 1: Acheter BTC avec USDT
            step1_amount = self.trade_size
            step1_result = step1_amount / price1
            self.place_market_order(self.symbol1, "buy", step1_result)
            
            # Étape 2: Acheter ETH avec BTC
            step2_amount = step1_result
            step2_result = step2_amount * price2
            self.place_market_order(self.symbol2, "buy", step2_result)
            
            # Étape 3: Vendre ETH contre USDT
            step3_amount = step2_result
            step3_result = step3_amount * price3
            self.place_market_order(self.symbol3, "sell", step3_amount)
            
            # Calculer le profit
            profit = step3_result - self.trade_size
            profit_pct = profit / self.trade_size * 100
            
        else:
            # Chemin 2: USDT -> ETH -> BTC -> USDT
            logger.info(f"Exécution d'arbitrage triangulaire (chemin 2): {self.base_asset} -> {self.asset2} -> {self.asset1} -> {self.base_asset}")
            
            # Étape 1: Acheter ETH avec USDT
            step1_amount = self.trade_size
            step1_result = step1_amount / price3
            self.place_market_order(self.symbol3, "buy", step1_result)
            
            # Étape 2: Vendre ETH contre BTC
            step2_amount = step1_result
            step2_result = step2_amount / price2
            self.place_market_order(self.symbol2, "sell", step2_amount)
            
            # Étape 3: Vendre BTC contre USDT
            step3_amount = step2_result
            step3_result = step3_amount * price1
            self.place_market_order(self.symbol1, "sell", step3_amount)
            
            # Calculer le profit
            profit = step3_result - self.trade_size
            profit_pct = profit / self.trade_size * 100
        
        # Mettre à jour l'état
        self.last_trade_time = timestamp
        
        # Enregistrer l'opération d'arbitrage
        arbitrage_trade = {
            "timestamp": timestamp,
            "market": self.market,
            "path": path,
            "price1": price1,
            "price2": price2,
            "price3": price3,
            "trade_size": self.trade_size,
            "profit": profit,
            "profit_pct": profit_pct
        }
        
        logger.info(f"Arbitrage triangulaire exécuté: {arbitrage_trade}")


class StatisticalArbitrageStrategy(BaseStrategy):
    """
    Stratégie d'arbitrage statistique basée sur la cointegration.
    
    Cette stratégie surveille les paires d'actifs qui ont tendance à évoluer ensemble
    et exécute des opérations lorsque l'écart entre eux devient statistiquement significatif.
    """
    
    def __init__(self, market_simulator, **kwargs):
        """
        Initialise la stratégie d'arbitrage statistique.
        
        Args:
            market_simulator: Simulateur de marché
            **kwargs: Paramètres de la stratégie
                - market: Marché à utiliser (ex: "binance")
                - pair_a: Premier actif de la paire (ex: "BTC/USDT")
                - pair_b: Deuxième actif de la paire (ex: "ETH/USDT")
                - window: Fenêtre pour le calcul de la moyenne et de l'écart-type (défaut: 100)
                - entry_threshold: Seuil d'entrée en nombre d'écarts-types (défaut: 2.0)
                - exit_threshold: Seuil de sortie en nombre d'écarts-types (défaut: 0.5)
                - trade_size: Taille de l'opération en unités de base (défaut: 1.0)
                - max_position: Position maximale autorisée (défaut: 5.0)
        """
        super().__init__(market_simulator, **kwargs)
        
        # Paramètres de la stratégie
        self.market = kwargs.get("market", "binance")
        self.pair_a = kwargs.get("pair_a", "BTC/USDT")
        self.pair_b = kwargs.get("pair_b", "ETH/USDT")
        self.window = int(kwargs.get("window", 100))
        self.entry_threshold = float(kwargs.get("entry_threshold", 2.0))
        self.exit_threshold = float(kwargs.get("exit_threshold", 0.5))
        self.trade_size = float(kwargs.get("trade_size", 1.0))
        self.max_position = float(kwargs.get("max_position", 5.0))
        
        # Symboles complets pour le marché
        self.symbol_a = f"{self.market}:{self.pair_a}"
        self.symbol_b = f"{self.market}:{self.pair_b}"
        
        # État de la stratégie
        self.position_a = 0.0
        self.position_b = 0.0
        self.price_history_a = []
        self.price_history_b = []
        self.spread_history = []
        self.spread_mean = None
        self.spread_std = None
        self.current_zscore = None
        
        logger.info(f"Stratégie d'arbitrage statistique initialisée sur {self.market}")
        logger.info(f"Paires: {self.pair_a} et {self.pair_b}")
        logger.info(f"Fenêtre: {self.window}, Seuil d'entrée: {self.entry_threshold}, Seuil de sortie: {self.exit_threshold}")
    
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
        # Vérifier si le symbole fait partie de notre paire
        if symbol not in [self.symbol_a, self.symbol_b]:
            return
        
        # Récupérer les prix actuels
        price_a = self.get_market_price(self.symbol_a)
        price_b = self.get_market_price(self.symbol_b)
        
        if price_a is None or price_b is None:
            return
        
        # Mettre à jour l'historique des prix
        self.price_history_a.append(price_a)
        self.price_history_b.append(price_b)
        
        # Limiter la taille de l'historique
        if len(self.price_history_a) > self.window:
            self.price_history_a.pop(0)
            self.price_history_b.pop(0)
        
        # Calculer le spread (différence normalisée entre les prix)
        if len(self.price_history_a) >= self.window:
            # Normaliser les prix
            norm_price_a = self.price_history_a[-1] / self.price_history_a[0]
            norm_price_b = self.price_history_b[-1] / self.price_history_b[0]
            
            # Calculer le spread
            spread = norm_price_a - norm_price_b
            self.spread_history.append(spread)
            
            # Limiter la taille de l'historique du spread
            if len(self.spread_history) > self.window:
                self.spread_history.pop(0)
            
            # Calculer la moyenne et l'écart-type du spread
            self.spread_mean = np.mean(self.spread_history)
            self.spread_std = np.std(self.spread_history)
            
            # Calculer le z-score (nombre d'écarts-types par rapport à la moyenne)
            if self.spread_std > 0:
                self.current_zscore = (spread - self.spread_mean) / self.spread_std
                
                # Exécuter la stratégie
                self._execute_statistical_arbitrage(timestamp, price_a, price_b, self.current_zscore)
    
    def _execute_statistical_arbitrage(self, timestamp: datetime, price_a: float, price_b: float, zscore: float) -> None:
        """
        Exécute une opération d'arbitrage statistique.
        
        Args:
            timestamp: Horodatage
            price_a: Prix de l'actif A
            price_b: Prix de l'actif B
            zscore: Z-score actuel
        """
        # Vérifier si nous avons une position ouverte
        has_position = abs(self.position_a) > 0 or abs(self.position_b) > 0
        
        if not has_position:
            # Pas de position, vérifier si nous devons en ouvrir une
            if zscore > self.entry_threshold:
                # Le spread est trop élevé, vendre A et acheter B
                logger.info(f"Ouverture de position: Vente de {self.pair_a}, Achat de {self.pair_b} (Z-score: {zscore:.2f})")
                
                # Calculer la taille de la position
                position_size = min(self.trade_size, self.max_position)
                
                # Placer les ordres
                self.place_market_order(self.symbol_a, "sell", position_size)
                self.place_market_order(self.symbol_b, "buy", position_size)
                
                # Mettre à jour les positions
                self.position_a = -position_size
                self.position_b = position_size
                
            elif zscore < -self.entry_threshold:
                # Le spread est trop bas, acheter A et vendre B
                logger.info(f"Ouverture de position: Achat de {self.pair_a}, Vente de {self.pair_b} (Z-score: {zscore:.2f})")
                
                # Calculer la taille de la position
                position_size = min(self.trade_size, self.max_position)
                
                # Placer les ordres
                self.place_market_order(self.symbol_a, "buy", position_size)
                self.place_market_order(self.symbol_b, "sell", position_size)
                
                # Mettre à jour les positions
                self.position_a = position_size
                self.position_b = -position_size
        
        else:
            # Nous avons une position, vérifier si nous devons la fermer
            if (self.position_a > 0 and zscore > -self.exit_threshold) or \
               (self.position_a < 0 and zscore < self.exit_threshold):
                # Le spread est revenu à la normale, fermer la position
                logger.info(f"Fermeture de position (Z-score: {zscore:.2f})")
                
                # Placer les ordres pour fermer la position
                if self.position_a > 0:
                    self.place_market_order(self.symbol_a, "sell", abs(self.position_a))
                    self.place_market_order(self.symbol_b, "buy", abs(self.position_b))
                else:
                    self.place_market_order(self.symbol_a, "buy", abs(self.position_a))
                    self.place_market_order(self.symbol_b, "sell", abs(self.position_b))
                
                # Réinitialiser les positions
                self.position_a = 0.0
                self.position_b = 0.0 