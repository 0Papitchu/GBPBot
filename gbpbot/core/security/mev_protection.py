#!/usr/bin/env python3
"""
Module de protection contre les attaques MEV (Miner Extractable Value).
"""

import asyncio
from decimal import Decimal
from typing import Dict, Optional, List
import logging
from web3 import Web3
from eth_typing import HexStr
from dataclasses import dataclass

@dataclass
class MEVConfig:
    """Configuration pour la protection MEV."""
    min_priority_fee: int  # En wei
    max_priority_fee: int  # En wei
    base_fee_multiplier: float  # Multiplicateur pour le base fee
    max_base_fee: int  # En wei
    privacy_mode: bool  # Utiliser un relayer privé
    slippage_buffer: Decimal  # Buffer supplémentaire pour le slippage
    block_delay: int  # Nombre de blocks à attendre

class MEVProtection:
    """Protection contre les attaques MEV."""
    
    def __init__(self, config: Dict, web3: Web3):
        """Initialise la protection MEV."""
        self.web3 = web3
        self.logger = logging.getLogger(__name__)
        
        # Configuration
        self.config = MEVConfig(
            min_priority_fee=Web3.to_wei(2, 'gwei'),
            max_priority_fee=Web3.to_wei(50, 'gwei'),
            base_fee_multiplier=1.125,  # +12.5%
            max_base_fee=Web3.to_wei(500, 'gwei'),
            privacy_mode=config.get('mev', {}).get('privacy_mode', True),
            slippage_buffer=Decimal(str(config.get('mev', {}).get('slippage_buffer', '0.005'))),
            block_delay=config.get('mev', {}).get('block_delay', 2)
        )
        
        # État
        self.pending_transactions: Dict[HexStr, Dict] = {}
        self.known_sandwichers: List[str] = []
        self.last_base_fee: int = 0
        self.last_priority_fee: int = 0
    
    async def protect_transaction(self, tx: Dict) -> Dict:
        """
        Protège une transaction contre les attaques MEV.
        
        Args:
            tx: Transaction à protéger
            
        Returns:
            Transaction protégée
        """
        # 1. Optimiser les gas fees
        tx = await self._optimize_gas_fees(tx)
        
        # 2. Ajouter une protection contre le slippage
        tx = self._add_slippage_protection(tx)
        
        # 3. Ajouter une limite de validité
        current_block = await self.web3.eth.block_number
        tx['validUntilBlock'] = current_block + self.config.block_delay
        
        # 4. Utiliser un relayer privé si activé
        if self.config.privacy_mode:
            tx = await self._use_private_relayer(tx)
        
        # 5. Enregistrer la transaction pour surveillance
        self.pending_transactions[tx['hash']] = {
            'original_tx': tx.copy(),
            'timestamp': self.web3.eth.get_block('latest')['timestamp'],
            'block_number': current_block
        }
        
        return tx
    
    async def monitor_transaction(self, tx_hash: HexStr) -> bool:
        """
        Surveille une transaction pour détecter les attaques MEV.
        
        Args:
            tx_hash: Hash de la transaction à surveiller
            
        Returns:
            True si la transaction est sûre, False sinon
        """
        if tx_hash not in self.pending_transactions:
            return True
            
        tx_info = self.pending_transactions[tx_hash]
        
        # 1. Vérifier si la transaction est toujours en attente après trop de blocks
        current_block = await self.web3.eth.block_number
        if current_block - tx_info['block_number'] > self.config.block_delay:
            self.logger.warning(f"Transaction {tx_hash} pending for too long")
            return False
        
        # 2. Détecter les transactions suspectes dans le même block
        receipt = await self.web3.eth.get_transaction_receipt(tx_hash)
        if receipt:
            block = await self.web3.eth.get_block(receipt['blockNumber'], True)
            suspicious = await self._detect_sandwich_attack(tx_hash, block['transactions'])
            if suspicious:
                self.logger.warning(f"Potential sandwich attack detected for {tx_hash}")
                return False
            
            # Nettoyer les données de la transaction
            del self.pending_transactions[tx_hash]
        
        return True
    
    async def _optimize_gas_fees(self, tx: Dict) -> Dict:
        """Optimise les gas fees pour éviter les front-running."""
        # Obtenir le dernier base fee
        latest_block = await self.web3.eth.get_block('latest')
        base_fee = latest_block['baseFeePerGas']
        
        # Calculer le nouveau base fee avec un buffer
        new_base_fee = min(
            int(base_fee * self.config.base_fee_multiplier),
            self.config.max_base_fee
        )
        
        # Calculer le priority fee optimal
        priority_fee = await self._calculate_optimal_priority_fee()
        
        # Mettre à jour les gas fees
        tx['maxFeePerGas'] = new_base_fee + priority_fee
        tx['maxPriorityFeePerGas'] = priority_fee
        
        return tx
    
    def _add_slippage_protection(self, tx: Dict) -> Dict:
        """Ajoute une protection contre le slippage."""
        if 'value' in tx:
            # Pour les swaps, ajouter un buffer au slippage
            min_output = int(tx.get('minOutput', 0))
            if min_output > 0:
                tx['minOutput'] = int(min_output * (1 - self.config.slippage_buffer))
        return tx
    
    async def _use_private_relayer(self, tx: Dict) -> Dict:
        """Utilise un relayer privé pour la transaction."""
        # TODO: Implémenter l'intégration avec un relayer privé
        # Pour l'instant, on ajoute juste un flag
        tx['privateTransaction'] = True
        return tx
    
    async def _calculate_optimal_priority_fee(self) -> int:
        """Calcule le priority fee optimal basé sur l'historique récent."""
        # Obtenir les derniers blocks
        latest_block = await self.web3.eth.block_number
        fees = []
        
        for block_number in range(latest_block - 10, latest_block):
            block = await self.web3.eth.get_block(block_number, True)
            for tx in block['transactions']:
                if 'maxPriorityFeePerGas' in tx:
                    fees.append(tx['maxPriorityFeePerGas'])
        
        if not fees:
            return self.config.min_priority_fee
            
        # Utiliser le 75e percentile
        fees.sort()
        optimal_fee = fees[int(len(fees) * 0.75)]
        
        # Limiter entre min et max
        return min(max(optimal_fee, self.config.min_priority_fee), 
                  self.config.max_priority_fee)
    
    async def _detect_sandwich_attack(self, tx_hash: HexStr, block_txs: List[Dict]) -> bool:
        """
        Détecte les potentielles attaques sandwich.
        
        Une attaque sandwich typique implique:
        1. Une transaction d'achat juste avant notre transaction
        2. Une transaction de vente juste après notre transaction
        Par le même compte ou un compte connu pour faire du sandwich
        """
        our_tx_index = None
        for i, tx in enumerate(block_txs):
            if tx['hash'].hex() == tx_hash:
                our_tx_index = i
                break
                
        if our_tx_index is None:
            return False
            
        # Vérifier les transactions avant et après
        suspicious_before = False
        suspicious_after = False
        
        if our_tx_index > 0:
            before_tx = block_txs[our_tx_index - 1]
            suspicious_before = self._is_suspicious_transaction(before_tx)
            
        if our_tx_index < len(block_txs) - 1:
            after_tx = block_txs[our_tx_index + 1]
            suspicious_after = self._is_suspicious_transaction(after_tx)
            
        # Si on détecte une paire suspecte, ajouter l'adresse à la liste
        if suspicious_before and suspicious_after:
            attacker = block_txs[our_tx_index - 1]['from']
            if attacker not in self.known_sandwichers:
                self.known_sandwichers.append(attacker)
            return True
            
        return False
    
    def _is_suspicious_transaction(self, tx: Dict) -> bool:
        """Vérifie si une transaction est suspecte."""
        # Vérifier si l'adresse est connue pour faire du sandwich
        if tx['from'] in self.known_sandwichers:
            return True
            
        # Vérifier les gas fees (souvent élevés pour les sandwiches)
        if 'maxFeePerGas' in tx and tx['maxFeePerGas'] > self.config.max_base_fee:
            return True
            
        # Vérifier si c'est un swap (interaction avec un DEX)
        if tx.get('input', '0x') != '0x' and len(tx['input']) >= 10:
            # Les 4 premiers bytes sont la signature de la fonction
            function_signature = tx['input'][:10]
            # Liste des signatures communes pour les swaps
            swap_signatures = [
                '0x38ed1739',  # swapExactTokensForTokens
                '0x7ff36ab5',  # swapExactETHForTokens
                '0x18cbafe5'   # swapExactTokensForETH
            ]
            if function_signature in swap_signatures:
                return True
                
        return False 