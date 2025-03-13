"""
Gestionnaire de seuils dynamiques pour GBPBot
=============================================

Ce module permet d'ajuster automatiquement les seuils d'entrée et de sortie
pour le sniping de tokens en fonction des conditions de marché et de la
performance historique.
"""

import logging
import asyncio
import time
import json
import os
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np
from dataclasses import dataclass

logger = logging.getLogger("dynamic_threshold_manager")

@dataclass
class ThresholdSet:
    """Ensemble de seuils pour un token ou une catégorie de tokens."""
    # Seuils d'entrée
    min_liquidity_usd: float = 5000.0
    max_initial_mcap_usd: float = 2000000.0
    min_liquidity_to_mcap_ratio: float = 0.03
    max_buy_tax_percent: float = 10.0
    max_sell_tax_percent: float = 15.0
    
    # Seuils de sortie
    take_profit_targets: List[Dict[str, float]] = None
    stop_loss_percent: float = 20.0
    max_hold_time_hours: float = 48.0
    trailing_stop_percent: float = 15.0
    
    # Paramètres de transaction
    gas_boost_percent: float = 10.0
    slippage_tolerance_percent: float = 5.0
    
    # Facteurs de marché
    market_condition_factor: float = 1.0
    
    def __post_init__(self):
        """Initialiser des valeurs par défaut pour les listes."""
        if self.take_profit_targets is None:
            self.take_profit_targets = [
                {"percentage": 30, "roi_target": 2.0},  # 30% à 2x
                {"percentage": 40, "roi_target": 3.0},  # 40% à 3x
                {"percentage": 30, "roi_target": 5.0}   # 30% à 5x
            ]

