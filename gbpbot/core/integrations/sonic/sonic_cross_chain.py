#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Module d'arbitrage cross-chain pour Sonic
Permet l'exploitation d'opportunités d'arbitrage entre Sonic et d'autres blockchains
Intégré à l'architecture GBPBot pour maximiser les sources de profit
"""

import asyncio
import logging
from typing import Dict, List, Optional, Tuple, Union
from decimal import Decimal
import time

from gbpbot.core.blockchain.base_client import BlockchainClient
from gbpbot.core.transaction.transaction_executor import TransactionExecutor
from gbpbot.core.analysis.opportunity_analyzer import OpportunityAnalyzer
from gbpbot.core.optimization.route_optimizer import RouteOptimizer
from gbpbot.machine_learning.models.price_predictor import PricePredictor
from gbpbot.core.security.transaction_validator import TransactionValidator

logger = logging.getLogger(__name__)

class ArbitrageOpportunity:
    """Représente une opportunité d'arbitrage cross-chain identifiée"""
    
    def __init__(
        self, 
        source_chain: str,
        target_chain: str, 
        token_symbol: str,
        price_diff_pct: Decimal,
        estimated_profit_usd: Decimal,
        route: List[Dict],
        risk_score: float
    ):
        self.source_chain = source_chain
        self.target_chain = target_chain
        self.token_symbol = token_symbol
        self.price_diff_pct = price_diff_pct
        self.estimated_profit_usd = estimated_profit_usd
        self.route = route
        self.risk_score = risk_score
        self.timestamp = time.time()
        
    def __str__(self) -> str:
        return (f"ArbitrageOpportunity({self.token_symbol}): "
                f"{self.source_chain}->{self.target_chain}, "
                f"Diff: {self.price_diff_pct:.2f}%, "
                f"Profit: ${self.estimated_profit_usd:.2f}, "
                f"Risk: {self.risk_score:.2f}")
    
    def is_profitable(self, min_profit_usd: Decimal = Decimal("5.0")) -> bool:
        """Détermine si l'opportunité est suffisamment profitable"""
        return self.estimated_profit_usd >= min_profit_usd
    
    def is_expired(self, max_age_seconds: int = 30) -> bool:
        """Vérifie si l'opportunité n'est plus valide en raison de son âge"""
        return (time.time() - self.timestamp) > max_age_seconds


