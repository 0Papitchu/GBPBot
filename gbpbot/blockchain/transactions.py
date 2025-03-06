"""
Module de gestion des transactions pour GBPBot
=====================================================

Ce module fournit des fonctionnalités avancées pour la création, la signature,
l'envoi et le suivi des transactions sur différentes blockchains, avec focus
sur l'optimisation des transactions Solana.
"""

import os
import json
import time
import base64
import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple, Union, Callable
from dataclasses import dataclass, field
from datetime import datetime
import uuid
from collections import OrderedDict

# Configurer le logging
logger = logging.getLogger(__name__)

# Importer les modules GBPBot
try:
    from gbpbot.core import config
    from gbpbot.core import rpc
    from gbpbot.core import wallet
    from gbpbot.blockchain import solana
    from gbpbot import resource_monitor
except ImportError as e:
    logger.warning(f"ImportError: {e}")
    logger.warning("Certaines fonctionnalités peuvent être limitées")
    config = None
    rpc = None
    wallet = None
    solana = None
    resource_monitor = None


@dataclass
class TransactionResult:
    """Résultat d'une transaction"""
    transaction_id: str
    success: bool
    hash: Optional[str] = None
    block_number: Optional[int] = None
    timestamp: float = field(default_factory=time.time)
    fee_paid: Optional[float] = None
    error_message: Optional[str] = None
    confirmations: int = 0
    # Informations spécifiques à la blockchain
    blockchain_data: Dict[str, Any] = field(default_factory=dict)


class TransactionStatus:
    """Statuts possibles pour une transaction"""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    DROPPED = "dropped"
    UNKNOWN = "unknown"


class TransactionPriority:
    """Niveaux de priorité pour les transactions"""
    LOW = "low"            # Économiser les frais
    MEDIUM = "medium"      # Équilibre entre frais et vitesse
    HIGH = "high"          # Vitesse optimale, frais plus élevés
    URGENT = "urgent"      # Priorité maximale, frais très élevés


