#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestionnaire de Transactions pour GBPBot
=======================================

Ce module gère toutes les transactions blockchain du bot, avec:
- Optimisation du gas et du slippage
- Stratégies d'exécution (mempool, frontrunning)
- Gestion des erreurs et retry automatique
- Vérification avant exécution
- Retours d'état détaillés
"""

import os
import json
import time
import logging
import asyncio
from typing import Dict, List, Any, Optional, Union, Tuple, Callable
from datetime import datetime, timedelta
import random
from dataclasses import dataclass

from gbpbot.utils.logger import setup_logger

# Configuration du logger
logger = setup_logger("TransactionManager", logging.INFO)

@dataclass
class TransactionConfig:
    """Configuration pour une transaction"""
    blockchain: str
    wallet_address: str
    dex: str
    method: str  # buy, sell, swap, etc.
    token_address: str = ""
    token_symbol: str = ""
    amount: float = 0.0
    amount_in_usd: float = 0.0
    slippage: float = 0.01  # 1%
    deadline_minutes: int = 20
    gas_price_multiplier: float = 1.2
    priority_fee_multiplier: float = 1.5
    max_retries: int = 3
    retry_delay_ms: int = 1000
    simulate_before_send: bool = True
    use_flashbots: bool = False
    front_run_target: Optional[str] = None
    optimize_gas: bool = True
    verify_transaction: bool = True


@dataclass
class TransactionResult:
    """Résultat d'une transaction"""
    success: bool
    tx_hash: Optional[str] = None
    error: Optional[str] = None
    gas_used: Optional[int] = None
    gas_price: Optional[float] = None
    total_gas_cost: Optional[float] = None
    total_gas_cost_usd: Optional[float] = None
    block_number: Optional[int] = None
    timestamp: Optional[float] = None
    confirmations: int = 0
    receipt: Optional[Dict[str, Any]] = None
    simulation_result: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertir en dictionnaire"""
        return {
            "success": self.success,
            "tx_hash": self.tx_hash,
            "error": self.error,
            "gas_used": self.gas_used,
            "gas_price": self.gas_price,
            "total_gas_cost": self.total_gas_cost,
            "total_gas_cost_usd": self.total_gas_cost_usd,
            "block_number": self.block_number,
            "timestamp": self.timestamp,
            "confirmations": self.confirmations
        }


class TransactionManager:
    """
    Gestionnaire centralisé pour les transactions blockchain.
    
    Cette classe gère toutes les transactions blockchain du bot, avec:
    - Optimisation du gas pour maximiser la probabilité d'inclusion rapide
    - Gestion des erreurs et retry automatique
    - Support de différentes blockchains (Avalanche, Solana, Ethereum, etc.)
    - Techniques avancées: bundles, flashbots, MEV
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialise le gestionnaire de transactions.
        
        Args:
            config: Configuration du gestionnaire
        """
        self.config = config
        self.blockchain_clients = {}
        self.wallet_manager = None
        self.security_manager = None
        
        # Paramètres de transaction par défaut
        self.default_slippage = float(os.environ.get("DEFAULT_SLIPPAGE", "0.01"))  # 1%
        self.default_gas_multiplier = float(os.environ.get("DEFAULT_GAS_MULTIPLIER", "1.2"))
        self.default_priority_fee_multiplier = float(os.environ.get("DEFAULT_PRIORITY_FEE_MULTIPLIER", "1.5"))
        self.max_retries = int(os.environ.get("MAX_TX_RETRIES", "3"))
        self.verify_transactions = os.environ.get("VERIFY_TRANSACTIONS", "true").lower() == "true"
        self.use_flashbots = os.environ.get("USE_FLASHBOTS", "false").lower() == "true"
        
        # Statistiques de transactions
        self.tx_stats = {
            "total_txs": 0,
            "successful_txs": 0,
            "failed_txs": 0,
            "reverted_txs": 0,
            "retry_txs": 0,
            "total_gas_spent": 0.0,
            "total_gas_spent_usd": 0.0,
            "avg_confirmation_time_sec": 0.0,
            "last_tx_timestamp": None
        }
        
        # Gas cache pour différentes blockchains
        self.gas_cache = {}
        
        # File d'attente de transactions à traiter
        self.tx_queue = asyncio.Queue()
        self.tx_processing = False
        
        # Transactions en cours de confirmation
        self.pending_txs = {}
        
        logger.info("Gestionnaire de transactions initialisé")
    
    async def initialize(self, wallet_manager=None, security_manager=None):
        """
        Initialise les composants requis pour le gestionnaire.
        
        Args:
            wallet_manager: Gestionnaire de wallets
            security_manager: Gestionnaire de sécurité
        """
        self.wallet_manager = wallet_manager
        self.security_manager = security_manager
        
        # Initialiser les clients blockchain
        for chain in self.config.get("chains", []):
            client = await self._initialize_blockchain_client(chain)
            if client:
                self.blockchain_clients[chain["name"]] = client
        
        # Démarrer le worker de traitement des transactions
        asyncio.create_task(self._tx_queue_worker())
        
        # Démarrer le worker de vérification des transactions en attente
        asyncio.create_task(self._pending_tx_checker())
        
        logger.info(f"Gestionnaire de transactions initialisé avec {len(self.blockchain_clients)} clients blockchain")
    
    async def execute_transaction(self, tx_config: TransactionConfig) -> TransactionResult:
        """
        Exécute une transaction avec toutes les vérifications et optimisations.
        
        Args:
            tx_config: Configuration de la transaction
            
        Returns:
            TransactionResult: Résultat de la transaction
        """
        # Valider la configuration
        if not self._validate_tx_config(tx_config):
            return TransactionResult(
                success=False,
                error="Configuration de transaction invalide"
            )
        
        # Vérifier si la blockchain est supportée
        if tx_config.blockchain not in self.blockchain_clients:
            return TransactionResult(
                success=False,
                error=f"Blockchain {tx_config.blockchain} non supportée"
            )
        
        # Mettre à jour les statistiques
        self.tx_stats["total_txs"] += 1
        self.tx_stats["last_tx_timestamp"] = datetime.now().timestamp()
        
        # Vérifier la sécurité si un gestionnaire de sécurité est disponible
        if self.security_manager:
            is_safe, safety_details = await self._check_transaction_safety(tx_config)
            if not is_safe:
                logger.warning(f"Transaction bloquée pour raisons de sécurité: {safety_details}")
                return TransactionResult(
                    success=False,
                    error=f"Transaction non sécurisée: {safety_details}"
                )
        
        # Simuler la transaction si demandé
        if tx_config.simulate_before_send:
            simulation_result = await self._simulate_transaction(tx_config)
            if not simulation_result["success"]:
                logger.warning(f"Simulation de transaction échouée: {simulation_result['error']}")
                return TransactionResult(
                    success=False,
                    error=f"Échec de simulation: {simulation_result['error']}",
                    simulation_result=simulation_result
                )
        
        # Optimiser les paramètres de gas
        await self._optimize_gas_params(tx_config)
        
        # Exécuter la transaction avec retry
        for retry in range(tx_config.max_retries + 1):
            try:
                # Exécuter la transaction
                client = self.blockchain_clients[tx_config.blockchain]
                
                # Différentes stratégies d'exécution selon les paramètres
                if tx_config.use_flashbots and tx_config.blockchain == "ethereum":
                    result = await self._execute_flashbots_tx(client, tx_config)
                elif tx_config.front_run_target:
                    result = await self._execute_frontrun_tx(client, tx_config)
                else:
                    result = await self._execute_normal_tx(client, tx_config)
                
                # Vérifier le résultat
                if result.success:
                    # Ajouter la transaction aux transactions en attente pour vérification
                    if tx_config.verify_transaction and result.tx_hash:
                        self.pending_txs[result.tx_hash] = {
                            "tx_config": tx_config,
                            "result": result,
                            "timestamp": datetime.now().timestamp(),
                            "checked_count": 0,
                            "last_checked": None
                        }
                    
                    # Mettre à jour les statistiques
                    self.tx_stats["successful_txs"] += 1
                    if result.total_gas_cost_usd:
                        self.tx_stats["total_gas_spent_usd"] += result.total_gas_cost_usd
                    
                    logger.info(f"Transaction {result.tx_hash} exécutée avec succès")
                    return result
                else:
                    # Gérer les erreurs
                    error = result.error or "Erreur inconnue"
                    logger.warning(f"Échec de transaction (essai {retry+1}/{tx_config.max_retries+1}): {error}")
                    
                    # Si c'est le dernier essai, retourner l'erreur
                    if retry == tx_config.max_retries:
                        self.tx_stats["failed_txs"] += 1
                        return result
                    
                    # Sinon, attendre et réessayer
                    self.tx_stats["retry_txs"] += 1
                    await asyncio.sleep(tx_config.retry_delay_ms / 1000)
                    
                    # Optimiser à nouveau les paramètres de gas pour le prochain essai
                    await self._optimize_gas_params(tx_config, increase_factor=1.2)
            
            except Exception as e:
                logger.error(f"Exception lors de l'exécution de transaction: {str(e)}")
                
                # Si c'est le dernier essai, retourner l'erreur
                if retry == tx_config.max_retries:
                    self.tx_stats["failed_txs"] += 1
                    return TransactionResult(
                        success=False,
                        error=f"Exception: {str(e)}"
                    )
                
                # Sinon, attendre et réessayer
                self.tx_stats["retry_txs"] += 1
                await asyncio.sleep(tx_config.retry_delay_ms / 1000)
        
        # Ne devrait jamais arriver ici
        return TransactionResult(
            success=False,
            error="Erreur inattendue dans l'exécution de transaction"
        )
    
    async def queue_transaction(self, tx_config: TransactionConfig) -> str:
        """
        Ajoute une transaction à la file d'attente pour traitement asynchrone.
        
        Args:
            tx_config: Configuration de la transaction
            
        Returns:
            str: Identifiant de la transaction en file d'attente
        """
        tx_id = f"tx_{int(time.time())}_{random.randint(1000, 9999)}"
        
        # Ajouter à la file d'attente
        await self.tx_queue.put({
            "id": tx_id,
            "config": tx_config,
            "timestamp": datetime.now().timestamp()
        })
        
        logger.info(f"Transaction {tx_id} ajoutée à la file d'attente")
        return tx_id
    
    async def get_transaction_status(self, tx_hash: str) -> Dict[str, Any]:
        """
        Obtient l'état d'une transaction.
        
        Args:
            tx_hash: Hash de la transaction
            
        Returns:
            Dict: État de la transaction
        """
        # Vérifier d'abord si la transaction est en attente localement
        if tx_hash in self.pending_txs:
            pending_tx = self.pending_txs[tx_hash]
            blockchain = pending_tx["tx_config"].blockchain
            
            # Obtenir l'état depuis la blockchain
            if blockchain in self.blockchain_clients:
                client = self.blockchain_clients[blockchain]
                tx_status = await client.get_transaction_status(tx_hash)
                
                # Mettre à jour l'entrée en attente
                pending_tx["last_checked"] = datetime.now().timestamp()
                pending_tx["checked_count"] += 1
                
                return {
                    "pending": True,
                    "status": tx_status,
                    "tx_config": pending_tx["tx_config"].__dict__,
                    "initial_result": pending_tx["result"].to_dict(),
                    "last_checked": pending_tx["last_checked"],
                    "checked_count": pending_tx["checked_count"]
                }
        
        # Rechercher sur toutes les blockchains supportées
        for blockchain, client in self.blockchain_clients.items():
            try:
                tx_status = await client.get_transaction_status(tx_hash)
                if tx_status:
                    return {
                        "pending": False,
                        "status": tx_status,
                        "blockchain": blockchain
                    }
            except Exception as e:
                logger.error(f"Erreur lors de la vérification du statut sur {blockchain}: {str(e)}")
        
        # Transaction non trouvée
        return {
            "pending": False,
            "status": "not_found",
            "error": "Transaction non trouvée"
        }
    
    async def get_gas_price(self, blockchain: str) -> Dict[str, Any]:
        """
        Obtient le prix du gas actuel pour une blockchain.
        
        Args:
            blockchain: Nom de la blockchain
            
        Returns:
            Dict: Informations sur le prix du gas
        """
        if blockchain not in self.blockchain_clients:
            return {
                "error": f"Blockchain {blockchain} non supportée"
            }
        
        # Vérifier le cache (validité de 30 secondes)
        if blockchain in self.gas_cache:
            cache_entry = self.gas_cache[blockchain]
            if datetime.now().timestamp() - cache_entry["timestamp"] < 30:
                return cache_entry["data"]
        
        # Récupérer le prix du gas frais
        try:
            client = self.blockchain_clients[blockchain]
            gas_data = await client.get_gas_price()
            
            # Mettre à jour le cache
            self.gas_cache[blockchain] = {
                "timestamp": datetime.now().timestamp(),
                "data": gas_data
            }
            
            return gas_data
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du prix du gas pour {blockchain}: {str(e)}")
            return {
                "error": f"Erreur: {str(e)}"
            }
    
    async def _tx_queue_worker(self):
        """Worker pour traiter la file d'attente de transactions"""
        logger.info("Démarrage du worker de file d'attente de transactions")
        
        while True:
            try:
                # Récupérer une transaction de la file d'attente
                tx_data = await self.tx_queue.get()
                
                # Exécuter la transaction
                logger.info(f"Traitement de la transaction {tx_data['id']} depuis la file d'attente")
                result = await self.execute_transaction(tx_data["config"])
                
                # Marquer comme traitée
                self.tx_queue.task_done()
                
                # Traiter le résultat (à implémenter selon les besoins)
                
            except Exception as e:
                logger.error(f"Erreur dans le worker de file d'attente: {str(e)}")
                await asyncio.sleep(1)
    
    async def _pending_tx_checker(self):
        """Worker pour vérifier les transactions en attente de confirmation"""
        logger.info("Démarrage du worker de vérification des transactions en attente")
        
        while True:
            try:
                # Parcourir les transactions en attente
                for tx_hash, tx_data in list(self.pending_txs.items()):
                    try:
                        # Ignorer les transactions récemment vérifiées
                        current_time = datetime.now().timestamp()
                        if tx_data.get("last_checked") and current_time - tx_data["last_checked"] < 5:
                            continue
                        
                        # Vérifier l'état de la transaction
                        blockchain = tx_data["tx_config"].blockchain
                        if blockchain in self.blockchain_clients:
                            client = self.blockchain_clients[blockchain]
                            tx_status = await client.get_transaction_status(tx_hash)
                            
                            # Mettre à jour l'état
                            tx_data["last_checked"] = current_time
                            tx_data["checked_count"] += 1
                            
                            # Si la transaction est confirmée ou a échoué définitivement
                            if tx_status.get("confirmed") or tx_status.get("failed"):
                                logger.info(f"Transaction {tx_hash} finalisée: {'confirmée' if tx_status.get('confirmed') else 'échouée'}")
                                
                                # Calculer le temps de confirmation
                                if tx_status.get("confirmed"):
                                    confirm_time = current_time - tx_data["timestamp"]
                                    
                                    # Mettre à jour la moyenne des temps de confirmation
                                    old_avg = self.tx_stats["avg_confirmation_time_sec"]
                                    old_count = self.tx_stats["successful_txs"]
                                    new_avg = (old_avg * old_count + confirm_time) / (old_count + 1)
                                    self.tx_stats["avg_confirmation_time_sec"] = new_avg
                                elif tx_status.get("failed"):
                                    self.tx_stats["reverted_txs"] += 1
                                
                                # Retirer de la liste des transactions en attente
                                del self.pending_txs[tx_hash]
                            
                            # Abandonner les transactions trop anciennes (plus de 1 heure)
                            elif current_time - tx_data["timestamp"] > 3600:
                                logger.warning(f"Transaction {tx_hash} abandonnée après 1 heure sans confirmation")
                                del self.pending_txs[tx_hash]
                    
                    except Exception as e:
                        logger.error(f"Erreur lors de la vérification de {tx_hash}: {str(e)}")
                
                # Pause avant la prochaine vérification
                await asyncio.sleep(5)
            
            except Exception as e:
                logger.error(f"Erreur dans le worker de vérification: {str(e)}")
                await asyncio.sleep(5)
    
    async def _initialize_blockchain_client(self, chain_config: Dict[str, Any]):
        """Initialise un client blockchain"""
        try:
            chain_name = chain_config.get("name", "").lower()
            
            # Implémenter selon le besoin en fonction des blockchains supportées
            # Exemple simplifié:
            if chain_name == "avalanche":
                # from gbpbot.blockchain.avalanche import AvalancheClient
                # return AvalancheClient(chain_config)
                pass
            elif chain_name == "solana":
                # from gbpbot.blockchain.solana import SolanaClient
                # return SolanaClient(chain_config)
                pass
            elif chain_name == "ethereum":
                # from gbpbot.blockchain.ethereum import EthereumClient
                # return EthereumClient(chain_config)
                pass
            elif chain_name == "sonic":
                # from gbpbot.blockchain.sonic import SonicClient
                # return SonicClient(chain_config)
                pass
            else:
                logger.warning(f"Blockchain non supportée: {chain_name}")
                return None
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du client {chain_config.get('name')}: {str(e)}")
            return None
    
    def _validate_tx_config(self, tx_config: TransactionConfig) -> bool:
        """Valide la configuration d'une transaction"""
        
        # Vérifications de base
        if not tx_config.blockchain:
            logger.error("Blockchain non spécifiée")
            return False
        
        if not tx_config.wallet_address:
            logger.error("Adresse de wallet non spécifiée")
            return False
        
        if not tx_config.method:
            logger.error("Méthode de transaction non spécifiée")
            return False
        
        return True
    
    async def _check_transaction_safety(self, tx_config: TransactionConfig) -> Tuple[bool, str]:
        """Vérifie la sécurité d'une transaction"""
        # Exemple simple, à implémenter avec la logique complète
        if not self.security_manager:
            return True, ""
        
        # Logique spécifique pour vérifier la sécurité selon le type de transaction
        if tx_config.method == "buy":
            # Vérifier si le token est sécurisé
            token_data = {
                "address": tx_config.token_address,
                "blockchain": tx_config.blockchain,
                "symbol": tx_config.token_symbol
            }
            is_safe, details = await self.security_manager.check_token_security(token_data)
            if not is_safe:
                return False, f"Token non sécurisé: {details.get('reason', 'Raison inconnue')}"
        
        # Vérifier les limites de trading
        trade_data = {
            "method": tx_config.method,
            "amount_usd": tx_config.amount_in_usd,
            "expected_slippage": tx_config.slippage * 100
        }
        is_within_limits, reason = await self.security_manager.check_trade_limits(trade_data)
        if not is_within_limits:
            return False, reason or "Limites de trading dépassées"
        
        return True, ""
    
    async def _simulate_transaction(self, tx_config: TransactionConfig) -> Dict[str, Any]:
        """Simule une transaction pour vérifier qu'elle s'exécuterait correctement"""
        try:
            client = self.blockchain_clients[tx_config.blockchain]
            simulation_result = await client.simulate_transaction(tx_config)
            return simulation_result
        except Exception as e:
            logger.error(f"Erreur lors de la simulation: {str(e)}")
            return {
                "success": False,
                "error": f"Erreur de simulation: {str(e)}"
            }
    
    async def _optimize_gas_params(self, tx_config: TransactionConfig, increase_factor: float = 1.0):
        """Optimise les paramètres de gas d'une transaction"""
        try:
            # Récupérer les prix du gas actuels
            gas_data = await self.get_gas_price(tx_config.blockchain)
            
            # Si échec, utiliser les multipliers par défaut
            if "error" in gas_data:
                return
            
            # Appliquer différentes stratégies selon la blockchain
            if tx_config.blockchain == "ethereum" or tx_config.blockchain == "avalanche":
                # EIP-1559: base_fee + priority_fee
                if "base_fee" in gas_data and "priority_fee" in gas_data:
                    # Si on augmente les facteurs pour un retry
                    gas_multiplier = tx_config.gas_price_multiplier * increase_factor
                    priority_multiplier = tx_config.priority_fee_multiplier * increase_factor
                    
                    # Calculer les nouvelles valeurs
                    base_fee = gas_data["base_fee"]
                    new_priority_fee = gas_data["priority_fee"] * priority_multiplier
                    
                    # Mettre à jour la configuration
                    tx_config.gas_price_multiplier = gas_multiplier
                    tx_config.priority_fee_multiplier = priority_multiplier
                    
                    # Ajouter à la configuration pour l'utilisation dans l'exécution
                    tx_config.base_fee = base_fee
                    tx_config.priority_fee = new_priority_fee
                    
                    logger.info(f"Paramètres optimisés: base_fee={base_fee}, priority_fee={new_priority_fee}")
            
            elif tx_config.blockchain == "solana":
                # Solana utilise un modèle de prix différent
                if "recent_priority_fee" in gas_data:
                    priority_fee = gas_data["recent_priority_fee"] * tx_config.priority_fee_multiplier * increase_factor
                    tx_config.priority_fee = priority_fee
                    logger.info(f"Priorité Solana optimisée: {priority_fee}")
            
            # Autres blockchains à implémenter selon le besoin
            
        except Exception as e:
            logger.error(f"Erreur lors de l'optimisation du gas: {str(e)}")
    
    async def _execute_normal_tx(self, client, tx_config: TransactionConfig) -> TransactionResult:
        """Exécute une transaction normale"""
        # À implémenter avec les appels spécifiques au client
        # Exemple simplifié:
        try:
            if tx_config.method == "buy":
                tx_hash = await client.buy_token(
                    wallet_address=tx_config.wallet_address,
                    token_address=tx_config.token_address,
                    amount=tx_config.amount,
                    slippage=tx_config.slippage,
                    gas_price_multiplier=tx_config.gas_price_multiplier,
                    priority_fee=getattr(tx_config, "priority_fee", None)
                )
            elif tx_config.method == "sell":
                tx_hash = await client.sell_token(
                    wallet_address=tx_config.wallet_address,
                    token_address=tx_config.token_address,
                    amount=tx_config.amount,
                    slippage=tx_config.slippage,
                    gas_price_multiplier=tx_config.gas_price_multiplier,
                    priority_fee=getattr(tx_config, "priority_fee", None)
                )
            elif tx_config.method == "swap":
                tx_hash = await client.swap_tokens(
                    wallet_address=tx_config.wallet_address,
                    from_token=tx_config.from_token,
                    to_token=tx_config.to_token,
                    amount=tx_config.amount,
                    slippage=tx_config.slippage,
                    gas_price_multiplier=tx_config.gas_price_multiplier,
                    priority_fee=getattr(tx_config, "priority_fee", None)
                )
            else:
                return TransactionResult(
                    success=False,
                    error=f"Méthode non supportée: {tx_config.method}"
                )
            
            return TransactionResult(
                success=True,
                tx_hash=tx_hash,
                timestamp=datetime.now().timestamp()
            )
            
        except Exception as e:
            return TransactionResult(
                success=False,
                error=f"Erreur d'exécution: {str(e)}"
            )
    
    async def _execute_flashbots_tx(self, client, tx_config: TransactionConfig) -> TransactionResult:
        """Exécute une transaction via Flashbots (Ethereum)"""
        # À implémenter avec les appels flashbots
        # Exemple simplifié:
        try:
            # Simuler d'abord pour obtenir le calldata et le gas estimé
            simulation = await self._simulate_transaction(tx_config)
            if not simulation["success"]:
                return TransactionResult(
                    success=False,
                    error=f"Échec de simulation pour Flashbots: {simulation.get('error')}"
                )
            
            # Exécuter via Flashbots
            fb_result = await client.send_flashbots_bundle(
                wallet_address=tx_config.wallet_address,
                calldata=simulation["calldata"],
                gas_limit=int(simulation["gas_estimate"] * 1.1),  # +10% pour la marge
                base_fee=getattr(tx_config, "base_fee", None),
                priority_fee=getattr(tx_config, "priority_fee", None)
            )
            
            if fb_result["success"]:
                return TransactionResult(
                    success=True,
                    tx_hash=fb_result["tx_hash"],
                    timestamp=datetime.now().timestamp(),
                    simulation_result=simulation
                )
            else:
                return TransactionResult(
                    success=False,
                    error=f"Échec Flashbots: {fb_result.get('error')}",
                    simulation_result=simulation
                )
                
        except Exception as e:
            return TransactionResult(
                success=False,
                error=f"Erreur Flashbots: {str(e)}"
            )
    
    async def _execute_frontrun_tx(self, client, tx_config: TransactionConfig) -> TransactionResult:
        """Exécute une transaction de frontrunning"""
        # À implémenter avec la logique de frontrunning
        # Exemple simplifié:
        try:
            # Surveiller la transaction cible
            target_tx = await client.get_pending_transaction(tx_config.front_run_target)
            if not target_tx:
                return TransactionResult(
                    success=False,
                    error=f"Transaction cible {tx_config.front_run_target} non trouvée dans le mempool"
                )
            
            # Préparer notre transaction avec un gas légèrement plus élevé
            our_gas_price = target_tx["gas_price"] * 1.1  # +10%
            
            # Exécuter notre transaction
            if tx_config.method == "buy":
                tx_hash = await client.buy_token(
                    wallet_address=tx_config.wallet_address,
                    token_address=tx_config.token_address,
                    amount=tx_config.amount,
                    slippage=tx_config.slippage,
                    gas_price=our_gas_price
                )
            elif tx_config.method == "sell":
                tx_hash = await client.sell_token(
                    wallet_address=tx_config.wallet_address,
                    token_address=tx_config.token_address,
                    amount=tx_config.amount,
                    slippage=tx_config.slippage,
                    gas_price=our_gas_price
                )
            else:
                return TransactionResult(
                    success=False,
                    error=f"Méthode non supportée pour le frontrunning: {tx_config.method}"
                )
            
            return TransactionResult(
                success=True,
                tx_hash=tx_hash,
                timestamp=datetime.now().timestamp()
            )
            
        except Exception as e:
            return TransactionResult(
                success=False,
                error=f"Erreur de frontrunning: {str(e)}"
            ) 