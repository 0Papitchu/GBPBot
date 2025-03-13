#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module d'optimisation MEV pour Avalanche C-Chain
================================================

Ce module implémente l'intégration avec Flashbots et autres services MEV pour Avalanche,
permettant d'optimiser les transactions et de les protéger contre l'extraction de
valeur maximale (MEV). Il offre des fonctionnalités d'envoi de bundles de
transactions, de frontrunning optimisé et de protection contre les sandwiches.

Documentation de référence:
- Flashbots: https://docs.flashbots.net/
- Avalanche C-Chain: https://docs.avax.network/learn/platform-overview/avalanche-consensus
"""

import os
import time
import json
import logging
import asyncio
import secrets
import base64
import re
from typing import Dict, List, Any, Optional, Tuple, Union, Set
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal

# Configuration du logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("avax_mev_optimizer")

# Variables globales pour tracking des imports
flashbots_imports_ok = False
web3_imports_ok = False

# Essai d'importation des modules Web3 et Flashbots
try:
    from web3 import Web3
    from web3.middleware import geth_poa_middleware
    from web3.types import TxParams, Wei
    from eth_account.account import Account
    from eth_account.signers.local import LocalAccount
    
    # Imports spécifiques à Flashbots
    try:
        # Ces imports peuvent échouer car le package flashbots est optionnel
        # pylint: disable=import-error
        from flashbots import flashbot
        from flashbots.types import BundleOptions, BundleTx, SignedBundle
        flashbots_imports_ok = True
        logger.info("Modules Flashbots chargés avec succès")
    except ImportError:
        logger.warning("Modules Flashbots non disponibles. Installation via: pip install flashbots")
        # Définir des classes stub pour éviter les erreurs
        class BundleOptions:
            pass
        
        class BundleTx:
            pass
        
        class SignedBundle:
            pass
        
        def flashbot(*args, **kwargs):
            logger.warning("Fonction flashbot appelée mais non disponible")
            return None
        
    web3_imports_ok = True
except ImportError as e:
    logger.warning(f"Modules Web3 non disponibles: {e}")
    logger.warning("Installation via: pip install web3")
    
    # Définir des classes stub pour éviter les erreurs
    class Web3:
        @staticmethod
        def HTTPProvider(url):
            return None
            
    class LocalAccount:
        pass

@dataclass
class AVAXMEVConfig:
    """Configuration pour l'optimiseur MEV AVAX."""
    flashbots_relay_url: str = "https://relay.flashbots.net"  # URL du relay Flashbots
    use_flashbots: bool = True  # Utiliser Flashbots pour les bundles
    use_eden_network: bool = False  # Utiliser le réseau Eden (alternative à Flashbots)
    bundle_timeout_seconds: int = 15  # Timeout pour l'envoi de bundles
    max_gas_price_gwei: float = 225.0  # Prix maximum de gaz en GWEI
    priority_fee_gwei: float = 2.0  # Priority fee en GWEI (EIP-1559)
    gas_boost_percentage: float = 10.0  # Pourcentage d'augmentation du gaz pour frontrunning
    max_bundle_size: int = 6  # Nombre maximum de transactions dans un bundle
    simulation_before_send: bool = True  # Simuler avant d'envoyer
    revert_on_fail: bool = True  # Annuler toutes les transactions si une échoue
    private_tx_enabled: bool = True  # Envoyer des transactions privées (non visibles dans le mempool)
    min_profit_threshold: float = 0.01  # Profit minimum pour exécuter une transaction (en AVAX)
    
    def __post_init__(self):
        """Effectue des validations et ajustements après l'initialisation."""
        # Valider et ajuster les prix de gaz
        self.max_gas_price_gwei = max(1.0, self.max_gas_price_gwei)
        self.priority_fee_gwei = max(0.1, min(self.priority_fee_gwei, self.max_gas_price_gwei * 0.5))
        
        # Valider et ajuster le pourcentage de boost
        self.gas_boost_percentage = max(0.0, min(100.0, self.gas_boost_percentage))
        
        # Valider et ajuster la taille du bundle
        self.max_bundle_size = max(1, min(10, self.max_bundle_size))

