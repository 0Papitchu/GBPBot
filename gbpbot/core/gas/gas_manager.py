#!/usr/bin/env python3
"""
Module de gestion des gas fees selon EIP-1559.
"""

import asyncio
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
import logging
from web3 import Web3
from dataclasses import dataclass
import statistics
from datetime import datetime, timedelta

@dataclass
class GasConfig:
    """Configuration pour la gestion des gas fees."""
    max_base_fee: int  # En wei
    max_priority_fee: int  # En wei
    min_priority_fee: int  # En wei
    base_fee_multiplier: float  # Multiplicateur pour le base fee
    priority_fee_multiplier: float  # Multiplicateur pour le priority fee
    max_total_fee: int  # En wei
    update_interval: int  # En secondes
    history_size: int  # Nombre de blocks à analyser

class GasManager:
    """Gestionnaire des gas fees EIP-1559."""
    
    def __init__(self, config: Dict, web3: Web3):
        """Initialise le gestionnaire de gas."""
        self.web3 = web3
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.config = GasConfig(
            max_base_fee=Web3.to_wei(500, 'gwei'),
            max_priority_fee=Web3.to_wei(50, 'gwei'),
            min_priority_fee=Web3.to_wei(1, 'gwei'),
            base_fee_multiplier=1.125,  # +12.5%
            priority_fee_multiplier=1.1,  # +10%
            max_total_fee=Web3.to_wei(1000, 'gwei'),
            update_interval=15,  # 15 secondes
            history_size=20  # 20 blocks
        )
        
        # État
        self.base_fee_history: List[int] = []
        self.priority_fee_history: List[int] = []
        self.last_update = datetime.min
        self.is_running = False
        self._update_task = None
        
        # Statistiques
        self.stats = {
            'avg_base_fee': 0,
            'avg_priority_fee': 0,
            'min_base_fee': 0,
            'max_base_fee': 0,
            'success_rate': 1.0,
            'total_transactions': 0,
            'failed_transactions': 0
        }
    
    async def start(self):
        """Démarre le monitoring des gas fees."""
        if self.is_running:
            return
            
        self.is_running = True
        self._update_task = asyncio.create_task(self._update_loop())
        self.logger.info("Gas fee monitoring started")
    
    async def stop(self):
        """Arrête le monitoring des gas fees."""
        if not self.is_running:
            return
            
        self.is_running = False
        if self._update_task:
            self._update_task.cancel()
            try:
                await self._update_task
            except asyncio.CancelledError:
                pass
            
        self.logger.info("Gas fee monitoring stopped")
    
    async def get_gas_params(self, priority: str = 'medium') -> Dict[str, int]:
        """
        Calcule les paramètres de gas optimaux.
        
        Args:
            priority: 'low', 'medium', ou 'high'
            
        Returns:
            Dict avec maxFeePerGas et maxPriorityFeePerGas
        """
        # Mettre à jour si nécessaire
        await self._maybe_update()
        
        # Calculer les multiplicateurs selon la priorité
        multipliers = {
            'low': 1.0,
            'medium': self.config.base_fee_multiplier,
            'high': self.config.base_fee_multiplier * 1.2
        }
        
        base_multiplier = multipliers.get(priority, self.config.base_fee_multiplier)
        priority_multiplier = 1.0 if priority == 'low' else self.config.priority_fee_multiplier
        
        # Calculer les fees
        base_fee = await self._get_optimal_base_fee(base_multiplier)
        priority_fee = await self._get_optimal_priority_fee(priority_multiplier)
        
        # Limiter le total
        total_fee = base_fee + priority_fee
        if total_fee > self.config.max_total_fee:
            # Réduire proportionnellement
            reduction_factor = self.config.max_total_fee / total_fee
            base_fee = int(base_fee * reduction_factor)
            priority_fee = int(priority_fee * reduction_factor)
        
        return {
            'maxFeePerGas': base_fee,
            'maxPriorityFeePerGas': priority_fee
        }
    
    async def estimate_gas_cost(self, gas_limit: int, priority: str = 'medium') -> int:
        """
        Estime le coût en gas d'une transaction.
        
        Args:
            gas_limit: Limite de gas
            priority: Priorité de la transaction
            
        Returns:
            Coût estimé en wei
        """
        gas_params = await self.get_gas_params(priority)
        return gas_limit * gas_params['maxFeePerGas']
    
    def record_transaction_result(self, success: bool, gas_used: int, 
                                base_fee: int, priority_fee: int):
        """
        Enregistre le résultat d'une transaction pour améliorer les estimations.
        
        Args:
            success: Si la transaction a réussi
            gas_used: Gas utilisé
            base_fee: Base fee utilisé
            priority_fee: Priority fee utilisé
        """
        self.stats['total_transactions'] += 1
        if not success:
            self.stats['failed_transactions'] += 1
            
        self.stats['success_rate'] = 1 - (
            self.stats['failed_transactions'] / self.stats['total_transactions']
        )
    
    async def _update_loop(self):
        """Boucle de mise à jour des historiques de gas."""
        while self.is_running:
            try:
                await self._update_gas_history()
                await asyncio.sleep(self.config.update_interval)
            except Exception as e:
                self.logger.error(f"Error updating gas history: {e}")
                await asyncio.sleep(5)  # Attendre un peu en cas d'erreur
    
    async def _maybe_update(self):
        """Met à jour l'historique si nécessaire."""
        if (datetime.now() - self.last_update).total_seconds() > self.config.update_interval:
            await self._update_gas_history()
    
    async def _update_gas_history(self):
        """Met à jour l'historique des gas fees."""
        try:
            # Obtenir le dernier block
            latest_block = await self.web3.eth.block_number
            
            # Analyser les derniers blocks
            base_fees = []
            priority_fees = []
            
            for block_number in range(latest_block - self.config.history_size, latest_block):
                block = await self.web3.eth.get_block(block_number, True)
                base_fees.append(block['baseFeePerGas'])
                
                # Collecter les priority fees des transactions
                for tx in block['transactions']:
                    if 'maxPriorityFeePerGas' in tx:
                        priority_fees.append(tx['maxPriorityFeePerGas'])
            
            # Mettre à jour les historiques
            self.base_fee_history = base_fees[-self.config.history_size:]
            self.priority_fee_history = priority_fees[-self.config.history_size:]
            
            # Mettre à jour les statistiques
            if self.base_fee_history:
                self.stats.update({
                    'avg_base_fee': statistics.mean(self.base_fee_history),
                    'min_base_fee': min(self.base_fee_history),
                    'max_base_fee': max(self.base_fee_history)
                })
            
            if self.priority_fee_history:
                self.stats['avg_priority_fee'] = statistics.mean(self.priority_fee_history)
            
            self.last_update = datetime.now()
            
        except Exception as e:
            self.logger.error(f"Failed to update gas history: {e}")
            raise
    
    async def _get_optimal_base_fee(self, multiplier: float = 1.0) -> int:
        """
        Calcule le base fee optimal.
        
        Args:
            multiplier: Multiplicateur à appliquer
            
        Returns:
            Base fee optimal en wei
        """
        if not self.base_fee_history:
            return self.config.max_base_fee
            
        # Utiliser une moyenne pondérée des derniers blocks
        weights = [1 + i/len(self.base_fee_history) for i in range(len(self.base_fee_history))]
        weighted_avg = sum(f * w for f, w in zip(self.base_fee_history, weights)) / sum(weights)
        
        base_fee = int(weighted_avg * multiplier)
        return min(base_fee, self.config.max_base_fee)
    
    async def _get_optimal_priority_fee(self, multiplier: float = 1.0) -> int:
        """
        Calcule le priority fee optimal.
        
        Args:
            multiplier: Multiplicateur à appliquer
            
        Returns:
            Priority fee optimal en wei
        """
        if not self.priority_fee_history:
            return self.config.min_priority_fee
            
        # Utiliser le 75e percentile des priority fees récents
        sorted_fees = sorted(self.priority_fee_history)
        percentile_75 = sorted_fees[int(len(sorted_fees) * 0.75)]
        
        priority_fee = int(percentile_75 * multiplier)
        return min(
            max(priority_fee, self.config.min_priority_fee),
            self.config.max_priority_fee
        )
    
    def get_stats(self) -> Dict:
        """Retourne les statistiques de gas."""
        return {
            'current': {
                'base_fee': self.base_fee_history[-1] if self.base_fee_history else 0,
                'priority_fee': self.priority_fee_history[-1] if self.priority_fee_history else 0
            },
            'averages': {
                'base_fee': self.stats['avg_base_fee'],
                'priority_fee': self.stats['avg_priority_fee']
            },
            'ranges': {
                'min_base_fee': self.stats['min_base_fee'],
                'max_base_fee': self.stats['max_base_fee']
            },
            'performance': {
                'success_rate': self.stats['success_rate'],
                'total_transactions': self.stats['total_transactions'],
                'failed_transactions': self.stats['failed_transactions']
            }
        } 