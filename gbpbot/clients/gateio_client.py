#!/usr/bin/env python3
"""
Module client Gate.io pour GBPBot.

Ce module fournit une interface pour interagir avec l'API Gate.io,
permettant d'effectuer des opérations de trading sur la plateforme Gate.io.
"""

import time
import logging
import asyncio
import hmac
import base64
import hashlib
import json
from typing import Dict, List, Optional, Any, Tuple, Union
from decimal import Decimal

from gbpbot.clients.base_cex_client import BaseCEXClient
from gbpbot.utils.exceptions import ExchangeConnectionError, ExchangeAPIError

# Essayer d'importer le SDK Gate.io
try:
    import gate_api
    from gate_api.exceptions import ApiException, GateApiException
    GATEIO_SDK_AVAILABLE = True
except ImportError:
    GATEIO_SDK_AVAILABLE = False
    logging.warning("Gate.io client not available. Install with 'pip install gate-api'")

# Configuration du logger
logger = logging.getLogger(__name__)

class GateIOClient(BaseCEXClient):
    """
    Client pour interagir avec l'API Gate.io.
    
    Cette classe implémente l'interface BaseCEXClient pour Gate.io,
    permettant d'effectuer des opérations de trading sur la plateforme.
    """
    
    def __init__(self, api_key: str, api_secret: str, 
                 sandbox: bool = False, request_timeout: int = 10,
                 rate_limit_requests: int = 6, rate_limit_seconds: int = 1):
        """
        Initialise le client Gate.io.
        
        Args:
            api_key: Clé API Gate.io
            api_secret: Secret API Gate.io
            sandbox: Utiliser l'environnement sandbox (défaut: False)
            request_timeout: Timeout pour les requêtes en secondes (défaut: 10)
            rate_limit_requests: Nombre maximum de requêtes par période (défaut: 6)
            rate_limit_seconds: Période pour le rate limit en secondes (défaut: 1)
        """
        config = {
            "api_key": api_key,
            "api_secret": api_secret,
            "request_timeout": request_timeout,
            "rate_limit_requests": rate_limit_requests,
            "rate_limit_seconds": rate_limit_seconds
        }
        
        super().__init__(config)
        self.exchange_name = "gateio"
        
        if not GATEIO_SDK_AVAILABLE:
            raise ImportError("Gate.io SDK non disponible. Installez-le avec 'pip install gate-api'")
        
        self.sandbox = sandbox
        
        # Configuration de l'API Gate.io
        self.api_config = gate_api.Configuration(
            host="https://api.gateio.ws/api/v4" if not sandbox else "https://api.testnet.gate.io/api/v4",
            key=api_key,
            secret=api_secret
        )
        
        # Clients Gate.io
        self.spot_api = None
        self.wallet_api = None
        self.order_api = None
        
        # Symboles
        self.symbols_info = {}
        self.symbol_format = {}  # Mapping des symboles (ex: BTC_USDT -> BTC/USDT)
        
        logger.info(f"Client Gate.io initialisé (sandbox: {sandbox})")
    
    async def connect(self) -> bool:
        """
        Établit la connexion avec l'API Gate.io.
        
        Returns:
            True si la connexion est établie avec succès, False sinon
        """
        if self.connected:
            logger.warning("Client Gate.io déjà connecté")
            return True
        
        try:
            # Initialiser les clients Gate.io
            api_client = gate_api.ApiClient(self.api_config)
            self.spot_api = gate_api.SpotApi(api_client)
            self.wallet_api = gate_api.WalletApi(api_client)
            self.order_api = gate_api.SpotApi(api_client)
            
            # Tester la connexion
            currencies = self.spot_api.list_currencies()
            if not currencies:
                raise ExchangeConnectionError("Impossible de récupérer la liste des devises")
            
            # Charger les informations sur les symboles
            await self._populate_symbols()
            
            self.connected = True
            self.last_connection_time = time.time()
            logger.info("Connexion à Gate.io établie avec succès")
            
            return True
            
        except Exception as e:
            self.connected = False
            logger.error(f"Erreur lors de la connexion à Gate.io: {e}")
            raise ExchangeConnectionError(f"Erreur lors de la connexion à Gate.io: {e}")
    
    async def disconnect(self) -> bool:
        """
        Ferme la connexion avec l'API Gate.io.
        
        Returns:
            True si la déconnexion est réussie, False sinon
        """
        if not self.connected:
            logger.warning("Client Gate.io déjà déconnecté")
            return True
        
        try:
            # Réinitialiser les clients
            self.spot_api = None
            self.wallet_api = None
            self.order_api = None
            
            self.connected = False
            logger.info("Déconnexion de Gate.io réussie")
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la déconnexion de Gate.io: {e}")
            return False
    
    async def _populate_symbols(self):
        """Charge les informations sur les symboles disponibles sur Gate.io."""
        try:
            # Vérifier la connexion
            if not self.connected:
                await self.connect()
            
            # Récupérer les informations sur les symboles
            symbols = self.spot_api.list_currency_pairs()
            
            # Stocker les informations
            for symbol_info in symbols:
                symbol = symbol_info.id
                self.symbols_info[symbol] = symbol_info
                
                # Créer un mapping pour les formats de symboles
                base_currency = symbol_info.base
                quote_currency = symbol_info.quote
                
                # Format standard: BTC/USDT
                standard_format = f"{base_currency}/{quote_currency}"
                
                # Format Gate.io: BTC_USDT
                gateio_format = symbol
                
                # Mapping dans les deux sens
                self.symbol_format[standard_format] = gateio_format
                self.symbol_format[gateio_format] = standard_format
            
            logger.info(f"Chargé {len(symbols)} symboles depuis Gate.io")
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement des symboles Gate.io: {e}")
            raise ExchangeAPIError(f"Erreur lors du chargement des symboles Gate.io: {e}")
    
    def _format_symbol(self, symbol: str) -> str:
        """
        Convertit un symbole au format Gate.io.
        
        Args:
            symbol: Symbole à convertir (ex: "BTC/USDT")
            
        Returns:
            Symbole au format Gate.io (ex: "BTC_USDT")
        """
        # Si le symbole est déjà dans le bon format, le retourner
        if symbol in self.symbol_format:
            return self.symbol_format[symbol]
        
        # Sinon, essayer de le convertir
        if "/" in symbol:
            base, quote = symbol.split("/")
            return f"{base}_{quote}"
        
        # Si le format n'est pas reconnu, retourner tel quel
        return symbol
    
    async def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        Récupère les informations de ticker pour un symbole.
        
        Args:
            symbol: Symbole du marché (ex: "BTC/USDT")
            
        Returns:
            Informations de ticker
        """
        await self._ensure_connected()
        await self._handle_rate_limit()
        
        try:
            # Convertir le symbole au format Gate.io
            gateio_symbol = self._format_symbol(symbol)
            
            # Récupérer le ticker
            ticker = self.spot_api.list_tickers(currency_pair=gateio_symbol)
            
            if not ticker or len(ticker) == 0:
                raise ExchangeAPIError(f"Aucun ticker trouvé pour {symbol}")
            
            ticker = ticker[0]
            
            # Formater la réponse
            result = {
                "symbol": symbol,
                "bid": float(ticker.highest_bid),
                "ask": float(ticker.lowest_ask),
                "last": float(ticker.last),
                "volume": float(ticker.base_volume),
                "timestamp": time.time(),  # Gate.io ne fournit pas de timestamp
                "exchange": "gateio"
            }
            
            # Mettre à jour le cache
            self._update_ticker_cache(symbol, result)
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du ticker pour {symbol}: {e}")
            
            # Essayer de récupérer depuis le cache
            cached_ticker = self._get_cached_ticker(symbol)
            if cached_ticker:
                logger.info(f"Utilisation du ticker en cache pour {symbol}")
                return cached_ticker
            
            raise ExchangeAPIError(f"Erreur lors de la récupération du ticker pour {symbol}: {e}")
    
    async def get_balance(self, currency: Optional[str] = None) -> Union[Dict[str, float], float]:
        """
        Récupère le solde du compte.
        
        Args:
            currency: Devise spécifique à récupérer (optionnel)
            
        Returns:
            Solde du compte pour toutes les devises ou pour une devise spécifique
        """
        await self._ensure_connected()
        await self._handle_rate_limit()
        
        try:
            # Récupérer les soldes
            accounts = self.spot_api.list_spot_accounts()
            
            # Formater la réponse
            balances = {}
            for account in accounts:
                curr = account.currency
                balance = float(account.available) + float(account.locked)
                available = float(account.available)
                
                balances[curr] = {
                    "total": balance,
                    "available": available
                }
            
            # Retourner le solde pour une devise spécifique si demandé
            if currency:
                currency = currency.upper()
                if currency in balances:
                    return balances[currency]["available"]
                return 0.0
            
            # Sinon, retourner tous les soldes
            return balances
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des soldes: {e}")
            raise ExchangeAPIError(f"Erreur lors de la récupération des soldes: {e}")
    
    async def place_order(self, symbol: str, side: str, order_type: str, 
                         amount: float, price: Optional[float] = None,
                         params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Place un ordre sur Gate.io.
        
        Args:
            symbol: Symbole du marché (ex: "BTC/USDT")
            side: Côté de l'ordre ("buy" ou "sell")
            order_type: Type d'ordre ("limit", "market")
            amount: Quantité à acheter/vendre
            price: Prix pour les ordres limit (optionnel pour market)
            params: Paramètres supplémentaires (optionnel)
            
        Returns:
            Informations sur l'ordre placé
        """
        await self._ensure_connected()
        await self._handle_rate_limit()
        
        try:
            # Convertir le symbole au format Gate.io
            gateio_symbol = self._format_symbol(symbol)
            
            # Préparer l'ordre
            order = gate_api.Order(
                currency_pair=gateio_symbol,
                side=side.lower(),
                amount=str(amount),
                time_in_force="gtc"  # Good Till Cancel
            )
            
            # Ajouter les paramètres spécifiques au type d'ordre
            if order_type.lower() == "limit":
                if price is None:
                    raise ValueError("Le prix est requis pour les ordres limit")
                
                order.price = str(price)
                order.type = "limit"
                
            elif order_type.lower() == "market":
                order.type = "market"
                
            else:
                raise ValueError(f"Type d'ordre non supporté: {order_type}")
            
            # Ajouter les paramètres supplémentaires
            if params:
                for key, value in params.items():
                    setattr(order, key, value)
            
            # Placer l'ordre
            response = self.spot_api.create_order(order)
            
            # Formater la réponse
            result = {
                "id": response.id,
                "symbol": symbol,
                "side": side,
                "type": order_type,
                "amount": amount,
                "price": price,
                "status": self._map_order_status(response.status),
                "timestamp": time.time(),
                "exchange": "gateio"
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors du placement de l'ordre {side} {order_type} pour {symbol}: {e}")
            raise ExchangeAPIError(f"Erreur lors du placement de l'ordre: {e}")
    
    async def get_order(self, order_id: str, symbol: Optional[str] = None) -> Dict[str, Any]:
        """
        Récupère les informations sur un ordre spécifique.
        
        Args:
            order_id: ID de l'ordre
            symbol: Symbole du marché (requis pour Gate.io)
            
        Returns:
            Informations sur l'ordre
        """
        await self._ensure_connected()
        await self._handle_rate_limit()
        
        if not symbol:
            raise ValueError("Le symbole est requis pour récupérer un ordre sur Gate.io")
        
        try:
            # Convertir le symbole au format Gate.io
            gateio_symbol = self._format_symbol(symbol)
            
            # Récupérer les détails de l'ordre
            order_details = self.spot_api.get_order(order_id, gateio_symbol)
            
            # Formater la réponse
            result = {
                "id": order_details.id,
                "symbol": symbol,
                "side": order_details.side,
                "type": order_details.type,
                "amount": float(order_details.amount),
                "filled": float(order_details.filled_total) / float(order_details.price) if order_details.price else 0,
                "remaining": float(order_details.left),
                "price": float(order_details.price) if order_details.price else None,
                "cost": float(order_details.filled_total),
                "status": self._map_order_status(order_details.status),
                "timestamp": int(order_details.create_time_ms) / 1000,  # Convertir en secondes
                "exchange": "gateio"
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de l'ordre {order_id}: {e}")
            raise ExchangeAPIError(f"Erreur lors de la récupération de l'ordre: {e}")
    
    async def cancel_order(self, order_id: str, symbol: Optional[str] = None) -> bool:
        """
        Annule un ordre spécifique.
        
        Args:
            order_id: ID de l'ordre
            symbol: Symbole du marché (requis pour Gate.io)
            
        Returns:
            True si l'annulation est réussie, False sinon
        """
        await self._ensure_connected()
        await self._handle_rate_limit()
        
        if not symbol:
            raise ValueError("Le symbole est requis pour annuler un ordre sur Gate.io")
        
        try:
            # Convertir le symbole au format Gate.io
            gateio_symbol = self._format_symbol(symbol)
            
            # Annuler l'ordre
            response = self.spot_api.cancel_order(order_id, gateio_symbol)
            
            # Vérifier si l'annulation a réussi
            if response.status == "cancelled":
                logger.info(f"Ordre {order_id} annulé avec succès")
                return True
            
            logger.warning(f"Annulation de l'ordre {order_id} non confirmée")
            return False
            
        except Exception as e:
            logger.error(f"Erreur lors de l'annulation de l'ordre {order_id}: {e}")
            raise ExchangeAPIError(f"Erreur lors de l'annulation de l'ordre: {e}")
    
    async def get_order_book(self, symbol: str, limit: int = 20) -> Dict[str, Any]:
        """
        Récupère le carnet d'ordres pour un symbole.
        
        Args:
            symbol: Symbole du marché (ex: "BTC/USDT")
            limit: Nombre d'ordres à récupérer (défaut: 20)
            
        Returns:
            Carnet d'ordres
        """
        await self._ensure_connected()
        await self._handle_rate_limit()
        
        try:
            # Convertir le symbole au format Gate.io
            gateio_symbol = self._format_symbol(symbol)
            
            # Récupérer le carnet d'ordres
            order_book = self.spot_api.list_order_book(gateio_symbol, limit=limit)
            
            # Formater la réponse
            result = {
                "symbol": symbol,
                "bids": [[float(price), float(amount)] for price, amount in order_book.bids],
                "asks": [[float(price), float(amount)] for price, amount in order_book.asks],
                "timestamp": time.time(),  # Gate.io ne fournit pas de timestamp
                "exchange": "gateio"
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du carnet d'ordres pour {symbol}: {e}")
            raise ExchangeAPIError(f"Erreur lors de la récupération du carnet d'ordres: {e}")
    
    async def get_trading_pairs(self) -> List[str]:
        """
        Récupère la liste des paires de trading disponibles.
        
        Returns:
            Liste des paires de trading au format standard (ex: ["BTC/USDT", "ETH/BTC"])
        """
        await self._ensure_connected()
        
        try:
            # Si les symboles n'ont pas encore été chargés, les charger
            if not self.symbols_info:
                await self._populate_symbols()
            
            # Retourner les paires au format standard
            return [pair for pair in self.symbol_format.keys() if "/" in pair]
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des paires de trading: {e}")
            raise ExchangeAPIError(f"Erreur lors de la récupération des paires de trading: {e}")
    
    def _map_order_status(self, status: str) -> str:
        """
        Mappe le statut d'un ordre Gate.io au format standard.
        
        Args:
            status: Statut de l'ordre Gate.io
            
        Returns:
            Statut de l'ordre au format standard
        """
        status_map = {
            "open": "open",
            "closed": "closed",
            "cancelled": "canceled",
            "cancelling": "canceling",
            "pending": "open"
        }
        
        return status_map.get(status, "unknown")
    
    async def _ensure_connected(self):
        """Vérifie que le client est connecté et se reconnecte si nécessaire."""
        if not self.connected:
            await self.connect()
        elif time.time() - self.last_connection_time > 3600:  # Reconnexion toutes les heures
            logger.info("Reconnexion périodique à Gate.io")
            await self.disconnect()
            await self.connect() 