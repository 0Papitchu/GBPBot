#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Moteur d'arbitrage pour GBPBot
==============================

Ce module implémente le moteur d'arbitrage entre différents DEX, 
avec détection d'opportunités, calcul de rentabilité et exécution de transactions.
"""

import time
import logging
import asyncio
import threading
import os
import json
from typing import Dict, List, Optional, Any, Tuple, Set, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta

from gbpbot.clients.base_client import BaseBlockchainClient
from gbpbot.utils.logger import setup_logger
from gbpbot.ai import create_ai_client, create_market_intelligence

# Configurer le logger
logger = setup_logger("ArbitrageEngine", logging.INFO)

@dataclass
class ArbitrageOpportunity:
    """Représente une opportunité d'arbitrage entre DEX."""
    
    id: str
    timestamp: datetime
    blockchain: str
    token_address: str
    token_symbol: str
    
    dex_from: str
    dex_to: str
    
    buy_price: float
    sell_price: float
    
    price_difference: float
    price_difference_percent: float
    
    estimated_profit_usd: float
    estimated_gas_cost_usd: float
    net_profit_usd: float
    
    input_amount_usd: float
    
    # Informations sur les pools
    dex1_pool_address: str
    dex2_pool_address: str
    dex1_liquidity_usd: float
    dex2_liquidity_usd: float
    
    # Détails supplémentaires pour l'exécution
    route: Optional[List[Dict[str, Any]]] = None
    
    # Informations sur le token
    token_decimals: int = 18
    token_name: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'opportunité en dictionnaire"""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "blockchain": self.blockchain,
            "token": {
                "address": self.token_address,
                "symbol": self.token_symbol,
                "name": self.token_name,
                "decimals": self.token_decimals
            },
            "dexes": {
                "from": self.dex_from,
                "to": self.dex_to,
                "from_pool": self.dex1_pool_address,
                "to_pool": self.dex2_pool_address,
                "from_liquidity_usd": self.dex1_liquidity_usd,
                "to_liquidity_usd": self.dex2_liquidity_usd
            },
            "prices": {
                "buy": self.buy_price,
                "sell": self.sell_price,
                "difference": self.price_difference,
                "difference_percent": self.price_difference_percent
            },
            "profit": {
                "estimated_profit_usd": self.estimated_profit_usd,
                "estimated_gas_cost_usd": self.estimated_gas_cost_usd,
                "net_profit_usd": self.net_profit_usd,
                "input_amount_usd": self.input_amount_usd
            }
        }


