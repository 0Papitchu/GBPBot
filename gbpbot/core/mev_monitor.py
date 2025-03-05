"""
Module pour la surveillance et la protection contre les attaques MEV (Miner Extractable Value)
"""

import asyncio
import logging
import time
import statistics
from typing import Dict, List, Optional, Set, Tuple
from web3 import Web3

from gbpbot.core.exceptions import BlockchainError

class MEVMonitor:
    """
    Classe pour surveiller et se protéger contre les attaques MEV
    """
    
    def __init__(self, blockchain_client, logger=None):
        """
        Initialise le moniteur MEV
        
        Args:
            blockchain_client: Client blockchain à utiliser
            logger: Logger à utiliser (optionnel)
        """
        self.blockchain_client = blockchain_client
        self.logger = logger or logging.getLogger(__name__)
        self.suspicious_addresses = set()  # Cache des adresses suspectes
        
    async def monitor_mev_activity(self, 
                              token_addresses: List[str], 
                              time_window_seconds: int = 300,
                              min_transactions: int = 5) -> Dict:
        """
        Surveille l'activité MEV (Miner Extractable Value) pour un ensemble de tokens
        
        Args:
            token_addresses: Liste des adresses de tokens à surveiller
            time_window_seconds: Fenêtre de temps en secondes pour l'analyse
            min_transactions: Nombre minimum de transactions pour considérer une activité suspecte
            
        Returns:
            Dict: Rapport d'activité MEV
        """
        try:
            self.logger.info(f"Surveillance de l'activité MEV pour {len(token_addresses)} tokens")
            
            # Convertir les adresses en format checksum
            token_addresses = [Web3.to_checksum_address(addr) for addr in token_addresses]
            
            # Sélectionner le meilleur RPC
            web3 = self.blockchain_client._select_weighted_provider()
            
            # Obtenir le bloc actuel
            current_block = web3.eth.block_number
            
            # Calculer le bloc de début en fonction de la fenêtre de temps
            # Sur Avalanche, un bloc est produit environ toutes les 2 secondes
            blocks_to_analyze = time_window_seconds // 2
            start_block = max(0, current_block - blocks_to_analyze)
            
            self.logger.info(f"Analyse des blocs {start_block} à {current_block}")
            
            # Stocker les transactions par token
            token_transactions = {token: [] for token in token_addresses}
            
            # Stocker les adresses suspectes pour cette analyse
            current_suspicious_addresses = set()
            
            # Obtenir les routers DEX configurés
            dex_routers = set(Web3.to_checksum_address(router) for router in 
                             self.blockchain_client.config.get("dex_routers", {}).values())
            
            # Analyser les blocs récents
            for block_num in range(start_block, current_block + 1):
                # Obtenir le bloc
                try:
                    block = web3.eth.get_block(block_num, full_transactions=True)
                except Exception as e:
                    self.logger.warning(f"Erreur lors de la récupération du bloc {block_num}: {str(e)}")
                    continue
                
                # Analyser les transactions du bloc
                for tx in block['transactions']:
                    # Vérifier si la transaction est liée à un DEX
                    if tx.get('to') in dex_routers:
                        # Vérifier si la transaction implique l'un des tokens surveillés
                        tx_input = tx.get('input', '')
                        
                        for token in token_addresses:
                            # Rechercher l'adresse du token dans les données de la transaction
                            # Nous recherchons l'adresse sans le préfixe 0x et en minuscules
                            token_hex = token[2:].lower()
                            if token_hex in tx_input.lower():
                                # Ajouter la transaction à la liste pour ce token
                                token_transactions[token].append({
                                    'hash': tx.get('hash').hex(),
                                    'from': tx.get('from'),
                                    'gas_price': tx.get('gasPrice'),
                                    'block_number': block_num,
                                    'timestamp': block.get('timestamp')
                                })
            
            # Analyser les transactions pour détecter les modèles de MEV
            mev_patterns = {}
            
            for token, transactions in token_transactions.items():
                if len(transactions) < min_transactions:
                    continue
                
                # Trier les transactions par bloc et position dans le bloc
                transactions.sort(key=lambda x: (x['block_number'], x['timestamp']))
                
                # Détecter les transactions sandwich (frontrunning + backrunning)
                sandwich_attacks = self._detect_sandwich_attacks(transactions)
                
                # Détecter les transactions avec gas price anormalement élevé
                high_gas_transactions = self._detect_high_gas_transactions(transactions)
                
                # Détecter les adresses qui font plusieurs transactions rapprochées
                frequent_traders = self._detect_frequent_traders(transactions)
                
                # Ajouter les adresses suspectes
                for attack in sandwich_attacks:
                    current_suspicious_addresses.add(attack['frontrun_tx']['from'])
                    current_suspicious_addresses.add(attack['backrun_tx']['from'])
                
                for tx in high_gas_transactions:
                    current_suspicious_addresses.add(tx['from'])
                
                for address, count in frequent_traders.items():
                    if count > 3:  # Seuil arbitraire pour les traders fréquents
                        current_suspicious_addresses.add(address)
                
                # Stocker les résultats pour ce token
                token_symbol = await self._get_token_symbol(token)
                mev_patterns[token] = {
                    'token_address': token,
                    'token_symbol': token_symbol,
                    'total_transactions': len(transactions),
                    'sandwich_attacks': sandwich_attacks,
                    'high_gas_transactions': high_gas_transactions,
                    'frequent_traders': [{'address': addr, 'count': count} 
                                        for addr, count in frequent_traders.items() 
                                        if count > 3]
                }
            
            # Mettre à jour le cache des adresses suspectes
            self.suspicious_addresses.update(current_suspicious_addresses)
            
            # Créer le rapport final
            mev_report = {
                'time_window_seconds': time_window_seconds,
                'blocks_analyzed': current_block - start_block + 1,
                'tokens_monitored': len(token_addresses),
                'suspicious_addresses': list(current_suspicious_addresses),
                'total_suspicious_addresses': len(self.suspicious_addresses),
                'mev_patterns': mev_patterns,
                'timestamp': int(time.time())
            }
            
            self.logger.info(f"Analyse MEV terminée: {len(current_suspicious_addresses)} adresses suspectes détectées")
            return mev_report
            
        except Exception as e:
            self.logger.error(f"Erreur lors de la surveillance MEV: {str(e)}")
            raise BlockchainError(f"Échec de la surveillance MEV: {str(e)}")
    
    def _detect_sandwich_attacks(self, transactions: List[Dict]) -> List[Dict]:
        """
        Détecte les attaques sandwich (frontrunning + backrunning)
        
        Args:
            transactions: Liste des transactions à analyser
            
        Returns:
            List[Dict]: Liste des attaques sandwich détectées
        """
        sandwich_attacks = []
        
        # Regrouper les transactions par bloc
        transactions_by_block = {}
        for tx in transactions:
            block_num = tx['block_number']
            if block_num not in transactions_by_block:
                transactions_by_block[block_num] = []
            transactions_by_block[block_num].append(tx)
        
        # Analyser chaque bloc
        for block_num, block_txs in transactions_by_block.items():
            if len(block_txs) < 3:
                continue
            
            # Trier les transactions par timestamp
            block_txs.sort(key=lambda x: x['timestamp'])
            
            # Rechercher des modèles de sandwich
            for i in range(len(block_txs) - 2):
                # Vérifier si les transactions i et i+2 proviennent de la même adresse
                if block_txs[i]['from'] == block_txs[i+2]['from'] and block_txs[i]['from'] != block_txs[i+1]['from']:
                    # Vérifier si le gas price de i et i+2 est plus élevé que celui de i+1
                    if (block_txs[i]['gas_price'] > block_txs[i+1]['gas_price'] and 
                        block_txs[i+2]['gas_price'] > block_txs[i+1]['gas_price']):
                        sandwich_attacks.append({
                            'block_number': block_num,
                            'frontrun_tx': block_txs[i],
                            'victim_tx': block_txs[i+1],
                            'backrun_tx': block_txs[i+2]
                        })
        
        return sandwich_attacks
    
    def _detect_high_gas_transactions(self, transactions: List[Dict]) -> List[Dict]:
        """
        Détecte les transactions avec un gas price anormalement élevé
        
        Args:
            transactions: Liste des transactions à analyser
            
        Returns:
            List[Dict]: Liste des transactions suspectes
        """
        if not transactions:
            return []
        
        # Calculer le gas price médian
        gas_prices = [tx['gas_price'] for tx in transactions]
        median_gas_price = statistics.median(gas_prices)
        
        # Détecter les transactions avec un gas price 2x supérieur à la médiane
        high_gas_transactions = [tx for tx in transactions if tx['gas_price'] > 2 * median_gas_price]
        
        return high_gas_transactions
    
    def _detect_frequent_traders(self, transactions: List[Dict]) -> Dict[str, int]:
        """
        Détecte les adresses qui font plusieurs transactions rapprochées
        
        Args:
            transactions: Liste des transactions à analyser
            
        Returns:
            Dict[str, int]: Dictionnaire des adresses avec le nombre de transactions
        """
        address_counts = {}
        
        for tx in transactions:
            address = tx['from']
            if address not in address_counts:
                address_counts[address] = 0
            address_counts[address] += 1
        
        return address_counts
    
    async def _get_token_symbol(self, token_address: str) -> str:
        """
        Récupère le symbole d'un token
        
        Args:
            token_address: Adresse du token
            
        Returns:
            str: Symbole du token
        """
        try:
            web3 = self.blockchain_client._select_weighted_provider()
            
            # Ajouter la fonction symbol à l'ABI
            abi = self.blockchain_client._load_erc20_abi() + [{
                "constant": True,
                "inputs": [],
                "name": "symbol",
                "outputs": [{"name": "", "type": "string"}],
                "payable": False,
                "stateMutability": "view",
                "type": "function"
            }]
            
            token_contract = web3.eth.contract(address=token_address, abi=abi)
            symbol = await self.blockchain_client._safe_call_contract_function(token_contract.functions.symbol())
            
            return symbol
        except Exception as e:
            self.logger.warning(f"Erreur lors de la récupération du symbole pour {token_address}: {str(e)}")
            return "UNKNOWN"
    
    def is_address_suspicious(self, address: str) -> bool:
        """
        Vérifie si une adresse est suspecte
        
        Args:
            address: Adresse à vérifier
            
        Returns:
            bool: True si l'adresse est suspecte, False sinon
        """
        return Web3.to_checksum_address(address) in self.suspicious_addresses
    
    async def get_optimal_gas_price(self, base_gas_price: int, protection_level: str = 'medium') -> int:
        """
        Calcule un prix de gas optimal pour éviter le frontrunning
        
        Args:
            base_gas_price: Prix de gas de base
            protection_level: Niveau de protection ('low', 'medium', 'high')
            
        Returns:
            int: Prix de gas optimal
        """
        # Obtenir le prix de gas actuel
        web3 = self.blockchain_client._select_weighted_provider()
        current_gas_price = web3.eth.gas_price
        
        # Appliquer un multiplicateur en fonction du niveau de protection
        if protection_level == 'low':
            multiplier = 1.1  # +10%
        elif protection_level == 'medium':
            multiplier = 1.3  # +30%
        elif protection_level == 'high':
            multiplier = 1.5  # +50%
        else:
            multiplier = 1.2  # +20% par défaut
        
        # Calculer le prix de gas optimal
        optimal_gas_price = max(base_gas_price, int(current_gas_price * multiplier))
        
        return optimal_gas_price
    
    async def protect_transaction(self, 
                                 tx_params: Dict, 
                                 protection_level: str = 'medium',
                                 private_mempool: bool = False) -> Dict:
        """
        Applique des protections anti-MEV à une transaction
        
        Args:
            tx_params: Paramètres de la transaction
            protection_level: Niveau de protection ('low', 'medium', 'high')
            private_mempool: Utiliser un mempool privé si disponible
            
        Returns:
            Dict: Paramètres de transaction modifiés
        """
        # Copier les paramètres pour ne pas modifier l'original
        protected_tx = tx_params.copy()
        
        # Optimiser le prix du gas
        if 'gasPrice' in protected_tx:
            protected_tx['gasPrice'] = await self.get_optimal_gas_price(
                protected_tx['gasPrice'], 
                protection_level
            )
        
        # Ajouter des paramètres pour les mempools privés si nécessaire
        if private_mempool:
            # Ces paramètres dépendent du service de mempool privé utilisé
            # Exemple pour Flashbots
            protected_tx['_flashbots'] = True
            
        return protected_tx 