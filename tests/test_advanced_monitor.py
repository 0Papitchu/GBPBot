#!/usr/bin/env python3
"""
Tests unitaires pour le système de monitoring avancé.
"""

import pytest
import asyncio
from decimal import Decimal
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta

from gbpbot.core.monitoring.advanced_monitor import AdvancedMonitor

@pytest.fixture
def config():
    """Configuration de test."""
    return {
        'monitoring': {
            'alert_thresholds': {
                'min_profit': '0.001',
                'max_gas_gwei': '500',
                'max_slippage': '0.02',
                'max_error_rate': '0.1',
                'min_liquidity': '1000'
            },
            'notification': {
                'discord_webhook': 'https://discord.webhook/test',
                'telegram_token': 'test_token',
                'telegram_chat_id': '123456789'
            },
            'metrics_interval': 60,
            'alert_cooldown': 300
        }
    }

@pytest.fixture
async def monitor(config):
    """Instance de AdvancedMonitor pour les tests."""
    with patch('gbpbot.core.monitoring.advanced_monitor.aiohttp.ClientSession'):
        monitor = AdvancedMonitor(config)
        yield monitor
        await monitor.stop()

@pytest.mark.asyncio
async def test_init(monitor):
    """Teste l'initialisation."""
    assert monitor.min_profit == Decimal('0.001')
    assert monitor.max_gas_gwei == 500
    assert monitor.max_slippage == Decimal('0.02')
    assert monitor.max_error_rate == Decimal('0.1')
    assert monitor.min_liquidity == Decimal('1000')
    assert not monitor.is_running
    assert isinstance(monitor.metrics, dict)
    assert isinstance(monitor.trades, list)
    assert isinstance(monitor.errors, list)

@pytest.mark.asyncio
async def test_start_stop(monitor):
    """Teste le démarrage et l'arrêt du monitoring."""
    await monitor.start()
    assert monitor.is_running
    assert monitor._update_task is not None
    
    await monitor.stop()
    assert not monitor.is_running
    assert monitor._update_task is None

@pytest.mark.asyncio
async def test_update_market_metrics(monitor):
    """Teste la mise à jour des métriques de marché."""
    metrics = {
        'price': Decimal('1000.0'),
        'spread': Decimal('0.001'),
        'liquidity': Decimal('5000.0'),
        'gas_price': 100
    }
    
    await monitor.update_market_metrics(metrics)
    
    assert monitor.metrics['market']['price'] == metrics['price']
    assert monitor.metrics['market']['spread'] == metrics['spread']
    assert monitor.metrics['market']['liquidity'] == metrics['liquidity']
    assert monitor.metrics['market']['gas_price'] == metrics['gas_price']

@pytest.mark.asyncio
async def test_update_performance_metrics(monitor):
    """Teste la mise à jour des métriques de performance."""
    metrics = {
        'total_profit': Decimal('0.5'),
        'trade_count': 10,
        'success_rate': Decimal('0.8'),
        'avg_execution_time': 2.5
    }
    
    await monitor.update_performance_metrics(metrics)
    
    assert monitor.metrics['performance']['total_profit'] == metrics['total_profit']
    assert monitor.metrics['performance']['trade_count'] == metrics['trade_count']
    assert monitor.metrics['performance']['success_rate'] == metrics['success_rate']
    assert monitor.metrics['performance']['avg_execution_time'] == metrics['avg_execution_time']

@pytest.mark.asyncio
async def test_log_trade(monitor):
    """Teste l'enregistrement d'un trade."""
    trade = {
        'timestamp': datetime.now(),
        'type': 'BUY',
        'amount': Decimal('1.0'),
        'price': Decimal('1000.0'),
        'profit': Decimal('0.1'),
        'gas_used': 100000
    }
    
    await monitor.log_trade(trade)
    
    assert len(monitor.trades) == 1
    assert monitor.trades[0] == trade
    assert monitor.metrics['performance']['last_trade'] == trade

@pytest.mark.asyncio
async def test_log_error(monitor):
    """Teste l'enregistrement d'une erreur."""
    error = {
        'timestamp': datetime.now(),
        'type': 'EXECUTION_FAILED',
        'message': 'Test error',
        'severity': 'HIGH'
    }
    
    await monitor.log_error(error)
    
    assert len(monitor.errors) == 1
    assert monitor.errors[0] == error
    assert monitor.metrics['system']['error_count'] > 0

