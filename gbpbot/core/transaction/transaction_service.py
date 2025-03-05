#!/usr/bin/env python3
"""
Service d'intégration pour le gestionnaire de transactions.
"""

import asyncio
from typing import Dict, List, Optional, Any, Tuple, Callable
from decimal import Decimal
from loguru import logger
from web3 import Web3
from web3.types import TxParams, TxReceipt, Wei, HexBytes

from gbpbot.config.config_manager import ConfigManager
from gbpbot.core.monitoring.bot_monitor import BotMonitor
from gbpbot.core.transaction.transaction_manager import get_transaction_manager, TransactionManager

class TransactionService:
    """Service d'intégration pour le gestionnaire de transactions."""
    
    def __init__(self, monitor: BotMonitor):
        """
        Initialise le service de transactions.
        
        Args:
            monitor: Moniteur du bot pour les métriques et alertes
        """
        logger.info("Initialisation du service de transactions")
        self.config = ConfigManager().get_config()
        self.monitor = monitor
        self.tx_manager = get_transaction_manager(monitor)
        
        # Configuration
        self.retry_config = self.config.get('transaction', {}).get('retry', {})
        self.retry_enabled = self.retry_config.get('enabled', True)
        self.max_retry_attempts = self.retry_config.get('max_attempts', 3)
        self.retry_delay = self.retry_config.get('delay', 5)
        self.retry_backoff_factor = self.retry_config.get('backoff_factor', 2)
        self.max_retry_delay = self.retry_config.get('max_delay', 60)
        
        # Callbacks
        self.on_transaction_sent = None
        self.on_transaction_confirmed = None
        self.on_transaction_failed = None
        
        logger.info(f"Service de transactions initialisé (retry: {'activé' if self.retry_enabled else 'désactivé'})")
    
    async def start(self) -> None:
        """Démarre le service de transactions."""
        logger.info("Démarrage du service de transactions")
        await self.tx_manager.start()
        logger.info("Service de transactions démarré")
    
    async def stop(self) -> None:
        """Arrête le service de transactions."""
        logger.info("Arrêt du service de transactions")
        await self.tx_manager.stop()
        logger.info("Service de transactions arrêté")
    
    async def send_transaction(self, tx_params: TxParams, wait_for_receipt: bool = True, 
                              retry_on_failure: Optional[bool] = None) -> Tuple[HexBytes, Optional[TxReceipt]]:
        """
        Envoie une transaction avec gestion des erreurs et retries.
        
        Args:
            tx_params: Paramètres de la transaction
            wait_for_receipt: Attendre le reçu de la transaction
            retry_on_failure: Réessayer en cas d'échec (None pour utiliser la valeur par défaut)
            
        Returns:
            Tuple[HexBytes, Optional[TxReceipt]]: (hash de la transaction, reçu de la transaction)
        """
        should_retry = self.retry_enabled if retry_on_failure is None else retry_on_failure
        attempt = 0
        last_error = None
        
        while attempt <= (self.max_retry_attempts if should_retry else 0):
            try:
                # Incrémenter le compteur de tentatives
                attempt += 1
                
                # Envoyer la transaction
                logger.info(f"Envoi de la transaction (tentative {attempt}/{self.max_retry_attempts + 1 if should_retry else 1})")
                tx_hash, receipt = await self.tx_manager.send_transaction(tx_params, wait_for_receipt)
                
                # Appeler le callback si défini
                if self.on_transaction_sent:
                    await self._call_callback(self.on_transaction_sent, tx_hash, receipt)
                
                # Appeler le callback de confirmation si défini et si la transaction est confirmée
                if receipt and receipt.status == 1 and self.on_transaction_confirmed:
                    await self._call_callback(self.on_transaction_confirmed, tx_hash, receipt)
                
                # Appeler le callback d'échec si défini et si la transaction a échoué
                if receipt and receipt.status == 0 and self.on_transaction_failed:
                    await self._call_callback(self.on_transaction_failed, tx_hash, receipt)
                
                return tx_hash, receipt
            except Exception as e:
                last_error = e
                logger.warning(f"Erreur lors de l'envoi de la transaction (tentative {attempt}): {str(e)}")
                
                # Si c'est la dernière tentative ou si on ne doit pas réessayer, lever l'exception
                if attempt > self.max_retry_attempts or not should_retry:
                    logger.error(f"Échec de l'envoi de la transaction après {attempt} tentative(s): {str(e)}")
                    raise
                
                # Calculer le délai avant la prochaine tentative
                delay = min(self.retry_delay * (self.retry_backoff_factor ** (attempt - 1)), self.max_retry_delay)
                logger.info(f"Nouvelle tentative dans {delay} secondes")
                await asyncio.sleep(delay)
        
        # Si on arrive ici, c'est qu'on a épuisé toutes les tentatives
        logger.error(f"Échec de l'envoi de la transaction après {self.max_retry_attempts} tentatives")
        raise last_error
    
    async def wait_for_optimal_gas(self, max_wait_time: Optional[int] = None) -> Wei:
        """
        Attend que le prix du gas soit optimal.
        
        Args:
            max_wait_time: Temps d'attente maximum en secondes
            
        Returns:
            Wei: Prix du gas optimal
        """
        from gbpbot.core.gas.gas_optimizer import gas_optimizer
        return await gas_optimizer.wait_for_optimal_gas(max_wait_time)
    
    async def estimate_transaction_cost(self, gas_limit: int) -> Tuple[Wei, str]:
        """
        Estime le coût d'une transaction.
        
        Args:
            gas_limit: Limite de gas
            
        Returns:
            Tuple[Wei, str]: (coût en wei, coût formaté)
        """
        from gbpbot.core.gas.gas_optimizer import gas_optimizer
        return await gas_optimizer.estimate_transaction_cost(gas_limit)
    
    async def get_transaction_status(self, tx_hash: str) -> Dict[str, Any]:
        """
        Récupère le statut d'une transaction.
        
        Args:
            tx_hash: Hash de la transaction
            
        Returns:
            Dict[str, Any]: Statut de la transaction
        """
        return await self.tx_manager.get_transaction_status(tx_hash)
    
    async def get_transaction_by_id(self, tx_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère une transaction par son ID.
        
        Args:
            tx_id: ID de la transaction
            
        Returns:
            Optional[Dict[str, Any]]: Transaction ou None si non trouvée
        """
        return await self.tx_manager.get_transaction_by_id(tx_id)
    
    async def get_all_transactions(self, status: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        Récupère toutes les transactions.
        
        Args:
            status: Filtrer par statut (None pour toutes)
            
        Returns:
            Dict[str, Dict[str, Any]]: Transactions
        """
        return await self.tx_manager.get_all_transactions(status)
    
    async def get_pending_transactions(self) -> Dict[str, Dict[str, Any]]:
        """
        Récupère les transactions en attente.
        
        Returns:
            Dict[str, Dict[str, Any]]: Transactions en attente
        """
        return await self.tx_manager.get_pending_transactions()
    
    async def cancel_transaction(self, tx_hash: str) -> Optional[HexBytes]:
        """
        Annule une transaction en attente.
        
        Args:
            tx_hash: Hash de la transaction
            
        Returns:
            Optional[HexBytes]: Hash de la nouvelle transaction ou None si échec
        """
        return await self.tx_manager.cancel_transaction(tx_hash)
    
    async def speed_up_transaction(self, tx_hash: str) -> Optional[HexBytes]:
        """
        Accélère une transaction en attente.
        
        Args:
            tx_hash: Hash de la transaction
            
        Returns:
            Optional[HexBytes]: Hash de la nouvelle transaction ou None si échec
        """
        return await self.tx_manager.speed_up_transaction(tx_hash)
    
    def set_transaction_sent_callback(self, callback: Callable[[HexBytes, Optional[TxReceipt]], None]) -> None:
        """
        Définit le callback à appeler lorsqu'une transaction est envoyée.
        
        Args:
            callback: Fonction à appeler
        """
        self.on_transaction_sent = callback
    
    def set_transaction_confirmed_callback(self, callback: Callable[[HexBytes, TxReceipt], None]) -> None:
        """
        Définit le callback à appeler lorsqu'une transaction est confirmée.
        
        Args:
            callback: Fonction à appeler
        """
        self.on_transaction_confirmed = callback
    
    def set_transaction_failed_callback(self, callback: Callable[[HexBytes, TxReceipt], None]) -> None:
        """
        Définit le callback à appeler lorsqu'une transaction échoue.
        
        Args:
            callback: Fonction à appeler
        """
        self.on_transaction_failed = callback
    
    async def _call_callback(self, callback: Callable, tx_hash: HexBytes, receipt: Optional[TxReceipt]) -> None:
        """
        Appelle un callback de manière sécurisée.
        
        Args:
            callback: Fonction à appeler
            tx_hash: Hash de la transaction
            receipt: Reçu de la transaction
        """
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(tx_hash, receipt)
            else:
                callback(tx_hash, receipt)
        except Exception as e:
            logger.error(f"Erreur lors de l'appel du callback: {str(e)}")

# Instance singleton
transaction_service = None

def get_transaction_service(monitor: BotMonitor) -> TransactionService:
    """
    Récupère l'instance du service de transactions.
    
    Args:
        monitor: Moniteur du bot
        
    Returns:
        TransactionService: Instance du service de transactions
    """
    global transaction_service
    if transaction_service is None:
        transaction_service = TransactionService(monitor)
    return transaction_service 