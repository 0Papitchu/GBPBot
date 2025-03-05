#!/usr/bin/env python3
"""
Module de protection des trades contre les attaques et les pertes.
"""

import asyncio
from typing import Dict, Optional
from decimal import Decimal
from web3 import Web3
from loguru import logger

from gbpbot.core.monitoring.monitor import BotMonitor

class TradeProtection:
    """Gestionnaire des protections pour les trades."""
    
    def __init__(self, config: Dict, monitor: BotMonitor):
        """
        Initialise le système de protection.
        
        Args:
            config: Configuration du bot
            monitor: Instance du moniteur
        """
        self.config = config
        self.monitor = monitor
        
        # Configuration des protections
        self.protection_config = self.config.get('protection', {})
        self.stop_loss = Decimal(str(self.protection_config.get('stop_loss', '0.05')))  # 5%
        self.take_profit = Decimal(str(self.protection_config.get('take_profit', '0.03')))  # 3%
        self.max_slippage = Decimal(str(self.protection_config.get('max_slippage', '0.01')))  # 1%
        
        # État des positions
        self.active_positions: Dict[str, Dict] = {}
        self.position_updates = asyncio.Queue()

    async def check_mev_protection(self, tx_params: Dict) -> Dict:
        """
        Vérifie et protège contre les attaques MEV.
        
        Args:
            tx_params: Paramètres de la transaction
            
        Returns:
            Dict: Paramètres de transaction modifiés
        """
        try:
            # Protection contre le frontrunning
            tx_params['maxFeePerGas'] = await self._calculate_optimal_gas()
            tx_params['maxPriorityFeePerGas'] = tx_params['maxFeePerGas'] // 2
            
            # Ajouter un délai minimum de validité
            current_block = await self._get_current_block()
            tx_params['validUntilBlock'] = current_block + 2
            
            # Protection contre le sandwich
            tx_params['minOutput'] = int(
                Decimal(str(tx_params.get('expectedOutput', 0))) * 
                (1 - self.max_slippage)
            )
            
            return tx_params
            
        except Exception as e:
            logger.error(f"Erreur lors de la protection MEV: {str(e)}")
            raise

    async def add_position(self, position_id: str, entry_price: Decimal, size: Decimal):
        """
        Ajoute une nouvelle position à surveiller.
        
        Args:
            position_id: Identifiant unique de la position
            entry_price: Prix d'entrée
            size: Taille de la position
        """
        try:
            self.active_positions[position_id] = {
                'entry_price': entry_price,
                'current_price': entry_price,
                'size': size,
                'stop_loss_price': entry_price * (1 - self.stop_loss),
                'take_profit_price': entry_price * (1 + self.take_profit),
                'timestamp': asyncio.get_event_loop().time()
            }
            
            # Démarrer le monitoring si nécessaire
            if len(self.active_positions) == 1:
                asyncio.create_task(self._monitor_positions())
                
            logger.info(f"Position {position_id} ajoutée avec SL à {self.stop_loss}% et TP à {self.take_profit}%")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout de la position: {str(e)}")
            raise

    async def update_position_price(self, position_id: str, new_price: Decimal):
        """
        Met à jour le prix d'une position.
        
        Args:
            position_id: Identifiant de la position
            new_price: Nouveau prix
        """
        try:
            if position_id not in self.active_positions:
                return
                
            position = self.active_positions[position_id]
            position['current_price'] = new_price
            
            # Vérifier les conditions de sortie
            await self._check_exit_conditions(position_id)
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour du prix: {str(e)}")

    async def remove_position(self, position_id: str):
        """
        Supprime une position du monitoring.
        
        Args:
            position_id: Identifiant de la position
        """
        if position_id in self.active_positions:
            del self.active_positions[position_id]
            logger.info(f"Position {position_id} supprimée du monitoring")

    async def _monitor_positions(self):
        """Monitore en continu les positions actives."""
        while True:
            try:
                # Vérifier chaque position
                for position_id in list(self.active_positions.keys()):
                    await self._check_exit_conditions(position_id)
                    
                await asyncio.sleep(1)  # Vérification toutes les secondes
                
            except Exception as e:
                logger.error(f"Erreur dans le monitoring des positions: {str(e)}")
                await asyncio.sleep(5)

    async def _check_exit_conditions(self, position_id: str):
        """
        Vérifie les conditions de sortie d'une position.
        
        Args:
            position_id: Identifiant de la position
        """
        try:
            position = self.active_positions[position_id]
            current_price = position['current_price']
            
            # Vérifier stop loss
            if current_price <= position['stop_loss_price']:
                await self.position_updates.put({
                    'position_id': position_id,
                    'action': 'stop_loss',
                    'price': current_price
                })
                return
                
            # Vérifier take profit
            if current_price >= position['take_profit_price']:
                await self.position_updates.put({
                    'position_id': position_id,
                    'action': 'take_profit',
                    'price': current_price
                })
                return
                
        except Exception as e:
            logger.error(f"Erreur lors de la vérification des conditions de sortie: {str(e)}")

    async def _calculate_optimal_gas(self) -> int:
        """
        Calcule le gas optimal pour éviter le frontrunning.
        
        Returns:
            int: Prix du gas optimal en wei
        """
        try:
            # TODO: Implémenter la logique de calcul du gas optimal
            # Pour l'instant, on utilise une valeur par défaut
            return Web3.to_wei(50, 'gwei')
            
        except Exception as e:
            logger.error(f"Erreur lors du calcul du gas optimal: {str(e)}")
            return Web3.to_wei(30, 'gwei')  # Valeur par défaut conservative

    async def _get_current_block(self) -> int:
        """
        Récupère le numéro du bloc actuel.
        
        Returns:
            int: Numéro du bloc
        """
        try:
            # TODO: Implémenter la récupération du bloc actuel
            return 0
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du bloc actuel: {str(e)}")
            return 0

    async def get_position_status(self, position_id: str) -> Optional[Dict]:
        """
        Récupère l'état d'une position.
        
        Args:
            position_id: Identifiant de la position
            
        Returns:
            Optional[Dict]: État de la position
        """
        return self.active_positions.get(position_id) 