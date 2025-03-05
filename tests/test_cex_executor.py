#!/usr/bin/env python3
"""
Tests unitaires pour le module CEXTradeExecutor.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from decimal import Decimal

from gbpbot.core.trading.cex_executor import CEXTradeExecutor

@pytest.fixture
def mock_config():
    """Fixture pour simuler la configuration."""
    return {
        "cex": {
            "binance": {
                "api_key": "test_key",
                "api_secret": "test_secret",
                "trading": {
                    "min_order_size": 0.001,
                    "max_order_size": 1.0,
                    "order_timeout": 30
                }
            }
        },
        "security": {
            "max_price_change": 0.01,
            "max_confirmation_attempts": 3
        },
        "arbitrage": {
            "max_trade_amount": 1.0
        }
    }

@pytest.fixture
def mock_opportunity():
    """Fixture pour simuler une opportunité d'arbitrage."""
    return {
        "symbol": "BTC/USDT",
        "cex_name": "binance",
        "cex_price": "50000",
        "amount": "0.1",
        "price_difference": "1.5"
    }

@pytest.fixture
async def cex_executor(mock_config):
    """Fixture pour créer une instance de CEXTradeExecutor avec des mocks."""
    with patch('gbpbot.core.trading.cex_executor.ConfigManager') as mock_cm:
        mock_cm.return_value.get_config.return_value = mock_config
        executor = CEXTradeExecutor()
        yield executor

@pytest.mark.asyncio
async def test_verify_market_conditions_success(cex_executor, mock_opportunity):
    """Teste la vérification des conditions de marché avec succès."""
    exchange = AsyncMock()
    exchange.fetch_ticker = AsyncMock(return_value={"last": 50000})
    
    result = await cex_executor._verify_market_conditions(exchange, mock_opportunity)
    assert result is True

@pytest.mark.asyncio
async def test_verify_market_conditions_price_changed(cex_executor, mock_opportunity):
    """Teste la vérification des conditions de marché avec un changement de prix important."""
    exchange = AsyncMock()
    exchange.fetch_ticker = AsyncMock(return_value={"last": 51000})  # +2% de différence
    
    result = await cex_executor._verify_market_conditions(exchange, mock_opportunity)
    assert result is False

@pytest.mark.asyncio
async def test_calculate_trade_amount_success(cex_executor, mock_opportunity):
    """Teste le calcul du montant de trade avec succès."""
    exchange = AsyncMock()
    exchange.load_markets = AsyncMock(return_value={
        "BTC/USDT": {
            "limits": {
                "amount": {
                    "min": 0.001,
                    "max": 2.0
                }
            }
        }
    })
    
    amount = await cex_executor._calculate_trade_amount(exchange, mock_opportunity)
    assert amount == 0.1

@pytest.mark.asyncio
async def test_calculate_trade_amount_below_minimum(cex_executor, mock_opportunity):
    """Teste le calcul du montant de trade inférieur au minimum."""
    mock_opportunity["amount"] = "0.0001"  # En dessous du minimum
    exchange = AsyncMock()
    exchange.load_markets = AsyncMock(return_value={
        "BTC/USDT": {
            "limits": {
                "amount": {
                    "min": 0.001,
                    "max": 2.0
                }
            }
        }
    })
    
    amount = await cex_executor._calculate_trade_amount(exchange, mock_opportunity)
    assert amount is None

@pytest.mark.asyncio
async def test_place_order_success(cex_executor, mock_opportunity):
    """Teste le placement d'un ordre avec succès."""
    exchange = AsyncMock()
    exchange.create_order = AsyncMock(return_value={"id": "test_order"})
    
    order = await cex_executor._place_order(exchange, mock_opportunity, 0.1)
    assert order["id"] == "test_order"
    exchange.create_order.assert_called_once_with(
        symbol="BTC/USDT",
        type="market",
        side="buy",
        amount=0.1
    )

@pytest.mark.asyncio
async def test_wait_for_order_completion_success(cex_executor):
    """Teste l'attente de la confirmation d'un ordre avec succès."""
    exchange = AsyncMock()
    exchange.fetch_order = AsyncMock(return_value={"status": "closed"})
    
    result = await cex_executor._wait_for_order_completion(exchange, "test_order")
    assert result is True

@pytest.mark.asyncio
async def test_wait_for_order_completion_canceled(cex_executor):
    """Teste l'attente de la confirmation d'un ordre annulé."""
    exchange = AsyncMock()
    exchange.fetch_order = AsyncMock(return_value={"status": "canceled"})
    
    result = await cex_executor._wait_for_order_completion(exchange, "test_order")
    assert result is False

@pytest.mark.asyncio
async def test_execute_trade_success(cex_executor, mock_opportunity):
    """Teste l'exécution complète d'un trade avec succès."""
    # Configuration des mocks
    exchange = AsyncMock()
    exchange.fetch_ticker = AsyncMock(return_value={"last": 50000})
    exchange.load_markets = AsyncMock(return_value={
        "BTC/USDT": {
            "limits": {
                "amount": {
                    "min": 0.001,
                    "max": 2.0
                }
            }
        }
    })
    exchange.create_order = AsyncMock(return_value={"id": "test_order"})
    exchange.fetch_order = AsyncMock(return_value={"status": "closed"})
    
    cex_executor.exchanges["binance"] = exchange
    
    result = await cex_executor.execute_trade(mock_opportunity)
    assert result is True

@pytest.mark.asyncio
async def test_execute_trade_market_conditions_failed(cex_executor, mock_opportunity):
    """Teste l'échec d'un trade dû aux conditions de marché."""
    exchange = AsyncMock()
    exchange.fetch_ticker = AsyncMock(return_value={"last": 51000})  # Prix trop différent
    
    cex_executor.exchanges["binance"] = exchange
    
    result = await cex_executor.execute_trade(mock_opportunity)
    assert result is False 