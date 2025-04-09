#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Moniteur de Marché pour GBPBot
=============================

Ce module fournit une surveillance en temps réel des marchés crypto avec :
- Détection des opportunités d'arbitrage
- Surveillance des nouveaux tokens et listings
- Alertes sur mouvements de prix
- Détection des whales
- Analyse des tendances
"""

import os
import json
import time
import logging
import asyncio
from typing import Dict, List, Any, Optional, Union, Tuple, Set
from datetime import datetime, timedelta
import threading
import queue
import pandas as pd
import numpy as np
from dataclasses import dataclass

from gbpbot.utils.logger import setup_logger

# Configuration du logger
logger = setup_logger("MarketMonitor", logging.INFO)

@dataclass
class MarketOpportunity:
    """Opportunité détectée sur le marché"""
    id: str
    type: str  # "arbitrage", "new_token", "price_movement", "whale_movement"
    blockchain: str
    token_address: str
    token_symbol: str
    timestamp: datetime
    expiration: datetime
    priority: int  # 1-5, 5 étant la plus haute
    details: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convertit l'opportunité en dictionnaire"""
        return {
            "id": self.id,
            "type": self.type,
            "blockchain": self.blockchain,
            "token_address": self.token_address,
            "token_symbol": self.token_symbol,
            "timestamp": self.timestamp.isoformat(),
            "expiration": self.expiration.isoformat(),
            "priority": self.priority,
            "details": self.details,
            "age_seconds": (datetime.now() - self.timestamp).total_seconds()
        }
    
    def is_expired(self) -> bool:
        """Vérifie si l'opportunité est expirée"""
        return datetime.now() > self.expiration


