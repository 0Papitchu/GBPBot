#!/usr/bin/env python3
"""
Tests unitaires pour le système d'urgence.
"""

import pytest
import asyncio
from decimal import Decimal
from unittest.mock import Mock, patch
from web3 import Web3

from gbpbot.core.security.emergency_system import EmergencySystem
from gbpbot.core.monitoring.monitor import BotMonitor
from gbpbot.core.rpc.rpc_manager import RPCManager

@pytest.fixture
def config():
    """Configuration de test."""
    return {
        'emergency': {
            'max_loss': '0.10',
            'max_gas_gwei': '500',
            'min_balance_eth': '0.1',
            'safe_wallet_address': '0x1234567890123456789012345678901234567890'
        }
    }

@pytest.fixture
def monitor():
    """Mock du moniteur."""
    return Mock(spec=BotMonitor)

@pytest.fixture
def rpc_manager():
    """Mock du RPC manager."""
    return Mock(spec=RPCManager)

@pytest.fixture
async def emergency_system(config, monitor):
    """Instance de EmergencySystem pour les tests."""
    with patch('gbpbot.core.security.emergency_system.RPCManager') as mock_rpc:
        mock_rpc.return_value = Mock(spec=RPCManager)
        system = EmergencySystem(config, monitor)
        yield system

@pytest.mark.asyncio
async def test_init(emergency_system):
    """Teste l'initialisation."""
    assert emergency_system.max_loss_threshold == Decimal('0.10')
    assert emergency_system.max_gas_threshold == Web3.to_wei(500, 'gwei')
    assert emergency_system.min_balance_threshold == Web3.to_wei(0.1, 'ether')
    assert not emergency_system.is_emergency
    assert isinstance(emergency_system.pending_transactions, dict)
    assert isinstance(emergency_system.emergency_actions, list)

@pytest.mark.asyncio
async def test_check_emergency_conditions_low_balance(emergency_system):
    """Teste la détection d'une balance faible."""
    # Mock de la balance
    emergency_system._get_wallet_balance = Mock(return_value=Web3.to_wei(0.05, 'ether'))
    
    is_emergency = await emergency_system.check_emergency_conditions()
    
    assert is_emergency
    assert emergency_system.is_emergency
    assert len(emergency_system.emergency_actions) == 1
    assert emergency_system.emergency_actions[0]['reason'] == 'LOW_BALANCE'

@pytest.mark.asyncio
async def test_check_emergency_conditions_high_gas(emergency_system):
    """Teste la détection d'un gas price élevé."""
    # Mock des fonctions
    emergency_system._get_wallet_balance = Mock(return_value=Web3.to_wei(1, 'ether'))
    emergency_system._get_current_gas_price = Mock(return_value=Web3.to_wei(600, 'gwei'))
    
    is_emergency = await emergency_system.check_emergency_conditions()
    
    assert is_emergency
    assert emergency_system.is_emergency
    assert len(emergency_system.emergency_actions) == 1
    assert emergency_system.emergency_actions[0]['reason'] == 'HIGH_GAS'

@pytest.mark.asyncio
async def test_check_emergency_conditions_excessive_loss(emergency_system):
    """Teste la détection de pertes excessives."""
    # Mock des fonctions
    emergency_system._get_wallet_balance = Mock(return_value=Web3.to_wei(1, 'ether'))
    emergency_system._get_current_gas_price = Mock(return_value=Web3.to_wei(100, 'gwei'))
    emergency_system._calculate_total_loss = Mock(return_value=Decimal('0.15'))
    
    is_emergency = await emergency_system.check_emergency_conditions()
    
    assert is_emergency
    assert emergency_system.is_emergency
    assert len(emergency_system.emergency_actions) == 1
    assert emergency_system.emergency_actions[0]['reason'] == 'EXCESSIVE_LOSS'