class AVAXMEVOptimizer:
    """
    Optimiseur MEV pour Avalanche C-Chain.
    
    Cette classe fournit des méthodes pour envoyer des transactions optimisées
    via Flashbots et autres services MEV, réduisant l'impact du MEV et augmentant 
    les chances d'exécution prioritaire sur Avalanche.
    """
    
    def __init__(
        self,
        config: Optional[AVAXMEVConfig] = None,
        avax_rpc_url: Optional[str] = None,
        wallet_key_path: Optional[str] = None,
        wallet_private_key: Optional[str] = None
    ):
        """
        Initialise l'optimiseur MEV pour Avalanche.
        
        Args:
            config: Configuration MEV pour AVAX
            avax_rpc_url: URL du nœud RPC Avalanche
            wallet_key_path: Chemin vers le fichier de clé privée (alternative à wallet_private_key)
            wallet_private_key: Clé privée du wallet pour signer les transactions
        """
        self.config = config or AVAXMEVConfig()
        self.rpc_url = avax_rpc_url or os.environ.get("AVAX_RPC_URL", "https://api.avax.network/ext/bc/C/rpc")
        
        # Initialiser Web3 si disponible
        if web3_imports_ok:
            self.w3 = Web3(Web3.HTTPProvider(self.rpc_url))
            # Ajout du middleware POA pour Avalanche
            self.w3.middleware_onion.inject(geth_poa_middleware, layer=0)
            logger.info(f"Connexion Web3 établie: {self.w3.is_connected()}")
            
            # Vérifier la compatibilité EIP-1559
            self.eip1559_support = self._check_eip1559_support()
            logger.info(f"Support EIP-1559: {self.eip1559_support}")
        else:
            self.w3 = None
            logger.error("Web3 non disponible. L'optimiseur MEV ne fonctionnera pas.")
            return
        
        # Initialiser le compte
        self.account = self._initialize_account(wallet_key_path, wallet_private_key)
        if not self.account:
            logger.error("Compte non initialisé. Impossible de signer les transactions.")
            return
        
        # Initialiser Flashbots si disponible
        if flashbots_imports_ok and self.config.use_flashbots:
            try:
                self.flashbot_middleware = flashbot(
                    self.w3,
                    self.account,
                    self.config.flashbots_relay_url
                )
                logger.info("Middleware Flashbots initialisé avec succès")
            except Exception as e:
                logger.error(f"Erreur lors de l'initialisation du middleware Flashbots: {e}")
                self.flashbot_middleware = None
        else:
            self.flashbot_middleware = None
            if self.config.use_flashbots:
                logger.warning("Flashbots demandé mais non disponible. Les transactions seront envoyées normalement.")
        
        # Mémoire de nonces
        self._next_nonce = None
        self._last_nonce_check = 0
        
        # Cache de prix du gaz
        self._gas_price_cache = None
        self._last_gas_check = 0
        self._gas_cache_ttl = 10  # Secondes
        
        # Initialiser le moniteur de mempool
        self.mempool_monitor = None
        if hasattr(self.w3, 'eth') and hasattr(self.w3.eth, 'subscribe'):
            self.mempool_monitor = MempoolMonitor(self.w3)
            logger.info("Moniteur de mempool initialisé")
        else:
            logger.warning("Abonnement au mempool non supporté par le nœud RPC. Surveillance limitée.")
    
    def _initialize_account(self, key_path: Optional[str], private_key: Optional[str]) -> Optional[LocalAccount]:
        """
        Initialise le compte utilisateur à partir d'une clé privée.
        
        Args:
            key_path: Chemin vers le fichier de clé privée
            private_key: Clé privée directe en hexadécimal
            
        Returns:
            LocalAccount ou None en cas d'échec
        """
        try:
            if private_key:
                # Utiliser la clé privée fournie directement
                if not private_key.startswith('0x'):
                    private_key = '0x' + private_key
                account = Account.from_key(private_key)
                logger.info(f"Compte initialisé à partir de la clé privée: {account.address}")
                return account
            elif key_path and os.path.exists(key_path):
                # Charger la clé depuis le fichier
                with open(key_path, 'r') as f:
                    key_data = json.load(f)
                    if 'private_key' in key_data:
                        pk = key_data['private_key']
                        if not pk.startswith('0x'):
                            pk = '0x' + pk
                        account = Account.from_key(pk)
                        logger.info(f"Compte initialisé à partir du fichier de clé: {account.address}")
                        return account
            else:
                # Vérifier les variables d'environnement
                env_key = os.environ.get('AVAX_PRIVATE_KEY')
                if env_key:
                    if not env_key.startswith('0x'):
                        env_key = '0x' + env_key
                    account = Account.from_key(env_key)
                    logger.info(f"Compte initialisé à partir de la variable d'environnement: {account.address}")
                    return account
                
            logger.error("Aucune clé privée trouvée. Veuillez fournir une clé ou un chemin vers un fichier de clé.")
            return None
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du compte: {e}")
            return None
    
    def _check_eip1559_support(self) -> bool:
        """
        Vérifie si le réseau supporte EIP-1559.
        
        Returns:
            bool: True si EIP-1559 est supporté
        """
        try:
            if not hasattr(self.w3, 'eth'):
                return False
                
            # Vérifier si le dernier bloc contient les informations EIP-1559
            latest_block = self.w3.eth.get_block('latest')
            return 'baseFeePerGas' in latest_block
        except Exception as e:
            logger.warning(f"Erreur lors de la vérification du support EIP-1559: {e}")
            return False
    
    async def get_current_gas_price(self, force_refresh: bool = False) -> Dict[str, float]:
        """
        Obtient les prix de gaz actuels avec mise en cache.
        
        Args:
            force_refresh: Force le rafraîchissement du cache
            
        Returns:
            Dict avec les prix de gaz (max_fee_per_gas, priority_fee_per_gas, gas_price)
        """
        current_time = time.time()
        
        # Vérifier si le cache est valide
        if (not force_refresh and 
            self._gas_price_cache is not None and 
            (current_time - self._last_gas_check) < self._gas_cache_ttl):
            return self._gas_price_cache
        
        try:
            if not hasattr(self.w3, 'eth'):
                raise AttributeError("Web3 instance has no eth attribute")
                
            if self.eip1559_support:
                # Récupérer les informations EIP-1559
                max_priority_fee = self.w3.eth.max_priority_fee
                latest_block = self.w3.eth.get_block('latest')
                base_fee = latest_block['baseFeePerGas']  # Utilisation de l'accès par clé
                
                # Convertir en GWEI
                max_priority_fee_gwei = float(self.w3.from_wei(max_priority_fee, 'gwei'))
                base_fee_gwei = float(self.w3.from_wei(base_fee, 'gwei'))
                
                # Ajuster avec les paramètres de configuration
                priority_fee_gwei = min(
                    max_priority_fee_gwei, 
                    self.config.priority_fee_gwei
                )
                
                # Calculer le max_fee_per_gas (baseFee + priorityFee)
                max_fee_gwei = float(base_fee_gwei) * 1.2 + priority_fee_gwei
                max_fee_gwei = min(max_fee_gwei, self.config.max_gas_price_gwei)
                
                gas_price = {
                    'max_fee_per_gas': max_fee_gwei,
                    'max_priority_fee_per_gas': priority_fee_gwei,
                    'base_fee_per_gas': float(base_fee_gwei),
                    'gas_price': max_fee_gwei  # Pour compatibilité
                }
            else:
                # Utiliser le gas price standard pour les réseaux sans EIP-1559
                gas_price_wei = self.w3.eth.gas_price
                gas_price_gwei = float(self.w3.from_wei(gas_price_wei, 'gwei'))
                gas_price_gwei = min(gas_price_gwei * 1.1, self.config.max_gas_price_gwei)
                
                gas_price = {
                    'gas_price': gas_price_gwei,
                    'max_fee_per_gas': gas_price_gwei,  # Pour compatibilité
                    'max_priority_fee_per_gas': self.config.priority_fee_gwei  # Pour compatibilité
                }
            
            # Mise à jour du cache
            self._gas_price_cache = gas_price
            self._last_gas_check = current_time
            
            return gas_price
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des prix de gaz: {e}")
            # Utiliser des valeurs par défaut en cas d'échec
            return {
                'gas_price': self.config.max_gas_price_gwei * 0.5,
                'max_fee_per_gas': self.config.max_gas_price_gwei * 0.5,
                'max_priority_fee_per_gas': self.config.priority_fee_gwei
            }

    async def get_next_nonce(self, force_refresh: bool = False) -> int:
        """
        Obtient le prochain nonce pour le compte avec mise en cache.
        
        Args:
            force_refresh: Force le rafraîchissement du cache
            
        Returns:
            int: Le prochain nonce à utiliser
        """
        current_time = time.time()
        
        # Vérifier si le cache est valide (max 2 secondes)
        if (not force_refresh and 
            self._next_nonce is not None and 
            (current_time - self._last_nonce_check) < 2):
            # Incrémenter le nonce et retourner
            nonce = self._next_nonce
            self._next_nonce += 1
            return nonce
        
        try:
            if not hasattr(self.w3, 'eth'):
                raise AttributeError("Web3 instance has no eth attribute")
                
            # Récupérer le nonce actuel depuis la blockchain
            nonce = self.w3.eth.get_transaction_count(self.account.address, 'pending')
            self._next_nonce = nonce + 1
            self._last_nonce_check = current_time
            return nonce
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du nonce: {e}")
            if self._next_nonce is not None:
                # Utiliser la dernière valeur connue en cas d'échec
                nonce = self._next_nonce
                self._next_nonce += 1
                return nonce
            else:
                raise ValueError("Impossible de déterminer le nonce actuel") from e

    async def prepare_frontrun_transaction(
        self, 
        target_tx: Dict[str, Any], 
        contract_address: str,
        function_signature: str,
        function_params: List[Any],
        value: int = 0,
        gas_limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Prépare une transaction de frontrunning.
        
        Args:
            target_tx: Transaction cible à frontrun
            contract_address: Adresse du contrat à appeler
            function_signature: Signature de la fonction à appeler
            function_params: Paramètres de la fonction
            value: Montant de AVAX à envoyer (en wei)
            gas_limit: Limite de gaz (si None, estimée automatiquement)
            
        Returns:
            Dict: Transaction préparée
        """
        if not web3_imports_ok or not hasattr(self.w3, 'eth'):
            raise RuntimeError("Web3 non disponible, impossible de préparer la transaction")
            
        # Encoder la fonction avec ses paramètres
        contract = self.w3.eth.contract(address=contract_address, abi=[])
        data = contract.encodeABI(fn_name=function_signature, args=function_params)
        
        # Calculer le gas_price en fonction de la transaction cible
        target_gas_price = target_tx.get('gasPrice', 0)
        if isinstance(target_gas_price, str) and target_gas_price.startswith('0x'):
            target_gas_price = int(target_gas_price, 16)
            
        # Boost du gas price pour frontrunning
        gas_boost = 1 + (self.config.gas_boost_percentage / 100.0)
        gas_price = int(target_gas_price * gas_boost)
        
        # Limiter le gas price au maximum configuré
        max_gas_price_wei = self.w3.to_wei(self.config.max_gas_price_gwei, 'gwei')
        gas_price = min(gas_price, max_gas_price_wei)
        
        # Obtenir le nonce
        nonce = await self.get_next_nonce()
        
        # Estimer la limite de gaz si non fournie
        if gas_limit is None:
            try:
                gas_limit = self.w3.eth.estimate_gas({
                    'from': self.account.address,
                    'to': contract_address,
                    'data': data,
                    'value': value
                })
                # Ajouter une marge de sécurité de 20%
                gas_limit = int(gas_limit * 1.2)
            except Exception as e:
                logger.warning(f"Erreur lors de l'estimation du gaz: {e}")
                # Valeur par défaut sécuritaire
                gas_limit = 500000
        
        # Préparer la transaction
        if self.eip1559_support:
            # Obtenir les informations de gaz EIP-1559
            gas_data = await self.get_current_gas_price(force_refresh=True)
            max_fee_per_gas = self.w3.to_wei(gas_data['max_fee_per_gas'], 'gwei')
            max_priority_fee_per_gas = self.w3.to_wei(gas_data['max_priority_fee_per_gas'], 'gwei')
            
            # Booster le priority fee pour frontrunning
            max_priority_fee_per_gas = int(max_priority_fee_per_gas * gas_boost)
            
            tx = {
                'from': self.account.address,
                'to': contract_address,
                'value': value,
                'gas': gas_limit,
                'maxFeePerGas': max_fee_per_gas,
                'maxPriorityFeePerGas': max_priority_fee_per_gas,
                'nonce': nonce,
                'data': data,
                'chainId': self.w3.eth.chain_id,
                'type': '0x2'  # Type de transaction EIP-1559
            }
        else:
            # Transaction legacy
            tx = {
                'from': self.account.address,
                'to': contract_address,
                'value': value,
                'gas': gas_limit,
                'gasPrice': gas_price,
                'nonce': nonce,
                'data': data,
                'chainId': self.w3.eth.chain_id
            }
        
        return tx

    async def send_frontrun_transaction(
        self, 
        target_tx_hash: str,
        contract_address: str,
        function_signature: str,
        function_params: List[Any],
        value: int = 0,
        gas_limit: Optional[int] = None
    ) -> str:
        """
        Envoie une transaction de frontrunning.
        
        Args:
            target_tx_hash: Hash de la transaction cible à frontrun
            contract_address: Adresse du contrat à appeler
            function_signature: Signature de la fonction à appeler
            function_params: Paramètres de la fonction
            value: Montant de AVAX à envoyer (en wei)
            gas_limit: Limite de gaz (si None, estimée automatiquement)
            
        Returns:
            str: Hash de la transaction envoyée
        """
        if not web3_imports_ok or not hasattr(self.w3, 'eth'):
            raise RuntimeError("Web3 non disponible, impossible d'envoyer la transaction")
            
        # Récupérer la transaction cible
        target_tx = self.w3.eth.get_transaction(target_tx_hash)
        if not target_tx:
            raise ValueError(f"Transaction cible non trouvée: {target_tx_hash}")
        
        # Préparer la transaction de frontrunning
        tx = await self.prepare_frontrun_transaction(
            target_tx=target_tx,
            contract_address=contract_address,
            function_signature=function_signature,
            function_params=function_params,
            value=value,
            gas_limit=gas_limit
        )
        
        # Signer la transaction
        signed_tx = self.account.sign_transaction(tx)
        
        # Envoyer la transaction
        if flashbots_imports_ok and self.flashbot_middleware is not None and self.config.use_flashbots:
            # Utiliser Flashbots pour l'envoi
            bundle = [
                {"signed_transaction": signed_tx.rawTransaction},
                {"txHash": target_tx_hash}
            ]
            
            # Calculer le block target (bloc actuel + 1)
            block_number = self.w3.eth.block_number
            target_block = block_number + 1
            
            try:
                # Envoyer le bundle via Flashbots
                bundle_response = await self.w3.eth.flashbots.send_bundle(
                    bundle,
                    target_block_number=target_block
                )
                
                logger.info(f"Bundle Flashbots envoyé: {bundle_response.bundle_hash}")
                return signed_tx.hash.hex()
            except Exception as e:
                logger.error(f"Erreur lors de l'envoi du bundle Flashbots: {e}")
                # Fallback vers l'envoi normal
                tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
                return tx_hash.hex()
        else:
            # Envoi normal
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
            return tx_hash.hex()

    async def create_and_send_bundle(
        self, 
        transactions: List[Dict[str, Any]]
    ) -> Optional[str]:
        """
        Crée et envoie un bundle de transactions.
        
        Args:
            transactions: Liste de transactions à inclure dans le bundle
            
        Returns:
            str ou None: Hash du bundle ou None en cas d'échec
        """
        if not web3_imports_ok or not hasattr(self.w3, 'eth'):
            raise RuntimeError("Web3 non disponible, impossible d'envoyer le bundle")
            
        if not flashbots_imports_ok or self.flashbot_middleware is None:
            logger.warning("Flashbots non disponible, envoi des transactions individuellement")
            results = []
            for tx in transactions:
                try:
                    signed_tx = self.account.sign_transaction(tx)
                    tx_hash = self.w3.eth.send_raw_transaction(signed_tx.rawTransaction)
                    results.append(tx_hash.hex())
                except Exception as e:
                    logger.error(f"Erreur lors de l'envoi de la transaction: {e}")
            
            return ",".join(results) if results else None
        
        # Signer toutes les transactions
        signed_txs = []
        for tx in transactions:
            signed_tx = self.account.sign_transaction(tx)
            signed_txs.append({"signed_transaction": signed_tx.rawTransaction})
        
        # Calculer le block target (bloc actuel + 1)
        block_number = self.w3.eth.block_number
        target_block = block_number + 1
        
        try:
            # Envoyer le bundle via Flashbots
            bundle_response = await self.w3.eth.flashbots.send_bundle(
                signed_txs,
                target_block_number=target_block
            )
            
            logger.info(f"Bundle Flashbots envoyé: {bundle_response.bundle_hash}")
            return bundle_response.bundle_hash
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi du bundle Flashbots: {e}")
            # Fallback vers l'envoi normal
            results = []
            for signed_tx in signed_txs:
                try:
                    tx_hash = self.w3.eth.send_raw_transaction(signed_tx["signed_transaction"])
                    results.append(tx_hash.hex())
                except Exception as e2:
                    logger.error(f"Erreur lors de l'envoi de la transaction: {e2}")
            
            return ",".join(results) if results else None

    async def simulate_transaction(self, 
                                  tx: Dict[str, Any], 
                                  block_identifier: Optional[str] = "latest") -> Dict[str, Any]:
        """
        Simule l'exécution d'une transaction pour vérifier sa validité et son comportement.
        
        Args:
            tx: Transaction à simuler
            block_identifier: Bloc sur lequel faire la simulation
            
        Returns:
            Résultat de la simulation avec des indicateurs de succès et consommation de gas
        """
        if not web3_imports_ok or self.w3 is None:
            logger.warning("Web3 non disponible. Impossible de simuler la transaction.")
            return {"success": False, "error": "Web3 non disponible"}
            
        result = {
            "success": False,
            "gas_used": 0,
            "error": None,
            "return_value": None,
            "logs": []
        }
        
        try:
            # Préparer les paramètres de la transaction pour la simulation
            sim_tx = {
                "from": tx.get("from", self.account.address if self.account else None),
                "to": tx.get("to"),
                "data": tx.get("data", tx.get("input", "0x")),
                "value": tx.get("value", 0),
                "gas": tx.get("gas", 500000),
                "gasPrice": tx.get("gasPrice", 0),
                "nonce": tx.get("nonce", await self.get_next_nonce())
            }
            
            # Utiliser la méthode call pour simuler la transaction
            result_data = await self.w3.eth.call(sim_tx, block_identifier)
            
            # La transaction a réussi si nous arrivons ici sans exception
            result["success"] = True
            result["return_value"] = result_data.hex()
            
            # Estimer la consommation de gas
            try:
                gas_used = await self.w3.eth.estimate_gas(sim_tx)
                result["gas_used"] = gas_used
            except Exception as e:
                # La transaction peut réussir mais l'estimation de gas peut échouer
                logger.warning(f"Erreur lors de l'estimation du gas: {str(e)}")
                result["gas_used"] = tx.get("gas", 500000)
            
        except Exception as e:
            error_msg = str(e)
            result["success"] = False
            result["error"] = error_msg
            
            # Analyser l'erreur pour des informations supplémentaires
            if "revert" in error_msg.lower():
                # Extraire la raison du revert si disponible
                reason_match = re.search(r"reverted: (.+?)$", error_msg)
                if reason_match:
                    result["revert_reason"] = reason_match.group(1)
                else:
                    result["revert_reason"] = "Unknown revert reason"
            
        return result
        
    async def simulate_frontrun_profit(self, 
                                       target_tx: Dict[str, Any], 
                                       frontrun_tx: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simule une opération de frontrunning complète pour estimer sa rentabilité.
        
        Args:
            target_tx: Transaction ciblée pour le frontrun
            frontrun_tx: Notre transaction de frontrun
            
        Returns:
            Résultat de la simulation avec profit estimé et risques
        """
        result = {
            "success": False,
            "estimated_profit": 0.0,
            "risks": [],
            "recommendation": "abort"  # "execute", "abort", "adjust"
        }
        
        try:
            # Simuler notre transaction de frontrun
            frontrun_sim = await self.simulate_transaction(frontrun_tx)
            if not frontrun_sim["success"]:
                result["risks"].append(f"Frontrun échouerait: {frontrun_sim.get('error', 'Erreur inconnue')}")
                return result
                
            # Simuler la transaction ciblée après notre frontrun
            target_sim = await self.simulate_transaction(target_tx)
            if not target_sim["success"]:
                result["risks"].append("La transaction cible échouerait après notre frontrun")
                result["risks"].append(f"Raison: {target_sim.get('error', 'Erreur inconnue')}")
                return result
            
            # À ce stade, les deux transactions réussiraient
            # Nous devrions avoir une logique plus sophistiquée pour estimer le profit
            # en examinant les conséquences des deux transactions sur les pools
            
            # Pour l'instant, nous utilisons une méthode simplifiée
            from gbpbot.core.optimization.tx_decoder import TransactionDecoder
            decoder = TransactionDecoder(self.w3)
            
            # Analyser la transaction cible
            swap_analysis = decoder.analyze_swap_transaction(target_tx)
            estimated_profit = decoder.estimate_profit_potential(swap_analysis)
            
            # Calculer les coûts de notre frontrun
            gas_price = int(frontrun_tx.get("gasPrice", 0))
            gas_limit = int(frontrun_tx.get("gas", frontrun_sim["gas_used"]))
            gas_cost_wei = gas_price * gas_limit
            gas_cost_avax = gas_cost_wei / 1e18
            
            # Profit net = profit brut - coûts
            net_profit = estimated_profit - gas_cost_avax
            
            result["estimated_profit"] = net_profit
            result["success"] = True
            
            # Déterminer la recommandation
            if net_profit > self.config.min_profit_threshold:
                result["recommendation"] = "execute"
            elif net_profit > 0:
                result["recommendation"] = "adjust"
                result["risks"].append("Profit faible, considérer une augmentation du slippage ou du gas")
            else:
                result["recommendation"] = "abort"
                result["risks"].append("Profit négatif après les coûts de gas")
                
        except Exception as e:
            logger.error(f"Erreur lors de la simulation du profit: {str(e)}")
            result["risks"].append(f"Erreur de simulation: {str(e)}")
            
        return result

class MempoolMonitor:
    """
    Moniteur de mempool pour Avalanche C-Chain.
    
    Surveille les transactions dans le mempool et identifie des opportunités
    de frontrunning ou d'arbitrage.
    """
    
    def __init__(self, web3_instance):
        """
        Initialise le moniteur de mempool.
        
        Args:
            web3_instance: Instance Web3 connectée à un nœud Avalanche
        """
        self.w3 = web3_instance
        self.subscription = None
        self.running = False
        self.callbacks = []
        
        # Pool de transactions surveillées
        self.pending_txs = {}
        
        # Liste des signatures de fonctions à surveiller (swap, addLiquidity, etc.)
        self.target_signatures = {
            # TraderJoe v2
            "0x3598d8ab": "exactInputSingle",  # exactInputSingle(ExactInputSingleParams)
            "0x12210e8a": "exactOutputSingle",  # exactOutputSingle(ExactOutputSingleParams)
            
            # TraderJoe v1 et Pangolin
            "0x7ff36ab5": "swapExactETHForTokens",  # swapExactETHForTokens(uint,address[],address,uint)
            "0x791ac947": "swapExactTokensForETHSupportingFeeOnTransferTokens",  # swapExactTokensForETHSupportingFeeOnTransferTokens(uint,uint,address[],address,uint)
            "0x38ed1739": "swapExactTokensForTokens",  # swapExactTokensForTokens(uint,uint,address[],address,uint)
            "0x4a25d94a": "swapTokensForExactETH",  # swapTokensForExactETH(uint,uint,address[],address,uint)
            "0x5c11d795": "swapExactTokensForTokensSupportingFeeOnTransferTokens",  # swapExactTokensForTokensSupportingFeeOnTransferTokens(uint,uint,address[],address,uint)
            
            # Fonctions d'ajout de liquidité
            "0xe8e33700": "addLiquidity",  # addLiquidity(address,address,uint,uint,uint,uint,address,uint)
            "0xf305d719": "addLiquidityETH",  # addLiquidityETH(address,uint,uint,uint,address,uint)
        }
    
    async def start_monitoring(self):
        """
        Démarre la surveillance du mempool.
        """
        if self.running:
            logger.warning("Le moniteur de mempool est déjà en cours d'exécution")
            return
            
        if not hasattr(self.w3, 'eth') or not hasattr(self.w3.eth, 'subscribe'):
            logger.error("Le nœud RPC ne supporte pas les abonnements au mempool")
            return
            
        try:
            self.subscription = await self.w3.eth.subscribe('newPendingTransactions')
            self.running = True
            logger.info("Surveillance du mempool démarrée avec succès")
            asyncio.create_task(self._process_transactions())
        except Exception as e:
            logger.error(f"Erreur lors du démarrage de la surveillance du mempool: {e}")
    
    async def stop_monitoring(self):
        """
        Arrête la surveillance du mempool.
        """
        if not self.running:
            return
            
        try:
            if self.subscription:
                await self.w3.eth.unsubscribe(self.subscription)
            self.running = False
            logger.info("Surveillance du mempool arrêtée")
        except Exception as e:
            logger.error(f"Erreur lors de l'arrêt de la surveillance du mempool: {e}")
    
    def add_transaction_callback(self, callback):
        """
        Ajoute un callback pour les transactions détectées.
        
        Args:
            callback: Fonction à appeler quand une transaction intéressante est détectée
        """
        self.callbacks.append(callback)
    
    async def _process_transactions(self):
        """
        Traite les transactions entrantes dans le mempool.
        """
        while self.running:
            try:
                tx_hash = await self.w3.eth.get_subscription_update(self.subscription)
                if not tx_hash:
                    await asyncio.sleep(0.1)
                    continue
                    
                # Récupérer les détails de la transaction
                tx = await self.w3.eth.get_transaction(tx_hash)
                if not tx or not tx.get('input') or len(tx.get('input')) < 10:
                    continue
                    
                # Vérifier si c'est une transaction intéressante
                method_id = tx['input'][:10]  # Les 4 premiers bytes de la donnée (0x + 8 caractères)
                if method_id in self.target_signatures:
                    # Analyser la transaction
                    function_name = self.target_signatures[method_id]
                    self.pending_txs[tx_hash] = {
                        'tx': tx,
                        'function': function_name,
                        'timestamp': time.time()
                    }
                    
                    # Notifier les callbacks
                    for callback in self.callbacks:
                        try:
                            callback(tx_hash, tx, function_name)
                        except Exception as e:
                            logger.error(f"Erreur dans le callback pour la transaction {tx_hash}: {e}")
            except Exception as e:
                logger.error(f"Erreur lors du traitement des transactions du mempool: {e}")
                await asyncio.sleep(1)
            
            # Clean up old transactions (plus de 2 minutes)
            current_time = time.time()
            to_remove = []
            for tx_hash, tx_data in self.pending_txs.items():
                if current_time - tx_data['timestamp'] > 120:
                    to_remove.append(tx_hash)
            
            for tx_hash in to_remove:
                del self.pending_txs[tx_hash] 