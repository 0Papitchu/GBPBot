#!/usr/bin/env python3
"""
Tests unitaires pour le module TradeExecutor.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from decimal import Decimal
from web3 import Web3

from gbpbot.core.trading.trade_executor import TradeExecutor
from gbpbot.config.config_manager import ConfigManager

@pytest.fixture
def mock_config():
    """Fixture pour simuler la configuration."""
    return {
        "wallet": {
            "private_key": "0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        },
        "arbitrage": {
            "min_liquidity": "1.0",
            "max_trade_amount": "2.0",
            "estimated_gas_limit": 300000
        },
        "security": {
            "max_price_change": 0.01,
            "max_slippage": 0.01,
            "max_gas_price": 100,
            "max_confirmation_attempts": 3
        },
        "dex": {
            "traderjoe": {
                "router_address": "0x60aE616a2155Ee3d9A68541Ba4544862310933d4",
                "router_abi": []
            }
        },
        "tokens": {
            "weth": "0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7"
        }
    }

@pytest.fixture
def mock_opportunity():
    """Fixture pour simuler une opportunité d'arbitrage."""
    return {
        "token_address": "0x1234567890123456789012345678901234567890",
        "dex_name": "traderjoe",
        "cex_name": "binance",
        "dex_price": "1.5",
        "cex_price": "1.6",
        "price_difference": "6.67",
        "estimated_profit": "0.1",
        "liquidity": str(Web3.to_wei(2, 'ether')),
        "gas_cost": str(Web3.to_wei(0.01, 'ether'))
    }

@pytest.fixture
def mock_web3():
    """Fixture pour simuler Web3."""
    web3 = Mock()
    web3.eth = Mock()
    web3.eth.contract = Mock()
    web3.eth.account = Mock()
    return web3

@pytest.fixture
async def trade_executor(mock_config, mock_web3):
    """Fixture pour créer une instance de TradeExecutor avec des mocks."""
    with patch('gbpbot.core.trading.trade_executor.ConfigManager') as mock_cm, \
         patch('gbpbot.core.trading.trade_executor.RPCManager') as mock_rm, \
         patch('gbpbot.core.trading.trade_executor.Web3', return_value=mock_web3):
        
        mock_cm.return_value.get_config.return_value = mock_config
        mock_rm.return_value.get_best_rpc_url.return_value = "http://localhost:8545"
        
        executor = TradeExecutor()
        yield executor

@pytest.mark.asyncio
async def test_verify_market_conditions_success(trade_executor, mock_opportunity):
    """Teste la vérification des conditions de marché avec succès."""
    # Mock des méthodes nécessaires
    trade_executor._get_current_price = AsyncMock(return_value=float(mock_opportunity["dex_price"]))
    trade_executor._check_current_liquidity = AsyncMock(
        return_value=Web3.to_wei(2, 'ether')
    )
    
    result = await trade_executor._verify_market_conditions(mock_opportunity)
    assert result is True

@pytest.mark.asyncio
async def test_verify_market_conditions_price_changed(trade_executor, mock_opportunity):
    """Teste la vérification des conditions de marché avec un changement de prix important."""
    # Simuler un changement de prix de +2%
    current_price = float(mock_opportunity["dex_price"]) * 1.02
    trade_executor._get_current_price = AsyncMock(return_value=current_price)
    trade_executor._check_current_liquidity = AsyncMock(
        return_value=Web3.to_wei(2, 'ether')
    )
    
    result = await trade_executor._verify_market_conditions(mock_opportunity)
    assert result is False

@pytest.mark.asyncio
async def test_verify_market_conditions_low_liquidity(trade_executor, mock_opportunity):
    """Teste la vérification des conditions de marché avec une liquidité insuffisante."""
    trade_executor._get_current_price = AsyncMock(return_value=float(mock_opportunity["dex_price"]))
    trade_executor._check_current_liquidity = AsyncMock(
        return_value=Web3.to_wei(0.5, 'ether')  # Liquidité trop faible
    )
    
    result = await trade_executor._verify_market_conditions(mock_opportunity)
    assert result is False

