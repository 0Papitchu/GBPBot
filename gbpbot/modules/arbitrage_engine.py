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
from typing import Dict, List, Optional, Any, Tuple, Set, Callable
from dataclasses import dataclass
from datetime import datetime

from gbpbot.clients.base_client import BaseBlockchainClient

logger = logging.getLogger("gbpbot.modules.arbitrage")

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
    Moteur d'arbitrage entre différents DEX.
    
    Cette classe est responsable de :
    1. Détecter les opportunités d'arbitrage entre DEX
    2. Calculer la rentabilité de chaque opportunité
    3. Exécuter les transactions d'arbitrage optimales
    4. Maintenir un historique des opportunités et des transactions
    """
    
    def __init__(
        self,
        blockchain_clients: Dict[str, BaseBlockchainClient],
        config: Dict[str, Any]
    ):
        """
        Initialise le moteur d'arbitrage.
        
        Args:
            blockchain_clients: Dictionnaire de clients blockchain par nom
            config: Configuration du moteur d'arbitrage
        """
        self.clients = blockchain_clients
        self.config = config
        
        # Paramètres de configuration
        self.min_profit_percentage = config.get("min_profit_percentage", 0.5)
        self.max_slippage = config.get("max_slippage", 1.0)
        self.gas_multiplier = config.get("gas_multiplier", 1.05)
        self.scan_interval = config.get("scan_interval", 5)  # en secondes
        
        # Paires à surveiller (si vide, toutes les paires supportées sont surveillées)
        self.pairs = config.get("pairs", [])
        
        # DEX à surveiller (si vide, tous les DEX supportés sont utilisés)
        self.exchanges = config.get("exchanges", [])
        
        # Limite de montant par transaction
        self.max_trade_amount_usd = config.get("max_trade_amount_usd", 500)
        
        # Paramètres avancés
        self.use_flash_arbitrage = config.get("use_flash_arbitrage", True)
        self.max_concurrent_arbitrages = config.get("max_concurrent_arbitrages", 3)
        self.max_pending_txs = config.get("max_pending_txs", 5)
        
        # État interne
        self.running = False
        self.stop_event = threading.Event()
        self.runner_thread = None
        
        # Statistiques
        self.opportunities_found = 0
        self.successful_arbitrages = 0
        self.failed_arbitrages = 0
        self.total_profit_usd = 0.0
        self.start_time = None
        
        # Cache des opportunités
        self._opportunities_cache: List[ArbitrageOpportunity] = []
        self._max_cache_size = config.get("max_cache_size", 1000)
        
        # Callback pour les nouvelles opportunités
        self._opportunity_callbacks: List[Callable[[ArbitrageOpportunity], None]] = []
        
        logger.info(f"Moteur d'arbitrage initialisé avec {len(blockchain_clients)} clients blockchain")
    
    def start(self, stop_event: Optional[threading.Event] = None) -> None:
        """
        Démarre le moteur d'arbitrage dans un thread séparé.
        
        Args:
            stop_event: Événement pour arrêter le moteur
        """
        if self.running:
            logger.warning("Le moteur d'arbitrage est déjà en cours d'exécution")
            return
        
        self.stop_event = stop_event or threading.Event()
        self.running = True
        self.start_time = datetime.now()
        
        # Démarrer le thread de surveillance
        self.runner_thread = threading.Thread(
            target=self._run_arbitrage_loop,
            name="ArbitrageEngineThread",
            daemon=True
        )
        self.runner_thread.start()
        
        logger.info("Moteur d'arbitrage démarré")
    
    def stop(self) -> None:
        """Arrête le moteur d'arbitrage."""
        if not self.running:
            return
        
        self.running = False
        self.stop_event.set()
        
        if self.runner_thread and self.runner_thread.is_alive():
            self.runner_thread.join(timeout=5)
        
        logger.info("Moteur d'arbitrage arrêté")
    
    def register_opportunity_callback(self, callback: Callable[[ArbitrageOpportunity], None]) -> None:
        """
        Enregistre un callback à appeler pour chaque nouvelle opportunité détectée.
        
        Args:
            callback: Fonction à appeler avec l'opportunité d'arbitrage
        """
        self._opportunity_callbacks.append(callback)
    
    def get_opportunities(self, min_profit_usd: float = 0) -> List[ArbitrageOpportunity]:
        """
        Récupère les opportunités d'arbitrage récentes.
        
        Args:
            min_profit_usd: Profit minimum en USD pour filtrer les opportunités
            
        Returns:
            Liste d'opportunités d'arbitrage
        """
        if min_profit_usd > 0:
            return [o for o in self._opportunities_cache if o.net_profit_usd >= min_profit_usd]
        return list(self._opportunities_cache)
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Récupère les statistiques du moteur d'arbitrage.
        
        Returns:
            Dict: Statistiques
        """
        runtime = None
        if self.start_time:
            runtime = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "running": self.running,
            "runtime_seconds": runtime,
            "opportunities_found": self.opportunities_found,
            "successful_arbitrages": self.successful_arbitrages,
            "failed_arbitrages": self.failed_arbitrages,
            "total_profit_usd": self.total_profit_usd,
            "config": {
                "min_profit_percentage": self.min_profit_percentage,
                "max_slippage": self.max_slippage,
                "scan_interval": self.scan_interval,
                "use_flash_arbitrage": self.use_flash_arbitrage
            }
        }
    
    def execute_opportunity(self, opportunity_id: str) -> Dict[str, Any]:
        """
        Exécute manuellement une opportunité d'arbitrage spécifique.
        
        Args:
            opportunity_id: ID de l'opportunité à exécuter
            
        Returns:
            Dict: Résultat de l'exécution
            
        Raises:
            ValueError: Si l'opportunité n'est pas trouvée
        """
        # Trouver l'opportunité dans le cache
        opportunity = next((o for o in self._opportunities_cache if o.id == opportunity_id), None)
        if not opportunity:
            raise ValueError(f"Opportunité d'arbitrage avec ID {opportunity_id} non trouvée")
        
        logger.info(f"Exécution manuelle de l'opportunité d'arbitrage {opportunity_id}")
        
        # Exécuter l'arbitrage
        return asyncio.run(self._execute_arbitrage(opportunity))
    
    def _run_arbitrage_loop(self) -> None:
        """Boucle principale d'exécution du moteur d'arbitrage."""
        logger.debug("Démarrage de la boucle d'arbitrage")
        
        while not self.stop_event.is_set() and self.running:
            try:
                # Exécuter la recherche d'opportunités
                asyncio.run(self._scan_arbitrage_opportunities())
                
                # Attendre l'intervalle configuré
                self.stop_event.wait(self.scan_interval)
            except Exception as e:
                logger.error(f"Erreur dans la boucle d'arbitrage: {e}", exc_info=True)
                time.sleep(5)  # Attendre un peu avant de réessayer
    
    async def _scan_arbitrage_opportunities(self) -> None:
        """Scanne les opportunités d'arbitrage sur les différentes blockchains."""
        all_opportunities = []
        
        # Vérifier chaque blockchain supportée
        for blockchain, client in self.clients.items():
            try:
                # Obtenir les DEX pour cette blockchain
                dexes = await client.get_dexes()
                
                if self.exchanges:
                    # Filtrer les DEX selon la configuration
                    dexes = [dex for dex in dexes if dex["name"].lower() in 
                            [ex.lower() for ex in self.exchanges]]
                
                if len(dexes) < 2:
                    logger.debug(f"Pas assez de DEX disponibles sur {blockchain} pour l'arbitrage")
                    continue
                
                # Obtenir les opportunités d'arbitrage pour cette blockchain
                blockchain_opportunities = await self._find_opportunities_for_blockchain(
                    blockchain, client, dexes
                )
                
                all_opportunities.extend(blockchain_opportunities)
            except Exception as e:
                logger.error(f"Erreur lors de la recherche d'opportunités sur {blockchain}: {e}", 
                            exc_info=True)
        
        # Mettre à jour les compteurs
        if all_opportunities:
            self.opportunities_found += len(all_opportunities)
            logger.info(f"Trouvé {len(all_opportunities)} opportunités d'arbitrage")
            
            # Mettre à jour le cache
            self._update_opportunities_cache(all_opportunities)
            
            # Notifier les callbacks
            for opportunity in all_opportunities:
                for callback in self._opportunity_callbacks:
                    try:
                        callback(opportunity)
                    except Exception as e:
                        logger.error(f"Erreur dans le callback d'opportunité: {e}", exc_info=True)
            
            # Exécuter automatiquement les meilleures opportunités si configuré
            if self.config.get("auto_execute", False):
                await self._auto_execute_best_opportunities(all_opportunities)
    
    async def _find_opportunities_for_blockchain(
        self, 
        blockchain: str, 
        client: BaseBlockchainClient, 
        dexes: List[Dict[str, Any]]
    ) -> List[ArbitrageOpportunity]:
        """
        Recherche des opportunités d'arbitrage sur une blockchain spécifique.
        
        Args:
            blockchain: Nom de la blockchain
            client: Client blockchain
            dexes: Liste des DEX disponibles
            
        Returns:
            Liste d'opportunités d'arbitrage
        """
        opportunities = []
        
        # Liste des paires à vérifier
        pairs_to_check = self.pairs
        
        # Si aucune paire n'est spécifiée, utiliser les paires populaires
        if not pairs_to_check:
            # Obtenir les paires populaires depuis le client
            # Cette méthode devrait être implémentée dans chaque client blockchain
            pairs_to_check = await self._get_popular_pairs(blockchain, client)
        
        # Pour chaque paire
        for pair in pairs_to_check:
            token_address = pair.get("token_address")
            base_token = pair.get("base_token", "native")  # native, usdc, usdt, etc.
            
            if not token_address:
                continue
            
            # Obtenir les informations sur le token
            try:
                token_info = await client.get_token_info(token_address)
            except Exception as e:
                logger.debug(f"Impossible d'obtenir les informations pour le token {token_address}: {e}")
                continue
            
            # Pour chaque combinaison de DEX
            for i, dex1 in enumerate(dexes):
                for dex2 in dexes[i+1:]:
                    try:
                        # Vérifier s'il y a une opportunité entre ces deux DEX
                        opportunity = await self._check_arbitrage_opportunity(
                            blockchain, client, dex1, dex2, token_address, token_info, base_token
                        )
                        
                        if opportunity:
                            opportunities.append(opportunity)
                    except Exception as e:
                        logger.debug(f"Erreur lors de la vérification de l'arbitrage entre "
                                    f"{dex1['name']} et {dex2['name']} pour {token_info.get('symbol')}: {e}")
        
        return opportunities
    
    async def _check_arbitrage_opportunity(
        self,
        blockchain: str,
        client: BaseBlockchainClient,
        dex1: Dict[str, Any],
        dex2: Dict[str, Any],
        token_address: str,
        token_info: Dict[str, Any],
        base_token: str = "native"
    ) -> Optional[ArbitrageOpportunity]:
        """
        Vérifie s'il existe une opportunité d'arbitrage pour un token entre deux DEX.
        
        Args:
            blockchain: Nom de la blockchain
            client: Client blockchain
            dex1: Premier DEX
            dex2: Deuxième DEX
            token_address: Adresse du token
            token_info: Informations sur le token
            base_token: Token de base pour le swap (native, usdc, etc.)
            
        Returns:
            Opportunité d'arbitrage ou None
        """
        # Déterminer l'adresse du token de base
        base_token_address = self._get_base_token_address(blockchain, base_token)
        
        # Obtenir les informations sur les pools
        dex1_pool = await self._get_pool_info(client, dex1, token_address, base_token_address)
        dex2_pool = await self._get_pool_info(client, dex2, token_address, base_token_address)
        
        if not dex1_pool or not dex2_pool:
            return None
        
        # Obtenir les prix
        dex1_price = dex1_pool.get("price", 0)
        dex2_price = dex2_pool.get("price", 0)
        
        if dex1_price <= 0 or dex2_price <= 0:
            return None
        
        # Calculer la différence de prix
        price_diff = abs(dex1_price - dex2_price)
        price_diff_percent = price_diff / min(dex1_price, dex2_price) * 100
        
        # Si la différence est inférieure au minimum, pas d'opportunité
        if price_diff_percent < self.min_profit_percentage:
            return None
        
        # Déterminer le sens de l'arbitrage
        if dex1_price < dex2_price:
            buy_dex, sell_dex = dex1, dex2
            buy_price, sell_price = dex1_price, dex2_price
            buy_pool, sell_pool = dex1_pool, dex2_pool
        else:
            buy_dex, sell_dex = dex2, dex1
            buy_price, sell_price = dex2_price, dex1_price
            buy_pool, sell_pool = dex2_pool, dex1_pool
        
        # Calculer le montant optimal à utiliser pour l'arbitrage
        optimal_amount_usd = self._calculate_optimal_amount(
            price_diff_percent,
            buy_pool.get("liquidity_usd", 0),
            sell_pool.get("liquidity_usd", 0),
            self.max_trade_amount_usd
        )
        
        # Estimer le coût en gas
        gas_price = await client.get_gas_price()
        estimated_gas_units = self._estimate_gas_units(blockchain, self.use_flash_arbitrage)
        estimated_gas_cost_native = gas_price * estimated_gas_units * self.gas_multiplier
        
        # Convertir le coût en gas en USD
        native_price_usd = await self._get_native_price_usd(client, blockchain)
        estimated_gas_cost_usd = estimated_gas_cost_native * native_price_usd
        
        # Calculer le profit estimé
        token_amount = optimal_amount_usd / buy_price
        estimated_sell_amount_usd = token_amount * sell_price * (1 - self.max_slippage / 100)
        estimated_profit_usd = estimated_sell_amount_usd - optimal_amount_usd
        net_profit_usd = estimated_profit_usd - estimated_gas_cost_usd
        
        # Si le profit net est négatif, pas d'opportunité
        if net_profit_usd <= 0:
            return None
        
        # Créer l'opportunité d'arbitrage
        opportunity = ArbitrageOpportunity(
            id=f"{blockchain}_{token_address}_{buy_dex['name']}_{sell_dex['name']}_{int(time.time())}",
            timestamp=datetime.now(),
            blockchain=blockchain,
            token_address=token_address,
            token_symbol=token_info.get("symbol", "UNKNOWN"),
            token_name=token_info.get("name", "Unknown Token"),
            token_decimals=token_info.get("decimals", 18),
            
            dex_from=buy_dex["name"],
            dex_to=sell_dex["name"],
            
            buy_price=buy_price,
            sell_price=sell_price,
            
            price_difference=price_diff,
            price_difference_percent=price_diff_percent,
            
            estimated_profit_usd=estimated_profit_usd,
            estimated_gas_cost_usd=estimated_gas_cost_usd,
            net_profit_usd=net_profit_usd,
            
            input_amount_usd=optimal_amount_usd,
            
            dex1_pool_address=buy_pool.get("address", ""),
            dex2_pool_address=sell_pool.get("address", ""),
            dex1_liquidity_usd=buy_pool.get("liquidity_usd", 0),
            dex2_liquidity_usd=sell_pool.get("liquidity_usd", 0),
        )
        
        return opportunity
    
    async def _execute_arbitrage(self, opportunity: ArbitrageOpportunity) -> Dict[str, Any]:
        """
        Exécute une opportunité d'arbitrage.
        
        Args:
            opportunity: Opportunité d'arbitrage à exécuter
            
        Returns:
            Dict: Résultat de l'exécution
        """
        logger.info(f"Exécution de l'arbitrage: {opportunity.token_symbol} entre "
                   f"{opportunity.dex_from} et {opportunity.dex_to}, "
                   f"profit estimé: ${opportunity.net_profit_usd:.2f}")
        
        start_time = time.time()
        client = self.clients.get(opportunity.blockchain)
        
        if not client:
            return {
                "success": False,
                "error": f"Client pour la blockchain {opportunity.blockchain} non disponible",
                "opportunity": opportunity.to_dict()
            }
        
        try:
            result = {}
            
            if self.use_flash_arbitrage:
                # Exécution via flash arbitrage (nécessite un contrat spécifique)
                result = await self._execute_flash_arbitrage(client, opportunity)
            else:
                # Exécution manuelle (achat puis vente)
                result = await self._execute_manual_arbitrage(client, opportunity)
            
            execution_time = time.time() - start_time
            
            if result.get("success", False):
                self.successful_arbitrages += 1
                self.total_profit_usd += result.get("actual_profit_usd", 0)
                
                logger.info(f"Arbitrage réussi en {execution_time:.2f}s, "
                           f"profit réel: ${result.get('actual_profit_usd', 0):.2f}")
            else:
                self.failed_arbitrages += 1
                logger.warning(f"Échec de l'arbitrage: {result.get('error', 'Erreur inconnue')}")
            
            return {
                **result,
                "execution_time_seconds": execution_time,
                "opportunity": opportunity.to_dict()
            }
            
        except Exception as e:
            self.failed_arbitrages += 1
            execution_time = time.time() - start_time
            
            logger.error(f"Erreur lors de l'exécution de l'arbitrage: {e}", exc_info=True)
            
            return {
                "success": False,
                "error": str(e),
                "execution_time_seconds": execution_time,
                "opportunity": opportunity.to_dict()
            }
    
    async def _execute_flash_arbitrage(
        self, 
        client: BaseBlockchainClient, 
        opportunity: ArbitrageOpportunity
    ) -> Dict[str, Any]:
        """
        Exécute un flash arbitrage (en une seule transaction).
        
        Args:
            client: Client blockchain
            opportunity: Opportunité d'arbitrage
            
        Returns:
            Dict: Résultat de l'exécution
        """
        # Note: Ceci est un placeholder. L'implémentation complète nécessiterait
        # un contrat spécifique pour exécuter le flash arbitrage.
        logger.warning("Flash arbitrage non implémenté, utilisation de l'arbitrage manuel")
        return await self._execute_manual_arbitrage(client, opportunity)
    
    async def _execute_manual_arbitrage(
        self, 
        client: BaseBlockchainClient, 
        opportunity: ArbitrageOpportunity
    ) -> Dict[str, Any]:
        """
        Exécute un arbitrage manuel (achat puis vente).
        
        Args:
            client: Client blockchain
            opportunity: Opportunité d'arbitrage
            
        Returns:
            Dict: Résultat de l'exécution
        """
        # Obtenir le solde initial
        initial_balance = await client.get_balance()
        
        # 1. Achat du token sur le premier DEX
        buy_amount_native = opportunity.input_amount_usd / await self._get_native_price_usd(
            client, opportunity.blockchain
        )
        
        buy_tx = await client.buy_token(
            token_address=opportunity.token_address,
            amount=buy_amount_native,
            slippage=self.max_slippage,
            dex_address=opportunity.dex1_pool_address
        )
        
        if not buy_tx.get("success", False):
            return {
                "success": False,
                "error": f"Échec de l'achat: {buy_tx.get('error', 'Erreur inconnue')}",
                "buy_tx": buy_tx
            }
        
        # Attendre la confirmation de la transaction d'achat
        buy_tx_status = await client.get_transaction_status(buy_tx["tx_hash"])
        
        if not buy_tx_status.get("confirmed", False):
            return {
                "success": False,
                "error": "La transaction d'achat n'a pas été confirmée",
                "buy_tx": buy_tx,
                "buy_tx_status": buy_tx_status
            }
        
        # 2. Obtenir le solde du token
        token_balance = await client.get_token_balance(opportunity.token_address)
        
        if token_balance <= 0:
            return {
                "success": False,
                "error": "Aucun token reçu après l'achat",
                "buy_tx": buy_tx,
                "token_balance": token_balance
            }
        
        # 3. Vente du token sur le deuxième DEX
        sell_tx = await client.sell_token(
            token_address=opportunity.token_address,
            percent=100,  # Vendre tout
            slippage=self.max_slippage,
            dex_address=opportunity.dex2_pool_address
        )
        
        if not sell_tx.get("success", False):
            return {
                "success": False,
                "error": f"Échec de la vente: {sell_tx.get('error', 'Erreur inconnue')}",
                "buy_tx": buy_tx,
                "sell_tx": sell_tx
            }
        
        # Attendre la confirmation de la transaction de vente
        sell_tx_status = await client.get_transaction_status(sell_tx["tx_hash"])
        
        if not sell_tx_status.get("confirmed", False):
            return {
                "success": False,
                "error": "La transaction de vente n'a pas été confirmée",
                "buy_tx": buy_tx,
                "sell_tx": sell_tx,
                "sell_tx_status": sell_tx_status
            }
        
        # 4. Calculer le profit réel
        final_balance = await client.get_balance()
        balance_diff = final_balance - initial_balance
        
        # Convertir la différence en USD
        native_price_usd = await self._get_native_price_usd(client, opportunity.blockchain)
        actual_profit_usd = balance_diff * native_price_usd
        
        return {
            "success": True,
            "buy_tx": buy_tx,
            "sell_tx": sell_tx,
            "initial_balance": initial_balance,
            "final_balance": final_balance,
            "balance_diff": balance_diff,
            "actual_profit_usd": actual_profit_usd,
            "expected_profit_usd": opportunity.net_profit_usd,
            "profit_difference_usd": actual_profit_usd - opportunity.net_profit_usd
        }
    
    async def _auto_execute_best_opportunities(self, opportunities: List[ArbitrageOpportunity]) -> None:
        """
        Exécute automatiquement les meilleures opportunités d'arbitrage.
        
        Args:
            opportunities: Liste d'opportunités d'arbitrage
        """
        if not opportunities:
            return
        
        # Trier les opportunités par profit net
        sorted_opportunities = sorted(
            opportunities, 
            key=lambda o: o.net_profit_usd, 
            reverse=True
        )
        
        # Limiter au nombre maximum d'arbitrages concurrents
        opportunities_to_execute = sorted_opportunities[:self.max_concurrent_arbitrages]
        
        for opportunity in opportunities_to_execute:
            if opportunity.net_profit_usd >= self.config.get("min_auto_profit_usd", 1.0):
                logger.info(f"Exécution automatique de l'opportunité: {opportunity.token_symbol}, "
                           f"profit estimé: ${opportunity.net_profit_usd:.2f}")
                
                try:
                    await self._execute_arbitrage(opportunity)
                except Exception as e:
                    logger.error(f"Erreur lors de l'exécution automatique: {e}", exc_info=True)
    
    def _update_opportunities_cache(self, new_opportunities: List[ArbitrageOpportunity]) -> None:
        """
        Met à jour le cache des opportunités.
        
        Args:
            new_opportunities: Nouvelles opportunités à ajouter au cache
        """
        # Ajouter les nouvelles opportunités
        self._opportunities_cache.extend(new_opportunities)
        
        # Trier par timestamp (plus récent en premier)
        self._opportunities_cache.sort(key=lambda o: o.timestamp, reverse=True)
        
        # Limiter la taille du cache
        if len(self._opportunities_cache) > self._max_cache_size:
            self._opportunities_cache = self._opportunities_cache[:self._max_cache_size]
    
    @staticmethod
    def _get_base_token_address(blockchain: str, base_token: str) -> str:
        """
        Obtient l'adresse du token de base selon la blockchain.
        
        Args:
            blockchain: Nom de la blockchain
            base_token: Type de token de base (native, usdc, usdt, etc.)
            
        Returns:
            Adresse du token de base
        """
        # Mapping des adresses de tokens courants par blockchain
        token_addresses = {
            "solana": {
                "native": "So11111111111111111111111111111111111111112",  # SOL wrapped
                "usdc": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
                "usdt": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"
            },
            "avalanche": {
                "native": "0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7",  # WAVAX
                "usdc": "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E",
                "usdt": "0x9702230A8Ea53601f5cD2dc00fDBc13d4dF4A8c7"
            }
        }
        
        blockchain = blockchain.lower()
        base_token = base_token.lower()
        
        if blockchain not in token_addresses:
            return ""
        
        return token_addresses[blockchain].get(base_token, "")
    
    @staticmethod
    def _calculate_optimal_amount(
        price_diff_percent: float,
        buy_liquidity_usd: float,
        sell_liquidity_usd: float,
        max_amount_usd: float
    ) -> float:
        """
        Calcule le montant optimal à utiliser pour l'arbitrage.
        
        Args:
            price_diff_percent: Différence de prix en pourcentage
            buy_liquidity_usd: Liquidité du pool d'achat en USD
            sell_liquidity_usd: Liquidité du pool de vente en USD
            max_amount_usd: Montant maximum autorisé en USD
            
        Returns:
            Montant optimal en USD
        """
        # Limiter le montant à un pourcentage de la liquidité la plus faible
        # pour minimiser l'impact sur le prix
        min_liquidity = min(buy_liquidity_usd, sell_liquidity_usd)
        
        # Plus la différence de prix est importante, plus on peut utiliser
        # un pourcentage élevé de la liquidité
        liquidity_percent = min(price_diff_percent / 2, 5.0)
        optimal_by_liquidity = min_liquidity * (liquidity_percent / 100)
        
        # Limiter au montant maximum configuré
        return min(optimal_by_liquidity, max_amount_usd)
    
    @staticmethod
    def _estimate_gas_units(blockchain: str, use_flash: bool = False) -> int:
        """
        Estime le nombre d'unités de gas nécessaires pour l'arbitrage.
        
        Args:
            blockchain: Nom de la blockchain
            use_flash: Si True, utiliser un flash arbitrage
            
        Returns:
            Nombre d'unités de gas estimé
        """
        # Estimation approximative par blockchain et type d'arbitrage
        gas_estimates = {
            "solana": {
                "standard": 300000,
                "flash": 500000
            },
            "avalanche": {
                "standard": 250000,
                "flash": 400000
            }
        }
        
        blockchain = blockchain.lower()
        arbitrage_type = "flash" if use_flash else "standard"
        
        return gas_estimates.get(blockchain, {}).get(arbitrage_type, 300000)
    
    async def _get_native_price_usd(self, client: BaseBlockchainClient, blockchain: str) -> float:
        """
        Obtient le prix du token natif en USD.
        
        Args:
            client: Client blockchain
            blockchain: Nom de la blockchain
            
        Returns:
            Prix du token natif en USD
        """
        # Adresses des tokens natifs wrapped
        native_tokens = {
            "solana": "So11111111111111111111111111111111111111112",  # SOL wrapped
            "avalanche": "0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7",  # WAVAX
        }
        
        token_address = native_tokens.get(blockchain.lower(), "")
        if not token_address:
            return 0
        
        try:
            return await client.get_token_price(token_address)
        except Exception as e:
            logger.warning(f"Erreur lors de l'obtention du prix natif pour {blockchain}: {e}")
            return 0
    
    async def _get_popular_pairs(self, blockchain: str, client: BaseBlockchainClient) -> List[Dict[str, Any]]:
        """
        Obtient les paires populaires pour une blockchain.
        
        Args:
            blockchain: Nom de la blockchain
            client: Client blockchain
            
        Returns:
            Liste de paires populaires
        """
        # Cette méthode devrait être implémentée dans chaque client blockchain
        # Pour l'instant, retourner une liste vide
        return []
    
    async def _get_pool_info(
        self, 
        client: BaseBlockchainClient, 
        dex: Dict[str, Any], 
        token_address: str, 
        base_token_address: str
    ) -> Optional[Dict[str, Any]]:
        """
        Obtient les informations sur un pool de liquidité.
        
        Args:
            client: Client blockchain
            dex: Informations sur le DEX
            token_address: Adresse du token
            base_token_address: Adresse du token de base
            
        Returns:
            Informations sur le pool ou None
        """
        try:
            # TODO: Implémenter la logique spécifique à chaque DEX
            # Pour l'instant, simuler une réponse
            return {
                "address": f"{dex['name']}_{token_address}_{base_token_address}",
                "liquidity_usd": 1000000,  # Exemple
                "price": 1.0  # Exemple
            }
        except Exception as e:
            logger.debug(f"Erreur lors de l'obtention des informations du pool: {e}")
            return None 