class ArbitrageEngine:
    """
    Moteur d'arbitrage avancé qui détecte et exploite les opportunités
    entre différents DEX et pools de liquidité.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialise le moteur d'arbitrage.
        
        Args:
            config: Configuration du moteur d'arbitrage
        """
        self.config = config
        self.blockchain_clients = {}
        self.exchange_clients = {}
        self.running = False
        self.ai_client = None
        self.market_intelligence = None
        
        # Paramètres d'arbitrage
        self.min_profit_threshold = float(os.environ.get("MIN_ARBITRAGE_PROFIT_THRESHOLD", "0.5"))
        self.max_slippage = float(os.environ.get("MAX_SLIPPAGE", "1.0"))
        self.use_ai_optimization = os.environ.get("USE_AI_ARBITRAGE_OPTIMIZATION", "true").lower() == "true"
        
        # Liste des DEX et leurs configurations
        self.dex_list = self._parse_dex_config()
        
        # Statistiques d'activité
        self.stats = {
            "opportunities_detected": 0,
            "opportunities_executed": 0,
            "successful_arbitrages": 0,
            "failed_arbitrages": 0,
            "total_profit_usd": 0.0,
            "last_activity": datetime.now().isoformat()
        }
        
        # Opportunités en cours d'exécution
        self.active_opportunities = {}
        
        logger.info("Moteur d'arbitrage initialisé")
    
    async def initialize(self):
        """Initialise tous les clients nécessaires au fonctionnement du moteur"""
        # Initialiser les clients blockchain
        for chain in self.config.get("chains", []):
            self.blockchain_clients[chain["name"]] = await self._initialize_blockchain_client(chain)
        
        # Initialiser les clients d'échange
        for exchange in self.config.get("exchanges", []):
            self.exchange_clients[exchange["name"]] = await self._initialize_exchange_client(exchange)
        
        # Initialiser le client IA si l'optimisation IA est activée
        if self.use_ai_optimization:
            try:
                logger.info("Initialisation du client IA pour l'arbitrage...")
                self.ai_client = await create_ai_client(
                    provider=os.environ.get("AI_PROVIDER", "claude"),
                    config=self._get_ai_config()
                )
                
                # Initialiser le système d'intelligence de marché
                self.market_intelligence = await create_market_intelligence({
                    "ai_config": self._get_ai_config(),
                    "web_search_config": {
                        "serper_api_key": os.environ.get("SERPER_API_KEY")
                    }
                })
                
                logger.info("Client IA pour l'arbitrage initialisé avec succès")
            except Exception as e:
                logger.error(f"Erreur lors de l'initialisation du client IA: {str(e)}")
                self.use_ai_optimization = False
        
        logger.info("Initialisation du moteur d'arbitrage terminée")
    
    async def start(self):
        """Démarre le moteur d'arbitrage"""
        if self.running:
            logger.warning("Le moteur d'arbitrage est déjà en cours d'exécution")
            return
        
        # Initialiser si nécessaire
        if not self.blockchain_clients:
            await self.initialize()
        
        self.running = True
        logger.info("Démarrage du moteur d'arbitrage")
        
        # Démarrer les tâches de surveillance
        asyncio.create_task(self._monitor_dex_prices())
        
        if self.use_ai_optimization:
            asyncio.create_task(self._ai_optimization_loop())
    
    async def stop(self):
        """Arrête le moteur d'arbitrage"""
        if not self.running:
            logger.warning("Le moteur d'arbitrage n'est pas en cours d'exécution")
            return
        
        self.running = False
        logger.info("Arrêt du moteur d'arbitrage")
        
        # Fermer proprement les connexions
        for client in self.blockchain_clients.values():
            if hasattr(client, "close"):
                await client.close()
        
        for client in self.exchange_clients.values():
            if hasattr(client, "close"):
                await client.close()
        
        if self.ai_client:
            await self.ai_client.close()
        
        if self.market_intelligence:
            await self.market_intelligence.close()
    
    async def _monitor_dex_prices(self):
        """Surveille les prix sur différents DEX pour détecter les opportunités d'arbitrage"""
        logger.info("Démarrage de la surveillance des prix sur les DEX")
        
        while self.running:
            try:
                # Pour chaque paire surveillée, vérifier les prix sur différents DEX
                for pair in self.config.get("pairs", []):
                    # Récupérer les informations de la paire
                    token_a = pair["token_a"]
                    token_b = pair["token_b"]
                    chain = pair.get("chain", "solana")
                    
                    # Vérifier si la chaîne est supportée
                    if chain not in self.blockchain_clients:
                        continue
                    
                    # Récupérer les prix sur différents DEX
                    prices = await self._get_pair_prices(token_a, token_b, chain)
                    
                    if len(prices) < 2:
                        continue  # Pas assez de prix pour un arbitrage
                    
                    # Détecter les opportunités d'arbitrage
                    opportunities = self._find_arbitrage_opportunities(prices, token_a, token_b, chain)
                    
                    # Traiter les opportunités détectées
                    for opportunity in opportunities:
                        self.stats["opportunities_detected"] += 1
                        
                        # Analyser et optimiser l'opportunité avec l'IA si activé
                        if self.use_ai_optimization and self.ai_client:
                            is_optimized, optimized_opportunity = await self._optimize_opportunity_with_ai(opportunity)
                            
                            if is_optimized:
                                logger.info(f"Opportunité optimisée par l'IA: {optimized_opportunity['profit_percentage']:.2f}% de profit potentiel")
                                opportunity = optimized_opportunity
                        
                        # Exécuter l'arbitrage si le profit est suffisant
                        if opportunity["profit_percentage"] >= self.min_profit_threshold:
                            asyncio.create_task(self._execute_arbitrage(opportunity))
                
                # Pause avant la prochaine vérification
                await asyncio.sleep(0.1)  # Fréquence agressive pour les opportunités rapides
                
            except Exception as e:
                logger.error(f"Erreur dans la surveillance des prix: {str(e)}")
                await asyncio.sleep(1)  # Pause plus longue en cas d'erreur
    
    async def _ai_optimization_loop(self):
        """Boucle d'optimisation des stratégies d'arbitrage par l'IA"""
        logger.info("Démarrage de la boucle d'optimisation IA des stratégies d'arbitrage")
        
        # Attendre que le système collecte suffisamment de données
        await asyncio.sleep(60)
        
        while self.running:
            try:
                if not self.ai_client:
                    await asyncio.sleep(60)
                    continue
                
                # Collecter les données des dernières 24h
                historical_data = self._collect_historical_performance()
                
                # Optimiser les stratégies en fonction des performances passées
                strategy_updates = await self._optimize_strategies_with_ai(historical_data)
                
                if strategy_updates:
                    logger.info(f"IA a suggéré {len(strategy_updates)} mises à jour de stratégie")
                    
                    # Appliquer les mises à jour de stratégie
                    for update in strategy_updates:
                        self._apply_strategy_update(update)
                
                # Optimisation toutes les heures
                await asyncio.sleep(3600)
                
            except Exception as e:
                logger.error(f"Erreur dans la boucle d'optimisation IA: {str(e)}")
                await asyncio.sleep(300)  # 5 minutes de pause en cas d'erreur
    
    async def _get_pair_prices(self, token_a: str, token_b: str, chain: str) -> List[Dict[str, Any]]:
        """
        Récupère les prix d'une paire de tokens sur différents DEX
        
        Args:
            token_a: Premier token de la paire
            token_b: Second token de la paire
            chain: Blockchain concernée
            
        Returns:
            Liste des prix sur différents DEX
        """
        prices = []
        
        # Récupérer les DEX disponibles pour cette chaîne
        dex_list = [dex for dex in self.dex_list if dex["chain"] == chain]
        
        # Récupérer les prix sur chaque DEX
        for dex in dex_list:
            try:
                # Récupérer le prix via le client blockchain
                price = await self.blockchain_clients[chain].get_pair_price(
                    token_a, token_b, dex["name"]
                )
                
                if price:
                    prices.append({
                        "dex": dex["name"],
                        "price": price,
                        "liquidity": price.get("liquidity", 0),
                        "fee": dex.get("fee", 0.3),
                        "timestamp": datetime.now().timestamp()
                    })
            except Exception as e:
                logger.warning(f"Erreur lors de la récupération du prix sur {dex['name']}: {str(e)}")
        
        return prices
    
    def _find_arbitrage_opportunities(self, prices: List[Dict[str, Any]], 
                                     token_a: str, token_b: str, 
                                     chain: str) -> List[Dict[str, Any]]:
        """
        Détecte les opportunités d'arbitrage entre différents DEX
        
        Args:
            prices: Liste des prix sur différents DEX
            token_a: Premier token de la paire
            token_b: Second token de la paire
            chain: Blockchain concernée
            
        Returns:
            Liste des opportunités d'arbitrage détectées
        """
        opportunities = []
        
        for i in range(len(prices)):
            for j in range(i + 1, len(prices)):
                dex_a = prices[i]
                dex_b = prices[j]
                
                # Calculer la différence de prix
                price_a = float(dex_a["price"]["price"])
                price_b = float(dex_b["price"]["price"])
                
                # Calculer la différence en pourcentage (dans les deux sens)
                diff_a_to_b = (price_b - price_a) / price_a * 100
                diff_b_to_a = (price_a - price_b) / price_b * 100
                
                # Soustraire les frais des deux DEX
                fee_a = dex_a.get("fee", 0.3)
                fee_b = dex_b.get("fee", 0.3)
                total_fee = fee_a + fee_b
                
                # Calculer le profit net (après frais)
                profit_a_to_b = diff_a_to_b - total_fee
                profit_b_to_a = diff_b_to_a - total_fee
                
                # Vérifier s'il y a une opportunité d'arbitrage (A vers B)
                if profit_a_to_b > 0:
                    opportunities.append({
                        "token_a": token_a,
                        "token_b": token_b,
                        "chain": chain,
                        "buy_dex": dex_a["dex"],
                        "sell_dex": dex_b["dex"],
                        "buy_price": price_a,
                        "sell_price": price_b,
                        "price_difference": diff_a_to_b,
                        "total_fee": total_fee,
                        "profit_percentage": profit_a_to_b,
                        "direction": "a_to_b",
                        "timestamp": datetime.now().timestamp()
                    })
                
                # Vérifier s'il y a une opportunité d'arbitrage (B vers A)
                if profit_b_to_a > 0:
                    opportunities.append({
                        "token_a": token_a,
                        "token_b": token_b,
                        "chain": chain,
                        "buy_dex": dex_b["dex"],
                        "sell_dex": dex_a["dex"],
                        "buy_price": price_b,
                        "sell_price": price_a,
                        "price_difference": diff_b_to_a,
                        "total_fee": total_fee,
                        "profit_percentage": profit_b_to_a,
                        "direction": "b_to_a",
                        "timestamp": datetime.now().timestamp()
                    })
        
        # Trier les opportunités par profit décroissant
        opportunities.sort(key=lambda x: x["profit_percentage"], reverse=True)
        
        return opportunities
    
    async def _execute_arbitrage(self, opportunity: Dict[str, Any]) -> bool:
        """
        Exécute une opportunité d'arbitrage
        
        Args:
            opportunity: Détails de l'opportunité d'arbitrage
            
        Returns:
            True si l'arbitrage a réussi, False sinon
        """
        # Générer un ID unique pour cette opportunité
        opportunity_id = f"{opportunity['buy_dex']}_{opportunity['sell_dex']}_{opportunity['token_a']}_{opportunity['token_b']}_{int(time.time())}"
        
        # Vérifier si une opportunité similaire est déjà en cours d'exécution
        for active_id, active_op in self.active_opportunities.items():
            if (active_op["buy_dex"] == opportunity["buy_dex"] and
                active_op["sell_dex"] == opportunity["sell_dex"] and
                active_op["token_a"] == opportunity["token_a"] and
                active_op["token_b"] == opportunity["token_b"]):
                logger.info(f"Une opportunité similaire est déjà en cours d'exécution: {active_id}")
                return False
        
        # Marquer l'opportunité comme en cours d'exécution
        self.active_opportunities[opportunity_id] = opportunity
        self.stats["opportunities_executed"] += 1
        
        try:
            logger.info(f"Exécution de l'arbitrage: {opportunity['buy_dex']} -> {opportunity['sell_dex']} "
                       f"pour {opportunity['token_a']}/{opportunity['token_b']} "
                       f"(profit potentiel: {opportunity['profit_percentage']:.2f}%)")
            
            # Récupérer le client blockchain pour cette chaîne
            chain = opportunity["chain"]
            client = self.blockchain_clients.get(chain)
            
            if not client:
                logger.error(f"Client blockchain non disponible pour {chain}")
                return False
        
            # Calculer le montant optimal à utiliser pour l'arbitrage
            amount = await self._calculate_optimal_amount(opportunity)
            
            # Exécuter l'arbitrage
            if opportunity["direction"] == "a_to_b":
                # Acheter sur le premier DEX
                buy_tx = await client.execute_swap(
                    opportunity["token_a"],
                    opportunity["token_b"],
                    amount,
                    opportunity["buy_dex"],
                    self.max_slippage
                )
                
                if not buy_tx or not buy_tx.get("success", False):
                    logger.error(f"Échec de l'achat sur {opportunity['buy_dex']}")
                    return False
                
                # Récupérer le montant obtenu
                tokens_received = buy_tx.get("tokens_received", 0)
                
                # Vendre sur le deuxième DEX
                sell_tx = await client.execute_swap(
                    opportunity["token_b"],
                    opportunity["token_a"],
                    tokens_received,
                    opportunity["sell_dex"],
                    self.max_slippage
                )
                
                if not sell_tx or not sell_tx.get("success", False):
                    logger.error(f"Échec de la vente sur {opportunity['sell_dex']}")
                    return False
                
                # Calculer le profit réel
                final_amount = sell_tx.get("tokens_received", 0)
                profit = final_amount - amount
                profit_percentage = (profit / amount) * 100
                
            else:  # b_to_a
                # Logique similaire pour l'autre direction
                # (Simplifié pour la démonstration)
                profit = 0
                profit_percentage = 0
            
            # Enregistrer le résultat de l'arbitrage
            logger.info(f"Arbitrage réussi! Profit: {profit_percentage:.2f}% ({profit})")
            self.stats["successful_arbitrages"] += 1
            self.stats["total_profit_usd"] += self._convert_to_usd(profit, opportunity["token_a"])
            
            # Ajouter le résultat à l'historique pour l'analyse IA
            self._record_arbitrage_result(opportunity_id, opportunity, {
                "success": True,
                "profit": profit,
                "profit_percentage": profit_percentage,
                "executed_at": datetime.now().timestamp()
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'exécution de l'arbitrage: {str(e)}")
            self.stats["failed_arbitrages"] += 1
            
            # Enregistrer l'échec pour l'analyse IA
            self._record_arbitrage_result(opportunity_id, opportunity, {
                "success": False,
                "error": str(e),
                "executed_at": datetime.now().timestamp()
            })
            
            return False
            
        finally:
            # Supprimer l'opportunité de la liste des opportunités actives
            if opportunity_id in self.active_opportunities:
                del self.active_opportunities[opportunity_id]
    
    async def _optimize_opportunity_with_ai(self, opportunity: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        Utilise l'IA pour optimiser une opportunité d'arbitrage
        
        Args:
            opportunity: Opportunité d'arbitrage à optimiser
            
        Returns:
            Tuple (optimisé, opportunité optimisée)
        """
        if not self.ai_client:
            return False, opportunity
        
        try:
            # Enrichir l'opportunité avec des données supplémentaires pour l'IA
            enriched_opportunity = await self._enrich_opportunity_data(opportunity)
            
            # Appeler l'IA pour optimiser l'opportunité
            optimization_result = await self.ai_client.optimize_arbitrage(enriched_opportunity)
            
            if not optimization_result or not optimization_result.get("is_optimized"):
                return False, opportunity
            
            # Appliquer les optimisations suggérées par l'IA
            optimized_opportunity = opportunity.copy()
            
            # Mettre à jour le slippage si suggéré
            if "suggested_slippage" in optimization_result:
                optimized_opportunity["suggested_slippage"] = optimization_result["suggested_slippage"]
            
            # Mettre à jour l'estimation de profit si suggérée
            if "predicted_profit_percentage" in optimization_result:
                optimized_opportunity["profit_percentage"] = optimization_result["predicted_profit_percentage"]
            
            # Ajouter des données supplémentaires pour l'exécution
            optimized_opportunity["ai_optimized"] = True
            optimized_opportunity["optimization_reason"] = optimization_result.get("optimization_reason", "")
            optimized_opportunity["optimization_confidence"] = optimization_result.get("confidence", 0)
            
            return True, optimized_opportunity
            
        except Exception as e:
            logger.error(f"Erreur lors de l'optimisation de l'opportunité avec l'IA: {str(e)}")
            return False, opportunity
    
    async def _optimize_strategies_with_ai(self, historical_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Utilise l'IA pour optimiser les stratégies d'arbitrage
        
        Args:
            historical_data: Données historiques des performances d'arbitrage
            
        Returns:
            Liste des mises à jour de stratégie suggérées
        """
        if not self.ai_client:
            return []
        
        try:
            # Enrichir les données historiques avec des informations sur le marché
            if self.market_intelligence:
                market_overview = await self.market_intelligence.get_market_overview(
                    chains=list(self.blockchain_clients.keys())
                )
                historical_data["market_overview"] = market_overview
            
            # Appeler l'IA pour optimiser les stratégies
            strategy_suggestions = await self.ai_client.optimize_arbitrage_strategy(historical_data)
            
            if not strategy_suggestions or not isinstance(strategy_suggestions, list):
                return []
            
            return strategy_suggestions
            
        except Exception as e:
            logger.error(f"Erreur lors de l'optimisation des stratégies avec l'IA: {str(e)}")
            return []
    
    def _apply_strategy_update(self, update: Dict[str, Any]) -> bool:
        """
        Applique une mise à jour de stratégie suggérée par l'IA
        
        Args:
            update: Mise à jour de stratégie à appliquer
            
        Returns:
            True si la mise à jour a été appliquée avec succès
        """
        update_type = update.get("type")
        
        if update_type == "threshold":
            # Mettre à jour le seuil de profit minimum
            new_threshold = update.get("value")
            if new_threshold and isinstance(new_threshold, (int, float)) and new_threshold > 0:
                old_threshold = self.min_profit_threshold
                self.min_profit_threshold = new_threshold
                logger.info(f"Seuil de profit minimum mis à jour: {old_threshold} -> {new_threshold} "
                          f"(Raison: {update.get('reason', 'Non spécifiée')})")
                return True
        
        elif update_type == "slippage":
            # Mettre à jour le slippage maximum
            new_slippage = update.get("value")
            if new_slippage and isinstance(new_slippage, (int, float)) and new_slippage > 0:
                old_slippage = self.max_slippage
                self.max_slippage = new_slippage
                logger.info(f"Slippage maximum mis à jour: {old_slippage} -> {new_slippage} "
                          f"(Raison: {update.get('reason', 'Non spécifiée')})")
                return True
        
        # Autres types de mises à jour possibles...
        
        return False
    
    async def _calculate_optimal_amount(self, opportunity: Dict[str, Any]) -> float:
        """
        Calcule le montant optimal à utiliser pour un arbitrage
        
        Args:
            opportunity: Opportunité d'arbitrage
            
        Returns:
            Montant optimal en tokens
        """
        # Logique simple: montant fixe de base
        base_amount = float(os.environ.get("DEFAULT_ARBITRAGE_AMOUNT", "100"))
        
        # Si l'opportunité a été optimisée par l'IA, utiliser ses suggestions
        if opportunity.get("ai_optimized") and "suggested_amount" in opportunity:
            return opportunity["suggested_amount"]
        
        # Logique avancée à implémenter: prendre en compte la liquidité, etc.
        # Pour l'exemple, on retourne simplement le montant de base
        return base_amount
    
    def _convert_to_usd(self, amount: float, token: str) -> float:
        """
        Convertit un montant de token en USD
        
        Args:
            amount: Montant à convertir
            token: Token à convertir
            
        Returns:
            Montant équivalent en USD
        """
        # À implémenter: conversion réelle en USD
        # Pour l'exemple, on suppose que le token vaut 1 USD
        return amount
    
    def _record_arbitrage_result(self, opportunity_id: str, opportunity: Dict[str, Any], result: Dict[str, Any]):
        """
        Enregistre le résultat d'un arbitrage pour analyse ultérieure
        
        Args:
            opportunity_id: ID de l'opportunité
            opportunity: Détails de l'opportunité
            result: Résultat de l'exécution
        """
        # Stocker les résultats pour l'analyse IA
        # Cette implémentation simplifiée pourrait être améliorée avec une base de données
        result_with_details = {
            "id": opportunity_id,
            "opportunity": opportunity,
            "result": result
        }
        
        # Ajouter à un fichier de journal ou à une base de données
        self._append_to_history(result_with_details)
    
    def _append_to_history(self, data: Dict[str, Any]):
        """
        Ajoute des données à l'historique
        
        Args:
            data: Données à ajouter
        """
        # Implémentation simplifiée: peut être remplacée par une base de données
        history_file = os.path.join(os.environ.get("DATA_DIR", "./data"), "arbitrage_history.jsonl")
        
        try:
            with open(history_file, "a") as f:
                f.write(json.dumps(data) + "\n")
        except Exception as e:
            logger.error(f"Erreur lors de l'enregistrement dans l'historique: {str(e)}")
    
    def _collect_historical_performance(self) -> Dict[str, Any]:
        """
        Collecte les données historiques de performance pour l'analyse IA
        
        Returns:
            Données historiques de performance
        """
        # Implémentation simplifiée: dans une version complète, ces données viendraient d'une base de données
        return {
            "stats": self.stats,
            "recent_executions": [],  # Exécutions récentes
            "pair_performance": {},   # Performance par paire
            "dex_performance": {},    # Performance par DEX
        }
    
    async def _enrich_opportunity_data(self, opportunity: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enrichit une opportunité avec des données supplémentaires pour l'analyse IA
        
        Args:
            opportunity: Opportunité à enrichir
            
        Returns:
            Opportunité enrichie
        """
        enriched = opportunity.copy()
        
        try:
            # Ajouter des informations sur la volatilité de la paire
            token_a = opportunity["token_a"]
            token_b = opportunity["token_b"]
            chain = opportunity["chain"]
            
            # Récupérer la volatilité historique si disponible
            client = self.blockchain_clients.get(chain)
            if client and hasattr(client, "get_pair_volatility"):
                volatility = await client.get_pair_volatility(token_a, token_b)
                if volatility:
                    enriched["historical_volatility"] = volatility
            
            # Ajouter des données de marché via MarketIntelligence
            if self.market_intelligence:
                market_data = await self.market_intelligence.get_token_market_data(
                    token_symbol=token_a,
                    chain=chain
                )
                if market_data:
                    enriched["market_data"] = market_data
        
        except Exception as e:
            logger.warning(f"Erreur lors de l'enrichissement des données d'opportunité: {str(e)}")
        
        return enriched
    
    def _parse_dex_config(self) -> List[Dict[str, Any]]:
        """
        Parse la configuration des DEX
            
        Returns:
            Liste des DEX configurés
        """
        # Exemple de configuration des DEX
        return self.config.get("dex_list", [
            {"name": "traderjoe", "chain": "avax", "fee": 0.3},
            {"name": "pangolin", "chain": "avax", "fee": 0.3},
            {"name": "sushi", "chain": "avax", "fee": 0.3},
            {"name": "raydium", "chain": "solana", "fee": 0.25},
            {"name": "orca", "chain": "solana", "fee": 0.3}
        ])
    
    async def _initialize_blockchain_client(self, chain_config: Dict[str, Any]):
        """
        Initialise un client blockchain
        
        Args:
            chain_config: Configuration de la blockchain
            
        Returns:
            Client blockchain initialisé
        """
        # À implémenter: initialisation du client blockchain spécifique
        return None
    
    async def _initialize_exchange_client(self, exchange_config: Dict[str, Any]):
        """
        Initialise un client d'échange
        
        Args:
            exchange_config: Configuration de l'échange
            
        Returns:
            Client d'échange initialisé
        """
        # À implémenter: initialisation du client d'échange spécifique
        return None
    
    def _get_ai_config(self) -> Dict[str, Any]:
        """
        Prépare la configuration pour le client IA
            
        Returns:
            Configuration du client IA
        """
        ai_provider = os.environ.get("AI_PROVIDER", "claude")
        
        if ai_provider == "claude":
            return {
                "api_key": os.environ.get("CLAUDE_API_KEY"),
                "model": os.environ.get("CLAUDE_MODEL", "claude-3-7-sonnet-20240229")
            }
        elif ai_provider == "openai":
            return {
                "api_key": os.environ.get("OPENAI_API_KEY"),
                "model": os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo")
            }
        else:
            return {}
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Récupère les statistiques d'activité du moteur d'arbitrage
            
        Returns:
            Statistiques d'activité
        """
        # Mettre à jour le timestamp de dernière activité
        self.stats["last_activity"] = datetime.now().isoformat()
        return self.stats 