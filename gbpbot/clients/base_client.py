#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Client Blockchain de Base pour GBPBot
====================================

Définit l'interface commune à tous les clients blockchain spécifiques,
avec les méthodes abstraites que chaque implémentation doit fournir.
"""

import logging
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union, Tuple

logger = logging.getLogger("gbpbot.clients")

class BaseBlockchainClient(ABC):
    """
    Classe abstraite définissant l'interface commune pour tous les clients blockchain.
    
    Chaque blockchain supportée (Solana, Avalanche, etc.) doit implémenter cette interface
    pour assurer une intégration cohérente avec les modules de trading de GBPBot.
    """
    
    def __init__(
        self, 
        rpc_url: str, 
        private_key: Optional[str] = None,
        alternative_rpcs: Optional[List[str]] = None,
        timeout: int = 60,
    ):
        """
        Initialise un client blockchain.
        
        Args:
            rpc_url: URL du point d'accès RPC principal
            private_key: Clé privée du wallet à utiliser (optionnelle)
            alternative_rpcs: Liste d'URLs RPC alternatives à utiliser en cas d'échec
            timeout: Délai d'expiration des requêtes en secondes
        """
        self.rpc_url = rpc_url
        self.private_key = private_key
        self.alternative_rpcs = alternative_rpcs or []
        self.timeout = timeout
        self._connection = None
        self._wallet = None
        
        # Statistiques et métriques
        self.request_count = 0
        self.failed_requests = 0
        self.last_error = None
        self.connected = False
        
        # Cache
        self._token_cache = {}
        self._pair_cache = {}
        self._dex_cache = {}
        
        # Configuration des limites
        self.rate_limit = 100  # Requêtes par seconde
        self.concurrent_requests_limit = 20
        self._request_semaphore = asyncio.Semaphore(self.concurrent_requests_limit)
        
        logger.info(f"Client blockchain initialisé pour {self.__class__.__name__}")
    
    @abstractmethod
    async def connect(self) -> bool:
        """
        Établit une connexion avec la blockchain.
        
        Returns:
            bool: True si la connexion est établie avec succès
        """
        pass
    
    @abstractmethod
    async def disconnect(self) -> None:
        """Ferme la connexion avec la blockchain."""
        pass
    
    @abstractmethod
    async def get_balance(self, address: Optional[str] = None) -> float:
        """
        Récupère le solde d'une adresse.
        
        Args:
            address: Adresse du wallet (utilise le wallet principal si None)
            
        Returns:
            float: Solde en tokens natifs
        """
        pass
    
    @abstractmethod
    async def get_token_balance(self, token_address: str, wallet_address: Optional[str] = None) -> float:
        """
        Récupère le solde d'un token spécifique.
        
        Args:
            token_address: Adresse du contrat du token
            wallet_address: Adresse du wallet (utilise le wallet principal si None)
            
        Returns:
            float: Solde du token
        """
        pass
    
    @abstractmethod
    async def get_token_info(self, token_address: str) -> Dict[str, Any]:
        """
        Récupère les informations sur un token.
        
        Args:
            token_address: Adresse du contrat du token
            
        Returns:
            Dict: Informations sur le token (symbole, nom, décimales, etc.)
        """
        pass
    
    @abstractmethod
    async def get_token_price(self, token_address: str, vs_currency: str = "usd") -> float:
        """
        Récupère le prix actuel d'un token.
        
        Args:
            token_address: Adresse du contrat du token
            vs_currency: Devise de référence (usd, eur, btc, etc.)
            
        Returns:
            float: Prix du token dans la devise spécifiée
        """
        pass
    
    @abstractmethod
    async def buy_token(
        self, 
        token_address: str, 
        amount: float, 
        slippage: float = 1.0,
        deadline: Optional[int] = None,
        dex_address: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Achète un token.
        
        Args:
            token_address: Adresse du contrat du token à acheter
            amount: Montant en tokens natifs à dépenser
            slippage: Pourcentage de slippage autorisé
            deadline: Délai d'expiration de la transaction en secondes
            dex_address: Adresse du DEX à utiliser (optionnel)
            
        Returns:
            Dict: Informations sur la transaction
        """
        pass
    
    @abstractmethod
    async def sell_token(
        self, 
        token_address: str, 
        amount: Optional[float] = None, 
        percent: Optional[float] = None,
        slippage: float = 1.0,
        deadline: Optional[int] = None,
        dex_address: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Vend un token.
        
        Args:
            token_address: Adresse du contrat du token à vendre
            amount: Montant exact de tokens à vendre (si percent est None)
            percent: Pourcentage du solde à vendre (si amount est None)
            slippage: Pourcentage de slippage autorisé
            deadline: Délai d'expiration de la transaction en secondes
            dex_address: Adresse du DEX à utiliser (optionnel)
            
        Returns:
            Dict: Informations sur la transaction
        """
        pass
    
    @abstractmethod
    async def get_pool_info(self, pool_address: str) -> Dict[str, Any]:
        """
        Récupère les informations sur un pool de liquidité.
        
        Args:
            pool_address: Adresse du pool
            
        Returns:
            Dict: Informations sur le pool (tokens, réserves, etc.)
        """
        pass
    
    @abstractmethod
    async def get_transaction_status(self, tx_hash: str) -> Dict[str, Any]:
        """
        Vérifie le statut d'une transaction.
        
        Args:
            tx_hash: Hash de la transaction
            
        Returns:
            Dict: Informations sur le statut de la transaction
        """
        pass
    
    @abstractmethod
    async def simulate_swap(
        self,
        token_in_address: str,
        token_out_address: str,
        amount_in: float,
        dex_address: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Simule un swap entre deux tokens.
        
        Args:
            token_in_address: Adresse du token d'entrée
            token_out_address: Adresse du token de sortie
            amount_in: Montant du token d'entrée
            dex_address: Adresse du DEX à utiliser (optionnel)
            
        Returns:
            Dict: Résultat de la simulation (montant estimé, impact sur le prix, etc.)
        """
        pass
    
    @abstractmethod
    async def get_dexes(self) -> List[Dict[str, Any]]:
        """
        Récupère la liste des DEX disponibles sur la blockchain.
        
        Returns:
            List[Dict]: Liste des DEX avec leurs informations
        """
        pass
    
    @abstractmethod
    async def monitor_new_pools(self, callback: callable) -> None:
        """
        Surveille la création de nouveaux pools de liquidité.
        
        Args:
            callback: Fonction à appeler lorsqu'un nouveau pool est détecté
        """
        pass
    
    @abstractmethod
    async def get_gas_price(self) -> float:
        """
        Récupère le prix actuel du gas.
        
        Returns:
            float: Prix du gas
        """
        pass
    
    @abstractmethod
    async def is_contract(self, address: str) -> bool:
        """
        Vérifie si une adresse est un contrat.
        
        Args:
            address: Adresse à vérifier
            
        Returns:
            bool: True si l'adresse est un contrat
        """
        pass
    
    @abstractmethod
    def get_explorer_url(self, tx_hash: Optional[str] = None, address: Optional[str] = None) -> str:
        """
        Génère une URL vers l'explorateur de blockchain.
        
        Args:
            tx_hash: Hash de transaction (optionnel)
            address: Adresse (optionnelle)
            
        Returns:
            str: URL vers l'explorateur
        """
        pass
    
    async def _handle_request(self, request_func, *args, **kwargs):
        """
        Gère une requête avec gestion des erreurs et rate limiting.
        
        Args:
            request_func: Fonction à appeler
            *args: Arguments pour la fonction
            **kwargs: Arguments nommés pour la fonction
            
        Returns:
            Le résultat de la fonction request_func
        """
        async with self._request_semaphore:
            self.request_count += 1
            try:
                return await request_func(*args, **kwargs)
            except Exception as e:
                self.failed_requests += 1
                self.last_error = str(e)
                logger.error(f"Erreur lors d'une requête blockchain: {e}")
                raise
    
    def clear_cache(self, cache_type: Optional[str] = None) -> None:
        """
        Nettoie le cache.
        
        Args:
            cache_type: Type de cache à nettoyer ('token', 'pair', 'dex' ou None pour tous)
        """
        if cache_type == "token" or cache_type is None:
            self._token_cache.clear()
        if cache_type == "pair" or cache_type is None:
            self._pair_cache.clear()
        if cache_type == "dex" or cache_type is None:
            self._dex_cache.clear()
        
        logger.debug(f"Cache {'complet' if cache_type is None else cache_type} nettoyé")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Récupère les statistiques du client.
        
        Returns:
            Dict: Statistiques du client
        """
        success_rate = 0 if self.request_count == 0 else (self.request_count - self.failed_requests) / self.request_count * 100
        
        return {
            "request_count": self.request_count,
            "failed_requests": self.failed_requests,
            "success_rate": round(success_rate, 2),
            "connected": self.connected,
            "last_error": self.last_error,
        } 