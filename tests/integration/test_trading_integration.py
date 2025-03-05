#!/usr/bin/env python3
"""
Tests d'intégration pour le système de trading.
Valide l'interaction entre TradeExecutor, EmergencySystem et GasManager.
"""

import pytest
import asyncio
from decimal import Decimal
from unittest.mock import Mock, AsyncMock, patch
from web3 import Web3

from gbpbot.core.trading.trade_executor import TradeExecutor
from gbpbot.core.trading.trade_protection import TradeProtection
from gbpbot.core.emergency.emergency_system import EmergencySystem
from gbpbot.core.gas.gas_manager import GasManager
from gbpbot.core.monitoring.advanced_monitor import AdvancedMonitor

@pytest.fixture
def config():
    """Configuration de test."""
    return {
        'trading': {
            'max_slippage': 0.01,
            'min_profit': 0.005,
            'max_gas_price_gwei': '300',
            'confirmation_timeout': 60,
            'max_pending_transactions': 3,
            'emergency_shutdown_threshold': 0.05
        },
        'wallet': {
            'private_key': '0x0000000000000000000000000000000000000000000000000000000000000001',
            'address': '0x1234567890123456789012345678901234567890',
            'min_balance_eth': '0.1'
        },
        'gas': {
            'max_base_fee_gwei': '500',
            'max_priority_fee_gwei': '50',
            'min_priority_fee_gwei': '1',
            'base_fee_multiplier': '1.125',
            'priority_fee_multiplier': '1.1',
            'max_total_fee_gwei': '1000',
            'update_interval': 15,
            'history_size': 20
        },
        'security': {
            'max_price_change': 0.02,
            'min_liquidity': 1000,
            'max_gas_price_gwei': 500,
            'min_confirmations': 2,
            'max_confirmation_attempts': 5
        },
        'monitoring': {
            'update_interval': 5,
            'alert_thresholds': {
                'low_balance': 0.05,
                'high_gas': 300,
                'low_profit': 0.001,
                'price_deviation': 0.05,
                'error_rate': 0.2
            }
        }
    }

@pytest.fixture
def mock_web3():
    """Mock de Web3."""
    mock = Mock(spec=Web3)
    mock.eth = Mock()
    mock.eth.get_transaction_count = AsyncMock(return_value=10)
    mock.eth.get_block = AsyncMock(return_value={'baseFeePerGas': 50000000000})
    mock.eth.max_priority_fee = AsyncMock(return_value=2000000000)
    mock.eth.wait_for_transaction_receipt = AsyncMock(return_value={'status': 1})
    mock.eth.get_transaction = AsyncMock(return_value={'blockNumber': 1000})
    mock.eth.chain_id = 1
    mock.to_wei = Web3.to_wei
    mock.from_wei = Web3.from_wei
    return mock

@pytest.fixture
def mock_monitor():
    """Mock du moniteur."""
    monitor = Mock(spec=AdvancedMonitor)
    monitor.log_trade = AsyncMock()
    monitor.log_error = AsyncMock()
    monitor.update_metric = AsyncMock()
    monitor.check_alerts = AsyncMock(return_value=[])
    return monitor

@pytest.fixture
def mock_gas_manager():
    """Mock du GasManager."""
    manager = Mock(spec=GasManager)
    manager.start = AsyncMock()
    manager.stop = AsyncMock()
    manager.get_gas_params = AsyncMock(return_value={
        'maxFeePerGas': Web3.to_wei(100, 'gwei'),
        'maxPriorityFeePerGas': Web3.to_wei(2, 'gwei')
    })
    manager.estimate_gas_cost = AsyncMock(return_value=Web3.to_wei(0.01, 'ether'))
    manager.record_transaction_result = Mock()
    return manager

@pytest.fixture
def mock_emergency_system():
    """Mock du système d'urgence."""
    system = Mock(spec=EmergencySystem)
    system.start = AsyncMock()
    system.stop = AsyncMock()
    system.check_emergency_conditions = AsyncMock(return_value=(False, None))
    system.handle_emergency = AsyncMock()
    system.is_emergency_mode = False
    return system

@pytest.fixture
def mock_trade_protection():
    """Mock de la protection des trades."""
    protection = Mock(spec=TradeProtection)
    protection.start = AsyncMock()
    protection.stop = AsyncMock()
    protection.check_mev_protection = AsyncMock(return_value=True)
    protection.add_position = AsyncMock()
    protection.update_position = AsyncMock()
    protection.remove_position = AsyncMock()
    protection.get_position_status = AsyncMock(return_value={
        'token': 'ETH-USDT',
        'entry_price': Decimal('1000.0'),
        'current_price': Decimal('1050.0'),
        'quantity': Decimal('1.0'),
        'profit_loss': Decimal('50.0'),
        'profit_loss_percent': Decimal('0.05')
    })
    return protection

@pytest.fixture
async def trade_executor(config, mock_web3, mock_monitor, mock_gas_manager, mock_emergency_system, mock_trade_protection):
    """Instance de TradeExecutor pour les tests."""
    executor = TradeExecutor(config, mock_web3, mock_monitor)
    executor.gas_manager = mock_gas_manager
    executor.emergency_system = mock_emergency_system
    executor.trade_protection = mock_trade_protection
    await executor.start()
    yield executor
    await executor.stop()

