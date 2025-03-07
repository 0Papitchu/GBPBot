#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Moteur de Backtesting pour GBPBot
================================

Ce module implémente le moteur principal de backtesting, responsable de
l'exécution des stratégies sur des données historiques et de la simulation
des transactions.
"""

import logging
import time
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Union, Callable
from datetime import datetime, timedelta
from decimal import Decimal

# Configuration du logger
logger = logging.getLogger("gbpbot.backtesting.engine")

class BacktestEngine:
    """
    Moteur principal de backtesting pour GBPBot.
    
    Cette classe est responsable de l'exécution des stratégies sur des données
    historiques, de la simulation des transactions et du calcul des performances.
    """
    
    def __init__(
        self,
        data_loader,
        strategy_name: str,
        initial_capital: float = 10000.0,
        strategy_params: Optional[Dict[str, Any]] = None,
        commission_rate: float = 0.001,
        slippage_model: str = "fixed",
        slippage_params: Optional[Dict[str, Any]] = None,
        risk_manager = None,
        execution_handler = None
    ):
        """
        Initialise le moteur de backtesting.
        
        Args:
            data_loader: Instance de DataLoader pour charger les données historiques
            strategy_name (str): Nom de la stratégie à tester
            initial_capital (float): Capital initial pour le backtest
            strategy_params (dict, optional): Paramètres spécifiques à la stratégie
            commission_rate (float): Taux de commission (0.001 = 0.1%)
            slippage_model (str): Modèle de slippage ('fixed', 'variable', 'orderbook')
            slippage_params (dict, optional): Paramètres pour le modèle de slippage
            risk_manager: Gestionnaire de risque (optionnel)
            execution_handler: Gestionnaire d'exécution (optionnel)
        """
        self.data_loader = data_loader
        self.strategy_name = strategy_name
        self.initial_capital = initial_capital
        self.strategy_params = strategy_params or {}
        self.commission_rate = commission_rate
        self.slippage_model = slippage_model
        self.slippage_params = slippage_params or {"fixed_bps": 10}  # 10 bps par défaut
        
        # Composants optionnels
        self.risk_manager = risk_manager
        self.execution_handler = execution_handler
        
        # État interne
        self.strategy = None
        self.data = None
        self.current_time = None
        self.portfolio = None
        self.trades = []
        self.orders = []
        self.equity_curve = []
        self.performance_metrics = {}
        self.is_running = False
        self.start_time = None
        self.end_time = None
        
        # Initialisation
        self._initialize()
    
    def _initialize(self):
        """Initialise le moteur de backtesting."""
        # Chargement de la stratégie
        self.strategy = self._load_strategy(self.strategy_name, self.strategy_params)
        
        # Initialisation du portfolio
        self.portfolio = {
            "cash": self.initial_capital,
            "positions": {},
            "equity": self.initial_capital,
            "margin_used": 0.0,
            "margin_available": self.initial_capital
        }
        
        logger.info(f"Moteur de backtesting initialisé pour la stratégie {self.strategy_name}")
    
    def _load_strategy(self, strategy_name: str, strategy_params: Dict[str, Any]):
        """
        Charge la stratégie spécifiée.
        
        Args:
            strategy_name (str): Nom de la stratégie
            strategy_params (dict): Paramètres de la stratégie
            
        Returns:
            object: Instance de la stratégie
        """
        try:
            # Import dynamique de la stratégie
            module_path = f"gbpbot.strategies.{strategy_name.lower()}"
            strategy_module = __import__(module_path, fromlist=["Strategy"])
            strategy_class = getattr(strategy_module, "Strategy")
            
            # Création de l'instance avec les paramètres
            strategy = strategy_class(**strategy_params)
            
            return strategy
        except (ImportError, AttributeError) as e:
            logger.error(f"Erreur lors du chargement de la stratégie {strategy_name}: {e}")
            raise ValueError(f"Stratégie {strategy_name} non trouvée ou invalide")
    
    def load_data(self):
        """
        Charge les données historiques via le data_loader.
        
        Returns:
            bool: True si les données ont été chargées avec succès
        """
        try:
            self.data = self.data_loader.load()
            self.start_time = self.data.index[0]
            self.end_time = self.data.index[-1]
            self.current_time = self.start_time
            
            logger.info(f"Données chargées: {len(self.data)} points de données de {self.start_time} à {self.end_time}")
            return True
        except Exception as e:
            logger.error(f"Erreur lors du chargement des données: {e}")
            return False
    
    def run(self, progress_callback: Optional[Callable] = None):
        """
        Exécute le backtest complet.
        
        Args:
            progress_callback (callable, optional): Fonction de callback pour le suivi de progression
            
        Returns:
            dict: Résultats du backtest
        """
        if self.data is None:
            self.load_data()
        
        if self.data is None or len(self.data) == 0:
            logger.error("Aucune donnée disponible pour le backtest")
            return {"success": False, "error": "Aucune donnée disponible"}
        
        logger.info(f"Démarrage du backtest pour {self.strategy_name} de {self.start_time} à {self.end_time}")
        
        self.is_running = True
        start_process_time = time.time()
        
        try:
            # Initialisation de la stratégie avec les données
            self.strategy.initialize(self.data)
            
            # Boucle principale du backtest
            total_bars = len(self.data)
            for i, (timestamp, bar) in enumerate(self.data.iterrows()):
                self.current_time = timestamp
                
                # Mise à jour du portfolio avec les prix actuels
                self._update_portfolio_value(bar)
                
                # Enregistrement de l'equity curve
                self.equity_curve.append({
                    "timestamp": timestamp,
                    "equity": self.portfolio["equity"],
                    "cash": self.portfolio["cash"]
                })
                
                # Exécution de la stratégie pour cette barre
                signals = self.strategy.on_bar(timestamp, bar, self.portfolio)
                
                # Traitement des signaux
                if signals:
                    self._process_signals(signals, bar)
                
                # Mise à jour de la progression
                if progress_callback and i % max(1, total_bars // 100) == 0:
                    progress = (i + 1) / total_bars * 100
                    progress_callback(progress)
            
            # Finalisation du backtest
            self._finalize_backtest()
            
            process_time = time.time() - start_process_time
            logger.info(f"Backtest terminé en {process_time:.2f} secondes")
            
            return self.get_results()
        
        except Exception as e:
            logger.error(f"Erreur lors de l'exécution du backtest: {e}", exc_info=True)
            return {"success": False, "error": str(e)}
        
        finally:
            self.is_running = False
    
    def _process_signals(self, signals: List[Dict[str, Any]], bar: pd.Series):
        """
        Traite les signaux générés par la stratégie.
        
        Args:
            signals (list): Liste des signaux générés
            bar (pd.Series): Données de la barre actuelle
        """
        for signal in signals:
            # Validation du signal
            if not self._validate_signal(signal):
                continue
            
            # Application du risk management si disponible
            if self.risk_manager:
                signal = self.risk_manager.process_signal(signal, self.portfolio, bar)
                if not signal:  # Signal rejeté par le risk manager
                    continue
            
            # Création de l'ordre
            order = self._create_order_from_signal(signal, bar)
            self.orders.append(order)
            
            # Exécution de l'ordre
            if self.execution_handler:
                trade = self.execution_handler.execute_order(order, bar, self.portfolio)
            else:
                trade = self._execute_order(order, bar)
            
            if trade:
                self.trades.append(trade)
                self._update_portfolio(trade)
    
    def _validate_signal(self, signal: Dict[str, Any]) -> bool:
        """
        Valide un signal généré par la stratégie.
        
        Args:
            signal (dict): Signal à valider
            
        Returns:
            bool: True si le signal est valide
        """
        required_fields = ["symbol", "direction", "type"]
        
        # Vérification des champs requis
        for field in required_fields:
            if field not in signal:
                logger.warning(f"Signal invalide: champ '{field}' manquant")
                return False
        
        # Validation du type de signal
        valid_types = ["market", "limit", "stop", "stop_limit"]
        if signal["type"] not in valid_types:
            logger.warning(f"Type de signal invalide: {signal['type']}")
            return False
        
        # Validation de la direction
        valid_directions = ["buy", "sell"]
        if signal["direction"] not in valid_directions:
            logger.warning(f"Direction de signal invalide: {signal['direction']}")
            return False
        
        return True
    
    def _create_order_from_signal(self, signal: Dict[str, Any], bar: pd.Series) -> Dict[str, Any]:
        """
        Crée un ordre à partir d'un signal.
        
        Args:
            signal (dict): Signal généré par la stratégie
            bar (pd.Series): Données de la barre actuelle
            
        Returns:
            dict: Ordre créé
        """
        order = {
            "id": len(self.orders) + 1,
            "timestamp": self.current_time,
            "symbol": signal["symbol"],
            "type": signal["type"],
            "direction": signal["direction"],
            "quantity": signal.get("quantity", 0),
            "price": signal.get("price", None),
            "status": "created"
        }
        
        # Si la quantité n'est pas spécifiée mais que le montant l'est
        if order["quantity"] == 0 and "amount" in signal:
            price = bar["close"]  # Prix par défaut
            if signal["type"] == "limit" and "price" in signal:
                price = signal["price"]
            
            order["quantity"] = signal["amount"] / price
        
        # Ajout des paramètres spécifiques au type d'ordre
        if signal["type"] in ["limit", "stop_limit"]:
            order["price"] = signal.get("price", bar["close"])
        
        if signal["type"] in ["stop", "stop_limit"]:
            order["stop_price"] = signal.get("stop_price", bar["close"])
        
        return order
    
    def _execute_order(self, order: Dict[str, Any], bar: pd.Series) -> Optional[Dict[str, Any]]:
        """
        Exécute un ordre et génère un trade.
        
        Args:
            order (dict): Ordre à exécuter
            bar (pd.Series): Données de la barre actuelle
            
        Returns:
            dict: Trade généré ou None si l'ordre n'a pas été exécuté
        """
        # Vérification si l'ordre peut être exécuté
        if order["type"] == "market":
            execution_price = self._calculate_execution_price(order, bar)
            order["status"] = "filled"
        elif order["type"] == "limit":
            # Pour les ordres limit, vérifier si le prix a été atteint
            if (order["direction"] == "buy" and bar["low"] <= order["price"]) or \
               (order["direction"] == "sell" and bar["high"] >= order["price"]):
                execution_price = order["price"]
                order["status"] = "filled"
            else:
                return None  # Ordre non exécuté
        else:
            # Autres types d'ordres non supportés pour l'instant
            logger.warning(f"Type d'ordre non supporté: {order['type']}")
            return None
        
        # Création du trade
        trade = {
            "id": len(self.trades) + 1,
            "order_id": order["id"],
            "timestamp": self.current_time,
            "symbol": order["symbol"],
            "direction": order["direction"],
            "quantity": order["quantity"],
            "price": execution_price,
            "commission": self._calculate_commission(order["quantity"], execution_price)
        }
        
        return trade
    
    def _calculate_execution_price(self, order: Dict[str, Any], bar: pd.Series) -> float:
        """
        Calcule le prix d'exécution en tenant compte du slippage.
        
        Args:
            order (dict): Ordre à exécuter
            bar (pd.Series): Données de la barre actuelle
            
        Returns:
            float: Prix d'exécution
        """
        base_price = bar["close"]
        
        # Application du slippage selon le modèle choisi
        if self.slippage_model == "fixed":
            slippage_bps = self.slippage_params.get("fixed_bps", 10)
            slippage_factor = slippage_bps / 10000  # Conversion en pourcentage
            
            if order["direction"] == "buy":
                execution_price = base_price * (1 + slippage_factor)
            else:  # sell
                execution_price = base_price * (1 - slippage_factor)
        
        elif self.slippage_model == "variable":
            # Slippage variable basé sur la volatilité
            volatility = self.slippage_params.get("volatility_factor", 0.5)
            price_range = bar["high"] - bar["low"]
            slippage_amount = price_range * volatility
            
            if order["direction"] == "buy":
                execution_price = base_price + slippage_amount
            else:  # sell
                execution_price = base_price - slippage_amount
        
        elif self.slippage_model == "orderbook":
            # Simulation basée sur le carnet d'ordres (non implémenté)
            # Nécessiterait des données de carnet d'ordres historiques
            execution_price = base_price
            logger.warning("Modèle de slippage 'orderbook' non implémenté, utilisation du prix de clôture")
        
        else:
            execution_price = base_price
            logger.warning(f"Modèle de slippage inconnu: {self.slippage_model}, utilisation du prix de clôture")
        
        return execution_price
    
    def _calculate_commission(self, quantity: float, price: float) -> float:
        """
        Calcule la commission pour une transaction.
        
        Args:
            quantity (float): Quantité tradée
            price (float): Prix d'exécution
            
        Returns:
            float: Montant de la commission
        """
        return quantity * price * self.commission_rate
    
    def _update_portfolio(self, trade: Dict[str, Any]):
        """
        Met à jour le portfolio après l'exécution d'un trade.
        
        Args:
            trade (dict): Trade exécuté
        """
        symbol = trade["symbol"]
        direction = trade["direction"]
        quantity = trade["quantity"]
        price = trade["price"]
        commission = trade["commission"]
        
        # Mise à jour des positions
        if symbol not in self.portfolio["positions"]:
            self.portfolio["positions"][symbol] = {
                "quantity": 0,
                "avg_price": 0,
                "cost_basis": 0
            }
        
        position = self.portfolio["positions"][symbol]
        
        if direction == "buy":
            # Calcul du nouveau coût moyen
            total_cost = position["quantity"] * position["avg_price"]
            new_cost = quantity * price
            total_quantity = position["quantity"] + quantity
            
            if total_quantity > 0:
                position["avg_price"] = (total_cost + new_cost) / total_quantity
            
            position["quantity"] += quantity
            position["cost_basis"] += new_cost
            
            # Mise à jour du cash
            self.portfolio["cash"] -= (price * quantity + commission)
        
        else:  # sell
            # Mise à jour de la position
            position["quantity"] -= quantity
            
            # Si la position est fermée, réinitialiser le coût moyen
            if position["quantity"] <= 0:
                position["avg_price"] = 0
                position["cost_basis"] = 0
            
            # Mise à jour du cash
            self.portfolio["cash"] += (price * quantity - commission)
    
    def _update_portfolio_value(self, bar: pd.Series):
        """
        Met à jour la valeur du portfolio avec les prix actuels.
        
        Args:
            bar (pd.Series): Données de la barre actuelle
        """
        equity = self.portfolio["cash"]
        
        # Valorisation des positions
        for symbol, position in self.portfolio["positions"].items():
            if position["quantity"] > 0:
                # Utiliser le prix de clôture pour la valorisation
                current_price = bar.get(f"{symbol}_close", bar["close"])
                position_value = position["quantity"] * current_price
                equity += position_value
        
        self.portfolio["equity"] = equity
        self.portfolio["margin_available"] = equity - self.portfolio["margin_used"]
    
    def _finalize_backtest(self):
        """Finalise le backtest et calcule les métriques de performance."""
        # Conversion de l'equity curve en DataFrame
        self.equity_curve = pd.DataFrame(self.equity_curve)
        self.equity_curve.set_index("timestamp", inplace=True)
        
        # Calcul des métriques de performance
        self._calculate_performance_metrics()
        
        logger.info(f"Backtest finalisé pour {self.strategy_name}")
        logger.info(f"Résultat final: {self.performance_metrics['total_return']:.2f}% de rendement")
    
    def _calculate_performance_metrics(self):
        """Calcule les métriques de performance du backtest."""
        if len(self.equity_curve) == 0:
            logger.warning("Aucune donnée d'equity curve disponible pour calculer les métriques")
            return
        
        equity = self.equity_curve["equity"]
        
        # Calcul des rendements
        returns = equity.pct_change().dropna()
        
        # Métriques de base
        total_return = (equity.iloc[-1] / equity.iloc[0] - 1) * 100
        
        # Calcul de la volatilité annualisée
        annual_factor = 252  # Jours de trading par an
        volatility = returns.std() * np.sqrt(annual_factor) * 100
        
        # Calcul du ratio de Sharpe (en supposant un taux sans risque de 0%)
        sharpe_ratio = (returns.mean() / returns.std()) * np.sqrt(annual_factor) if returns.std() > 0 else 0
        
        # Calcul du drawdown maximum
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.cummax()
        drawdown = (cumulative / running_max - 1) * 100
        max_drawdown = drawdown.min()
        
        # Calcul du ratio de Sortino (en supposant un taux sans risque de 0%)
        negative_returns = returns[returns < 0]
        downside_deviation = negative_returns.std() * np.sqrt(annual_factor)
        sortino_ratio = (returns.mean() / downside_deviation) * np.sqrt(annual_factor) if downside_deviation > 0 else 0
        
        # Calcul du CAGR (Compound Annual Growth Rate)
        years = (self.end_time - self.start_time).days / 365.25
        cagr = ((equity.iloc[-1] / equity.iloc[0]) ** (1 / years) - 1) * 100 if years > 0 else 0
        
        # Statistiques des trades
        winning_trades = [t for t in self.trades if 
                          (t["direction"] == "buy" and t["price"] < self.equity_curve.loc[t["timestamp"], "equity"]) or
                          (t["direction"] == "sell" and t["price"] > self.equity_curve.loc[t["timestamp"], "equity"])]
        
        win_rate = len(winning_trades) / len(self.trades) * 100 if len(self.trades) > 0 else 0
        
        # Stockage des métriques
        self.performance_metrics = {
            "total_return": total_return,
            "volatility": volatility,
            "sharpe_ratio": sharpe_ratio,
            "sortino_ratio": sortino_ratio,
            "max_drawdown": max_drawdown,
            "cagr": cagr,
            "win_rate": win_rate,
            "total_trades": len(self.trades),
            "winning_trades": len(winning_trades),
            "losing_trades": len(self.trades) - len(winning_trades),
            "initial_capital": self.initial_capital,
            "final_capital": equity.iloc[-1],
            "start_date": self.start_time,
            "end_date": self.end_time
        }
    
    def get_results(self) -> Dict[str, Any]:
        """
        Retourne les résultats complets du backtest.
        
        Returns:
            dict: Résultats du backtest
        """
        return {
            "success": True,
            "strategy": self.strategy_name,
            "performance": self.performance_metrics,
            "equity_curve": self.equity_curve,
            "trades": self.trades,
            "orders": self.orders,
            "portfolio": self.portfolio
        }
    
    def plot_results(self, show_trades: bool = True, save_path: Optional[str] = None):
        """
        Génère des visualisations des résultats du backtest.
        
        Args:
            show_trades (bool): Afficher les trades sur le graphique
            save_path (str, optional): Chemin pour sauvegarder les graphiques
            
        Returns:
            object: Objet de visualisation (dépend de l'implémentation)
        """
        # Cette méthode serait implémentée dans une classe dédiée à la visualisation
        from gbpbot.backtesting.visualization import BacktestVisualizer
        
        visualizer = BacktestVisualizer(self)
        return visualizer.plot_equity_curve(show_trades=show_trades, save_path=save_path)
    
    def generate_report(self, output_format: str = "html", output_path: Optional[str] = None) -> str:
        """
        Génère un rapport détaillé du backtest.
        
        Args:
            output_format (str): Format du rapport ('html', 'pdf', 'json')
            output_path (str, optional): Chemin pour sauvegarder le rapport
            
        Returns:
            str: Chemin du rapport généré ou contenu du rapport
        """
        # Cette méthode serait implémentée dans une classe dédiée aux rapports
        from gbpbot.backtesting.reporting import ReportGenerator
        
        report_generator = ReportGenerator(self)
        return report_generator.generate(output_format=output_format, output_path=output_path) 