import pytest
import asyncio
from unittest.mock import MagicMock, patch
from decimal import Decimal
from web3 import Web3

from gbpbot.core.price_feed.dex_feed import DEXPriceFeed
from gbpbot.core.rpc.rpc_manager import RPCManager
from gbpbot.core.monitoring.monitor import BotMonitor

@pytest.fixture
def mock_monitor():
    """Fixture pour un moniteur simulé."""
    monitor = MagicMock(spec=BotMonitor)
    return monitor

@pytest.fixture
def mock_rpc_manager():
    """Fixture pour un gestionnaire RPC simulé."""
    manager = MagicMock(spec=RPCManager)
    return manager

@pytest.fixture
def mock_config():
    """Fixture pour une configuration simulée."""
    return {
        "price_feed": {
            "dex_update_interval": 1
        },
        "dex": {
            "trader_joe": {
                "router": "0x60aE616a2155Ee3d9A68541Ba4544862310933d4",
                "factory": "0x9Ad6C38BE94206cA50bb0d90783181662f0Cfa10"
            },
            "pangolin": {
                "router": "0xE54Ca86531e17Ef3616d22Ca28b0D458b6C89106",
                "factory": "0xefa94DE7a4656D787667C749f7E1223D71E9FD88"
            }
        },
        "tokens": {
            "WAVAX": {
                "address": "0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7",
                "decimals": 18
            },
            "USDC": {
                "address": "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E",
                "decimals": 6
            }
        }
    }

@pytest.fixture
def dex_feed(mock_rpc_manager, mock_monitor, mock_config):
    """Fixture pour un feed DEX avec des dépendances simulées."""
    feed = DEXPriceFeed(mock_config, mock_rpc_manager)
    feed.monitor = mock_monitor  # Ajouter le moniteur manuellement
    return feed

@pytest.mark.asyncio
async def test_dex_feed_initialization(dex_feed):
    """Teste l'initialisation du feed DEX."""
    assert dex_feed.rpc_manager is not None
    assert dex_feed.price_cache is not None
    assert dex_feed.is_running is False

@pytest.mark.asyncio
async def test_dex_feed_start_stop(dex_feed):
    """Teste le démarrage et l'arrêt du feed DEX."""
    # Mock des méthodes internes
    dex_feed._init_contracts = MagicMock(return_value=asyncio.Future())
    dex_feed._init_contracts.return_value.set_result(None)
    
    dex_feed._start_price_monitoring = MagicMock(return_value=asyncio.Future())
    dex_feed._start_price_monitoring.return_value.set_result(None)
    
    # Démarrer le feed
    await dex_feed.start()
    
    # Vérifier que les méthodes internes ont été appelées
    dex_feed._init_contracts.assert_called_once()
    dex_feed._start_price_monitoring.assert_called_once()
    assert dex_feed.is_running is True
    
    # Arrêter le feed
    await dex_feed.stop()
    
    # Vérifier que le feed est arrêté
    assert dex_feed.is_running is False

@pytest.mark.asyncio
async def test_get_price(dex_feed):
    """Teste la récupération d'un prix."""
    # Simuler un prix dans le cache
    token_address = "0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7"  # WAVAX
    dex_feed.prices = {
        f"{token_address}_USDC": {
            "price": Decimal('30.5'),
            "exchange": "trader_joe",
            "timestamp": 1234567890
        }
    }
    
    # Mock de la méthode _get_price_from_dex
    dex_feed._get_price_from_dex = MagicMock(return_value=asyncio.Future())
    dex_feed._get_price_from_dex.return_value.set_result(Decimal('30.5'))
    
    # Récupérer le prix
    price = await dex_feed.get_price(token_address)
    
    # Vérifier que le prix est correct
    assert price == Decimal('30.5')

@pytest.mark.asyncio
async def test_get_price_no_cache(dex_feed):
    """Teste la récupération d'un prix sans cache."""
    # Simuler un cache vide
    dex_feed.prices = {}
    
    # Mock de la méthode _get_price_from_dex
    token_address = "0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7"  # WAVAX
    dex_feed._get_price_from_dex = MagicMock(return_value=asyncio.Future())
    dex_feed._get_price_from_dex.return_value.set_result(Decimal('30.5'))
    
    # Récupérer le prix
    price = await dex_feed.get_price(token_address)
    
    # Vérifier que le prix est correct et que la méthode a été appelée
    assert price == Decimal('30.5')
    dex_feed._get_price_from_dex.assert_called_once()

@pytest.mark.asyncio
async def test_get_liquidity(dex_feed):
    """Teste la récupération de la liquidité."""
    # Simuler une liquidité dans le cache
    token_address = "0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7"  # WAVAX
    dex_feed.liquidity_cache = {
        token_address: {
            "liquidity": Decimal('1000000'),
            "timestamp": 1234567890
        }
    }
    
    # Récupérer la liquidité
    liquidity = await dex_feed.get_liquidity(token_address)
    
    # Vérifier que la liquidité est correcte
    assert liquidity == Decimal('1000000')

@pytest.mark.asyncio
async def test_validate_price(dex_feed):
    """Teste la validation d'un prix."""
    token_address = "0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7"  # WAVAX
    
    # Simuler la méthode get_price
    original_get_price = dex_feed.get_price
    dex_feed.get_price = MagicMock(return_value=asyncio.Future())
    dex_feed.get_price.return_value.set_result(Decimal('30.5'))
    
    # Valider un prix proche
    is_valid = await dex_feed.validate_price(token_address, Decimal('31.0'))
    
    # Vérifier que le prix est valide (moins de 5% d'écart)
    assert is_valid is True
    
    # Valider un prix trop éloigné
    is_valid = await dex_feed.validate_price(token_address, Decimal('40.0'))
    
    # Vérifier que le prix n'est pas valide (plus de 5% d'écart)
    assert is_valid is False
    
    # Restaurer la méthode originale
    dex_feed.get_price = original_get_price

@pytest.mark.asyncio
async def test_init_contracts(dex_feed):
    """Teste l'initialisation des contrats."""
    # Simuler la méthode get_web3 du rpc_manager
    web3 = MagicMock(spec=Web3)
    dex_feed.rpc_manager.get_web3 = MagicMock(return_value=asyncio.Future())
    dex_feed.rpc_manager.get_web3.return_value.set_result(web3)
    
    # Simuler la création de contrats
    web3.eth.contract = MagicMock(return_value="contract")
    
    # Initialiser les contrats
    await dex_feed._init_contracts()
    
    # Vérifier que les contrats ont été créés
    assert "trader_joe_router" in dex_feed.router_contracts
    assert "pangolin_router" in dex_feed.router_contracts 