#!/usr/bin/env python3
"""
Tests d'intégration pour le système de prix.
Valide l'interaction entre DEXPriceFeed, CEXPriceFeed et PriceAggregator.
"""

import pytest
import asyncio
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch

from gbpbot.core.price_feed.base import BasePriceFeed
from gbpbot.core.price_feed.dex_feed import DEXPriceFeed
from gbpbot.core.price_feed.cex_feed import CEXPriceFeed
from gbpbot.core.price_feed import EnhancedPriceNormalizer
from gbpbot.core.price_feed.aggregator import PriceAggregator
from gbpbot.core.rpc.rpc_manager import RPCManager

@pytest.fixture
def config():
    """Configuration de test."""
    return {
        'price_feed': {
            'update_interval': 10,
            'cache_ttl': 30,
            'max_price_deviation': 0.05,
            'min_sources': 2,
            'outlier_threshold': 2.0,
            'max_history_size': 100,
            'max_volatility': 0.02,
            'min_arbitrage_spread': 0.01,
            'min_trade_volume': 0.1,
            'dex_fee': 0.003,
            'cex_fee': 0.001,
            'tokens': ['ETH-USDT', 'BTC-USDT']
        },
        'dex': {
            'max_price_change': 0.02,
            'min_liquidity': 1000
        },
        'cex': {
            'exchanges': [
                {
                    'name': 'binance',
                    'api_url': 'https://api.binance.com/api/v3',
                    'ws_url': 'wss://stream.binance.com:9443/ws',
                    'symbols': ['ETHUSDT', 'BTCUSDT']
                }
            ]
        }
    }

@pytest.fixture
def mock_rpc_manager():
    """Mock du RPCManager."""
    manager = Mock(spec=RPCManager)
    manager.call_rpc = AsyncMock()
    return manager

@pytest.fixture
def mock_dex_feed():
    """Mock du DEXPriceFeed."""
    feed = Mock(spec=DEXPriceFeed)
    feed.start = AsyncMock()
    feed.stop = AsyncMock()
    feed.get_price = AsyncMock(return_value=Decimal('1000.0'))
    feed.get_liquidity = AsyncMock(return_value=Decimal('10000.0'))
    feed.validate_price = AsyncMock(return_value=True)
    return feed

@pytest.fixture
def mock_cex_feed():
    """Mock du CEXPriceFeed."""
    feed = Mock(spec=CEXPriceFeed)
    feed.start = AsyncMock()
    feed.stop = AsyncMock()
    feed.get_price = AsyncMock(return_value=Decimal('1010.0'))
    feed.get_liquidity = AsyncMock(return_value=Decimal('20000.0'))
    feed.validate_price = AsyncMock(return_value=True)
    return feed

@pytest.mark.asyncio
async def test_price_aggregator_integration(config, mock_dex_feed, mock_cex_feed):
    """Teste l'intégration entre les feeds de prix et l'agrégateur."""
    # Patch les classes pour utiliser nos mocks
    with patch('gbpbot.core.price_feed.aggregator.DEXPriceFeed', return_value=mock_dex_feed), \
         patch('gbpbot.core.price_feed.aggregator.CEXPriceFeed', return_value=mock_cex_feed):
        
        # Créer l'agrégateur
        aggregator = PriceAggregator(config)
        
        # Démarrer l'agrégateur
        await aggregator.start()
        
        # Vérifier que les feeds ont été démarrés
        mock_dex_feed.start.assert_called_once()
        mock_cex_feed.start.assert_called_once()
        
        # Récupérer un prix agrégé
        token = 'ETH-USDT'
        price_data = await aggregator.get_price(token)
        
        # Vérifier que les feeds ont été consultés
        mock_dex_feed.get_price.assert_called_with(token)
        mock_cex_feed.get_price.assert_called_with(token)
        
        # Vérifier que le prix est normalisé correctement
        assert price_data is not None
        assert 'price' in price_data
        assert 'sources' in price_data
        assert 'confidence' in price_data
        
        # Le prix devrait être entre les deux sources (pondéré par la liquidité)
        assert Decimal('1000.0') <= price_data['price'] <= Decimal('1010.0')
        
        # Vérifier la détection d'opportunités d'arbitrage
        opportunities = await aggregator.get_arbitrage_opportunities()
        assert len(opportunities) > 0
        
        # Vérifier que la première opportunité est correctement formatée
        opportunity = opportunities[0]
        assert 'token' in opportunity
        assert 'buy_venue' in opportunity
        assert 'sell_venue' in opportunity
        assert 'spread' in opportunity
        assert 'estimated_profit' in opportunity
        
        # Arrêter l'agrégateur
        await aggregator.stop()
        
        # Vérifier que les feeds ont été arrêtés
        mock_dex_feed.stop.assert_called_once()
        mock_cex_feed.stop.assert_called_once()

