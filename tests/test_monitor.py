#!/usr/bin/env python3
"""
Tests unitaires pour le module de monitoring.
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from decimal import Decimal
from datetime import datetime

from gbpbot.core.monitoring.monitor import BotMonitor

@pytest.fixture
def mock_config():
    """Fixture pour simuler la configuration."""
    return {
        'monitoring': {
            'metrics_port': 9090,
            'discord_webhook': 'https://discord.webhook/test',
            'telegram_token': 'test_token',
            'telegram_chat_id': '123456',
            'alert_threshold': {
                'profit': 0.5,
                'gas': 100,
                'error_rate': 0.05
            }
        },
        'security': {
            'emergency_shutdown': {
                'max_consecutive_errors': 3
            }
        }
    }

@pytest.fixture
def monitor(mock_config):
    """Fixture pour créer une instance de BotMonitor."""
    with patch('gbpbot.core.monitoring.monitor.start_http_server'):
        monitor = BotMonitor(mock_config)
        return monitor

@pytest.mark.asyncio
async def test_track_trade_success(monitor):
    """Teste le tracking d'un trade réussi."""
    trade_info = {
        'status': 'success',
        'exchange': 'binance',
        'profit': '1.5',
        'gas_price': '50'
    }
    
    with patch.object(monitor, '_send_alerts'):
        await monitor.track_trade(trade_info)
        
        assert monitor.performance['trades_count'] == 1
        assert monitor.performance['successful_trades'] == 1
        assert monitor.performance['total_profit_loss'] == Decimal('1.5')
        assert len(monitor.events) == 1
        assert monitor.events[0]['type'] == 'trade'

@pytest.mark.asyncio
async def test_track_trade_failure(monitor):
    """Teste le tracking d'un trade échoué."""
    trade_info = {
        'status': 'failed',
        'exchange': 'binance',
        'error': 'Insufficient funds'
    }
    
    await monitor.track_trade(trade_info)
    
    assert monitor.performance['trades_count'] == 1
    assert monitor.performance['successful_trades'] == 0
    assert monitor.performance['total_profit_loss'] == Decimal('0')

@pytest.mark.asyncio
async def test_track_error(monitor):
    """Teste le tracking des erreurs."""
    error_info = {
        'type': 'rpc_error',
        'message': 'Connection failed'
    }
    
    with patch.object(monitor, '_send_alerts'), \
         patch.object(monitor, '_trigger_emergency_shutdown'):
        await monitor.track_error(error_info)
        
        assert monitor.bot_status['consecutive_errors'] == 1
        assert monitor.bot_status['last_error'] == error_info
        assert len(monitor.events) == 1
        assert monitor.events[0]['type'] == 'error'

@pytest.mark.asyncio
async def test_emergency_shutdown_trigger(monitor):
    """Teste le déclenchement de l'arrêt d'urgence."""
    error_info = {
        'type': 'critical_error',
        'message': 'Fatal error'
    }
    
    with patch.object(monitor, '_send_alerts') as mock_send_alerts:
        # Simuler 3 erreurs consécutives
        for _ in range(3):
            await monitor.track_error(error_info)
        
        assert not monitor.bot_status['is_running']
        mock_send_alerts.assert_called()

@pytest.mark.asyncio
async def test_update_market_metrics(monitor):
    """Teste la mise à jour des métriques de marché."""
    market_info = {
        'spread': 1.5,
        'gas_price': 50,
        'wallet_balance': 1.0
    }
    
    await monitor.update_market_metrics(market_info)
    
    # Vérifier que les métriques ont été mises à jour
    assert monitor.gas_price_gauge._value.get() == 50
    assert monitor.balance_gauge._value.get() == 1.0

@pytest.mark.asyncio
async def test_alert_triggers(monitor):
    """Teste le déclenchement des alertes."""
    trade_info = {
        'status': 'success',
        'profit': '0.1',  # En dessous du seuil de 0.5
        'gas_price': '150'  # Au-dessus du seuil de 100
    }
    
    with patch.object(monitor, '_send_discord_alert') as mock_discord, \
         patch.object(monitor, '_send_telegram_alert') as mock_telegram:
        await monitor.track_trade(trade_info)
        
        mock_discord.assert_called()
        mock_telegram.assert_called()

@pytest.mark.asyncio
async def test_status_report(monitor):
    """Teste la génération du rapport d'état."""
    # Simuler quelques événements
    trade_info = {
        'status': 'success',
        'exchange': 'binance',
        'profit': '1.5'
    }
    await monitor.track_trade(trade_info)
    
    report = monitor.get_status_report()
    
    assert 'status' in report
    assert 'performance' in report
    assert 'uptime' in report
    assert 'recent_events' in report
    assert len(report['recent_events']) == 1

@pytest.mark.asyncio
async def test_discord_alert(monitor):
    """Teste l'envoi d'alertes Discord."""
    with patch('aiohttp.ClientSession.post') as mock_post:
        mock_post.return_value.__aenter__.return_value.status = 200
        
        await monitor._send_discord_alert("Test alert")
        
        mock_post.assert_called_with(
            monitor.discord_webhook,
            json={'content': "Test alert"}
        )

@pytest.mark.asyncio
async def test_telegram_alert(monitor):
    """Teste l'envoi d'alertes Telegram."""
    with patch('aiohttp.ClientSession.post') as mock_post:
        mock_post.return_value.__aenter__.return_value.status = 200
        
        await monitor._send_telegram_alert("Test alert")
        
        mock_post.assert_called_with(
            f"https://api.telegram.org/bot{monitor.telegram_token}/sendMessage",
            json={
                'chat_id': monitor.telegram_chat_id,
                'text': "Test alert"
            }
        ) 