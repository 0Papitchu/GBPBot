"""
Base API Adapter

Defines the base class for all API adapters. This provides common
functionality and a consistent interface for different API services.
"""

import logging
from typing import Dict, List, Optional, Any
from abc import ABC, abstractmethod
from loguru import logger
import aiohttp
import asyncio
import time
import json

class BaseAPIAdapter(ABC):
    """
    Abstract base class for all API adapters.
    All concrete API adapters should inherit from this class.
    """
    
    def __init__(self, config: Dict):
        """
        Initialize the base API adapter
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.session = None
        self.last_request_time = 0
        self.min_request_interval = 1.0  # Intervalle minimum entre les requêtes en secondes
        
    async def initialize(self):
        """Initialise l'adaptateur (crée la session HTTP)"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=30),
                headers=self._get_headers()
            )
        return True
        
    async def close(self):
        """Ferme les ressources utilisées par l'adaptateur"""
        if self.session and not self.session.closed:
            await self.session.close()
            
    def _get_headers(self) -> Dict[str, str]:
        """
        Retourne les headers HTTP à utiliser pour les requêtes
        
        Returns:
            Dict[str, str]: Headers HTTP
        """
        return {
            "User-Agent": "GBPBot/1.0",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        
    async def _make_request(self, method: str, url: str, params: Optional[Dict] = None, 
                          data: Optional[Dict] = None, headers: Optional[Dict] = None) -> Dict:
        """
        Effectue une requête HTTP vers l'API
        
        Args:
            method: Méthode HTTP (GET, POST, etc.)
            url: URL de la requête
            params: Paramètres de requête (pour GET)
            data: Données de la requête (pour POST)
            headers: Headers HTTP additionnels
            
        Returns:
            Dict: Réponse de l'API (parsée en JSON)
            
        Raises:
            Exception: Si la requête échoue
        """
        # Respecter la limite de rate
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.min_request_interval:
            await asyncio.sleep(self.min_request_interval - time_since_last_request)
            
        # Mettre à jour le temps de la dernière requête
        self.last_request_time = time.time()
        
        # Fusionner les headers par défaut avec les headers spécifiques
        merged_headers = self._get_headers()
        if headers:
            merged_headers.update(headers)
            
        try:
            # Initialiser la session si nécessaire
            await self.initialize()
            
            # Effectuer la requête
            async with self.session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                headers=merged_headers
            ) as response:
                # Vérifier le statut de la réponse
                if response.status == 429:  # Too Many Requests
                    retry_after = int(response.headers.get("Retry-After", "5"))
                    logger.warning(f"Rate limit dépassé, attente de {retry_after} secondes")
                    await asyncio.sleep(retry_after)
                    return await self._make_request(method, url, params, data, headers)
                    
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Erreur {response.status}: {error_text}")
                    
                # Parser la réponse JSON
                try:
                    result = await response.json()
                    return result
                except json.JSONDecodeError:
                    text_response = await response.text()
                    raise Exception(f"Impossible de parser la réponse JSON: {text_response}")
                    
        except aiohttp.ClientError as e:
            raise Exception(f"Erreur HTTP: {str(e)}")
            
    @abstractmethod
    async def get_new_tokens(self, **kwargs) -> List[Dict]:
        """
        Get new tokens from the API service
        
        Returns:
            List[Dict]: List of new tokens
        """
        pass
    
    @abstractmethod
    async def get_token_info(self, token_address: str) -> Dict:
        """
        Récupère les informations détaillées sur un token
        
        Args:
            token_address: Adresse du token
            
        Returns:
            Dict: Informations détaillées sur le token
        """
        pass 