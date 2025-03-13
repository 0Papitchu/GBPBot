#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module de stratégie MEV pour GBPBot
===================================

Ce module implémente des stratégies d'extraction de valeur maximale (MEV)
comme le frontrunning, les sandwich attacks et l'arbitrage. Il utilise les
optimiseurs MEV spécifiques à chaque blockchain pour maximiser les profits
tout en minimisant les risques.

Les stratégies supportées :
1. Frontrunning de swaps importants
2. Sandwich attacks sur des pools à faible liquidité
3. MEV-Boost et Bundle Aggregation
"""

import os
import time
import json
import asyncio
import logging
import random
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
from decimal import Decimal

from gbpbot.utils.logger import setup_logger
from gbpbot.core.optimization.jito_mev_optimizer import JitoMEVOptimizer, JitoConfig
from gbpbot.core.optimization.avax_mev_optimizer import AVAXMEVOptimizer, AVAXMEVConfig, MempoolMonitor
from gbpbot.core.optimization.tx_decoder import TransactionDecoder

# Initialisation du logger
logger = setup_logger("MEVStrategy", logging.INFO)

class MEVStrategy:
    """
    Stratégie d'exploitation MEV (Maximal Extractable Value) sur différentes blockchains.
    
    Cette classe implémente diverses techniques d'extraction de valeur, comme le
    frontrunning, les sandwich attacks et l'arbitrage. Elle est capable de
    s'adapter à différentes blockchains et d'utiliser les optimiseurs MEV
    spécifiques à chaque blockchain.
    """
    
    def __init__(self, blockchain: str, config: Dict[str, Any]):
        """
        Initialise la stratégie MEV.
        
        Args:
            blockchain: Nom de la blockchain (avax, solana, etc.)
            config: Configuration de la stratégie
        """
        self.blockchain = blockchain
        self.config = config
        self.logger = logging.getLogger(f"gbpbot.strategies.mev.{blockchain}")
        
        # Configuration de base
        self.min_profit_threshold = config.get("min_profit_threshold", 0.001)
        self.min_sandwich_profit_threshold = config.get("min_sandwich_profit_threshold", 0.005)
        self.max_gas_price = config.get("max_gas_price_gwei", 100.0) * 10**9
        self.gas_boost_percentage = config.get("gas_boost_percentage", 10.0) / 100.0
        self.simulation_only = config.get("simulation_only", True)
        
        # Paires à surveiller
        self.monitored_pairs = config.get("pairs_to_monitor", [])
        
        # Optimiseurs MEV spécifiques à la blockchain
        self.avax_optimizer = None
        self.solana_optimizer = None
        
        # Décodeur de transactions
        self.tx_decoder = None
        
        # État interne
        self.is_monitoring = False
        self.monitoring_task = None
        self.opportunities = []
        self.simulated_transactions = []
        self.mempool_transactions = {}
        
        # Moniteurs de mempool
        self.avax_mempool_monitor = None
        self.solana_mempool_monitor = None
        
        # Statistiques
        self.stats = {
            "start_time": time.time(),
            "frontrun_attempts": 0,
            "backrun_attempts": 0,
            "sandwich_attempts": 0,
            "successful_transactions": 0,
            "failed_transactions": 0,
            "estimated_profit": 0.0,
            "confirmed_profit": 0.0,
            "transactions": []
        }
        
        # Transactions en cours
        self.active_frontruns = {}
        self.active_backruns = {}
        self.active_sandwiches = {}
        
        # Transactions traitées
        self.processed_txs = set()
        
        # Initialiser les optimiseurs
        self._initialize_optimizers()
        
        # État de la stratégie
        self.running = False
        self.active_opportunities = {}
        self.completed_transactions = []
        
        logger.info(f"Stratégie MEV initialisée pour {self.blockchain}")
    
    def _initialize_optimizers(self):
        """
        Initialise les optimiseurs MEV pour les blockchains supportées.
        """
        # Optimiseur Solana via Jito
        if self.blockchain == "solana":
            try:
                jito_config = JitoConfig(
                    jito_auth_keypair_path=self.config.get("jito_auth_keypair_path"),
                    jito_searcher_endpoint=self.config.get("jito_searcher_endpoint", "http://localhost:8100"),
                    max_tip_percentage=float(self.config.get("max_tip_percentage", "1.0")),
                    bundle_timeout_seconds=int(self.config.get("bundle_timeout_seconds", "10"))
                )
                
                solana_rpc_url = self.config.get("solana_rpc_url")
                self.solana_optimizer = JitoMEVOptimizer(
                    config=jito_config,
                    solana_rpc_url=solana_rpc_url,
                    wallet_keypair_path=self.config.get("solana_wallet_keypair_path")
                )
                logger.info("Optimiseur MEV Solana (Jito) initialisé")
            except Exception as e:
                logger.error(f"Erreur lors de l'initialisation de l'optimiseur MEV Solana: {e}")
        
        # Optimiseur Avalanche
        if self.blockchain == "avalanche":
            try:
                avax_config = AVAXMEVConfig(
                    use_flashbots=self.config.get("use_flashbots", "true").lower() == "true",
                    max_gas_price_gwei=float(self.config.get("max_gas_price_gwei", "225.0")),
                    priority_fee_gwei=float(self.config.get("priority_fee_gwei", "2.0")),
                    gas_boost_percentage=self.gas_boost_percentage
                )
                
                avax_rpc_url = self.config.get("avax_rpc_url")
                self.avax_optimizer = AVAXMEVOptimizer(
                    config=avax_config,
                    avax_rpc_url=avax_rpc_url,
                    wallet_private_key=self.private_keys[0] if self.private_keys else None
                )
                logger.info("Optimiseur MEV Avalanche initialisé")
            except Exception as e:
                logger.error(f"Erreur lors de l'initialisation de l'optimiseur MEV Avalanche: {e}")
    
    def _load_monitored_pairs(self) -> Dict[str, Dict[str, Any]]:
        """
        Charge la liste des paires de tokens à surveiller.
        
        Returns:
            Dict avec les paires surveillées et leurs configurations
        """
        pairs_file = self.config.get("monitored_pairs_file", "config/mev_pairs.json")
        default_pairs = {
            # Pour Avalanche (TraderJoe v2)
            "AVAX-USDC": {
                "address": "0xEb466342C4d449BC9f53A865D5Cb90586f405215",
                "minLiquidity": 100000,
                "profitThreshold": 0.02
            },
            "AVAX-USDT": {
                "address": "0xbb4646a764358ee93c2a9c4a147d5aDEd527ab73",
                "minLiquidity": 100000,
                "profitThreshold": 0.02
            },
            "JOE-AVAX": {
                "address": "0x454E67025631C065d3cFAD6d71E6892f74487a15",
                "minLiquidity": 50000,
                "profitThreshold": 0.03
            }
        }
        
        try:
            if os.path.exists(pairs_file):
                with open(pairs_file, 'r') as f:
                    return json.load(f)
            else:
                # Utiliser les paires par défaut
                return default_pairs
        except Exception as e:
            logger.error(f"Erreur lors du chargement des paires: {e}")
            return default_pairs
    
    async def start(self):
        """
        Démarre la stratégie MEV.
        """
        logger.info(f"Démarrage de la stratégie MEV sur {self.blockchain}")
        
        # Réinitialiser les statistiques
        self.stats = {
            "start_time": time.time(),
            "frontrun_attempts": 0,
            "backrun_attempts": 0,
            "sandwich_attempts": 0,
            "successful_transactions": 0,
            "failed_transactions": 0,
            "estimated_profit": 0.0,
            "confirmed_profit": 0.0,
            "transactions": []
        }
        
        # Démarrer le monitoring des transactions selon la blockchain
        if self.blockchain == "avax":
            await self._start_avax_monitoring()
        elif self.blockchain == "solana":
            await self._start_solana_monitoring()
        else:
            logger.error(f"Blockchain non supportée: {self.blockchain}")
            
        # Démarrer le monitoring des transactions en cours
        asyncio.create_task(self._monitor_pending_transactions())
        
        logger.info("Stratégie MEV démarrée")
    
    async def stop(self):
        """
        Arrête la stratégie MEV.
        """
        logger.info("Arrêt de la stratégie MEV")
        
        # Arrêter les moniteurs de mempool
        if self.avax_mempool_monitor:
            await self.avax_mempool_monitor.stop_monitoring()
            
        if self.solana_mempool_monitor:
            await self.solana_mempool_monitor.stop_monitoring()
            
        # Sauvegarder les statistiques
        self._save_statistics()
        
        logger.info("Stratégie MEV arrêtée")
    
    async def _start_avax_monitoring(self):
        """
        Démarre la surveillance du mempool Avalanche pour détecter des opportunités MEV.
        """
        if not self.avax_optimizer or not self.avax_mempool_monitor:
            logger.error("Moniteur de mempool Avalanche non disponible")
            return
        
        # Ajouter un callback pour les transactions intéressantes
        self.avax_mempool_monitor.add_transaction_callback(self._handle_avax_transaction)
        
        # Démarrer la surveillance
        await self.avax_mempool_monitor.start_monitoring()
        logger.info("Surveillance du mempool Avalanche démarrée")
        
        # Boucle de maintenance
        while self.running:
            # Nettoyage des opportunités expirées
            current_time = time.time()
            expired_keys = []
            for tx_hash, opportunity in self.active_opportunities.items():
                if current_time - opportunity['timestamp'] > 60:  # 60 secondes max
                    expired_keys.append(tx_hash)
            
            for key in expired_keys:
                del self.active_opportunities[key]
            
            await asyncio.sleep(10)
    
    async def _start_solana_monitoring(self):
        """
        Démarre la surveillance du mempool Solana pour détecter des opportunités MEV.
        """
        # L'implémentation dépend de l'optimiseur Jito
        logger.info("Surveillance du mempool Solana via Jito initialisée")
        
        # La surveillance Solana utilise une approche différente avec Jito
        # Cette méthode serait plus développée avec les fonctionnalités spécifiques à Jito
        
        # Boucle de maintenance pour Solana
        while self.running:
            await asyncio.sleep(10)
    
    def _handle_avax_transaction(self, tx_hash, tx, function_name):
        """
        Traite une transaction détectée dans le mempool AVAX.
        
        Args:
            tx_hash: Hash de la transaction
            tx: Détails de la transaction
            function_name: Nom de la fonction décodée
        """
        # Ignorer les transactions trop petites
        tx_value = int(tx.get("value", "0"), 16) if isinstance(tx.get("value"), str) else int(tx.get("value", 0))
        gas_price = int(tx.get("gasPrice", "0"), 16) if isinstance(tx.get("gasPrice"), str) else int(tx.get("gasPrice", 0))
        
        # Vérifier si c'est une transaction de grande valeur ou avec un gas élevé
        is_high_value = tx_value > 1e18  # > 1 AVAX
        is_high_gas = gas_price > 50e9   # > 50 Gwei
        
        # Ignorer les petites transactions avec gas normal
        if not is_high_value and not is_high_gas:
            return
            
        # Créer une tâche asyncio pour analyser la transaction
        asyncio.create_task(self._analyze_transaction(tx_hash, tx, function_name))
    
    async def _analyze_transaction(self, tx_hash, tx, function_name):
        """
        Analyse une transaction pour déterminer quelle stratégie MEV appliquer.
        
        Args:
            tx_hash: Hash de la transaction
            tx: La transaction complète
            function_name: Nom de la fonction identifiée
        """
        # Vérifier si on a déjà traité cette transaction
        if tx_hash in self.processed_txs:
            return
            
        # Vérifier s'il s'agit d'une transaction de swap
        if not any(keyword in function_name for keyword in ["swap", "exactTokens", "exactETH"]):
            return
            
        # Extraire la valeur et le prix du gas
        tx_value = int(tx.get("value", "0"), 16) if isinstance(tx.get("value"), str) else int(tx.get("value", 0))
        gas_price = int(tx.get("gasPrice", "0"), 16) if isinstance(tx.get("gasPrice"), str) else int(tx.get("gasPrice", 0))
        
        # Évaluer la transaction pour une attaque sandwich
        sandwich_profit = await self._estimate_sandwich_profit(tx, function_name)
        if sandwich_profit >= self.min_sandwich_profit_threshold:
            # L'attaque sandwich est la plus rentable
            logger.info(f"Tentative d'attaque sandwich sur {tx_hash[:10]}... (profit: {sandwich_profit:.6f} AVAX)")
            await self._execute_sandwich_attack(tx_hash, tx, function_name, sandwich_profit)
            return
            
        # Évaluer pour frontrunning
        frontrun_profit = await self._estimate_frontrun_profit(tx, function_name)
        if frontrun_profit >= self.min_profit_threshold:
            # Frontrun est rentable
            logger.info(f"Tentative de frontrun sur {tx_hash[:10]}... (profit: {frontrun_profit:.6f} AVAX)")
            await self._analyze_and_execute_frontrun(tx_hash, tx, function_name)
            return
            
        # Évaluer pour backrunning
        backrun_profit = await self._estimate_backrun_profit(tx, function_name)
        if backrun_profit >= self.min_profit_threshold:
            # Backrun est rentable
            logger.info(f"Tentative de backrun sur {tx_hash[:10]}... (profit: {backrun_profit:.6f} AVAX)")
            await self._analyze_and_execute_backrun(tx_hash, tx, function_name)
            return
    
    async def _estimate_sandwich_profit(self, tx, function_name) -> float:
        """
        Estime le profit potentiel d'une attaque sandwich sur une transaction.
        
        Args:
            tx: La transaction à analyser
            function_name: Le nom de la fonction identifiée
            
        Returns:
            Le profit estimé en AVAX
        """
        if not self.avax_optimizer:
            return 0.0
        
        try:
            # Utiliser notre décodeur de transactions
            decoder = TransactionDecoder(self.avax_optimizer.web3)
            
            # Analyser la transaction
            swap_analysis = decoder.analyze_swap_transaction(tx)
            
            # Si ce n'est pas un swap ou pas un potentiel MEV, retourner 0
            if not swap_analysis["is_swap"] or not swap_analysis["potential_mev"]:
                return 0.0
            
            # Pour une attaque sandwich, le profit potentiel est généralement 
            # supérieur au frontrunning seul, mais avec plus de risque
            base_profit = decoder.estimate_profit_potential(swap_analysis)
            
            # Une attaque sandwich peut générer jusqu'à 2 fois plus de profit
            # qu'un simple frontrun, mais nécessite plus de capital
            estimated_profit = base_profit * 1.8
            
            # Ajuster en fonction du prix du gas actuel (2 transactions)
            current_gas = await self.avax_optimizer.get_current_gas_price()
            gas_price_gwei = current_gas.get("max_fee_per_gas", 0)
            
            # Une attaque sandwich nécessite 2 transactions (frontrun + backrun)
            estimated_gas_cost = 2 * 250000 * (gas_price_gwei * 1e9) / 1e18
            estimated_profit -= estimated_gas_cost
            
            # Seuil de profit plus élevé pour les attaques sandwich en raison du risque accru
            if estimated_profit < self.min_sandwich_profit_threshold:
                return 0.0
                
            logger.info(f"Profit estimé pour attaque sandwich: {estimated_profit:.6f} AVAX")
            return estimated_profit
            
        except Exception as e:
            logger.error(f"Erreur lors de l'estimation du profit de sandwich: {str(e)}")
            return 0.0
    
    async def _execute_sandwich_attack(self, target_tx_hash, target_tx, function_name, estimated_profit):
        """
        Exécute une attaque sandwich (frontrun + backrun) sur une transaction.
        
        Args:
            target_tx_hash: Hash de la transaction ciblée
            target_tx: La transaction ciblée
            function_name: Nom de la fonction identifiée
            estimated_profit: Profit estimé
            
        Returns:
            True si l'opération a réussi, False sinon
        """
        if not self.avax_optimizer:
            logger.error("Optimiseur AVAX non initialisé")
            return False
            
        # Extraire les détails de la transaction
        contract_address = target_tx.get("to")
        input_data = target_tx.get("input", "")
        
        try:
            # Décoder la transaction
            decoder = TransactionDecoder(self.avax_optimizer.web3)
            swap_details = decoder.decode_function_data(input_data, contract_address)
            
            # Vérifier si c'est un swap que nous pouvons attaquer
            if not swap_details["is_swap"]:
                return False
                
            # Créer les transactions de l'attaque sandwich
            function_sig = swap_details["function_signature"]
            
            # 1. Transaction de frontrun (acheter le token avant la victime)
            frontrun_tx = {
                "to": contract_address,
                "data": input_data,  # Simplifié pour la démo
                "value": target_tx.get("value", 0),
                "gas": int(target_tx.get("gas", 0)) * 1.1,
                "gasPrice": int(int(target_tx.get("gasPrice", 0)) * 1.2)  # 20% plus élevé
            }
            
            # 2. Transaction de backrun (vendre le token après la victime)
            backrun_tx = {
                "to": contract_address,
                "data": input_data,  # Simplifié pour la démo
                "value": target_tx.get("value", 0),
                "gas": int(target_tx.get("gas", 0)) * 1.1,
                "gasPrice": int(int(target_tx.get("gasPrice", 0)) * 1.05)  # 5% plus élevé
            }
            
            # Vérifier si nous avons déjà traité cette transaction
            if target_tx_hash in self.processed_txs:
                logger.info(f"Transaction {target_tx_hash[:10]}... déjà traitée")
                return False
            
            # Option 1: Utiliser un bundle Flashbots pour l'attaque complète
            if self.avax_optimizer.config.use_flashbots:
                bundle_txs = [
                    frontrun_tx,      # Notre frontrun
                    target_tx,        # La transaction victime
                    backrun_tx        # Notre backrun
                ]
                
                bundle_hash = await self.avax_optimizer.create_and_send_bundle(bundle_txs)
                
                if not bundle_hash:
                    logger.error(f"Échec de l'envoi du bundle sandwich pour {target_tx_hash[:10]}...")
                    return False
                    
                sandwich_id = bundle_hash
                
            else:
                # Option 2: Exécuter les transactions séparément
                # Envoyer le frontrun
                frontrun_hash = await self.avax_optimizer.send_frontrun_transaction(
                    target_tx_hash=target_tx_hash,
                    contract_address=contract_address,
                    function_signature=function_sig,
                    function_params=[],
                    value=int(frontrun_tx["value"]),
                    gas_limit=int(frontrun_tx["gas"])
                )
                
                if not frontrun_hash:
                    logger.error(f"Échec de l'envoi du frontrun pour le sandwich sur {target_tx_hash[:10]}...")
                    return False
                
                # Le backrun sera envoyé automatiquement après confirmation de la transaction cible
                # Nous enregistrons les détails pour le suivi
                sandwich_id = frontrun_hash
                
                # Stocker les détails du backrun pour exécution ultérieure
                self.active_sandwiches[sandwich_id] = {
                    "frontrun_tx": frontrun_hash,
                    "target_tx": target_tx_hash,
                    "backrun_data": {
                        "contract_address": contract_address,
                        "function_signature": function_sig,
                        "params": [],
                        "value": int(backrun_tx["value"]),
                        "gas_limit": int(backrun_tx["gas"])
                    },
                    "timestamp": time.time(),
                    "estimated_profit": estimated_profit,
                    "status": "frontrun_sent"
                }
            
            # Marquer comme traitée
            self.processed_txs.add(target_tx_hash)
            
            # Mettre à jour les statistiques
            self.stats["sandwich_attempts"] += 1
            self.stats["estimated_profit"] += estimated_profit
            
            logger.info(f"Attaque sandwich initiée avec succès: {sandwich_id}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'exécution de l'attaque sandwich: {str(e)}")
            return False
    
    def get_status(self) -> Dict[str, Any]:
        """
        Retourne le statut actuel de la stratégie MEV.
        
        Returns:
            Dict avec le statut de la stratégie
        """
        return {
            "running": self.running,
            "blockchain": self.blockchain,
            "active_opportunities": len(self.active_opportunities),
            "completed_transactions": len(self.completed_transactions),
            "simulation_mode": self.simulation_only,
            "last_transactions": self.completed_transactions[-5:] if self.completed_transactions else []
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Calcule et retourne les statistiques de la stratégie MEV.
        
        Returns:
            Dict avec les statistiques
        """
        # Statistiques de base
        stats = {
            "total_transactions": len(self.completed_transactions),
            "total_profit": 0.0,
            "average_profit": 0.0,
            "success_rate": 0.0,
            "frontrun_count": 0,
            "backrun_count": 0,
            "sandwich_count": 0
        }
        
        # Si aucune transaction, retourner les stats de base
        if not self.completed_transactions:
            return stats
        
        # Calculer les statistiques
        successful_txs = 0
        total_profit = 0.0
        
        for tx in self.completed_transactions:
            if tx.get('status') in ['completed', 'simulated']:
                successful_txs += 1
                total_profit += tx.get('actual_profit', tx.get('estimated_profit', 0.0))
            
            # Compter par type
            tx_type = tx.get('type', '')
            if tx_type == 'frontrun':
                stats['frontrun_count'] += 1
            elif tx_type == 'backrun':
                stats['backrun_count'] += 1
            elif tx_type == 'sandwich':
                stats['sandwich_count'] += 1
        
        # Calculer les moyennes et pourcentages
        stats['total_profit'] = total_profit
        stats['average_profit'] = total_profit / max(1, successful_txs)
        stats['success_rate'] = (successful_txs / max(1, len(self.completed_transactions))) * 100
        
        return stats
    
    async def _monitor_pending_transactions(self):
        """
        Surveille les transactions en cours pour vérifier leur statut
        et calculer les profits réels.
        """
        while True:
            try:
                # Vérifier les frontruns en cours
                await self._check_pending_frontruns()
                
                # Vérifier les backruns en cours
                await self._check_pending_backruns()
                
                # Vérifier les attaques sandwich en cours
                await self._check_pending_sandwiches()
                
                # Sauvegarder les statistiques périodiquement
                self._save_statistics()
                
        except Exception as e:
                logger.error(f"Erreur lors du monitoring des transactions: {str(e)}")
                
            # Attendre avant la prochaine vérification
            await asyncio.sleep(5)
    
    async def _check_pending_frontruns(self):
        """Vérifie le statut des transactions de frontrunning en cours."""
        if not self.avax_optimizer:
            return
            
        # Liste des transactions à supprimer
        to_remove = []
        
        for tx_hash, tx_info in self.active_frontruns.items():
            # Vérifier si la transaction est en attente depuis trop longtemps
            if time.time() - tx_info["timestamp"] > self.config.get("max_pending_time", 300):
                logger.warning(f"Transaction de frontrunning {tx_hash[:10]}... en attente depuis trop longtemps. Marquée comme expirée.")
                tx_info["status"] = "expired"
                to_remove.append(tx_hash)
                continue
            
            try:
                # Récupérer la transaction si l'optimiseur est disponible
                receipt = None
                if hasattr(self.avax_optimizer, 'web3'):
                    receipt = await self.avax_optimizer.web3.eth.get_transaction_receipt(tx_hash)
                
                if receipt:
                    # Mettre à jour le statut
                    if receipt["status"] == 1:  # Transaction réussie
                        logger.info(f"Transaction de frontrunning {tx_hash[:10]}... confirmée avec succès.")
                        tx_info["status"] = "confirmed"
                        tx_info["gas_used"] = receipt.get("gasUsed", 0)
                        tx_info["block_number"] = receipt.get("blockNumber", 0)
                        
                        # Calculer le profit réel si possible
                        if "estimated_profit" in tx_info:
                            actual_profit = await self._calculate_actual_profit(tx_hash, receipt, tx_info["estimated_profit"])
                            tx_info["actual_profit"] = actual_profit
                        
                        to_remove.append(tx_hash)
                    else:
                        # Transaction échouée
                        logger.warning(f"Transaction de frontrunning {tx_hash[:10]}... a échoué.")
                        tx_info["status"] = "failed"
                        to_remove.append(tx_hash)
            except Exception as e:
                logger.error(f"Erreur lors de la vérification du frontrun {tx_hash[:10]}...: {str(e)}")
                # Supprimer si la transaction n'existe pas
                if "not found" in str(e).lower():
                    to_remove.append(tx_hash)
        
        # Supprimer les transactions traitées de la liste des transactions en attente
        for tx_hash in to_remove:
            if tx_hash in self.active_frontruns:
                # Ajouter aux transactions terminées
                self.completed_transactions.append(self.active_frontruns[tx_hash])
                # Supprimer des transactions en attente
                del self.active_frontruns[tx_hash]
    
    async def _check_pending_backruns(self):
        """Vérifie le statut des transactions de backrunning en cours."""
        # Similaire à _check_pending_frontruns
        if not self.avax_optimizer or not self.avax_optimizer.web3:
            return
            
        # Liste des transactions à supprimer
        to_remove = []
        
        # Vérifier chaque backrun en cours
        for tx_hash, tx_info in self.active_backruns.items():
            # Ignorer les transactions trop récentes
            if time.time() - tx_info["timestamp"] < 5:
                continue
                
            try:
                # Récupérer la transaction
                receipt = await self.avax_optimizer.web3.eth.get_transaction_receipt(tx_hash)
                
                if receipt:
                    # Mettre à jour le statut
                    if receipt["status"] == 1:
                        # Transaction réussie
                        tx_info["status"] = "success"
                        self.stats["successful_transactions"] += 1
                        
                        # Calculer le profit réel
                        profit = await self._calculate_actual_profit(tx_hash, receipt, tx_info["estimated_profit"])
                        self.stats["confirmed_profit"] += profit
                        
                        # Enregistrer les détails de la transaction
                        self.stats["transactions"].append({
                            "type": "backrun",
                            "tx_hash": tx_hash,
                            "target_tx": tx_info["target_tx"],
                            "timestamp": tx_info["timestamp"],
                            "estimated_profit": tx_info["estimated_profit"],
                            "actual_profit": profit,
                            "status": "success"
                        })
                        
                        # Marquer pour suppression
                        to_remove.append(tx_hash)
                        
                    else:
                        # Transaction échouée
                        tx_info["status"] = "failed"
                        self.stats["failed_transactions"] += 1
                        
                        # Enregistrer les détails de la transaction
                        self.stats["transactions"].append({
                            "type": "backrun",
                            "tx_hash": tx_hash,
                            "target_tx": tx_info["target_tx"],
                            "timestamp": tx_info["timestamp"],
                            "estimated_profit": tx_info["estimated_profit"],
                            "actual_profit": 0,
                            "status": "failed"
                        })
                        
                        # Marquer pour suppression
                        to_remove.append(tx_hash)
                
                # Supprimer les transactions trop anciennes (plus de 10 minutes)
                elif time.time() - tx_info["timestamp"] > 600:
                    # Transaction probablement perdue
                    tx_info["status"] = "lost"
                    self.stats["failed_transactions"] += 1
                    
                    # Enregistrer les détails de la transaction
                    self.stats["transactions"].append({
                        "type": "backrun",
                        "tx_hash": tx_hash,
                        "target_tx": tx_info["target_tx"],
                        "timestamp": tx_info["timestamp"],
                        "estimated_profit": tx_info["estimated_profit"],
                        "actual_profit": 0,
                        "status": "lost"
                    })
                    
                    # Marquer pour suppression
                    to_remove.append(tx_hash)
                    
            except Exception as e:
                logger.error(f"Erreur lors de la vérification du backrun {tx_hash}: {str(e)}")
                
                # Supprimer les transactions qui génèrent des erreurs
                if "not found" in str(e).lower():
                    to_remove.append(tx_hash)
        
        # Supprimer les transactions traitées
        for tx_hash in to_remove:
            if tx_hash in self.active_backruns:
                del self.active_backruns[tx_hash]
    
    async def _check_pending_sandwiches(self):
        """Vérifie le statut des attaques sandwich en cours."""
        if not self.avax_optimizer:
            return
            
        # Liste des transactions à supprimer
        to_remove = []
        
        for sandwich_id, sandwich_info in self.active_sandwiches.items():
            # Vérifier si l'attaque est en attente depuis trop longtemps
            if time.time() - sandwich_info["timestamp"] > self.config.get("max_pending_time", 300):
                logger.warning(f"Attaque sandwich {sandwich_id} en attente depuis trop longtemps. Marquée comme expirée.")
                sandwich_info["status"] = "expired"
                to_remove.append(sandwich_id)
                continue
            
            try:
                if sandwich_info["status"] == "frontrun_sent":
                    # Vérifier si le frontrun est confirmé
                    frontrun_hash = sandwich_info["frontrun_tx"]
                    frontrun_receipt = None
                    
                    if hasattr(self.avax_optimizer, 'web3'):
                        frontrun_receipt = await self.avax_optimizer.web3.eth.get_transaction_receipt(frontrun_hash)
                        
                    if frontrun_receipt:
                        if frontrun_receipt["status"] == 1:
                            # Frontrun réussi, vérifier si la transaction cible est confirmée
                            target_tx_hash = sandwich_info["target_tx"]
                            target_receipt = None
                            
                            if hasattr(self.avax_optimizer, 'web3'):
                                target_receipt = await self.avax_optimizer.web3.eth.get_transaction_receipt(target_tx_hash)
                            
                            if target_receipt and target_receipt["status"] == 1:
                                # Transaction cible confirmée, envoyer le backrun
                                logger.info(f"Transaction cible {target_tx_hash[:10]}... confirmée. Envoi du backrun...")
                                
                                # Créer la transaction de backrun
                                backrun_tx = self._create_backrun_tx(sandwich_info)
                                
                                # Envoyer la transaction
                                backrun_hash = await self.avax_optimizer.send_transaction(backrun_tx)
                                
                                # Mettre à jour l'état du sandwich
                                sandwich_info["status"] = "backrun_sent"
                                sandwich_info["backrun_tx"] = backrun_hash
                                sandwich_info["backrun_timestamp"] = time.time()
                                
                                logger.info(f"Backrun envoyé: {backrun_hash[:10]}...")
                            else:
                                # Frontrun échoué
                                logger.warning(f"Transaction de frontrun {frontrun_hash[:10]}... a échoué.")
                                sandwich_info["status"] = "frontrun_failed"
                                to_remove.append(sandwich_id)
                        else:
                            # Frontrun échoué
                            logger.warning(f"Transaction de frontrun {frontrun_hash[:10]}... a échoué.")
                            sandwich_info["status"] = "frontrun_failed"
                            to_remove.append(sandwich_id)
                
                elif sandwich_info["status"] == "backrun_sent":
                    # Vérifier si le backrun est confirmé
                    backrun_hash = sandwich_info["backrun_tx"]
                    backrun_receipt = None
                    
                    if hasattr(self.avax_optimizer, 'web3'):
                        backrun_receipt = await self.avax_optimizer.web3.eth.get_transaction_receipt(backrun_hash)
                    
                    if backrun_receipt:
                        if backrun_receipt["status"] == 1:
                            # Backrun réussi, l'attaque sandwich est terminée
                            logger.info(f"Attaque sandwich {sandwich_id} terminée avec succès.")
                            
                            # Calculer le profit total
                            frontrun_profit = sandwich_info.get("frontrun_profit", 0)
                            backrun_profit = await self._calculate_backrun_profit(backrun_hash, backrun_receipt)
                            
                            total_profit = frontrun_profit + backrun_profit
                            
                            # Mettre à jour l'état du sandwich
                            sandwich_info["status"] = "completed"
                            sandwich_info["backrun_profit"] = backrun_profit
                            sandwich_info["total_profit"] = total_profit
                            
                            logger.info(f"Profit total de l'attaque sandwich: {total_profit:.6f} AVAX")
                            
                            # Marquer pour suppression
                            to_remove.append(sandwich_id)
                        else:
                            # Backrun échoué
                            logger.warning(f"Transaction de backrun {backrun_hash[:10]}... a échoué.")
                            sandwich_info["status"] = "backrun_failed"
                            to_remove.append(sandwich_id)
            except Exception as e:
                logger.error(f"Erreur lors de la vérification du sandwich {sandwich_id}: {str(e)}")
            
            # Supprimer les transactions qui génèrent des erreurs
            if "not found" in str(e).lower():
                to_remove.append(sandwich_id)
        
        # Supprimer les transactions traitées
        for sandwich_id in to_remove:
            if sandwich_id in self.active_sandwiches:
                # Ajouter aux transactions terminées
                self.completed_transactions.append(self.active_sandwiches[sandwich_id])
                # Supprimer des transactions en attente
                del self.active_sandwiches[sandwich_id]
    
    async def _calculate_actual_profit(self, tx_hash, receipt, estimated_profit):
        """
        Calcule le profit réel d'une transaction MEV.
        Dans une implémentation complète, cela analyserait les logs d'événements
        pour calculer les changements de balance.
        
        Args:
            tx_hash: Hash de la transaction
            receipt: Reçu de la transaction
            estimated_profit: Profit estimé
            
        Returns:
            Profit réel calculé
        """
        # Dans une implémentation complète, nous devrions analyser les logs
        # d'événements pour calculer les changements de balance
        # Pour cette démonstration, nous utilisons une estimation simplifiée
        
        # Calculer le coût en gas
        gas_used = receipt["gasUsed"]
        gas_price = int(receipt.get("effectiveGasPrice", 0))
        gas_cost = (gas_used * gas_price) / 1e18  # En AVAX
        
        # Profit réel = profit estimé - coût en gas
        # Dans une implémentation réelle, le profit serait calculé en analysant
        # les changements de balance avant/après la transaction
        actual_profit = estimated_profit - gas_cost
        
        # Limiter à 0 si négatif
        return max(0, actual_profit)
    
    def _save_statistics(self):
        """Sauvegarde les statistiques de la stratégie MEV."""
        try:
            # Créer le répertoire de statistiques s'il n'existe pas
            stats_dir = os.path.join(os.path.dirname(__file__), "..", "..", "data", "stats")
            os.makedirs(stats_dir, exist_ok=True)
            
            # Nom du fichier de statistiques
            filename = os.path.join(stats_dir, f"mev_stats_{int(self.stats['start_time'])}.json")
            
            # Sauvegarder les statistiques
            with open(filename, "w") as f:
                json.dump(self.stats, f, indent=2)
                
            logger.debug(f"Statistiques sauvegardées dans {filename}")
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des statistiques: {str(e)}")
    
    async def analyze_performance(self) -> Dict[str, Any]:
        """
        Analyse les performances de la stratégie MEV et fournit des recommandations
        pour l'amélioration des paramètres.
        
        Returns:
            Analyse des performances avec recommandations
        """
        result = {
            "total_attempts": 0,
            "success_rate": 0,
            "total_profit": 0,
            "average_profit_per_transaction": 0,
            "profit_per_hour": 0,
            "strategy_breakdown": {},
            "recommended_adjustments": []
        }
        
        # Calculer les statistiques de base
        total_attempts = self.stats["frontrun_attempts"] + self.stats["backrun_attempts"] + self.stats["sandwich_attempts"]
        result["total_attempts"] = total_attempts
        
        if total_attempts > 0:
            result["success_rate"] = (self.stats["successful_transactions"] / total_attempts) * 100
        
        result["total_profit"] = self.stats["confirmed_profit"]
        
        if self.stats["successful_transactions"] > 0:
            result["average_profit_per_transaction"] = self.stats["confirmed_profit"] / self.stats["successful_transactions"]
        
        # Calculer le profit par heure
        runtime_hours = (time.time() - self.stats["start_time"]) / 3600
        if runtime_hours > 0:
            result["profit_per_hour"] = self.stats["confirmed_profit"] / runtime_hours
        
        # Répartition par stratégie
        strategy_counts = {
            "frontrun": 0,
            "backrun": 0,
            "sandwich": 0
        }
        
        strategy_profits = {
            "frontrun": 0,
            "backrun": 0,
            "sandwich": 0
        }
        
        for tx in self.stats.get("transactions", []):
            tx_type = tx.get("type")
            if tx_type in strategy_counts:
                strategy_counts[tx_type] += 1
                
                if tx.get("status") == "success":
                    strategy_profits[tx_type] += tx.get("actual_profit", 0)
        
        # Calculer les statistiques par stratégie
        for strategy, count in strategy_counts.items():
            if count > 0:
                result["strategy_breakdown"][strategy] = {
                    "attempts": count,
                    "success_rate": 0,
                    "total_profit": strategy_profits[strategy],
                    "average_profit": 0
                }
                
                # Succès par stratégie
                success_count = len([tx for tx in self.stats.get("transactions", []) 
                                   if tx.get("type") == strategy and tx.get("status") == "success"])
                
                if success_count > 0:
                    result["strategy_breakdown"][strategy]["success_rate"] = (success_count / count) * 100
                    result["strategy_breakdown"][strategy]["average_profit"] = strategy_profits[strategy] / success_count
        
        # Générer des recommandations
        if result["success_rate"] < 30:
            result["recommended_adjustments"].append("Augmenter le prix du gas pour améliorer le taux de succès")
        
        if result["success_rate"] > 80 and result["average_profit_per_transaction"] < 0.005:
            result["recommended_adjustments"].append("Réduire le prix du gas pour améliorer la rentabilité")
        
        for strategy, stats in result["strategy_breakdown"].items():
            if stats["success_rate"] < 20:
                result["recommended_adjustments"].append(f"Réviser les paramètres de la stratégie {strategy}")
            
            if stats["average_profit"] < 0.001 and stats["attempts"] > 5:
                result["recommended_adjustments"].append(f"Abandonner ou optimiser la stratégie {strategy} en raison de sa faible rentabilité")
        
        return result

    async def initialize(self) -> bool:
        """
        Initialise la stratégie MEV.
        
        Returns:
            bool: True si l'initialisation est réussie, False sinon
        """
        try:
            self.logger.info(f"Initialisation de la stratégie MEV pour {self.blockchain}")
            
            # Initialisation des opportunités et transactions traitées
            self.opportunities = []
            self.simulated_transactions = []
            self.mempool_transactions = {}
            self.is_monitoring = False
            
            return True
        except Exception as e:
            self.logger.error(f"Erreur lors de l'initialisation de la stratégie MEV: {str(e)}")
            return False
    
    async def start_mempool_monitoring(self) -> bool:
        """
        Démarre la surveillance du mempool.
        
        Returns:
            bool: True si la surveillance est démarrée avec succès, False sinon
        """
        try:
            self.logger.info(f"Démarrage de la surveillance du mempool pour {self.blockchain}")
            
            # Initialisation du moniteur de mempool selon la blockchain
            if self.blockchain == "avax":
                self.monitoring_task = asyncio.create_task(self._monitor_avax_mempool())
            elif self.blockchain == "solana":
                self.monitoring_task = asyncio.create_task(self._monitor_solana_mempool())
            
            self.is_monitoring = True
            return True
        except Exception as e:
            self.logger.error(f"Erreur lors du démarrage de la surveillance du mempool: {str(e)}")
            return False
    
    async def stop_mempool_monitoring(self) -> bool:
        """
        Arrête la surveillance du mempool.
        
        Returns:
            bool: True si la surveillance est arrêtée avec succès, False sinon
        """
        try:
            self.logger.info("Arrêt de la surveillance du mempool")
            
            if hasattr(self, 'monitoring_task') and self.monitoring_task:
                self.is_monitoring = False
                self.monitoring_task.cancel()
                try:
                    await self.monitoring_task
                except asyncio.CancelledError:
                    pass
                self.monitoring_task = None
            
            return True
        except Exception as e:
            self.logger.error(f"Erreur lors de l'arrêt de la surveillance du mempool: {str(e)}")
            return False
    
    async def analyze_transaction(self, tx_data: Dict[str, Any]) -> bool:
        """
        Analyse une transaction pour détecter une opportunité MEV.
        
        Args:
            tx_data: Données de la transaction
            
        Returns:
            bool: True si une opportunité est détectée, False sinon
        """
        try:
            # Pour les tests, on simule une analyse simple
            # Dans une implémentation réelle, analyserait le contenu de la transaction
            is_opportunity = random.random() < 0.3  # 30% de chance d'être une opportunité
            
            if is_opportunity:
                self.logger.info(f"Opportunité MEV détectée: {tx_data.get('hash', 'unknown')}")
                
                # Ajouter l'opportunité à la liste
                self.opportunities.append({
                    "tx_data": tx_data,
                    "detected_at": time.time(),
                    "type": self._determine_opportunity_type(tx_data)
                })
            
            return is_opportunity
        except Exception as e:
            self.logger.error(f"Erreur lors de l'analyse de la transaction: {str(e)}")
            return False
    
    async def optimize_gas(self, tx: Dict[str, Any]) -> Dict[str, Any]:
        """
        Optimise le gas pour une transaction.
        
        Args:
            tx: Transaction à optimiser
            
        Returns:
            Dict[str, Any]: Résultat de l'optimisation
        """
        try:
            original_gas = tx.get("gas_price", 0)
            
            # Optimisation simulée pour les tests
            # Dans une implémentation réelle, calculerait le gas optimal
            optimized_gas = original_gas * (0.9 + random.random() * 0.1)  # Entre 90% et 100%
            
            return {
                "success": True,
                "original_gas_price": original_gas,
                "optimized_gas_price": optimized_gas,
                "savings_percentage": (original_gas - optimized_gas) / original_gas * 100 if original_gas > 0 else 0
            }
        except Exception as e:
            self.logger.error(f"Erreur lors de l'optimisation du gas: {str(e)}")
            return {"success": False, "reason": str(e)}
    
    # Méthodes privées d'implémentation
    async def _monitor_avax_mempool(self):
        """Surveille le mempool AVAX pour détecter des opportunités."""
        self.logger.info("Démarrage de la surveillance du mempool AVAX")
        
        while self.is_monitoring:
            try:
                # Simulation simple pour les tests
                await asyncio.sleep(1)
                
                # Dans une implémentation réelle, nous utiliserions websocket
                # Pour les tests, nous simulons des transactions dans le mempool
                if len(self.mempool_transactions) < 5:  # Limiter à 5 transactions pour les tests
                    tx_hash = f"0x{os.urandom(32).hex()}"
                    self.mempool_transactions[tx_hash] = {
                        "hash": tx_hash,
                        "from": f"0x{os.urandom(20).hex()}",
                        "to": f"0x{os.urandom(20).hex()}",
                        "value": random.randint(1, 10) * 10**18,
                        "gas": random.randint(21000, 100000),
                        "gasPrice": random.randint(30, 100) * 10**9,
                        "input": f"0x{os.urandom(100).hex()}"
                    }
            except asyncio.CancelledError:
                self.logger.info("Surveillance du mempool annulée")
                break
            except Exception as e:
                self.logger.error(f"Erreur lors de la surveillance du mempool: {str(e)}")
                await asyncio.sleep(5)  # Attendre avant de réessayer
        
        self.logger.info("Surveillance du mempool AVAX arrêtée")

    async def _monitor_solana_mempool(self):
        """Surveille le mempool Solana pour détecter des opportunités."""
        self.logger.info("Démarrage de la surveillance du mempool Solana")
        
        # Similaire à _monitor_avax_mempool mais pour Solana
        # Pour les tests, nous simulons des transactions
        
        while self.is_monitoring:
            try:
                await asyncio.sleep(1)
                
                # Simuler des transactions Solana
                if len(self.mempool_transactions) < 5:
                    tx_hash = f"{os.urandom(32).hex()}"
                    self.mempool_transactions[tx_hash] = {
                        "hash": tx_hash,
                        "from": f"{os.urandom(32).hex()}",
                        "to": f"{os.urandom(32).hex()}",
                        "lamports": random.randint(1, 1000) * 10**9,
                        "priority_fee": random.randint(1, 100) * 10**6
                    }
            except asyncio.CancelledError:
                self.logger.info("Surveillance du mempool Solana annulée")
                break
            except Exception as e:
                self.logger.error(f"Erreur lors de la surveillance du mempool Solana: {str(e)}")
                await asyncio.sleep(5)
        
        self.logger.info("Surveillance du mempool Solana arrêtée")

    def _determine_opportunity_type(self, tx_data: Dict[str, Any]) -> str:
        """Détermine le type d'opportunité MEV."""
        # Analyse simplifiée pour les tests
        types = ["frontrun", "backrun", "sandwich"]
        return random.choice(types)
