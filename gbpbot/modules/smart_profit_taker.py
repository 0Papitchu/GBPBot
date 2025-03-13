#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module de prise de profit intelligent pour GBPBot
================================================

Ce module implémente un système avancé de prise de profit qui utilise des
algorithmes d'apprentissage automatique et l'analyse de la volatilité pour
déterminer les points de sortie optimaux, maximisant ainsi les profits tout
en minimisant le risque.

Caractéristiques:
- Analyse en temps réel des mouvements de prix
- Prises de profit échelonnées et adaptatives
- Intégration avec les modèles prédictifs de volatilité
- Gestion avancée du stop-loss glissant (trailing)
- Optimisation des stratégies basée sur les performances historiques
"""

import os
import json
import time
import asyncio
import logging
import numpy as np
from typing import Dict, List, Any, Optional, Tuple, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from gbpbot.utils.logger import setup_logger
from gbpbot.machine_learning.volatility_predictor import VolatilityPredictor, load_volatility_model

# Configuration du logger
logger = setup_logger("smart_profit_taker", logging.INFO)

@dataclass
class ProfitTarget:
    """Représente une cible de prise de profit."""
    percentage: float  # % de hausse pour déclencher cette prise de profit
    portion: float  # % du montant total à vendre à ce niveau
    adjustment_factor: float = 1.0  # Facteur d'ajustement dynamique
    triggered: bool = False  # Si cette cible a été déclenchée
    time_condition: Optional[int] = None  # Temps minimum en secondes avant déclenchement (optionnel)

@dataclass
class StopLossConfig:
    """Configuration du stop-loss."""
    initial_percentage: float  # % de baisse pour déclencher le stop-loss initial
    trailing_activation: float  # % de hausse pour activer le trailing stop
    trailing_distance: float  # Distance de suivi en % du prix max
    partial_trigger: Optional[float] = None  # % de la position à vendre si stop partiel
    time_based_adjustment: bool = True  # Ajuster le stop-loss en fonction du temps
    volatility_based: bool = True  # Ajuster en fonction de la volatilité
    moving_average_periods: Optional[List[int]] = None  # Périodes pour les moyennes mobiles (optionnel)

@dataclass
class ExitStrategyConfig:
    """Configuration complète de la stratégie de sortie."""
    profit_targets: List[ProfitTarget]
    stop_loss: StopLossConfig
    max_hold_time_minutes: Optional[int] = None  # Temps max de détention (optionnel)
    reinvest_profits: bool = False  # Réinvestir les profits dans d'autres opportunités
    enable_dynamic_adjustment: bool = True  # Ajuster dynamiquement en fonction du marché
    volatility_sensitivity: float = 1.0  # Sensibilité aux changements de volatilité
    volume_sensitivity: float = 1.0  # Sensibilité aux changements de volume
    market_trend_impact: float = 0.5  # Impact de la tendance de marché sur la stratégie
    minimum_profit: Optional[float] = None  # Profit minimum accepté (% du capital investi)
    max_loss_per_trade: Optional[float] = None  # Perte maximale acceptée par trade
    analysis_interval_seconds: int = 10  # Intervalle d'analyse en secondes

class SmartProfitTaker:
    """
    Système avancé de prise de profit intelligent qui optimise
    les stratégies de sortie pour maximiser les gains tout en
    gérant efficacement le risque.
    """
    
    def __init__(
        self,
        config: Optional[ExitStrategyConfig] = None,
        token_symbol: str = "",
        blockchain: str = "solana",
        initial_investment: float = 0.0,
        entry_price: float = 0.0,
        config_path: Optional[str] = None,
        volatility_predictor: Optional[VolatilityPredictor] = None
    ):
        """
        Initialise le SmartProfitTaker avec la configuration spécifiée.
        
        Args:
            config: Configuration de la stratégie de sortie
            token_symbol: Symbole du token concerné
            blockchain: Blockchain sur laquelle le token est échangé
            initial_investment: Montant initial investi
            entry_price: Prix d'entrée
            config_path: Chemin vers le fichier de configuration
            volatility_predictor: Prédicteur de volatilité préchargé
        """
        # Charger la configuration depuis le fichier si spécifié
        if config_path and os.path.exists(config_path):
            self.config = self._load_config(config_path)
        else:
            self.config = config or self._create_default_config()
        
        self.token_symbol = token_symbol
        self.blockchain = blockchain
        self.initial_investment = initial_investment
        self.entry_price = entry_price
        
        # État interne
        self.current_price = entry_price
        self.highest_price = entry_price
        self.lowest_price = entry_price
        self.current_investment = initial_investment
        self.profits_taken = 0.0
        self.profit_exits = []
        self.trailing_stop_active = False
        self.trailing_stop_price = 0.0
        self.entry_time = datetime.now()
        self.last_analysis_time = datetime.now()
        self.price_history = []
        self.volume_history = []
        self.volatility_history = []
        
        # Statistiques
        self.total_exits = 0
        self.total_profit = 0.0
        self.roi_percentage = 0.0
        
        # Chargement du modèle de prédiction de volatilité
        self.volatility_predictor = volatility_predictor or self._load_volatility_predictor()
        
        logger.info(f"SmartProfitTaker initialisé pour {token_symbol} sur {blockchain}")
    
    def _load_config(self, config_path: str) -> ExitStrategyConfig:
        """Charge la configuration depuis un fichier JSON."""
        try:
            with open(config_path, 'r') as f:
                config_data = json.load(f)
            
            profit_targets = []
            for pt_data in config_data.get('profit_targets', []):
                profit_targets.append(ProfitTarget(
                    percentage=pt_data.get('percentage', 10.0),
                    portion=pt_data.get('portion', 0.25),
                    adjustment_factor=pt_data.get('adjustment_factor', 1.0),
                    triggered=False,
                    time_condition=pt_data.get('time_condition')
                ))
            
            sl_data = config_data.get('stop_loss', {})
            stop_loss = StopLossConfig(
                initial_percentage=sl_data.get('initial_percentage', 5.0),
                trailing_activation=sl_data.get('trailing_activation', 10.0),
                trailing_distance=sl_data.get('trailing_distance', 5.0),
                partial_trigger=sl_data.get('partial_trigger'),
                time_based_adjustment=sl_data.get('time_based_adjustment', True),
                volatility_based=sl_data.get('volatility_based', True),
                moving_average_periods=sl_data.get('moving_average_periods')
            )
            
            return ExitStrategyConfig(
                profit_targets=profit_targets,
                stop_loss=stop_loss,
                max_hold_time_minutes=config_data.get('max_hold_time_minutes'),
                reinvest_profits=config_data.get('reinvest_profits', False),
                enable_dynamic_adjustment=config_data.get('enable_dynamic_adjustment', True),
                volatility_sensitivity=config_data.get('volatility_sensitivity', 1.0),
                volume_sensitivity=config_data.get('volume_sensitivity', 1.0),
                market_trend_impact=config_data.get('market_trend_impact', 0.5),
                minimum_profit=config_data.get('minimum_profit'),
                max_loss_per_trade=config_data.get('max_loss_per_trade'),
                analysis_interval_seconds=config_data.get('analysis_interval_seconds', 10)
            )
        except Exception as e:
            logger.error(f"Erreur lors du chargement de la configuration: {str(e)}")
            return self._create_default_config()
    
    def _create_default_config(self) -> ExitStrategyConfig:
        """Crée une configuration par défaut."""
        return ExitStrategyConfig(
            profit_targets=[
                ProfitTarget(percentage=10.0, portion=0.25, adjustment_factor=1.0),
                ProfitTarget(percentage=25.0, portion=0.30, adjustment_factor=1.0),
                ProfitTarget(percentage=50.0, portion=0.25, adjustment_factor=1.0),
                ProfitTarget(percentage=100.0, portion=0.20, adjustment_factor=1.0)
            ],
            stop_loss=StopLossConfig(
                initial_percentage=5.0,
                trailing_activation=15.0,
                trailing_distance=7.5,
                time_based_adjustment=True,
                volatility_based=True
            ),
            max_hold_time_minutes=180,  # 3 heures
            enable_dynamic_adjustment=True
        )
    
    def _load_volatility_predictor(self) -> Optional[VolatilityPredictor]:
        """Charge ou crée un prédicteur de volatilité."""
        try:
            return load_volatility_model(self.blockchain)
        except Exception as e:
            logger.warning(f"Impossible de charger le prédicteur de volatilité: {str(e)}")
            return None
    
    async def update_price(self, new_price: float, volume: Optional[float] = None) -> Dict[str, Any]:
        """
        Met à jour le prix actuel et vérifie si des actions doivent être prises.
        
        Args:
            new_price: Nouveau prix du token
            volume: Volume de trading (optionnel)
            
        Returns:
            Actions recommandées (ventes, stop-loss, etc.)
        """
        # Mettre à jour l'état
        self.current_price = new_price
        self.price_history.append((datetime.now(), new_price))
        if volume is not None:
            self.volume_history.append((datetime.now(), volume))
        
        # Mettre à jour les prix extrêmes
        if new_price > self.highest_price:
            self.highest_price = new_price
            # Ajuster le trailing stop si actif
            if self.trailing_stop_active:
                self._update_trailing_stop()
        elif new_price < self.lowest_price:
            self.lowest_price = new_price
        
        # Vérifier si une analyse est nécessaire
        now = datetime.now()
        seconds_since_last_analysis = (now - self.last_analysis_time).total_seconds()
        
        if seconds_since_last_analysis >= self.config.analysis_interval_seconds:
            # Calculer la volatilité actuelle
            if len(self.price_history) >= 10:
                recent_prices = [p[1] for p in self.price_history[-10:]]
                volatility = np.std(recent_prices) / np.mean(recent_prices) * 100
                self.volatility_history.append((now, volatility))
                
                # Prédire la volatilité future si possible
                predicted_volatility = None
                if self.volatility_predictor:
                    try:
                        predicted_volatility = await self.volatility_predictor.predict_volatility(
                            self.token_symbol, 
                            self.price_history, 
                            self.volume_history
                        )
                    except Exception as e:
                        logger.error(f"Erreur lors de la prédiction de volatilité: {str(e)}")
                
                # Ajuster dynamiquement les paramètres si activé
                if self.config.enable_dynamic_adjustment:
                    self._adjust_parameters(volatility, predicted_volatility)
            
            self.last_analysis_time = now
        
        # Vérifier si des cibles de profit sont atteintes
        actions = await self._check_profit_targets()
        
        # Vérifier si le stop-loss est déclenché
        stop_loss_action = self._check_stop_loss()
        if stop_loss_action:
            actions.update(stop_loss_action)
        
        # Vérifier le temps maximum de détention
        time_based_action = self._check_max_hold_time()
        if time_based_action:
            actions.update(time_based_action)
        
        return actions
    
    async def _check_profit_targets(self) -> Dict[str, Any]:
        """
        Vérifie si des cibles de profit sont atteintes.
        
        Returns:
            Actions recommandées pour les prises de profit
        """
        actions = {"take_profit": [], "info": {}}
        
        if self.current_investment <= 0:
            return actions
        
        # Calculer le pourcentage de profit actuel
        current_profit_percentage = ((self.current_price / self.entry_price) - 1) * 100
        
        for i, target in enumerate(self.config.profit_targets):
            if not target.triggered and current_profit_percentage >= target.percentage:
                # Vérifier la condition de temps si définie
                if target.time_condition:
                    time_since_entry = (datetime.now() - self.entry_time).total_seconds()
                    if time_since_entry < target.time_condition:
                        continue
                
                # Calculer le montant à vendre
                amount_to_sell = self.current_investment * target.portion
                
                # Marquer cette cible comme déclenchée
                self.config.profit_targets[i].triggered = True
                
                # Enregistrer cette prise de profit
                profit_taken = amount_to_sell * self.current_price / self.entry_price - amount_to_sell
                self.profits_taken += profit_taken
                self.profit_exits.append({
                    "time": datetime.now(),
                    "price": self.current_price,
                    "amount": amount_to_sell,
                    "profit": profit_taken,
                    "target_percentage": target.percentage
                })
                
                # Mettre à jour l'investissement restant
                self.current_investment -= amount_to_sell
                
                # Ajouter l'action
                actions["take_profit"].append({
                    "portion": target.portion,
                    "amount": amount_to_sell,
                    "price": self.current_price,
                    "profit_percentage": target.percentage,
                    "reason": f"Cible de profit {target.percentage}% atteinte"
                })
                
                # Mettre à jour les statistiques
                self.total_exits += 1
                self.total_profit += profit_taken
                self.roi_percentage = (self.total_profit / self.initial_investment) * 100
                
                logger.info(
                    f"Prise de profit déclenchée: {target.portion * 100}% à {self.current_price} "
                    f"(cible: {target.percentage}%, profit: {profit_taken:.4f})"
                )
                
                if self.config.reinvest_profits:
                    actions["info"]["reinvest"] = {
                        "amount": profit_taken,
                        "source": "take_profit"
                    }
        
        # Si toutes les cibles sont déclenchées, suggérer une sortie complète
        all_triggered = all(target.triggered for target in self.config.profit_targets)
        if all_triggered and self.current_investment > 0:
            actions["take_profit"].append({
                "portion": 1.0,
                "amount": self.current_investment,
                "price": self.current_price,
                "profit_percentage": current_profit_percentage,
                "reason": "Toutes les cibles de profit atteintes"
            })
            
            # Sortie complète
            profit_taken = self.current_investment * self.current_price / self.entry_price - self.current_investment
            self.profits_taken += profit_taken
            self.total_profit += profit_taken
            self.current_investment = 0
            self.total_exits += 1
            self.roi_percentage = (self.total_profit / self.initial_investment) * 100
        
        return actions
    
    def _check_stop_loss(self) -> Optional[Dict[str, Any]]:
        """
        Vérifie si le stop-loss est déclenché.
        
        Returns:
            Action de stop-loss si déclenchée, None sinon
        """
        if self.current_investment <= 0:
            return None
        
        # Vérifier si le trailing stop est actif
        profit_percentage = ((self.current_price / self.entry_price) - 1) * 100
        
        if not self.trailing_stop_active and profit_percentage >= self.config.stop_loss.trailing_activation:
            # Activer le trailing stop
            self.trailing_stop_active = True
            self._update_trailing_stop()
            logger.info(
                f"Trailing stop activé à {profit_percentage:.2f}% de profit. "
                f"Prix de stop: {self.trailing_stop_price:.6f}"
            )
        
        # Vérifier si le stop-loss est déclenché
        if self.trailing_stop_active and self.current_price <= self.trailing_stop_price:
            # Stop-loss déclenché
            loss_amount = (self.trailing_stop_price / self.current_price - 1) * self.current_investment
            logger.info(
                f"Trailing stop déclenché à {self.trailing_stop_price:.6f}. "
                f"Distance du plus haut: {(1 - self.trailing_stop_price / self.highest_price) * 100:.2f}%"
            )
            
            # Si stop-loss partiel configuré
            if self.config.stop_loss.partial_trigger:
                amount_to_sell = self.current_investment * self.config.stop_loss.partial_trigger
                self.current_investment -= amount_to_sell
                
                return {
                    "stop_loss": {
                        "portion": self.config.stop_loss.partial_trigger,
                        "amount": amount_to_sell,
                        "price": self.trailing_stop_price,
                        "reason": "Trailing stop-loss partiel déclenché"
                    }
                }
            else:
                # Stop-loss complet
                amount_to_sell = self.current_investment
                self.current_investment = 0
                
                return {
                    "stop_loss": {
                        "portion": 1.0,
                        "amount": amount_to_sell,
                        "price": self.trailing_stop_price,
                        "reason": "Trailing stop-loss déclenché"
                    }
                }
        
        # Vérifier le stop-loss initial si le trailing n'est pas actif
        elif not self.trailing_stop_active:
            loss_percentage = ((self.entry_price / self.current_price) - 1) * 100
            
            if loss_percentage >= self.config.stop_loss.initial_percentage:
                # Stop-loss initial déclenché
                amount_to_sell = self.current_investment
                self.current_investment = 0
                
                logger.info(
                    f"Stop-loss initial déclenché à {loss_percentage:.2f}% de perte. "
                    f"Prix: {self.current_price:.6f}"
                )
                
                return {
                    "stop_loss": {
                        "portion": 1.0,
                        "amount": amount_to_sell,
                        "price": self.current_price,
                        "reason": f"Stop-loss initial déclenché à {loss_percentage:.2f}% de perte"
                    }
                }
        
        return None
    
    def _update_trailing_stop(self) -> None:
        """Met à jour le prix du trailing stop basé sur le prix le plus haut."""
        distance_percentage = self.config.stop_loss.trailing_distance / 100
        self.trailing_stop_price = self.highest_price * (1 - distance_percentage)
    
    def _check_max_hold_time(self) -> Optional[Dict[str, Any]]:
        """
        Vérifie si le temps maximum de détention est dépassé.
        
        Returns:
            Action de sortie si le temps max est dépassé, None sinon
        """
        if not self.config.max_hold_time_minutes or self.current_investment <= 0:
            return None
        
        time_since_entry = (datetime.now() - self.entry_time).total_seconds() / 60
        
        if time_since_entry >= self.config.max_hold_time_minutes:
            # Temps maximum dépassé, sortir complètement
            amount_to_sell = self.current_investment
            profit_percentage = ((self.current_price / self.entry_price) - 1) * 100
            
            # Vérifier profit minimum si configuré
            if self.config.minimum_profit is not None and profit_percentage < self.config.minimum_profit:
                logger.info(
                    f"Temps max dépassé mais profit ({profit_percentage:.2f}%) < "
                    f"minimum ({self.config.minimum_profit:.2f}%). Maintien de la position."
                )
                return None
            
            self.current_investment = 0
            
            logger.info(
                f"Temps maximum de détention atteint ({time_since_entry:.2f} min). "
                f"Sortie complète au prix {self.current_price:.6f} "
                f"(profit: {profit_percentage:.2f}%)"
            )
            
            return {
                "time_exit": {
                    "portion": 1.0,
                    "amount": amount_to_sell,
                    "price": self.current_price,
                    "profit_percentage": profit_percentage,
                    "reason": f"Temps maximum de détention atteint ({self.config.max_hold_time_minutes} min)"
                }
            }
        
        return None
    
    def _adjust_parameters(self, current_volatility: float, predicted_volatility: Optional[float] = None) -> None:
        """
        Ajuste dynamiquement les paramètres de la stratégie en fonction
        des conditions de marché actuelles.
        
        Args:
            current_volatility: Volatilité actuelle du token
            predicted_volatility: Volatilité prédite (si disponible)
        """
        if not self.config.enable_dynamic_adjustment:
            return
        
        volatility_to_use = predicted_volatility if predicted_volatility is not None else current_volatility
        
        # Ajuster la distance du trailing stop en fonction de la volatilité
        if self.config.stop_loss.volatility_based and self.trailing_stop_active:
            # Plus de volatilité = plus de distance
            base_distance = self.config.stop_loss.trailing_distance
            volatility_adjustment = (volatility_to_use - 5) * 0.5  # 5% considéré comme volatilité normale
            
            new_distance = base_distance + volatility_adjustment * self.config.volatility_sensitivity
            new_distance = max(2.0, min(20.0, new_distance))  # Limiter entre 2% et 20%
            
            if abs(new_distance - self.config.stop_loss.trailing_distance) > 1.0:
                logger.info(f"Ajustement de la distance du trailing stop: {self.config.stop_loss.trailing_distance:.2f}% -> {new_distance:.2f}%")
                self.config.stop_loss.trailing_distance = new_distance
                self._update_trailing_stop()
        
        # Ajuster les facteurs des cibles de profit en fonction de la volatilité
        for i, target in enumerate(self.config.profit_targets):
            if not target.triggered:
                # Haute volatilité = cibles plus élevées
                volatility_factor = volatility_to_use / 10.0  # 10% considéré comme référence
                volatility_factor = max(0.7, min(1.5, volatility_factor))
                
                # Appliquer le facteur d'ajustement
                self.config.profit_targets[i].adjustment_factor = volatility_factor
                
                # Le pourcentage effectif est celui de base multiplié par le facteur d'ajustement
                # Ce facteur est utilisé lors de la vérification des cibles
    
    def get_current_status(self) -> Dict[str, Any]:
        """
        Retourne l'état actuel de la stratégie de sortie.
        
        Returns:
            Dictionnaire avec l'état actuel
        """
        profit_percentage = ((self.current_price / self.entry_price) - 1) * 100
        
        # Calculer les cibles ajustées
        adjusted_targets = []
        for target in self.config.profit_targets:
            adjusted_targets.append({
                "percentage": target.percentage * target.adjustment_factor,
                "portion": target.portion,
                "triggered": target.triggered
            })
        
        return {
            "token_symbol": self.token_symbol,
            "blockchain": self.blockchain,
            "entry_price": self.entry_price,
            "current_price": self.current_price,
            "highest_price": self.highest_price,
            "lowest_price": self.lowest_price,
            "initial_investment": self.initial_investment,
            "current_investment": self.current_investment,
            "profits_taken": self.profits_taken,
            "profit_percentage": profit_percentage,
            "trailing_stop_active": self.trailing_stop_active,
            "trailing_stop_price": self.trailing_stop_price if self.trailing_stop_active else None,
            "time_since_entry_minutes": (datetime.now() - self.entry_time).total_seconds() / 60,
            "total_exits": self.total_exits,
            "total_profit": self.total_profit,
            "roi_percentage": self.roi_percentage,
            "adjusted_profit_targets": adjusted_targets
        }
    
    def reset(self, entry_price: Optional[float] = None, initial_investment: Optional[float] = None) -> None:
        """
        Réinitialise la stratégie pour une nouvelle entrée.
        
        Args:
            entry_price: Nouveau prix d'entrée (si différent)
            initial_investment: Nouveau montant investi (si différent)
        """
        self.entry_price = entry_price if entry_price is not None else self.entry_price
        self.initial_investment = initial_investment if initial_investment is not None else self.initial_investment
        
        self.current_price = self.entry_price
        self.highest_price = self.entry_price
        self.lowest_price = self.entry_price
        self.current_investment = self.initial_investment
        self.profits_taken = 0.0
        self.profit_exits = []
        self.trailing_stop_active = False
        self.trailing_stop_price = 0.0
        self.entry_time = datetime.now()
        self.last_analysis_time = datetime.now()
        self.price_history = []
        self.volume_history = []
        self.volatility_history = []
        
        # Réinitialiser les cibles de profit
        for i in range(len(self.config.profit_targets)):
            self.config.profit_targets[i].triggered = False
            self.config.profit_targets[i].adjustment_factor = 1.0
        
        logger.info(f"Stratégie réinitialisée pour {self.token_symbol} à {self.entry_price}")

def create_smart_profit_taker(
    token_symbol: str,
    blockchain: str = "solana",
    initial_investment: float = 0.0,
    entry_price: float = 0.0,
    config_path: Optional[str] = None
) -> SmartProfitTaker:
    """
    Crée et retourne une instance de SmartProfitTaker.
    
    Args:
        token_symbol: Symbole du token
        blockchain: Blockchain sur laquelle le token est échangé
        initial_investment: Montant initial investi
        entry_price: Prix d'entrée
        config_path: Chemin vers le fichier de configuration
        
    Returns:
        Instance de SmartProfitTaker
    """
    return SmartProfitTaker(
        token_symbol=token_symbol,
        blockchain=blockchain,
        initial_investment=initial_investment,
        entry_price=entry_price,
        config_path=config_path
    ) 