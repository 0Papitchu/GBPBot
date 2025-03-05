import pytest
import asyncio
from unittest.mock import MagicMock, patch
from decimal import Decimal

from gbpbot.core.price_feed.cex_feed import CEXPriceFeed
from gbpbot.core.monitoring.monitor import BotMonitor

@pytest.fixture
def mock_monitor():
    """Fixture pour un moniteur simulé."""
    monitor = MagicMock(spec=BotMonitor)
    return monitor

@pytest.fixture
def mock_config():
    """Fixture pour une configuration simulée."""
    return {
        "price_feed": {
            "cex_update_interval": 1
        },
        "cex": {
            "binance": {
                "api_key": "test_key",
                "api_secret": "test_secret"
            },
            "kucoin": {
                "api_key": "test_key",
                "api_secret": "test_secret"
            }
        },
        "tokens": {
            "AVAX": {
                "symbol": "AVAX",
                "cex_symbols": {
                    "binance": "AVAXUSDT",
                    "kucoin": "AVAX-USDT"
                }
            },
            "ETH": {
                "symbol": "ETH",
                "cex_symbols": {
                    "binance": "ETHUSDT",
                    "kucoin": "ETH-USDT"
                }
            }
        }
    }

@pytest.fixture
def cex_feed(mock_monitor, mock_config):
    """Fixture pour un feed CEX avec des dépendances simulées."""
    with patch('aiohttp.ClientSession') as mock_session:
        feed = CEXPriceFeed(mock_config, mock_monitor)
        feed.session = mock_session.return_value
        return feed

@pytest.mark.asyncio
async def test_cex_feed_initialization(cex_feed):
    """Teste l'initialisation du feed CEX."""
    assert cex_feed.monitor is not None
    assert cex_feed.is_running is False
    assert cex_feed.cex_configs is not None
    assert cex_feed.update_interval == 1

@pytest.mark.asyncio
async def test_cex_feed_start_stop(cex_feed):
    """Teste le démarrage et l'arrêt du feed CEX."""
    # Mock des méthodes internes
    cex_feed._init_websockets = MagicMock(return_value=asyncio.Future())
    cex_feed._init_websockets.return_value.set_result(None)
    
    cex_feed._start_price_monitoring = MagicMock(return_value=asyncio.Future())
    cex_feed._start_price_monitoring.return_value.set_result(None)
    
    # Démarrer le feed
    await cex_feed.start()
    
    # Vérifier que les méthodes internes ont été appelées
    cex_feed._init_websockets.assert_called_once()
    assert cex_feed.is_running is True
    
    # Arrêter le feed
    await cex_feed.stop()
    
    # Vérifier que le feed est arrêté
    assert cex_feed.is_running is False
    assert cex_feed.session.close.called

@pytest.mark.asyncio
async def test_get_price(cex_feed):
    """Teste la récupération d'un prix."""
    # Simuler un prix dans le cache
    token_symbol = "AVAX"
    cex_feed.prices = {
        f"{token_symbol}_binance": {
            "price": Decimal('30.5'),
            "exchange": "binance",
            "timestamp": 1234567890
        }
    }
    
    # Mock de la méthode _get_price_from_cex
    cex_feed._get_price_from_cex = MagicMock(return_value=asyncio.Future())
    cex_feed._get_price_from_cex.return_value.set_result(Decimal('30.5'))
    
    # Récupérer le prix
    price = await cex_feed.get_price(token_symbol)
    
    # Vérifier que le prix est correct
    assert price == Decimal('30.5')

@pytest.mark.asyncio
async def test_get_price_no_cache(cex_feed):
    """Teste la récupération d'un prix sans cache."""
    # Simuler un cache vide
    cex_feed.prices = {}
    
    # Mock de la méthode _get_price_from_cex
    token_symbol = "AVAX"
    cex_feed._get_price_from_cex = MagicMock(return_value=asyncio.Future())
    cex_feed._get_price_from_cex.return_value.set_result(Decimal('30.5'))
    
    # Récupérer le prix
    price = await cex_feed.get_price(token_symbol)
    
    # Vérifier que le prix est correct et que la méthode a été appelée
    assert price == Decimal('30.5')
    cex_feed._get_price_from_cex.assert_called_once()

@pytest.mark.asyncio
async def test_fetch_price_binance(cex_feed):
    """Teste la récupération d'un prix depuis Binance."""
    # Mock de la réponse HTTP
    mock_response = MagicMock()
    mock_response.json.return_value = asyncio.Future()
    mock_response.json.return_value.set_result({"price": "30.5"})
    
    cex_feed.session.get = MagicMock(return_value=asyncio.Future())
    cex_feed.session.get.return_value.set_result(mock_response)
    
    # Récupérer le prix
    price = await cex_feed._fetch_price_binance("AVAXUSDT")
    
    # Vérifier que le prix est correct
    assert price == Decimal('30.5')
    cex_feed.session.get.assert_called_once()

@pytest.mark.asyncio
async def test_fetch_price_kucoin(cex_feed):
    """Teste la récupération d'un prix depuis KuCoin."""
    # Mock de la réponse HTTP
    mock_response = MagicMock()
    mock_response.json.return_value = asyncio.Future()
    mock_response.json.return_value.set_result({"data": {"price": "30.5"}})
    
    cex_feed.session.get = MagicMock(return_value=asyncio.Future())
    cex_feed.session.get.return_value.set_result(mock_response)
    
    # Récupérer le prix
    price = await cex_feed._fetch_price_kucoin("AVAX-USDT")
    
    # Vérifier que le prix est correct
    assert price == Decimal('30.5')
    cex_feed.session.get.assert_called_once() 