#!/usr/bin/env python3
"""
Module d'optimisation des frais de gas avec support EIP-1559.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal
from loguru import logger
from web3 import Web3
from web3.types import TxParams, Wei

from gbpbot.config.config_manager import ConfigManager
from gbpbot.core.rpc.rpc_manager import RPCManager

class GasOptimizer:
    """Optimiseur de frais de gas avec support EIP-1559."""
    
    def __init__(self):
        """Initialise l'optimiseur de gas."""
        logger.info("Initialisation de l'optimiseur de gas")
        self.config = ConfigManager().get_config()
        self.rpc_manager = RPCManager()
        
        # Configuration EIP-1559
        self.eip1559_config = self.config.get('gas', {}).get('eip1559', {})
        self.eip1559_enabled = self.eip1559_config.get('enabled', True)
        self.priority_fee_multiplier = Decimal(str(self.eip1559_config.get('priority_fee_multiplier', 1.2)))
        self.max_priority_fee = Decimal(str(self.eip1559_config.get('max_priority_fee', 3)))
        self.base_fee_multiplier = Decimal(str(self.eip1559_config.get('base_fee_multiplier', 1.1)))
        
        # Configuration de l'optimiseur
        self.optimizer_config = self.config.get('gas', {}).get('optimizer', {})
        self.gas_price_strategy = self.optimizer_config.get('gas_price_strategy', 'medium')
        self.max_wait_time = self.optimizer_config.get('max_wait_time', 60)
        self.min_gas_price = Wei(int(Decimal(str(self.optimizer_config.get('min_gas_price', 25))) * Decimal('1e9')))
        self.max_gas_price = Wei(int(Decimal(str(self.optimizer_config.get('max_gas_price', 100))) * Decimal('1e9')))
        
        # Cache des estimations
        self.last_base_fee = None
        self.last_priority_fee = None
        self.last_gas_price = None
        self.last_update_time = 0
        self.cache_ttl = 30  # 30 secondes
        
        logger.info(f"Optimiseur de gas initialisé (EIP-1559: {'activé' if self.eip1559_enabled else 'désactivé'})")
    
    async def get_gas_price(self) -> Wei:
        """
        Récupère le prix du gas optimal selon la stratégie configurée.
        
        Returns:
            Wei: Prix du gas en wei
        """
        try:
            # Vérifier si le cache est valide
            if self.last_gas_price is not None and time.time() - self.last_update_time < self.cache_ttl:
                logger.debug(f"Utilisation du prix du gas en cache: {Web3.from_wei(self.last_gas_price, 'gwei')} gwei")
                return self.last_gas_price
            
            # Récupérer le prix du gas depuis le RPC
            web3 = await self.rpc_manager.get_web3()
            gas_price = web3.eth.gas_price
            
            # Appliquer la stratégie
            if self.gas_price_strategy == 'low':
                gas_price = Wei(int(gas_price * 0.8))
            elif self.gas_price_strategy == 'high':
                gas_price = Wei(int(gas_price * 1.2))
            
            # Appliquer les limites
            gas_price = max(self.min_gas_price, min(self.max_gas_price, gas_price))
            
            # Mettre à jour le cache
            self.last_gas_price = gas_price
            self.last_update_time = time.time()
            
            logger.debug(f"Prix du gas estimé: {Web3.from_wei(gas_price, 'gwei')} gwei (stratégie: {self.gas_price_strategy})")
            return gas_price
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du prix du gas: {str(e)}")
            # En cas d'erreur, utiliser le dernier prix connu ou la valeur par défaut
            return self.last_gas_price or self.min_gas_price
    
    async def get_eip1559_fees(self) -> Tuple[Wei, Wei]:
        """
        Récupère les frais EIP-1559 (base fee et priority fee).
        
        Returns:
            Tuple[Wei, Wei]: (max_fee_per_gas, max_priority_fee_per_gas)
        """
        try:
            # Vérifier si le cache est valide
            if (self.last_base_fee is not None and self.last_priority_fee is not None and 
                time.time() - self.last_update_time < self.cache_ttl):
                logger.debug(f"Utilisation des frais EIP-1559 en cache: base={Web3.from_wei(self.last_base_fee, 'gwei')} gwei, priorité={Web3.from_wei(self.last_priority_fee, 'gwei')} gwei")
                return self.last_base_fee, self.last_priority_fee
            
            # Récupérer les informations du dernier bloc
            web3 = await self.rpc_manager.get_web3()
            latest_block = web3.eth.get_block('latest')
            
            # Récupérer le base fee du dernier bloc
            base_fee_per_gas = latest_block.get('baseFeePerGas', 0)
            
            # Estimer le max priority fee
            max_priority_fee_per_gas = await self._estimate_priority_fee()
            
            # Calculer le max fee (base fee * multiplier + priority fee)
            max_fee_per_gas = Wei(int(base_fee_per_gas * float(self.base_fee_multiplier)) + max_priority_fee_per_gas)
            
            # Mettre à jour le cache
            self.last_base_fee = max_fee_per_gas
            self.last_priority_fee = max_priority_fee_per_gas
            self.last_update_time = time.time()
            
            logger.debug(f"Frais EIP-1559 estimés: base={Web3.from_wei(max_fee_per_gas, 'gwei')} gwei, priorité={Web3.from_wei(max_priority_fee_per_gas, 'gwei')} gwei")
            return max_fee_per_gas, max_priority_fee_per_gas
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des frais EIP-1559: {str(e)}")
            # En cas d'erreur, utiliser les dernières valeurs connues ou des valeurs par défaut
            if self.last_base_fee is not None and self.last_priority_fee is not None:
                return self.last_base_fee, self.last_priority_fee
            else:
                gas_price = await self.get_gas_price()
                return gas_price, Wei(int(gas_price * 0.1))
    
    async def _estimate_priority_fee(self) -> Wei:
        """
        Estime le priority fee optimal en fonction des blocs récents.
        
        Returns:
            Wei: Priority fee en wei
        """
        try:
            web3 = await self.rpc_manager.get_web3()
            
            # Récupérer les 10 derniers blocs
            latest_block = web3.eth.block_number
            priority_fees = []
            
            for i in range(10):
                block_number = latest_block - i
                if block_number < 0:
                    break
                
                block = web3.eth.get_block(block_number, full_transactions=True)
                
                # Extraire les priority fees des transactions
                for tx in block.get('transactions', []):
                    if hasattr(tx, 'maxPriorityFeePerGas'):
                        priority_fees.append(tx.maxPriorityFeePerGas)
            
            if not priority_fees:
                # Si aucun priority fee n'est trouvé, utiliser une valeur par défaut
                return Wei(int(Decimal('1.5') * Decimal('1e9')))
            
            # Calculer le priority fee médian
            priority_fees.sort()
            median_priority_fee = priority_fees[len(priority_fees) // 2]
            
            # Appliquer le multiplicateur
            priority_fee = Wei(int(median_priority_fee * float(self.priority_fee_multiplier)))
            
            # Limiter au maximum configuré
            max_priority_fee_wei = Wei(int(self.max_priority_fee * Decimal('1e9')))
            priority_fee = min(priority_fee, max_priority_fee_wei)
            
            return priority_fee
        except Exception as e:
            logger.error(f"Erreur lors de l'estimation du priority fee: {str(e)}")
            # En cas d'erreur, utiliser une valeur par défaut
            return Wei(int(Decimal('1.5') * Decimal('1e9')))
    
    async def optimize_transaction(self, tx_params: TxParams) -> TxParams:
        """
        Optimise les paramètres de transaction en fonction de la configuration.
        
        Args:
            tx_params: Paramètres de la transaction
            
        Returns:
            TxParams: Paramètres optimisés
        """
        try:
            # Copier les paramètres pour ne pas modifier l'original
            optimized_tx = dict(tx_params)
            
            # Appliquer EIP-1559 si activé
            if self.eip1559_enabled:
                max_fee_per_gas, max_priority_fee_per_gas = await self.get_eip1559_fees()
                
                # Mettre à jour les paramètres
                optimized_tx['maxFeePerGas'] = max_fee_per_gas
                optimized_tx['maxPriorityFeePerGas'] = max_priority_fee_per_gas
                
                # Supprimer gasPrice s'il existe
                if 'gasPrice' in optimized_tx:
                    del optimized_tx['gasPrice']
                    
                logger.debug(f"Transaction optimisée avec EIP-1559: maxFeePerGas={Web3.from_wei(max_fee_per_gas, 'gwei')} gwei, maxPriorityFeePerGas={Web3.from_wei(max_priority_fee_per_gas, 'gwei')} gwei")
            else:
                # Utiliser le prix du gas standard
                gas_price = await self.get_gas_price()
                
                # Mettre à jour les paramètres
                optimized_tx['gasPrice'] = gas_price
                
                # Supprimer les paramètres EIP-1559 s'ils existent
                if 'maxFeePerGas' in optimized_tx:
                    del optimized_tx['maxFeePerGas']
                if 'maxPriorityFeePerGas' in optimized_tx:
                    del optimized_tx['maxPriorityFeePerGas']
                    
                logger.debug(f"Transaction optimisée avec gasPrice standard: {Web3.from_wei(gas_price, 'gwei')} gwei")
            
            return optimized_tx
        except Exception as e:
            logger.error(f"Erreur lors de l'optimisation de la transaction: {str(e)}")
            # En cas d'erreur, retourner les paramètres originaux
            return tx_params
    
    async def wait_for_optimal_gas(self, max_wait_time: Optional[int] = None) -> Wei:
        """
        Attend que le prix du gas soit optimal selon la stratégie configurée.
        
        Args:
            max_wait_time: Temps d'attente maximum en secondes (None pour utiliser la valeur configurée)
            
        Returns:
            Wei: Prix du gas optimal en wei
        """
        try:
            max_wait = max_wait_time or self.max_wait_time
            start_time = time.time()
            
            # Récupérer le prix du gas initial
            initial_gas_price = await self.get_gas_price()
            current_gas_price = initial_gas_price
            
            logger.info(f"Attente d'un prix du gas optimal (initial: {Web3.from_wei(initial_gas_price, 'gwei')} gwei, max: {max_wait}s)")
            
            # Définir le prix cible en fonction de la stratégie
            if self.gas_price_strategy == 'low':
                target_gas_price = Wei(int(initial_gas_price * 0.8))
            elif self.gas_price_strategy == 'high':
                # Pour la stratégie 'high', on n'attend pas un prix plus bas
                return initial_gas_price
            else:  # 'medium'
                target_gas_price = Wei(int(initial_gas_price * 0.9))
            
            # Attendre que le prix du gas soit inférieur à la cible
            while time.time() - start_time < max_wait:
                # Attendre un peu avant de vérifier à nouveau
                await asyncio.sleep(5)
                
                # Récupérer le prix du gas actuel
                current_gas_price = await self.get_gas_price()
                
                # Si le prix est inférieur à la cible, on arrête d'attendre
                if current_gas_price <= target_gas_price:
                    logger.info(f"Prix du gas optimal atteint: {Web3.from_wei(current_gas_price, 'gwei')} gwei (après {int(time.time() - start_time)}s)")
                    return current_gas_price
                
                logger.debug(f"Prix du gas actuel: {Web3.from_wei(current_gas_price, 'gwei')} gwei (cible: {Web3.from_wei(target_gas_price, 'gwei')} gwei)")
            
            # Si on a atteint le temps maximum, on retourne le prix actuel
            logger.info(f"Temps d'attente maximum atteint, utilisation du prix actuel: {Web3.from_wei(current_gas_price, 'gwei')} gwei")
            return current_gas_price
        except Exception as e:
            logger.error(f"Erreur lors de l'attente d'un prix du gas optimal: {str(e)}")
            # En cas d'erreur, retourner le prix actuel
            return await self.get_gas_price()
    
    async def estimate_transaction_cost(self, gas_limit: int) -> Tuple[Wei, str]:
        """
        Estime le coût d'une transaction en fonction de la limite de gas.
        
        Args:
            gas_limit: Limite de gas pour la transaction
            
        Returns:
            Tuple[Wei, str]: (coût estimé en wei, coût formaté)
        """
        try:
            # Récupérer le prix du gas
            if self.eip1559_enabled:
                max_fee_per_gas, _ = await self.get_eip1559_fees()
                gas_price = max_fee_per_gas
            else:
                gas_price = await self.get_gas_price()
            
            # Calculer le coût estimé
            cost_wei = Wei(gas_limit * gas_price)
            
            # Formater le coût
            if cost_wei < Wei(10**15):  # < 0.001 ETH
                cost_formatted = f"{Web3.from_wei(cost_wei, 'gwei')} gwei"
            else:
                cost_formatted = f"{Web3.from_wei(cost_wei, 'ether'):.6f} ETH"
            
            logger.debug(f"Coût estimé pour {gas_limit} gas: {cost_formatted}")
            return cost_wei, cost_formatted
        except Exception as e:
            logger.error(f"Erreur lors de l'estimation du coût de la transaction: {str(e)}")
            # En cas d'erreur, retourner une estimation par défaut
            cost_wei = Wei(gas_limit * 50 * 10**9)  # 50 gwei par défaut
            return cost_wei, f"{Web3.from_wei(cost_wei, 'ether'):.6f} ETH"

# Instance singleton
gas_optimizer = GasOptimizer()