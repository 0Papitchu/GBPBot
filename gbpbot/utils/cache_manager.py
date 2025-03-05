"""
Module de gestion du cache pour GBPBot
Ce module fournit des fonctionnalités de mise en cache pour optimiser les performances
"""

import time
import functools
from typing import Dict, List, Optional, Tuple, Any, Callable
from loguru import logger
from gbpbot.config.config_manager import config_manager

class CacheManager:
    """
    Gestionnaire de cache pour stocker les résultats des requêtes RPC et autres données
    """
    
    _instance = None
    
    def __new__(cls):
        """Implémentation du pattern Singleton"""
        if cls._instance is None:
            cls._instance = super(CacheManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """
        Initialise le gestionnaire de cache
        """
        if not hasattr(self, 'initialized'):
            # Charger la configuration du cache
            self.config = config_manager.get_config("cache")
            
            # Initialiser les caches
            self.rpc_cache = {}
            self.price_cache = {}
            self.contract_cache = {}
            
            # Statistiques du cache
            self.stats = {
                "rpc_hits": 0,
                "rpc_misses": 0,
                "price_hits": 0,
                "price_misses": 0,
                "contract_hits": 0,
                "contract_misses": 0,
                "total_items": 0,
                "expired_items": 0,
                "evicted_items": 0
            }
            
            # Marquer comme initialisé
            self.initialized = True
            logger.info("Gestionnaire de cache initialisé")
    
    def get_rpc_result(self, key: str) -> Optional[Any]:
        """
        Récupère un résultat RPC du cache
        
        Args:
            key: Clé du cache
            
        Returns:
            Any: Résultat en cache, None si non trouvé ou expiré
        """
        # Vérifier si la clé existe
        if key not in self.rpc_cache:
            self.stats["rpc_misses"] += 1
            return None
        
        # Récupérer l'entrée du cache
        entry = self.rpc_cache[key]
        
        # Vérifier si l'entrée est expirée
        current_time = time.time()
        if current_time > entry["expires_at"]:
            # Supprimer l'entrée expirée
            del self.rpc_cache[key]
            self.stats["expired_items"] += 1
            self.stats["rpc_misses"] += 1
            return None
        
        # Mettre à jour les statistiques
        self.stats["rpc_hits"] += 1
        
        # Retourner la valeur
        return entry["value"]
    
    def set_rpc_result(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Stocke un résultat RPC dans le cache
        
        Args:
            key: Clé du cache
            value: Valeur à stocker
            ttl: Durée de vie en secondes (None pour utiliser la valeur par défaut)
        """
        # Utiliser le TTL par défaut si non spécifié
        if ttl is None:
            ttl = self.config["rpc_ttl"]
        
        # Calculer la date d'expiration
        expires_at = time.time() + ttl
        
        # Stocker l'entrée
        self.rpc_cache[key] = {
            "value": value,
            "created_at": time.time(),
            "expires_at": expires_at
        }
        
        # Mettre à jour les statistiques
        if key not in self.rpc_cache:
            self.stats["total_items"] += 1
        
        # Vérifier si le cache doit être nettoyé
        if len(self.rpc_cache) > self.config["max_rpc_items"]:
            self._evict_oldest_entries(self.rpc_cache, 
                                      int(self.config["max_rpc_items"] * 0.2))
    
    def get_price(self, symbol: str) -> Optional[float]:
        """
        Récupère un prix du cache
        
        Args:
            symbol: Symbole du token
            
        Returns:
            float: Prix en cache, None si non trouvé ou expiré
        """
        # Vérifier si la clé existe
        if symbol not in self.price_cache:
            self.stats["price_misses"] += 1
            return None
        
        # Récupérer l'entrée du cache
        entry = self.price_cache[symbol]
        
        # Vérifier si l'entrée est expirée
        current_time = time.time()
        if current_time > entry["expires_at"]:
            # Supprimer l'entrée expirée
            del self.price_cache[symbol]
            self.stats["expired_items"] += 1
            self.stats["price_misses"] += 1
            return None
        
        # Mettre à jour les statistiques
        self.stats["price_hits"] += 1
        
        # Retourner la valeur
        return entry["value"]
    
    def set_price(self, symbol: str, price: float, ttl: Optional[int] = None) -> None:
        """
        Stocke un prix dans le cache
        
        Args:
            symbol: Symbole du token
            price: Prix à stocker
            ttl: Durée de vie en secondes (None pour utiliser la valeur par défaut)
        """
        # Utiliser le TTL par défaut si non spécifié
        if ttl is None:
            ttl = self.config["price_ttl"]
        
        # Calculer la date d'expiration
        expires_at = time.time() + ttl
        
        # Stocker l'entrée
        self.price_cache[symbol] = {
            "value": price,
            "created_at": time.time(),
            "expires_at": expires_at
        }
        
        # Mettre à jour les statistiques
        if symbol not in self.price_cache:
            self.stats["total_items"] += 1
        
        # Vérifier si le cache doit être nettoyé
        if len(self.price_cache) > self.config["max_price_items"]:
            self._evict_oldest_entries(self.price_cache, 
                                      int(self.config["max_price_items"] * 0.2))
    
    def get_contract(self, address: str) -> Optional[Any]:
        """
        Récupère un contrat du cache
        
        Args:
            address: Adresse du contrat
            
        Returns:
            Any: Contrat en cache, None si non trouvé
        """
        # Les contrats n'expirent pas, ils sont valides pour toute la durée de vie du bot
        if address not in self.contract_cache:
            self.stats["contract_misses"] += 1
            return None
        
        # Mettre à jour les statistiques
        self.stats["contract_hits"] += 1
        
        # Retourner la valeur
        return self.contract_cache[address]["value"]
    
    def set_contract(self, address: str, contract: Any) -> None:
        """
        Stocke un contrat dans le cache
        
        Args:
            address: Adresse du contrat
            contract: Contrat à stocker
        """
        # Stocker l'entrée
        self.contract_cache[address] = {
            "value": contract,
            "created_at": time.time()
        }
        
        # Mettre à jour les statistiques
        if address not in self.contract_cache:
            self.stats["total_items"] += 1
    
    def _evict_oldest_entries(self, cache: Dict, count: int) -> None:
        """
        Supprime les entrées les plus anciennes du cache
        
        Args:
            cache: Cache à nettoyer
            count: Nombre d'entrées à supprimer
        """
        # Trier les entrées par date de création
        sorted_entries = sorted(
            cache.items(),
            key=lambda x: x[1]["created_at"]
        )
        
        # Supprimer les entrées les plus anciennes
        for i in range(min(count, len(sorted_entries))):
            key = sorted_entries[i][0]
            del cache[key]
            self.stats["evicted_items"] += 1
        
        logger.debug(f"{count} entrées supprimées du cache")
    
    def clear_cache(self, cache_type: Optional[str] = None) -> None:
        """
        Vide le cache
        
        Args:
            cache_type: Type de cache à vider (rpc, price, contract, None pour tous)
        """
        if cache_type is None or cache_type == "rpc":
            self.rpc_cache.clear()
            logger.info("Cache RPC vidé")
        
        if cache_type is None or cache_type == "price":
            self.price_cache.clear()
            logger.info("Cache de prix vidé")
        
        if cache_type is None or cache_type == "contract":
            self.contract_cache.clear()
            logger.info("Cache de contrats vidé")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Récupère les statistiques du cache
        
        Returns:
            Dict: Statistiques du cache
        """
        # Calculer les taux de hit
        total_rpc = self.stats["rpc_hits"] + self.stats["rpc_misses"]
        total_price = self.stats["price_hits"] + self.stats["price_misses"]
        total_contract = self.stats["contract_hits"] + self.stats["contract_misses"]
        
        rpc_hit_rate = (self.stats["rpc_hits"] / max(1, total_rpc)) * 100
        price_hit_rate = (self.stats["price_hits"] / max(1, total_price)) * 100
        contract_hit_rate = (self.stats["contract_hits"] / max(1, total_contract)) * 100
        
        # Calculer la taille actuelle du cache
        current_size = {
            "rpc": len(self.rpc_cache),
            "price": len(self.price_cache),
            "contract": len(self.contract_cache),
            "total": len(self.rpc_cache) + len(self.price_cache) + len(self.contract_cache)
        }
        
        return {
            "hit_rates": {
                "rpc": rpc_hit_rate,
                "price": price_hit_rate,
                "contract": contract_hit_rate
            },
            "hits": {
                "rpc": self.stats["rpc_hits"],
                "price": self.stats["price_hits"],
                "contract": self.stats["contract_hits"],
                "total": self.stats["rpc_hits"] + self.stats["price_hits"] + self.stats["contract_hits"]
            },
            "misses": {
                "rpc": self.stats["rpc_misses"],
                "price": self.stats["price_misses"],
                "contract": self.stats["contract_misses"],
                "total": self.stats["rpc_misses"] + self.stats["price_misses"] + self.stats["contract_misses"]
            },
            "current_size": current_size,
            "evicted_items": self.stats["evicted_items"],
            "expired_items": self.stats["expired_items"]
        }

def cache_rpc_result(func):
    """
    Décorateur pour mettre en cache les résultats des fonctions RPC
    
    Args:
        func: Fonction à décorer
        
    Returns:
        Callable: Fonction décorée
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        # Générer une clé de cache basée sur la fonction et ses arguments
        cache_key = f"{func.__name__}_{str(args)}_{str(kwargs)}"
        
        # Vérifier si le résultat est en cache
        cached_result = cache_manager.get_rpc_result(cache_key)
        if cached_result is not None:
            return cached_result
        
        # Exécuter la fonction
        result = await func(*args, **kwargs)
        
        # Mettre le résultat en cache
        cache_manager.set_rpc_result(cache_key, result)
        
        return result
    
    return wrapper

# Créer une instance singleton
cache_manager = CacheManager() 