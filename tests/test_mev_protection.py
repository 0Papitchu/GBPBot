#!/usr/bin/env python3
"""
Tests unitaires pour le module de protection MEV.
"""

import pytest
import asyncio
from decimal import Decimal
from unittest.mock import Mock, patch, AsyncMock
from web3 import Web3
from eth_typing import HexStr

from gbpbot.core.security.mev_protection import MEVProtection, MEVConfig

@pytest.fixture
def config():
    """Configuration de test."""
    return {
        'mev': {
            'privacy_mode': True,
            'slippage_buffer': '0.005',
            'block_delay': 2
        }
    }

@pytest.fixture
def web3():
    """Mock de Web3."""
    mock_web3 = Mock(spec=Web3)
    mock_web3.to_wei = Web3.to_wei
    return mock_web3

@pytest.fixture
async def mev_protection(config, web3):
    """Instance de MEVProtection pour les tests."""
    protection = MEVProtection(config, web3)
    yield protection

@pytest.mark.asyncio
async def test_init(mev_protection):
    """Teste l'initialisation."""
    assert isinstance(mev_protection.config, MEVConfig)
    assert mev_protection.config.privacy_mode is True
    assert mev_protection.config.slippage_buffer == Decimal('0.005')
    assert mev_protection.config.block_delay == 2
    assert isinstance(mev_protection.pending_transactions, dict)
    assert isinstance(mev_protection.known_sandwichers, list)

@pytest.mark.asyncio
async def test_protect_transaction(mev_protection):
    """Teste la protection d'une transaction."""
    # Mock des fonctions internes
    mev_protection._optimize_gas_fees = AsyncMock(return_value={
        'maxFeePerGas': 100000000000,
        'maxPriorityFeePerGas': 2000000000
    })
    mev_protection.web3.eth.block_number = AsyncMock(return_value=1000)
    mev_protection.web3.eth.get_block = AsyncMock(return_value={'timestamp': 1234567890})
    
    # Transaction de test
    tx = {
        'from': '0x1234...',
        'to': '0x5678...',
        'value': 1000000000000000000,
        'hash': '0xabcd...'
    }
    
    protected_tx = await mev_protection.protect_transaction(tx)
    
    assert 'maxFeePerGas' in protected_tx
    assert 'maxPriorityFeePerGas' in protected_tx
    assert 'validUntilBlock' in protected_tx
    assert protected_tx['validUntilBlock'] == 1002
    assert protected_tx['hash'] in mev_protection.pending_transactions

@pytest.mark.asyncio
async def test_monitor_transaction_pending_too_long(mev_protection):
    """Teste la détection d'une transaction en attente trop longtemps."""
    tx_hash = '0xabcd...'
    mev_protection.pending_transactions[tx_hash] = {
        'block_number': 1000,
        'timestamp': 1234567890,
        'original_tx': {}
    }
    
    mev_protection.web3.eth.block_number = AsyncMock(return_value=1003)
    
    is_safe = await mev_protection.monitor_transaction(tx_hash)
    assert not is_safe

@pytest.mark.asyncio
async def test_monitor_transaction_sandwich_attack(mev_protection):
    """Teste la détection d'une attaque sandwich."""
    tx_hash = '0xabcd...'
    mev_protection.pending_transactions[tx_hash] = {
        'block_number': 1000,
        'timestamp': 1234567890,
        'original_tx': {}
    }
    
    # Mock des transactions dans le block
    block_txs = [
        {
            'hash': HexStr('0x1111'),
            'from': '0xattacker',
            'input': '0x38ed1739...',  # Signature de swap
            'maxFeePerGas': mev_protection.config.max_base_fee + 1000
        },
        {
            'hash': HexStr(tx_hash),
            'from': '0xuser',
            'input': '0x38ed1739...'
        },
        {
            'hash': HexStr('0x2222'),
            'from': '0xattacker',
            'input': '0x18cbafe5...'  # Signature de swap
        }
    ]
    
    mev_protection.web3.eth.block_number = AsyncMock(return_value=1001)
    mev_protection.web3.eth.get_transaction_receipt = AsyncMock(return_value={'blockNumber': 1001})
    mev_protection.web3.eth.get_block = AsyncMock(return_value={'transactions': block_txs})
    
    is_safe = await mev_protection.monitor_transaction(tx_hash)
    assert not is_safe
    assert '0xattacker' in mev_protection.known_sandwichers

@pytest.mark.asyncio
async def test_optimize_gas_fees(mev_protection):
    """Teste l'optimisation des gas fees."""
    # Mock du dernier block
    mev_protection.web3.eth.get_block = AsyncMock(return_value={
        'baseFeePerGas': Web3.to_wei(50, 'gwei'),
        'transactions': []
    })
    
    # Mock du calcul du priority fee
    mev_protection._calculate_optimal_priority_fee = AsyncMock(
        return_value=Web3.to_wei(2, 'gwei')
    )
    
    tx = {}
    optimized_tx = await mev_protection._optimize_gas_fees(tx)
    
    assert 'maxFeePerGas' in optimized_tx
    assert 'maxPriorityFeePerGas' in optimized_tx
    assert optimized_tx['maxFeePerGas'] > optimized_tx['maxPriorityFeePerGas']

@pytest.mark.asyncio
async def test_calculate_optimal_priority_fee(mev_protection):
    """Teste le calcul du priority fee optimal."""
    # Mock des blocks récents
    blocks = []
    for i in range(10):
        blocks.append({
            'transactions': [
                {'maxPriorityFeePerGas': Web3.to_wei(2 + i, 'gwei')},
                {'maxPriorityFeePerGas': Web3.to_wei(3 + i, 'gwei')}
            ]
        })
    
    mev_protection.web3.eth.block_number = AsyncMock(return_value=1000)
    mev_protection.web3.eth.get_block = AsyncMock(side_effect=blocks)
    
    optimal_fee = await mev_protection._calculate_optimal_priority_fee()
    
    assert optimal_fee >= mev_protection.config.min_priority_fee
    assert optimal_fee <= mev_protection.config.max_priority_fee

def test_add_slippage_protection(mev_protection):
    """Teste l'ajout de protection contre le slippage."""
    tx = {
        'value': 1000000000000000000,
        'minOutput': 1000
    }
    
    protected_tx = mev_protection._add_slippage_protection(tx)
    
    assert protected_tx['minOutput'] < tx['minOutput']
    assert protected_tx['minOutput'] == int(tx['minOutput'] * (1 - mev_protection.config.slippage_buffer))

def test_is_suspicious_transaction(mev_protection):
    """Teste la détection de transactions suspectes."""
    # Cas 1: Adresse connue
    mev_protection.known_sandwichers = ['0xattacker']
    tx1 = {'from': '0xattacker'}
    assert mev_protection._is_suspicious_transaction(tx1)
    
    # Cas 2: Gas fees élevés
    tx2 = {
        'from': '0xother',
        'maxFeePerGas': mev_protection.config.max_base_fee + 1000
    }
    assert mev_protection._is_suspicious_transaction(tx2)
    
    # Cas 3: Signature de swap
    tx3 = {
        'from': '0xother',
        'input': '0x38ed1739...'  # swapExactTokensForTokens
    }
    assert mev_protection._is_suspicious_transaction(tx3)
    
    # Cas 4: Transaction normale
    tx4 = {
        'from': '0xnormal',
        'maxFeePerGas': mev_protection.config.max_base_fee - 1000,
        'input': '0x'
    }
    assert not mev_protection._is_suspicious_transaction(tx4) 