class SonicCrossChainArbitrage:
    """
    Système d'arbitrage cross-chain spécialisé pour l'écosystème Sonic
    Permet d'exploiter les différences de prix entre Sonic et d'autres blockchain
    """
    
    def __init__(
        self,
        config: Dict,
        sonic_client: BlockchainClient,
        solana_client: Optional[BlockchainClient] = None,
        avax_client: Optional[BlockchainClient] = None
    ):
        self.config = config
        self.sonic_client = sonic_client
        self.solana_client = solana_client
        self.avax_client = avax_client
        
        # Initialisation des composants auxiliaires
        self.opportunity_analyzer = OpportunityAnalyzer()
        self.route_optimizer = RouteOptimizer()
        self.transaction_executor = TransactionExecutor()
        self.price_predictor = PricePredictor()
        self.validator = TransactionValidator()
        
        # Métriques
        self.total_opportunities_found = 0
        self.successful_arbitrages = 0
        self.total_profit_usd = Decimal("0.0")
        
        logger.info("SonicCrossChainArbitrage initialisé avec les clients: %s", 
                   ", ".join(filter(None, ["Sonic", 
                                          "Solana" if solana_client else None,
                                          "AVAX" if avax_client else None])))
    
    async def start_monitoring(self, interval_seconds: int = 10) -> None:
        """Démarre la surveillance continue des opportunités d'arbitrage"""
        logger.info("Démarrage de la surveillance des opportunités cross-chain avec Sonic")
        
        try:
            while True:
                try:
                    # Recherche d'opportunités
                    opportunities = await self.scan_cross_chain_opportunities()
                    
                    if opportunities:
                        logger.info("Détection de %d opportunités d'arbitrage cross-chain", len(opportunities))
                        
                        # Filtrer et trier les opportunités par profit estimé
                        valid_opportunities = [
                            op for op in opportunities 
                            if op.is_profitable(self.config.get("min_profit_usd", Decimal("5.0")))
                        ]
                        valid_opportunities.sort(key=lambda op: op.estimated_profit_usd, reverse=True)
                        
                        # Exécuter les meilleures opportunités
                        for opportunity in valid_opportunities[:self.config.get("max_concurrent_trades", 3)]:
                            asyncio.create_task(self.execute_arbitrage(opportunity))
                    
                    await asyncio.sleep(interval_seconds)
                    
                except Exception as e:
                    logger.error("Erreur lors de la surveillance des opportunités: %s", str(e), exc_info=True)
                    await asyncio.sleep(interval_seconds * 2)  # Attente plus longue en cas d'erreur
                    
        except asyncio.CancelledError:
            logger.info("Surveillance des opportunités cross-chain avec Sonic arrêtée")
    
    async def scan_cross_chain_opportunities(self) -> List[ArbitrageOpportunity]:
        """Analyse en parallèle les opportunités d'arbitrage entre Sonic et autres chaînes"""
        # Collecte des prix sur Sonic DEXs
        try:
            sonic_prices = await self._gather_sonic_prices()
            
            # Collecte parallèle des prix sur autres chaînes
            other_prices = {}
            
            if self.solana_client:
                solana_prices = await self.solana_client.get_prices_for_common_tokens()
                other_prices["Solana"] = solana_prices
                
            if self.avax_client:
                avax_prices = await self.avax_client.get_prices_for_common_tokens()
                other_prices["AVAX"] = avax_prices
            
            # Identification des différentiels de prix significatifs
            opportunities = self.opportunity_analyzer.find_cross_chain_opportunities(
                sonic_prices, 
                other_prices, 
                threshold=self.config.get("min_price_difference", Decimal("1.5"))
            )
            
            # Pour chaque opportunité, calculer une route optimisée
            for i, opportunity in enumerate(opportunities):
                # Estimation des coûts de gas pour chaque blockchain
                gas_costs = {
                    "Sonic": await self.sonic_client.estimate_gas(),
                }
                
                if self.solana_client and opportunity.target_chain == "Solana":
                    gas_costs["Solana"] = await self.solana_client.estimate_gas()
                
                if self.avax_client and opportunity.target_chain == "AVAX":
                    gas_costs["AVAX"] = await self.avax_client.estimate_gas()
                
                # Optimisation de la route
                optimized_route = self.route_optimizer.optimize(
                    opportunity,
                    gas_costs=gas_costs,
                    slippage_models=self._get_slippage_models()
                )
                
                # Mise à jour de l'opportunité avec la route optimisée
                opportunities[i].route = optimized_route
            
            # Mettre à jour les métriques
            self.total_opportunities_found += len(opportunities)
            
            return opportunities
            
        except Exception as e:
            logger.error("Erreur lors de la recherche d'opportunités cross-chain: %s", str(e), exc_info=True)
            return []
    
    async def execute_arbitrage(self, opportunity: ArbitrageOpportunity) -> Optional[Decimal]:
        """Exécute une opportunité d'arbitrage cross-chain de manière atomique si possible"""
        logger.info("Exécution de l'arbitrage: %s", opportunity)
        
        try:
            # Vérifier que l'opportunité est toujours valide
            if opportunity.is_expired(self.config.get("max_opportunity_age_seconds", 30)):
                logger.warning("Opportunité expirée, abandon de l'exécution")
                return None
                
            # Validation en temps réel de l'opportunité
            is_valid = await self._validate_opportunity_still_valid(opportunity)
            if not is_valid:
                logger.warning("Opportunité non valide en temps réel, abandon de l'exécution")
                return None
            
            # Prédiction de la tendance de prix à court terme
            price_trend = await self.price_predictor.predict_short_term_trend(
                token=opportunity.token_symbol,
                source_chain=opportunity.source_chain,
                target_chain=opportunity.target_chain
            )
            
            # Ajustement de la stratégie en fonction de la tendance prédite
            if price_trend.is_favorable_for_arbitrage():
                logger.info("Tendance de prix favorable détectée, optimisation de l'exécution")
                # Utiliser des paramètres plus agressifs
                max_slippage = self.config.get("aggressive_max_slippage", Decimal("1.5"))
                timeout = self.config.get("aggressive_timeout", 30)
            else:
                # Utiliser des paramètres plus conservateurs
                max_slippage = self.config.get("conservative_max_slippage", Decimal("0.5"))
                timeout = self.config.get("conservative_timeout", 60)
            
            # Exécution des transactions dans l'ordre optimal
            result = await self.transaction_executor.execute_cross_chain(
                route=opportunity.route,
                safety_checks=True,
                max_slippage=max_slippage,
                timeout=timeout,
                priority_level=self.config.get("gas_priority", "high")
            )
            
            # Analyse des résultats
            if result.success:
                profit = self._calculate_actual_profit(result)
                self.successful_arbitrages += 1
                self.total_profit_usd += profit
                
                logger.info("Arbitrage réussi! Profit: $%.2f, Total cumulé: $%.2f", 
                           float(profit), float(self.total_profit_usd))
                
                # Enregistrer les résultats pour apprentissage
                self._log_arbitrage_result(opportunity, result, profit)
                
                return profit
            else:
                logger.warning("Échec de l'arbitrage: %s", result.error_message)
                return None
                
        except Exception as e:
            logger.error("Erreur lors de l'exécution de l'arbitrage: %s", str(e), exc_info=True)
            return None
    
    async def _gather_sonic_prices(self) -> Dict[str, Dict[str, Decimal]]:
        """Recueille les prix actuels sur les DEX Sonic"""
        prices = {}
        
        # Récupérer les prix de SpiritSwap
        try:
            spirit_prices = await self.sonic_client.get_dex_prices("SpiritSwap")
            prices["SpiritSwap"] = spirit_prices
        except Exception as e:
            logger.error("Erreur lors de la récupération des prix SpiritSwap: %s", str(e))
        
        # Récupérer les prix de SpookySwap
        try:
            spooky_prices = await self.sonic_client.get_dex_prices("SpookySwap")
            prices["SpookySwap"] = spooky_prices
        except Exception as e:
            logger.error("Erreur lors de la récupération des prix SpookySwap: %s", str(e))
        
        return prices
    
    def _get_slippage_models(self) -> Dict[str, object]:
        """Récupère les modèles de slippage pour chaque DEX"""
        return {
            "SpiritSwap": self.sonic_client.get_slippage_model("SpiritSwap"),
            "SpookySwap": self.sonic_client.get_slippage_model("SpookySwap"),
            "Solana": self.solana_client.get_slippage_model() if self.solana_client else None,
            "AVAX": self.avax_client.get_slippage_model() if self.avax_client else None
        }
    
    async def _validate_opportunity_still_valid(self, opportunity: ArbitrageOpportunity) -> bool:
        """Vérifie en temps réel que l'opportunité d'arbitrage est toujours valide"""
        # Obtenir les prix actuels
        current_prices = {}
        
        # Prix sur Sonic
        sonic_prices = await self._gather_sonic_prices()
        source_dex = opportunity.route[0].get("dex")
        if source_dex in sonic_prices:
            current_prices["Sonic"] = sonic_prices[source_dex].get(opportunity.token_symbol)
        
        # Prix sur chaîne cible
        if opportunity.target_chain == "Solana" and self.solana_client:
            solana_price = await self.solana_client.get_token_price(opportunity.token_symbol)
            current_prices["Solana"] = solana_price
        elif opportunity.target_chain == "AVAX" and self.avax_client:
            avax_price = await self.avax_client.get_token_price(opportunity.token_symbol)
            current_prices["AVAX"] = avax_price
        
        # Recalculer le différentiel de prix
        if "Sonic" in current_prices and opportunity.target_chain in current_prices:
            sonic_price = current_prices["Sonic"]
            target_price = current_prices[opportunity.target_chain]
            
            # Calculer la différence actuelle
            current_diff_pct = abs((target_price - sonic_price) / sonic_price * 100)
            
            # Vérifier si l'opportunité est toujours profitable
            min_diff = self.config.get("min_price_difference", Decimal("1.5"))
            return current_diff_pct >= min_diff
        
        return False
    
    def _calculate_actual_profit(self, result) -> Decimal:
        """Calcule le profit réel obtenu après exécution de l'arbitrage"""
        # Extraire les montants avant et après
        initial_amount = result.initial_amount
        final_amount = result.final_amount
        
        # Calculer le profit (en tenant compte des frais)
        gross_profit = final_amount - initial_amount
        fees = sum(tx.fee for tx in result.transactions)
        
        # Profit net
        net_profit = gross_profit - fees
        
        return net_profit
    
    def _log_arbitrage_result(self, opportunity, result, profit):
        """Enregistre les résultats de l'arbitrage pour apprentissage et analyse"""
        # Créer un enregistrement pour l'analyse future
        log_entry = {
            "timestamp": time.time(),
            "opportunity": {
                "source_chain": opportunity.source_chain,
                "target_chain": opportunity.target_chain,
                "token_symbol": opportunity.token_symbol,
                "price_diff_pct": float(opportunity.price_diff_pct),
                "estimated_profit": float(opportunity.estimated_profit_usd),
                "risk_score": opportunity.risk_score
            },
            "execution": {
                "success": result.success,
                "execution_time_ms": result.execution_time_ms,
                "transactions": len(result.transactions),
                "slippage_experienced": float(result.slippage_experienced) if hasattr(result, "slippage_experienced") else None
            },
            "outcome": {
                "actual_profit": float(profit),
                "profit_difference": float(profit - opportunity.estimated_profit_usd),
                "profitability_ratio": float(profit / opportunity.estimated_profit_usd) if opportunity.estimated_profit_usd > 0 else 0
            }
        }
        
        # Enregistrer dans la base de données pour apprentissage
        logger.debug("Résultat d'arbitrage enregistré: %s", log_entry)
        # TODO: Implémenter la persistance des données 