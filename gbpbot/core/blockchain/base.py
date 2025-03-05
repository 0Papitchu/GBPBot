"""
Interface de base pour les clients blockchain.

Ce module définit les interfaces abstraites que tous les clients blockchain
doivent implémenter, assurant une API cohérente à travers différentes blockchains.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union


class BaseBlockchainClient(ABC):
    """
    Interface abstraite pour tous les clients blockchain.
    
    Cette classe définit les méthodes que chaque implémentation spécifique
    à une blockchain doit fournir.
    """
    
    @abstractmethod
    async def connect(self) -> bool:
        """
        Établit une connexion avec la blockchain.
        
        Returns:
            bool: True si la connexion est établie avec succès, False sinon
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """
        Ferme la connexion avec la blockchain.
        
        Returns:
            bool: True si la déconnexion est réussie, False sinon
        """
        pass
    
    @abstractmethod
    async def get_balance(self, token_address: str, wallet_address: Optional[str] = None) -> float:
        """
        Récupère le solde d'un token pour un wallet donné.
        
        Args:
            token_address: Adresse du token (ou symbole pour les tokens natifs)
            wallet_address: Adresse du wallet (par défaut: l'adresse du client)
            
        Returns:
            float: Solde du token
        """
        pass
    
    @abstractmethod
    async def get_token_price(self, token_address: str, base_token: Optional[str] = None) -> float:
        """
        Récupère le prix d'un token en termes d'un autre token.
        
        Args:
            token_address: Adresse du token pour lequel obtenir le prix
            base_token: Adresse du token de base (par défaut: token natif de la blockchain)
            
        Returns:
            float: Prix du token
        """
        pass
    
    @abstractmethod
    async def execute_transaction(self, tx_params: Dict) -> Dict:
        """
        Exécute une transaction sur la blockchain.
        
        Args:
            tx_params: Paramètres de la transaction
            
        Returns:
            Dict: Résultat de la transaction
        """
        pass
    
    @abstractmethod
    async def execute_swap(self, token_in: str, token_out: str, amount_in: float, 
                          slippage: float = 0.5, deadline_seconds: int = 300,
                          gas_priority: str = "normal") -> Dict:
        """
        Exécute un swap de tokens.
        
        Args:
            token_in: Adresse du token d'entrée
            token_out: Adresse du token de sortie
            amount_in: Montant du token d'entrée à échanger
            slippage: Pourcentage de slippage maximum autorisé
            deadline_seconds: Délai d'expiration de la transaction en secondes
            gas_priority: Priorité pour les frais de gas ('slow', 'normal', 'fast')
            
        Returns:
            Dict: Résultat du swap
        """
        pass
    
    @abstractmethod
    async def check_token_approval(self, token_address: str, spender_address: str, amount: Optional[int] = None) -> bool:
        """
        Vérifie si un token est approuvé pour un spender.
        
        Args:
            token_address: Adresse du token
            spender_address: Adresse du spender
            amount: Montant à vérifier l'approbation pour (par défaut: None, vérifie toute approbation)
            
        Returns:
            bool: True si le token est approuvé, False sinon
        """
        pass
    
    @abstractmethod
    async def approve_token(self, token_address: str, spender_address: str, amount: int, 
                           gas_priority: str = "normal") -> Dict:
        """
        Approuve un token pour un spender.
        
        Args:
            token_address: Adresse du token
            spender_address: Adresse du spender
            amount: Montant à approuver
            gas_priority: Priorité pour les frais de gas
            
        Returns:
            Dict: Résultat de la transaction d'approbation
        """
        pass
    
    @abstractmethod
    async def wait_for_transaction(self, tx_hash: str, timeout_seconds: int = 60) -> Dict:
        """
        Attend la confirmation d'une transaction.
        
        Args:
            tx_hash: Hash de la transaction
            timeout_seconds: Délai d'attente maximum en secondes
            
        Returns:
            Dict: Détails de la transaction confirmée
        """
        pass
    
    @abstractmethod
    async def get_transaction_status(self, tx_hash: str) -> Dict:
        """
        Récupère le statut d'une transaction.
        
        Args:
            tx_hash: Hash de la transaction
            
        Returns:
            Dict: Statut de la transaction
        """
        pass


class BlockchainClientFactory:
    """
    Factory pour créer des instances de clients blockchain.
    """
    
    @staticmethod
    def get_client(blockchain_type: str, config: Dict) -> BaseBlockchainClient:
        """
        Crée et retourne une instance du client blockchain approprié.
        
        Args:
            blockchain_type: Type de blockchain ('ethereum', 'solana', 'polygon', 'avalanche', 'arbitrum', etc.)
            config: Configuration pour le client
            
        Returns:
            BaseBlockchainClient: Instance du client blockchain
            
        Raises:
            ValueError: Si le type de blockchain n'est pas supporté
        """
        blockchain_type = blockchain_type.lower()
        
        if blockchain_type == "ethereum":
            from gbpbot.core.blockchain.ethereum import EthereumClient
            return EthereumClient(config)
        elif blockchain_type in ["polygon", "avalanche", "arbitrum", "optimism", "bsc"]:
            # These are EVM-compatible chains, so we can use the Ethereum client
            from gbpbot.core.blockchain.ethereum import EthereumClient
            return EthereumClient(config)
        elif blockchain_type == "solana":
            from gbpbot.core.blockchain.solana import SolanaClient
            return SolanaClient(config)
        else:
            from gbpbot.utils.exceptions import UnsupportedBlockchainError
            raise UnsupportedBlockchainError(f"Unsupported blockchain type: {blockchain_type}") 