@pytest.mark.asyncio
async def test_emergency_shutdown(emergency_system):
    """Teste la procédure d'arrêt d'urgence."""
    # Mock des fonctions
    emergency_system._cancel_pending_transactions = Mock()
    emergency_system._close_all_positions = Mock()
    emergency_system._secure_funds = Mock()
    emergency_system._send_emergency_notifications = Mock()
    
    await emergency_system.emergency_shutdown()
    
    assert emergency_system.is_emergency
    assert emergency_system._cancel_pending_transactions.called
    assert emergency_system._close_all_positions.called
    assert emergency_system._secure_funds.called
    assert emergency_system._send_emergency_notifications.called

@pytest.mark.asyncio
async def test_rollback_transaction_confirmed(emergency_system):
    """Teste le rollback d'une transaction confirmée."""
    tx_hash = "0x1234"
    tx_info = {'value': 1000000}
    
    # Ajouter une transaction
    await emergency_system.add_pending_transaction(tx_hash, tx_info)
    
    # Mock de la vérification
    emergency_system._is_transaction_confirmed = Mock(return_value=True)
    
    result = await emergency_system.rollback_transaction(tx_hash)
    
    assert not result
    assert tx_hash in emergency_system.pending_transactions

@pytest.mark.asyncio
async def test_rollback_transaction_success(emergency_system):
    """Teste le rollback réussi d'une transaction."""
    tx_hash = "0x1234"
    tx_info = {
        'value': 1000000,
        'maxFeePerGas': 50000000000,
        'maxPriorityFeePerGas': 25000000000
    }
    
    # Ajouter une transaction
    await emergency_system.add_pending_transaction(tx_hash, tx_info)
    
    # Mock des fonctions
    emergency_system._is_transaction_confirmed = Mock(return_value=False)
    emergency_system._send_replacement_transaction = Mock(return_value="0x5678")
    
    result = await emergency_system.rollback_transaction(tx_hash)
    
    assert result
    assert tx_hash not in emergency_system.pending_transactions

@pytest.mark.asyncio
async def test_add_pending_transaction(emergency_system):
    """Teste l'ajout d'une transaction en attente."""
    tx_hash = "0x1234"
    tx_info = {'value': 1000000}
    
    await emergency_system.add_pending_transaction(tx_hash, tx_info)
    
    assert tx_hash in emergency_system.pending_transactions
    assert emergency_system.pending_transactions[tx_hash] == tx_info

@pytest.mark.asyncio
async def test_create_replacement_transaction(emergency_system):
    """Teste la création d'une transaction de remplacement."""
    tx_info = {
        'value': 1000000,
        'maxFeePerGas': 50000000000,
        'maxPriorityFeePerGas': 25000000000
    }
    
    replacement_tx = await emergency_system._create_replacement_transaction(tx_info)
    
    assert replacement_tx['value'] == 0
    assert replacement_tx['maxFeePerGas'] == int(tx_info['maxFeePerGas'] * 1.1)
    assert replacement_tx['maxPriorityFeePerGas'] == int(tx_info['maxPriorityFeePerGas'] * 1.1)

@pytest.mark.asyncio
async def test_get_emergency_status(emergency_system):
    """Teste la récupération de l'état d'urgence."""
    # Ajouter quelques données
    emergency_system.is_emergency = True
    await emergency_system.add_pending_transaction("0x1234", {})
    emergency_system.emergency_actions.append({
        'timestamp': 1234567890,
        'reason': 'TEST'
    })
    
    status = emergency_system.get_emergency_status()
    
    assert status['is_emergency']
    assert status['pending_transactions'] == 1
    assert len(status['emergency_actions']) == 1

@pytest.mark.asyncio
async def test_error_handling(emergency_system):
    """Teste la gestion des erreurs."""
    # Test avec une transaction inexistante
    result = await emergency_system.rollback_transaction("0x9999")
    assert not result
    
    # Test avec des erreurs dans les fonctions critiques
    emergency_system._get_wallet_balance = Mock(side_effect=Exception("Test error"))
    is_emergency = await emergency_system.check_emergency_conditions()
    assert is_emergency  # Par sécurité, on considère qu'il y a urgence en cas d'erreur 