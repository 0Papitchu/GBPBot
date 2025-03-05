import os
import time
import asyncio
import aiohttp
import random
from typing import Dict, List, Optional, Tuple, Any, Callable
from loguru import logger
from web3 import Web3
from web3.providers import HTTPProvider
from functools import wraps
import hashlib
import json
from gbpbot.config.config_manager import config_manager
from gbpbot.utils.cache_manager import cache_manager, cache_rpc_result

# Configurer asyncio pour Windows
if os.name == 'nt':
    # Utiliser le SelectorEventLoop sur Windows pour éviter les problèmes avec aiodns
    try:
        import asyncio
        import sys
        if sys.version_info >= (3, 8):
            # Python 3.8+ utilise ProactorEventLoop par défaut sur Windows
            # Forcer l'utilisation de SelectorEventLoop
            if asyncio.get_event_loop_policy()._loop_factory.__name__ == 'ProactorEventLoop':
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
                logger.info("Politique d'événements asyncio configurée pour Windows (SelectorEventLoop)")
    except Exception as e:
        logger.warning(f"Impossible de configurer la politique d'événements asyncio pour Windows: {str(e)}")

class RPCManager:
    """
    Gestionnaire de connexions RPC avec monitoring actif et sélection intelligente
    """
    
    _instance = None
    
    def __new__(cls):
        """Implémentation du pattern Singleton"""
        if cls._instance is None:
            cls._instance = super(RPCManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """
        Initialise le gestionnaire de RPC
        """
        if not hasattr(self, 'initialized'):
            # Charger la configuration RPC
            self.config = config_manager.get_config("rpc")
            
            # Valeurs par défaut si la configuration est incomplète
            default_config = {
                "providers": {
                    "avalanche": {
                        "mainnet": [
                            {"url": "https://api.avax.network/ext/bc/C/rpc", "weight": 10},
                            {"url": "https://avalanche-c-chain.publicnode.com", "weight": 8},
                            {"url": "https://rpc.ankr.com/avalanche", "weight": 7}
                        ]
                    }
                },
                "timeout": 10,
                "max_retries": 3,
                "retry_delay": 1,
                "max_retry_delay": 30,
                "jitter": True,
                "batch_size": 10,
                "batch_interval": 0.5
            }
            
            # Fusionner avec les valeurs par défaut
            for key, value in default_config.items():
                if key not in self.config:
                    self.config[key] = value
            
            # S'assurer que la structure des providers est correcte
            if "providers" not in self.config:
                self.config["providers"] = default_config["providers"]
            
            # Initialiser les connexions
            self.providers = {}
            self.provider_stats = {}
            self.provider_health = {}
            self.active_providers = {}
            self.session = None
            self.batch_queue = {}
            self.batch_lock = {}
            
            # Initialiser les statistiques
            self.stats = {
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
                "retried_calls": 0,
                "cached_calls": 0,
                "avg_response_time": 0,
                "batch_calls": 0,
                "batch_savings": 0,
                "provider_stats": {}
            }
            
            # Suivi de la dernière vérification de santé
            self.last_health_check = 0
            
            # Initialiser les sessions aiohttp
            self._init_session()
            
            # Initialiser les fournisseurs
            self._init_providers()
            
            # Marquer comme initialisé
            self.initialized = True
            logger.info("Gestionnaire RPC initialisé")
    
    def _init_session(self):
        """
        Initialise la session aiohttp pour les requêtes RPC
        """
        if self.session is None or self.session.closed:
            # Ne pas créer de session immédiatement, mais seulement quand nécessaire
            # La session sera créée lors du premier appel RPC
            pass
    
    async def _ensure_session(self):
        """
        S'assure qu'une session aiohttp est disponible
        """
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.config["timeout"]),
                headers={"Content-Type": "application/json"}
            )
    
    def _init_providers(self):
        """Initialise les fournisseurs RPC à partir de la configuration"""
        for chain, networks in self.config.get("providers", {}).items():
            self.providers[chain] = {}
            for network, providers in networks.items():
                self.providers[chain][network] = []
                for provider in providers:
                    # Vérifier si le provider est un dictionnaire ou une chaîne
                    if isinstance(provider, str):
                        # Convertir la chaîne en dictionnaire
                        provider = {"url": provider, "weight": 1}
                    
                    # Générer un ID unique pour ce fournisseur
                    provider_id = self._get_provider_id(provider["url"])
                    
                    # Ajouter le fournisseur avec ses statistiques
                    self.providers[chain][network].append({
                        "id": provider_id,
                        "url": provider["url"],
                        "weight": provider.get("weight", 1),
                        "type": provider.get("type", "http"),
                        "stats": {
                            "calls": 0,
                            "errors": 0,
                            "avg_response_time": 0,
                            "total_response_time": 0,
                            "last_call": 0,
                            "last_error": None,
                            "consecutive_errors": 0,
                            "health": 1.0
                        }
                    })
                    
                    # Initialiser les statistiques pour ce fournisseur
                    if chain not in self.stats["provider_stats"]:
                        self.stats["provider_stats"][chain] = {}
                    if network not in self.stats["provider_stats"][chain]:
                        self.stats["provider_stats"][chain][network] = {}
                    self.stats["provider_stats"][chain][network][provider_id] = {
                        "calls": 0,
                        "errors": 0,
                        "avg_response_time": 0,
                        "health": 1.0
                    }
        
        logger.info(f"Fournisseurs RPC initialisés: {sum(len(providers) for chain_providers in self.stats['provider_stats'].values() for providers in chain_providers.values())} endpoints")
    
    def _get_provider_id(self, url: str) -> str:
        """
        Génère un identifiant unique pour un fournisseur RPC
        
        Args:
            url: URL du fournisseur RPC
            
        Returns:
            str: Identifiant unique
        """
        # Utiliser un hash pour masquer les clés API dans les logs
        return hashlib.md5(url.encode()).hexdigest()[:8]
    
    async def _select_best_provider(self, chain: str, network: str) -> str:
        """
        Sélectionne le meilleur fournisseur RPC en fonction de la santé et du poids
        
        Args:
            chain: Chaîne blockchain
            network: Réseau
            
        Returns:
            str: ID du meilleur fournisseur
        """
        if chain not in self.providers or network not in self.providers[chain]:
            raise ValueError(f"Aucun fournisseur disponible pour {chain}/{network}")
        
        providers = self.providers[chain][network]
        if not providers:
            raise ValueError(f"Aucun fournisseur disponible pour {chain}/{network}")
        
        # Calculer un score pour chaque fournisseur
        scores = []
        for provider in providers:
            # Facteurs de score
            health = provider["stats"]["health"]
            weight = provider["weight"]
            response_time = provider["stats"]["avg_response_time"] or 1.0
            calls = provider["stats"]["calls"]
            errors = provider["stats"]["errors"]
            consecutive_errors = provider["stats"]["consecutive_errors"]
            last_call = provider["stats"]["last_call"]
            
            # Pénalité pour les erreurs consécutives
            error_penalty = 0.5 ** consecutive_errors if consecutive_errors > 0 else 1.0
            
            # Pénalité pour les appels récents (pour équilibrer la charge)
            time_since_last_call = time.time() - last_call
            recency_factor = min(1.0, time_since_last_call / 5.0) if last_call > 0 else 1.0
            
            # Score final
            score = health * weight * error_penalty * recency_factor * (1.0 / (response_time + 0.1))
            
            # Ajouter à la liste des scores
            scores.append((provider["id"], score))
        
        # Trier par score décroissant
        scores.sort(key=lambda x: x[1], reverse=True)
        
        # Sélectionner le meilleur fournisseur
        return scores[0][0]
    
    async def _update_provider_stats(self, chain: str, network: str, url: str, success: bool, response_time: float, error: Optional[str] = None):
        """
        Met à jour les statistiques d'un fournisseur
        
        Args:
            chain: Chaîne blockchain
            network: Réseau
            url: URL du fournisseur
            success: Succès de l'appel
            response_time: Temps de réponse
            error: Message d'erreur (si échec)
        """
        # Trouver le fournisseur
        provider_id = self._get_provider_id(url)
        provider = None
        for p in self.providers.get(chain, {}).get(network, []):
            if p["id"] == provider_id:
                provider = p
                break
        
        if not provider:
            return
        
        # Mettre à jour les statistiques
        provider["stats"]["calls"] += 1
        provider["stats"]["last_call"] = time.time()
        
        if success:
            # Réinitialiser les erreurs consécutives
            provider["stats"]["consecutive_errors"] = 0
            provider["stats"]["last_error"] = None
            
            # Mettre à jour le temps de réponse moyen
            total_calls = provider["stats"]["calls"]
            current_avg = provider["stats"]["avg_response_time"] or 0
            new_avg = ((current_avg * (total_calls - 1)) + response_time) / total_calls
            provider["stats"]["avg_response_time"] = new_avg
            provider["stats"]["total_response_time"] += response_time
            
            # Améliorer la santé
            provider["stats"]["health"] = min(1.0, provider["stats"]["health"] + 0.05)
        else:
            # Incrémenter les erreurs
            provider["stats"]["errors"] += 1
            provider["stats"]["consecutive_errors"] += 1
            provider["stats"]["last_error"] = error
            
            # Dégrader la santé
            provider["stats"]["health"] = max(0.1, provider["stats"]["health"] - 0.2)
        
        # Mettre à jour les statistiques globales
        if chain in self.stats["provider_stats"] and network in self.stats["provider_stats"][chain]:
            self.stats["provider_stats"][chain][network][provider_id] = {
                "calls": provider["stats"]["calls"],
                "errors": provider["stats"]["errors"],
                "avg_response_time": provider["stats"]["avg_response_time"],
                "health": provider["stats"]["health"]
            }
    
    @cache_rpc_result
    async def call_rpc(self, method: str, params: List = None, chain: str = "avalanche", 
                      network: str = "mainnet", provider_id: str = None) -> Dict:
        """
        Appelle une méthode RPC avec les paramètres fournis
        
        Args:
            method: Méthode RPC à appeler
            params: Paramètres de la méthode
            chain: Chaîne blockchain
            network: Réseau
            provider_id: ID du fournisseur à utiliser (optionnel)
            
        Returns:
            Dict: Résultat de l'appel RPC
        """
        # Vérifier si le mode simulation est activé
        try:
            from gbpbot.core.simulation import is_simulation_mode
            from gbpbot.core.rpc.rpc_simulation import simulated_rpc_manager
            
            if is_simulation_mode() and simulated_rpc_manager is not None:
                logger.debug(f"Appel RPC simulé: {method}")
                provider = simulated_rpc_manager.get_current_provider()
                result = await provider.make_request(method, params or [])
                return result
        except ImportError:
            # En cas d'erreur d'importation, continuer avec le mode normal
            pass
            
        params = params or []
        
        self.stats["total_calls"] += 1
        
        # S'assurer que la session est disponible
        await self._ensure_session()
        
        # Obtenir le fournisseur
        provider = await self._get_provider(chain, network, provider_id)
        url = provider["url"]
        provider_id = provider["id"]
        
        # Construire la requête
        request_id = str(random.randint(1, 10000))
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": request_id
        }
        
        # Enregistrer le début de l'appel
        start_time = time.time()
        
        # Effectuer la requête avec retries
        max_retries = self.config["max_retries"]
        retry_delay = self.config["retry_delay"]
        max_retry_delay = self.config["max_retry_delay"]
        
        # Variables pour les retries
        current_retry = 0
        
        while current_retry <= max_retries:
            try:
                async with self.session.post(url, json=payload, timeout=self.config["timeout"]) as response:
                    # Enregistrer le temps de réponse
                    response_time = (time.time() - start_time) * 1000  # en ms
                    
                    # Vérifier le statut HTTP
                    if response.status != 200:
                        error_msg = f"Erreur HTTP {response.status}: {await response.text()}"
                        logger.warning(f"Erreur RPC ({url}): {error_msg}")
                        
                        # Mettre à jour les statistiques
                        await self._update_provider_stats(chain, network, url, False, response_time, error_msg)
                        
                        # Réessayer avec un autre fournisseur si possible
                        if current_retry < max_retries:
                            # Calculer le délai avant de réessayer
                            if self.config["jitter"]:
                                delay = min(max_retry_delay, retry_delay * (2 ** current_retry)) * (0.5 + random.random())
                            else:
                                delay = min(max_retry_delay, retry_delay * (2 ** current_retry))
                            
                            # Changer de fournisseur
                            logger.debug(f"Changement de fournisseur après erreur, attente de {delay:.2f}s...")
                            await asyncio.sleep(delay)
                            
                            # Incrémenter le compteur de retries
                            current_retry += 1
                            self.stats["retried_calls"] += 1
                            
                            # Obtenir un nouveau fournisseur
                            provider = await self._get_provider(chain, network)
                            url = provider["url"]
                            provider_id = provider["id"]
                            
                            # Recommencer la boucle
                            start_time = time.time()
                            continue
                        
                        # Si on a épuisé les retries, lever une exception
                        self.stats["failed_calls"] += 1
                        raise Exception(f"Erreur RPC: {error_msg} (après {max_retries} tentatives)")
                    
                    # Parser la réponse JSON
                    try:
                        result = await response.json()
                    except Exception as e:
                        error_msg = f"Erreur de parsing JSON: {str(e)}"
                        logger.warning(f"Erreur RPC ({url}): {error_msg}")
                        
                        # Mettre à jour les statistiques
                        await self._update_provider_stats(chain, network, url, False, response_time, error_msg)
                        
                        # Si on a épuisé les retries, lever une exception
                        if current_retry >= max_retries:
                            self.stats["failed_calls"] += 1
                            raise Exception(f"Erreur RPC: {error_msg} (après {max_retries} tentatives)")
                        
                        # Sinon, réessayer
                        current_retry += 1
                        self.stats["retried_calls"] += 1
                        continue
                    
                    # Vérifier s'il y a une erreur dans la réponse
                    if "error" in result and result["error"] is not None:
                        error_msg = f"Erreur RPC: {result['error']}"
                        logger.warning(f"Erreur RPC ({url}): {error_msg}")
                        
                        # Mettre à jour les statistiques
                        await self._update_provider_stats(chain, network, url, False, response_time, error_msg)
                        
                        # Si on a épuisé les retries, retourner l'erreur
                        if current_retry >= max_retries:
                            self.stats["failed_calls"] += 1
                            return result
                        
                        # Sinon, réessayer
                        current_retry += 1
                        self.stats["retried_calls"] += 1
                        continue
                    
                    # Mettre à jour les statistiques
                    await self._update_provider_stats(chain, network, url, True, response_time)
                    
                    # Incrémenter le compteur de succès
                    self.stats["successful_calls"] += 1
                    
                    # Retourner le résultat
                    return result
            
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                error_msg = f"Erreur de connexion: {str(e)}"
                logger.warning(f"Erreur RPC ({url}): {error_msg}")
                
                # Mettre à jour les statistiques
                await self._update_provider_stats(chain, network, url, False, (time.time() - start_time) * 1000, error_msg)
                
                # Si on a épuisé les retries, lever une exception
                if current_retry >= max_retries:
                    self.stats["failed_calls"] += 1
                    raise Exception(f"Erreur RPC: {error_msg} (après {max_retries} tentatives)")
                
                # Sinon, réessayer
                current_retry += 1
                self.stats["retried_calls"] += 1
                
                # Calculer le délai avant de réessayer
                if self.config["jitter"]:
                    delay = min(max_retry_delay, retry_delay * (2 ** current_retry)) * (0.5 + random.random())
                else:
                    delay = min(max_retry_delay, retry_delay * (2 ** current_retry))
                
                # Attendre avant de réessayer
                logger.debug(f"Tentative {current_retry}/{max_retries} dans {delay:.2f}s...")
                await asyncio.sleep(delay)
                
                # Changer de fournisseur
                provider = await self._get_provider(chain, network)
                url = provider["url"]
                provider_id = provider["id"]
                
                # Recommencer la boucle
                start_time = time.time()
        
        # Si on arrive ici, c'est qu'on a épuisé les retries sans succès
        self.stats["failed_calls"] += 1
        raise Exception(f"Erreur RPC: Toutes les tentatives ont échoué")
    
    async def batch_call_rpc(self, calls: List[Dict], chain: str = "avalanche", 
                           network: str = "mainnet", provider_id: str = None) -> List[Dict]:
        """
        Effectue plusieurs appels RPC en batch
        
        Args:
            calls: Liste d'appels RPC (chaque appel est un dict avec method et params)
            chain: Chaîne blockchain
            network: Réseau
            provider_id: ID du fournisseur (None pour sélectionner le meilleur)
            
        Returns:
            List[Dict]: Résultats des appels RPC
        """
        # S'assurer que la session est initialisée
        await self._ensure_session()
        
        # Obtenir le fournisseur
        provider = await self._get_provider(chain, network, provider_id)
        url = provider["url"]
        provider_id = provider["id"]
        
        # Préparer les requêtes
        batch_requests = []
        for i, call in enumerate(calls):
            batch_requests.append({
                "jsonrpc": "2.0",
                "method": call["method"],
                "params": call.get("params", []),
                "id": i + 1
            })
        
        # Statistiques
        start_time = time.time()
        success = False
        error_message = None
        
        try:
            # Envoyer la requête
            async with self.session.post(url, json=batch_requests, timeout=self.config.get("timeout", 10)) as response:
                # Vérifier le code de statut
                if response.status != 200:
                    error_message = f"Erreur HTTP {response.status}: {await response.text()}"
                    logger.warning(f"Erreur RPC batch ({url}): {error_message}")
                    return [{"error": {"code": response.status, "message": error_message}} for _ in calls]
                
                # Analyser la réponse
                results = await response.json()
                
                # Vérifier si la réponse est une liste
                if not isinstance(results, list):
                    results = [results]
                
                # Succès
                success = True
                return results
                
        except Exception as e:
            # Gérer les erreurs
            error_message = str(e)
            logger.warning(f"Exception lors de l'appel RPC batch ({url}): {error_message}")
            return [{"error": {"code": -32000, "message": error_message}} for _ in calls]
            
        finally:
            # Calculer le temps de réponse
            response_time = time.time() - start_time
            
            # Mettre à jour les statistiques
            await self._update_provider_stats(chain, network, url, success, response_time, error_message)
            
            # Mettre à jour les statistiques globales
            self.stats["batch_calls"] += 1
            self.stats["total_calls"] += len(calls)
            if success:
                self.stats["successful_calls"] += len(calls)
                self.stats["batch_savings"] += len(calls) - 1  # Économie d'appels
            else:
                self.stats["failed_calls"] += len(calls)
    
    async def add_to_batch_queue(self, chain: str, network: str, method: str, params: List = None) -> int:
        """
        Ajoute un appel RPC à la file d'attente de batch
        
        Args:
            chain: Chaîne blockchain
            network: Réseau
            method: Méthode RPC
            params: Paramètres de la méthode
            
        Returns:
            int: ID de l'appel dans la file d'attente
        """
        if params is None:
            params = []
        
        # Initialiser la file d'attente pour cette chaîne/réseau si nécessaire
        queue_key = f"{chain}_{network}"
        if queue_key not in self.batch_queue:
            self.batch_queue[queue_key] = []
            self.batch_queue_ids[queue_key] = {}
        
        # Générer un ID unique pour cet appel
        self.batch_queue_counter += 1
        call_id = self.batch_queue_counter
        
        # Ajouter l'appel à la file d'attente
        self.batch_queue[queue_key].append({
            "method": method,
            "params": params,
            "id": call_id
        })
        
        # Associer l'ID à l'index dans la file d'attente
        self.batch_queue_ids[queue_key][call_id] = len(self.batch_queue[queue_key]) - 1
        
        return call_id
    
    async def execute_batch_queue(self, chain: str, network: str, max_age: float = 0.5, min_batch_size: int = 2, max_batch_size: int = 20) -> Dict[int, Any]:
        """
        Exécute la file d'attente de batch
        
        Args:
            chain: Chaîne blockchain
            network: Réseau
            max_age: Âge maximum des appels en secondes
            min_batch_size: Taille minimale du batch
            max_batch_size: Taille maximale du batch
            
        Returns:
            Dict[int, Any]: Résultats des appels
        """
        # Vérifier si la file d'attente existe
        queue_key = f"{chain}_{network}"
        if queue_key not in self.batch_queue or not self.batch_queue[queue_key]:
            return {}
        
        # Vérifier si la file d'attente est assez grande
        if len(self.batch_queue[queue_key]) < min_batch_size:
            return {}
        
        # Limiter la taille du batch
        calls = self.batch_queue[queue_key][:max_batch_size]
        call_ids = [call["id"] for call in calls]
        
        # Exécuter le batch
        results = await self.batch_call_rpc(calls, chain, network)
        
        # Associer les résultats aux IDs d'appel
        call_results = {}
        for i, result in enumerate(results):
            if i < len(call_ids):
                call_id = call_ids[i]
                call_results[call_id] = result.get("result") if "result" in result else None
        
        # Supprimer les appels traités de la file d'attente
        self.batch_queue[queue_key] = self.batch_queue[queue_key][len(calls):]
        
        # Mettre à jour les IDs
        self.batch_queue_ids[queue_key] = {}
        for i, call in enumerate(self.batch_queue[queue_key]):
            self.batch_queue_ids[queue_key][call["id"]] = i
        
        return call_results
    
    async def get_web3(self, chain: str, network: str) -> Web3:
        """
        Récupère une instance Web3 configurée avec le meilleur fournisseur
        
        Args:
            chain: Chaîne blockchain
            network: Réseau
            
        Returns:
            Web3: Instance Web3
        """
        # Vérifier si le mode simulation est activé
        try:
            from gbpbot.core.simulation import is_simulation_mode
            from gbpbot.core.rpc.rpc_simulation import simulated_rpc_manager
            
            if is_simulation_mode() and simulated_rpc_manager is not None:
                logger.info("Utilisation du gestionnaire RPC simulé")
                return await simulated_rpc_manager.get_web3()
        except ImportError:
            # En cas d'erreur d'importation, continuer avec le mode normal
            logger.debug("Module de simulation non disponible, utilisation du mode normal")
        
        # Obtenir le meilleur fournisseur
        provider = await self._get_provider(chain, network)
        url = provider["url"]
        
        # Créer l'instance Web3
        web3 = Web3(HTTPProvider(url))
        
        # Vérifier la connexion
        if not web3.is_connected():
            logger.warning(f"Impossible de se connecter à {url}, tentative avec un autre fournisseur")
            
            # Marquer ce fournisseur comme défaillant
            await self._update_provider_stats(chain, network, url, False, 0, "Échec de connexion Web3")
            
            # Réessayer avec un autre fournisseur
            for p in self.providers.get(chain, {}).get(network, []):
                if p["id"] != provider["id"]:
                    url = p["url"]
                    web3 = Web3(HTTPProvider(url))
                    if web3.is_connected():
                        logger.info(f"Connexion établie avec {url}")
                        break
        
        return web3
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Récupère les statistiques du gestionnaire RPC
        
        Returns:
            Dict[str, Any]: Statistiques
        """
        # Calculer des statistiques supplémentaires
        total_calls = self.stats["total_calls"]
        if total_calls > 0:
            success_rate = self.stats["successful_calls"] / total_calls * 100
            error_rate = self.stats["failed_calls"] / total_calls * 100
            retry_rate = self.stats["retried_calls"] / total_calls * 100 if "retried_calls" in self.stats else 0
            cache_hit_rate = self.stats["cached_calls"] / total_calls * 100 if "cached_calls" in self.stats else 0
        else:
            success_rate = 0
            error_rate = 0
            retry_rate = 0
            cache_hit_rate = 0
            
        # Ajouter les statistiques calculées
        stats = self.stats.copy()
        stats["success_rate"] = success_rate
        stats["error_rate"] = error_rate
        stats["retry_rate"] = retry_rate
        stats["cache_hit_rate"] = cache_hit_rate
        
        return stats
    
    def get_web3_provider(self, chain: str = "avalanche", network: str = "mainnet") -> Web3:
        """
        Récupère une instance Web3 configurée avec le meilleur fournisseur (version synchrone)
        
        Args:
            chain: Chaîne blockchain
            network: Réseau
            
        Returns:
            Web3: Instance Web3
        """
        # Obtenir l'URL du meilleur fournisseur
        url = self.get_best_rpc_url(chain, network)
        
        if not url:
            logger.warning(f"Aucun fournisseur disponible pour {chain}/{network}")
            return None
        
        # Créer l'instance Web3
        web3 = Web3(HTTPProvider(url))
        
        # Vérifier la connexion
        if not web3.is_connected():
            logger.warning(f"Impossible de se connecter à {url}")
            return None
            
        return web3
    
    def get_provider_stats(self, chain: str = None, network: str = None) -> Dict[str, Any]:
        """
        Récupère les statistiques des fournisseurs
        
        Args:
            chain: Chaîne blockchain (None pour toutes les chaînes)
            network: Réseau (None pour tous les réseaux)
            
        Returns:
            Dict[str, Any]: Statistiques des fournisseurs
        """
        if chain is None:
            # Retourner les statistiques pour toutes les chaînes
            return self.stats["provider_stats"]
        
        if chain not in self.stats["provider_stats"]:
            return {}
        
        if network is None:
            # Retourner les statistiques pour tous les réseaux de cette chaîne
            return self.stats["provider_stats"][chain]
        
        if network not in self.stats["provider_stats"][chain]:
            return {}
        
        # Retourner les statistiques pour cette chaîne et ce réseau
        return self.stats["provider_stats"][chain][network]
    
    async def check_all_providers(self) -> Dict[str, Dict[str, Dict[str, bool]]]:
        """
        Vérifie la disponibilité de tous les fournisseurs RPC
        
        Returns:
            Dict[str, Dict[str, Dict[str, bool]]]: Résultats des vérifications
        """
        results = {}
        
        # Vérifier chaque fournisseur
        for chain, networks in self.providers.items():
            results[chain] = {}
            
            for network, providers in networks.items():
                results[chain][network] = {}
                
                for provider in providers:
                    provider_id = provider["id"]
                    url = provider["url"]
                    
                    # Vérifier la disponibilité
                    try:
                        # Effectuer un appel simple
                        start_time = time.time()
                        async with self.session.post(
                            url,
                            json={
                                "jsonrpc": "2.0",
                                "method": "eth_blockNumber",
                                "params": [],
                                "id": 1
                            },
                            timeout=5
                        ) as response:
                            if response.status == 200:
                                response_data = await response.json()
                                if "result" in response_data:
                                    # Mettre à jour les statistiques
                                    response_time = time.time() - start_time
                                    await self._update_provider_stats(chain, network, url, True, response_time)
                                    results[chain][network][provider_id] = True
                                    continue
                            
                            # Si on arrive ici, il y a eu un problème
                            response_time = time.time() - start_time
                            await self._update_provider_stats(chain, network, url, False, response_time, "Réponse invalide")
                            results[chain][network][provider_id] = False
                            
                    except Exception as e:
                        # Mettre à jour les statistiques
                        response_time = time.time() - start_time if 'start_time' in locals() else 0
                        await self._update_provider_stats(chain, network, url, False, response_time, str(e))
                        results[chain][network][provider_id] = False
        
        return results
    
    async def check_rpc_health(self) -> Dict[str, Any]:
        """
        Vérifie la santé des nœuds RPC et met à jour les statistiques
        
        Returns:
            Dict[str, Any]: Résultat de la vérification de santé
        """
        # Vérifier si le mode simulation est activé
        try:
            from gbpbot.core.simulation import is_simulation_mode
            from gbpbot.core.rpc.rpc_simulation import simulated_rpc_manager
            
            if is_simulation_mode() and simulated_rpc_manager is not None:
                logger.debug("Vérification de la santé des nœuds RPC simulés")
                return await simulated_rpc_manager.check_rpc_health()
        except ImportError:
            # En cas d'erreur d'importation, continuer avec le mode normal
            pass
            
        # Vérifier si une vérification récente a été effectuée
        current_time = time.time()
        if current_time - self.last_health_check < 60:  # 1 minute de cache
            # Calculer le nombre de nœuds actifs
            active_nodes = 0
            total_nodes = 0
            
            for chain, networks in self.providers.items():
                for network, providers in networks.items():
                    for provider in providers:
                        total_nodes += 1
                        if provider["stats"]["health"] > 0.5:
                            active_nodes += 1
            
            logger.debug(f"Utilisation des résultats de santé en cache: {active_nodes}/{total_nodes} nœuds actifs")
            return {
                "last_check": self.last_health_check,
                "age": current_time - self.last_health_check,
                "active_nodes": active_nodes,
                "total_nodes": total_nodes,
                "cached": True
            }
            
        logger.debug("Vérification de la santé des nœuds RPC")
        results = await self.check_all_providers()
        
        # Mettre à jour le timestamp de dernière vérification
        self.last_health_check = current_time
        
        # Compter les nœuds actifs
        active_nodes = 0
        total_nodes = 0
        nodes = []
        
        for chain, networks in results.items():
            for network, providers in networks.items():
                for provider_id, status in providers.items():
                    total_nodes += 1
                    
                    # Rechercher les détails du fournisseur
                    provider = self._get_provider_by_id(chain, network, provider_id)
                    if provider is None:
                        continue
                    
                    # Ajouter aux nœuds
                    node_info = {
                        "id": provider_id,
                        "endpoint": provider["url"],
                        "chain": chain,
                        "network": network,
                        "status": "inactive"
                    }
                    
                    # Vérifier si le nœud est actif
                    if status:
                        active_nodes += 1
                        node_info["status"] = "active"
                    
                    # Ajouter les statistiques si disponibles
                    if "stats" in provider:
                        node_info["stats"] = {
                            "calls": provider["stats"]["calls"],
                            "errors": provider["stats"]["errors"],
                            "health": provider["stats"]["health"],
                            "avg_response_time": provider["stats"]["avg_response_time"]
                        }
                    
                    nodes.append(node_info)
        
        return {
            "last_check": self.last_health_check,
            "age": 0,
            "active_nodes": active_nodes,
            "total_nodes": total_nodes,
            "cached": False,
            "nodes": nodes
        }
    
    def _get_provider_by_id(self, chain: str, network: str, provider_id: str) -> Optional[Dict]:
        """
        Récupère un fournisseur par son ID
        
        Args:
            chain: Chaîne blockchain
            network: Réseau
            provider_id: ID du fournisseur
            
        Returns:
            Dict: Fournisseur, None si non trouvé
        """
        if chain not in self.providers or network not in self.providers[chain]:
            return None
        
        for provider in self.providers[chain][network]:
            if provider["id"] == provider_id:
                return provider
        
        return None

    async def close(self):
        """
        Ferme la session HTTP
        """
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("Session RPC fermée")

    def get_best_rpc_url(self, chain: str = "avalanche", network: str = "mainnet") -> Optional[str]:
        """
        Récupère l'URL du meilleur fournisseur RPC
        
        Args:
            chain: Chaîne blockchain
            network: Réseau
            
        Returns:
            str: URL du meilleur fournisseur, None si aucun n'est disponible
        """
        # Vérifier si la chaîne et le réseau existent
        if chain not in self.providers or network not in self.providers[chain]:
            logger.warning(f"Aucun fournisseur disponible pour {chain}/{network}")
            return None
        
        # Sélectionner le meilleur fournisseur
        provider = self._select_provider(chain, network)
        if provider:
            return provider["url"]
        
        return None
    
    def _select_provider(self, chain: str = "avalanche", network: str = "mainnet") -> Optional[Dict]:
        """
        Sélectionne le meilleur fournisseur RPC en fonction des statistiques
        
        Args:
            chain: Chaîne blockchain
            network: Réseau
            
        Returns:
            Dict: Meilleur fournisseur, None si aucun n'est disponible
        """
        if chain not in self.providers or network not in self.providers[chain]:
            logger.warning(f"Aucun fournisseur disponible pour {chain}/{network}")
            return None
        
        providers = self.providers[chain][network]
        if not providers:
            logger.warning(f"Aucun fournisseur disponible pour {chain}/{network}")
            return None
        
        # Calculer un score pour chaque fournisseur
        scored_providers = []
        for provider in providers:
            # Facteurs de score
            health = provider["stats"]["health"]
            weight = provider["weight"]
            response_time = provider["stats"]["avg_response_time"] or 1.0
            calls = provider["stats"]["calls"]
            errors = provider["stats"]["errors"]
            consecutive_errors = provider["stats"]["consecutive_errors"]
            last_call = provider["stats"]["last_call"]
            
            # Pénalité pour les erreurs consécutives
            error_penalty = 0.5 ** consecutive_errors if consecutive_errors > 0 else 1.0
            
            # Pénalité pour les appels récents (pour équilibrer la charge)
            time_since_last_call = time.time() - last_call
            recency_factor = min(1.0, time_since_last_call / 5.0) if last_call > 0 else 1.0
            
            # Score final
            score = health * weight * error_penalty * recency_factor * (1.0 / (response_time + 0.1))
            
            # Ajouter à la liste des scores
            scored_providers.append((provider, score))
        
        # Trier par score décroissant
        scored_providers.sort(key=lambda x: x[1], reverse=True)
        
        # Sélectionner le meilleur fournisseur
        if scored_providers:
            return scored_providers[0][0]
        
        return None
    
    async def _get_provider(self, chain: str, network: str, provider_id: Optional[str] = None) -> Dict:
        """
        Récupère un fournisseur RPC
        
        Args:
            chain: Chaîne blockchain
            network: Réseau
            provider_id: ID du fournisseur (None pour sélectionner le meilleur)
            
        Returns:
            Dict: Fournisseur RPC
        """
        if chain not in self.providers or network not in self.providers[chain]:
            raise ValueError(f"Aucun fournisseur disponible pour {chain}/{network}")
        
        providers = self.providers[chain][network]
        if not providers:
            raise ValueError(f"Aucun fournisseur disponible pour {chain}/{network}")
        
        if provider_id is None:
            # Sélectionner le meilleur fournisseur
            provider_id = await self._select_best_provider(chain, network)
        
        # Trouver le fournisseur
        for provider in providers:
            if provider["id"] == provider_id:
                return provider
        
        # Si le fournisseur n'est pas trouvé, sélectionner le meilleur
        logger.warning(f"Fournisseur {provider_id} non trouvé pour {chain}/{network}, sélection du meilleur")
        provider_id = await self._select_best_provider(chain, network)
        
        for provider in providers:
            if provider["id"] == provider_id:
                return provider
        
        # Si aucun fournisseur n'est disponible, lever une erreur
        raise ValueError(f"Aucun fournisseur disponible pour {chain}/{network}")

# Créer une instance singleton du gestionnaire RPC
rpc_manager = RPCManager() 