@pytest.mark.asyncio
async def test_trade_executor_integration(trade_executor, mock_web3, mock_gas_manager, mock_emergency_system, mock_trade_protection):
    """Teste l'intégration entre TradeExecutor, GasManager et EmergencySystem."""
    # Créer une opportunité d'arbitrage
    opportunity = {
        'token': 'ETH-USDT',
        'buy_venue': 'dex',
        'sell_venue': 'cex',
        'buy_price': Decimal('1000.0'),
        'sell_price': Decimal('1050.0'),
        'spread': Decimal('0.05'),
        'max_volume': Decimal('1.0'),
        'estimated_profit': Decimal('50.0')
    }
    
    # Exécuter l'arbitrage
    result = await trade_executor.execute_arbitrage(opportunity)
    
    # Vérifier que l'exécution a réussi
    assert result is True
    
    # Vérifier que le GasManager a été utilisé
    mock_gas_manager.get_gas_params.assert_called_once()
    mock_gas_manager.estimate_gas_cost.assert_called_once()
    mock_gas_manager.record_transaction_result.assert_called_once()
    
    # Vérifier que le système d'urgence a été consulté
    mock_emergency_system.check_emergency_conditions.assert_called_once()
    
    # Vérifier que la protection des trades a été utilisée
    mock_trade_protection.check_mev_protection.assert_called_once()
    mock_trade_protection.add_position.assert_called_once()
    mock_trade_protection.update_position.assert_called_once()

@pytest.mark.asyncio
async def test_emergency_conditions_integration(trade_executor, mock_emergency_system):
    """Teste l'intégration avec le système d'urgence en cas de conditions critiques."""
    # Simuler une condition d'urgence
    mock_emergency_system.check_emergency_conditions.return_value = (True, "Prix anormal détecté")
    
    # Créer une opportunité d'arbitrage
    opportunity = {
        'token': 'ETH-USDT',
        'buy_venue': 'dex',
        'sell_venue': 'cex',
        'buy_price': Decimal('1000.0'),
        'sell_price': Decimal('1050.0'),
        'spread': Decimal('0.05'),
        'max_volume': Decimal('1.0'),
        'estimated_profit': Decimal('50.0')
    }
    
    # Exécuter l'arbitrage (devrait échouer à cause de la condition d'urgence)
    result = await trade_executor.execute_arbitrage(opportunity)
    
    # Vérifier que l'exécution a échoué
    assert result is False
    
    # Vérifier que le système d'urgence a été consulté
    mock_emergency_system.check_emergency_conditions.assert_called_once()
    
    # Vérifier que le gestionnaire d'urgence a été appelé
    mock_emergency_system.handle_emergency.assert_called_once()

@pytest.mark.asyncio
async def test_gas_price_too_high_integration(trade_executor, mock_gas_manager):
    """Teste l'intégration avec le GasManager en cas de prix du gas trop élevé."""
    # Simuler un prix du gas trop élevé
    mock_gas_manager.get_gas_params.return_value = {
        'maxFeePerGas': Web3.to_wei(600, 'gwei'),  # Au-dessus du seuil configuré
        'maxPriorityFeePerGas': Web3.to_wei(60, 'gwei')
    }
    
    # Créer une opportunité d'arbitrage
    opportunity = {
        'token': 'ETH-USDT',
        'buy_venue': 'dex',
        'sell_venue': 'cex',
        'buy_price': Decimal('1000.0'),
        'sell_price': Decimal('1050.0'),
        'spread': Decimal('0.05'),
        'max_volume': Decimal('1.0'),
        'estimated_profit': Decimal('50.0')
    }
    
    # Exécuter l'arbitrage (devrait échouer à cause du prix du gas trop élevé)
    result = await trade_executor.execute_arbitrage(opportunity)
    
    # Vérifier que l'exécution a échoué
    assert result is False
    
    # Vérifier que le GasManager a été consulté
    mock_gas_manager.get_gas_params.assert_called_once()

@pytest.mark.asyncio
async def test_trade_protection_integration(trade_executor, mock_trade_protection):
    """Teste l'intégration avec la protection des trades."""
    # Simuler une détection de MEV
    mock_trade_protection.check_mev_protection.return_value = False
    
    # Créer une opportunité d'arbitrage
    opportunity = {
        'token': 'ETH-USDT',
        'buy_venue': 'dex',
        'sell_venue': 'cex',
        'buy_price': Decimal('1000.0'),
        'sell_price': Decimal('1050.0'),
        'spread': Decimal('0.05'),
        'max_volume': Decimal('1.0'),
        'estimated_profit': Decimal('50.0')
    }
    
    # Exécuter l'arbitrage (devrait échouer à cause de la protection MEV)
    result = await trade_executor.execute_arbitrage(opportunity)
    
    # Vérifier que l'exécution a échoué
    assert result is False
    
    # Vérifier que la protection des trades a été consultée
    mock_trade_protection.check_mev_protection.assert_called_once() 