class MarketMonitor:
    """
    Moniteur de marché qui surveille en temps réel les prix et activités 
    pour détecter des opportunités de trading.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialise le moniteur de marché.
        
        Args:
            config: Configuration du moniteur
        """
        self.config = config
        self.blockchain_clients = {}
        self.running = False
        self.alert_handlers = []
        
        # File d'attente des opportunités détectées
        self.opportunity_queue = asyncio.Queue()
        
        # Liste des opportunités actives
        self.active_opportunities: Dict[str, MarketOpportunity] = {}
        
        # Tokens en surveillance
        self.watched_tokens: Dict[str, Dict[str, Any]] = {}
        
        # Paramètres de surveillance
        self.price_movement_threshold = float(os.environ.get("PRICE_MOVEMENT_THRESHOLD", "5.0"))  # 5%
        self.arbitrage_min_diff = float(os.environ.get("ARBITRAGE_MIN_DIFF", "0.5"))  # 0.5%
        self.new_token_max_age = int(os.environ.get("NEW_TOKEN_MAX_AGE", "3600"))  # 1 heure
        self.whale_min_usd = float(os.environ.get("WHALE_MIN_USD", "10000"))  # 10,000 USD
        
        # Cache des prix
        self.price_cache = {}
        
        # Compteurs et statistiques
        self.stats = {
            "opportunities_detected": 0,
            "opportunities_processed": 0,
            "opportunities_by_type": {
                "arbitrage": 0,
                "new_token": 0,
                "price_movement": 0,
                "whale_movement": 0
            },
            "last_activity": datetime.now().isoformat()
        }
        
        logger.info("Moniteur de marché initialisé")
    
    async def initialize(self):
        """Initialise les clients et ressources nécessaires"""
        # Initialiser les clients blockchain
        for chain in self.config.get("chains", []):
            client = await self._initialize_blockchain_client(chain)
            if client:
                self.blockchain_clients[chain["name"]] = client
        
        # Charger les tokens à surveiller
        await self._load_watched_tokens()
        
        logger.info(f"Moniteur de marché initialisé avec {len(self.blockchain_clients)} clients blockchain")
    
    async def start(self):
        """Démarre la surveillance du marché"""
        if self.running:
            logger.warning("Le moniteur de marché est déjà en cours d'exécution")
            return
        
        # Initialiser si nécessaire
        if not self.blockchain_clients:
            await self.initialize()
        
        self.running = True
        logger.info("Démarrage du moniteur de marché")
        
        # Démarrer les tâches de surveillance
        asyncio.create_task(self._monitor_price_movements())
        asyncio.create_task(self._monitor_arbitrage_opportunities())
        asyncio.create_task(self._monitor_new_tokens())
        asyncio.create_task(self._monitor_whale_movements())
        asyncio.create_task(self._process_opportunities())
        
        # Mettre à jour les statistiques
        self.stats["last_activity"] = datetime.now().isoformat()
    
    async def stop(self):
        """Arrête la surveillance du marché"""
        if not self.running:
            logger.warning("Le moniteur de marché n'est pas en cours d'exécution")
            return
        
        self.running = False
        logger.info("Arrêt du moniteur de marché")
    
    def register_alert_handler(self, handler):
        """
        Enregistre un gestionnaire d'alertes pour les opportunités.
        
        Args:
            handler: Fonction à appeler lors de la détection d'une opportunité
        """
        self.alert_handlers.append(handler)
        logger.info(f"Gestionnaire d'alertes enregistré ({len(self.alert_handlers)} total)")
    
    async def get_active_opportunities(self, opp_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Obtient la liste des opportunités actives.
        
        Args:
            opp_type: Type d'opportunité (None pour toutes)
            
        Returns:
            Liste des opportunités actives
        """
        # Filtrer les opportunités expirées
        for opp_id in list(self.active_opportunities.keys()):
            if self.active_opportunities[opp_id].is_expired():
                del self.active_opportunities[opp_id]
        
        # Filtrer par type si spécifié
        if opp_type:
            return [
                opp.to_dict() for opp in self.active_opportunities.values()
                if opp.type == opp_type
            ]
        
        return [opp.to_dict() for opp in self.active_opportunities.values()]
    
    async def add_watch_token(self, token_data: Dict[str, Any]) -> bool:
        """
        Ajoute un token à surveiller.
        
        Args:
            token_data: Données du token
            
        Returns:
            True si ajouté avec succès
        """
        token_address = token_data.get("address", "").lower()
        blockchain = token_data.get("blockchain", "").lower()
        
        if not token_address or not blockchain:
            logger.error("Adresse de token ou blockchain manquante")
            return False
        
        key = f"{blockchain}:{token_address}"
        
        # Vérifier si le token est déjà surveillé
        if key in self.watched_tokens:
            logger.info(f"Le token {token_address} est déjà surveillé")
            return True
        
        # Ajouter le token
        self.watched_tokens[key] = {
            "address": token_address,
            "blockchain": blockchain,
            "symbol": token_data.get("symbol", "UNKNOWN"),
            "added_at": datetime.now().isoformat(),
            "last_price": token_data.get("price", 0),
            "last_update": datetime.now().isoformat()
        }
        
        # Sauvegarder la liste des tokens surveillés
        await self._save_watched_tokens()
        
        logger.info(f"Token {token_address} ajouté à la surveillance")
        return True
    
    async def remove_watch_token(self, token_address: str, blockchain: str) -> bool:
        """
        Retire un token de la surveillance.
        
        Args:
            token_address: Adresse du token
            blockchain: Blockchain du token
            
        Returns:
            True si retiré avec succès
        """
        key = f"{blockchain.lower()}:{token_address.lower()}"
        
        if key in self.watched_tokens:
            del self.watched_tokens[key]
            await self._save_watched_tokens()
            logger.info(f"Token {token_address} retiré de la surveillance")
            return True
        
        logger.warning(f"Token {token_address} non trouvé dans la liste de surveillance")
        return False
    
    async def get_token_price(self, token_address: str, blockchain: str, force_refresh: bool = False) -> Optional[float]:
        """
        Obtient le prix actuel d'un token.
        
        Args:
            token_address: Adresse du token
            blockchain: Blockchain du token
            force_refresh: Forcer le rafraîchissement du cache
            
        Returns:
            Prix du token ou None en cas d'erreur
        """
        key = f"{blockchain.lower()}:{token_address.lower()}"
        
        # Vérifier le cache (validité de 60 secondes)
        if not force_refresh and key in self.price_cache:
            cache_entry = self.price_cache[key]
            if datetime.now().timestamp() - cache_entry["timestamp"] < 60:
                return cache_entry["price"]
        
        # Récupérer le prix frais
        try:
            if blockchain not in self.blockchain_clients:
                logger.warning(f"Client blockchain non disponible pour {blockchain}")
                return None
            
            client = self.blockchain_clients[blockchain]
            price = await client.get_token_price(token_address)
            
            # Mettre à jour le cache
            self.price_cache[key] = {
                "timestamp": datetime.now().timestamp(),
                "price": price
            }
            
            # Mettre à jour le prix du token surveillé
            if key in self.watched_tokens:
                self.watched_tokens[key]["last_price"] = price
                self.watched_tokens[key]["last_update"] = datetime.now().isoformat()
            
            return price
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du prix pour {token_address}: {str(e)}")
            return None
    
    async def _process_opportunities(self):
        """Traite les opportunités détectées dans la file d'attente"""
        logger.info("Démarrage du traitement des opportunités")
        
        while self.running:
            try:
                # Récupérer une opportunité de la file d'attente
                opportunity = await self.opportunity_queue.get()
                
                # Ajouter aux opportunités actives
                self.active_opportunities[opportunity.id] = opportunity
                
                # Mettre à jour les statistiques
                self.stats["opportunities_processed"] += 1
                self.stats["opportunities_by_type"][opportunity.type] += 1
                self.stats["last_activity"] = datetime.now().isoformat()
                
                # Notifier les gestionnaires d'alertes
                for handler in self.alert_handlers:
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            await handler(opportunity)
                        else:
                            handler(opportunity)
                    except Exception as e:
                        logger.error(f"Erreur dans le gestionnaire d'alertes: {str(e)}")
                
                # Marquer comme traitée
                self.opportunity_queue.task_done()
                
                logger.info(f"Opportunité {opportunity.id} traitée ({opportunity.type})")
            
            except Exception as e:
                logger.error(f"Erreur dans le traitement des opportunités: {str(e)}")
                await asyncio.sleep(1)
    
    async def _monitor_price_movements(self):
        """Surveille les mouvements de prix des tokens surveillés"""
        logger.info("Démarrage de la surveillance des mouvements de prix")
        
        while self.running:
            try:
                # Parcourir tous les tokens surveillés
                for key, token_data in list(self.watched_tokens.items()):
                    try:
                        blockchain = token_data["blockchain"]
                        token_address = token_data["address"]
                        
                        # Récupérer le dernier prix
                        current_price = await self.get_token_price(token_address, blockchain)
                        
                        if current_price is None:
                            continue
                        
                        # Calculer le mouvement de prix
                        last_price = token_data.get("last_price", 0)
                        if last_price > 0:
                            price_change_percent = (current_price - last_price) / last_price * 100
                            
                            # Détecter un mouvement significatif
                            if abs(price_change_percent) >= self.price_movement_threshold:
                                # Créer une opportunité
                                opportunity = MarketOpportunity(
                                    id=f"price_movement_{token_address}_{int(time.time())}",
                                    type="price_movement",
                                    blockchain=blockchain,
                                    token_address=token_address,
                                    token_symbol=token_data.get("symbol", "UNKNOWN"),
                                    timestamp=datetime.now(),
                                    expiration=datetime.now() + timedelta(minutes=10),
                                    priority=4 if abs(price_change_percent) > 20 else 3,
                                    details={
                                        "current_price": current_price,
                                        "previous_price": last_price,
                                        "change_percent": price_change_percent,
                                        "direction": "up" if price_change_percent > 0 else "down"
                                    }
                                )
                                
                                # Ajouter à la file d'attente
                                await self.opportunity_queue.put(opportunity)
                                self.stats["opportunities_detected"] += 1
                                
                                logger.info(f"Mouvement de prix détecté pour {token_data.get('symbol')}: {price_change_percent:.2f}%")
                    
                    except Exception as e:
                        logger.error(f"Erreur lors de la surveillance du prix pour {key}: {str(e)}")
                
                # Pause avant la prochaine vérification
                await asyncio.sleep(5)
            
            except Exception as e:
                logger.error(f"Erreur dans la surveillance des prix: {str(e)}")
                await asyncio.sleep(5)
    
    async def _monitor_arbitrage_opportunities(self):
        """Surveille les opportunités d'arbitrage entre DEX"""
        logger.info("Démarrage de la surveillance des opportunités d'arbitrage")
        
        while self.running:
            try:
                # Pour chaque blockchain supportée
                for blockchain, client in self.blockchain_clients.items():
                    # Pour chaque token surveillé sur cette blockchain
                    watched_on_chain = [
                        token_data for key, token_data in self.watched_tokens.items()
                        if token_data["blockchain"] == blockchain
                    ]
                    
                    for token_data in watched_on_chain:
                        token_address = token_data["address"]
                        
                        # Récupérer les prix sur différents DEX
                        try:
                            dex_prices = await client.get_token_prices_across_dexes(token_address)
                            
                            if not dex_prices or len(dex_prices) < 2:
                                continue
                            
                            # Chercher les écarts de prix
                            for i, (dex1, price1) in enumerate(dex_prices.items()):
                                for dex2, price2 in list(dex_prices.items())[i+1:]:
                                    # Calculer la différence en pourcentage
                                    if price1 > 0 and price2 > 0:
                                        if price1 > price2:
                                            diff_percent = (price1 - price2) / price2 * 100
                                            buy_dex, sell_dex = dex2, dex1
                                            buy_price, sell_price = price2, price1
                                        else:
                                            diff_percent = (price2 - price1) / price1 * 100
                                            buy_dex, sell_dex = dex1, dex2
                                            buy_price, sell_price = price1, price2
                                        
                                        # Si l'écart est suffisant
                                        if diff_percent >= self.arbitrage_min_diff:
                                            # Créer une opportunité
                                            opportunity = MarketOpportunity(
                                                id=f"arbitrage_{token_address}_{buy_dex}_{sell_dex}_{int(time.time())}",
                                                type="arbitrage",
                                                blockchain=blockchain,
                                                token_address=token_address,
                                                token_symbol=token_data.get("symbol", "UNKNOWN"),
                                                timestamp=datetime.now(),
                                                expiration=datetime.now() + timedelta(minutes=2),
                                                priority=3 if diff_percent < 1 else (4 if diff_percent < 3 else 5),
                                                details={
                                                    "buy_dex": buy_dex,
                                                    "sell_dex": sell_dex,
                                                    "buy_price": buy_price,
                                                    "sell_price": sell_price,
                                                    "diff_percent": diff_percent
                                                }
                                            )
                                            
                                            # Ajouter à la file d'attente
                                            await self.opportunity_queue.put(opportunity)
                                            self.stats["opportunities_detected"] += 1
                                            
                                            logger.info(f"Opportunité d'arbitrage détectée pour {token_data.get('symbol')}: {diff_percent:.2f}% entre {buy_dex} et {sell_dex}")
                        
                        except Exception as e:
                            logger.error(f"Erreur lors de la vérification d'arbitrage pour {token_address}: {str(e)}")
                
                # Pause avant la prochaine vérification
                await asyncio.sleep(10)
            
            except Exception as e:
                logger.error(f"Erreur dans la surveillance d'arbitrage: {str(e)}")
                await asyncio.sleep(10)
    
    async def _monitor_new_tokens(self):
        """Surveille les nouveaux tokens créés"""
        logger.info("Démarrage de la surveillance des nouveaux tokens")
        
        # Ensemble des tokens déjà détectés
        detected_tokens = set()
        
        while self.running:
            try:
                # Pour chaque blockchain supportée
                for blockchain, client in self.blockchain_clients.items():
                    try:
                        # Récupérer les nouveaux tokens
                        new_tokens = await client.get_new_tokens(max_age_seconds=self.new_token_max_age)
                        
                        for token in new_tokens:
                            token_address = token.get("address", "").lower()
                            
                            # Vérifier si déjà détecté
                            token_key = f"{blockchain}:{token_address}"
                            if token_key in detected_tokens:
                                continue
                            
                            # Marquer comme détecté
                            detected_tokens.add(token_key)
                            
                            # Créer une opportunité
                            opportunity = MarketOpportunity(
                                id=f"new_token_{token_address}_{int(time.time())}",
                                type="new_token",
                                blockchain=blockchain,
                                token_address=token_address,
                                token_symbol=token.get("symbol", "UNKNOWN"),
                                timestamp=datetime.now(),
                                expiration=datetime.now() + timedelta(hours=1),
                                priority=2,
                                details={
                                    "name": token.get("name", ""),
                                    "created_at": token.get("created_at", ""),
                                    "initial_price": token.get("initial_price", 0),
                                    "initial_liquidity": token.get("initial_liquidity", 0),
                                    "creator": token.get("creator", ""),
                                    "source_dex": token.get("source_dex", "")
                                }
                            )
                            
                            # Ajouter à la file d'attente
                            await self.opportunity_queue.put(opportunity)
                            self.stats["opportunities_detected"] += 1
                            
                            logger.info(f"Nouveau token détecté: {token.get('symbol', 'UNKNOWN')} ({token_address})")
                    
                    except Exception as e:
                        logger.error(f"Erreur lors de la détection de nouveaux tokens sur {blockchain}: {str(e)}")
                
                # Nettoyage des tokens trop anciens (plus de 24h)
                current_time = time.time()
                to_remove = set()
                for token_key in detected_tokens:
                    token_time = int(token_key.split("_")[-1]) if "_" in token_key else 0
                    if current_time - token_time > 86400:  # 24 heures
                        to_remove.add(token_key)
                
                for token_key in to_remove:
                    detected_tokens.remove(token_key)
                
                # Pause avant la prochaine vérification
                await asyncio.sleep(30)
            
            except Exception as e:
                logger.error(f"Erreur dans la surveillance des nouveaux tokens: {str(e)}")
                await asyncio.sleep(30)
    
    async def _monitor_whale_movements(self):
        """Surveille les mouvements des whales"""
        logger.info("Démarrage de la surveillance des mouvements de whales")
        
        while self.running:
            try:
                # Pour chaque blockchain supportée
                for blockchain, client in self.blockchain_clients.items():
                    try:
                        # Récupérer les mouvements récents des whales
                        whale_movements = await client.get_whale_movements(min_usd_value=self.whale_min_usd)
                        
                        for movement in whale_movements:
                            token_address = movement.get("token_address", "").lower()
                            
                            # Créer une opportunité
                            opportunity = MarketOpportunity(
                                id=f"whale_{token_address}_{movement.get('tx_hash', '')}",
                                type="whale_movement",
                                blockchain=blockchain,
                                token_address=token_address,
                                token_symbol=movement.get("token_symbol", "UNKNOWN"),
                                timestamp=datetime.now(),
                                expiration=datetime.now() + timedelta(minutes=30),
                                priority=3,
                                details={
                                    "wallet_address": movement.get("wallet_address", ""),
                                    "action": movement.get("action", ""),  # buy, sell
                                    "amount": movement.get("amount", 0),
                                    "amount_usd": movement.get("amount_usd", 0),
                                    "tx_hash": movement.get("tx_hash", ""),
                                    "dex": movement.get("dex", "")
                                }
                            )
                            
                            # Ajouter à la file d'attente
                            await self.opportunity_queue.put(opportunity)
                            self.stats["opportunities_detected"] += 1
                            
                            logger.info(f"Mouvement de whale détecté: {movement.get('action')} {movement.get('amount_usd')}$ de {movement.get('token_symbol')}")
                    
                    except Exception as e:
                        logger.error(f"Erreur lors de la détection des mouvements de whales sur {blockchain}: {str(e)}")
                
                # Pause avant la prochaine vérification
                await asyncio.sleep(15)
            
            except Exception as e:
                logger.error(f"Erreur dans la surveillance des whales: {str(e)}")
                await asyncio.sleep(15)
    
    async def _load_watched_tokens(self):
        """Charge la liste des tokens surveillés depuis le stockage"""
        try:
            # Déterminer le chemin du fichier
            file_path = os.path.join(os.path.dirname(__file__), "data", "watched_tokens.json")
            
            if os.path.exists(file_path):
                with open(file_path, "r") as f:
                    self.watched_tokens = json.load(f)
                    logger.info(f"Chargement de {len(self.watched_tokens)} tokens surveillés")
            else:
                logger.info("Aucun token surveillé trouvé, initialisation d'une liste vide")
                self.watched_tokens = {}
        except Exception as e:
            logger.error(f"Erreur lors du chargement des tokens surveillés: {str(e)}")
            self.watched_tokens = {}
    
    async def _save_watched_tokens(self):
        """Sauvegarde la liste des tokens surveillés"""
        try:
            # Déterminer le chemin du fichier
            file_path = os.path.join(os.path.dirname(__file__), "data", "watched_tokens.json")
            
            # S'assurer que le répertoire existe
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, "w") as f:
                json.dump(self.watched_tokens, f, indent=2)
            
            logger.info(f"Sauvegarde de {len(self.watched_tokens)} tokens surveillés")
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des tokens surveillés: {str(e)}")
    
    async def _initialize_blockchain_client(self, chain_config: Dict[str, Any]):
        """Initialise un client blockchain"""
        try:
            chain_name = chain_config.get("name", "").lower()
            
            # Implémenter selon le besoin en fonction des blockchains supportées
            # Exemple simplifié:
            if chain_name == "avalanche":
                # from gbpbot.blockchain.avalanche import AvalancheClient
                # return AvalancheClient(chain_config)
                pass
            elif chain_name == "solana":
                # from gbpbot.blockchain.solana import SolanaClient
                # return SolanaClient(chain_config)
                pass
            elif chain_name == "ethereum":
                # from gbpbot.blockchain.ethereum import EthereumClient
                # return EthereumClient(chain_config)
                pass
            elif chain_name == "sonic":
                # from gbpbot.blockchain.sonic import SonicClient
                # return SonicClient(chain_config)
                pass
            else:
                logger.warning(f"Blockchain non supportée: {chain_name}")
                return None
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du client {chain_config.get('name')}: {str(e)}")
            return None 