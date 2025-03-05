from typing import Dict, List, Optional, Any
import time
from loguru import logger
from web3 import Web3
import asyncio

class MempoolScanner:
    """Scanner de mempool pour détecter les transactions en attente"""
    
    def __init__(self, web3_provider: Optional[Any] = None):
        self.web3 = web3_provider or Web3()
        self.monitored_addresses = set()
        self.monitored_patterns = set()
        self.last_scan_time = 0
        self.scan_interval = 0.5  # 500ms entre les scans
        
    async def scan_mempool(self) -> List[Dict]:
        """Scanne le mempool pour des transactions en attente"""
        try:
            # Limiter la fréquence de scan
            if time.time() - self.last_scan_time < self.scan_interval:
                return []
                
            self.last_scan_time = time.time()
            
            # Implémentation de base pour les tests
            # Dans un environnement réel, cela utiliserait web3.eth.get_pending_transactions()
            return []
            
        except Exception as e:
            logger.error(f"Mempool scanning failed: {str(e)}")
            return []
            
    async def get_pending_transactions(self) -> List[Dict]:
        """Récupère les transactions en attente dans le mempool"""
        try:
            # Implémentation de base pour les tests
            return [
                {
                    "hash": "0x111...",
                    "gasPrice": Web3.to_wei(40, "gwei"),
                    "input": "0x..."  # Données de swap AVAX -> USDC
                },
                {
                    "hash": "0x222...",
                    "gasPrice": Web3.to_wei(45, "gwei"),
                    "input": "0x..."  # Données de swap USDC -> AVAX
                }
            ]
        except Exception as e:
            logger.error(f"Error getting pending transactions: {str(e)}")
            return []
            
    def add_monitored_address(self, address: str) -> None:
        """Ajoute une adresse à surveiller"""
        self.monitored_addresses.add(address.lower())
        
    def add_monitored_pattern(self, pattern: str) -> None:
        """Ajoute un pattern de données à surveiller"""
        self.monitored_patterns.add(pattern)
        
    def is_transaction_interesting(self, tx: Dict) -> bool:
        """Vérifie si une transaction est intéressante selon les critères"""
        try:
            # Vérifier l'adresse
            if tx.get('to', '').lower() in self.monitored_addresses:
                return True
                
            # Vérifier les patterns dans les données
            tx_data = tx.get('input', '')
            for pattern in self.monitored_patterns:
                if pattern in tx_data:
                    return True
                    
            return False
            
        except Exception as e:
            logger.error(f"Error checking transaction interest: {str(e)}")
            return False 