class TransactionManager:
    """
    Gestionnaire de transactions pour différentes blockchains.
    Permet l'envoi optimisé de transactions avec monitoring et résilience.
    """
    
    def __init__(self):
        """Initialise le gestionnaire de transactions"""
        # État interne
        self.pending_transactions = {}
        # Utiliser OrderedDict pour préserver l'ordre chronologique des transactions
        self.transaction_history = OrderedDict()
        self.tx_monitor_task = None
        self.is_running = False
        
        # Callbacks
        self.tx_status_callbacks = {}
        
        # Chargement de la configuration
        self.default_config = {
            "timeout": 60,                 # Timeout en secondes
            "max_retries": 3,              # Nombre maximal de tentatives
            "retry_delay": 2.0,            # Délai entre les tentatives
            "confirmation_blocks": {
                "solana": 1,              # Confirmation sur Solana
                "avalanche": 2,           # Confirmation sur Avalanche
                "ethereum": 3             # Confirmation sur Ethereum
            },
            "gas_price_multiplier": {
                "low": 0.9,               # 90% du prix de marché
                "medium": 1.1,            # 110% du prix de marché
                "high": 1.3,              # 130% du prix de marché
                "urgent": 1.5             # 150% du prix de marché
            },
            "max_history_size": 10000     # Taille maximale de l'historique
        }
        
        # Configuration actuelle
        self.config = self.default_config.copy()
        
        # Charger la configuration
        self._load_config()
        
        # Enregistrer un callback pour les notifications d'optimisation des ressources
        if resource_monitor:
            resource_monitor.subscribe("optimization_applied", self._handle_resource_optimization)
        
    def _load_config(self) -> None:
        """Charge la configuration depuis le gestionnaire de configuration"""
        if not config:
            return
            
        try:
            # Charger les paramètres de transactions
            tx_config = config.get("blockchain.transactions", {})
            
            # Fusionner avec la configuration par défaut
            for key, value in tx_config.items():
                if isinstance(value, dict) and key in self.default_config and isinstance(self.default_config[key], dict):
                    # Pour les dictionnaires, fusionner les valeurs
                    self.default_config[key].update(value)
                else:
                    # Pour les valeurs simples, remplacer
                    self.default_config[key] = value
                    
        except Exception as e:
            logger.error(f"Erreur lors du chargement de la configuration: {e}")
            
    async def start(self) -> None:
        """Démarre le gestionnaire de transactions"""
        if self.is_running:
            logger.warning("Le gestionnaire de transactions est déjà démarré")
            return
            
        self.is_running = True
        self.tx_monitor_task = asyncio.create_task(self._monitor_transactions())
        
        logger.info("Gestionnaire de transactions démarré")
        
    async def stop(self) -> None:
        """Arrête le gestionnaire de transactions"""
        if not self.is_running:
            logger.warning("Le gestionnaire de transactions n'est pas démarré")
            return
            
        self.is_running = False
        if self.tx_monitor_task:
            self.tx_monitor_task.cancel()
            try:
                await self.tx_monitor_task
            except asyncio.CancelledError:
                pass
                
        logger.info("Gestionnaire de transactions arrêté")
        
    async def _monitor_transactions(self) -> None:
        """Boucle de surveillance des transactions en attente"""
        while self.is_running:
            try:
                # Créer une liste des tx à vérifier pour éviter les erreurs de modification pendant l'itération
                transactions = list(self.pending_transactions.items())
                
                for tx_id, tx_info in transactions:
                    # Récupérer les détails
                    blockchain_type = tx_info.get("blockchain")
                    hash = tx_info.get("hash")
                    creation_time = tx_info.get("creation_time", time.time())
                    status = tx_info.get("status", TransactionStatus.PENDING)
                    
                    # Ignorer les transactions déjà confirmées ou échouées
                    if status not in [TransactionStatus.PENDING, TransactionStatus.UNKNOWN]:
                        continue
                        
                    # Vérifier si la transaction a expiré
                    timeout = self.default_config.get("timeout", 60)
                    if time.time() - creation_time > timeout:
                        await self._update_transaction_status(
                            tx_id, TransactionStatus.TIMEOUT,
                            "La transaction a expiré"
                        )
                        continue
                        
                    # Vérifier le statut en fonction du type de blockchain
                    if blockchain_type == "solana":
                        await self._check_solana_transaction(tx_id, hash)
                    # Ajouter d'autres blockchains ici au besoin
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Erreur lors de la surveillance des transactions: {e}")
                
            # Attendre avant la prochaine vérification
            await asyncio.sleep(5.0)  # Vérifier toutes les 5 secondes
            
    async def _check_solana_transaction(self, tx_id: str, signature: str) -> None:
        """
        Vérifie le statut d'une transaction Solana
        
        Args:
            tx_id: Identifiant interne de la transaction
            signature: Signature de la transaction Solana
        """
        if not rpc:
            logger.error("Module RPC non disponible")
            return
            
        try:
            # Récupérer les informations sur la transaction
            tx_info = await rpc.rpc_manager.call_rpc("getTransaction", [
                signature,
                {"encoding": "jsonParsed"}
            ], chain="solana")
            
            if not tx_info:
                # Transaction pas encore incluse dans un bloc
                return
                
            # Vérifier si la transaction a réussi
            meta = tx_info.get("meta", {})
            error = meta.get("err")
            
            if error is not None:
                # Transaction échouée
                await self._update_transaction_status(
                    tx_id, TransactionStatus.FAILED,
                    f"Erreur Solana: {error}"
                )
                return
                
            # Récupérer les confirmations
            confirmations = tx_info.get("confirmations", 0)
            required_confirmations = self.default_config.get("confirmation_blocks", {}).get("solana", 1)
            
            # Mettre à jour le nombre de confirmations
            self.pending_transactions[tx_id]["confirmations"] = confirmations
            
            # Vérifier si la transaction est considérée comme confirmée
            if confirmations >= required_confirmations:
                # Transaction confirmée
                slot = tx_info.get("slot", 0)
                fee = meta.get("fee", 0)
                block_time = tx_info.get("blockTime", time.time())
                
                # Créer un objet résultat
                result = TransactionResult(
                    transaction_id=tx_id,
                    success=True,
                    hash=signature,
                    block_number=slot,
                    timestamp=block_time,
                    fee_paid=float(fee) / 1e9,  # Convertir lamports en SOL
                    confirmations=confirmations,
                    blockchain_data={
                        "slot": slot,
                        "confirmations": confirmations,
                        "block_time": block_time
                    }
                )
                
                # Mettre à jour le statut
                await self._update_transaction_status(
                    tx_id, TransactionStatus.CONFIRMED,
                    result=result
                )
                
        except Exception as e:
            logger.error(f"Erreur lors de la vérification de la transaction Solana {signature}: {e}")
            
    async def _update_transaction_status(self, tx_id: str, status: str, error_message: Optional[str] = None, result: Optional[TransactionResult] = None) -> None:
        """
        Met à jour le statut d'une transaction et notifie les callbacks
        
        Args:
            tx_id: Identifiant de la transaction
            status: Nouveau statut
            error_message: Message d'erreur optionnel
            result: Résultat de la transaction
        """
        # Mettre à jour la transaction
        if tx_id in self.pending_transactions:
            self.pending_transactions[tx_id]["status"] = status
            self.pending_transactions[tx_id]["last_update"] = time.time()
            
            if error_message:
                self.pending_transactions[tx_id]["error"] = error_message
                
            if status != TransactionStatus.PENDING:
                # Déplacer de pending vers history
                tx_info = self.pending_transactions.pop(tx_id)
                self.transaction_history[tx_id] = tx_info
                
                # Limiter la taille de l'historique
                self._trim_transaction_history()
                
        # Notifier les callbacks enregistrés
        if tx_id in self.tx_status_callbacks:
            for callback in self.tx_status_callbacks[tx_id]:
                try:
                    if result:
                        callback(status, result)
                    else:
                        # Créer un résultat minimal
                        minimal_result = TransactionResult(
                            transaction_id=tx_id,
                            success=(status == TransactionStatus.CONFIRMED),
                            hash=self.pending_transactions.get(tx_id, {}).get("hash"),
                            error_message=error_message
                        )
                        callback(status, minimal_result)
                except Exception as e:
                    logger.error(f"Erreur lors de l'appel d'un callback de transaction: {e}")
                    
    def _trim_transaction_history(self) -> None:
        """Limite la taille de l'historique des transactions"""
        try:
            max_history_size = self.config.get("max_history_size", 10000)
            
            # Vérifier si la taille actuelle dépasse la limite
            current_size = len(self.transaction_history)
            if current_size <= max_history_size:
                return
                
            # Calculer le nombre de transactions à supprimer
            to_remove = current_size - max_history_size
            if to_remove <= 0:
                return
                
            # Supprimer les transactions les plus anciennes (qui sont au début de l'OrderedDict)
            for _ in range(to_remove):
                if not self.transaction_history:
                    break
                self.transaction_history.popitem(last=False)
                
            logger.debug(f"Transaction history trimmed to {max_history_size} items (removed {to_remove} old items)")
            
        except Exception as e:
            logger.error(f"Erreur lors de la limitation de l'historique des transactions: {str(e)}")
            
    async def send_transaction(
        self,
        blockchain: str,
        tx_data: Dict[str, Any],
        priority: str = TransactionPriority.MEDIUM,
        wait_for_confirmation: bool = False,
        status_callback: Optional[Callable] = None
    ) -> Tuple[str, Optional[str]]:
        """
        Envoie une transaction sur la blockchain
        
        Args:
            blockchain: Type de blockchain (ex: "solana")
            tx_data: Données de la transaction (spécifique à chaque blockchain)
            priority: Priorité de la transaction
            wait_for_confirmation: Attendre la confirmation de la transaction
            status_callback: Fonction de callback pour les mises à jour de statut
        
        Returns:
            Tuple[str, Optional[str]]: (ID de la transaction, hash de la transaction)
        """
        # Générer un ID unique pour cette transaction
        tx_id = str(uuid.uuid4())
        
        # Enregistrer le callback si fourni
        if status_callback:
            if tx_id not in self.tx_status_callbacks:
                self.tx_status_callbacks[tx_id] = []
            self.tx_status_callbacks[tx_id].append(status_callback)
            
        try:
            # Ajouter à la liste des transactions en attente
            self.pending_transactions[tx_id] = {
                "id": tx_id,
                "blockchain": blockchain,
                "status": TransactionStatus.PENDING,
                "priority": priority,
                "creation_time": time.time(),
                "last_update": time.time(),
                "confirmations": 0
            }
            
            # Envoyer la transaction en fonction du type de blockchain
            if blockchain == "solana":
                tx_hash = await self._send_solana_transaction(tx_id, tx_data, priority)
            # Ajouter d'autres blockchains au besoin
            else:
                raise ValueError(f"Blockchain non supportée: {blockchain}")
                
            # Mettre à jour le hash
            self.pending_transactions[tx_id]["hash"] = tx_hash
            
            # Si on doit attendre la confirmation
            if wait_for_confirmation:
                required_confirmations = self.default_config.get("confirmation_blocks", {}).get(blockchain, 1)
                timeout = self.default_config.get("timeout", 60)
                
                # Attendre la confirmation
                start_time = time.time()
                while time.time() - start_time < timeout:
                    # Vérifier si la transaction n'est plus en attente
                    if tx_id not in self.pending_transactions:
                        # Récupérer depuis l'historique
                        tx_info = self.transaction_history.get(tx_id, {})
                        status = tx_info.get("status", TransactionStatus.UNKNOWN)
                        
                        if status == TransactionStatus.CONFIRMED:
                            return tx_id, tx_hash
                        elif status in [TransactionStatus.FAILED, TransactionStatus.TIMEOUT, TransactionStatus.DROPPED]:
                            error = tx_info.get("error", "Transaction échouée")
                            raise Exception(f"Transaction {tx_id} échouée: {error}")
                            
                    # Sinon, attendre un peu
                    await asyncio.sleep(1.0)
                    
                # Si on arrive ici, c'est un timeout
                raise Exception(f"Timeout lors de l'attente de la confirmation pour la transaction {tx_id}")
                
            return tx_id, tx_hash
            
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de la transaction: {e}")
            
            # Mettre à jour le statut
            await self._update_transaction_status(
                tx_id, TransactionStatus.FAILED,
                str(e)
            )
            
            raise
            
    async def _send_solana_transaction(self, tx_id: str, tx_data: Dict[str, Any], priority: str) -> str:
        """
        Envoie une transaction Solana
        
        Args:
            tx_id: Identifiant interne de la transaction
            tx_data: Données de la transaction
            priority: Priorité de la transaction
            
        Returns:
            Signature de la transaction
        """
        if not rpc:
            raise Exception("Module RPC non disponible")
            
        # Vérifier les données minimales requises
        if "serialized_transaction" not in tx_data:
            raise ValueError("Transaction Solana non valide: serialized_transaction manquant")
            
        # Récupérer la transaction sérialisée
        serialized_tx = tx_data["serialized_transaction"]
        
        # Ajouter les options d'envoi
        options = {
            "skipPreflight": tx_data.get("skip_preflight", False),
            "preflightCommitment": tx_data.get("commitment", "confirmed"),
            "maxRetries": self.default_config.get("max_retries", 3)
        }
        
        # Ajouter un fee de priorité si nécessaire
        if priority != TransactionPriority.LOW:
            # Récupérer le fee de priorité selon le niveau
            priority_fee = self.default_config.get("priority_fee", {}).get(priority, 0)
            
            if priority_fee > 0:
                options["computeUnitPrice"] = priority_fee
                
        # Envoyer la transaction
        try:
            response = await rpc.rpc_manager.call_rpc("sendTransaction", [
                serialized_tx,
                options
            ], chain="solana")
            
            if not response:
                raise Exception("Réponse invalide du nœud Solana")
                
            # Récupérer la signature
            # La réponse de sendTransaction est directement la signature pour Solana
            signature = response if isinstance(response, str) else response.get("result", "")
            
            if not signature or not isinstance(signature, str):
                raise Exception(f"Signature invalide reçue: {response}")
            
            logger.info(f"Transaction Solana envoyée: {signature}")
            
            return signature
            
        except Exception as e:
            error_message = f"Erreur lors de l'envoi de la transaction Solana: {str(e)}"
            logger.error(error_message)
            
            raise Exception(error_message)
            
    async def get_transaction_status(self, tx_id: str) -> Tuple[str, Dict[str, Any]]:
        """
        Récupère le statut actuel d'une transaction
        
        Args:
            tx_id: Identifiant de la transaction
            
        Returns:
            Tuple[str, Dict[str, Any]]: (statut, informations détaillées)
        """
        # Vérifier d'abord dans les transactions en attente
        if tx_id in self.pending_transactions:
            status = self.pending_transactions[tx_id].get("status", TransactionStatus.PENDING)
            return status, self.pending_transactions[tx_id]
            
        # Sinon, vérifier dans l'historique
        if tx_id in self.transaction_history:
            status = self.transaction_history[tx_id].get("status", TransactionStatus.UNKNOWN)
            return status, self.transaction_history[tx_id]
            
        # Transaction non trouvée
        return TransactionStatus.UNKNOWN, {"error": "Transaction non trouvée"}
    
    async def get_transaction_history(self, limit: int = 50, offset: int = 0, blockchain: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Récupère l'historique des transactions
        
        Args:
            limit: Nombre maximum de transactions à récupérer
            offset: Décalage dans la liste (pour pagination)
            blockchain: Filtrer par type de blockchain
            
        Returns:
            Liste des transactions
        """
        # Filtrer par blockchain si spécifiée
        if blockchain:
            filtered_history = {
                tx_id: tx_info for tx_id, tx_info in self.transaction_history.items()
                if tx_info.get("blockchain") == blockchain
            }
        else:
            filtered_history = self.transaction_history
            
        # Trier par timestamp décroissant (transaction la plus récente en premier)
        sorted_tx = sorted(
            filtered_history.values(),
            key=lambda tx: tx.get("last_update", 0),
            reverse=True
        )
        
        # Appliquer pagination
        paginated_tx = sorted_tx[offset:offset + limit]
        
        return paginated_tx
        
    async def build_solana_transaction(
        self,
        instructions: List[Dict[str, Any]],
        signers: List[Dict[str, Any]],
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Construit une transaction Solana prête à être signée et envoyée
        
        Args:
            instructions: Liste des instructions à inclure
            signers: Liste des signataires
            options: Options supplémentaires
            
        Returns:
            Transaction sérialisée et autres informations
        """
        # Vérifier que les dépendances sont disponibles
        if not wallet or not hasattr(wallet, 'wallet_manager'):
            raise Exception("Module wallet non disponible")
            
        # Options par défaut
        default_options = {
            "commitment": "confirmed",
            "skip_preflight": False,
            "compute_budget": 200000,  # Unités de calcul
            "add_recent_blockhash": True
        }
        
        # Fusionner avec les options fournies
        if options:
            default_options.update(options)
            
        # Cette fonction est un placeholder
        # Une implémentation complète nécessiterait l'accès à la bibliothèque Solana
        # pour construire et sérialiser la transaction
        
        raise NotImplementedError("Implémentation complète requise - nécessite intégration avec solana-py")
        
    def register_status_callback(self, tx_id: str, callback: Callable) -> None:
        """
        Enregistre un callback pour les mises à jour de statut d'une transaction
        
        Args:
            tx_id: Identifiant de la transaction
            callback: Fonction de callback
        """
        if tx_id not in self.tx_status_callbacks:
            self.tx_status_callbacks[tx_id] = []
        self.tx_status_callbacks[tx_id].append(callback)
        
    def unregister_status_callback(self, tx_id: str, callback: Callable) -> None:
        """
        Supprime un callback pour les mises à jour de statut d'une transaction
        
        Args:
            tx_id: Identifiant de la transaction
            callback: Fonction de callback
        """
        if tx_id in self.tx_status_callbacks:
            if callback in self.tx_status_callbacks[tx_id]:
                self.tx_status_callbacks[tx_id].remove(callback)
                
            if not self.tx_status_callbacks[tx_id]:
                del self.tx_status_callbacks[tx_id]

    def _handle_resource_optimization(self, state: Dict[str, Any]) -> None:
        """
        Gère les notifications d'optimisation des ressources
        
        Args:
            state: État des ressources et optimisations appliquées
        """
        try:
            # Vérifier que le module resource_monitor est disponible
            if resource_monitor is None:
                return
                
            # Récupérer les limites d'historique des transactions
            if state.get("type") in ["system", "dynamic", "manual"]:
                # Récupérer les valeurs d'optimisation
                optimization_values = resource_monitor.get_optimization_values()
                tx_history_limit = optimization_values.get("tx_history_limit")
                
                if tx_history_limit and tx_history_limit != self.config.get("max_history_size"):
                    # Mettre à jour la configuration
                    self.config["max_history_size"] = tx_history_limit
                    logger.info(f"Limite d'historique des transactions mise à jour: {tx_history_limit}")
                    
                    # Appliquer la nouvelle limite
                    self._trim_transaction_history()
        except Exception as e:
            logger.error(f"Erreur lors du traitement de l'optimisation des ressources: {str(e)}")


# Instance globale du gestionnaire de transactions
transaction_manager = TransactionManager()

# Fonctions d'accès simplifiées
async def start() -> None:
    """Démarre le gestionnaire de transactions"""
    await transaction_manager.start()

async def stop() -> None:
    """Arrête le gestionnaire de transactions"""
    await transaction_manager.stop()

async def send_transaction(
    blockchain: str,
    tx_data: Dict[str, Any],
    priority: str = TransactionPriority.MEDIUM,
    wait_for_confirmation: bool = False,
    status_callback: Optional[Callable] = None
) -> Tuple[str, Optional[str]]:
    """Envoie une transaction sur la blockchain"""
    return await transaction_manager.send_transaction(
        blockchain, tx_data, priority, wait_for_confirmation, status_callback
    )

async def get_transaction_status(tx_id: str) -> Tuple[str, Dict[str, Any]]:
    """Récupère le statut actuel d'une transaction"""
    return await transaction_manager.get_transaction_status(tx_id)

async def get_transaction_history(limit: int = 50, offset: int = 0, blockchain: Optional[str] = None) -> List[Dict[str, Any]]:
    """Récupère l'historique des transactions"""
    return await transaction_manager.get_transaction_history(limit, offset, blockchain) 