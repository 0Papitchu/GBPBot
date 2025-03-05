#!/usr/bin/env python3
"""
Tests unitaires pour le gestionnaire de gas fees EIP-1559.
"""

import pytest
import asyncio
from decimal import Decimal
from unittest.mock import Mock, patch, AsyncMock
from web3 import Web3
from datetime import datetime, timedelta

from gbpbot.core.gas.gas_manager import GasManager, GasConfig

@pytest.fixture
def config():
    """Configuration de test."""
    return {
        'gas': {
            'max_base_fee_gwei': '500',
            'max_priority_fee_gwei': '50',
            'min_priority_fee_gwei': '1',
            'base_fee_multiplier': '1.125',
            'priority_fee_multiplier': '1.1',
            'max_total_fee_gwei': '1000',
            'update_interval': 15,
            'history_size': 20
        }
    }

@pytest.fixture
def web3():
    """Mock de Web3."""
    mock_web3 = Mock(spec=Web3)
    mock_web3.to_wei = Web3.to_wei
    return mock_web3

@pytest.fixture
async def gas_manager(config, web3):
    """Instance de GasManager pour les tests."""
    manager = GasManager(config, web3)
    yield manager
    await manager.stop()

@pytest.mark.asyncio
async def test_init(gas_manager):
    """Teste l'initialisation."""
    assert isinstance(gas_manager.config, GasConfig)
    assert gas_manager.config.max_base_fee == Web3.to_wei(500, 'gwei')
    assert gas_manager.config.max_priority_fee == Web3.to_wei(50, 'gwei')
    assert gas_manager.config.min_priority_fee == Web3.to_wei(1, 'gwei')
    assert gas_manager.config.base_fee_multiplier == 1.125
    assert gas_manager.config.priority_fee_multiplier == 1.1
    assert gas_manager.config.max_total_fee == Web3.to_wei(1000, 'gwei')
    assert gas_manager.config.update_interval == 15
    assert gas_manager.config.history_size == 20

@pytest.mark.asyncio
async def test_start_stop(gas_manager):
    """Teste le démarrage et l'arrêt du monitoring."""
    await gas_manager.start()
    assert gas_manager.is_running
    assert gas_manager._update_task is not None
    
    await gas_manager.stop()
    assert not gas_manager.is_running
    assert gas_manager._update_task is None

@pytest.mark.asyncio
async def test_get_gas_params_low_priority(gas_manager):
    """Teste l'obtention des paramètres de gas en priorité basse."""
    # Mock de l'historique
    gas_manager.base_fee_history = [Web3.to_wei(50, 'gwei')] * 10
    gas_manager.priority_fee_history = [Web3.to_wei(2, 'gwei')] * 10
    
    params = await gas_manager.get_gas_params('low')
    
    assert params['maxFeePerGas'] == Web3.to_wei(50, 'gwei')
    assert params['maxPriorityFeePerGas'] == Web3.to_wei(2, 'gwei')

@pytest.mark.asyncio
async def test_get_gas_params_high_priority(gas_manager):
    """Teste l'obtention des paramètres de gas en priorité haute."""
    # Mock de l'historique
    gas_manager.base_fee_history = [Web3.to_wei(50, 'gwei')] * 10
    gas_manager.priority_fee_history = [Web3.to_wei(2, 'gwei')] * 10
    
    params = await gas_manager.get_gas_params('high')
    
    assert params['maxFeePerGas'] > Web3.to_wei(50, 'gwei')
    assert params['maxPriorityFeePerGas'] > Web3.to_wei(2, 'gwei')

@pytest.mark.asyncio
async def test_get_gas_params_max_total_fee(gas_manager):
    """Teste la limitation du total des gas fees."""
    # Mock de l'historique avec des valeurs élevées
    gas_manager.base_fee_history = [Web3.to_wei(800, 'gwei')] * 10
    gas_manager.priority_fee_history = [Web3.to_wei(300, 'gwei')] * 10
    
    params = await gas_manager.get_gas_params('high')
    
    total_fee = params['maxFeePerGas'] + params['maxPriorityFeePerGas']
    assert total_fee <= gas_manager.config.max_total_fee

@pytest.mark.asyncio
async def test_estimate_gas_cost(gas_manager):
    """Teste l'estimation du coût en gas."""
    # Mock des paramètres de gas
    gas_manager.get_gas_params = AsyncMock(return_value={
        'maxFeePerGas': Web3.to_wei(100, 'gwei'),
        'maxPriorityFeePerGas': Web3.to_wei(2, 'gwei')
    })
    
    gas_limit = 21000  # Gas limit standard pour un transfert ETH
    estimated_cost = await gas_manager.estimate_gas_cost(gas_limit)
    
    assert estimated_cost == gas_limit * Web3.to_wei(100, 'gwei')

