#!/usr/bin/env python3
"""
Module client KuCoin pour GBPBot.

Ce module fournit une interface pour interagir avec l'API KuCoin,
permettant d'effectuer des opérations de trading sur la plateforme KuCoin.
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

# Essayer d'importer le SDK KuCoin
try:
    from kucoin.client import Market, Trade, User
    from kucoin.asyncio import KucoinSocketManager
    KUCOIN_SDK_AVAILABLE = True
except ImportError:
    KUCOIN_SDK_AVAILABLE = False
    logging.warning("KuCoin client not available. Install with 'pip install kucoin-python'")

# Configuration du logger
logger = logging.getLogger(__name__)

class KuCoinClient(BaseCEXClient):
    """
    Client pour interagir avec l'API KuCoin.
    
    Cette classe implémente l'interface BaseCEXClient pour KuCoin,
    permettant d'effectuer des opérations de trading sur la plateforme.
    """
    
    def __init__(self, api_key: str, api_secret: str, passphrase: str, 
                 sandbox: bool = False, request_timeout: int = 10,
                 rate_limit_requests: int = 6, rate_limit_seconds: int = 1):
        """
        Initialise le client KuCoin.
        
        Args:
            api_key: Clé API KuCoin
            api_secret: Secret API KuCoin
            passphrase: Passphrase API KuCoin
            sandbox: Utiliser l'environnement sandbox (défaut: False)
            request_timeout: Timeout pour les requêtes en secondes (défaut: 10)
            rate_limit_requests: Nombre maximum de requêtes par période (défaut: 6)
            rate_limit_seconds: Période pour le rate limit en secondes (défaut: 1)
        """
        super().__init__(
            exchange_name="kucoin",
            api_key=api_key,
            api_secret=api_secret,
            request_timeout=request_timeout,
            rate_limit_requests=rate_limit_requests,
            rate_limit_seconds=rate_limit_seconds
        )
        
        if not KUCOIN_SDK_AVAILABLE:
            raise ImportError("KuCoin SDK non disponible. Installez-le avec 'pip install kucoin-python'")
        
        self.passphrase = passphrase
        self.sandbox = sandbox
        
        # Clients KuCoin
        self.market_client = None
        self.trade_client = None
        self.user_client = None
        self.socket_manager = None
        
        # Websocket
        self.ws_connected = False
        self.ws_callbacks = {}
        self.ws_task = None
        
        # Symboles
        self.symbols_info = {}
        self.symbol_format = {}  # Mapping des symboles (ex: BTC-USDT -> BTCUSDT)
        
        logger.info(f"Client KuCoin initialisé (sandbox: {sandbox})")
    
    async def connect(self) -> bool:
        """
        Établit la connexion avec l'API KuCoin.
        
        Returns:
            True si la connexion est établie avec succès, False sinon
        """
        if self.connected:
            logger.warning("Client KuCoin déjà connecté")
            return True
        
        try:
            # Initialiser les clients KuCoin
            self.market_client = Market(
                key=self.api_key,
                secret=self.api_secret,
                passphrase=self.passphrase,
                is_sandbox=self.sandbox
            )
            
            self.trade_client = Trade(
                key=self.api_key,
                secret=self.api_secret,
                passphrase=self.passphrase,
                is_sandbox=self.sandbox
            )
            
            self.user_client = User(
                key=self.api_key,
                secret=self.api_secret,
                passphrase=self.passphrase,
                is_sandbox=self.sandbox
            )
            
            # Initialiser le socket manager
            self.socket_manager = KucoinSocketManager(
                key=self.api_key,
                secret=self.api_secret,
                passphrase=self.passphrase,
                is_sandbox=self.sandbox
            )
            
            # Tester la connexion
            currencies = self.market_client.get_currency_list()
            if not currencies:
                raise ExchangeConnectionError("Impossible de récupérer la liste des devises")
            
            # Charger les informations sur les symboles
            await self._populate_symbols()
            
            self.connected = True
            self.last_connection_time = time.time()
            logger.info("Connexion à KuCoin établie avec succès")
            
            return True
            
        except Exception as e:
            self.connected = False
            logger.error(f"Erreur lors de la connexion à KuCoin: {e}")
            raise ExchangeConnectionError(f"Erreur lors de la connexion à KuCoin: {e}")
    
    async def disconnect(self) -> bool:
        """
        Ferme la connexion avec l'API KuCoin.
        
        Returns:
            True si la déconnexion est réussie, False sinon
        """
        if not self.connected:
            logger.warning("Client KuCoin déjà déconnecté")
            return True
        
        try:
            # Fermer les websockets
            if self.ws_connected and self.socket_manager:
                if self.ws_task and not self.ws_task.done():
                    self.ws_task.cancel()
                    try:
                        await self.ws_task
                    except asyncio.CancelledError:
                        pass
                
                self.ws_connected = False
            
            # Réinitialiser les clients
            self.market_client = None
            self.trade_client = None
            self.user_client = None
            self.socket_manager = None
            
            self.connected = False
            logger.info("Déconnexion de KuCoin réussie")
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la déconnexion de KuCoin: {e}")
            return False
    
    async def _populate_symbols(self):
        """Charge les informations sur les symboles disponibles sur KuCoin."""
        try:
            # Vérifier la connexion
            if not self.connected:
                await self.connect()
            
            # Récupérer les informations sur les symboles
            symbols = self.market_client.get_symbols()
            
            # Stocker les informations
            for symbol_info in symbols:
                symbol = symbol_info["symbol"]
                self.symbols_info[symbol] = symbol_info
                
                # Créer un mapping pour les formats de symboles
                base_currency = symbol_info["baseCurrency"]
                quote_currency = symbol_info["quoteCurrency"]
                
                # Format standard: BTC/USDT
                standard_format = f"{base_currency}/{quote_currency}"
                
                # Format KuCoin: BTC-USDT
                kucoin_format = symbol
                
                # Mapping dans les deux sens
                self.symbol_format[standard_format] = kucoin_format
                self.symbol_format[kucoin_format] = standard_format
            
            logger.info(f"Chargé {len(symbols)} symboles depuis KuCoin")
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement des symboles KuCoin: {e}")
            raise ExchangeAPIError(f"Erreur lors du chargement des symboles KuCoin: {e}")
    
    def _format_symbol(self, symbol: str) -> str:
        """
        Convertit un symbole au format KuCoin.
        
        Args:
            symbol: Symbole à convertir (ex: "BTC/USDT")
            
        Returns:
            Symbole au format KuCoin (ex: "BTC-USDT")
        """
        # Si le symbole est déjà dans le bon format, le retourner
        if symbol in self.symbol_format:
            return self.symbol_format[symbol]
        
        # Sinon, essayer de le convertir
        if "/" in symbol:
            base, quote = symbol.split("/")
            return f"{base}-{quote}"
        
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
            # Convertir le symbole au format KuCoin
            kucoin_symbol = self._format_symbol(symbol)
            
            # Récupérer le ticker
            ticker = self.market_client.get_ticker(kucoin_symbol)
            
            # Formater la réponse
            result = {
                "symbol": symbol,
                "bid": float(ticker["bestBid"]),
                "ask": float(ticker["bestAsk"]),
                "last": float(ticker["price"]),
                "volume": float(ticker["volValue"]),
                "timestamp": int(ticker["time"]) / 1000,  # Convertir en secondes
                "exchange": "kucoin"
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
            accounts = self.user_client.get_account_list()
            
            # Formater la réponse
            balances = {}
            for account in accounts:
                curr = account["currency"]
                balance = float(account["balance"])
                available = float(account["available"])
                
                if curr not in balances:
                    balances[curr] = {
                        "total": 0.0,
                        "available": 0.0
                    }
                
                balances[curr]["total"] += balance
                balances[curr]["available"] += available
            
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
        Place un ordre sur KuCoin.
        
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
            # Convertir le symbole au format KuCoin
            kucoin_symbol = self._format_symbol(symbol)
            
            # Préparer les paramètres de l'ordre
            order_params = {
                "clientOid": f"gbpbot_{int(time.time() * 1000)}",
                "side": side.lower(),
                "symbol": kucoin_symbol,
            }
            
            # Ajouter les paramètres spécifiques au type d'ordre
            if order_type.lower() == "limit":
                if price is None:
                    raise ValueError("Le prix est requis pour les ordres limit")
                
                order_params["price"] = str(price)
                order_params["size"] = str(amount)
                order_params["type"] = "limit"
                
            elif order_type.lower() == "market":
                order_params["type"] = "market"
                
                # Pour les ordres market, KuCoin utilise "size" pour les ventes et "funds" pour les achats
                if side.lower() == "sell":
                    order_params["size"] = str(amount)
                else:  # buy
                    # Si le prix est fourni, calculer les fonds
                    if price is not None:
                        order_params["funds"] = str(amount * price)
                    else:
                        order_params["funds"] = str(amount)
            
            else:
                raise ValueError(f"Type d'ordre non supporté: {order_type}")
            
            # Ajouter les paramètres supplémentaires
            if params:
                order_params.update(params)
            
            # Placer l'ordre
            response = self.trade_client.create_order(**order_params)
            
            # Formater la réponse
            result = {
                "id": response["orderId"],
                "symbol": symbol,
                "side": side,
                "type": order_type,
                "amount": amount,
                "price": price,
                "status": "open",
                "timestamp": time.time(),
                "exchange": "kucoin"
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
            symbol: Symbole du marché (optionnel, mais recommandé pour de meilleures performances)
            
        Returns:
            Informations sur l'ordre
        """
        await self._ensure_connected()
        await self._handle_rate_limit()
        
        try:
            # Récupérer les détails de l'ordre
            order_details = self.trade_client.get_order_details(order_id)
            
            # Convertir le symbole au format standard
            kucoin_symbol = order_details["symbol"]
            standard_symbol = self.symbol_format.get(kucoin_symbol, kucoin_symbol)
            
            # Formater la réponse
            result = {
                "id": order_details["id"],
                "symbol": standard_symbol,
                "side": order_details["side"],
                "type": order_details["type"],
                "amount": float(order_details["size"]),
                "filled": float(order_details["dealSize"]),
                "remaining": float(order_details["size"]) - float(order_details["dealSize"]),
                "price": float(order_details["price"]) if order_details["price"] else None,
                "cost": float(order_details["dealFunds"]),
                "status": self._map_order_status(order_details["isActive"], order_details["cancelExist"]),
                "timestamp": int(order_details["createdAt"]) / 1000,  # Convertir en secondes
                "exchange": "kucoin"
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
            symbol: Symbole du marché (optionnel, mais recommandé pour de meilleures performances)
            
        Returns:
            True si l'annulation est réussie, False sinon
        """
        await self._ensure_connected()
        await self._handle_rate_limit()
        
        try:
            # Annuler l'ordre
            response = self.trade_client.cancel_order(order_id)
            
            # Vérifier si l'annulation a réussi
            if "cancelledOrderIds" in response and order_id in response["cancelledOrderIds"]:
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
            # Convertir le symbole au format KuCoin
            kucoin_symbol = self._format_symbol(symbol)
            
            # Récupérer le carnet d'ordres
            order_book = self.market_client.get_part_order(kucoin_symbol, limit)
            
            # Formater la réponse
            result = {
                "symbol": symbol,
                "bids": [[float(price), float(amount)] for price, amount in order_book["bids"]],
                "asks": [[float(price), float(amount)] for price, amount in order_book["asks"]],
                "timestamp": int(order_book["time"]) / 1000,  # Convertir en secondes
                "exchange": "kucoin"
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
    
    def _map_order_status(self, is_active: bool, cancel_exist: bool) -> str:
        """
        Mappe le statut d'un ordre KuCoin au format standard.
        
        Args:
            is_active: Si l'ordre est actif
            cancel_exist: Si l'ordre a été annulé
            
        Returns:
            Statut de l'ordre au format standard
        """
        if cancel_exist:
            return "canceled"
        elif is_active:
            return "open"
        else:
            return "closed"
    
    async def _ensure_connected(self):
        """Vérifie que le client est connecté et se reconnecte si nécessaire."""
        if not self.connected:
            await self.connect()
        elif time.time() - self.last_connection_time > 3600:  # Reconnexion toutes les heures
            logger.info("Reconnexion périodique à KuCoin")
            await self.disconnect()
            await self.connect() 