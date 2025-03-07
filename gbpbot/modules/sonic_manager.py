#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestionnaire Sonic pour GBPBot
==============================

Ce module centralise les fonctionnalités de trading sur Sonic,
coordonnant le sniping, l'arbitrage et les autres stratégies.
"""

import os
import logging
import asyncio
from typing import Dict, List, Any, Optional, Union, Tuple
from datetime import datetime

from gbpbot.config.config_manager import config_manager
from gbpbot.clients.blockchain_client_factory import BlockchainClientFactory
from gbpbot.modules.sonic_sniper import SonicSniper
from gbpbot.utils.notification_manager import send_notification

# Configuration du logger
logger = logging.getLogger("gbpbot.modules.sonic_manager")

class SonicManager:
    """
    Gestionnaire centralisé pour les opérations sur Sonic.
    
    Cette classe coordonne les différents modules de trading sur Sonic,
    offrant une interface unifiée pour les démarrer, les arrêter et les surveiller.
    """
    
    def __init__(self):
        """
        Initialise le gestionnaire Sonic.
        """
        logger.info("Initialisation du gestionnaire Sonic")
        
        # Charger la configuration
        self.config = config_manager.get_config().get("blockchains", {}).get("sonic", {})
        
        # Vérifier si Sonic est activé
        if not self.config.get("enabled", False):
            logger.warning("Sonic est désactivé dans la configuration")
            self.enabled = False
            return
        
        self.enabled = True
        
        # Client blockchain
        self.client = None
        self.init_client()
        
        # Modules
        self.sniper = None
        self.arbitrage_engine = None  # À implémenter ultérieurement
        
        # État du gestionnaire
        self.running = False
        
        # Statistiques
        self.stats = {
            "last_startup": None,
            "uptime_seconds": 0,
            "total_profit": 0.0,
            "sniper_active": False,
            "arbitrage_active": False,
        }
        
        # Initialiser les modules
        self._init_modules()
        
        logger.info("Gestionnaire Sonic initialisé")
    
    def init_client(self):
        """
        Initialise le client blockchain pour Sonic.
        """
        try:
            # Créer le client Sonic
            self.client = BlockchainClientFactory.create_client("sonic")
            
            if not self.client:
                logger.error("Échec de l'initialisation du client Sonic")
                return False
            
            logger.info("Client Sonic initialisé avec succès")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du client Sonic: {str(e)}")
            return False
    
    def _init_modules(self):
        """
        Initialise les modules de trading pour Sonic.
        """
        # Initialiser le sniper si activé
        if self.config.get("sniper", {}).get("enabled", True):
            try:
                self.sniper = SonicSniper(config=self.config.get("sniper", {}))
                logger.info("Module de sniping Sonic initialisé")
            except Exception as e:
                logger.error(f"Erreur lors de l'initialisation du sniper Sonic: {str(e)}")
                self.sniper = None
        
        # Initialiser l'arbitrage si activé (à implémenter ultérieurement)
        # if self.config.get("arbitrage", {}).get("enabled", True):
        #    try:
        #        self.arbitrage_engine = SonicArbitrageEngine(config=self.config.get("arbitrage", {}))
        #        logger.info("Module d'arbitrage Sonic initialisé")
        #    except Exception as e:
        #        logger.error(f"Erreur lors de l'initialisation de l'arbitrage Sonic: {str(e)}")
        #        self.arbitrage_engine = None
    
    async def start(self, sniper: bool = True, arbitrage: bool = False):
        """
        Démarre les modules de trading sur Sonic.
        
        Args:
            sniper: Activer le sniping (défaut: True)
            arbitrage: Activer l'arbitrage (défaut: False)
        """
        if not self.enabled:
            logger.warning("Impossible de démarrer: Sonic est désactivé dans la configuration")
            return False
        
        if self.running:
            logger.warning("Le gestionnaire Sonic est déjà en cours d'exécution")
            return True
        
        logger.info("Démarrage du gestionnaire Sonic")
        
        # Mettre à jour l'état
        self.running = True
        self.stats["last_startup"] = datetime.now()
        
        # Démarrer le sniper si demandé et disponible
        if sniper and self.sniper:
            try:
                await self.sniper.start()
                self.stats["sniper_active"] = True
                logger.info("Module de sniping Sonic démarré")
            except Exception as e:
                logger.error(f"Erreur lors du démarrage du sniper Sonic: {str(e)}")
                self.stats["sniper_active"] = False
        
        # Démarrer l'arbitrage si demandé et disponible
        if arbitrage and self.arbitrage_engine:
            try:
                await self.arbitrage_engine.start()
                self.stats["arbitrage_active"] = True
                logger.info("Module d'arbitrage Sonic démarré")
            except Exception as e:
                logger.error(f"Erreur lors du démarrage de l'arbitrage Sonic: {str(e)}")
                self.stats["arbitrage_active"] = False
        
        # Notifier le démarrage
        if self.stats["sniper_active"] or self.stats["arbitrage_active"]:
            message = "GBPBot Sonic démarré avec "
            components = []
            if self.stats["sniper_active"]:
                components.append("sniping")
            if self.stats["arbitrage_active"]:
                components.append("arbitrage")
            message += " et ".join(components)
            send_notification("info", "GBPBot Sonic", message)
        
        logger.info("Gestionnaire Sonic démarré")
        return True
    
    async def stop(self):
        """
        Arrête les modules de trading sur Sonic.
        """
        if not self.running:
            logger.warning("Le gestionnaire Sonic n'est pas en cours d'exécution")
            return
        
        logger.info("Arrêt du gestionnaire Sonic")
        
        # Arrêter le sniper si actif
        if self.stats["sniper_active"] and self.sniper:
            try:
                await self.sniper.stop()
                self.stats["sniper_active"] = False
                logger.info("Module de sniping Sonic arrêté")
            except Exception as e:
                logger.error(f"Erreur lors de l'arrêt du sniper Sonic: {str(e)}")
        
        # Arrêter l'arbitrage si actif
        if self.stats["arbitrage_active"] and self.arbitrage_engine:
            try:
                await self.arbitrage_engine.stop()
                self.stats["arbitrage_active"] = False
                logger.info("Module d'arbitrage Sonic arrêté")
            except Exception as e:
                logger.error(f"Erreur lors de l'arrêt de l'arbitrage Sonic: {str(e)}")
        
        # Mettre à jour l'état
        self.running = False
        
        # Calculer le temps d'exécution
        if self.stats["last_startup"]:
            uptime = datetime.now() - self.stats["last_startup"]
            self.stats["uptime_seconds"] += uptime.total_seconds()
        
        # Notifier l'arrêt
        send_notification("info", "GBPBot Sonic", "GBPBot Sonic arrêté")
        
        logger.info("Gestionnaire Sonic arrêté")
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Récupère les statistiques du gestionnaire Sonic.
        
        Returns:
            Statistiques du gestionnaire et de ses modules
        """
        # Récupérer les statistiques
        stats = self.stats.copy()
        
        # Ajouter les statistiques des modules
        if self.sniper:
            stats["sniper_stats"] = self.sniper.get_stats()
        
        if self.arbitrage_engine:
            stats["arbitrage_stats"] = self.arbitrage_engine.get_stats()
        
        # Calculer le temps d'exécution si actif
        if self.running and self.stats["last_startup"]:
            current_uptime = (datetime.now() - self.stats["last_startup"]).total_seconds()
            stats["current_uptime_seconds"] = current_uptime
            stats["total_uptime_seconds"] = self.stats["uptime_seconds"] + current_uptime
        else:
            stats["total_uptime_seconds"] = self.stats["uptime_seconds"]
        
        # Calculer le profit total
        total_profit = 0.0
        if self.sniper:
            total_profit += self.sniper.stats.get("total_profit", 0.0)
        if self.arbitrage_engine:
            total_profit += getattr(self.arbitrage_engine, "total_profit", 0.0)
        
        stats["total_profit"] = total_profit
        
        return stats
    
    async def test_connection(self) -> bool:
        """
        Teste la connexion avec Sonic.
        
        Returns:
            True si la connexion est établie, False sinon
        """
        if not self.client:
            logger.error("Client Sonic non disponible")
            return False
        
        try:
            # Tester la connexion en récupérant le prix d'un token connu
            wftm_address = "0x21be370D5312f44cB42ce377BC9b8a0cEF1A4C83"  # WFTM sur Fantom
            price = await self.client.get_token_price(wftm_address)
            
            if price > 0:
                logger.info(f"Connexion Sonic réussie, prix WFTM: {price}")
                return True
            else:
                logger.warning("Connexion Sonic établie mais données de prix invalides")
                return False
                
        except Exception as e:
            logger.error(f"Erreur lors du test de connexion Sonic: {str(e)}")
            return False

# Singleton
_sonic_manager_instance = None

def get_sonic_manager() -> SonicManager:
    """
    Récupère l'instance unique du gestionnaire Sonic.
    
    Returns:
        Instance du gestionnaire Sonic
    """
    global _sonic_manager_instance
    
    if _sonic_manager_instance is None:
        _sonic_manager_instance = SonicManager()
    
    return _sonic_manager_instance 