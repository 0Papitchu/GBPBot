#!/usr/bin/env python3
"""
Module de gestion des transactions blockchain.
"""

import asyncio
import time
import uuid
from typing import Dict, List, Optional, Any, Tuple, Callable
from decimal import Decimal
from loguru import logger
from web3 import Web3
from web3.types import TxParams, TxReceipt, Wei, HexBytes

from gbpbot.config.config_manager import ConfigManager
from gbpbot.core.rpc.rpc_manager import RPCManager
from gbpbot.core.gas.gas_optimizer import gas_optimizer
from gbpbot.core.monitoring.bot_monitor import BotMonitor

class TransactionManager:
    """Gestionnaire de transactions blockchain."""
    
    def __init__(self, monitor: BotMonitor):
        """
        Initialise le gestionnaire de transactions.
        
        Args:
            monitor: Moniteur du bot pour les métriques et alertes
        """
        logger.info("Initialisation du gestionnaire de transactions")
        self.config = ConfigManager().get_config()
        self.rpc_manager = RPCManager()
        self.monitor = monitor
        
        # Configuration des transactions
        self.tx_config = self.config.get('transaction', {})
        self.tx_timeout = self.tx_config.get('timeout', 180)
        self.max_pending_txs = self.tx_config.get('max_pending_transactions', 5)
        self.confirmation_blocks = self.config.get('security', {}).get('min_block_confirmations', 1)
        self.max_confirmation_attempts = self.config.get('security', {}).get('max_confirmation_attempts', 5)
        
        # Configuration de sécurité
        self.security_config = self.config.get('security', {})
        self.max_slippage = Decimal(str(self.security_config.get('max_slippage', 1.0)))
        self.max_gas_price = Wei(int(Decimal(str(self.security_config.get('max_gas_price', 100))) * Decimal('1e9')))
        
        # État des transactions
        self.pending_transactions = {}
        self.transaction_history = {}
        self.nonce_lock = asyncio.Lock()
        self.current_nonce = None
        
        # Tâche de surveillance des transactions en attente
        self.pending_tx_task = None
        self.running = False
        
        logger.info(f"Gestionnaire de transactions initialisé (timeout: {self.tx_timeout}s, confirmations: {self.confirmation_blocks})")
    
    async def start(self) -> None:
        """Démarre le gestionnaire de transactions."""
        if self.running:
            logger.warning("Le gestionnaire de transactions est déjà en cours d'exécution")
            return
        
        logger.info("Démarrage du gestionnaire de transactions")
        self.running = True
        
        # Démarrer la tâche de surveillance des transactions en attente
        self.pending_tx_task = asyncio.create_task(self._monitor_pending_transactions())
        
        # Initialiser le nonce actuel
        await self._initialize_nonce()
        
        logger.info("Gestionnaire de transactions démarré")
    
    async def stop(self) -> None:
        """Arrête le gestionnaire de transactions."""
        if not self.running:
            logger.warning("Le gestionnaire de transactions n'est pas en cours d'exécution")
            return
        
        logger.info("Arrêt du gestionnaire de transactions")
        self.running = False
        
        # Annuler la tâche de surveillance des transactions en attente
        if self.pending_tx_task:
            self.pending_tx_task.cancel()
            try:
                await self.pending_tx_task
            except asyncio.CancelledError:
                pass
            self.pending_tx_task = None
        
        logger.info("Gestionnaire de transactions arrêté")
    
    async def send_transaction(self, tx_params: TxParams, wait_for_receipt: bool = True) -> Tuple[HexBytes, Optional[TxReceipt]]:
        """
        Envoie une transaction avec optimisation des frais de gas.
        
        Args:
            tx_params: Paramètres de la transaction
            wait_for_receipt: Attendre le reçu de la transaction
            
        Returns:
            Tuple[HexBytes, Optional[TxReceipt]]: (hash de la transaction, reçu de la transaction)
        """
        try:
            # Vérifier le nombre de transactions en attente
            if len(self.pending_transactions) >= self.max_pending_txs:
                logger.warning(f"Nombre maximum de transactions en attente atteint ({self.max_pending_txs})")
                raise ValueError(f"Nombre maximum de transactions en attente atteint ({self.max_pending_txs})")
            
            # Optimiser les paramètres de la transaction
            optimized_tx = await gas_optimizer.optimize_transaction(tx_params)
            
            # Vérifier le prix du gas
            if 'gasPrice' in optimized_tx and optimized_tx['gasPrice'] > self.max_gas_price:
                logger.warning(f"Prix du gas trop élevé: {Web3.from_wei(optimized_tx['gasPrice'], 'gwei')} gwei (max: {Web3.from_wei(self.max_gas_price, 'gwei')} gwei)")
                raise ValueError(f"Prix du gas trop élevé: {Web3.from_wei(optimized_tx['gasPrice'], 'gwei')} gwei")
            elif 'maxFeePerGas' in optimized_tx and optimized_tx['maxFeePerGas'] > self.max_gas_price:
                logger.warning(f"Prix du gas (maxFeePerGas) trop élevé: {Web3.from_wei(optimized_tx['maxFeePerGas'], 'gwei')} gwei (max: {Web3.from_wei(self.max_gas_price, 'gwei')} gwei)")
                raise ValueError(f"Prix du gas (maxFeePerGas) trop élevé: {Web3.from_wei(optimized_tx['maxFeePerGas'], 'gwei')} gwei")
            
            # Ajouter le nonce si non spécifié
            if 'nonce' not in optimized_tx:
                async with self.nonce_lock:
                    optimized_tx['nonce'] = self.current_nonce
                    self.current_nonce += 1
            
            # Récupérer le web3
            web3 = await self.rpc_manager.get_web3()
            
            # Estimer le coût de la transaction
            gas_limit = optimized_tx.get('gas', 0)
            if gas_limit == 0:
                # Estimer la limite de gas si non spécifiée
                gas_limit = await web3.eth.estimate_gas(optimized_tx)
                optimized_tx['gas'] = gas_limit
            
            cost_wei, cost_formatted = await gas_optimizer.estimate_transaction_cost(gas_limit)
            
            # Envoyer la transaction
            logger.info(f"Envoi de la transaction (coût estimé: {cost_formatted})")
            tx_hash = await web3.eth.send_transaction(optimized_tx)
            
            # Créer un ID unique pour la transaction
            tx_id = str(uuid.uuid4())
            
            # Enregistrer la transaction dans les transactions en attente
            self.pending_transactions[tx_hash.hex()] = {
                'id': tx_id,
                'hash': tx_hash.hex(),
                'params': optimized_tx,
                'timestamp': time.time(),
                'status': 'pending',
                'cost_wei': cost_wei,
                'cost_formatted': cost_formatted
            }
            
            # Enregistrer la transaction dans l'historique
            self.transaction_history[tx_id] = {
                'id': tx_id,
                'hash': tx_hash.hex(),
                'params': optimized_tx,
                'timestamp': time.time(),
                'status': 'pending',
                'cost_wei': cost_wei,
                'cost_formatted': cost_formatted
            }
            
            # Mettre à jour les métriques
            self.monitor.increment_counter('transactions_sent')
            self.monitor.set_gauge('pending_transactions', len(self.pending_transactions))
            
            logger.info(f"Transaction envoyée: {tx_hash.hex()} (ID: {tx_id})")
            
            # Attendre le reçu de la transaction si demandé
            receipt = None
            if wait_for_receipt:
                receipt = await self.wait_for_transaction_receipt(tx_hash)
            
            return tx_hash, receipt
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de la transaction: {str(e)}")
            self.monitor.increment_counter('transaction_errors')
            raise
    
    async def wait_for_transaction_receipt(self, tx_hash: HexBytes, timeout: Optional[int] = None) -> TxReceipt:
        """
        Attend le reçu d'une transaction.
        
        Args:
            tx_hash: Hash de la transaction
            timeout: Timeout en secondes (None pour utiliser la valeur par défaut)
            
        Returns:
            TxReceipt: Reçu de la transaction
        """
        try:
            tx_timeout = timeout or self.tx_timeout
            web3 = await self.rpc_manager.get_web3()
            
            logger.info(f"Attente du reçu de la transaction {tx_hash.hex()} (timeout: {tx_timeout}s)")
            
            # Attendre le reçu de la transaction
            start_time = time.time()
            while time.time() - start_time < tx_timeout:
                try:
                    receipt = await web3.eth.get_transaction_receipt(tx_hash)
                    if receipt is not None:
                        # Vérifier si la transaction est confirmée
                        confirmations = 0
                        if receipt.blockNumber is not None:
                            current_block = await web3.eth.block_number
                            confirmations = current_block - receipt.blockNumber
                        
                        # Mettre à jour le statut de la transaction
                        if tx_hash.hex() in self.pending_transactions:
                            self.pending_transactions[tx_hash.hex()]['status'] = 'confirmed' if receipt.status == 1 else 'failed'
                            self.pending_transactions[tx_hash.hex()]['receipt'] = receipt
                            self.pending_transactions[tx_hash.hex()]['confirmations'] = confirmations
                        
                        # Mettre à jour l'historique
                        tx_id = self.pending_transactions[tx_hash.hex()]['id']
                        self.transaction_history[tx_id]['status'] = 'confirmed' if receipt.status == 1 else 'failed'
                        self.transaction_history[tx_id]['receipt'] = receipt
                        self.transaction_history[tx_id]['confirmations'] = confirmations
                        
                        # Vérifier si la transaction est confirmée
                        if confirmations >= self.confirmation_blocks:
                            logger.info(f"Transaction {tx_hash.hex()} confirmée ({confirmations} confirmations)")
                            
                            # Supprimer la transaction des transactions en attente
                            if tx_hash.hex() in self.pending_transactions:
                                del self.pending_transactions[tx_hash.hex()]
                            
                            # Mettre à jour les métriques
                            self.monitor.set_gauge('pending_transactions', len(self.pending_transactions))
                            if receipt.status == 1:
                                self.monitor.increment_counter('transactions_confirmed')
                            else:
                                self.monitor.increment_counter('transactions_failed')
                            
                            return receipt
                        else:
                            logger.debug(f"Transaction {tx_hash.hex()} en attente de confirmations ({confirmations}/{self.confirmation_blocks})")
                    
                    # Attendre un peu avant de vérifier à nouveau
                    await asyncio.sleep(1)
                except Exception as e:
                    logger.warning(f"Erreur lors de la récupération du reçu de la transaction {tx_hash.hex()}: {str(e)}")
                    await asyncio.sleep(1)
            
            # Si on arrive ici, c'est que le timeout a été atteint
            logger.warning(f"Timeout atteint pour la transaction {tx_hash.hex()}")
            raise TimeoutError(f"Timeout atteint pour la transaction {tx_hash.hex()}")
        except Exception as e:
            logger.error(f"Erreur lors de l'attente du reçu de la transaction {tx_hash.hex()}: {str(e)}")
            self.monitor.increment_counter('transaction_errors')
            raise
    
    async def get_transaction_status(self, tx_hash: str) -> Dict[str, Any]:
        """
        Récupère le statut d'une transaction.
        
        Args:
            tx_hash: Hash de la transaction
            
        Returns:
            Dict[str, Any]: Statut de la transaction
        """
        try:
            # Vérifier si la transaction est dans les transactions en attente
            if tx_hash in self.pending_transactions:
                return self.pending_transactions[tx_hash]
            
            # Sinon, récupérer le statut depuis la blockchain
            web3 = await self.rpc_manager.get_web3()
            tx = await web3.eth.get_transaction(tx_hash)
            
            if tx is None:
                return {'status': 'unknown', 'hash': tx_hash}
            
            status = {}
            status['hash'] = tx_hash
            status['params'] = dict(tx)
            
            # Récupérer le reçu si la transaction est minée
            if tx.blockNumber is not None:
                receipt = await web3.eth.get_transaction_receipt(tx_hash)
                status['status'] = 'confirmed' if receipt.status == 1 else 'failed'
                status['receipt'] = receipt
                
                # Calculer le nombre de confirmations
                current_block = await web3.eth.block_number
                status['confirmations'] = current_block - receipt.blockNumber
            else:
                status['status'] = 'pending'
            
            return status
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du statut de la transaction {tx_hash}: {str(e)}")
            return {'status': 'error', 'hash': tx_hash, 'error': str(e)}
    
    async def get_transaction_by_id(self, tx_id: str) -> Optional[Dict[str, Any]]:
        """
        Récupère une transaction par son ID.
        
        Args:
            tx_id: ID de la transaction
            
        Returns:
            Optional[Dict[str, Any]]: Transaction ou None si non trouvée
        """
        return self.transaction_history.get(tx_id)
    
    async def get_all_transactions(self, status: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        Récupère toutes les transactions.
        
        Args:
            status: Filtrer par statut (None pour toutes)
            
        Returns:
            Dict[str, Dict[str, Any]]: Transactions
        """
        if status is None:
            return self.transaction_history
        
        return {tx_id: tx for tx_id, tx in self.transaction_history.items() if tx.get('status') == status}
    
    async def get_pending_transactions(self) -> Dict[str, Dict[str, Any]]:
        """
        Récupère les transactions en attente.
        
        Returns:
            Dict[str, Dict[str, Any]]: Transactions en attente
        """
        return self.pending_transactions
    
    async def _initialize_nonce(self) -> None:
        """Initialise le nonce actuel."""
        try:
            web3 = await self.rpc_manager.get_web3()
            
            # Récupérer l'adresse du portefeuille
            wallet_config = self.config.get('wallet', {})
            private_key = wallet_config.get('private_key', '')
            
            if not private_key:
                logger.error("Clé privée non configurée")
                raise ValueError("Clé privée non configurée")
            
            # Récupérer l'adresse à partir de la clé privée
            account = web3.eth.account.from_key(private_key)
            address = account.address
            
            # Récupérer le nonce actuel
            nonce = await web3.eth.get_transaction_count(address)
            
            async with self.nonce_lock:
                self.current_nonce = nonce
            
            logger.info(f"Nonce initialisé: {nonce}")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du nonce: {str(e)}")
            raise
    
    async def _monitor_pending_transactions(self) -> None:
        """Surveille les transactions en attente."""
        try:
            while self.running:
                # Attendre un peu avant de vérifier à nouveau
                await asyncio.sleep(5)
                
                # Vérifier les transactions en attente
                pending_txs = list(self.pending_transactions.keys())
                for tx_hash in pending_txs:
                    try:
                        # Vérifier si la transaction est toujours en attente
                        tx_data = self.pending_transactions[tx_hash]
                        
                        # Vérifier si le timeout est atteint
                        if time.time() - tx_data['timestamp'] > self.tx_timeout:
                            logger.warning(f"Timeout atteint pour la transaction {tx_hash}")
                            
                            # Mettre à jour le statut de la transaction
                            tx_data['status'] = 'timeout'
                            
                            # Mettre à jour l'historique
                            tx_id = tx_data['id']
                            self.transaction_history[tx_id]['status'] = 'timeout'
                            
                            # Supprimer la transaction des transactions en attente
                            del self.pending_transactions[tx_hash]
                            
                            # Mettre à jour les métriques
                            self.monitor.set_gauge('pending_transactions', len(self.pending_transactions))
                            self.monitor.increment_counter('transactions_timeout')
                            continue
                        
                        # Récupérer le statut de la transaction
                        web3 = await self.rpc_manager.get_web3()
                        receipt = await web3.eth.get_transaction_receipt(tx_hash)
                        
                        if receipt is not None:
                            # Vérifier si la transaction est confirmée
                            confirmations = 0
                            if receipt.blockNumber is not None:
                                current_block = await web3.eth.block_number
                                confirmations = current_block - receipt.blockNumber
                            
                            # Mettre à jour le statut de la transaction
                            tx_data['status'] = 'confirmed' if receipt.status == 1 else 'failed'
                            tx_data['receipt'] = receipt
                            tx_data['confirmations'] = confirmations
                            
                            # Mettre à jour l'historique
                            tx_id = tx_data['id']
                            self.transaction_history[tx_id]['status'] = 'confirmed' if receipt.status == 1 else 'failed'
                            self.transaction_history[tx_id]['receipt'] = receipt
                            self.transaction_history[tx_id]['confirmations'] = confirmations
                            
                            # Vérifier si la transaction est confirmée
                            if confirmations >= self.confirmation_blocks:
                                logger.info(f"Transaction {tx_hash} confirmée ({confirmations} confirmations)")
                                
                                # Supprimer la transaction des transactions en attente
                                del self.pending_transactions[tx_hash]
                                
                                # Mettre à jour les métriques
                                self.monitor.set_gauge('pending_transactions', len(self.pending_transactions))
                                if receipt.status == 1:
                                    self.monitor.increment_counter('transactions_confirmed')
                                else:
                                    self.monitor.increment_counter('transactions_failed')
                    except Exception as e:
                        logger.warning(f"Erreur lors de la surveillance de la transaction {tx_hash}: {str(e)}")
        except asyncio.CancelledError:
            logger.info("Tâche de surveillance des transactions annulée")
        except Exception as e:
            logger.error(f"Erreur dans la tâche de surveillance des transactions: {str(e)}")
    
    async def cancel_transaction(self, tx_hash: str) -> Optional[HexBytes]:
        """
        Annule une transaction en attente en envoyant une transaction avec le même nonce et un prix du gas plus élevé.
        
        Args:
            tx_hash: Hash de la transaction à annuler
            
        Returns:
            Optional[HexBytes]: Hash de la nouvelle transaction ou None si échec
        """
        try:
            # Vérifier si la transaction est dans les transactions en attente
            if tx_hash not in self.pending_transactions:
                logger.warning(f"Transaction {tx_hash} non trouvée dans les transactions en attente")
                return None
            
            # Récupérer les paramètres de la transaction
            tx_data = self.pending_transactions[tx_hash]
            tx_params = tx_data['params']
            
            # Créer une nouvelle transaction avec le même nonce et un prix du gas plus élevé
            new_tx_params = {}
            new_tx_params['nonce'] = tx_params['nonce']
            new_tx_params['to'] = tx_params['from']  # Envoyer à soi-même
            new_tx_params['value'] = 0  # Valeur nulle
            
            # Augmenter le prix du gas
            if 'gasPrice' in tx_params:
                new_tx_params['gasPrice'] = Wei(int(tx_params['gasPrice'] * 1.1))  # +10%
            elif 'maxFeePerGas' in tx_params:
                new_tx_params['maxFeePerGas'] = Wei(int(tx_params['maxFeePerGas'] * 1.1))  # +10%
                new_tx_params['maxPriorityFeePerGas'] = Wei(int(tx_params['maxPriorityFeePerGas'] * 1.1))  # +10%
            
            # Estimer la limite de gas
            web3 = await self.rpc_manager.get_web3()
            new_tx_params['gas'] = 21000  # Transfert simple
            
            # Envoyer la nouvelle transaction
            logger.info(f"Annulation de la transaction {tx_hash}")
            new_tx_hash, _ = await self.send_transaction(new_tx_params, wait_for_receipt=False)
            
            # Mettre à jour le statut de la transaction annulée
            tx_data['status'] = 'cancelled'
            tx_data['cancelled_by'] = new_tx_hash.hex()
            
            # Mettre à jour l'historique
            tx_id = tx_data['id']
            self.transaction_history[tx_id]['status'] = 'cancelled'
            self.transaction_history[tx_id]['cancelled_by'] = new_tx_hash.hex()
            
            # Mettre à jour les métriques
            self.monitor.increment_counter('transactions_cancelled')
            
            logger.info(f"Transaction {tx_hash} annulée par {new_tx_hash.hex()}")
            return new_tx_hash
        except Exception as e:
            logger.error(f"Erreur lors de l'annulation de la transaction {tx_hash}: {str(e)}")
            return None
    
    async def speed_up_transaction(self, tx_hash: str) -> Optional[HexBytes]:
        """
        Accélère une transaction en attente en envoyant une transaction avec le même nonce et un prix du gas plus élevé.
        
        Args:
            tx_hash: Hash de la transaction à accélérer
            
        Returns:
            Optional[HexBytes]: Hash de la nouvelle transaction ou None si échec
        """
        try:
            # Vérifier si la transaction est dans les transactions en attente
            if tx_hash not in self.pending_transactions:
                logger.warning(f"Transaction {tx_hash} non trouvée dans les transactions en attente")
                return None
            
            # Récupérer les paramètres de la transaction
            tx_data = self.pending_transactions[tx_hash]
            tx_params = tx_data['params']
            
            # Créer une nouvelle transaction avec le même nonce et un prix du gas plus élevé
            new_tx_params = dict(tx_params)
            
            # Augmenter le prix du gas
            if 'gasPrice' in new_tx_params:
                new_tx_params['gasPrice'] = Wei(int(new_tx_params['gasPrice'] * 1.2))  # +20%
            elif 'maxFeePerGas' in new_tx_params:
                new_tx_params['maxFeePerGas'] = Wei(int(new_tx_params['maxFeePerGas'] * 1.2))  # +20%
                new_tx_params['maxPriorityFeePerGas'] = Wei(int(new_tx_params['maxPriorityFeePerGas'] * 1.2))  # +20%
            
            # Envoyer la nouvelle transaction
            logger.info(f"Accélération de la transaction {tx_hash}")
            new_tx_hash, _ = await self.send_transaction(new_tx_params, wait_for_receipt=False)
            
            # Mettre à jour le statut de la transaction accélérée
            tx_data['status'] = 'replaced'
            tx_data['replaced_by'] = new_tx_hash.hex()
            
            # Mettre à jour l'historique
            tx_id = tx_data['id']
            self.transaction_history[tx_id]['status'] = 'replaced'
            self.transaction_history[tx_id]['replaced_by'] = new_tx_hash.hex()
            
            # Mettre à jour les métriques
            self.monitor.increment_counter('transactions_speedup')
            
            logger.info(f"Transaction {tx_hash} accélérée par {new_tx_hash.hex()}")
            return new_tx_hash
        except Exception as e:
            logger.error(f"Erreur lors de l'accélération de la transaction {tx_hash}: {str(e)}")
            return None

# Instance singleton
transaction_manager = None

def get_transaction_manager(monitor: BotMonitor) -> TransactionManager:
    """
    Récupère l'instance du gestionnaire de transactions.
    
    Args:
        monitor: Moniteur du bot
        
    Returns:
        TransactionManager: Instance du gestionnaire de transactions
    """
    global transaction_manager
    if transaction_manager is None:
        transaction_manager = TransactionManager(monitor)
    return transaction_manager 