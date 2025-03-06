#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Factory pour les clients blockchain du GBPBot
=============================================

Ce module fournit une factory pour créer les instances appropriées
de clients blockchain selon la blockchain spécifiée.
"""

import logging
import importlib
from typing import Dict, List, Optional, Any, Union, Type

from gbpbot.clients.base_client import BaseBlockchainClient

logger = logging.getLogger("gbpbot.clients.factory")

class BlockchainClientFactory:
    """
    Factory pour créer des instances de clients blockchain.
    
    Cette classe utilise le pattern Factory pour instancier le client approprié
    en fonction de la blockchain demandée, tout en cachant la complexité
    de l'initialisation spécifique à chaque blockchain.
    """
    
    # Mapping des noms de blockchains vers les classes de clients
    _CLIENT_MAPPING: Dict[str, str] = {
        "solana": "gbpbot.clients.solana_client.SolanaClient",
        "avalanche": "gbpbot.clients.avalanche_client.AvalancheClient",
        "avax": "gbpbot.clients.avalanche_client.AvalancheClient",  # Alias
        "sonic": "gbpbot.clients.sonic_client.SonicClient",
        # Ajoutez d'autres blockchains ici au besoin
    }
    
    # Cache des clients déjà créés (singleton par blockchain)
    _client_instances: Dict[str, BaseBlockchainClient] = {}
    
    @classmethod
    def create_client(
        cls, 
        blockchain: str, 
        rpc_url: str = None, 
        private_key: Optional[str] = None,
        alternative_rpcs: Optional[List[str]] = None,
        use_cache: bool = True,
        **kwargs
    ) -> BaseBlockchainClient:
        """
        Crée ou récupère une instance de client blockchain.
        
        Args:
            blockchain: Nom de la blockchain (solana, avalanche, etc.)
            rpc_url: URL du point d'accès RPC
            private_key: Clé privée du wallet (optionnelle)
            alternative_rpcs: Liste d'URLs RPC alternatives
            use_cache: Si True, utilise une instance en cache si disponible
            **kwargs: Arguments supplémentaires spécifiques au client
            
        Returns:
            Une instance de BaseBlockchainClient pour la blockchain spécifiée
            
        Raises:
            ValueError: Si la blockchain n'est pas supportée
            ImportError: Si le module du client ne peut pas être importé
        """
        blockchain = blockchain.lower()
        
        # Vérifier si une instance existe déjà dans le cache
        cache_key = f"{blockchain}:{rpc_url}"
        if use_cache and cache_key in cls._client_instances:
            logger.debug(f"Utilisation d'une instance de client {blockchain} en cache")
            return cls._client_instances[cache_key]
        
        # Vérifier si la blockchain est supportée
        if blockchain not in cls._CLIENT_MAPPING:
            supported = ", ".join(cls._CLIENT_MAPPING.keys())
            raise ValueError(
                f"Blockchain '{blockchain}' non supportée. "
                f"Blockchains supportées: {supported}"
            )
        
        # Importer dynamiquement la classe du client
        client_path = cls._CLIENT_MAPPING[blockchain]
        module_path, class_name = client_path.rsplit(".", 1)
        
        try:
            module = importlib.import_module(module_path)
            client_class = getattr(module, class_name)
        except (ImportError, AttributeError) as e:
            logger.error(f"Erreur lors de l'import du client {blockchain}: {e}")
            raise ImportError(f"Le client pour '{blockchain}' n'a pas pu être importé: {e}")
        
        # Créer l'instance du client avec les paramètres spécifiés
        try:
            client = client_class(
                rpc_url=rpc_url,
                private_key=private_key,
                alternative_rpcs=alternative_rpcs,
                **kwargs
            )
            
            # Ajouter l'instance au cache si demandé
            if use_cache:
                cls._client_instances[cache_key] = client
            
            logger.info(f"Client {blockchain} créé avec succès")
            return client
        except Exception as e:
            logger.error(f"Erreur lors de la création du client {blockchain}: {e}")
            raise
    
    @classmethod
    def get_supported_blockchains(cls) -> List[str]:
        """
        Récupère la liste des blockchains supportées.
        
        Returns:
            List[str]: Liste des noms de blockchains supportées
        """
        return list(cls._CLIENT_MAPPING.keys())
    
    @classmethod
    def clear_cache(cls, blockchain: Optional[str] = None) -> None:
        """
        Nettoie le cache des instances de clients.
        
        Args:
            blockchain: Nom de la blockchain à nettoyer (None pour toutes)
        """
        if blockchain is None:
            # Nettoyer tout le cache
            cls._client_instances.clear()
            logger.debug("Cache des clients blockchain entièrement nettoyé")
        else:
            # Nettoyer uniquement les instances de la blockchain spécifiée
            blockchain = blockchain.lower()
            keys_to_remove = [k for k in cls._client_instances if k.startswith(f"{blockchain}:")]
            
            for key in keys_to_remove:
                del cls._client_instances[key]
            
            logger.debug(f"Cache des clients {blockchain} nettoyé ({len(keys_to_remove)} instances)") 