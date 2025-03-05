from typing import Dict, List, Optional
from loguru import logger
import time
import base58
import re
import json

from gbpbot.api_adapters.base_adapter import BaseAPIAdapter

class PumpFunAdapter(BaseAPIAdapter):
    """Adaptateur pour l'API de Pump.fun"""
    
    def __init__(self, config: Dict):
        """
        Initialise l'adaptateur pour Pump.fun
        
        Args:
            config: Configuration de l'adaptateur
        """
        super().__init__(config)
        
        # URL de base de l'API Pump.fun
        self.base_url = "https://pump.fun/api"
        
        # Derniers tokens récupérés (pour ne pas renvoyer les mêmes tokens)
        self.last_token_timestamps = {}
        
        # Paramètres spécifiques
        if "api_adapters" in config and "pump_fun" in config["api_adapters"]:
            pump_config = config["api_adapters"]["pump_fun"]
            self.min_request_interval = pump_config.get("min_request_interval", 2.0)
            self.max_tokens_per_request = pump_config.get("max_tokens_per_request", 50)
            self.min_liquidity = pump_config.get("min_liquidity", 1000)  # En dollars
        else:
            # Valeurs par défaut
            self.min_request_interval = 2.0
            self.max_tokens_per_request = 50
            self.min_liquidity = 1000
            
        logger.info(f"✅ Adaptateur Pump.fun initialisé (intervalle: {self.min_request_interval}s)")
    
    def _get_headers(self) -> Dict[str, str]:
        """Retourne les headers HTTP pour les requêtes à Pump.fun"""
        headers = super()._get_headers()
        headers.update({
            "Origin": "https://pump.fun",
            "Referer": "https://pump.fun/",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        })
        return headers
        
    async def get_new_tokens(self) -> List[Dict]:
        """
        Récupère les nouveaux tokens sur Pump.fun
        
        Returns:
            List[Dict]: Liste des nouveaux tokens
        """
        try:
            # URL pour récupérer les derniers tokens listés
            url = f"{self.base_url}/tokens/list"
            
            params = {
                "sortBy": "createdAt",  # Trier par date de création
                "order": "desc",        # Ordre décroissant (plus récent en premier)
                "limit": self.max_tokens_per_request,
                "offset": 0
            }
            
            # Effectuer la requête
            response = await self._make_request("GET", url, params=params)
            
            # Traiter la réponse
            if "data" not in response or not isinstance(response["data"], list):
                logger.error(f"❌ Format de réponse inattendu de Pump.fun: {response}")
                return []
                
            # Filtrer les nouveaux tokens et ceux qui ont suffisamment de liquidité
            new_tokens = []
            current_time = time.time()
            
            for token in response["data"]:
                token_address = token.get("mintAddress")
                if not token_address:
                    continue
                    
                # Vérifier si on a déjà vu ce token
                if token_address in self.last_token_timestamps:
                    continue
                    
                # Mettre à jour le timestamp
                self.last_token_timestamps[token_address] = current_time
                
                # Vérifier la liquidité
                liquidity = token.get("liquidity", 0)
                if liquidity < self.min_liquidity:
                    logger.debug(f"⚠️ Token {token_address} ignoré (liquidité insuffisante: ${liquidity})")
                    continue
                
                # Format standardisé
                new_token = {
                    "address": token_address,
                    "name": token.get("name", "Unknown"),
                    "symbol": token.get("symbol", "UNKNOWN"),
                    "blockchain": "solana",
                    "created_at": token.get("createdAt"),
                    "liquidity": liquidity,
                    "volume_24h": token.get("volume24h", 0),
                    "price": token.get("price", 0),
                    "market_cap": token.get("marketCap", 0),
                    "total_supply": token.get("totalSupply", 0),
                    "holders_count": token.get("holderCount", 0),
                    "source": "pump_fun",
                    "raw_data": token  # Données brutes pour analyse ultérieure
                }
                
                new_tokens.append(new_token)
                
            if new_tokens:
                logger.info(f"✅ {len(new_tokens)} nouveaux tokens détectés sur Pump.fun")
            
            # Ne garder que les 1000 derniers tokens pour éviter une fuite de mémoire
            if len(self.last_token_timestamps) > 1000:
                oldest_tokens = sorted(self.last_token_timestamps.items(), key=lambda x: x[1])[:500]
                for token_addr, _ in oldest_tokens:
                    del self.last_token_timestamps[token_addr]
                
            return new_tokens
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la récupération des tokens sur Pump.fun: {str(e)}")
            return []
            
    async def get_token_info(self, token_address: str) -> Dict:
        """
        Récupère les informations détaillées sur un token
        
        Args:
            token_address: Adresse du token sur Solana
            
        Returns:
            Dict: Informations détaillées sur le token
        """
        try:
            # URL pour récupérer les détails d'un token
            url = f"{self.base_url}/tokens/{token_address}"
            
            # Effectuer la requête
            response = await self._make_request("GET", url)
            
            # Vérifier si la réponse contient les données attendues
            if "data" not in response:
                logger.error(f"❌ Format de réponse inattendu pour le token {token_address}: {response}")
                return {}
                
            token_data = response["data"]
            
            # Format standardisé
            return {
                "address": token_address,
                "name": token_data.get("name", "Unknown"),
                "symbol": token_data.get("symbol", "UNKNOWN"),
                "blockchain": "solana",
                "created_at": token_data.get("createdAt"),
                "liquidity": token_data.get("liquidity", 0),
                "volume_24h": token_data.get("volume24h", 0),
                "price": token_data.get("price", 0),
                "market_cap": token_data.get("marketCap", 0),
                "total_supply": token_data.get("totalSupply", 0),
                "holders_count": token_data.get("holderCount", 0),
                "twitter": token_data.get("twitter", ""),
                "website": token_data.get("website", ""),
                "telegram": token_data.get("telegram", ""),
                "description": token_data.get("description", ""),
                "verified": token_data.get("verified", False),
                "source": "pump_fun",
                "raw_data": token_data
            }
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la récupération des infos sur le token {token_address}: {str(e)}")
            return {}
            
    async def get_chart_data(self, token_address: str, time_frame: str = "1d") -> List[Dict]:
        """
        Récupère les données de chart pour un token
        
        Args:
            token_address: Adresse du token
            time_frame: Intervalle de temps ("1h", "1d", "1w", "1m", "all")
            
        Returns:
            List[Dict]: Données du chart (liste de points)
        """
        try:
            # URL pour récupérer les données de chart
            url = f"{self.base_url}/tokens/{token_address}/chart"
            
            params = {
                "timeFrame": time_frame
            }
            
            # Effectuer la requête
            response = await self._make_request("GET", url, params=params)
            
            # Vérifier si la réponse contient les données attendues
            if "data" not in response:
                logger.error(f"❌ Format de réponse inattendu pour le chart du token {token_address}: {response}")
                return []
                
            # Format: {timestamp, price, volume}
            return response["data"]
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la récupération des données de chart pour {token_address}: {str(e)}")
            return []
            
    async def search_tokens(self, query: str) -> List[Dict]:
        """
        Recherche des tokens sur Pump.fun
        
        Args:
            query: Terme de recherche
            
        Returns:
            List[Dict]: Liste des tokens correspondant à la recherche
        """
        try:
            # URL pour la recherche
            url = f"{self.base_url}/tokens/search"
            
            params = {
                "query": query,
                "limit": 20
            }
            
            # Effectuer la requête
            response = await self._make_request("GET", url, params=params)
            
            # Vérifier si la réponse contient les données attendues
            if "data" not in response or not isinstance(response["data"], list):
                logger.error(f"❌ Format de réponse inattendu pour la recherche: {response}")
                return []
                
            # Formater les résultats
            result = []
            for token in response["data"]:
                result.append({
                    "address": token.get("mintAddress", ""),
                    "name": token.get("name", "Unknown"),
                    "symbol": token.get("symbol", "UNKNOWN"),
                    "price": token.get("price", 0),
                    "market_cap": token.get("marketCap", 0),
                    "liquidity": token.get("liquidity", 0)
                })
                
            return result
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de la recherche de tokens: {str(e)}")
            return [] 