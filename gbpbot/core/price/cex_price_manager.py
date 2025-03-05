#!/usr/bin/env python3
"""
Module de gestion des prix CEX pour GBPBot.
Gère la récupération et le traitement des prix des exchanges centralisés.
"""

import asyncio
import aiohttp
from typing import Dict, Optional
from datetime import datetime
from loguru import logger

from gbpbot.config.config_manager import ConfigManager
from gbpbot.core.websocket_manager import WebSocketManager

class CexPriceManager:
    def __init__(self):
        self.config = ConfigManager().get_config()
        self.ws_manager = WebSocketManager()
        self.prices: Dict[str, float] = {}
        self.last_update: Dict[str, float] = {}
        self.subscriptions: Dict[str, bool] = {}
        
    async def initialize(self):
        """Initialise les connexions WebSocket pour les CEX configurés."""
        for cex_name, cex_config in self.config["cex"].items():
            if cex_config.get("use_websocket", True):
                await self.setup_websocket(cex_name)
                
    async def setup_websocket(self, cex_name: str):
        """Configure la connexion WebSocket pour un CEX spécifique."""
        try:
            ws_url = self.config["cex"][cex_name]["websocket_url"]
            
            # Définir les callbacks
            async def on_message(msg):
                await self._handle_ws_message(cex_name, msg)
                
            async def on_connect():
                logger.info(f"Connecté au WebSocket de {cex_name}")
                await self._subscribe_to_prices(cex_name)
                
            async def on_disconnect():
                logger.warning(f"Déconnecté du WebSocket de {cex_name}")
                self.subscriptions[cex_name] = False
                
            # Enregistrer la connexion WebSocket
            await self.ws_manager.register_connection(
                cex_name,
                ws_url,
                on_message=on_message,
                on_connect=on_connect,
                on_disconnect=on_disconnect
            )
            
        except Exception as e:
            logger.error(f"Erreur lors de la configuration du WebSocket pour {cex_name}: {str(e)}")
            
    async def _subscribe_to_prices(self, cex_name: str):
        """S'abonne aux flux de prix pour un CEX spécifique."""
        try:
            subscription_msg = self.config["cex"][cex_name]["subscription_message"]
            await self.ws_manager.send_message(cex_name, subscription_msg)
            self.subscriptions[cex_name] = True
        except Exception as e:
            logger.error(f"Erreur lors de l'abonnement aux prix sur {cex_name}: {str(e)}")
            
    async def _handle_ws_message(self, cex_name: str, message: dict):
        """Traite les messages WebSocket reçus."""
        try:
            # Adapter selon le format spécifique de chaque CEX
            if cex_name == "binance":
                if "p" in message and "s" in message:
                    symbol = message["s"]
                    price = float(message["p"])
                    self.update_price(cex_name, symbol, price)
            # Ajouter d'autres CEX selon besoin
            
        except Exception as e:
            logger.error(f"Erreur lors du traitement du message de {cex_name}: {str(e)}")
            
    def update_price(self, cex_name: str, symbol: str, price: float):
        """Met à jour le prix en cache pour un symbole donné."""
        key = f"{cex_name}_{symbol}"
        self.prices[key] = price
        self.last_update[key] = asyncio.get_event_loop().time()
        
    async def get_price(self, symbol: str, cex_name: str) -> Optional[float]:
        """Récupère le prix d'un symbole sur un CEX spécifique."""
        key = f"{cex_name}_{symbol}"
        
        # Vérifier si nous avons un prix récent en cache
        if self.is_price_fresh(symbol, cex_name):
            return self.prices.get(key)
            
        # Si pas de WebSocket ou prix périmé, faire un appel REST
        try:
            rest_url = self.config["cex"][cex_name]["rest_url"]
            rest_url = rest_url.format(symbol=symbol)
            
            async with aiohttp.ClientSession() as session:
                async with session.get(rest_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Adapter selon le format de réponse du CEX
                        if cex_name == "binance":
                            price = float(data["price"])
                            self.update_price(cex_name, symbol, price)
                            return price
                            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du prix via REST sur {cex_name}: {str(e)}")
            
        return None
        
    def is_price_fresh(self, symbol: str, cex_name: str, max_age: float = 5.0) -> bool:
        """Vérifie si le prix en cache est suffisamment récent."""
        key = f"{cex_name}_{symbol}"
        if key not in self.last_update:
            return False
        current_time = asyncio.get_event_loop().time()
        return (current_time - self.last_update[key]) <= max_age
        
    async def cleanup(self):
        """Nettoie les ressources utilisées."""
        # Fermer toutes les connexions WebSocket
        await self.ws_manager.close_all() 