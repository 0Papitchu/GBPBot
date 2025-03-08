#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module d'intégration du reporting Sonic avec le système de rapport global
Permet de collecter, analyser et visualiser les données de performance sur Sonic
"""

import logging
from typing import Dict, List, Optional, Any
import time
from datetime import datetime, timedelta
import json
import os
from enum import Enum

from gbpbot.core.monitoring.base_monitor import BaseMonitor
from gbpbot.core.reporting.metrics_collector import MetricsCollector
from gbpbot.core.reporting.report_manager import ReportManager
from gbpbot.core.reporting.visualization import VisualizationManager

logger = logging.getLogger(__name__)

class MetricType(Enum):
    """Types de métriques supportés par le système de reporting"""
    COUNTER = "counter"      # Compteur incrémental
    GAUGE = "gauge"          # Valeur instantanée
    CUMULATIVE = "cumulative"  # Valeur cumulative
    FINANCIAL = "financial"  # Métrique financière
    RATIO = "ratio"          # Rapport entre deux valeurs


class VisualizationType(Enum):
    """Types de visualisations supportés par le système de reporting"""
    LINE_CHART = "line_chart"
    BAR_CHART = "bar_chart"
    PIE_CHART = "pie_chart"
    HEAT_MAP = "heat_map"
    TIME_SERIES = "time_series"
    COMPARISON_CHART = "comparison_chart"


class AlertPriority(Enum):
    """Niveaux de priorité des alertes"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Metric:
    """Représente une métrique à suivre dans le système de reporting"""
    
    def __init__(
        self,
        name: str,
        metric_type: MetricType,
        description: Optional[str] = None,
        unit: Optional[str] = None
    ):
        self.name = name
        self.metric_type = metric_type
        self.description = description or f"Metric {name}"
        self.unit = unit
        
    def to_dict(self) -> Dict:
        """Convertit la métrique en dictionnaire"""
        return {
            "name": self.name,
            "type": self.metric_type.value,
            "description": self.description,
            "unit": self.unit
        }


class Visualization:
    """Représente une visualisation dans le système de reporting"""
    
    def __init__(
        self,
        name: str,
        visualization_type: VisualizationType,
        title: Optional[str] = None,
        description: Optional[str] = None,
        metrics: Optional[List[str]] = None,
        config: Optional[Dict] = None
    ):
        self.name = name
        self.visualization_type = visualization_type
        self.title = title or name.replace("_", " ").title()
        self.description = description
        self.metrics = metrics or []
        self.config = config or {}
        
    def to_dict(self) -> Dict:
        """Convertit la visualisation en dictionnaire"""
        return {
            "name": self.name,
            "type": self.visualization_type.value,
            "title": self.title,
            "description": self.description,
            "metrics": self.metrics,
            "config": self.config
        }


class Alert:
    """Représente une alerte dans le système de reporting"""
    
    def __init__(
        self,
        name: str,
        description: str,
        priority: AlertPriority,
        condition: Optional[str] = None,
        metrics: Optional[List[str]] = None
    ):
        self.name = name
        self.description = description
        self.priority = priority
        self.condition = condition
        self.metrics = metrics or []
        
    def to_dict(self) -> Dict:
        """Convertit l'alerte en dictionnaire"""
        return {
            "name": self.name,
            "description": self.description,
            "priority": self.priority.value,
            "condition": self.condition,
            "metrics": self.metrics
        }


