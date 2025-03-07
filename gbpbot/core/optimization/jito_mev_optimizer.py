#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module d'optimisation MEV pour Solana avec Jito Labs
===================================================

Ce module implémente l'intégration avec Jito Labs pour Solana, permettant
d'optimiser les transactions et de les protéger contre l'extraction de
valeur maximale (MEV). Il offre des fonctionnalités d'envoi de bundles de
transactions et d'accès au mempool privé de Jito.

Documentation Jito: https://jito-labs.gitbook.io/mev/
"""

import os
import time
import json
import logging
import asyncio
import base64
from typing import Dict, List, Any, Optional, Tuple, Union, Set
from dataclasses import dataclass
from datetime import datetime, timedelta

# Configuration du logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("jito_mev_optimizer")

# Essai d'importation des modules Solana et Jito
try:
    from solana.rpc.async_api import AsyncClient
    from solana.rpc.commitment import Commitment
    from solana.transaction import Transaction, TransactionInstruction
    from solana.publickey import PublicKey
    from solana.keypair import Keypair
    
    # Imports spécifiques à Jito
    try:
        import jito_searcher_client
        from jito_searcher_client import (
            JitoSearcherClient, 
            JitoBundle, 
            JitoTip, 
            BundleResult,
            MEV_PACKET_V0_DISCRIMINATOR
        )
        JITO_IMPORTS_OK = True
        logger.info("Modules Jito chargés avec succès")
    except ImportError:
        logger.warning("Modules Jito non disponibles. Installation via: pip install jito-searcher-client")
        JITO_IMPORTS_OK = False
        
    SOLANA_IMPORTS_OK = True
except ImportError as e:
    logger.warning(f"Modules Solana non disponibles: {e}")
    logger.warning("Installation via: pip install solana-py")
    SOLANA_IMPORTS_OK = False

@dataclass
class JitoConfig:
    """Configuration pour l'optimiseur Jito MEV."""
    jito_auth_keypair_path: Optional[str] = None  # Chemin vers le keypair d'authentification Jito
    jito_searcher_endpoint: str = "http://localhost:8100"  # Endpoint du service Jito
    jito_tip_account: Optional[str] = None  # Compte pour les tips (optionnel)
    bundle_timeout_seconds: int = 10  # Timeout pour l'envoi de bundles
    enable_private_mempool: bool = True  # Utiliser le mempool privé
    prioritize_transactions: bool = True  # Prioriser les transactions dans la queue
    max_tip_percentage: float = 1.0  # Pourcentage maximum du gain à donner en tip (0-100)
    min_tip_amount: float = 0.001  # Montant minimum de tip en SOL
    max_tip_amount: float = 0.1  # Montant maximum de tip en SOL
    simulation_before_send: bool = True  # Simuler avant d'envoyer
    
    def __post_init__(self):
        """Effectue des validations et ajustements après l'initialisation."""
        # Valider et ajuster les pourcentages
        self.max_tip_percentage = min(100.0, max(0.0, self.max_tip_percentage))
        
        # Valider et ajuster les montants
        self.min_tip_amount = max(0.0, self.min_tip_amount)
        self.max_tip_amount = max(self.min_tip_amount, self.max_tip_amount)
        
        # Vérifier que le keypair existe si spécifié
        if self.jito_auth_keypair_path and not os.path.exists(self.jito_auth_keypair_path):
            logger.warning(f"Keypair Jito non trouvé: {self.jito_auth_keypair_path}")