@pytest.mark.asyncio
async def test_prepare_dex_transaction_buy(trade_executor, mock_opportunity):
    """Teste la préparation d'une transaction d'achat sur DEX."""
    # Mock des méthodes nécessaires
    trade_executor._get_next_nonce = AsyncMock(return_value=1)
    trade_executor._get_max_fee_per_gas = AsyncMock(return_value=Web3.to_wei(50, 'gwei'))
    trade_executor._get_max_priority_fee = AsyncMock(return_value=Web3.to_wei(2, 'gwei'))
    
    # Modifier l'opportunité pour un achat
    mock_opportunity["price_difference"] = "6.67"  # Positif = achat
    
    tx = await trade_executor._prepare_dex_transaction(mock_opportunity)
    assert tx is not None
    assert "nonce" in tx
    assert tx["nonce"] == 1

@pytest.mark.asyncio
async def test_prepare_dex_transaction_sell(trade_executor, mock_opportunity):
    """Teste la préparation d'une transaction de vente sur DEX."""
    # Mock des méthodes nécessaires
    trade_executor._get_next_nonce = AsyncMock(return_value=1)
    trade_executor._get_max_fee_per_gas = AsyncMock(return_value=Web3.to_wei(50, 'gwei'))
    trade_executor._get_max_priority_fee = AsyncMock(return_value=Web3.to_wei(2, 'gwei'))
    
    # Modifier l'opportunité pour une vente
    mock_opportunity["price_difference"] = "-6.67"  # Négatif = vente
    
    tx = await trade_executor._prepare_dex_transaction(mock_opportunity)
    assert tx is not None
    assert "nonce" in tx
    assert tx["nonce"] == 1

@pytest.mark.asyncio
async def test_execute_arbitrage_success(trade_executor, mock_opportunity):
    """Teste l'exécution complète d'un arbitrage avec succès."""
    # Mock de toutes les méthodes nécessaires
    trade_executor._verify_market_conditions = AsyncMock(return_value=True)
    trade_executor._prepare_dex_transaction = AsyncMock(return_value={"nonce": 1})
    trade_executor._check_slippage = Mock(return_value=True)
    trade_executor._send_transaction = AsyncMock(return_value="0x123")
    trade_executor._wait_for_confirmation = AsyncMock(return_value=True)
    
    result = await trade_executor.execute_arbitrage(mock_opportunity)
    assert result is True

@pytest.mark.asyncio
async def test_execute_arbitrage_market_conditions_failed(trade_executor, mock_opportunity):
    """Teste l'échec de l'arbitrage dû aux conditions de marché."""
    trade_executor._verify_market_conditions = AsyncMock(return_value=False)
    
    result = await trade_executor.execute_arbitrage(mock_opportunity)
    assert result is False

@pytest.mark.asyncio
async def test_execute_arbitrage_slippage_too_high(trade_executor, mock_opportunity):
    """Teste l'échec de l'arbitrage dû à un slippage trop important."""
    trade_executor._verify_market_conditions = AsyncMock(return_value=True)
    trade_executor._prepare_dex_transaction = AsyncMock(return_value={"nonce": 1})
    trade_executor._check_slippage = Mock(return_value=False)
    
    result = await trade_executor.execute_arbitrage(mock_opportunity)
    assert result is False

@pytest.mark.asyncio
async def test_wait_for_confirmation_success(trade_executor):
    """Teste l'attente de confirmation d'une transaction avec succès."""
    trade_executor.rpc_manager.call_rpc = AsyncMock(
        return_value={"status": "0x1"}
    )
    
    result = await trade_executor._wait_for_confirmation("0x123")
    assert result is True

@pytest.mark.asyncio
async def test_wait_for_confirmation_failure(trade_executor):
    """Teste l'attente de confirmation d'une transaction échouée."""
    trade_executor.rpc_manager.call_rpc = AsyncMock(
        return_value={"status": "0x0"}
    )
    
    result = await trade_executor._wait_for_confirmation("0x123")
    assert result is False

@pytest.mark.asyncio
async def test_get_next_nonce_success(trade_executor):
    """Teste la récupération du prochain nonce valide."""
    trade_executor.rpc_manager.call_rpc = AsyncMock(return_value=10)
    
    nonce = await trade_executor._get_next_nonce()
    assert nonce == 10
    
    # Test de l'incrémentation locale
    trade_executor.last_nonce = 10
    nonce = await trade_executor._get_next_nonce()
    assert nonce == 11 