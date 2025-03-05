import pytest
import asyncio
from unittest.mock import MagicMock, patch
from decimal import Decimal

# Utiliser des imports relatifs pour éviter les problèmes de résolution de module
from gbpbot.core.price_feed.price_manager import PriceManager
from gbpbot.core.monitoring.monitor import BotMonitor
from gbpbot.core.price_feed.dex_feed import DEXPriceFeed
from gbpbot.core.price_feed.cex_feed import CEXPriceFeed
from gbpbot.core.price_feed.price_normalizer import PriceNormalizer as EnhancedPriceNormalizer

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
            "cache_timeout": 5,
            "dex_update_interval": 1,
            "cex_update_interval": 1,
            "outlier_threshold": 2.0,
            "min_sources": 2
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
        "cex": {
            "binance": {
                "api_key": "test_key",
                "api_secret": "test_secret"
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
def price_manager(mock_monitor, mock_config):
    """Fixture pour un gestionnaire de prix avec des dépendances simulées."""
    with patch('gbpbot.core.price_feed.price_manager.ConfigManager') as mock_config_manager:
        mock_config_manager().get_config.return_value = mock_config
        
        # Mock des dépendances
        with patch('gbpbot.core.price_feed.price_manager.DEXPriceFeed') as mock_dex_feed, \
             patch('gbpbot.core.price_feed.price_manager.CEXPriceFeed') as mock_cex_feed, \
             patch('gbpbot.core.price_feed.price_manager.PriceNormalizer') as mock_normalizer:
            
            # Configurer les mocks pour qu'ils retournent des instances simulées
            mock_dex_feed.return_value = MagicMock(spec=DEXPriceFeed)
            mock_cex_feed.return_value = MagicMock(spec=CEXPriceFeed)
            mock_normalizer.return_value = MagicMock(spec=EnhancedPriceNormalizer)
            
            manager = PriceManager(mock_monitor)
            return manager

@pytest.mark.asyncio
async def test_price_manager_initialization(price_manager):
    """Teste l'initialisation du gestionnaire de prix."""
    assert price_manager.monitor is not None
    assert price_manager.dex_feed is not None
    assert price_manager.cex_feed is not None
    assert price_manager.normalizer is not None
    assert price_manager.is_running is False

@pytest.mark.asyncio
async def test_price_manager_start_stop(price_manager):
    """Teste le démarrage et l'arrêt du gestionnaire de prix."""
    # Simuler les méthodes start des feeds
    price_manager.dex_feed.start = MagicMock(return_value=asyncio.Future())
    price_manager.dex_feed.start.return_value.set_result(None)
    
    price_manager.cex_feed.start = MagicMock(return_value=asyncio.Future())
    price_manager.cex_feed.start.return_value.set_result(None)
    
    # Démarrer le gestionnaire
    await price_manager.start()
    
    # Vérifier que les feeds ont été démarrés
    price_manager.dex_feed.start.assert_called_once()
    price_manager.cex_feed.start.assert_called_once()
    assert price_manager.is_running is True
    
    # Simuler les méthodes stop des feeds
    price_manager.dex_feed.stop = MagicMock(return_value=asyncio.Future())
    price_manager.dex_feed.stop.return_value.set_result(None)
    
    price_manager.cex_feed.stop = MagicMock(return_value=asyncio.Future())
    price_manager.cex_feed.stop.return_value.set_result(None)
    
    # Arrêter le gestionnaire
    await price_manager.stop()
    
    # Vérifier que les feeds ont été arrêtés
    price_manager.dex_feed.stop.assert_called_once()
    price_manager.cex_feed.stop.assert_called_once()
    assert price_manager.is_running is False

@pytest.mark.asyncio
async def test_get_price(price_manager):
    """Teste la récupération d'un prix."""
    # Simuler la méthode get_price du DEX feed
    price_manager.dex_feed.get_price = MagicMock(return_value=asyncio.Future())
    price_manager.dex_feed.get_price.return_value.set_result(Decimal('30.5'))
    
    # Récupérer le prix
    token_address = "0x1234567890123456789012345678901234567890"
    price = await price_manager.get_price(token_address)
    
    # Vérifier que le prix est correct
    assert price == Decimal('30.5')
    price_manager.dex_feed.get_price.assert_called_once_with(token_address)

@pytest.mark.asyncio
async def test_get_price_with_cache(price_manager):
    """Teste la mise en cache des prix."""
    token_address = "0x1234567890123456789012345678901234567890"
    
    # Simuler la méthode get_price du DEX feed
    price_manager.dex_feed.get_price = MagicMock(return_value=asyncio.Future())
    price_manager.dex_feed.get_price.return_value.set_result(Decimal('30.5'))
    
    # Récupérer le prix une première fois
    price1 = await price_manager.get_price(token_address)
    
    # Vérifier que le prix est correct
    assert price1 == Decimal('30.5')
    price_manager.dex_feed.get_price.assert_called_once_with(token_address)
    
    # Réinitialiser le mock
    price_manager.dex_feed.get_price.reset_mock()
    
    # Récupérer le prix une deuxième fois (devrait utiliser le cache)
    price2 = await price_manager.get_price(token_address)
    
    # Vérifier que le prix est le même et que get_price n'a pas été appelé
    assert price2 == Decimal('30.5')
    price_manager.dex_feed.get_price.assert_not_called()

@pytest.mark.asyncio
async def test_get_normalized_price(price_manager):
    """Teste la normalisation des prix."""
    token_address = "0x1234567890123456789012345678901234567890"
    
    # Simuler les méthodes get_price des feeds
    price_manager.dex_feed.get_price = MagicMock(return_value=asyncio.Future())
    price_manager.dex_feed.get_price.return_value.set_result(Decimal('30.5'))
    
    price_manager.cex_feed.get_price = MagicMock(return_value=asyncio.Future())
    price_manager.cex_feed.get_price.return_value.set_result(Decimal('31.0'))
    
    # Simuler la méthode normalize_price du normalizer
    price_manager.normalizer.normalize_price = MagicMock(return_value=Decimal('30.75'))
    
    # Récupérer le prix normalisé
    price = await price_manager.get_normalized_price(token_address)
    
    # Vérifier que le prix est correct
    assert price == Decimal('30.75')
    price_manager.dex_feed.get_price.assert_called_once_with(token_address)
    price_manager.cex_feed.get_price.assert_called_once_with(token_address)
    price_manager.normalizer.normalize_price.assert_called_once() 