@pytest.mark.asyncio
async def test_price_normalizer_integration(config):
    """Teste l'intégration du normalisateur de prix."""
    normalizer = EnhancedPriceNormalizer(config['price_feed'])
    
    # Simuler des prix de différentes sources
    prices = [
        {'price': Decimal('1000.0'), 'source': 'dex', 'liquidity': Decimal('10000.0')},
        {'price': Decimal('1010.0'), 'source': 'cex', 'liquidity': Decimal('20000.0')},
        {'price': Decimal('1005.0'), 'source': 'cex2', 'liquidity': Decimal('15000.0')}
    ]
    
    # Normaliser les prix
    normalized_price = normalizer.normalize_price('ETH-USDT', prices)
    
    # Vérifier que le prix est normalisé correctement
    assert normalized_price is not None
    
    # Le prix devrait être une moyenne pondérée par la liquidité
    expected_price = (Decimal('1000.0') * Decimal('10000.0') + 
                      Decimal('1010.0') * Decimal('20000.0') + 
                      Decimal('1005.0') * Decimal('15000.0')) / (
                      Decimal('10000.0') + Decimal('20000.0') + Decimal('15000.0'))
    assert abs(normalized_price - expected_price) < Decimal('0.001')
    
    # Tester le filtrage des outliers
    prices_with_outlier = prices + [
        {'price': Decimal('1500.0'), 'source': 'bad_source', 'liquidity': Decimal('1000.0')}
    ]
    
    normalized_price_filtered = normalizer.normalize_price('ETH-USDT', prices_with_outlier)
    
    # Le prix ne devrait pas être affecté par l'outlier
    assert abs(normalized_price_filtered - expected_price) < Decimal('0.001')
    
    # Tester la volatilité
    for i in range(10):
        normalizer.normalize_price('ETH-USDT', [
            {'price': Decimal('1000.0') + Decimal(i), 'source': 'test', 'liquidity': Decimal('1000.0')}
        ])
    
    volatility = normalizer.get_price_volatility('ETH-USDT')
    assert volatility is not None
    assert volatility > 0

@pytest.mark.asyncio
async def test_price_feed_error_handling(config, mock_rpc_manager):
    """Teste la gestion des erreurs dans les feeds de prix."""
    # Simuler une erreur dans le feed DEX
    mock_rpc_manager.call_rpc.side_effect = Exception("RPC Error")
    
    # Créer un feed DEX réel avec le mock RPC
    dex_feed = DEXPriceFeed(config, mock_rpc_manager)
    
    # Démarrer le feed (ne devrait pas lever d'exception)
    try:
        await dex_feed.start()
    except Exception as e:
        pytest.fail(f"DEXPriceFeed.start() a levé une exception inattendue: {e}")
    
    # Tenter de récupérer un prix (devrait gérer l'erreur)
    price = await dex_feed.get_price('ETH-USDT')
    assert price is None
    
    # Arrêter le feed
    await dex_feed.stop() 