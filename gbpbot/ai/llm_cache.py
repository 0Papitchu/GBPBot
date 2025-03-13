#!/usr/bin/env python
"""
Cache intelligent pour les modèles LLM et résultats d'analyse - GBPBot

Ce module fournit un système de cache optimisé pour stocker et récupérer 
efficacement les résultats d'analyse et les réponses des modèles LLM,
réduisant ainsi les appels API et améliorant les performances.
"""

import os
import json
import time
import hashlib
import logging
from typing import Any, Dict, Optional, Union, List, Tuple
from pathlib import Path
from datetime import datetime, timedelta
import threading
import sqlite3
from dataclasses import dataclass, field, asdict
import asyncio

from gbpbot.utils.logger import setup_logger

# Configuration du logger
logger = setup_logger("llm_cache", logging.INFO)

@dataclass
class CacheEntry:
    """Entrée de cache avec métadonnées complètes."""
    query: str
    result: Any
    timestamp: float = field(default_factory=time.time)
    model: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    expiration: Optional[float] = None
    priority: int = 0  # Plus la priorité est élevée, plus l'entrée est importante
    hit_count: int = 0  # Nombre de fois où cette entrée a été consultée
    
    def is_expired(self) -> bool:
        """Vérifie si l'entrée est expirée."""
        if self.expiration is None:
            return False
        return time.time() > self.expiration
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'entrée en dictionnaire pour le stockage."""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CacheEntry":
        """Crée une entrée de cache à partir d'un dictionnaire."""
        return cls(**data)