class JitoMEVOptimizer:
    """
    Optimiseur MEV pour Solana utilisant Jito Labs.
    
    Cette classe fournit des méthodes pour envoyer des transactions optimisées
    via le service Jito, réduisant l'impact du MEV et augmentant les chances
    d'exécution prioritaire.
    """
    
    def __init__(
        self,
        config: Optional[JitoConfig] = None,
        solana_rpc_url: Optional[str] = None,
        wallet_keypair_path: Optional[str] = None
    ):
        """
        Initialise l'optimiseur Jito MEV.
        
        Args:
            config: Configuration pour l'optimiseur Jito
            solana_rpc_url: URL du RPC Solana
            wallet_keypair_path: Chemin vers le keypair du wallet
        """
        self.config = config or JitoConfig()
        self.solana_rpc_url = solana_rpc_url or os.environ.get("SOLANA_RPC_URL", "https://api.mainnet-beta.solana.com")
        self.wallet_keypair_path = wallet_keypair_path
        
        self.jito_client = None
        self.solana_client = None
        self.wallet_keypair = None
        self.jito_auth_keypair = None
        
        # Statistiques
        self.total_bundles_sent = 0
        self.successful_bundles = 0
        self.failed_bundles = 0
        self.total_tips_paid = 0.0
        self.saved_from_mev = 0.0  # Valeur estimée sauvée du MEV
        
        # Initialisation des clients Solana et Jito
        if SOLANA_IMPORTS_OK:
            self.solana_client = AsyncClient(self.solana_rpc_url, commitment=Commitment("confirmed"))
            self._load_wallet_keypair()
            
            if JITO_IMPORTS_OK:
                self._init_jito_client()
                logger.info("Optimiseur Jito MEV initialisé avec succès")
            else:
                logger.warning("Fonctionnalités Jito désactivées en raison de dépendances manquantes")
        else:
            logger.error("Impossible d'initialiser l'optimiseur Jito MEV: modules Solana manquants")
    
    def _load_wallet_keypair(self) -> None:
        """Charge le keypair du wallet à partir du chemin spécifié."""
        if not self.wallet_keypair_path:
            logger.warning("Chemin du keypair wallet non spécifié")
            return
            
        try:
            with open(self.wallet_keypair_path, 'r') as f:
                keypair_data = json.load(f)
                self.wallet_keypair = Keypair.from_secret_key(bytes(keypair_data))
                logger.info(f"Keypair wallet chargé: {self.wallet_keypair.public_key}")
        except Exception as e:
            logger.error(f"Erreur lors du chargement du keypair wallet: {e}")
    
    def _init_jito_client(self) -> None:
        """Initialise le client Jito avec le keypair d'authentification."""
        if not JITO_IMPORTS_OK:
            return
            
        try:
            # Charger le keypair d'authentification Jito
            if self.config.jito_auth_keypair_path:
                try:
                    with open(self.config.jito_auth_keypair_path, 'r') as f:
                        auth_keypair_data = json.load(f)
                        self.jito_auth_keypair = Keypair.from_secret_key(bytes(auth_keypair_data))
                        logger.info(f"Keypair d'authentification Jito chargé")
                except Exception as e:
                    logger.error(f"Erreur lors du chargement du keypair Jito: {e}")
                    
            # Initialiser le client Jito
            self.jito_client = JitoSearcherClient(
                self.config.jito_searcher_endpoint,
                self.jito_auth_keypair.secret_key if self.jito_auth_keypair else None
            )
            logger.info(f"Client Jito initialisé avec l'endpoint: {self.config.jito_searcher_endpoint}")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du client Jito: {e}")
            self.jito_client = None
    
    async def send_transaction_via_jito(
        self,
        transaction: Transaction,
        expected_profit: Optional[float] = None,
        tip_override: Optional[float] = None
    ) -> Tuple[bool, str]:
        """
        Envoie une transaction via Jito pour optimisation MEV.
        
        Args:
            transaction: Transaction Solana à envoyer
            expected_profit: Profit attendu de la transaction en SOL (pour calculer le tip)
            tip_override: Montant du tip en SOL, remplace le calcul basé sur le profit
            
        Returns:
            Tuple[bool, str]: (Succès, Message/Identifiant de transaction)
        """
        if not JITO_IMPORTS_OK or not self.jito_client:
            logger.warning("Jito n'est pas disponible, la transaction sera envoyée normalement")
            return await self._fallback_send_transaction(transaction)
            
        if not self.wallet_keypair:
            logger.error("Wallet keypair non configuré pour l'envoi via Jito")
            return False, "Wallet keypair non configuré"
            
        try:
            # Préparation de la transaction
            if not transaction.signatures or not any(transaction.signatures):
                transaction = await self._prepare_transaction(transaction)
                
            # Calcul du tip basé sur le profit attendu ou utilisation de l'override
            tip_amount = 0.0
            if tip_override is not None:
                tip_amount = min(self.config.max_tip_amount, max(self.config.min_tip_amount, tip_override))
            elif expected_profit is not None and expected_profit > 0:
                # Calculer un pourcentage du profit comme tip, limité aux bornes configurées
                tip_amount = min(
                    self.config.max_tip_amount,
                    max(
                        self.config.min_tip_amount,
                        expected_profit * (self.config.max_tip_percentage / 100.0)
                    )
                )
            else:
                # Utiliser le minimum si pas de profit spécifié
                tip_amount = self.config.min_tip_amount
                
            # Convertir le tip en lamports (1 SOL = 10^9 lamports)
            tip_lamports = int(tip_amount * 1_000_000_000)
            
            # Créer un bundle Jito
            bundle = JitoBundle()
            bundle.add_transaction(transaction.serialize())
            
            # Ajouter un tip si configuré
            if self.config.jito_tip_account and tip_lamports > 0:
                tip_pubkey = PublicKey(self.config.jito_tip_account)
                tip = JitoTip(
                    tip_pubkey,
                    tip_lamports
                )
                bundle.set_tip(tip)
                logger.info(f"Tip de {tip_amount} SOL ({tip_lamports} lamports) ajouté à la transaction")
                
            # Envoyer le bundle à Jito
            logger.info("Envoi du bundle Jito...")
            start_time = time.time()
            
            # Simuler d'abord si configuré
            if self.config.simulation_before_send:
                simulation_result = await self.jito_client.simulate_bundle(bundle)
                if not simulation_result.success:
                    error_msg = f"Simulation du bundle Jito échouée: {simulation_result.error_msg}"
                    logger.error(error_msg)
                    self.failed_bundles += 1
                    return False, error_msg
                logger.info(f"Simulation du bundle Jito réussie, logs: {simulation_result.logs[:100]}...")
            
            # Envoyer le bundle
            result = await asyncio.wait_for(
                self.jito_client.send_bundle(bundle),
                timeout=self.config.bundle_timeout_seconds
            )
            
            elapsed = time.time() - start_time
            
            # Traiter le résultat
            if result.success:
                logger.info(f"Bundle Jito envoyé avec succès en {elapsed:.2f}s: {result.uuid}")
                self.successful_bundles += 1
                self.total_tips_paid += tip_amount
                
                # Estimer la valeur sauvée du MEV (simpliste, à raffiner)
                if expected_profit:
                    mev_saved_estimate = expected_profit * 0.05  # Estimation: 5% du profit aurait été capturé par MEV
                    self.saved_from_mev += mev_saved_estimate
                    
                return True, result.uuid
            else:
                error_msg = f"Échec de l'envoi du bundle Jito: {result.error_msg}"
                logger.error(error_msg)
                self.failed_bundles += 1
                
                # Si échec avec Jito, essayer l'envoi normal
                logger.info("Tentative d'envoi par le canal normal...")
                return await self._fallback_send_transaction(transaction)
                
        except asyncio.TimeoutError:
            logger.error(f"Timeout lors de l'envoi du bundle Jito après {self.config.bundle_timeout_seconds}s")
            self.failed_bundles += 1
            return await self._fallback_send_transaction(transaction)
            
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi via Jito: {e}")
            self.failed_bundles += 1
            return await self._fallback_send_transaction(transaction)
            
        finally:
            self.total_bundles_sent += 1
    
    async def send_transaction_bundle(
        self,
        transactions: List[Transaction],
        expected_profit: Optional[float] = None,
        tip_override: Optional[float] = None
    ) -> Tuple[bool, str]:
        """
        Envoie un bundle de transactions via Jito.
        Utile pour les arbitrages ou autres opérations nécessitant plusieurs transactions atomiques.
        
        Args:
            transactions: Liste de transactions Solana à envoyer atomiquement
            expected_profit: Profit attendu du bundle en SOL
            tip_override: Montant du tip en SOL
            
        Returns:
            Tuple[bool, str]: (Succès, Message/Identifiant de bundle)
        """
        if not JITO_IMPORTS_OK or not self.jito_client:
            logger.warning("Jito n'est pas disponible, les transactions seront envoyées séquentiellement")
            return await self._fallback_send_transactions(transactions)
            
        if not transactions:
            return False, "Aucune transaction fournie"
            
        if not self.wallet_keypair:
            logger.error("Wallet keypair non configuré pour l'envoi via Jito")
            return False, "Wallet keypair non configuré"
            
        try:
            # Préparation des transactions
            prepared_transactions = []
            for tx in transactions:
                if not tx.signatures or not any(tx.signatures):
                    tx = await self._prepare_transaction(tx)
                prepared_transactions.append(tx)
                
            # Calcul du tip
            tip_amount = 0.0
            if tip_override is not None:
                tip_amount = min(self.config.max_tip_amount, max(self.config.min_tip_amount, tip_override))
            elif expected_profit is not None and expected_profit > 0:
                # Calculer un pourcentage du profit comme tip, limité aux bornes configurées
                tip_amount = min(
                    self.config.max_tip_amount,
                    max(
                        self.config.min_tip_amount,
                        expected_profit * (self.config.max_tip_percentage / 100.0)
                    )
                )
            else:
                # Utiliser le minimum si pas de profit spécifié
                tip_amount = self.config.min_tip_amount
                
            # Convertir le tip en lamports
            tip_lamports = int(tip_amount * 1_000_000_000)
            
            # Créer un bundle Jito
            bundle = JitoBundle()
            for tx in prepared_transactions:
                bundle.add_transaction(tx.serialize())
                
            # Ajouter un tip si configuré
            if self.config.jito_tip_account and tip_lamports > 0:
                tip_pubkey = PublicKey(self.config.jito_tip_account)
                tip = JitoTip(
                    tip_pubkey,
                    tip_lamports
                )
                bundle.set_tip(tip)
                logger.info(f"Tip de {tip_amount} SOL ({tip_lamports} lamports) ajouté au bundle de {len(prepared_transactions)} transactions")
                
            # Envoyer le bundle à Jito
            logger.info(f"Envoi d'un bundle de {len(prepared_transactions)} transactions via Jito...")
            start_time = time.time()
            
            # Simuler d'abord si configuré
            if self.config.simulation_before_send:
                simulation_result = await self.jito_client.simulate_bundle(bundle)
                if not simulation_result.success:
                    error_msg = f"Simulation du bundle Jito échouée: {simulation_result.error_msg}"
                    logger.error(error_msg)
                    self.failed_bundles += 1
                    return False, error_msg
                logger.info(f"Simulation du bundle Jito réussie, logs: {simulation_result.logs[:100]}...")
            
            # Envoyer le bundle
            result = await asyncio.wait_for(
                self.jito_client.send_bundle(bundle),
                timeout=self.config.bundle_timeout_seconds
            )
            
            elapsed = time.time() - start_time
            
            # Traiter le résultat
            if result.success:
                logger.info(f"Bundle Jito de {len(prepared_transactions)} transactions envoyé avec succès en {elapsed:.2f}s: {result.uuid}")
                self.successful_bundles += 1
                self.total_tips_paid += tip_amount
                
                # Estimer la valeur sauvée du MEV
                if expected_profit:
                    mev_saved_estimate = expected_profit * 0.1  # Estimation: 10% du profit aurait été capturé par MEV pour les bundles
                    self.saved_from_mev += mev_saved_estimate
                    
                return True, result.uuid
            else:
                error_msg = f"Échec de l'envoi du bundle Jito: {result.error_msg}"
                logger.error(error_msg)
                self.failed_bundles += 1
                
                # Si échec avec Jito, essayer l'envoi séquentiel normal
                logger.info("Tentative d'envoi séquentiel par le canal normal...")
                return await self._fallback_send_transactions(prepared_transactions)
                
        except asyncio.TimeoutError:
            logger.error(f"Timeout lors de l'envoi du bundle Jito après {self.config.bundle_timeout_seconds}s")
            self.failed_bundles += 1
            return await self._fallback_send_transactions(transactions)
            
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi du bundle via Jito: {e}")
            self.failed_bundles += 1
            return await self._fallback_send_transactions(transactions)
            
        finally:
            self.total_bundles_sent += 1
    
    async def _prepare_transaction(self, transaction: Transaction) -> Transaction:
        """
        Prépare une transaction pour l'envoi via Jito.
        
        Args:
            transaction: Transaction à préparer
            
        Returns:
            Transaction: Transaction préparée
        """
        if not self.solana_client:
            raise ValueError("Client Solana non initialisé")
            
        if not self.wallet_keypair:
            raise ValueError("Wallet keypair non configuré")
            
        # Obtenir le blockhash récent
        recent_blockhash = (await self.solana_client.get_recent_blockhash()).value.blockhash
        transaction.recent_blockhash = recent_blockhash
        
        # Signer la transaction si ce n'est pas déjà fait
        if not transaction.signatures or not any(transaction.signatures):
            transaction.sign(self.wallet_keypair)
            
        return transaction
    
    async def _fallback_send_transaction(self, transaction: Transaction) -> Tuple[bool, str]:
        """
        Méthode de fallback pour envoyer une transaction via le RPC standard.
        
        Args:
            transaction: Transaction à envoyer
            
        Returns:
            Tuple[bool, str]: (Succès, Signature/Message d'erreur)
        """
        if not self.solana_client:
            return False, "Client Solana non initialisé"
            
        try:
            # Préparer la transaction si nécessaire
            if not transaction.signatures or not any(transaction.signatures):
                transaction = await self._prepare_transaction(transaction)
                
            # Envoyer la transaction
            result = await self.solana_client.send_transaction(transaction)
            tx_sig = result.value
            logger.info(f"Transaction envoyée via canal standard: {tx_sig}")
            
            return True, tx_sig
            
        except Exception as e:
            error_msg = f"Échec de l'envoi standard: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    async def _fallback_send_transactions(self, transactions: List[Transaction]) -> Tuple[bool, str]:
        """
        Méthode de fallback pour envoyer plusieurs transactions séquentiellement.
        
        Args:
            transactions: Liste de transactions à envoyer
            
        Returns:
            Tuple[bool, str]: (Succès, Message)
        """
        if not transactions:
            return False, "Aucune transaction fournie"
            
        success_count = 0
        signatures = []
        
        for i, tx in enumerate(transactions):
            success, result = await self._fallback_send_transaction(tx)
            if success:
                success_count += 1
                signatures.append(result)
            else:
                return False, f"Échec de la transaction {i+1}/{len(transactions)}: {result}"
                
            # Petit délai entre les transactions
            if i < len(transactions) - 1:
                await asyncio.sleep(0.5)
                
        return True, f"Envoyé {success_count}/{len(transactions)} transactions: {', '.join(signatures)}"
    
    async def optimize_transaction_timing(
        self,
        transaction: Transaction,
        target_slot: Optional[int] = None,
        max_wait_seconds: int = 30
    ) -> Tuple[bool, Union[Transaction, str]]:
        """
        Optimise le timing d'envoi d'une transaction pour un slot cible.
        
        Args:
            transaction: Transaction à optimiser
            target_slot: Slot cible (si None, le prochain slot valide)
            max_wait_seconds: Temps maximum d'attente en secondes
            
        Returns:
            Tuple[bool, Union[Transaction, str]]: (Succès, Transaction préparée ou message d'erreur)
        """
        if not self.solana_client:
            return False, "Client Solana non initialisé"
            
        try:
            start_time = time.time()
            
            # Obtenir le slot actuel
            current_slot = (await self.solana_client.get_slot()).value
            
            # Si pas de slot cible, viser le prochain slot
            if target_slot is None:
                target_slot = current_slot + 1
                
            # Vérifier si le slot cible est dans le futur
            if target_slot <= current_slot:
                # Si déjà passé, préparer simplement la transaction
                return True, await self._prepare_transaction(transaction)
                
            # Calculer le temps d'attente estimé (approximatif)
            # En moyenne, un slot Solana dure environ 400-600ms
            slots_to_wait = target_slot - current_slot
            estimated_wait_seconds = slots_to_wait * 0.5  # 500ms par slot en moyenne
            
            if estimated_wait_seconds > max_wait_seconds:
                return False, f"Temps d'attente estimé ({estimated_wait_seconds:.1f}s) dépasse le maximum configuré ({max_wait_seconds}s)"
                
            logger.info(f"Attente du slot {target_slot} (actuel: {current_slot}, ~{estimated_wait_seconds:.1f}s)...")
            
            # Attendre que le slot cible soit atteint ou presque
            while True:
                if time.time() - start_time > max_wait_seconds:
                    return False, f"Timeout après {max_wait_seconds}s d'attente"
                    
                current_slot = (await self.solana_client.get_slot()).value
                
                if current_slot >= target_slot - 1:  # Préparer légèrement en avance
                    # Obtenir le blockhash le plus récent possible
                    return True, await self._prepare_transaction(transaction)
                    
                # Courte pause avant la prochaine vérification
                await asyncio.sleep(0.1)
                
        except Exception as e:
            error_msg = f"Erreur lors de l'optimisation du timing: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Retourne les statistiques d'utilisation de l'optimiseur.
        
        Returns:
            Dict[str, Any]: Statistiques d'utilisation
        """
        success_rate = 0.0
        if self.total_bundles_sent > 0:
            success_rate = (self.successful_bundles / self.total_bundles_sent) * 100.0
            
        return {
            "total_bundles_sent": self.total_bundles_sent,
            "successful_bundles": self.successful_bundles,
            "failed_bundles": self.failed_bundles,
            "success_rate_percentage": success_rate,
            "total_tips_paid_sol": self.total_tips_paid,
            "estimated_mev_saved_sol": self.saved_from_mev,
            "net_benefit_sol": self.saved_from_mev - self.total_tips_paid,
            "jito_available": JITO_IMPORTS_OK and self.jito_client is not None,
            "jito_endpoint": self.config.jito_searcher_endpoint if self.jito_client else None
        }
    
    async def close(self) -> None:
        """Ferme les connexions clients."""
        if self.solana_client:
            await self.solana_client.close()
            
        # Le client Jito n'a pas de méthode close() explicite
        self.jito_client = None
        logger.info("Connexions fermées")

# Fonction utilitaire pour créer un optimiseur avec config par défaut
def create_jito_optimizer(
    solana_rpc_url: Optional[str] = None,
    wallet_keypair_path: Optional[str] = None,
    jito_auth_keypair_path: Optional[str] = None,
    jito_searcher_endpoint: Optional[str] = None,
    jito_tip_account: Optional[str] = None
) -> JitoMEVOptimizer:
    """
    Crée un optimiseur Jito MEV avec configuration par défaut.
    
    Args:
        solana_rpc_url: URL du RPC Solana
        wallet_keypair_path: Chemin du keypair wallet
        jito_auth_keypair_path: Chemin du keypair d'authentification Jito
        jito_searcher_endpoint: Endpoint du service Jito
        jito_tip_account: Compte pour les tips
        
    Returns:
        JitoMEVOptimizer: Instance de l'optimiseur
    """
    config = JitoConfig(
        jito_auth_keypair_path=jito_auth_keypair_path,
        jito_searcher_endpoint=jito_searcher_endpoint or "http://localhost:8100",
        jito_tip_account=jito_tip_account
    )
    
    return JitoMEVOptimizer(
        config=config,
        solana_rpc_url=solana_rpc_url,
        wallet_keypair_path=wallet_keypair_path
    ) 