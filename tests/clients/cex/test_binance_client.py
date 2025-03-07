#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Tests unitaires pour le client Binance.

Ce module contient les tests unitaires pour vérifier le bon fonctionnement
du client Binance, y compris l'initialisation, les requêtes API et la gestion des erreurs.
"""

import asyncio
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import json
from decimal import Decimal
from typing import Dict, Any, List

from gbpbot.clients.cex.binance_client import BinanceClient


class TestBinanceClient(unittest.TestCase):
    """Classe de tests pour le client Binance."""

    def setUp(self):
        """Initialisation avant chaque test."""
        self.client = BinanceClient(
            api_key="test_api_key",
            api_secret="test_api_secret",
            testnet=True
        )
        # Remplacer la session par un mock
        self.client._session = MagicMock()
        self.client._session.request = AsyncMock()
        
        # Mock pour la réponse HTTP
        self.mock_response = MagicMock()
        self.mock_response.status = 200
        self.mock_response.json = AsyncMock()
        
        # Configurer le mock de session pour retourner notre mock de réponse
        self.client._session.request.return_value.__aenter__.return_value = self.mock_response

    def tearDown(self):
        """Nettoyage après chaque test."""
        self.client = None

    def test_init(self):
        """Tester l'initialisation du client."""
        client = BinanceClient(testnet=True)
        self.assertEqual(client.api_url, BinanceClient.API_TESTNET_URL)
        self.assertIsNone(client.api_key)
        self.assertIsNone(client.api_secret)
        
        client = BinanceClient(testnet=False)
        self.assertEqual(client.api_url, BinanceClient.API_URL)

    async def async_test(self, coro):
        """Exécuter un test asynchrone."""
        return await coro

    def test_get_ticker(self):
        """Tester la récupération d'un ticker."""
        # Préparer les données de réponse
        ticker_data = {
            "symbol": "BTCUSDT",
            "bidPrice": "50000.00",
            "askPrice": "50100.00",
            "lastPrice": "50050.00",
            "highPrice": "51000.00",
            "lowPrice": "49000.00",
            "volume": "100.00",
            "quoteVolume": "5000000.00",
            "closeTime": 1630000000000,
            "priceChange": "1000.00",
            "priceChangePercent": "2.00"
        }
        self.mock_response.json.return_value = ticker_data
        
        # Exécuter le test
        ticker = asyncio.run(self.async_test(self.client.get_ticker("BTC/USDT")))
        
        # Vérifier les assertions
        self.assertEqual(ticker["symbol"], "BTC/USDT")
        self.assertEqual(ticker["last"], Decimal("50050.00"))
        self.assertEqual(ticker["bid"], Decimal("50000.00"))
        self.assertEqual(ticker["ask"], Decimal("50100.00"))
        
        # Vérifier que la requête a été effectuée correctement
        self.client._session.request.assert_called_once()
        call_args = self.client._session.request.call_args[1]
        self.assertEqual(call_args["method"], "GET")
        self.assertTrue("/api/v3/ticker/24hr" in call_args["url"])
        self.assertEqual(call_args["params"]["symbol"], "BTCUSDT")

    def test_get_price(self):
        """Tester la récupération d'un prix."""
        # Préparer les données de réponse
        price_data = {
            "symbol": "BTCUSDT",
            "price": "50000.00"
        }
        self.mock_response.json.return_value = price_data
        
        # Exécuter le test
        price = asyncio.run(self.async_test(self.client.get_price("BTC/USDT")))
        
        # Vérifier les assertions
        self.assertEqual(price, Decimal("50000.00"))
        
        # Vérifier que la requête a été effectuée correctement
        self.client._session.request.assert_called_once()
        call_args = self.client._session.request.call_args[1]
        self.assertEqual(call_args["method"], "GET")
        self.assertTrue("/api/v3/ticker/price" in call_args["url"])
        self.assertEqual(call_args["params"]["symbol"], "BTCUSDT")

    def test_get_orderbook(self):
        """Tester la récupération d'un carnet d'ordres."""
        # Préparer les données de réponse
        orderbook_data = {
            "lastUpdateId": 1027024,
            "bids": [
                ["50000.00", "1.00"],
                ["49990.00", "2.00"]
            ],
            "asks": [
                ["50100.00", "1.50"],
                ["50200.00", "2.50"]
            ]
        }
        self.mock_response.json.return_value = orderbook_data
        
        # Exécuter le test
        orderbook = asyncio.run(self.async_test(self.client.get_orderbook("BTC/USDT", 2)))
        
        # Vérifier les assertions
        self.assertEqual(orderbook["symbol"], "BTC/USDT")
        self.assertEqual(len(orderbook["bids"]), 2)
        self.assertEqual(len(orderbook["asks"]), 2)
        self.assertEqual(orderbook["bids"][0][0], Decimal("50000.00"))
        self.assertEqual(orderbook["bids"][0][1], Decimal("1.00"))
        
        # Vérifier que la requête a été effectuée correctement
        self.client._session.request.assert_called_once()
        call_args = self.client._session.request.call_args[1]
        self.assertEqual(call_args["method"], "GET")
        self.assertTrue("/api/v3/depth" in call_args["url"])
        self.assertEqual(call_args["params"]["symbol"], "BTCUSDT")
        self.assertEqual(call_args["params"]["limit"], 2)

    def test_get_balance(self):
        """Tester la récupération des soldes."""
        # Préparer les données de réponse
        balance_data = {
            "makerCommission": 10,
            "takerCommission": 10,
            "buyerCommission": 0,
            "sellerCommission": 0,
            "canTrade": True,
            "canWithdraw": True,
            "canDeposit": True,
            "updateTime": 1630000000000,
            "accountType": "SPOT",
            "balances": [
                {
                    "asset": "BTC",
                    "free": "1.00",
                    "locked": "0.00"
                },
                {
                    "asset": "ETH",
                    "free": "10.00",
                    "locked": "5.00"
                },
                {
                    "asset": "USDT",
                    "free": "5000.00",
                    "locked": "0.00"
                }
            ]
        }
        self.mock_response.json.return_value = balance_data
        
        # Exécuter le test pour tous les soldes
        balances = asyncio.run(self.async_test(self.client.get_balance()))
        
        # Vérifier les assertions pour tous les soldes
        self.assertEqual(len(balances), 3)
        self.assertEqual(balances["BTC"], Decimal("1.00"))
        self.assertEqual(balances["ETH"], Decimal("15.00"))  # free + locked
        
        # Réinitialiser le mock pour le test suivant
        self.client._session.request.reset_mock()
        self.mock_response.json.return_value = balance_data
        
        # Exécuter le test pour un solde spécifique
        btc_balance = asyncio.run(self.async_test(self.client.get_balance("BTC")))
        
        # Vérifier les assertions pour un solde spécifique
        self.assertEqual(btc_balance, Decimal("1.00"))

    def test_create_order(self):
        """Tester la création d'un ordre."""
        # Préparer les données de réponse
        order_data = {
            "symbol": "BTCUSDT",
            "orderId": 12345,
            "orderListId": -1,
            "clientOrderId": "x-test",
            "transactTime": 1630000000000,
            "price": "50000.00",
            "origQty": "1.00",
            "executedQty": "0.00",
            "cummulativeQuoteQty": "0.00",
            "status": "NEW",
            "timeInForce": "GTC",
            "type": "LIMIT",
            "side": "BUY"
        }
        self.mock_response.json.return_value = order_data
        
        # Exécuter le test
        order = asyncio.run(self.async_test(self.client.create_order(
            symbol="BTC/USDT",
            order_type="limit",
            side="buy",
            amount=Decimal("1.00"),
            price=Decimal("50000.00")
        )))
        
        # Vérifier les assertions
        self.assertEqual(order["id"], "12345")
        self.assertEqual(order["symbol"], "BTC/USDT")
        self.assertEqual(order["type"], "limit")
        self.assertEqual(order["side"], "buy")
        self.assertEqual(order["amount"], Decimal("1.00"))
        self.assertEqual(order["price"], Decimal("50000.00"))
        self.assertEqual(order["status"], "new")
        
        # Vérifier que la requête a été effectuée correctement
        self.client._session.request.assert_called_once()
        call_args = self.client._session.request.call_args[1]
        self.assertEqual(call_args["method"], "POST")
        self.assertTrue("/api/v3/order" in call_args["url"])
        self.assertEqual(call_args["params"]["symbol"], "BTCUSDT")
        self.assertEqual(call_args["params"]["side"], "BUY")
        self.assertEqual(call_args["params"]["type"], "LIMIT")
        self.assertEqual(call_args["params"]["quantity"], "1.00")
        self.assertEqual(call_args["params"]["price"], "50000.00")

    def test_cancel_order(self):
        """Tester l'annulation d'un ordre."""
        # Préparer les données de réponse
        cancel_data = {
            "symbol": "BTCUSDT",
            "origClientOrderId": "x-test",
            "orderId": 12345,
            "orderListId": -1,
            "clientOrderId": "y-test",
            "price": "50000.00",
            "origQty": "1.00",
            "executedQty": "0.00",
            "cummulativeQuoteQty": "0.00",
            "status": "CANCELED",
            "timeInForce": "GTC",
            "type": "LIMIT",
            "side": "BUY"
        }
        self.mock_response.json.return_value = cancel_data
        
        # Exécuter le test
        order = asyncio.run(self.async_test(self.client.cancel_order("12345", "BTC/USDT")))
        
        # Vérifier les assertions
        self.assertEqual(order["id"], "12345")
        self.assertEqual(order["symbol"], "BTC/USDT")
        self.assertEqual(order["status"], "canceled")
        
        # Vérifier que la requête a été effectuée correctement
        self.client._session.request.assert_called_once()
        call_args = self.client._session.request.call_args[1]
        self.assertEqual(call_args["method"], "DELETE")
        self.assertTrue("/api/v3/order" in call_args["url"])
        self.assertEqual(call_args["params"]["symbol"], "BTCUSDT")
        self.assertEqual(call_args["params"]["orderId"], "12345")

    def test_get_markets(self):
        """Tester la récupération des marchés disponibles."""
        # Préparer les données de réponse
        exchange_info = {
            "timezone": "UTC",
            "serverTime": 1630000000000,
            "rateLimits": [],
            "exchangeFilters": [],
            "symbols": [
                {
                    "symbol": "BTCUSDT",
                    "status": "TRADING",
                    "baseAsset": "BTC",
                    "baseAssetPrecision": 8,
                    "quoteAsset": "USDT",
                    "quotePrecision": 8,
                    "filters": [
                        {
                            "filterType": "PRICE_FILTER",
                            "minPrice": "0.01",
                            "maxPrice": "1000000.00",
                            "tickSize": "0.01"
                        },
                        {
                            "filterType": "LOT_SIZE",
                            "minQty": "0.00001",
                            "maxQty": "9000.00000",
                            "stepSize": "0.00001"
                        }
                    ]
                },
                {
                    "symbol": "ETHUSDT",
                    "status": "TRADING",
                    "baseAsset": "ETH",
                    "baseAssetPrecision": 8,
                    "quoteAsset": "USDT",
                    "quotePrecision": 8,
                    "filters": [
                        {
                            "filterType": "PRICE_FILTER",
                            "minPrice": "0.01",
                            "maxPrice": "100000.00",
                            "tickSize": "0.01"
                        },
                        {
                            "filterType": "LOT_SIZE",
                            "minQty": "0.0001",
                            "maxQty": "9000.0000",
                            "stepSize": "0.0001"
                        }
                    ]
                }
            ]
        }
        self.mock_response.json.return_value = exchange_info
        
        # Exécuter le test
        markets = asyncio.run(self.async_test(self.client.get_markets()))
        
        # Vérifier les assertions
        self.assertEqual(len(markets), 2)
        self.assertEqual(markets[0]["symbol"], "BTC/USDT")
        self.assertEqual(markets[0]["base"], "BTC")
        self.assertEqual(markets[0]["quote"], "USDT")
        self.assertEqual(markets[1]["symbol"], "ETH/USDT")
        self.assertEqual(markets[1]["base"], "ETH")
        self.assertEqual(markets[1]["quote"], "USDT")
        
        # Vérifier que les limites sont correctement récupérées
        self.assertEqual(markets[0]["limits"]["price"]["min"], Decimal("0.01"))
        self.assertEqual(markets[0]["limits"]["price"]["max"], Decimal("1000000.00"))
        self.assertEqual(markets[0]["limits"]["amount"]["min"], Decimal("0.00001"))
        self.assertEqual(markets[0]["limits"]["amount"]["max"], Decimal("9000.00000"))

    def test_error_handling(self):
        """Tester la gestion des erreurs."""
        # Modifier le mock pour simuler une erreur
        self.mock_response.status = 400
        self.mock_response.text = AsyncMock(return_value='{"code": -1121, "msg": "Invalid symbol"}')
        
        # Vérifier que l'exception est bien levée
        with self.assertRaises(Exception):
            asyncio.run(self.async_test(self.client.get_ticker("INVALID/SYMBOL")))
        
        # Vérifier que l'erreur a été enregistrée
        self.assertEqual(self.client.error_count, 1)
        self.assertIsNotNone(self.client.last_error)

    def test_cache(self):
        """Tester la mise en cache des données."""
        # Préparer les données de réponse pour le premier appel
        ticker_data = {
            "symbol": "BTCUSDT",
            "bidPrice": "50000.00",
            "askPrice": "50100.00",
            "lastPrice": "50050.00",
            "highPrice": "51000.00",
            "lowPrice": "49000.00",
            "volume": "100.00",
            "quoteVolume": "5000000.00",
            "closeTime": 1630000000000,
            "priceChange": "1000.00",
            "priceChangePercent": "2.00"
        }
        self.mock_response.json.return_value = ticker_data
        
        # Premier appel à get_ticker (sans cache)
        asyncio.run(self.async_test(self.client.get_ticker("BTC/USDT")))
        
        # Vérifier que la requête a été effectuée
        self.assertEqual(self.client._session.request.call_count, 1)
        
        # Deuxième appel à get_ticker (avec cache)
        asyncio.run(self.async_test(self.client.get_ticker("BTC/USDT")))
        
        # Vérifier que la requête n'a pas été effectuée une deuxième fois
        self.assertEqual(self.client._session.request.call_count, 1)


if __name__ == "__main__":
    unittest.main() 