class DynamicThresholdManager:
    """
    Gestionnaire de seuils dynamiques qui ajuste automatiquement les points 
    d'entrée et de sortie pour le sniping de tokens.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise le gestionnaire de seuils dynamiques.
        
        Args:
            config: Configuration optionnelle
        """
        self.config = config or {}
        self.data_path = self.config.get("thresholds_data_path", "data/dynamic_thresholds.json")
        
        # Thresholds par blockchain et catégorie de token
        self.thresholds: Dict[str, Dict[str, ThresholdSet]] = {
            "solana": {},
            "avax": {},
            "ethereum": {},
            "default": {}
        }
        
        # Facteurs de marché actuels (mise à jour périodique)
        self.market_factors = {
            "solana": 1.0,
            "avax": 1.0,
            "ethereum": 1.0,
            "overall": 1.0
        }
        
        # Historique des performances
        self.performance_history: List[Dict[str, Any]] = []
        
        # Charger les données existantes
        self._load_thresholds()
        
        # Initialiser les seuils par défaut pour chaque catégorie
        self._initialize_default_thresholds()
    
    def _load_thresholds(self):
        """Charge les seuils depuis le fichier JSON."""
        try:
            if not os.path.exists(self.data_path):
                return
                
            with open(self.data_path, "r") as f:
                data = json.load(f)
                
            # Charger les seuils par blockchain et catégorie
            for blockchain, categories in data.get("thresholds", {}).items():
                if blockchain not in self.thresholds:
                    self.thresholds[blockchain] = {}
                    
                for category, threshold_data in categories.items():
                    # Convertir les données en ThresholdSet
                    threshold_set = ThresholdSet(
                        min_liquidity_usd=threshold_data.get("min_liquidity_usd", 5000.0),
                        max_initial_mcap_usd=threshold_data.get("max_initial_mcap_usd", 2000000.0),
                        min_liquidity_to_mcap_ratio=threshold_data.get("min_liquidity_to_mcap_ratio", 0.03),
                        max_buy_tax_percent=threshold_data.get("max_buy_tax_percent", 10.0),
                        max_sell_tax_percent=threshold_data.get("max_sell_tax_percent", 15.0),
                        take_profit_targets=threshold_data.get("take_profit_targets"),
                        stop_loss_percent=threshold_data.get("stop_loss_percent", 20.0),
                        max_hold_time_hours=threshold_data.get("max_hold_time_hours", 48.0),
                        trailing_stop_percent=threshold_data.get("trailing_stop_percent", 15.0),
                        gas_boost_percent=threshold_data.get("gas_boost_percent", 10.0),
                        slippage_tolerance_percent=threshold_data.get("slippage_tolerance_percent", 5.0),
                        market_condition_factor=threshold_data.get("market_condition_factor", 1.0)
                    )
                    
                    self.thresholds[blockchain][category] = threshold_set
            
            # Charger les facteurs de marché
            if "market_factors" in data:
                self.market_factors = data["market_factors"]
                
            # Charger l'historique des performances
            if "performance_history" in data:
                self.performance_history = data["performance_history"]
                
            logger.info(f"Loaded threshold data from {self.data_path}")
            
        except Exception as e:
            logger.error(f"Error loading threshold data: {str(e)}")
    
    def _initialize_default_thresholds(self):
        """Initialise les seuils par défaut pour chaque catégorie si non existants."""
        # Catégories par défaut
        categories = ["meme", "defi", "game", "ai", "utility"]
        
        # Pour chaque blockchain
        for blockchain in self.thresholds.keys():
            for category in categories:
                # Si la catégorie n'existe pas, créer des seuils par défaut
                if category not in self.thresholds[blockchain]:
                    # Ajuster les paramètres par défaut selon la blockchain et la catégorie
                    if category == "meme":
                        self.thresholds[blockchain][category] = ThresholdSet(
                            min_liquidity_usd=10000.0 if blockchain == "ethereum" else 5000.0,
                            max_initial_mcap_usd=3000000.0,
                            take_profit_targets=[
                                {"percentage": 30, "roi_target": 2.0},
                                {"percentage": 40, "roi_target": 3.5},
                                {"percentage": 30, "roi_target": 5.0}
                            ],
                            stop_loss_percent=25.0,
                            trailing_stop_percent=15.0,
                            slippage_tolerance_percent=10.0
                        )
                    elif category == "defi":
                        self.thresholds[blockchain][category] = ThresholdSet(
                            min_liquidity_usd=20000.0,
                            max_initial_mcap_usd=5000000.0,
                            min_liquidity_to_mcap_ratio=0.05,
                            take_profit_targets=[
                                {"percentage": 40, "roi_target": 1.5},
                                {"percentage": 40, "roi_target": 2.5},
                                {"percentage": 20, "roi_target": 4.0}
                            ],
                            max_hold_time_hours=72.0,
                            slippage_tolerance_percent=3.0
                        )
                    elif category == "game":
                        self.thresholds[blockchain][category] = ThresholdSet(
                            min_liquidity_usd=15000.0,
                            max_initial_mcap_usd=4000000.0,
                            take_profit_targets=[
                                {"percentage": 25, "roi_target": 1.8},
                                {"percentage": 50, "roi_target": 3.0},
                                {"percentage": 25, "roi_target": 5.0}
                            ],
                            max_hold_time_hours=120.0
                        )
                    else:
                        # Catégories utility et ai
                        self.thresholds[blockchain][category] = ThresholdSet()
    
    def get_thresholds(self, blockchain: str, category: str) -> ThresholdSet:
        """
        Récupère les seuils appropriés pour une blockchain et une catégorie.
        
        Args:
            blockchain: Nom de la blockchain (solana, avax, ethereum)
            category: Catégorie du token (meme, defi, game, ai, utility)
            
        Returns:
            Ensemble de seuils (ThresholdSet)
        """
        # Normaliser les noms
        blockchain = blockchain.lower()
        category = category.lower()
        
        # Vérifier si la blockchain est supportée
        if blockchain not in self.thresholds:
            blockchain = "default"
            
        # Récupérer les seuils pour la catégorie
        if category in self.thresholds[blockchain]:
            thresholds = self.thresholds[blockchain][category]
        elif category in self.thresholds["default"]:
            thresholds = self.thresholds["default"][category]
        else:
            # Seuils génériques par défaut
            thresholds = ThresholdSet()
            
        # Appliquer les ajustements en fonction des conditions de marché
        adjusted_thresholds = self._adjust_for_market_conditions(thresholds, blockchain)
        
        return adjusted_thresholds
    
    def _adjust_for_market_conditions(self, thresholds: ThresholdSet, blockchain: str) -> ThresholdSet:
        """
        Ajuste les seuils en fonction des conditions actuelles du marché.
        
        Args:
            thresholds: Seuils de base
            blockchain: Blockchain concernée
            
        Returns:
            Seuils ajustés
        """
        # Créer une copie pour éviter de modifier l'original
        adjusted = ThresholdSet(
            min_liquidity_usd=thresholds.min_liquidity_usd,
            max_initial_mcap_usd=thresholds.max_initial_mcap_usd,
            min_liquidity_to_mcap_ratio=thresholds.min_liquidity_to_mcap_ratio,
            max_buy_tax_percent=thresholds.max_buy_tax_percent,
            max_sell_tax_percent=thresholds.max_sell_tax_percent,
            take_profit_targets=thresholds.take_profit_targets.copy() if thresholds.take_profit_targets else None,
            stop_loss_percent=thresholds.stop_loss_percent,
            max_hold_time_hours=thresholds.max_hold_time_hours,
            trailing_stop_percent=thresholds.trailing_stop_percent,
            gas_boost_percent=thresholds.gas_boost_percent,
            slippage_tolerance_percent=thresholds.slippage_tolerance_percent,
            market_condition_factor=thresholds.market_condition_factor
        )
        
        # Facteur de marché blockchain-spécifique
        blockchain_factor = self.market_factors.get(blockchain, 1.0)
        
        # Facteur global
        overall_factor = self.market_factors.get("overall", 1.0)
        
        # Facteur combiné
        combined_factor = (blockchain_factor + overall_factor) / 2
        
        # Ajuster les seuils en fonction des conditions de marché
        # En marché baissier (factor < 1), on est plus conservateur
        # En marché haussier (factor > 1), on est plus agressif
        
        # Ajuster les seuils d'entrée
        adjusted.min_liquidity_usd *= (1.5 - combined_factor * 0.5)  # Plus élevé en marché baissier
        adjusted.max_initial_mcap_usd *= combined_factor  # Plus élevé en marché haussier
        
        # Ajuster les seuils de sortie
        adjusted.stop_loss_percent *= (0.8 + combined_factor * 0.2)  # Plus serré en marché baissier
        
        # Ajuster les cibles de prise de profit
        if adjusted.take_profit_targets:
            for i, target in enumerate(adjusted.take_profit_targets):
                # En marché haussier, viser des profits plus élevés
                # En marché baissier, prendre profit plus tôt
                adjusted.take_profit_targets[i]["roi_target"] = target["roi_target"] * combined_factor
        
        # Ajuster le temps maximum de détention (tenir plus longtemps en marché haussier)
        adjusted.max_hold_time_hours *= combined_factor
        
        # Ajuster le trailing stop (plus serré en marché baissier)
        adjusted.trailing_stop_percent *= (0.8 + combined_factor * 0.2)
        
        return adjusted
    
    async def update_market_conditions(self, blockchain_client) -> None:
        """
        Met à jour les facteurs de marché en fonction des conditions actuelles.
        
        Args:
            blockchain_client: Client blockchain pour les requêtes
        """
        try:
            # Obtenir des indicateurs de marché pour différentes blockchains
            market_indicators = await blockchain_client.get_market_indicators()
            
            # Mettre à jour les facteurs pour chaque blockchain
            for blockchain, indicators in market_indicators.items():
                if blockchain in self.market_factors:
                    # Calculer un facteur de marché entre 0.5 (très baissier) et 1.5 (très haussier)
                    # 1.0 est neutre
                    
                    # Indicateurs typiques: tendance de prix, volume, sentiment, volatilité
                    price_trend = indicators.get("price_trend", 0)  # -100 à +100
                    volume_change = indicators.get("volume_change", 0)  # -100 à +100
                    sentiment = indicators.get("sentiment", 0)  # -100 à +100
                    volatility = indicators.get("volatility", 50)  # 0 à 100
                    
                    # Calculer un score composite
                    composite_score = (price_trend + volume_change + sentiment) / 300  # -1 à +1
                    
                    # Convertir en facteur de marché
                    market_factor = 1.0 + composite_score
                    
                    # Ajuster en fonction de la volatilité (plus conservateur en haute volatilité)
                    volatility_adjustment = 1.0 - (volatility - 50) / 100
                    market_factor *= volatility_adjustment
                    
                    # Limiter entre 0.5 et 1.5
                    market_factor = max(0.5, min(1.5, market_factor))
                    
                    self.market_factors[blockchain] = market_factor
            
            # Calculer un facteur global
            self.market_factors["overall"] = sum(v for k, v in self.market_factors.items() if k != "overall") / 3
            
            logger.info(f"Updated market factors: {self.market_factors}")
            
            # Sauvegarder les données mises à jour
            self._save_thresholds()
            
        except Exception as e:
            logger.error(f"Error updating market conditions: {str(e)}")
    
    def record_trade_performance(self, trade_data: Dict[str, Any]) -> None:
        """
        Enregistre les performances d'un trade pour améliorer les seuils.
        
        Args:
            trade_data: Données du trade
        """
        try:
            # Ajouter le timestamp
            trade_data["timestamp"] = datetime.now().isoformat()
            
            # Ajouter aux données d'historique
            self.performance_history.append(trade_data)
            
            # Limiter l'historique aux 1000 derniers trades
            if len(self.performance_history) > 1000:
                self.performance_history = self.performance_history[-1000:]
            
            # Mise à jour des seuils en fonction de la nouvelle donnée
            self._update_thresholds_from_performance()
            
            # Sauvegarder les données
            self._save_thresholds()
            
        except Exception as e:
            logger.error(f"Error recording trade performance: {str(e)}")
    
    def _update_thresholds_from_performance(self) -> None:
        """Met à jour les seuils en fonction des performances récentes."""
        # Récupérer les trades des 30 derniers jours
        recent_threshold = datetime.now() - timedelta(days=30)
        recent_trades = [
            trade for trade in self.performance_history
            if datetime.fromisoformat(trade["timestamp"]) > recent_threshold
        ]
        
        if len(recent_trades) < 10:
            # Pas assez de données pour ajuster
            return
            
        # Organiser les trades par blockchain et catégorie
        by_blockchain_category = {}
        for trade in recent_trades:
            blockchain = trade.get("blockchain", "").lower()
            category = trade.get("category", "").lower()
            
            if not blockchain or not category:
                continue
                
            if blockchain not in by_blockchain_category:
                by_blockchain_category[blockchain] = {}
                
            if category not in by_blockchain_category[blockchain]:
                by_blockchain_category[blockchain][category] = []
                
            by_blockchain_category[blockchain][category].append(trade)
        
        # Analyser chaque groupe pour ajuster les seuils
        for blockchain, categories in by_blockchain_category.items():
            for category, trades in categories.items():
                if len(trades) < 5:
                    continue
                    
                # Calculer des statistiques
                roi_values = [trade.get("roi", 0) for trade in trades]
                successful = [trade for trade in trades if trade.get("status") == "success"]
                failed = [trade for trade in trades if trade.get("status") == "failed"]
                
                success_rate = len(successful) / len(trades) if trades else 0
                avg_roi = sum(roi_values) / len(roi_values) if roi_values else 0
                
                # Récupérer les seuils actuels
                current_thresholds = self.get_thresholds(blockchain, category)
                
                # Ajuster les seuils en fonction des performances
                if blockchain in self.thresholds and category in self.thresholds[blockchain]:
                    threshold_set = self.thresholds[blockchain][category]
                    
                    # Analyser les raisons d'échec
                    failed_liquidity = [t for t in failed if t.get("failure_reason") == "low_liquidity"]
                    failed_slippage = [t for t in failed if t.get("failure_reason") == "high_slippage"]
                    failed_tax = [t for t in failed if t.get("failure_reason") == "high_tax"]
                    
                    # Ajuster les seuils d'entrée
                    if failed_liquidity and len(failed_liquidity) / len(trades) > 0.2:
                        # Trop d'échecs liés à la liquidité, augmenter le seuil
                        threshold_set.min_liquidity_usd *= 1.1
                        
                    if failed_tax and len(failed_tax) / len(trades) > 0.2:
                        # Trop d'échecs liés aux taxes, réduire les seuils
                        threshold_set.max_buy_tax_percent *= 0.9
                        threshold_set.max_sell_tax_percent *= 0.9
                        
                    if failed_slippage and len(failed_slippage) / len(trades) > 0.2:
                        # Trop d'échecs liés au slippage, ajuster
                        threshold_set.slippage_tolerance_percent *= 1.1
                    
                    # Ajuster les seuils de sortie en fonction du ROI moyen
                    if success_rate > 0.7 and avg_roi > 0:
                        # Bon taux de succès, ajuster les cibles de profit
                        for i, target in enumerate(threshold_set.take_profit_targets):
                            # Ajuster progressivement vers des objectifs plus élevés
                            current = target["roi_target"]
                            ideal = avg_roi * (i + 1) / len(threshold_set.take_profit_targets)
                            # Ajustement progressif (20% vers l'idéal)
                            threshold_set.take_profit_targets[i]["roi_target"] = current * 0.8 + ideal * 0.2
                    
                    # Sauvegarder les changements
                    self.thresholds[blockchain][category] = threshold_set
    
    def get_entry_decision(self, token_data: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Décide si un token doit être acheté en fonction des seuils dynamiques.
        
        Args:
            token_data: Données du token
            
        Returns:
            Tuple contenant:
            - Décision d'entrée (True/False)
            - Raison de la décision
            - Paramètres recommandés pour l'achat
        """
        blockchain = token_data.get("blockchain", "").lower()
        category = token_data.get("category", "").lower()
        
        if not blockchain or not category:
            return False, "Données blockchain/catégorie manquantes", {}
            
        # Obtenir les seuils appropriés
        thresholds = self.get_thresholds(blockchain, category)
        
        # Vérifier les critères d'entrée
        reasons = []
        
        # Vérifier la liquidité
        liquidity = token_data.get("liquidity_usd", 0)
        if liquidity < thresholds.min_liquidity_usd:
            reasons.append(f"Liquidité trop faible: ${liquidity:.2f} < ${thresholds.min_liquidity_usd:.2f}")
            
        # Vérifier le market cap initial
        market_cap = token_data.get("market_cap_usd", 0)
        if market_cap > thresholds.max_initial_mcap_usd:
            reasons.append(f"Market cap trop élevé: ${market_cap:.2f} > ${thresholds.max_initial_mcap_usd:.2f}")
            
        # Vérifier le ratio liquidité/market cap
        if market_cap > 0:
            ratio = liquidity / market_cap
            if ratio < thresholds.min_liquidity_to_mcap_ratio:
                reasons.append(f"Ratio liquidité/mcap trop faible: {ratio:.2%} < {thresholds.min_liquidity_to_mcap_ratio:.2%}")
                
        # Vérifier les taxes
        buy_tax = token_data.get("buy_tax_percent", 0)
        sell_tax = token_data.get("sell_tax_percent", 0)
        
        if buy_tax > thresholds.max_buy_tax_percent:
            reasons.append(f"Taxe d'achat trop élevée: {buy_tax:.1f}% > {thresholds.max_buy_tax_percent:.1f}%")
            
        if sell_tax > thresholds.max_sell_tax_percent:
            reasons.append(f"Taxe de vente trop élevée: {sell_tax:.1f}% > {thresholds.max_sell_tax_percent:.1f}%")
            
        # Vérifier les signaux de risque
        risk_signals = token_data.get("risk_signals", [])
        critical_risks = [r for r in risk_signals if r.get("severity") == "critical"]
        high_risks = [r for r in risk_signals if r.get("severity") == "high"]
        
        if critical_risks:
            reasons.append(f"{len(critical_risks)} risques critiques détectés")
            
        if len(high_risks) > 2:
            reasons.append(f"{len(high_risks)} risques élevés détectés")
            
        # Décision finale
        decision = len(reasons) == 0
        
        # Paramètres recommandés pour l'achat
        recommended_params = {
            "slippage_tolerance_percent": thresholds.slippage_tolerance_percent,
            "gas_boost_percent": thresholds.gas_boost_percent,
            "take_profit_targets": thresholds.take_profit_targets,
            "stop_loss_percent": thresholds.stop_loss_percent,
            "trailing_stop_percent": thresholds.trailing_stop_percent,
            "max_hold_time_hours": thresholds.max_hold_time_hours
        }
        
        reason_str = ", ".join(reasons) if reasons else "Tous les critères sont satisfaits"
        
        return decision, reason_str, recommended_params
    
    def get_exit_recommendation(self, position_data: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Décide si une position doit être vendue en fonction des seuils dynamiques.
        
        Args:
            position_data: Données de la position
            
        Returns:
            Tuple contenant:
            - Décision de sortie (True/False)
            - Raison de la décision
            - Paramètres recommandés pour la vente
        """
        blockchain = position_data.get("blockchain", "").lower()
        category = position_data.get("category", "").lower()
        
        # Obtenir les seuils appropriés
        thresholds = self.get_thresholds(blockchain, category)
        
        # Paramètres de la position
        entry_price = position_data.get("entry_price", 0)
        current_price = position_data.get("current_price", 0)
        highest_price = position_data.get("highest_price", current_price)
        entry_time = position_data.get("entry_time")
        current_time = time.time()
        
        if not entry_price or not current_price or not entry_time:
            return False, "Données de position incomplètes", {}
            
        # Calculer le ROI actuel
        roi = (current_price / entry_price) - 1 if entry_price > 0 else 0
        
        # Calculer le temps écoulé depuis l'entrée (en heures)
        hours_elapsed = (current_time - entry_time) / 3600
        
        # Vérifier les critères de sortie
        reasons = []
        
        # Vérifier le stop loss
        loss_percent = (entry_price - current_price) / entry_price * 100 if entry_price > 0 else 0
        if loss_percent >= thresholds.stop_loss_percent:
            reasons.append(f"Stop loss déclenché: -{loss_percent:.1f}% (seuil: -{thresholds.stop_loss_percent:.1f}%)")
            
        # Vérifier le trailing stop
        if highest_price > 0:
            drop_from_high = (highest_price - current_price) / highest_price * 100
            if drop_from_high >= thresholds.trailing_stop_percent:
                reasons.append(f"Trailing stop déclenché: -{drop_from_high:.1f}% depuis le pic (seuil: -{thresholds.trailing_stop_percent:.1f}%)")
                
        # Vérifier le temps maximum de détention
        if hours_elapsed >= thresholds.max_hold_time_hours:
            reasons.append(f"Temps maximum atteint: {hours_elapsed:.1f}h (max: {thresholds.max_hold_time_hours:.1f}h)")
            
        # Vérifier les cibles de prise de profit
        for target in thresholds.take_profit_targets:
            target_roi = target["roi_target"] - 1  # Convertir en pourcentage de ROI
            if roi >= target_roi:
                percentage = target["percentage"]
                reasons.append(f"Cible de profit atteinte: +{roi*100:.1f}% ≥ +{target_roi*100:.1f}% (vendre {percentage}%)")
                break
        
        # Signaux de risque supplémentaires
        risk_signals = position_data.get("risk_signals", [])
        for signal in risk_signals:
            if signal.get("severity") == "critical":
                reasons.append(f"Signal de risque critique: {signal.get('message', '')}")
        
        # Décision finale
        decision = len(reasons) > 0
        
        # Pourcentage à vendre
        sell_percentage = 100  # Par défaut, tout vendre
        
        # Si c'est une prise de profit, ajuster le pourcentage selon la cible
        if decision and roi > 0:
            for target in thresholds.take_profit_targets:
                target_roi = target["roi_target"] - 1
                if roi >= target_roi:
                    sell_percentage = target["percentage"]
                    break
        
        # Paramètres recommandés pour la vente
        recommended_params = {
            "sell_percentage": sell_percentage,
            "slippage_tolerance_percent": thresholds.slippage_tolerance_percent * 1.2,  # Plus de tolérance pour la vente
            "gas_boost_percent": thresholds.gas_boost_percent * 1.5,  # Plus de boost pour la vente
            "reason": reasons[0] if reasons else ""
        }
        
        reason_str = ", ".join(reasons) if reasons else "Aucun critère de sortie déclenché"
        
        return decision, reason_str, recommended_params
    
    def _save_thresholds(self):
        """Sauvegarde les seuils dans le fichier JSON."""
        try:
            # Convertir les ThresholdSet en dictionnaires
            thresholds_data = {}
            for blockchain, categories in self.thresholds.items():
                thresholds_data[blockchain] = {}
                for category, threshold_set in categories.items():
                    thresholds_data[blockchain][category] = {
                        "min_liquidity_usd": threshold_set.min_liquidity_usd,
                        "max_initial_mcap_usd": threshold_set.max_initial_mcap_usd,
                        "min_liquidity_to_mcap_ratio": threshold_set.min_liquidity_to_mcap_ratio,
                        "max_buy_tax_percent": threshold_set.max_buy_tax_percent,
                        "max_sell_tax_percent": threshold_set.max_sell_tax_percent,
                        "take_profit_targets": threshold_set.take_profit_targets,
                        "stop_loss_percent": threshold_set.stop_loss_percent,
                        "max_hold_time_hours": threshold_set.max_hold_time_hours,
                        "trailing_stop_percent": threshold_set.trailing_stop_percent,
                        "gas_boost_percent": threshold_set.gas_boost_percent,
                        "slippage_tolerance_percent": threshold_set.slippage_tolerance_percent,
                        "market_condition_factor": threshold_set.market_condition_factor
                    }
            
            # Créer le dictionnaire complet
            data = {
                "last_updated": datetime.now().isoformat(),
                "thresholds": thresholds_data,
                "market_factors": self.market_factors,
                "performance_history": self.performance_history[-100:]  # Sauvegarder seulement les 100 derniers
            }
            
            # S'assurer que le répertoire existe
            os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
            
            # Sauvegarder les données
            with open(self.data_path, "w") as f:
                json.dump(data, f, indent=2)
                
            logger.info(f"Saved threshold data to {self.data_path}")
            
        except Exception as e:
            logger.error(f"Error saving threshold data: {str(e)}") 