class LLMCache:
    """
    Cache intelligent pour les réponses des modèles LLM et résultats d'analyse.
    
    Caractéristiques:
    - Stratégies d'expiration variables (TTL, LRU, priorité)
    - Cache multi-niveaux (mémoire, disque)
    - Versionnement sémantique des entrées de cache
    - Prise en compte du contexte pour la similarité des requêtes
    - Optimisation automatique basée sur les hits/miss
    """
    
    def __init__(
        self, 
        cache_dir: Optional[str] = None,
        max_memory_entries: int = 1000,
        max_disk_entries: int = 10000,
        default_ttl: int = 3600,  # 1 heure en secondes
        similarity_threshold: float = 0.85,
        enable_semantic_matching: bool = True,
    ):
        """
        Initialise le cache intelligent.
        
        Args:
            cache_dir: Répertoire pour le stockage persistant du cache.
            max_memory_entries: Nombre maximum d'entrées en mémoire.
            max_disk_entries: Nombre maximum d'entrées sur disque.
            default_ttl: Durée de vie par défaut des entrées (en secondes).
            similarity_threshold: Seuil pour considérer deux requêtes similaires (0.0-1.0).
            enable_semantic_matching: Activer la correspondance sémantique des requêtes.
        """
        # Paramètres de configuration
        self.cache_dir = cache_dir or os.path.join(str(Path.home()), ".gbpbot", "cache")
        self.max_memory_entries = max_memory_entries
        self.max_disk_entries = max_disk_entries
        self.default_ttl = default_ttl
        self.similarity_threshold = similarity_threshold
        self.enable_semantic_matching = enable_semantic_matching
        
        # Créer le répertoire de cache s'il n'existe pas
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Cache en mémoire (pour les accès rapides)
        self.memory_cache: Dict[str, CacheEntry] = {}
        
        # Base de données SQLite pour le stockage persistant
        self.db_path = os.path.join(self.cache_dir, "llm_cache.db")
        self._init_db()
        
        # Statistiques
        self.stats = {
            "hits": 0,
            "misses": 0,
            "memory_hits": 0,
            "disk_hits": 0,
            "semantic_hits": 0,
            "evictions": 0,
            "insertions": 0,
            "updates": 0
        }
        
        # Verrou pour accès concurrent
        self._lock = threading.RLock()
        
        # Démarrer le thread d'optimisation périodique
        self._start_optimization_thread()
        
        logger.info(f"Cache LLM initialisé: {self.cache_dir}")
    
    def _init_db(self) -> None:
        """Initialise la base de données SQLite pour le stockage persistant."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Créer la table principale pour les entrées de cache
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS cache_entries (
                key TEXT PRIMARY KEY,
                query TEXT NOT NULL,
                result TEXT NOT NULL,
                timestamp REAL NOT NULL,
                model TEXT,
                parameters TEXT,
                context TEXT,
                expiration REAL,
                priority INTEGER DEFAULT 0,
                hit_count INTEGER DEFAULT 0
            )
            ''')
            
            # Index pour améliorer les performances
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON cache_entries (timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_expiration ON cache_entries (expiration)')
            
            # Créer la table pour les statistiques
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS cache_stats (
                name TEXT PRIMARY KEY,
                value INTEGER DEFAULT 0
            )
            ''')
            
            conn.commit()
            conn.close()
            logger.debug("Base de données de cache initialisée")
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation de la base de données: {str(e)}")
    
    def _compute_key(self, query: str, model: str = "", params: Dict[str, Any] = None) -> str:
        """
        Calcule une clé unique pour la requête.
        
        Args:
            query: La requête à hasher.
            model: Le modèle LLM utilisé.
            params: Paramètres de la requête.
            
        Returns:
            Clé de hachage unique.
        """
        params = params or {}
        # Ignorer certains paramètres qui ne devraient pas affecter le résultat
        filtered_params = {k: v for k, v in params.items() 
                           if k not in ["temperature", "stream", "max_tokens"]}
        
        # Créer une chaîne représentant la requête et ses paramètres
        key_content = f"{query}|{model}|{json.dumps(filtered_params, sort_keys=True)}"
        return hashlib.sha256(key_content.encode()).hexdigest()
    
    def get(
        self, 
        query: str, 
        model: str = "", 
        params: Dict[str, Any] = None,
        context: Dict[str, Any] = None
    ) -> Optional[Any]:
        """
        Récupère une entrée du cache.
        
        Args:
            query: La requête à chercher.
            model: Le modèle LLM utilisé.
            params: Paramètres de la requête.
            context: Contexte supplémentaire pour la recherche sémantique.
            
        Returns:
            Le résultat s'il est trouvé et valide, None sinon.
        """
        params = params or {}
        context = context or {}
        
        # Calculer la clé exacte
        key = self._compute_key(query, model, params)
        
        # Essayer d'abord la correspondance exacte en mémoire (plus rapide)
        with self._lock:
            if key in self.memory_cache:
                entry = self.memory_cache[key]
                if not entry.is_expired():
                    # Incrémenter les statistiques
                    self.stats["hits"] += 1
                    self.stats["memory_hits"] += 1
                    entry.hit_count += 1
                    return entry.result
                else:
                    # Supprimer l'entrée expirée
                    del self.memory_cache[key]
        
        # Essayer la correspondance exacte dans la base de données
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT result, timestamp, expiration, hit_count, query, model, parameters, context, priority FROM cache_entries WHERE key = ?", 
                (key,)
            )
            row = cursor.fetchone()
            
            if row:
                result, timestamp, expiration, hit_count, query_str, model_str, params_str, context_str, priority = row
                
                # Vérifier l'expiration
                if expiration is None or time.time() <= expiration:
                    # Incrémenter le compteur de hits
                    cursor.execute(
                        "UPDATE cache_entries SET hit_count = hit_count + 1 WHERE key = ?",
                        (key,)
                    )
                    conn.commit()
                    
                    # Créer l'entrée de cache
                    entry = CacheEntry(
                        query=query_str,
                        result=json.loads(result),
                        timestamp=timestamp,
                        model=model_str,
                        parameters=json.loads(params_str) if params_str else {},
                        context=json.loads(context_str) if context_str else {},
                        expiration=expiration,
                        priority=priority,
                        hit_count=hit_count + 1
                    )
                    
                    # Ajouter à la mémoire cache
                    with self._lock:
                        self.memory_cache[key] = entry
                        # Gérer la taille du cache mémoire
                        self._manage_memory_cache_size()
                    
                    # Incrémenter les statistiques
                    self.stats["hits"] += 1
                    self.stats["disk_hits"] += 1
                    
                    return entry.result
                else:
                    # Supprimer l'entrée expirée
                    cursor.execute("DELETE FROM cache_entries WHERE key = ?", (key,))
                    conn.commit()
            
            conn.close()
        except Exception as e:
            logger.error(f"Erreur lors de la recherche dans le cache disque: {str(e)}")
        
        # Si activé, essayer la correspondance sémantique
        if self.enable_semantic_matching and context:
            semantic_result = self._find_semantic_match(query, model, params, context)
            if semantic_result is not None:
                self.stats["hits"] += 1
                self.stats["semantic_hits"] += 1
                return semantic_result
        
        # Cache miss
        self.stats["misses"] += 1
        return None
    
    def put(
        self, 
        query: str, 
        result: Any, 
        model: str = "", 
        params: Dict[str, Any] = None,
        context: Dict[str, Any] = None,
        ttl: Optional[int] = None,
        priority: int = 0
    ) -> None:
        """
        Ajoute une entrée au cache.
        
        Args:
            query: La requête à stocker.
            result: Le résultat à stocker.
            model: Le modèle LLM utilisé.
            params: Paramètres de la requête.
            context: Contexte supplémentaire pour la recherche sémantique.
            ttl: Durée de vie en secondes (None pour utiliser la valeur par défaut).
            priority: Priorité de l'entrée (plus élevée = plus importante).
        """
        params = params or {}
        context = context or {}
        ttl = ttl if ttl is not None else self.default_ttl
        
        # Calculer la clé
        key = self._compute_key(query, model, params)
        
        # Calculer l'expiration
        expiration = time.time() + ttl if ttl is not None else None
        
        # Créer l'entrée de cache
        entry = CacheEntry(
            query=query,
            result=result,
            timestamp=time.time(),
            model=model,
            parameters=params,
            context=context,
            expiration=expiration,
            priority=priority
        )
        
        # Ajouter à la mémoire cache
        with self._lock:
            self.memory_cache[key] = entry
            # Gérer la taille du cache mémoire
            self._manage_memory_cache_size()
        
        # Ajouter à la base de données
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                """
                INSERT OR REPLACE INTO cache_entries 
                (key, query, result, timestamp, model, parameters, context, expiration, priority, hit_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    key, 
                    query, 
                    json.dumps(result), 
                    entry.timestamp, 
                    model, 
                    json.dumps(params), 
                    json.dumps(context), 
                    expiration, 
                    priority, 
                    0
                )
            )
            
            conn.commit()
            conn.close()
            
            # Incrémenter les statistiques
            self.stats["insertions"] += 1
            
            # Gérer la taille du cache disque
            self._manage_disk_cache_size()
            
            logger.debug(f"Entrée ajoutée au cache: {key}")
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout au cache disque: {str(e)}")
    
    def invalidate(self, query: str, model: str = "", params: Dict[str, Any] = None) -> bool:
        """
        Invalide une entrée du cache.
        
        Args:
            query: La requête à invalider.
            model: Le modèle LLM utilisé.
            params: Paramètres de la requête.
            
        Returns:
            True si l'entrée a été trouvée et invalidée, False sinon.
        """
        params = params or {}
        key = self._compute_key(query, model, params)
        
        # Supprimer de la mémoire cache
        found_memory = False
        with self._lock:
            if key in self.memory_cache:
                del self.memory_cache[key]
                found_memory = True
        
        # Supprimer de la base de données
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM cache_entries WHERE key = ?", (key,))
            found_disk = cursor.rowcount > 0
            
            conn.commit()
            conn.close()
            
            return found_memory or found_disk
        except Exception as e:
            logger.error(f"Erreur lors de l'invalidation du cache: {str(e)}")
            return found_memory
    
    def clear(self) -> None:
        """Efface tout le cache."""
        # Effacer la mémoire cache
        with self._lock:
            self.memory_cache.clear()
        
        # Effacer la base de données
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM cache_entries")
            
            conn.commit()
            conn.close()
            
            logger.info("Cache LLM entièrement effacé")
        except Exception as e:
            logger.error(f"Erreur lors de l'effacement du cache: {str(e)}")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Récupère les statistiques du cache.
        
        Returns:
            Dictionnaire de statistiques.
        """
        stats = self.stats.copy()
        
        # Calculer les statistiques supplémentaires
        total_requests = stats["hits"] + stats["misses"]
        if total_requests > 0:
            stats["hit_ratio"] = stats["hits"] / total_requests
        else:
            stats["hit_ratio"] = 0.0
        
        stats["memory_entries"] = len(self.memory_cache)
        
        # Compter les entrées disque
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) FROM cache_entries")
            stats["disk_entries"] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM cache_entries WHERE expiration < ?", (time.time(),))
            stats["expired_entries"] = cursor.fetchone()[0]
            
            conn.close()
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des statistiques de cache: {str(e)}")
            stats["disk_entries"] = -1
            stats["expired_entries"] = -1
        
        return stats
    
    def _find_semantic_match(
        self, 
        query: str, 
        model: str, 
        params: Dict[str, Any], 
        context: Dict[str, Any]
    ) -> Optional[Any]:
        """
        Recherche une correspondance sémantique dans le cache.
        
        Pour l'instant, cette implémentation est simplifiée et se base 
        sur des mots-clés et le contexte similaire. Une version plus avancée
        pourrait utiliser des embeddings vectoriels.
        
        Args:
            query: La requête à chercher.
            model: Le modèle LLM utilisé.
            params: Paramètres de la requête.
            context: Contexte de la requête.
            
        Returns:
            Le résultat s'il est trouvé et valide, None sinon.
        """
        # Implémenter une recherche par similitude contextuelle et lexicale
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Version simplifiée pour l'instant - recherche par modèle et mots-clés similaires
            # Extraire les mots-clés de la requête
            keywords = set(query.lower().split())
            threshold_words = max(3, len(keywords) * self.similarity_threshold)
            
            # Rechercher des entrées du même modèle
            cursor.execute(
                "SELECT key, query, result, timestamp, expiration, model, parameters, context FROM cache_entries WHERE model = ? AND expiration > ?",
                (model, time.time())
            )
            
            potential_matches = []
            
            for row in cursor.fetchall():
                key, stored_query, result, timestamp, expiration, stored_model, params_str, context_str = row
                
                # Calculer la similarité des requêtes
                stored_keywords = set(stored_query.lower().split())
                common_words = keywords.intersection(stored_keywords)
                
                # Vérifier le seuil de similarité
                if len(common_words) >= threshold_words:
                    # Vérifier la similarité du contexte si disponible
                    context_similarity = 0.0
                    if context and context_str:
                        stored_context = json.loads(context_str)
                        common_context_keys = set(context.keys()).intersection(set(stored_context.keys()))
                        if common_context_keys:
                            matching_values = sum(1 for k in common_context_keys if context[k] == stored_context[k])
                            context_similarity = matching_values / len(common_context_keys)
                    
                    # Score combiné
                    word_similarity = len(common_words) / max(len(keywords), len(stored_keywords))
                    combined_score = word_similarity * 0.7 + context_similarity * 0.3
                    
                    if combined_score >= self.similarity_threshold:
                        potential_matches.append((
                            combined_score,
                            key,
                            json.loads(result),
                            stored_query
                        ))
            
            conn.close()
            
            # Retourner le meilleur match s'il existe
            if potential_matches:
                potential_matches.sort(reverse=True, key=lambda x: x[0])
                best_match = potential_matches[0]
                logger.debug(f"Correspondance sémantique trouvée: {best_match[3]} (score: {best_match[0]:.2f})")
                return best_match[2]
        
        except Exception as e:
            logger.error(f"Erreur lors de la recherche sémantique: {str(e)}")
        
        return None
    
    def _manage_memory_cache_size(self) -> None:
        """Gère la taille du cache mémoire."""
        if len(self.memory_cache) <= self.max_memory_entries:
            return
        
        # Nombre d'entrées à supprimer
        entries_to_remove = len(self.memory_cache) - self.max_memory_entries
        
        # Trier les entrées par priorité et hit_count
        sorted_entries = sorted(
            self.memory_cache.items(),
            key=lambda x: (x[1].priority, x[1].hit_count)
        )
        
        # Supprimer les entrées les moins importantes
        for i in range(entries_to_remove):
            if i < len(sorted_entries):
                key, _ = sorted_entries[i]
                del self.memory_cache[key]
                self.stats["evictions"] += 1
    
    def _manage_disk_cache_size(self) -> None:
        """Gère la taille du cache disque."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Compter les entrées
            cursor.execute("SELECT COUNT(*) FROM cache_entries")
            count = cursor.fetchone()[0]
            
            if count <= self.max_disk_entries:
                conn.close()
                return
            
            # Nombre d'entrées à supprimer
            entries_to_remove = count - self.max_disk_entries
            
            # Supprimer d'abord les entrées expirées
            cursor.execute("DELETE FROM cache_entries WHERE expiration IS NOT NULL AND expiration < ?", 
                           (time.time(),))
            deleted = cursor.rowcount
            
            # Si nécessaire, supprimer les entrées les moins importantes
            if deleted < entries_to_remove:
                remaining = entries_to_remove - deleted
                cursor.execute(
                    """
                    DELETE FROM cache_entries 
                    WHERE key IN (
                        SELECT key FROM cache_entries 
                        ORDER BY priority ASC, hit_count ASC, timestamp ASC 
                        LIMIT ?
                    )
                    """, 
                    (remaining,)
                )
                deleted += cursor.rowcount
            
            conn.commit()
            conn.close()
            
            self.stats["evictions"] += deleted
            logger.debug(f"Cache disque nettoyé: {deleted} entrées supprimées")
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage du cache disque: {str(e)}")
    
    def _start_optimization_thread(self) -> None:
        """Démarre un thread d'optimisation périodique."""
        def optimization_routine():
            while True:
                try:
                    # Attendre avant la prochaine optimisation
                    time.sleep(3600)  # 1 heure
                    
                    # Nettoyer les entrées expirées
                    self._clean_expired_entries()
                    
                    # Optimiser la base de données
                    self._optimize_database()
                    
                    logger.debug("Optimisation périodique du cache effectuée")
                except Exception as e:
                    logger.error(f"Erreur lors de l'optimisation périodique: {str(e)}")
        
        optimization_thread = threading.Thread(
            target=optimization_routine,
            daemon=True
        )
        optimization_thread.start()
    
    def _clean_expired_entries(self) -> None:
        """Nettoie les entrées expirées."""
        # Nettoyer la mémoire cache
        with self._lock:
            keys_to_remove = [k for k, v in self.memory_cache.items() if v.is_expired()]
            for key in keys_to_remove:
                del self.memory_cache[key]
        
        # Nettoyer la base de données
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "DELETE FROM cache_entries WHERE expiration IS NOT NULL AND expiration < ?",
                (time.time(),)
            )
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Erreur lors du nettoyage des entrées expirées: {str(e)}")
    
    def _optimize_database(self) -> None:
        """Optimise la base de données SQLite."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("VACUUM")
            cursor.execute("ANALYZE")
            
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Erreur lors de l'optimisation de la base de données: {str(e)}")

# Instance singleton pour faciliter l'utilisation
_cache_instance = None

def get_llm_cache() -> LLMCache:
    """
    Récupère l'instance singleton du cache LLM.
    
    Returns:
        Instance du cache LLM.
    """
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = LLMCache()
    return _cache_instance

async def cached_llm_request(
    llm_callable: callable, 
    query: str, 
    model: str = "",
    params: Dict[str, Any] = None,
    context: Dict[str, Any] = None,
    ttl: Optional[int] = None,
    priority: int = 0,
    force_refresh: bool = False
) -> Any:
    """
    Effectue une requête LLM avec mise en cache.
    
    Args:
        llm_callable: Fonction asynchrone qui effectue la requête LLM.
        query: La requête à envoyer.
        model: Le modèle LLM utilisé.
        params: Paramètres de la requête.
        context: Contexte supplémentaire pour la recherche sémantique.
        ttl: Durée de vie en secondes (None pour utiliser la valeur par défaut).
        priority: Priorité de l'entrée (plus élevée = plus importante).
        force_refresh: Forcer le rafraîchissement du cache.
        
    Returns:
        Résultat de la requête.
    """
    cache = get_llm_cache()
    
    # Si pas de rafraîchissement forcé, vérifier le cache
    if not force_refresh:
        cached_result = cache.get(query, model, params, context)
        if cached_result is not None:
            return cached_result
    
    # Effectuer la requête
    result = await llm_callable(query, **params) if params else await llm_callable(query)
    
    # Mettre en cache le résultat
    cache.put(query, result, model, params, context, ttl, priority)
    
    return result 