class SonicMetricsCollector(MetricsCollector):
    """Collecteur de métriques spécifique à l'écosystème Sonic"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialise le collecteur de métriques Sonic
        
        Args:
            config: Configuration du collecteur
        """
        super().__init__()
        self.config = config or {}
        self.metrics_data = {}
        
    def collect_transaction_metrics(self, transaction_data: Dict) -> Dict:
        """
        Collecte les métriques d'une transaction Sonic
        
        Args:
            transaction_data: Données de la transaction
            
        Returns:
            Métriques collectées
        """
        try:
            metrics = {}
            
            # Extraction des données de base
            tx_hash = transaction_data.get("hash")
            timestamp = transaction_data.get("timestamp", time.time())
            gas_used = transaction_data.get("gas_used", 0)
            gas_price = transaction_data.get("gas_price", 0)
            success = transaction_data.get("success", False)
            
            # Calcul des métriques
            gas_cost = gas_used * gas_price
            execution_time = transaction_data.get("execution_time_ms", 0)
            
            # Construction des métriques
            metrics["sonic_transactions_count"] = 1
            metrics["sonic_gas_spent"] = gas_cost
            
            if "profit_loss" in transaction_data:
                metrics["sonic_profit_loss"] = transaction_data["profit_loss"]
                
            if success:
                metrics["sonic_successful_transactions"] = 1
                
                if transaction_data.get("transaction_type") == "arbitrage":
                    metrics["sonic_successful_arbitrages"] = 1
                    
            # Métriques de performance
            metrics["sonic_transaction_execution_time"] = execution_time
            
            # Métriques de DEX
            dex = transaction_data.get("dex")
            if dex:
                metrics[f"sonic_{dex.lower()}_transactions"] = 1
                if success:
                    metrics[f"sonic_{dex.lower()}_successful_transactions"] = 1
                if "profit_loss" in transaction_data:
                    metrics[f"sonic_{dex.lower()}_profit_loss"] = transaction_data["profit_loss"]
            
            # Stockage des métriques
            self._store_metrics(tx_hash, metrics, timestamp)
            
            return metrics
            
        except Exception as e:
            logger.error("Erreur lors de la collecte des métriques de transaction: %s", str(e), exc_info=True)
            return {}
    
    def collect_market_metrics(self, market_data: Dict) -> Dict:
        """
        Collecte les métriques de marché Sonic
        
        Args:
            market_data: Données de marché
            
        Returns:
            Métriques collectées
        """
        try:
            metrics = {}
            
            # Extraction des données de base
            timestamp = market_data.get("timestamp", time.time())
            
            # Métriques de volume
            if "volume_usd" in market_data:
                metrics["sonic_market_volume_usd"] = market_data["volume_usd"]
                
            # Métriques de liquidité
            if "liquidity" in market_data:
                for dex, liquidity in market_data["liquidity"].items():
                    metrics[f"sonic_{dex.lower()}_liquidity"] = liquidity
                    
            # Métriques de prix
            if "price_data" in market_data:
                for token, price_info in market_data["price_data"].items():
                    metrics[f"sonic_{token.lower()}_price"] = price_info.get("price", 0)
                    metrics[f"sonic_{token.lower()}_24h_change_pct"] = price_info.get("24h_change_pct", 0)
            
            # Stockage des métriques
            identifier = f"market_{int(timestamp)}"
            self._store_metrics(identifier, metrics, timestamp)
            
            return metrics
            
        except Exception as e:
            logger.error("Erreur lors de la collecte des métriques de marché: %s", str(e), exc_info=True)
            return {}
    
    def collect_system_metrics(self, system_data: Dict) -> Dict:
        """
        Collecte les métriques système pour Sonic
        
        Args:
            system_data: Données système
            
        Returns:
            Métriques collectées
        """
        try:
            metrics = {}
            
            # Extraction des données de base
            timestamp = system_data.get("timestamp", time.time())
            
            # Métriques réseau
            if "network" in system_data:
                network_data = system_data["network"]
                metrics["sonic_network_latency_ms"] = network_data.get("latency_ms", 0)
                metrics["sonic_network_congestion"] = network_data.get("congestion", 0)
                metrics["sonic_network_gas_price"] = network_data.get("gas_price", 0)
            
            # Métriques d'opportunités
            if "opportunities" in system_data:
                opportunities_data = system_data["opportunities"]
                metrics["sonic_opportunities_detected"] = opportunities_data.get("detected", 0)
                metrics["sonic_opportunities_executed"] = opportunities_data.get("executed", 0)
                metrics["sonic_opportunities_successful"] = opportunities_data.get("successful", 0)
            
            # Stockage des métriques
            identifier = f"system_{int(timestamp)}"
            self._store_metrics(identifier, metrics, timestamp)
            
            return metrics
            
        except Exception as e:
            logger.error("Erreur lors de la collecte des métriques système: %s", str(e), exc_info=True)
            return {}
    
    def _store_metrics(self, identifier: str, metrics: Dict, timestamp: float) -> None:
        """
        Stocke les métriques collectées
        
        Args:
            identifier: Identifiant des métriques
            metrics: Métriques à stocker
            timestamp: Horodatage des métriques
        """
        if identifier not in self.metrics_data:
            self.metrics_data[identifier] = {
                "timestamp": timestamp,
                "metrics": {}
            }
            
        self.metrics_data[identifier]["metrics"].update(metrics)
    
    def get_metrics(self, start_time: Optional[float] = None, end_time: Optional[float] = None) -> Dict:
        """
        Récupère les métriques collectées dans une plage de temps
        
        Args:
            start_time: Timestamp de début
            end_time: Timestamp de fin
            
        Returns:
            Métriques collectées
        """
        result = {}
        
        # Filtre par plage de temps
        for identifier, data in self.metrics_data.items():
            timestamp = data["timestamp"]
            
            if start_time and timestamp < start_time:
                continue
                
            if end_time and timestamp > end_time:
                continue
                
            result[identifier] = data.copy()
            
        return result
    
    def calculate_aggregated_metrics(self, time_range_hours: int = 24) -> Dict:
        """
        Calcule des métriques agrégées sur une période donnée
        
        Args:
            time_range_hours: Nombre d'heures pour l'agrégation
            
        Returns:
            Métriques agrégées
        """
        try:
            # Définir la plage de temps
            end_time = time.time()
            start_time = end_time - (time_range_hours * 3600)
            
            # Récupérer les métriques dans la plage
            filtered_metrics = self.get_metrics(start_time, end_time)
            
            # Initialiser les agrégats
            aggregates = {
                "sonic_transactions_count": 0,
                "sonic_gas_spent": 0,
                "sonic_profit_loss": 0,
                "sonic_successful_transactions": 0,
                "sonic_successful_arbitrages": 0,
                "sonic_avg_transaction_execution_time": 0,
                "sonic_spiritswap_profit_loss": 0,
                "sonic_spookyswap_profit_loss": 0,
                "sonic_opportunities_detected": 0,
                "sonic_opportunities_executed": 0,
                "sonic_opportunities_successful": 0,
            }
            
            # Compteurs pour les moyennes
            counters = {
                "execution_time": 0,
            }
            
            # Agréger les métriques
            for data in filtered_metrics.values():
                metrics = data["metrics"]
                
                for key, value in metrics.items():
                    if key in aggregates:
                        aggregates[key] += value
                        
                    if key == "sonic_transaction_execution_time":
                        counters["execution_time"] += 1
            
            # Calculer les moyennes
            if counters["execution_time"] > 0:
                aggregates["sonic_avg_transaction_execution_time"] = (
                    aggregates["sonic_transaction_execution_time"] / counters["execution_time"]
                )
                
            # Calculer les métriques dérivées
            if aggregates["sonic_transactions_count"] > 0:
                aggregates["sonic_success_rate"] = (
                    aggregates["sonic_successful_transactions"] / aggregates["sonic_transactions_count"] * 100
                )
                
            if aggregates["sonic_opportunities_detected"] > 0:
                aggregates["sonic_opportunity_execution_rate"] = (
                    aggregates["sonic_opportunities_executed"] / aggregates["sonic_opportunities_detected"] * 100
                )
                
            if aggregates["sonic_opportunities_executed"] > 0:
                aggregates["sonic_opportunity_success_rate"] = (
                    aggregates["sonic_opportunities_successful"] / aggregates["sonic_opportunities_executed"] * 100
                )
            
            return {
                "time_range_hours": time_range_hours,
                "start_time": start_time,
                "end_time": end_time,
                "metrics": aggregates
            }
            
        except Exception as e:
            logger.error("Erreur lors du calcul des métriques agrégées: %s", str(e), exc_info=True)
            return {}


