#!/usr/bin/env python3
"""
Tests d'intégration pour GBPBot.
"""

import pytest
import asyncio
from decimal import Decimal
from unittest.mock import Mock, patch, AsyncMock
from web3 import Web3

from gbpbot.core.gbpbot import GBPBot
from gbpbot.core.security.trade_protection import TradeProtection
from gbpbot.core.security.emergency_system import EmergencySystem
from gbpbot.core.monitoring.advanced_monitor import AdvancedMonitor

@pytest.fixture
def config():
    """Configuration complète pour les tests d'intégration."""
    return {
        'bot': {
            'wallet_address': '0x1234567890123456789012345678901234567890',
            'private_key': '0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890',
            'min_profit': '0.002'
        },
        'protection': {
            'stop_loss': '0.05',
            'take_profit': '0.03',
            'max_slippage': '0.01'
        },
        'emergency': {
            'max_loss': '0.10',
            'max_gas_gwei': '500',
            'min_balance_eth': '0.1',
            'safe_wallet_address': '0x9876543210987654321098765432109876543210'
        },
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
async def gbpbot(config):
    """Instance de GBPBot pour les tests."""
    with patch('web3.Web3'), \
         patch('gbpbot.core.rpc_manager.RPCManager'), \
         patch('gbpbot.core.monitoring.advanced_monitor.aiohttp.ClientSession'):
        bot = GBPBot(config)
        await bot.initialize()
        yield bot
        await bot.shutdown()

@pytest.mark.asyncio
async def test_full_arbitrage_cycle(gbpbot):
    """Teste un cycle complet d'arbitrage avec tous les composants."""
    # Mock des prix
    dex_price = Decimal('1000.0')
    cex_price = Decimal('1010.0')
    
    # Configuration des mocks
    gbpbot.price_manager.get_dex_price = AsyncMock(return_value=dex_price)
    gbpbot.price_manager.get_cex_price = AsyncMock(return_value=cex_price)
    gbpbot.trade_executor.execute_arbitrage = AsyncMock(return_value={'success': True, 'profit': Decimal('0.1')})
    
    # Exécuter l'arbitrage
    opportunity = await gbpbot._check_arbitrage_opportunity()
    assert opportunity is not None
    
    # Vérifier que la protection est active
    position_id = "test_position"
    await gbpbot.trade_protection.add_position(position_id, dex_price, Decimal('1.0'))
    
    # Vérifier le monitoring
    metrics = gbpbot.monitor.get_metrics_report()
    assert 'market' in metrics
    assert 'performance' in metrics

@pytest.mark.asyncio
async def test_emergency_scenario(gbpbot):
    """Teste un scénario d'urgence complet."""
    # Simuler une condition d'urgence (gas trop élevé)
    gbpbot.emergency_system._get_current_gas_price = AsyncMock(
        return_value=Web3.to_wei(600, 'gwei')
    )
    
    # Vérifier la détection
    is_emergency = await gbpbot.emergency_system.check_emergency_conditions()
    assert is_emergency
    
    # Vérifier l'arrêt d'urgence
    await gbpbot.emergency_system.emergency_shutdown()
    assert not gbpbot.is_running
    
    # Vérifier les notifications
    alerts = await gbpbot.monitor._check_alerts()
    assert any(alert['type'] == 'EMERGENCY_SHUTDOWN' for alert in alerts)

@pytest.mark.asyncio
async def test_protection_integration(gbpbot):
    """Teste l'intégration des mécanismes de protection."""
    # Configurer une position
    position_id = "test_position"
    entry_price = Decimal('1000.0')
    size = Decimal('1.0')
    
    # Ajouter la position
    await gbpbot.trade_protection.add_position(position_id, entry_price, size)
    
    # Simuler une baisse de prix
    new_price = entry_price * (1 - Decimal('0.06'))  # -6%, au-delà du stop-loss
    await gbpbot.trade_protection.update_position_price(position_id, new_price)
    
    # Vérifier le stop-loss
    update = await gbpbot.trade_protection.position_updates.get()
    assert update['action'] == 'stop_loss'
    
    # Vérifier le monitoring
    error = {
        'type': 'STOP_LOSS_TRIGGERED',
        'position_id': position_id,
        'loss_percentage': '6.00%'
    }
    await gbpbot.monitor.log_error(error)
    
    metrics = gbpbot.monitor.get_metrics_report()
    assert metrics['system']['error_count'] > 0

@pytest.mark.asyncio
async def test_monitoring_integration(gbpbot):
    """Teste l'intégration du système de monitoring."""
    # Simuler des trades
    trades = [
        {
            'timestamp': datetime.now(),
            'type': 'BUY',
            'amount': Decimal('1.0'),
            'price': Decimal('1000.0'),
            'profit': Decimal('0.1'),
            'gas_used': 100000
        },
        {
            'timestamp': datetime.now(),
            'type': 'SELL',
            'amount': Decimal('1.0'),
            'price': Decimal('1010.0'),
            'profit': Decimal('0.05'),
            'gas_used': 120000
        }
    ]
    
    for trade in trades:
        await gbpbot.monitor.log_trade(trade)
    
    # Vérifier les métriques
    metrics = gbpbot.monitor.get_metrics_report()
    assert metrics['performance']['trade_count'] == 2
    assert metrics['performance']['total_profit'] > 0
    
    # Vérifier les alertes
    await gbpbot.monitor.update_market_metrics({
        'gas_price': 600,  # Déclencher une alerte de gas élevé
        'liquidity': Decimal('500.0')  # Déclencher une alerte de liquidité faible
    })
    
    alerts = await gbpbot.monitor._check_alerts()
    assert len(alerts) >= 2

@pytest.mark.asyncio
async def test_error_scenarios(gbpbot):
    """Teste différents scénarios d'erreur."""
    # 1. Erreur RPC
    with patch.object(gbpbot.rpc_manager, 'get_gas_price', side_effect=Exception("RPC Error")):
        is_emergency = await gbpbot.emergency_system.check_emergency_conditions()
        assert is_emergency  # Le système devrait passer en mode urgence
    
    # 2. Erreur d'exécution de trade
    gbpbot.trade_executor.execute_arbitrage = AsyncMock(side_effect=Exception("Execution Error"))
    opportunity = {
        'dex_price': Decimal('1000.0'),
        'cex_price': Decimal('1010.0'),
        'profit': Decimal('0.01')
    }
    
    await gbpbot._execute_arbitrage(opportunity)
    metrics = gbpbot.monitor.get_metrics_report()
    assert metrics['system']['error_count'] > 0
    
    # 3. Erreur de protection
    with pytest.raises(Exception):
        await gbpbot.trade_protection.add_position("test", Decimal('-1'), Decimal('0'))
    
    # 4. Erreur de notification
    gbpbot.monitor._send_discord_notification = AsyncMock(side_effect=Exception("Discord Error"))
    alert = {
        'type': 'TEST_ALERT',
        'message': 'Test notification',
        'severity': 'HIGH'
    }
    await gbpbot.monitor._send_notification(alert)  # Ne devrait pas lever d'exception

@pytest.mark.asyncio
async def test_performance_metrics(gbpbot):
    """Teste les métriques de performance détaillées."""
    # Simuler une série de trades
    trades = []
    base_price = Decimal('1000.0')
    
    for i in range(10):
        profit = Decimal('0.1') if i % 2 == 0 else Decimal('-0.05')
        trade = {
            'timestamp': datetime.now(),
            'type': 'BUY' if i % 2 == 0 else 'SELL',
            'amount': Decimal('1.0'),
            'price': base_price * (1 + Decimal(str(i)) / Decimal('100')),
            'profit': profit,
            'gas_used': 100000 + i * 1000
        }
        trades.append(trade)
        await gbpbot.monitor.log_trade(trade)
    
    # Mettre à jour les métriques de performance
    await gbpbot.monitor.update_performance_metrics({
        'total_profit': sum(t['profit'] for t in trades),
        'trade_count': len(trades),
        'success_rate': Decimal('0.5'),
        'avg_execution_time': 2.5,
        'avg_gas_used': sum(t['gas_used'] for t in trades) / len(trades),
        'profit_factor': abs(sum(t['profit'] for t in trades if t['profit'] > 0)) / 
                        abs(sum(t['profit'] for t in trades if t['profit'] < 0))
    })
    
    # Vérifier les métriques détaillées
    report = gbpbot.monitor.get_metrics_report()
    performance = report['performance']
    
    assert 'total_profit' in performance
    assert 'trade_count' in performance
    assert 'success_rate' in performance
    assert 'avg_execution_time' in performance
    assert 'avg_gas_used' in performance
    assert 'profit_factor' in performance 