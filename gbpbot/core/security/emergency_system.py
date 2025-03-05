#!/usr/bin/env python3
"""
Module de gestion des situations d'urgence et rollbacks.
"""

import asyncio
from typing import Dict, List, Optional
from decimal import Decimal
from web3 import Web3
from loguru import logger

from gbpbot.core.monitoring.monitor import BotMonitor
from gbpbot.core.rpc.rpc_manager import RPCManager

class EmergencySystem:
    """Gestionnaire des situations d'urgence."""
    
    def __init__(self, config: Dict, monitor: BotMonitor):
        """
        Initialise le système d'urgence.
        
        Args:
            config: Configuration du bot
            monitor: Instance du moniteur
        """
        self.config = config
        self.monitor = monitor
        self.rpc_manager = RPCManager()
        
        # Configuration
        self.emergency_config = self.config.get('emergency', {})
        self.max_loss_threshold = Decimal(str(self.emergency_config.get('max_loss', '0.10')))  # 10%
        self.max_gas_threshold = Web3.to_wei(self.emergency_config.get('max_gas_gwei', 500), 'gwei')
        self.min_balance_threshold = Web3.to_wei(self.emergency_config.get('min_balance_eth', 0.1), 'ether')
        
        # État du système
        self.is_emergency = False
        self.pending_transactions: Dict[str, Dict] = {}
        self.emergency_actions: List[Dict] = []

    async def check_emergency_conditions(self) -> bool:
        """
        Vérifie si les conditions d'urgence sont remplies.
        
        Returns:
            bool: True si une situation d'urgence est détectée
        """
        try:
            # Vérifier la balance
            balance = await self._get_wallet_balance()
            if balance < self.min_balance_threshold:
                logger.critical("Balance trop faible - Activation du mode urgence")
                await self._trigger_emergency("LOW_BALANCE")
                return True
                
            # Vérifier le gas
            gas_price = await self._get_current_gas_price()
            if gas_price > self.max_gas_threshold:
                logger.critical("Gas price trop élevé - Activation du mode urgence")
                await self._trigger_emergency("HIGH_GAS")
                return True
                
            # Vérifier les pertes
            total_loss = await self._calculate_total_loss()
            if total_loss > self.max_loss_threshold:
                logger.critical("Pertes trop importantes - Activation du mode urgence")
                await self._trigger_emergency("EXCESSIVE_LOSS")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification des conditions d'urgence: {str(e)}")
            return True  # Par sécurité, on considère qu'il y a urgence en cas d'erreur

    async def emergency_shutdown(self):
        """Procédure d'arrêt d'urgence."""
        try:
            if self.is_emergency:
                return
                
            self.is_emergency = True
            logger.critical("ARRÊT D'URGENCE INITIÉ")
            
            # 1. Annuler les transactions en attente
            await self._cancel_pending_transactions()
            
            # 2. Fermer les positions ouvertes
            await self._close_all_positions()
            
            # 3. Sécuriser les fonds
            await self._secure_funds()
            
            # 4. Notifier
            await self._send_emergency_notifications()
            
            logger.info("Arrêt d'urgence terminé")
            
        except Exception as e:
            logger.critical(f"ERREUR CRITIQUE lors de l'arrêt d'urgence: {str(e)}")

    async def rollback_transaction(self, tx_hash: str) -> bool:
        """
        Tente d'annuler une transaction.
        
        Args:
            tx_hash: Hash de la transaction à annuler
            
        Returns:
            bool: True si la transaction a été annulée
        """
        try:
            if tx_hash not in self.pending_transactions:
                return False
                
            tx_info = self.pending_transactions[tx_hash]
            
            # Vérifier si la transaction peut être annulée
            if await self._is_transaction_confirmed(tx_hash):
                logger.warning(f"Transaction {tx_hash} déjà confirmée - Impossible d'annuler")
                return False
                
            # Envoyer une transaction de remplacement avec un gas price plus élevé
            replacement_tx = await self._create_replacement_transaction(tx_info)
            new_tx_hash = await self._send_replacement_transaction(replacement_tx)
            
            if new_tx_hash:
                logger.info(f"Transaction {tx_hash} annulée avec succès")
                del self.pending_transactions[tx_hash]
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Erreur lors de l'annulation de la transaction: {str(e)}")
            return False

    async def add_pending_transaction(self, tx_hash: str, tx_info: Dict):
        """
        Ajoute une transaction à surveiller.
        
        Args:
            tx_hash: Hash de la transaction
            tx_info: Informations sur la transaction
        """
        self.pending_transactions[tx_hash] = tx_info
        logger.info(f"Transaction {tx_hash} ajoutée au monitoring")

    async def _trigger_emergency(self, reason: str):
        """
        Déclenche une procédure d'urgence.
        
        Args:
            reason: Raison de l'urgence
        """
        self.emergency_actions.append({
            'timestamp': asyncio.get_event_loop().time(),
            'reason': reason
        })
        
        await self.emergency_shutdown()

    async def _cancel_pending_transactions(self):
        """Annule toutes les transactions en attente."""
        for tx_hash in list(self.pending_transactions.keys()):
            await self.rollback_transaction(tx_hash)

    async def _close_all_positions(self):
        """Ferme toutes les positions ouvertes."""
        # TODO: Implémenter la fermeture des positions
        pass

    async def _secure_funds(self):
        """Sécurise les fonds en les transférant vers un wallet sécurisé."""
        try:
            safe_wallet = self.emergency_config.get('safe_wallet_address')
            if not safe_wallet:
                logger.error("Adresse du wallet sécurisé non configurée")
                return
                
            balance = await self._get_wallet_balance()
            if balance <= 0:
                return
                
            # Garder un peu d'ETH pour le gas
            transfer_amount = balance - Web3.to_wei(0.05, 'ether')
            if transfer_amount <= 0:
                return
                
            # TODO: Implémenter le transfert des fonds
            logger.info(f"Fonds sécurisés: {Web3.from_wei(transfer_amount, 'ether')} ETH")
            
        except Exception as e:
            logger.error(f"Erreur lors de la sécurisation des fonds: {str(e)}")

    async def _send_emergency_notifications(self):
        """Envoie les notifications d'urgence."""
        try:
            message = (
                "🚨 ARRÊT D'URGENCE DU BOT 🚨\n"
                f"Raison: {self.emergency_actions[-1]['reason']}\n"
                f"Transactions annulées: {len(self.pending_transactions)}\n"
                "Vérifiez le dashboard pour plus de détails."
            )
            
            # TODO: Implémenter l'envoi des notifications
            logger.info(f"Notification d'urgence envoyée: {message}")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi des notifications: {str(e)}")

    async def _get_wallet_balance(self) -> int:
        """
        Récupère la balance du wallet.
        
        Returns:
            int: Balance en wei
        """
        try:
            # TODO: Implémenter la récupération de la balance
            return 0
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la balance: {str(e)}")
            return 0

    async def _get_current_gas_price(self) -> int:
        """
        Récupère le prix actuel du gas.
        
        Returns:
            int: Prix du gas en wei
        """
        try:
            # TODO: Implémenter la récupération du gas price
            return 0
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du gas price: {str(e)}")
            return Web3.to_wei(500, 'gwei')  # Valeur haute par sécurité

    async def _calculate_total_loss(self) -> Decimal:
        """
        Calcule la perte totale.
        
        Returns:
            Decimal: Pourcentage de perte
        """
        try:
            # TODO: Implémenter le calcul des pertes
            return Decimal('0')
            
        except Exception as e:
            logger.error(f"Erreur lors du calcul des pertes: {str(e)}")
            return Decimal('1')  # 100% de perte par sécurité

    async def _is_transaction_confirmed(self, tx_hash: str) -> bool:
        """
        Vérifie si une transaction est confirmée.
        
        Args:
            tx_hash: Hash de la transaction
            
        Returns:
            bool: True si la transaction est confirmée
        """
        try:
            # TODO: Implémenter la vérification
            return False
            
        except Exception as e:
            logger.error(f"Erreur lors de la vérification de la transaction: {str(e)}")
            return True  # Par sécurité

    async def _create_replacement_transaction(self, tx_info: Dict) -> Dict:
        """
        Crée une transaction de remplacement.
        
        Args:
            tx_info: Informations sur la transaction originale
            
        Returns:
            Dict: Nouvelle transaction
        """
        try:
            # Copier les paramètres de base
            new_tx = tx_info.copy()
            
            # Augmenter le gas price de 10%
            new_tx['maxFeePerGas'] = int(new_tx['maxFeePerGas'] * 1.1)
            new_tx['maxPriorityFeePerGas'] = int(new_tx['maxPriorityFeePerGas'] * 1.1)
            
            # Mettre à zéro la valeur pour annuler la transaction
            new_tx['value'] = 0
            
            return new_tx
            
        except Exception as e:
            logger.error(f"Erreur lors de la création de la transaction de remplacement: {str(e)}")
            raise

    async def _send_replacement_transaction(self, tx_params: Dict) -> Optional[str]:
        """
        Envoie une transaction de remplacement.
        
        Args:
            tx_params: Paramètres de la transaction
            
        Returns:
            Optional[str]: Hash de la nouvelle transaction
        """
        try:
            # TODO: Implémenter l'envoi de la transaction
            return None
            
        except Exception as e:
            logger.error(f"Erreur lors de l'envoi de la transaction de remplacement: {str(e)}")
            return None

    def get_emergency_status(self) -> Dict:
        """
        Récupère l'état du système d'urgence.
        
        Returns:
            Dict: État du système
        """
        return {
            'is_emergency': self.is_emergency,
            'pending_transactions': len(self.pending_transactions),
            'emergency_actions': self.emergency_actions
        } 