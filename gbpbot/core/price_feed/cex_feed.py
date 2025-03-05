#!/usr/bin/env python3
"""
Module de gestion des prix des exchanges centralisés (CEX).
"""

import asyncio
import aiohttp
from typing import Dict, List, Optional
from decimal import Decimal
from loguru import logger

from gbpbot.core.monitoring.monitor import BotMonitor
from .base import BasePriceFeed

class CEXPriceFeed(BasePriceFeed):
    """Price feed pour les CEX."""
    
    def __init__(self, config: Dict, monitor: BotMonitor):
        """
        Initialise le feed de prix CEX.
        
        Args:
            config: Configuration du bot
            monitor: Instance du moniteur
        """
        super().__init__(config)
        self.monitor = monitor
        
        # État du service
        self.is_running = False
        self.prices: Dict[str, Dict] = {}
        self.last_update = 0
        
        # Configuration des CEX
        self.cex_configs = self.config.get('cex', {})
        self.update_interval = self.config.get('price_feed', {}).get('cex_update_interval', 1)
        
        # Session HTTP
        self.session = None
        self.rate_limiters = {}
        self.price_cache = {}
        self.liquidity_cache = {}
        self.websockets = {}

    async def start(self):
        """Démarre le monitoring des prix CEX."""
        try:
            self.is_running = True
            self.session = aiohttp.ClientSession()
            await self._init_websockets()
            await self._start_price_monitoring()
            
            # Initialiser les rate limiters
            for cex_name, cex_config in self.cex_configs.items():
                self.rate_limiters[cex_name] = {
                    'last_request': 0,
                    'min_interval': cex_config.get('rate_limit', 1)
                }
            
            logger.info("Feed de prix CEX démarré")
            
        except Exception as e:
            logger.error(f"Erreur lors du démarrage du feed CEX: {str(e)}")
            raise

    async def stop(self):
        """Arrête le monitoring des prix."""
        self.is_running = False
        for ws in self.websockets.values():
            await ws.close()
        if self.session:
            await self.session.close()
            
        logger.info("Feed de prix CEX arrêté")

    async def get_price(self, token_address: str, cex_name: str) -> Optional[Dict]:
        """
        Récupère le prix d'un token sur un CEX spécifique.
        
        Args:
            token_address: Adresse du token
            cex_name: Nom du CEX
            
        Returns:
            Optional[Dict]: Informations sur le prix du token
        """
        try:
            if not self.is_running or not self.session:
                logger.warning("Le feed CEX n'est pas démarré")
                return None
                
            if cex_name not in self.cex_configs:
                logger.error(f"CEX {cex_name} non configuré")
                return None
                
            # Vérifier le rate limit
            if not await self._check_rate_limit(cex_name):
                return None
                
            # Récupérer le prix
            price_info = await self._fetch_price(token_address, cex_name)
            
            if price_info:
                # Mettre à jour le cache
                self.prices[f"{token_address}_{cex_name}"] = price_info
                
            return price_info
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du prix sur {cex_name}: {str(e)}")
            return None

    async def get_all_prices(self) -> Dict[str, Dict]:
        """
        Récupère tous les prix disponibles.
        
        Returns:
            Dict[str, Dict]: Dictionnaire des prix par token et CEX
        """
        return self.prices.copy()

    async def update_prices(self):
        """Met à jour les prix de tous les tokens configurés."""
        if not self.is_running:
            return
            
        try:
            current_time = asyncio.get_event_loop().time()
            if current_time - self.last_update < self.update_interval:
                return
                
            # Mettre à jour les prix pour chaque CEX
            for cex_name, cex_config in self.cex_configs.items():
                for token_address in cex_config.get('tokens', []):
                    await self.get_price(token_address, cex_name)
                    
            self.last_update = current_time
            
            # Mettre à jour les métriques
            await self._update_metrics()
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour des prix CEX: {str(e)}")

    async def get_status(self) -> Dict:
        """
        Récupère l'état actuel du feed.
        
        Returns:
            Dict: État du feed
        """
        return {
            'is_running': self.is_running,
            'last_update': self.last_update,
            'prices_count': len(self.prices),
            'cex_count': len(self.cex_configs)
        }

    async def _check_rate_limit(self, cex_name: str) -> bool:
        """
        Vérifie si on peut faire une requête selon le rate limit.
        
        Args:
            cex_name: Nom du CEX
            
        Returns:
            bool: True si on peut faire la requête
        """
        current_time = asyncio.get_event_loop().time()
        rate_limiter = self.rate_limiters[cex_name]
        
        if current_time - rate_limiter['last_request'] < rate_limiter['min_interval']:
            return False
            
        rate_limiter['last_request'] = current_time
        return True

    async def _fetch_price(self, token_address: str, cex_name: str) -> Optional[Dict]:
        """
        Récupère le prix d'un token via l'API du CEX.
        
        Args:
            token_address: Adresse du token
            cex_name: Nom du CEX
            
        Returns:
            Optional[Dict]: Informations sur le prix du token
        """
        try:
            cex_config = self.cex_configs[cex_name]
            token_symbol = cex_config['token_symbols'].get(token_address)
            
            if not token_symbol:
                logger.error(f"Symbole non trouvé pour le token {token_address} sur {cex_name}")
                return None
                
            # Construire l'URL
            base_url = cex_config['api_url']
            endpoint = cex_config['endpoints']['price']
            url = f"{base_url}{endpoint.format(symbol=token_symbol)}"
            
            # Faire la requête
            async with self.session.get(url) as response:
                if response.status != 200:
                    logger.error(f"Erreur {response.status} lors de la requête à {url}")
                    return None
                    
                data = await response.json()
                
                # Parser la réponse selon le format du CEX
                price = await self._parse_price_response(data, cex_name)
                
                if price is None:
                    return None
                    
                return {
                    'price': price,
                    'exchange': cex_name,
                    'timestamp': asyncio.get_event_loop().time()
                }
                
        except Exception as e:
            logger.error(f"Erreur lors de la requête au CEX {cex_name}: {str(e)}")
            return None

    async def _parse_price_response(self, data: Dict, cex_name: str) -> Optional[Decimal]:
        """
        Parse la réponse de l'API selon le format du CEX.
        
        Args:
            data: Données de la réponse
            cex_name: Nom du CEX
            
        Returns:
            Optional[Decimal]: Prix du token
        """
        try:
            cex_config = self.cex_configs[cex_name]
            price_path = cex_config['price_path'].split('.')
            
            # Naviguer dans la réponse
            value = data
            for key in price_path:
                value = value[key]
                
            return Decimal(str(value))
            
        except (KeyError, ValueError) as e:
            logger.error(f"Erreur lors du parsing de la réponse de {cex_name}: {str(e)}")
            return None

    async def _update_metrics(self):
        """Met à jour les métriques du feed CEX."""
        try:
            metrics = {
                'cex_prices_count': len(self.prices),
                'cex_update_time': asyncio.get_event_loop().time() - self.last_update
            }
            
            # Métriques par CEX
            for cex_name in self.cex_configs:
                cex_prices = [p for k, p in self.prices.items() if p['exchange'] == cex_name]
                metrics[f'cex_{cex_name}_prices'] = len(cex_prices)
                
                if cex_prices:
                    metrics[f'cex_{cex_name}_avg_price'] = sum(
                        float(p['price']) for p in cex_prices
                    ) / len(cex_prices)
                    
            await self.monitor.update_market_metrics(metrics)
            
        except Exception as e:
            logger.error(f"Erreur lors de la mise à jour des métriques CEX: {str(e)}")

    async def _init_websockets(self) -> None:
        """Initialise les connexions WebSocket."""
        for exchange in self.config['exchanges']:
            try:
                ws = await self._connect_websocket(exchange)
                self.websockets[exchange['name']] = ws
                asyncio.create_task(self._handle_websocket_messages(ws, exchange['name']))
            except Exception as e:
                logger.error(f"Erreur lors de l'initialisation du WebSocket pour {exchange['name']}: {str(e)}")
                
    async def _start_price_monitoring(self) -> None:
        """Démarre le monitoring continu des prix."""
        while self.is_running:
            try:
                for exchange in self.config['exchanges']:
                    for symbol in exchange['symbols']:
                        await self._update_price(exchange['name'], symbol)
                await asyncio.sleep(self.config['update_interval'])
            except Exception as e:
                logger.error(f"Erreur lors du monitoring des prix: {str(e)}")
                await asyncio.sleep(5)  # Attente avant retry
                
    async def _connect_websocket(self, exchange: Dict) -> aiohttp.ClientWebSocketResponse:
        """Établit une connexion WebSocket avec un exchange."""
        try:
            ws = await self.session.ws_connect(exchange['ws_url'])
            # Subscribe aux channels nécessaires
            subscribe_msg = {
                "method": "SUBSCRIBE",
                "params": [f"{symbol.lower()}@trade" for symbol in exchange['symbols']],
                "id": 1
            }
            await ws.send_json(subscribe_msg)
            return ws
        except Exception as e:
            logger.error(f"Erreur de connexion WebSocket: {str(e)}")
            raise
            
    async def _handle_websocket_messages(self, ws: aiohttp.ClientWebSocketResponse, exchange_name: str) -> None:
        """Gère les messages WebSocket."""
        try:
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = msg.json()
                    await self._process_ws_message(data, exchange_name)
                elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                    break
        except Exception as e:
            logger.error(f"Erreur lors du traitement des messages WebSocket: {str(e)}")
        finally:
            if not ws.closed:
                await ws.close()
                
    async def _process_ws_message(self, data: Dict, exchange_name: str) -> None:
        """Traite un message WebSocket."""
        try:
            if 'e' in data and data['e'] == 'trade':
                symbol = data['s']
                price = Decimal(data['p'])
                self.price_cache[f"{exchange_name}_{symbol}"] = price
        except Exception as e:
            logger.error(f"Erreur lors du traitement du message: {str(e)}")
            
    async def _fetch_rest_price(self, token_symbol: str) -> Optional[Decimal]:
        """Récupère le prix via l'API REST."""
        for exchange in self.config['exchanges']:
            try:
                url = f"{exchange['api_url']}/ticker/price?symbol={token_symbol}"
                async with self.session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return Decimal(data['price'])
            except Exception as e:
                logger.error(f"Erreur lors de la récupération du prix REST: {str(e)}")
        return None
        
    async def _fetch_rest_liquidity(self, token_symbol: str) -> Optional[Decimal]:
        """Récupère la liquidité via l'API REST."""
        for exchange in self.config['exchanges']:
            try:
                url = f"{exchange['api_url']}/depth?symbol={token_symbol}&limit=5"
                async with self.session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        # Calcule la liquidité basée sur les 5 meilleurs ordres
                        bids_liquidity = sum(Decimal(bid[1]) for bid in data['bids'][:5])
                        asks_liquidity = sum(Decimal(ask[1]) for ask in data['asks'][:5])
                        return (bids_liquidity + asks_liquidity) / 2
            except Exception as e:
                logger.error(f"Erreur lors de la récupération de la liquidité REST: {str(e)}")
        return None

    async def get_liquidity(self, token_symbol: str) -> Optional[Decimal]:
        """Récupère la liquidité d'un token sur le CEX."""
        if token_symbol in self.liquidity_cache:
            return self.liquidity_cache[token_symbol]
            
        liquidity = await self._fetch_rest_liquidity(token_symbol)
        if liquidity:
            self.liquidity_cache[token_symbol] = liquidity
        return liquidity
        
    async def validate_price(self, token_symbol: str, price: Decimal) -> bool:
        """Valide si un prix est cohérent avec les données du CEX."""
        current_price = await self.get_price(token_symbol, self.config['exchanges'][0]['name'])
        if not current_price:
            return False
            
        # Vérifie si le prix est dans une marge acceptable
        deviation = abs(price - current_price['price']) / current_price['price']
        return deviation <= self.config['max_price_deviation'] 