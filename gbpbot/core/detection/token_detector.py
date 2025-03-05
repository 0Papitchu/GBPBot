from typing import Dict, List, Set, Optional, Union, Tuple
from loguru import logger
import asyncio
import time
from datetime import datetime, timedelta
import re
import json
from web3 import Web3
from web3.logs import DISCARD
import aiohttp
from collections import deque

from gbpbot.core.blockchain_factory import BlockchainFactory
from gbpbot.api_adapters.base_adapter import BaseAPIAdapter
from gbpbot.core.config import Config
from gbpbot.core.token_analyzer import TokenAnalyzer
from gbpbot.utils.events import EventEmitter

class TokenDetector:
    """
    Système avancé de détection de nouveaux tokens sur plusieurs blockchains.
    """
    
    def __init__(self, config: Config):
        """
        Initialise le détecteur de tokens
        
        Args:
            config: Configuration du détecteur
        """
        self.config = config
        self.detection_config = config.get_config().get("detection", {})
        self.api_adapters = {}
        self.blockchains = {}
        self.event_emitter = EventEmitter()
        
        # Initialiser l'analyseur de tokens
        self.token_analyzer = TokenAnalyzer(config.get_config())
        
        # Liste des tokens détectés (max 1000)
        self.detected_tokens = deque(maxlen=1000)
        
        # Ensembles pour suivre les tokens déjà traités
        self.processed_addresses = set()
        self.mempool_processed = set()
        self.blacklisted_addresses = set()
        
        # Timestamps pour les limites de requêtes
        self.last_factory_check = {}
        self.last_mempool_check = {}
        
        # Statistiques
        self.stats = {
            "tokens_detected": 0,
            "tokens_analyzed": 0,
            "tokens_accepted": 0,
            "tokens_rejected": 0,
            "honeypots_detected": 0,
            "detection_by_source": {
                "factory_events": 0,
                "mempool": 0,
                "api_feeds": 0,
                "pancakeswap": 0,
                "manual": 0
            },
            "last_detection_time": None,
            "average_detection_time": 0.0,
            "total_detection_time": 0.0
        }
        
        # Chargement de la configuration spécifique
        self._load_config()
        
        logger.info(f"✅ Détecteur de tokens initialisé")
        
    def _load_config(self):
        """Charge la configuration spécifique du détecteur de tokens"""
        # Charger les tokens blacklistés
        token_filters = self.detection_config.get("filters", {})
        blacklist = token_filters.get("exclude_tokens", [])
        self.blacklisted_addresses = set(addr.lower() for addr in blacklist if addr)
        
        # Paramètres de filtrage
        self.min_liquidity = token_filters.get("min_liquidity", 5000)
        self.exclude_stablecoins = token_filters.get("exclude_stablecoins", True)
        
        # Méthodes de détection activées
        methods = self.detection_config.get("methods", {})
        self.detect_pancakeswap = methods.get("pancakeswap_new", True)
        self.detect_factory_events = methods.get("factory_events", True)
        self.detect_mempool = methods.get("mempool", True)
        self.use_api_feeds = methods.get("api_feeds", True)
        
        # Initialiser les blockchains et leur factory
        self._init_blockchains()
        
        # Initialiser les API si nécessaire
        if self.use_api_feeds:
            self._init_api_adapters()
            
        # Intervalle de vérification des usines et du mempool
        self.factory_interval = self.detection_config.get("factory_check_interval", 10)
        self.mempool_interval = self.detection_config.get("mempool_check_interval", 5)
        
    def _init_blockchains(self):
        """Initialise les connexions aux différentes blockchains"""
        blockchain_factory = BlockchainFactory(self.config)
        
        # Initialiser les blockchains en fonction de la configuration
        chains = self.config.get_config().get("rpc", {}).get("urls", {})
        for chain_name in chains:
            try:
                # Créer un client pour chaque blockchain configurée
                client = blockchain_factory.get_blockchain_client(chain_name)
                if client:
                    self.blockchains[chain_name] = client
                    self.last_factory_check[chain_name] = 0
                    self.last_mempool_check[chain_name] = 0
                    logger.info(f"✅ Blockchain {chain_name} initialisée pour la détection de tokens")
            except Exception as e:
                logger.error(f"❌ Erreur lors de l'initialisation de la blockchain {chain_name}: {str(e)}")
                
    def _init_api_adapters(self):
        """Initialise les adaptateurs d'API externes"""
        api_configs = self.detection_config.get("external_apis", {})
        
        # Vérifier si l'API Pump.fun est activée
        pump_fun_config = api_configs.get("pump_fun", {})
        if pump_fun_config.get("enabled", False):
            try:
                from gbpbot.api_adapters.pump_fun_adapter import PumpFunAdapter
                self.api_adapters["pump_fun"] = PumpFunAdapter(pump_fun_config)
                logger.info("✅ Adaptateur Pump.fun initialisé")
            except Exception as e:
                logger.error(f"❌ Erreur lors de l'initialisation de l'adaptateur Pump.fun: {str(e)}")
                
        # Vérifier si l'API Axiom Pro est activée
        axiom_config = api_configs.get("axiom_pro", {})
        if axiom_config.get("enabled", False):
            try:
                from gbpbot.api_adapters.axiom_adapter import AxiomAdapter
                self.api_adapters["axiom_pro"] = AxiomAdapter(axiom_config)
                logger.info("✅ Adaptateur Axiom Pro initialisé")
            except Exception as e:
                logger.error(f"❌ Erreur lors de l'initialisation de l'adaptateur Axiom Pro: {str(e)}")
                
    async def start(self):
        """Démarre la détection de tokens sur toutes les sources configurées"""
        logger.info("🚀 Démarrage du détecteur de tokens...")
        
        try:
            # Initialiser les adaptateurs d'API
            for name, adapter in self.api_adapters.items():
                await adapter.initialize()
                
            # Créer les tâches de détection
            tasks = []
            
            # Tâche pour les API externes
            if self.use_api_feeds and self.api_adapters:
                tasks.append(asyncio.create_task(self._api_detection_loop()))
                
            # Tâche pour la détection via les événements de factory
            if self.detect_factory_events:
                for chain_name, blockchain in self.blockchains.items():
                    tasks.append(asyncio.create_task(
                        self._factory_events_detection_loop(chain_name, blockchain)))
                    
            # Tâche pour la détection via le mempool
            if self.detect_mempool:
                for chain_name, blockchain in self.blockchains.items():
                    tasks.append(asyncio.create_task(
                        self._mempool_detection_loop(chain_name, blockchain)))
                    
            # Attendre que toutes les tâches se terminent (ne devrait jamais arriver)
            await asyncio.gather(*tasks)
            
        except Exception as e:
            logger.error(f"❌ Erreur lors du démarrage du détecteur de tokens: {str(e)}")
            
    async def stop(self):
        """Arrête toutes les tâches de détection"""
        logger.info("🛑 Arrêt du détecteur de tokens...")
        
        # Fermer les sessions HTTP des adaptateurs d'API
        for name, adapter in self.api_adapters.items():
            await adapter.close()
            
    async def _api_detection_loop(self):
        """Boucle de détection via les API externes"""
        logger.info("🔍 Démarrage de la détection via les API externes")
        
        while True:
            try:
                start_time = time.time()
                new_tokens_detected = 0
                
                # Interroger chaque adaptateur d'API
                for name, adapter in self.api_adapters.items():
                    try:
                        # Récupérer les nouveaux tokens
                        tokens = await adapter.get_new_tokens()
                        
                        if tokens:
                            logger.debug(f"📊 {len(tokens)} nouveaux tokens détectés via {name}")
                            
                            # Traiter chaque token
                            for token_data in tokens:
                                token_chain = token_data.get("chain", "").lower()
                                token_address = token_data.get("address", "").lower()
                                
                                if (token_address and 
                                    token_chain in self.blockchains and
                                    token_address not in self.processed_addresses and
                                    token_address not in self.blacklisted_addresses):
                                    
                                    # Ajouter à la liste des tokens traités
                                    self.processed_addresses.add(token_address)
                                    
                                    # Analyser le token
                                    enriched_data = await self._enrich_token_data(token_data, token_chain)
                                    analysis_result = await self.token_analyzer.analyze_token(enriched_data)
                                    
                                    # Enregistrer le token et ses résultats d'analyse
                                    token_record = {
                                        "address": token_address,
                                        "chain": token_chain,
                                        "name": token_data.get("name", "Unknown"),
                                        "symbol": token_data.get("symbol", "???"),
                                        "detection_time": datetime.now().isoformat(),
                                        "detection_source": name,
                                        "analysis_result": analysis_result,
                                        "data": enriched_data
                                    }
                                    
                                    # Ajouter à la liste des tokens détectés
                                    self.detected_tokens.append(token_record)
                                    
                                    # Mettre à jour les statistiques
                                    self.stats["tokens_detected"] += 1
                                    self.stats["tokens_analyzed"] += 1
                                    self.stats["detection_by_source"]["api_feeds"] += 1
                                    self.stats["last_detection_time"] = datetime.now().isoformat()
                                    
                                    # Si l'analyse recommande d'acheter, émettre un événement
                                    if analysis_result.get("recommendation") == "BUY":
                                        self.stats["tokens_accepted"] += 1
                                        self.event_emitter.emit("token_detected", token_record)
                                        logger.info(f"💰 Token intéressant détecté: {token_data.get('name')} ({token_data.get('symbol')}) sur {token_chain}")
                                    else:
                                        self.stats["tokens_rejected"] += 1
                                        
                                    new_tokens_detected += 1
                                    
                    except Exception as e:
                        logger.error(f"❌ Erreur lors de la détection via {name}: {str(e)}")
                        
                # Mettre à jour les statistiques de temps de détection
                detection_time = time.time() - start_time
                self.stats["total_detection_time"] += detection_time
                if self.stats["tokens_detected"] > 0:
                    self.stats["average_detection_time"] = (
                        self.stats["total_detection_time"] / self.stats["tokens_detected"]
                    )
                    
                if new_tokens_detected > 0:
                    logger.info(f"🔍 {new_tokens_detected} nouveaux tokens analysés via les API en {detection_time:.2f}s")
                    
                # Attendre avant la prochaine vérification
                # Utiliser des intervalles différents pour chaque adaptateur
                min_interval = min(
                    adapter.config.get("update_interval", 30) 
                    for adapter in self.api_adapters.values()
                )
                await asyncio.sleep(min_interval)
                
            except Exception as e:
                logger.error(f"❌ Erreur dans la boucle de détection API: {str(e)}")
                await asyncio.sleep(30)  # Attendre avant de réessayer
                
    async def _factory_events_detection_loop(self, chain_name: str, blockchain):
        """
        Boucle de détection via les événements de factory
        
        Args:
            chain_name: Nom de la blockchain
            blockchain: Client de la blockchain
        """
        logger.info(f"🔍 Démarrage de la détection via les événements de factory sur {chain_name}")
        
        # Obtenir les adresses de factory de la configuration pour cette chaîne
        dex_config = self.config.get_config().get("dex", {})
        factory_addresses = dex_config.get("factory_addresses", {})
        
        if not factory_addresses:
            logger.warning(f"⚠️ Aucune adresse de factory configurée pour {chain_name}, désactivation de la détection par événements")
            return
            
        while True:
            try:
                now = time.time()
                # Vérifier si le temps écoulé depuis la dernière vérification est suffisant
                if now - self.last_factory_check.get(chain_name, 0) < self.factory_interval:
                    await asyncio.sleep(1)
                    continue
                    
                self.last_factory_check[chain_name] = now
                new_tokens_detected = 0
                start_time = time.time()
                
                # Pour chaque factory configurée
                for dex_name, factory_address in factory_addresses.items():
                    try:
                        # Obtenir les derniers événements de création de paire
                        events = await blockchain.get_pair_creation_events(factory_address)
                        
                        if events:
                            logger.debug(f"📊 {len(events)} événements de création de paire détectés sur {dex_name} ({chain_name})")
                            
                            # Traiter chaque événement
                            for event in events:
                                # Extraire les adresses de tokens de l'événement
                                token0 = event.get("token0", "").lower()
                                token1 = event.get("token1", "").lower()
                                pair_address = event.get("pair", "").lower()
                                
                                # Vérifier les tokens qui ne sont pas encore traités
                                for token_address in [token0, token1]:
                                    if (token_address and 
                                        token_address not in self.processed_addresses and
                                        token_address not in self.blacklisted_addresses):
                                        
                                        # Ajouter à la liste des tokens traités
                                        self.processed_addresses.add(token_address)
                                        
                                        # Obtenir les informations du token
                                        token_data = await blockchain.get_token_info(token_address)
                                        
                                        if token_data:
                                            # Enrichir les données du token
                                            token_data["pair_address"] = pair_address
                                            token_data["dex"] = dex_name
                                            token_data["chain"] = chain_name
                                            token_data["address"] = token_address
                                            
                                            # Analyser le token
                                            enriched_data = await self._enrich_token_data(token_data, chain_name)
                                            analysis_result = await self.token_analyzer.analyze_token(enriched_data)
                                            
                                            # Enregistrer le token et ses résultats d'analyse
                                            token_record = {
                                                "address": token_address,
                                                "chain": chain_name,
                                                "name": token_data.get("name", "Unknown"),
                                                "symbol": token_data.get("symbol", "???"),
                                                "detection_time": datetime.now().isoformat(),
                                                "detection_source": f"factory_{dex_name}",
                                                "analysis_result": analysis_result,
                                                "data": enriched_data
                                            }
                                            
                                            # Ajouter à la liste des tokens détectés
                                            self.detected_tokens.append(token_record)
                                            
                                            # Mettre à jour les statistiques
                                            self.stats["tokens_detected"] += 1
                                            self.stats["tokens_analyzed"] += 1
                                            self.stats["detection_by_source"]["factory_events"] += 1
                                            self.stats["last_detection_time"] = datetime.now().isoformat()
                                            
                                            # Si l'analyse recommande d'acheter, émettre un événement
                                            if analysis_result.get("recommendation") == "BUY":
                                                self.stats["tokens_accepted"] += 1
                                                self.event_emitter.emit("token_detected", token_record)
                                                logger.info(f"💰 Token intéressant détecté via factory: {token_data.get('name')} ({token_data.get('symbol')}) sur {chain_name}")
                                            else:
                                                self.stats["tokens_rejected"] += 1
                                                
                                            new_tokens_detected += 1
                                    
                    except Exception as e:
                        logger.error(f"❌ Erreur lors de la détection via {dex_name} sur {chain_name}: {str(e)}")
                        
                # Mettre à jour les statistiques de temps de détection
                detection_time = time.time() - start_time
                self.stats["total_detection_time"] += detection_time
                if self.stats["tokens_detected"] > 0:
                    self.stats["average_detection_time"] = (
                        self.stats["total_detection_time"] / self.stats["tokens_detected"]
                    )
                    
                if new_tokens_detected > 0:
                    logger.info(f"🔍 {new_tokens_detected} nouveaux tokens analysés via factory sur {chain_name} en {detection_time:.2f}s")
                    
                # Attendre avant la prochaine vérification
                await asyncio.sleep(self.factory_interval)
                
            except Exception as e:
                logger.error(f"❌ Erreur dans la boucle de détection factory sur {chain_name}: {str(e)}")
                await asyncio.sleep(30)  # Attendre avant de réessayer
                
    async def _mempool_detection_loop(self, chain_name: str, blockchain):
        """
        Boucle de détection via le mempool
        
        Args:
            chain_name: Nom de la blockchain
            blockchain: Client de la blockchain
        """
        logger.info(f"🔍 Démarrage de la détection via le mempool sur {chain_name}")
        
        # Vérifier si la blockchain supporte la surveillance du mempool
        if not hasattr(blockchain, "monitor_mempool") or not callable(getattr(blockchain, "monitor_mempool")):
            logger.warning(f"⚠️ La blockchain {chain_name} ne supporte pas la surveillance du mempool, désactivation")
            return
            
        try:
            # Démarrer la surveillance du mempool
            await blockchain.monitor_mempool(callback=self._mempool_callback)
        except Exception as e:
            logger.error(f"❌ Erreur lors du démarrage de la surveillance du mempool sur {chain_name}: {str(e)}")
            
    async def _mempool_callback(self, chain_name: str, tx_data: Dict):
        """
        Callback pour traiter les transactions du mempool
        
        Args:
            chain_name: Nom de la blockchain
            tx_data: Données de la transaction
        """
        try:
            # Extraire l'ID de la transaction
            tx_hash = tx_data.get("hash", "").lower()
            
            # Vérifier si la transaction a déjà été traitée
            if tx_hash in self.mempool_processed:
                return
                
            self.mempool_processed.add(tx_hash)
            
            # Limiter la taille de l'ensemble des transactions traitées
            if len(self.mempool_processed) > 10000:
                self.mempool_processed = set(list(self.mempool_processed)[-5000:])
                
            # Analyser la transaction pour détecter les interactions avec les routers et factories
            blockchain = self.blockchains.get(chain_name)
            if not blockchain:
                return
                
            # Vérifier si c'est une création de paire ou une interaction avec un router
            is_pair_creation, token_address = await blockchain.analyze_transaction(tx_data)
            
            if is_pair_creation and token_address:
                token_address = token_address.lower()
                
                # Vérifier si le token a déjà été traité
                if (token_address in self.processed_addresses or 
                    token_address in self.blacklisted_addresses):
                    return
                    
                # Ajouter à la liste des tokens traités
                self.processed_addresses.add(token_address)
                
                # Obtenir les informations du token
                token_data = await blockchain.get_token_info(token_address)
                
                if token_data:
                    token_data["chain"] = chain_name
                    token_data["address"] = token_address
                    token_data["tx_hash"] = tx_hash
                    
                    # Analyser le token
                    enriched_data = await self._enrich_token_data(token_data, chain_name)
                    analysis_result = await self.token_analyzer.analyze_token(enriched_data)
                    
                    # Enregistrer le token et ses résultats d'analyse
                    token_record = {
                        "address": token_address,
                        "chain": chain_name,
                        "name": token_data.get("name", "Unknown"),
                        "symbol": token_data.get("symbol", "???"),
                        "detection_time": datetime.now().isoformat(),
                        "detection_source": "mempool",
                        "analysis_result": analysis_result,
                        "data": enriched_data
                    }
                    
                    # Ajouter à la liste des tokens détectés
                    self.detected_tokens.append(token_record)
                    
                    # Mettre à jour les statistiques
                    self.stats["tokens_detected"] += 1
                    self.stats["tokens_analyzed"] += 1
                    self.stats["detection_by_source"]["mempool"] += 1
                    self.stats["last_detection_time"] = datetime.now().isoformat()
                    
                    # Si l'analyse recommande d'acheter, émettre un événement
                    if analysis_result.get("recommendation") == "BUY":
                        self.stats["tokens_accepted"] += 1
                        self.event_emitter.emit("token_detected", token_record)
                        logger.info(f"💰 Token intéressant détecté via mempool: {token_data.get('name')} ({token_data.get('symbol')}) sur {chain_name}")
                    else:
                        self.stats["tokens_rejected"] += 1
                        
        except Exception as e:
            logger.error(f"❌ Erreur lors du traitement d'une transaction du mempool: {str(e)}")
            
    async def _enrich_token_data(self, token_data: Dict, chain_name: str) -> Dict:
        """
        Enrichit les données d'un token avec des informations supplémentaires
        
        Args:
            token_data: Données du token
            chain_name: Nom de la blockchain
            
        Returns:
            Dict: Données enrichies du token
        """
        try:
            # Créer une copie des données pour ne pas modifier l'original
            enriched_data = token_data.copy()
            
            # Obtenir le client blockchain correspondant
            blockchain = self.blockchains.get(chain_name)
            if not blockchain:
                return enriched_data
                
            token_address = token_data.get("address", "").lower()
            if not token_address:
                return enriched_data
                
            # Ajouter des informations manquantes si nécessaire
            if "name" not in enriched_data or "symbol" not in enriched_data:
                basic_info = await blockchain.get_token_basic_info(token_address)
                enriched_data.update(basic_info)
                
            # Vérifier et ajouter la liquidité
            if "liquidity" not in enriched_data:
                liquidity = await blockchain.get_token_liquidity(token_address)
                enriched_data["liquidity"] = liquidity
                
            # Vérifier le volume si absent
            if "volume_24h" not in enriched_data:
                volume = await blockchain.get_token_volume(token_address, period=86400)  # 24h en secondes
                enriched_data["volume_24h"] = volume
                
            # Ajouter des données de prix si absentes
            if "price" not in enriched_data:
                price = await blockchain.get_token_price(token_address)
                enriched_data["price"] = price
                
            # Vérifier le honeypot si configuré
            if self.config.get_config().get("sniping", {}).get("honeypot_check", True):
                is_honeypot, honeypot_info = await blockchain.check_honeypot(token_address)
                enriched_data["is_honeypot"] = is_honeypot
                enriched_data["honeypot_info"] = honeypot_info
                
                if is_honeypot:
                    self.stats["honeypots_detected"] += 1
                    
            # Vérifier les informations sociales via les adaptateurs d'API si disponibles
            for name, adapter in self.api_adapters.items():
                if hasattr(adapter, "get_token_info") and callable(getattr(adapter, "get_token_info")):
                    try:
                        api_token_info = await adapter.get_token_info(token_address, chain=chain_name)
                        if api_token_info:
                            # Fusionner certains champs mais ne pas écraser les données existantes
                            for key in ["website", "twitter", "telegram", "description", "verified"]:
                                if key in api_token_info and key not in enriched_data:
                                    enriched_data[key] = api_token_info[key]
                                    
                            # Ajouter les données de chart si disponibles
                            if "chart_data" in api_token_info and "chart_data" not in enriched_data:
                                enriched_data["chart_data"] = api_token_info["chart_data"]
                    except Exception as e:
                        logger.debug(f"⚠️ Impossible d'obtenir les infos de {name} pour {token_address}: {str(e)}")
                        
            return enriched_data
            
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'enrichissement des données pour {token_data.get('address', 'unknown')}: {str(e)}")
            return token_data
            
    def get_statistics(self) -> Dict:
        """
        Récupère les statistiques de détection
        
        Returns:
            Dict: Statistiques de détection
        """
        return self.stats
        
    def get_detected_tokens(self, limit: int = 50) -> List[Dict]:
        """
        Récupère la liste des tokens détectés
        
        Args:
            limit: Nombre maximum de tokens à retourner
            
        Returns:
            List[Dict]: Liste des tokens détectés
        """
        return list(self.detected_tokens)[-limit:]
        
    def reset_statistics(self):
        """Réinitialise les statistiques de détection"""
        self.stats = {
            "tokens_detected": 0,
            "tokens_analyzed": 0,
            "tokens_accepted": 0,
            "tokens_rejected": 0,
            "honeypots_detected": 0,
            "detection_by_source": {
                "factory_events": 0,
                "mempool": 0,
                "api_feeds": 0,
                "pancakeswap": 0,
                "manual": 0
            },
            "last_detection_time": None,
            "average_detection_time": 0.0,
            "total_detection_time": 0.0
        }
        
    def manually_add_token(self, chain_name: str, token_address: str) -> Dict:
        """
        Ajoute manuellement un token pour analyse
        
        Args:
            chain_name: Nom de la blockchain
            token_address: Adresse du token
            
        Returns:
            Dict: Résultat de l'opération
        """
        token_address = token_address.lower()
        
        # Vérifier si le token est déjà traité
        if token_address in self.processed_addresses:
            return {
                "success": False,
                "message": "Ce token a déjà été détecté et analysé"
            }
            
        # Vérifier si le token est blacklisté
        if token_address in self.blacklisted_addresses:
            return {
                "success": False,
                "message": "Ce token est dans la liste noire"
            }
            
        # Vérifier si la blockchain est supportée
        blockchain = self.blockchains.get(chain_name)
        if not blockchain:
            return {
                "success": False,
                "message": f"La blockchain {chain_name} n'est pas supportée"
            }
            
        # Ajouter la tâche d'analyse
        asyncio.create_task(self._analyze_manual_token(chain_name, token_address))
        
        return {
            "success": True,
            "message": f"Token {token_address} ajouté pour analyse sur {chain_name}"
        }
        
    async def _analyze_manual_token(self, chain_name: str, token_address: str):
        """
        Analyse un token ajouté manuellement
        
        Args:
            chain_name: Nom de la blockchain
            token_address: Adresse du token
        """
        try:
            # Obtenir le client blockchain
            blockchain = self.blockchains.get(chain_name)
            if not blockchain:
                return
                
            # Ajouter à la liste des tokens traités
            self.processed_addresses.add(token_address)
            
            # Obtenir les informations du token
            token_data = await blockchain.get_token_info(token_address)
            
            if token_data:
                token_data["chain"] = chain_name
                token_data["address"] = token_address
                
                # Analyser le token
                enriched_data = await self._enrich_token_data(token_data, chain_name)
                analysis_result = await self.token_analyzer.analyze_token(enriched_data)
                
                # Enregistrer le token et ses résultats d'analyse
                token_record = {
                    "address": token_address,
                    "chain": chain_name,
                    "name": token_data.get("name", "Unknown"),
                    "symbol": token_data.get("symbol", "???"),
                    "detection_time": datetime.now().isoformat(),
                    "detection_source": "manual",
                    "analysis_result": analysis_result,
                    "data": enriched_data
                }
                
                # Ajouter à la liste des tokens détectés
                self.detected_tokens.append(token_record)
                
                # Mettre à jour les statistiques
                self.stats["tokens_detected"] += 1
                self.stats["tokens_analyzed"] += 1
                self.stats["detection_by_source"]["manual"] += 1
                self.stats["last_detection_time"] = datetime.now().isoformat()
                
                # Si l'analyse recommande d'acheter, émettre un événement
                if analysis_result.get("recommendation") == "BUY":
                    self.stats["tokens_accepted"] += 1
                    self.event_emitter.emit("token_detected", token_record)
                    logger.info(f"💰 Token intéressant détecté manuellement: {token_data.get('name')} ({token_data.get('symbol')}) sur {chain_name}")
                else:
                    self.stats["tokens_rejected"] += 1
                    logger.info(f"❌ Token rejeté par l'analyse: {token_data.get('name')} ({token_data.get('symbol')}) sur {chain_name}")
                    
                return token_record
                
        except Exception as e:
            logger.error(f"❌ Erreur lors de l'analyse manuelle du token {token_address}: {str(e)}")
            
    def add_event_listener(self, event_name: str, callback):
        """
        Ajoute un écouteur d'événements
        
        Args:
            event_name: Nom de l'événement
            callback: Fonction de callback
        """
        self.event_emitter.on(event_name, callback)
        
    def remove_event_listener(self, event_name: str, callback):
        """
        Supprime un écouteur d'événements
        
        Args:
            event_name: Nom de l'événement
            callback: Fonction de callback
        """
        self.event_emitter.off(event_name, callback) 