class SonicReportingIntegration:
    """Intégration du reporting Sonic avec le système de rapport global"""
    
    def __init__(self, global_reporting_system: ReportManager):
        """
        Initialise l'intégration de reporting Sonic
        
        Args:
            global_reporting_system: Système de rapport global
        """
        self.global_reporting = global_reporting_system
        self.metrics_collector = SonicMetricsCollector()
        
    def register_with_global_system(self) -> None:
        """Enregistre les métriques Sonic avec le système de rapport global"""
        # Enregistrement des métriques standard
        self.global_reporting.register_metrics([
            Metric("sonic_transactions_count", MetricType.COUNTER, "Nombre de transactions Sonic"),
            Metric("sonic_gas_spent", MetricType.CUMULATIVE, "Gas total dépensé sur Sonic", "FTM"),
            Metric("sonic_profit_loss", MetricType.FINANCIAL, "Profit/Perte total sur Sonic", "USD"),
            Metric("sonic_successful_transactions", MetricType.COUNTER, "Nombre de transactions réussies sur Sonic"),
            Metric("sonic_successful_arbitrages", MetricType.COUNTER, "Nombre d'arbitrages réussis sur Sonic"),
            Metric("sonic_avg_transaction_execution_time", MetricType.GAUGE, "Temps d'exécution moyen des transactions Sonic", "ms"),
            Metric("sonic_spiritswap_profit_loss", MetricType.FINANCIAL, "Profit/Perte sur SpiritSwap", "USD"),
            Metric("sonic_spookyswap_profit_loss", MetricType.FINANCIAL, "Profit/Perte sur SpookySwap", "USD"),
            Metric("sonic_opportunities_detected", MetricType.COUNTER, "Nombre d'opportunités détectées sur Sonic"),
            Metric("sonic_opportunities_executed", MetricType.COUNTER, "Nombre d'opportunités exécutées sur Sonic"),
            Metric("sonic_opportunities_successful", MetricType.COUNTER, "Nombre d'opportunités réussies sur Sonic"),
            Metric("sonic_success_rate", MetricType.RATIO, "Taux de réussite des transactions Sonic", "%"),
            Metric("sonic_opportunity_execution_rate", MetricType.RATIO, "Taux d'exécution des opportunités Sonic", "%"),
            Metric("sonic_opportunity_success_rate", MetricType.RATIO, "Taux de réussite des opportunités Sonic", "%"),
        ])
        
        # Enregistrement des visualisations spécifiques à Sonic
        self.global_reporting.register_visualizations([
            Visualization(
                "sonic_vs_other_chains", 
                VisualizationType.COMPARISON_CHART,
                "Comparaison Sonic vs Autres Chaînes",
                "Comparaison des performances entre Sonic et les autres blockchains",
                metrics=["sonic_profit_loss", "solana_profit_loss", "avax_profit_loss"]
            ),
            Visualization(
                "sonic_profit_by_dex", 
                VisualizationType.PIE_CHART,
                "Répartition des Profits par DEX Sonic",
                "Répartition des profits par DEX sur Sonic",
                metrics=["sonic_spiritswap_profit_loss", "sonic_spookyswap_profit_loss"]
            ),
            Visualization(
                "sonic_historical_performance", 
                VisualizationType.TIME_SERIES,
                "Performance Historique Sonic",
                "Évolution des performances sur Sonic au fil du temps",
                metrics=["sonic_profit_loss", "sonic_transactions_count", "sonic_success_rate"]
            ),
            Visualization(
                "sonic_opportunities_funnel", 
                VisualizationType.BAR_CHART,
                "Entonnoir d'Opportunités Sonic",
                "Progression des opportunités détectées jusqu'à exécution réussie",
                metrics=[
                    "sonic_opportunities_detected", 
                    "sonic_opportunities_executed", 
                    "sonic_opportunities_successful"
                ]
            )
        ])
        
        # Configuration des alertes
        self.global_reporting.register_alerts([
            Alert(
                "sonic_high_opportunity", 
                "Opportunité d'arbitrage Sonic >3%", 
                AlertPriority.HIGH,
                condition="opportunity.price_diff_pct > 3.0",
                metrics=["sonic_opportunities_detected"]
            ),
            Alert(
                "sonic_network_congestion", 
                "Congestion réseau Sonic détectée", 
                AlertPriority.MEDIUM,
                condition="network.congestion > 0.8",
                metrics=["sonic_network_congestion"]
            ),
            Alert(
                "sonic_liquidity_drop",
                "Chute de liquidité importante sur Sonic",
                AlertPriority.HIGH,
                condition="liquidity_delta_pct < -30",
                metrics=["sonic_spiritswap_liquidity", "sonic_spookyswap_liquidity"]
            ),
            Alert(
                "sonic_gas_price_spike",
                "Pic du prix du gas sur Sonic",
                AlertPriority.MEDIUM,
                condition="gas_price > 3 * avg_gas_price",
                metrics=["sonic_network_gas_price"]
            )
        ])
        
        logger.info("Métriques, visualisations et alertes Sonic enregistrées avec succès")
    
    def add_transaction_data(self, transaction_data: Dict) -> None:
        """
        Ajoute des données de transaction pour traitement
        
        Args:
            transaction_data: Données de transaction
        """
        # Collecter les métriques
        metrics = self.metrics_collector.collect_transaction_metrics(transaction_data)
        
        # Envoyer au système global
        self.global_reporting.update_metrics(metrics)
        
        # Vérifier les conditions d'alerte
        self._check_transaction_alerts(transaction_data, metrics)
        
    def add_market_data(self, market_data: Dict) -> None:
        """
        Ajoute des données de marché pour traitement
        
        Args:
            market_data: Données de marché
        """
        # Collecter les métriques
        metrics = self.metrics_collector.collect_market_metrics(market_data)
        
        # Envoyer au système global
        self.global_reporting.update_metrics(metrics)
        
        # Vérifier les conditions d'alerte
        self._check_market_alerts(market_data, metrics)
        
    def add_system_data(self, system_data: Dict) -> None:
        """
        Ajoute des données système pour traitement
        
        Args:
            system_data: Données système
        """
        # Collecter les métriques
        metrics = self.metrics_collector.collect_system_metrics(system_data)
        
        # Envoyer au système global
        self.global_reporting.update_metrics(metrics)
        
        # Vérifier les conditions d'alerte
        self._check_system_alerts(system_data, metrics)
        
    def generate_sonic_report(self, time_range_hours: int = 24) -> Dict:
        """
        Génère un rapport détaillé sur les opérations Sonic
        
        Args:
            time_range_hours: Nombre d'heures pour l'analyse
            
        Returns:
            Rapport complet sur les opérations Sonic
        """
        # Calculer les métriques agrégées
        aggregated_metrics = self.metrics_collector.calculate_aggregated_metrics(time_range_hours)
        
        # Récupérer les visualisations
        visualizations = self.global_reporting.get_visualizations([
            "sonic_vs_other_chains",
            "sonic_profit_by_dex",
            "sonic_historical_performance",
            "sonic_opportunities_funnel"
        ], time_range_hours)
        
        # Générer le rapport
        report = {
            "title": f"Rapport Sonic - {time_range_hours}h",
            "generated_at": time.time(),
            "time_range_hours": time_range_hours,
            "metrics": aggregated_metrics.get("metrics", {}),
            "visualizations": visualizations,
            "summary": self._generate_report_summary(aggregated_metrics.get("metrics", {})),
            "recommendations": self._generate_recommendations(aggregated_metrics.get("metrics", {}))
        }
        
        return report
    
    def _check_transaction_alerts(self, transaction_data: Dict, metrics: Dict) -> None:
        """
        Vérifie les conditions d'alerte pour les transactions
        
        Args:
            transaction_data: Données de transaction
            metrics: Métriques collectées
        """
        # Vérifier les alertes spécifiques aux transactions
        if transaction_data.get("transaction_type") == "arbitrage":
            profit_pct = transaction_data.get("profit_pct", 0)
            
            if profit_pct > 3.0:
                self.global_reporting.trigger_alert(
                    "sonic_high_opportunity",
                    {
                        "opportunity": transaction_data,
                        "profit_pct": profit_pct,
                        "message": f"Opportunité d'arbitrage élevée détectée: {profit_pct:.2f}%"
                    }
                )
    
    def _check_market_alerts(self, market_data: Dict, metrics: Dict) -> None:
        """
        Vérifie les conditions d'alerte pour les données de marché
        
        Args:
            market_data: Données de marché
            metrics: Métriques collectées
        """
        # Vérifier les chutes de liquidité
        if "liquidity_delta_pct" in market_data:
            liquidity_delta_pct = market_data["liquidity_delta_pct"]
            
            if liquidity_delta_pct < -30:
                self.global_reporting.trigger_alert(
                    "sonic_liquidity_drop",
                    {
                        "liquidity_delta_pct": liquidity_delta_pct,
                        "dex": market_data.get("dex", "unknown"),
                        "message": f"Chute importante de liquidité détectée: {liquidity_delta_pct:.2f}%"
                    }
                )
    
    def _check_system_alerts(self, system_data: Dict, metrics: Dict) -> None:
        """
        Vérifie les conditions d'alerte pour les données système
        
        Args:
            system_data: Données système
            metrics: Métriques collectées
        """
        # Vérifier la congestion réseau
        if "network" in system_data:
            network_data = system_data["network"]
            congestion = network_data.get("congestion", 0)
            
            if congestion > 0.8:
                self.global_reporting.trigger_alert(
                    "sonic_network_congestion",
                    {
                        "network": network_data,
                        "congestion": congestion,
                        "message": f"Congestion réseau élevée détectée: {congestion:.2f}"
                    }
                )
            
            # Vérifier les pics de gas
            gas_price = network_data.get("gas_price", 0)
            avg_gas_price = network_data.get("avg_gas_price", gas_price / 2)  # Fallback
            
            if gas_price > 3 * avg_gas_price:
                self.global_reporting.trigger_alert(
                    "sonic_gas_price_spike",
                    {
                        "gas_price": gas_price,
                        "avg_gas_price": avg_gas_price,
                        "message": f"Pic du prix du gas détecté: {gas_price:.2f} (moyenne: {avg_gas_price:.2f})"
                    }
                )
    
    def _generate_report_summary(self, metrics: Dict) -> str:
        """
        Génère un résumé textuel des performances Sonic
        
        Args:
            metrics: Métriques agrégées
            
        Returns:
            Résumé textuel
        """
        # Générer un résumé en fonction des métriques
        transactions_count = metrics.get("sonic_transactions_count", 0)
        profit_loss = metrics.get("sonic_profit_loss", 0)
        success_rate = metrics.get("sonic_success_rate", 0)
        
        if transactions_count == 0:
            return "Aucune activité Sonic détectée pendant la période."
            
        profit_str = f"profit de ${profit_loss:.2f}" if profit_loss >= 0 else f"perte de ${abs(profit_loss):.2f}"
        
        summary = (
            f"Sur Sonic, {transactions_count} transactions ont été exécutées avec un taux "
            f"de réussite de {success_rate:.1f}%, générant un {profit_str}. "
        )
        
        # Ajouter des détails sur les DEX
        spirit_profit = metrics.get("sonic_spiritswap_profit_loss", 0)
        spooky_profit = metrics.get("sonic_spookyswap_profit_loss", 0)
        
        if spirit_profit != 0 or spooky_profit != 0:
            spirit_profit_str = f"profit de ${spirit_profit:.2f}" if spirit_profit >= 0 else f"perte de ${abs(spirit_profit):.2f}"
            spooky_profit_str = f"profit de ${spooky_profit:.2f}" if spooky_profit >= 0 else f"perte de ${abs(spooky_profit):.2f}"
            
            summary += (
                f"SpiritSwap a généré un {spirit_profit_str}, "
                f"tandis que SpookySwap a généré un {spooky_profit_str}."
            )
        
        # Ajouter des informations sur les opportunités
        opportunities_detected = metrics.get("sonic_opportunities_detected", 0)
        opportunities_success_rate = metrics.get("sonic_opportunity_success_rate", 0)
        
        if opportunities_detected > 0:
            summary += (
                f" {opportunities_detected} opportunités ont été détectées, "
                f"avec un taux de réussite d'exécution de {opportunities_success_rate:.1f}%."
            )
            
        return summary
    
    def _generate_recommendations(self, metrics: Dict) -> List[str]:
        """
        Génère des recommandations basées sur les métriques
        
        Args:
            metrics: Métriques agrégées
            
        Returns:
            Liste de recommandations
        """
        recommendations = []
        
        # Analyser les métriques pour générer des recommandations
        success_rate = metrics.get("sonic_success_rate", 0)
        opportunity_success_rate = metrics.get("sonic_opportunity_success_rate", 0)
        
        if success_rate < 80:
            recommendations.append(
                "Le taux de réussite des transactions est inférieur à 80%. "
                "Envisagez d'ajuster les paramètres de gas et de slippage pour améliorer ce taux."
            )
            
        if opportunity_success_rate < 70:
            recommendations.append(
                "Le taux de réussite des opportunités est inférieur à 70%. "
                "Analysez les raisons des échecs et ajustez les critères de sélection des opportunités."
            )
        
        # Analyser la répartition des profits
        spirit_profit = metrics.get("sonic_spiritswap_profit_loss", 0)
        spooky_profit = metrics.get("sonic_spookyswap_profit_loss", 0)
        
        if spirit_profit > 0 and spooky_profit < 0:
            recommendations.append(
                "SpiritSwap génère des profits tandis que SpookySwap génère des pertes. "
                "Envisagez d'augmenter l'allocation vers SpiritSwap ou d'ajuster les stratégies pour SpookySwap."
            )
        elif spirit_profit < 0 and spooky_profit > 0:
            recommendations.append(
                "SpookySwap génère des profits tandis que SpiritSwap génère des pertes. "
                "Envisagez d'augmenter l'allocation vers SpookySwap ou d'ajuster les stratégies pour SpiritSwap."
            )
        
        # Recommandations par défaut
        if not recommendations:
            recommendations.append(
                "Toutes les métriques semblent dans les plages normales. "
                "Continuez à surveiller les performances et ajustez les stratégies en fonction de l'évolution du marché."
            )
            
        return recommendations 