@pytest.mark.asyncio
async def test_update_gas_history(gas_manager):
    """Teste la mise à jour de l'historique des gas fees."""
    # Mock des blocks récents
    blocks = []
    for i in range(gas_manager.config.history_size):
        blocks.append({
            'baseFeePerGas': Web3.to_wei(50 + i, 'gwei'),
            'transactions': [
                {'maxPriorityFeePerGas': Web3.to_wei(2, 'gwei')},
                {'maxPriorityFeePerGas': Web3.to_wei(3, 'gwei')}
            ]
        })
    
    gas_manager.web3.eth.block_number = AsyncMock(return_value=1000)
    gas_manager.web3.eth.get_block = AsyncMock(side_effect=blocks)
    
    await gas_manager._update_gas_history()
    
    assert len(gas_manager.base_fee_history) == gas_manager.config.history_size
    assert len(gas_manager.priority_fee_history) > 0
    assert gas_manager.stats['avg_base_fee'] > 0
    assert gas_manager.stats['avg_priority_fee'] > 0

def test_record_transaction_result(gas_manager):
    """Teste l'enregistrement des résultats de transaction."""
    # Enregistrer quelques transactions
    gas_manager.record_transaction_result(True, 21000, 
                                        Web3.to_wei(50, 'gwei'),
                                        Web3.to_wei(2, 'gwei'))
    gas_manager.record_transaction_result(True, 21000,
                                        Web3.to_wei(55, 'gwei'),
                                        Web3.to_wei(2, 'gwei'))
    gas_manager.record_transaction_result(False, 21000,
                                        Web3.to_wei(60, 'gwei'),
                                        Web3.to_wei(2, 'gwei'))
    
    assert gas_manager.stats['total_transactions'] == 3
    assert gas_manager.stats['failed_transactions'] == 1
    assert gas_manager.stats['success_rate'] == 2/3

@pytest.mark.asyncio
async def test_get_optimal_base_fee(gas_manager):
    """Teste le calcul du base fee optimal."""
    # Configurer l'historique
    gas_manager.base_fee_history = [
        Web3.to_wei(40, 'gwei'),
        Web3.to_wei(50, 'gwei'),
        Web3.to_wei(60, 'gwei')
    ]
    
    # Test avec différents multiplicateurs
    base_fee_1 = await gas_manager._get_optimal_base_fee(1.0)
    base_fee_2 = await gas_manager._get_optimal_base_fee(1.5)
    
    assert base_fee_1 < base_fee_2
    assert base_fee_2 <= gas_manager.config.max_base_fee

@pytest.mark.asyncio
async def test_get_optimal_priority_fee(gas_manager):
    """Teste le calcul du priority fee optimal."""
    # Configurer l'historique
    gas_manager.priority_fee_history = [
        Web3.to_wei(1, 'gwei'),
        Web3.to_wei(2, 'gwei'),
        Web3.to_wei(3, 'gwei'),
        Web3.to_wei(4, 'gwei')
    ]
    
    # Test avec différents multiplicateurs
    priority_fee_1 = await gas_manager._get_optimal_priority_fee(1.0)
    priority_fee_2 = await gas_manager._get_optimal_priority_fee(1.5)
    
    assert priority_fee_1 < priority_fee_2
    assert gas_manager.config.min_priority_fee <= priority_fee_1 <= gas_manager.config.max_priority_fee
    assert gas_manager.config.min_priority_fee <= priority_fee_2 <= gas_manager.config.max_priority_fee

def test_get_stats(gas_manager):
    """Teste la récupération des statistiques."""
    # Configurer quelques données
    gas_manager.base_fee_history = [Web3.to_wei(50, 'gwei')]
    gas_manager.priority_fee_history = [Web3.to_wei(2, 'gwei')]
    gas_manager.stats.update({
        'avg_base_fee': Web3.to_wei(45, 'gwei'),
        'avg_priority_fee': Web3.to_wei(2, 'gwei'),
        'min_base_fee': Web3.to_wei(40, 'gwei'),
        'max_base_fee': Web3.to_wei(60, 'gwei'),
        'success_rate': 0.9,
        'total_transactions': 10,
        'failed_transactions': 1
    })
    
    stats = gas_manager.get_stats()
    
    assert 'current' in stats
    assert 'averages' in stats
    assert 'ranges' in stats
    assert 'performance' in stats
    assert stats['performance']['success_rate'] == 0.9
    assert stats['performance']['total_transactions'] == 10 