"""
Module de cache distribué pour GBPBot
=====================================

Ce module implémente un système de cache distribué pour partager des données entre
plusieurs instances ou processus du GBPBot. Il permet d'optimiser les performances
en évitant de dupliquer les requêtes et les calculs coûteux.

Le cache distribué peut fonctionner en mode local (pour les processus sur la même machine)
ou en mode réseau (pour les instances distribuées sur plusieurs machines).
"""

import os
import time
import pickle
import threading
import tempfile
import logging
from typing import Dict, Optional, Any, TypeVar
from pathlib import Path

# Import conditionnel de Redis
try:
    import redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False
    redis = None

from gbpbot.config.config_manager import config_manager

# Configuration du logger
logger = logging.getLogger("gbpbot.utils.distributed_cache")

# Type générique pour la méthode singleton
T = TypeVar('T', bound='DistributedCacheManager')

class RedisConnectionError(Exception):
    """Exception levée quand la connexion Redis échoue"""
    pass

class CacheWriteError(Exception):
    """Exception levée quand l'écriture dans le cache échoue"""
    pass

class CacheReadError(Exception):
    """Exception levée quand la lecture du cache échoue"""
    pass

class DistributedCacheManager:
    """
    Gestionnaire de cache distribué pour partager des données entre plusieurs
    instances du GBPBot. Il prend en charge deux modes de fonctionnement:
    
    1. Mode local: utilise des fichiers partagés pour le cache
    2. Mode réseau: utilise Redis pour le cache distribué
    """
    
    _instance = None
    
    def __new__(cls: type[T]) -> T:
        """Implémentation du pattern Singleton"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """
        Initialise le gestionnaire de cache distribué
        """
        if not hasattr(self, 'initialized'):
            # Charger la configuration
            self.config = config_manager.get_config("distributed_cache", {})
            
            # Paramètres par défaut
            self.mode = self.config.get("mode", "local")
            self.local_cache_dir = self.config.get("local_cache_dir", os.path.join(tempfile.gettempdir(), "gbpbot_cache"))
            self.redis_host = self.config.get("redis_host", "localhost")
            self.redis_port = int(self.config.get("redis_port", 6379))
            self.redis_password = self.config.get("redis_password", None)
            self.redis_db = int(self.config.get("redis_db", 0))
            self.prefix = self.config.get("prefix", "gbpbot:")
            self.default_ttl = int(self.config.get("default_ttl", 600))  # 10 minutes
            self.enable_compression = self.config.get("enable_compression", True)
            
            # Statistiques
            self.stats: Dict[str, int] = {
                "hits": 0,
                "misses": 0,
                "sets": 0,
                "evictions": 0,
                "errors": 0
            }
            
            # Instance Redis (si mode réseau)
            self.redis_client = None
            
            # Cache local (utilisé en mode local ou comme cache L1 en mode réseau)
            self.local_cache: Dict[str, Dict[str, Any]] = {}
            
            # Verrou pour les opérations concurrentes
            self.lock = threading.RLock()
            
            # Initialiser le cache
            self._initialize_cache()
            
            # Marquer comme initialisé
            self.initialized = True
            logger.info("Gestionnaire de cache distribué initialisé en mode %s", self.mode)
    
    def _initialize_cache(self) -> None:
        """
        Initialise le cache selon le mode configuré
        """
        if self.mode == "redis":
            # Vérifier que Redis est disponible
            if not HAS_REDIS:
                logger.warning("Module Redis non disponible. Passage en mode local.")
                self.mode = "local"
                self._initialize_local_cache()
                return
                
            try:
                self.redis_client = redis.Redis(
                    host=self.redis_host,
                    port=self.redis_port,
                    password=self.redis_password,
                    db=self.redis_db,
                    decode_responses=False
                )
                # Tester la connexion
                self.redis_client.ping()
                logger.info("Connexion au serveur Redis établie: %s:%s", self.redis_host, self.redis_port)
            except redis.ConnectionError as ce:
                logger.error("Impossible de se connecter au serveur Redis: %s", ce)
                logger.warning("Passage en mode local...")
                self.mode = "local"
                self._initialize_local_cache()
            except redis.RedisError as re:
                logger.error("Erreur Redis: %s", re)
                logger.warning("Passage en mode local...")
                self.mode = "local"
                self._initialize_local_cache()
        else:
            # Mode local (fichiers)
            self._initialize_local_cache()
    
    def _initialize_local_cache(self) -> None:
        """
        Initialise le cache local basé sur des fichiers
        """
        try:
            # Créer le répertoire de cache s'il n'existe pas
            os.makedirs(self.local_cache_dir, exist_ok=True)
            logger.info("Cache local initialisé dans %s", self.local_cache_dir)
            
            # Nettoyer les entrées expirées
            self._clean_expired_entries()
        except PermissionError as pe:
            logger.error("Erreur de permission lors de la création du répertoire de cache: %s", pe)
            # Utiliser un répertoire temporaire alternatif
            self.local_cache_dir = tempfile.mkdtemp(prefix="gbpbot_cache_")
            logger.info("Utilisation du répertoire alternatif: %s", self.local_cache_dir)
        except OSError as ose:
            logger.error("Erreur système lors de l'initialisation du cache local: %s", ose)
    
    def _clean_expired_entries(self) -> None:
        """
        Nettoie les entrées expirées du cache local
        """
        current_time = time.time()
        try:
            # Parcourir tous les fichiers du répertoire de cache
            cache_dir = Path(self.local_cache_dir)
            file_count = 0
            expired_count = 0
            
            for cache_file in cache_dir.glob("*.cache"):
                try:
                    file_count += 1
                    # Extraire l'horodatage d'expiration du nom du fichier
                    # Format: key_exptime.cache
                    file_name = cache_file.stem
                    if "_" in file_name:
                        _, exp_time_str = file_name.rsplit("_", 1)
                        try:
                            exp_time = float(exp_time_str)
                            
                            # Supprimer le fichier s'il est expiré
                            if current_time > exp_time:
                                os.remove(cache_file)
                                expired_count += 1
                                self.stats["evictions"] += 1
                        except ValueError:
                            # Le format d'horodatage est invalide, ignorer
                            pass
                except (OSError, PermissionError) as e:
                    logger.debug("Erreur lors du nettoyage de l'entrée %s: %s", cache_file, e)
            
            logger.debug("Nettoyage terminé: %d fichiers analysés, %d expirés supprimés", file_count, expired_count)
        except OSError as e:
            logger.error("Erreur lors du nettoyage du cache: %s", e)
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Récupère une valeur du cache distribué
        
        Args:
            key: Clé du cache
            default: Valeur par défaut si la clé n'existe pas
            
        Returns:
            Any: Valeur en cache ou valeur par défaut
        """
        if not key:
            logger.warning("Tentative de récupération avec une clé vide")
            return default
            
        prefixed_key = f"{self.prefix}{key}"
        
        try:
            # Vérifier d'abord le cache local (L1)
            if prefixed_key in self.local_cache:
                entry = self.local_cache[prefixed_key]
                current_time = time.time()
                
                # Vérifier si l'entrée est expirée
                if current_time > entry["expires_at"]:
                    # Supprimer l'entrée expirée
                    with self.lock:
                        del self.local_cache[prefixed_key]
                else:
                    # Cache hit au niveau L1
                    self.stats["hits"] += 1
                    return entry["value"]
            
            # Si non trouvé dans le cache L1, vérifier le cache distribué
            if self.mode == "redis" and self.redis_client:
                try:
                    # Récupérer du cache Redis
                    result = self.redis_client.get(prefixed_key)
                    if result:
                        # Désérialiser la valeur
                        try:
                            value = pickle.loads(result)
                            
                            # Stocker dans le cache local pour les futures requêtes
                            ttl = self.redis_client.ttl(prefixed_key)
                            if ttl > 0:
                                expires_at = time.time() + float(ttl)
                                with self.lock:
                                    self.local_cache[prefixed_key] = {
                                        "value": value,
                                        "created_at": time.time(),
                                        "expires_at": expires_at
                                    }
                            
                            self.stats["hits"] += 1
                            return value
                        except pickle.PickleError as pe:
                            logger.error("Erreur lors de la désérialisation: %s", pe)
                            self.stats["errors"] += 1
                except redis.RedisError as re:
                    logger.error("Erreur Redis lors de la récupération de %s: %s", key, re)
                    self.stats["errors"] += 1
            else:
                # Mode local (fichiers)
                cache_file = os.path.join(self.local_cache_dir, f"{prefixed_key}.cache")
                if os.path.exists(cache_file):
                    try:
                        with open(cache_file, "rb") as f:
                            entry = pickle.load(f)
                        
                        # Vérifier si l'entrée est expirée
                        current_time = time.time()
                        if current_time > entry["expires_at"]:
                            # Supprimer l'entrée expirée
                            try:
                                os.remove(cache_file)
                            except OSError:
                                pass
                        else:
                            # Stocker dans le cache local pour les futures requêtes
                            with self.lock:
                                self.local_cache[prefixed_key] = entry
                            
                            self.stats["hits"] += 1
                            return entry["value"]
                    except (OSError, pickle.PickleError) as e:
                        logger.error("Erreur lors de la lecture du fichier cache %s: %s", cache_file, e)
                        self.stats["errors"] += 1
                        
                        # Supprimer le fichier corrompu
                        try:
                            os.remove(cache_file)
                        except OSError:
                            pass
            
            # Cache miss
            self.stats["misses"] += 1
            return default
        
        except Exception as e:
            logger.error("Erreur inattendue lors de la récupération de %s: %s", key, e)
            self.stats["errors"] += 1
            return default
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Stocke une valeur dans le cache distribué
        
        Args:
            key: Clé du cache
            value: Valeur à stocker
            ttl: Durée de vie en secondes (None pour utiliser la valeur par défaut)
            
        Returns:
            bool: True si l'opération a réussi, False sinon
        """
        if not key:
            logger.warning("Tentative de stockage avec une clé vide")
            return False
            
        if ttl is None:
            ttl = self.default_ttl
        
        prefixed_key = f"{self.prefix}{key}"
        expires_at = time.time() + float(ttl)
        
        try:
            # Créer l'entrée de cache
            entry = {
                "value": value,
                "created_at": time.time(),
                "expires_at": expires_at
            }
            
            # Stocker dans le cache local (L1)
            with self.lock:
                self.local_cache[prefixed_key] = entry
            
            # Stocker dans le cache distribué
            if self.mode == "redis" and self.redis_client:
                try:
                    # Sérialiser la valeur
                    serialized_value = pickle.dumps(value)
                    self.redis_client.setex(prefixed_key, int(ttl), serialized_value)
                except pickle.PickleError as pe:
                    logger.error("Erreur lors de la sérialisation: %s", pe)
                    self.stats["errors"] += 1
                    return False
                except redis.RedisError as re:
                    logger.error("Erreur Redis lors du stockage de %s: %s", key, re)
                    self.stats["errors"] += 1
                    return False
            else:
                # Mode local (fichiers)
                cache_file = os.path.join(self.local_cache_dir, f"{prefixed_key}.cache")
                try:
                    with open(cache_file, "wb") as f:
                        pickle.dump(entry, f)
                except (OSError, pickle.PickleError) as e:
                    logger.error("Erreur lors de l'écriture du fichier cache %s: %s", cache_file, e)
                    self.stats["errors"] += 1
                    return False
            
            self.stats["sets"] += 1
            return True
        
        except Exception as e:
            logger.error("Erreur inattendue lors du stockage de %s: %s", key, e)
            self.stats["errors"] += 1
            return False
    
    def delete(self, key: str) -> bool:
        """
        Supprime une valeur du cache distribué
        
        Args:
            key: Clé du cache
            
        Returns:
            bool: True si l'opération a réussi, False sinon
        """
        if not key:
            return False
            
        prefixed_key = f"{self.prefix}{key}"
        
        try:
            # Supprimer du cache local (L1)
            with self.lock:
                if prefixed_key in self.local_cache:
                    del self.local_cache[prefixed_key]
            
            # Supprimer du cache distribué
            if self.mode == "redis" and self.redis_client:
                try:
                    self.redis_client.delete(prefixed_key)
                except redis.RedisError as re:
                    logger.error("Erreur Redis lors de la suppression de %s: %s", key, re)
                    self.stats["errors"] += 1
                    return False
            else:
                # Mode local (fichiers)
                cache_file = os.path.join(self.local_cache_dir, f"{prefixed_key}.cache")
                if os.path.exists(cache_file):
                    try:
                        os.remove(cache_file)
                    except OSError as e:
                        logger.error("Erreur lors de la suppression du fichier %s: %s", cache_file, e)
                        self.stats["errors"] += 1
                        return False
            
            return True
        
        except Exception as e:
            logger.error("Erreur inattendue lors de la suppression de %s: %s", key, e)
            self.stats["errors"] += 1
            return False
    
    def _filter_keys_by_pattern(self, keys: list, pattern: str) -> list:
        """Filtre les clés selon un motif"""
        pattern_prefixed = f"{self.prefix}{pattern}"
        return [k for k in keys if k.startswith(pattern_prefixed)]
    
    def clear(self, pattern: Optional[str] = None) -> bool:
        """
        Vide le cache distribué
        
        Args:
            pattern: Motif pour filtrer les clés à supprimer (None pour tout supprimer)
            
        Returns:
            bool: True si l'opération a réussi, False sinon
        """
        try:
            # Vider le cache local (L1)
            with self.lock:
                if pattern:
                    # Supprimer uniquement les clés correspondant au motif
                    keys_to_delete = self._filter_keys_by_pattern(list(self.local_cache.keys()), pattern)
                    for k in keys_to_delete:
                        del self.local_cache[k]
                else:
                    # Vider complètement le cache
                    self.local_cache.clear()
            
            # Vider le cache distribué
            if self.mode == "redis" and self.redis_client:
                try:
                    if pattern:
                        # Supprimer uniquement les clés correspondant au motif
                        pattern_prefixed = f"{self.prefix}{pattern}*"
                        keys = self.redis_client.keys(pattern_prefixed)
                        if keys:
                            self.redis_client.delete(*keys)
                    else:
                        # Supprimer toutes les clés avec le préfixe
                        keys = self.redis_client.keys(f"{self.prefix}*")
                        if keys:
                            self.redis_client.delete(*keys)
                except redis.RedisError as re:
                    logger.error("Erreur Redis lors de la suppression du cache: %s", re)
                    self.stats["errors"] += 1
                    return False
            else:
                # Mode local (fichiers)
                try:
                    cache_dir = Path(self.local_cache_dir)
                    if pattern:
                        # Supprimer uniquement les fichiers correspondant au motif
                        pattern_prefixed = f"{self.prefix}{pattern}"
                        for cache_file in cache_dir.glob("*.cache"):
                            if cache_file.stem.startswith(pattern_prefixed):
                                try:
                                    os.remove(cache_file)
                                except OSError:
                                    pass
                    else:
                        # Supprimer tous les fichiers de cache
                        for cache_file in cache_dir.glob("*.cache"):
                            try:
                                os.remove(cache_file)
                            except OSError:
                                pass
                except OSError as e:
                    logger.error("Erreur lors de la suppression des fichiers de cache: %s", e)
                    self.stats["errors"] += 1
                    return False
            
            return True
        
        except Exception as e:
            logger.error("Erreur inattendue lors de la suppression du cache: %s", e)
            self.stats["errors"] += 1
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Récupère les statistiques du cache
        
        Returns:
            Dict[str, Any]: Statistiques du cache
        """
        stats = self.stats.copy()
        
        # Calculer le taux de hit
        total_requests = stats["hits"] + stats["misses"]
        if total_requests > 0:
            stats["hit_rate"] = (stats["hits"] / total_requests) * 100
        else:
            stats["hit_rate"] = 0.0
        
        # Ajouter des informations sur le mode
        stats["mode"] = self.mode
        
        # Ajouter la taille du cache local
        stats["local_cache_items"] = len(self.local_cache)
        
        # Ajouter des statistiques Redis si disponible
        if self.mode == "redis" and self.redis_client:
            try:
                info = self.redis_client.info()
                stats["redis_used_memory"] = info.get("used_memory_human", "N/A")
                stats["redis_total_keys"] = info.get("db0", {}).get("keys", 0)
                stats["redis_uptime"] = info.get("uptime_in_seconds", 0)
            except redis.RedisError:
                pass
        
        return stats

# Instanciation du gestionnaire de cache distribué
distributed_cache = DistributedCacheManager()

def get_distributed_cache() -> DistributedCacheManager:
    """
    Récupère l'instance du gestionnaire de cache distribué
    
    Returns:
        DistributedCacheManager: Instance du gestionnaire de cache distribué
    """
    return distributed_cache 