@pytest.mark.asyncio
async def test_check_alerts_low_profit(monitor):
    """Teste la détection d'alerte de profit faible."""
    # Configurer des métriques avec profit faible
    await monitor.update_performance_metrics({
        'total_profit': Decimal('0.0005'),
        'trade_count': 10
    })
    
    alerts = await monitor._check_alerts()
    
    assert any(alert['type'] == 'LOW_PROFIT' for alert in alerts)

@pytest.mark.asyncio
async def test_check_alerts_high_gas(monitor):
    """Teste la détection d'alerte de gas élevé."""
    # Configurer des métriques avec gas élevé
    await monitor.update_market_metrics({
        'gas_price': 600
    })
    
    alerts = await monitor._check_alerts()
    
    assert any(alert['type'] == 'HIGH_GAS' for alert in alerts)

@pytest.mark.asyncio
async def test_check_alerts_low_liquidity(monitor):
    """Teste la détection d'alerte de liquidité faible."""
    # Configurer des métriques avec liquidité faible
    await monitor.update_market_metrics({
        'liquidity': Decimal('500.0')
    })
    
    alerts = await monitor._check_alerts()
    
    assert any(alert['type'] == 'LOW_LIQUIDITY' for alert in alerts)

@pytest.mark.asyncio
async def test_check_alerts_high_error_rate(monitor):
    """Teste la détection d'alerte de taux d'erreur élevé."""
    # Simuler plusieurs erreurs
    for _ in range(5):
        await monitor.log_error({
            'timestamp': datetime.now(),
            'type': 'TEST_ERROR',
            'message': 'Test error',
            'severity': 'HIGH'
        })
    
    alerts = await monitor._check_alerts()
    
    assert any(alert['type'] == 'HIGH_ERROR_RATE' for alert in alerts)

@pytest.mark.asyncio
async def test_send_notification(monitor):
    """Teste l'envoi de notifications."""
    # Mock des fonctions d'envoi
    monitor._send_discord_notification = AsyncMock()
    monitor._send_telegram_notification = AsyncMock()
    
    alert = {
        'type': 'TEST_ALERT',
        'message': 'Test notification',
        'severity': 'HIGH'
    }
    
    await monitor._send_notification(alert)
    
    assert monitor._send_discord_notification.called
    assert monitor._send_telegram_notification.called

@pytest.mark.asyncio
async def test_get_metrics_report(monitor):
    """Teste la génération du rapport de métriques."""
    # Configurer quelques métriques
    await monitor.update_market_metrics({
        'price': Decimal('1000.0'),
        'spread': Decimal('0.001'),
        'liquidity': Decimal('5000.0'),
        'gas_price': 100
    })
    
    await monitor.update_performance_metrics({
        'total_profit': Decimal('0.5'),
        'trade_count': 10,
        'success_rate': Decimal('0.8'),
        'avg_execution_time': 2.5
    })
    
    report = monitor.get_metrics_report()
    
    assert isinstance(report, dict)
    assert 'market' in report
    assert 'performance' in report
    assert 'system' in report

@pytest.mark.asyncio
async def test_alert_cooldown(monitor):
    """Teste le cooldown des alertes."""
    # Configurer une alerte
    alert_type = 'TEST_ALERT'
    monitor._last_alerts[alert_type] = datetime.now()
    
    # Vérifier que l'alerte est en cooldown
    assert monitor._is_alert_in_cooldown(alert_type)
    
    # Avancer le temps
    monitor._last_alerts[alert_type] = datetime.now() - timedelta(seconds=600)
    
    # Vérifier que l'alerte n'est plus en cooldown
    assert not monitor._is_alert_in_cooldown(alert_type)

@pytest.mark.asyncio
async def test_cleanup_old_data(monitor):
    """Teste le nettoyage des anciennes données."""
    # Ajouter des anciennes données
    old_time = datetime.now() - timedelta(days=2)
    
    monitor.trades.append({
        'timestamp': old_time,
        'type': 'TEST',
        'amount': Decimal('1.0')
    })
    
    monitor.errors.append({
        'timestamp': old_time,
        'type': 'TEST',
        'message': 'Old error'
    })
    
    # Exécuter le nettoyage
    await monitor._cleanup_old_data()
    
    assert len(monitor.trades) == 0
    assert len(monitor.errors) == 0 