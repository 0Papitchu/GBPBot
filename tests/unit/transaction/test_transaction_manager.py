#!/usr/bin/env python3
"""
Tests unitaires pour le gestionnaire de transactions.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from decimal import Decimal
from web3 import Web3
from web3.types import TxParams, TxReceipt, Wei, HexBytes

from gbpbot.core.transaction.transaction_manager import TransactionManager
from gbpbot.core.monitoring.bot_monitor import BotMonitor

@pytest.fixture
def mock_monitor():
    """Crée un mock du moniteur."""
    monitor = MagicMock(spec=BotMonitor)
    monitor.increment_counter = MagicMock()
    monitor.set_gauge = MagicMock()
    return monitor

@pytest.fixture
def mock_web3():
    """Crée un mock de Web3."""
    web3 = MagicMock()
    web3.eth = MagicMock()
    web3.eth.gas_price = Wei(50 * 10**9)  # 50 gwei
    web3.eth.get_transaction_count = AsyncMock(return_value=10)
    web3.eth.send_transaction = AsyncMock(return_value=HexBytes('0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef'))
    web3.eth.get_transaction_receipt = AsyncMock(return_value=None)
    web3.eth.get_transaction = AsyncMock(return_value=None)
    web3.eth.estimate_gas = AsyncMock(return_value=21000)
    web3.eth.block_number = 100
    web3.eth.account = MagicMock()
    web3.eth.account.from_key = MagicMock()
    web3.eth.account.from_key.return_value.address = '0x1234567890abcdef1234567890abcdef12345678'
    web3.from_wei = Web3.from_wei
    return web3

@pytest.fixture
def mock_rpc_manager(mock_web3):
    """Crée un mock du gestionnaire RPC."""
    rpc_manager = MagicMock()
    rpc_manager.get_web3 = AsyncMock(return_value=mock_web3)
    return rpc_manager

@pytest.fixture
def mock_gas_optimizer():
    """Crée un mock de l'optimiseur de gas."""
    gas_optimizer = MagicMock()
    gas_optimizer.optimize_transaction = AsyncMock(side_effect=lambda tx: tx)
    gas_optimizer.estimate_transaction_cost = AsyncMock(return_value=(Wei(21000 * 50 * 10**9), "0.00105 ETH"))
    gas_optimizer.get_gas_price = AsyncMock(return_value=Wei(50 * 10**9))
    gas_optimizer.get_eip1559_fees = AsyncMock(return_value=(Wei(60 * 10**9), Wei(5 * 10**9)))
    return gas_optimizer

@pytest.fixture
def mock_config():
    """Crée un mock de la configuration."""
    return {
        'transaction': {
            'timeout': 60,
            'max_pending_transactions': 5
        },
        'security': {
            'min_block_confirmations': 1,
            'max_confirmation_attempts': 3,
            'max_slippage': 1.0,
            'max_gas_price': 100
        },
        'wallet': {
            'private_key': '0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef'
        }
    }

@pytest.fixture
def transaction_manager(mock_monitor, mock_rpc_manager, mock_gas_optimizer, mock_config):
    """Crée une instance du gestionnaire de transactions avec des mocks."""
    with patch('gbpbot.core.transaction.transaction_manager.ConfigManager') as mock_config_manager, \
         patch('gbpbot.core.transaction.transaction_manager.RPCManager', return_value=mock_rpc_manager), \
         patch('gbpbot.core.transaction.transaction_manager.gas_optimizer', mock_gas_optimizer):
        
        # Configurer le mock du gestionnaire de configuration
        mock_config_manager.return_value.get_config.return_value = mock_config
        
        # Créer le gestionnaire de transactions
        tx_manager = TransactionManager(mock_monitor)
        
        # Remplacer la méthode _initialize_nonce par un mock
        tx_manager._initialize_nonce = AsyncMock()
        
        # Initialiser le nonce manuellement
        tx_manager.current_nonce = 10
        
        yield tx_manager

@pytest.mark.asyncio
async def test_transaction_manager_initialization(transaction_manager, mock_monitor):
    """Teste l'initialisation du gestionnaire de transactions."""
    assert transaction_manager.monitor == mock_monitor
    assert transaction_manager.tx_timeout == 60
    assert transaction_manager.max_pending_txs == 5
    assert transaction_manager.confirmation_blocks == 1
    assert transaction_manager.max_confirmation_attempts == 3
    assert transaction_manager.max_slippage == Decimal('1.0')
    assert transaction_manager.max_gas_price == Wei(100 * 10**9)
    assert transaction_manager.pending_transactions == {}
    assert transaction_manager.transaction_history == {}
    assert transaction_manager.current_nonce == 10
    assert transaction_manager.running == False

@pytest.mark.asyncio
async def test_transaction_manager_start_stop(transaction_manager):
    """Teste le démarrage et l'arrêt du gestionnaire de transactions."""
    # Remplacer la méthode _monitor_pending_transactions par un mock
    transaction_manager._monitor_pending_transactions = AsyncMock()
    
    # Démarrer le gestionnaire
    await transaction_manager.start()
    
    # Vérifier que le gestionnaire est démarré
    assert transaction_manager.running == True
    transaction_manager._initialize_nonce.assert_called_once()
    
    # Démarrer à nouveau (ne devrait rien faire)
    await transaction_manager.start()
    assert transaction_manager._initialize_nonce.call_count == 1
    
    # Arrêter le gestionnaire
    await transaction_manager.stop()
    
    # Vérifier que le gestionnaire est arrêté
    assert transaction_manager.running == False
    
    # Arrêter à nouveau (ne devrait rien faire)
    await transaction_manager.stop()
    assert transaction_manager.running == False

@pytest.mark.asyncio
async def test_send_transaction(transaction_manager, mock_web3, mock_gas_optimizer):
    """Teste l'envoi d'une transaction."""
    # Remplacer la méthode wait_for_transaction_receipt par un mock
    transaction_manager.wait_for_transaction_receipt = AsyncMock()
    
    # Créer les paramètres de la transaction
    tx_params = {
        'from': '0x1234567890abcdef1234567890abcdef12345678',
        'to': '0xabcdef1234567890abcdef1234567890abcdef12',
        'value': 1000000000000000000,  # 1 ETH
        'gas': 21000,
        'gasPrice': Wei(50 * 10**9)  # 50 gwei
    }
    
    # Démarrer le gestionnaire
    await transaction_manager.start()
    
    # Envoyer la transaction
    tx_hash, receipt = await transaction_manager.send_transaction(tx_params)
    
    # Vérifier que la transaction a été envoyée
    assert tx_hash == HexBytes('0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef')
    mock_gas_optimizer.optimize_transaction.assert_called_once_with(tx_params)
    mock_web3.eth.send_transaction.assert_called_once()
    transaction_manager.wait_for_transaction_receipt.assert_called_once_with(tx_hash)
    
    # Vérifier que la transaction a été enregistrée
    assert len(transaction_manager.pending_transactions) == 1
    assert tx_hash.hex() in transaction_manager.pending_transactions
    assert len(transaction_manager.transaction_history) == 1
    
    # Vérifier que les métriques ont été mises à jour
    transaction_manager.monitor.increment_counter.assert_called_with('transactions_sent')
    transaction_manager.monitor.set_gauge.assert_called_with('pending_transactions', 1)

@pytest.mark.asyncio
async def test_send_transaction_with_eip1559(transaction_manager, mock_web3, mock_gas_optimizer):
    """Teste l'envoi d'une transaction avec EIP-1559."""
    # Remplacer la méthode wait_for_transaction_receipt par un mock
    transaction_manager.wait_for_transaction_receipt = AsyncMock()
    
    # Créer les paramètres de la transaction
    tx_params = {
        'from': '0x1234567890abcdef1234567890abcdef12345678',
        'to': '0xabcdef1234567890abcdef1234567890abcdef12',
        'value': 1000000000000000000,  # 1 ETH
        'gas': 21000,
        'maxFeePerGas': Wei(60 * 10**9),  # 60 gwei
        'maxPriorityFeePerGas': Wei(5 * 10**9)  # 5 gwei
    }
    
    # Configurer le mock de l'optimiseur de gas pour retourner les paramètres EIP-1559
    mock_gas_optimizer.optimize_transaction.side_effect = lambda tx: {
        'from': tx['from'],
        'to': tx['to'],
        'value': tx['value'],
        'gas': tx['gas'],
        'maxFeePerGas': Wei(60 * 10**9),
        'maxPriorityFeePerGas': Wei(5 * 10**9)
    }
    
    # Démarrer le gestionnaire
    await transaction_manager.start()
    
    # Envoyer la transaction
    tx_hash, receipt = await transaction_manager.send_transaction(tx_params)
    
    # Vérifier que la transaction a été envoyée
    assert tx_hash == HexBytes('0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef')
    mock_gas_optimizer.optimize_transaction.assert_called_once_with(tx_params)
    mock_web3.eth.send_transaction.assert_called_once()
    
    # Vérifier que les paramètres EIP-1559 ont été utilisés
    call_args = mock_web3.eth.send_transaction.call_args[0][0]
    assert 'maxFeePerGas' in call_args
    assert 'maxPriorityFeePerGas' in call_args
    assert 'gasPrice' not in call_args
    assert call_args['maxFeePerGas'] == Wei(60 * 10**9)
    assert call_args['maxPriorityFeePerGas'] == Wei(5 * 10**9)

@pytest.mark.asyncio
async def test_wait_for_transaction_receipt(transaction_manager, mock_web3):
    """Teste l'attente du reçu d'une transaction."""
    # Configurer le mock pour retourner un reçu après quelques appels
    receipt = MagicMock()
    receipt.status = 1
    receipt.blockNumber = 100
    
    # Configurer le mock pour retourner None les 3 premières fois, puis le reçu
    mock_web3.eth.get_transaction_receipt.side_effect = [None, None, None, receipt]
    
    # Créer un hash de transaction
    tx_hash = HexBytes('0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef')
    
    # Ajouter la transaction aux transactions en attente
    transaction_manager.pending_transactions[tx_hash.hex()] = {
        'id': '12345',
        'hash': tx_hash.hex(),
        'params': {},
        'timestamp': 0,
        'status': 'pending'
    }
    transaction_manager.transaction_history['12345'] = {
        'id': '12345',
        'hash': tx_hash.hex(),
        'params': {},
        'timestamp': 0,
        'status': 'pending'
    }
    
    # Attendre le reçu
    result = await transaction_manager.wait_for_transaction_receipt(tx_hash)
    
    # Vérifier que le reçu a été retourné
    assert result == receipt
    assert mock_web3.eth.get_transaction_receipt.call_count == 4
    
    # Vérifier que le statut de la transaction a été mis à jour
    assert transaction_manager.transaction_history['12345']['status'] == 'confirmed'
    assert transaction_manager.transaction_history['12345']['receipt'] == receipt
    assert transaction_manager.transaction_history['12345']['confirmations'] == 0
    
    # Vérifier que la transaction a été supprimée des transactions en attente
    assert tx_hash.hex() not in transaction_manager.pending_transactions

@pytest.mark.asyncio
async def test_wait_for_transaction_receipt_timeout(transaction_manager, mock_web3):
    """Teste le timeout lors de l'attente du reçu d'une transaction."""
    # Configurer le mock pour toujours retourner None
    mock_web3.eth.get_transaction_receipt.return_value = None
    
    # Créer un hash de transaction
    tx_hash = HexBytes('0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef')
    
    # Réduire le timeout pour accélérer le test
    transaction_manager.tx_timeout = 0.1
    
    # Attendre le reçu (devrait lever une exception)
    with pytest.raises(TimeoutError):
        await transaction_manager.wait_for_transaction_receipt(tx_hash)

@pytest.mark.asyncio
async def test_get_transaction_status(transaction_manager, mock_web3):
    """Teste la récupération du statut d'une transaction."""
    # Créer un hash de transaction
    tx_hash = '0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef'
    
    # Ajouter la transaction aux transactions en attente
    transaction_manager.pending_transactions[tx_hash] = {
        'id': '12345',
        'hash': tx_hash,
        'params': {},
        'timestamp': 0,
        'status': 'pending'
    }
    
    # Récupérer le statut
    status = await transaction_manager.get_transaction_status(tx_hash)
    
    # Vérifier que le statut a été retourné
    assert status == transaction_manager.pending_transactions[tx_hash]
    
    # Tester avec une transaction non en attente
    tx = MagicMock()
    tx.blockNumber = 100
    mock_web3.eth.get_transaction.return_value = tx
    
    receipt = MagicMock()
    receipt.status = 1
    mock_web3.eth.get_transaction_receipt.return_value = receipt
    
    status = await transaction_manager.get_transaction_status('0xabcdef')
    
    assert status['status'] == 'confirmed'
    assert status['hash'] == '0xabcdef'
    assert status['receipt'] == receipt

@pytest.mark.asyncio
async def test_cancel_transaction(transaction_manager, mock_web3):
    """Teste l'annulation d'une transaction."""
    # Remplacer la méthode send_transaction par un mock
    transaction_manager.send_transaction = AsyncMock(return_value=(HexBytes('0xabcdef'), None))
    
    # Créer un hash de transaction
    tx_hash = '0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef'
    
    # Ajouter la transaction aux transactions en attente
    transaction_manager.pending_transactions[tx_hash] = {
        'id': '12345',
        'hash': tx_hash,
        'params': {
            'from': '0x1234567890abcdef1234567890abcdef12345678',
            'to': '0xabcdef1234567890abcdef1234567890abcdef12',
            'value': 1000000000000000000,
            'gas': 21000,
            'gasPrice': Wei(50 * 10**9),
            'nonce': 10
        },
        'timestamp': 0,
        'status': 'pending'
    }
    transaction_manager.transaction_history['12345'] = {
        'id': '12345',
        'hash': tx_hash,
        'params': {},
        'timestamp': 0,
        'status': 'pending'
    }
    
    # Annuler la transaction
    result = await transaction_manager.cancel_transaction(tx_hash)
    
    # Vérifier que la transaction a été annulée
    assert result == HexBytes('0xabcdef')
    transaction_manager.send_transaction.assert_called_once()
    
    # Vérifier que le statut de la transaction a été mis à jour
    assert transaction_manager.pending_transactions[tx_hash]['status'] == 'cancelled'
    assert transaction_manager.pending_transactions[tx_hash]['cancelled_by'] == '0xabcdef'
    assert transaction_manager.transaction_history['12345']['status'] == 'cancelled'
    assert transaction_manager.transaction_history['12345']['cancelled_by'] == '0xabcdef'
    
    # Tester avec une transaction non existante
    result = await transaction_manager.cancel_transaction('0xnonexistent')
    assert result is None

@pytest.mark.asyncio
async def test_speed_up_transaction(transaction_manager, mock_web3):
    """Teste l'accélération d'une transaction."""
    # Remplacer la méthode send_transaction par un mock
    transaction_manager.send_transaction = AsyncMock(return_value=(HexBytes('0xabcdef'), None))
    
    # Créer un hash de transaction
    tx_hash = '0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef'
    
    # Ajouter la transaction aux transactions en attente
    transaction_manager.pending_transactions[tx_hash] = {
        'id': '12345',
        'hash': tx_hash,
        'params': {
            'from': '0x1234567890abcdef1234567890abcdef12345678',
            'to': '0xabcdef1234567890abcdef1234567890abcdef12',
            'value': 1000000000000000000,
            'gas': 21000,
            'gasPrice': Wei(50 * 10**9),
            'nonce': 10
        },
        'timestamp': 0,
        'status': 'pending'
    }
    transaction_manager.transaction_history['12345'] = {
        'id': '12345',
        'hash': tx_hash,
        'params': {},
        'timestamp': 0,
        'status': 'pending'
    }
    
    # Accélérer la transaction
    result = await transaction_manager.speed_up_transaction(tx_hash)
    
    # Vérifier que la transaction a été accélérée
    assert result == HexBytes('0xabcdef')
    transaction_manager.send_transaction.assert_called_once()
    
    # Vérifier que le statut de la transaction a été mis à jour
    assert transaction_manager.pending_transactions[tx_hash]['status'] == 'replaced'
    assert transaction_manager.pending_transactions[tx_hash]['replaced_by'] == '0xabcdef'
    assert transaction_manager.transaction_history['12345']['status'] == 'replaced'
    assert transaction_manager.transaction_history['12345']['replaced_by'] == '0xabcdef'
    
    # Tester avec une transaction non existante
    result = await transaction_manager.speed_up_transaction('0xnonexistent')
    assert result is None

@pytest.mark.asyncio
async def test_monitor_pending_transactions(transaction_manager, mock_web3):
    """Teste la surveillance des transactions en attente."""
    # Créer un hash de transaction
    tx_hash = '0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef'
    
    # Ajouter la transaction aux transactions en attente
    transaction_manager.pending_transactions[tx_hash] = {
        'id': '12345',
        'hash': tx_hash,
        'params': {},
        'timestamp': 0,
        'status': 'pending'
    }
    transaction_manager.transaction_history['12345'] = {
        'id': '12345',
        'hash': tx_hash,
        'params': {},
        'timestamp': 0,
        'status': 'pending'
    }
    
    # Configurer le mock pour retourner un reçu
    receipt = MagicMock()
    receipt.status = 1
    receipt.blockNumber = 99
    mock_web3.eth.get_transaction_receipt.return_value = receipt
    
    # Démarrer la surveillance
    transaction_manager.running = True
    monitor_task = asyncio.create_task(transaction_manager._monitor_pending_transactions())
    
    # Attendre un peu pour que la surveillance s'exécute
    await asyncio.sleep(0.1)
    
    # Arrêter la surveillance
    transaction_manager.running = False
    monitor_task.cancel()
    try:
        await monitor_task
    except asyncio.CancelledError:
        pass
    
    # Vérifier que la transaction a été mise à jour
    assert tx_hash not in transaction_manager.pending_transactions
    assert transaction_manager.transaction_history['12345']['status'] == 'confirmed'
    assert transaction_manager.transaction_history['12345']['receipt'] == receipt
    assert transaction_manager.transaction_history['12345']['confirmations'] == 1

@pytest.mark.asyncio
async def test_get_transaction_by_id(transaction_manager):
    """Teste la récupération d'une transaction par son ID."""
    # Ajouter une transaction à l'historique
    transaction_manager.transaction_history['12345'] = {
        'id': '12345',
        'hash': '0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef',
        'params': {},
        'timestamp': 0,
        'status': 'pending'
    }
    
    # Récupérer la transaction
    tx = await transaction_manager.get_transaction_by_id('12345')
    
    # Vérifier que la transaction a été retournée
    assert tx == transaction_manager.transaction_history['12345']
    
    # Tester avec un ID non existant
    tx = await transaction_manager.get_transaction_by_id('nonexistent')
    assert tx is None

@pytest.mark.asyncio
async def test_get_all_transactions(transaction_manager):
    """Teste la récupération de toutes les transactions."""
    # Ajouter des transactions à l'historique
    transaction_manager.transaction_history['12345'] = {
        'id': '12345',
        'hash': '0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef',
        'params': {},
        'timestamp': 0,
        'status': 'pending'
    }
    transaction_manager.transaction_history['67890'] = {
        'id': '67890',
        'hash': '0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890',
        'params': {},
        'timestamp': 0,
        'status': 'confirmed'
    }
    
    # Récupérer toutes les transactions
    txs = await transaction_manager.get_all_transactions()
    
    # Vérifier que toutes les transactions ont été retournées
    assert len(txs) == 2
    assert '12345' in txs
    assert '67890' in txs
    
    # Récupérer les transactions avec un statut spécifique
    txs = await transaction_manager.get_all_transactions(status='pending')
    
    # Vérifier que seules les transactions avec le statut spécifié ont été retournées
    assert len(txs) == 1
    assert '12345' in txs
    assert '67890' not in txs

@pytest.mark.asyncio
async def test_get_pending_transactions(transaction_manager):
    """Teste la récupération des transactions en attente."""
    # Ajouter des transactions aux transactions en attente
    transaction_manager.pending_transactions['0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef'] = {
        'id': '12345',
        'hash': '0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef',
        'params': {},
        'timestamp': 0,
        'status': 'pending'
    }
    transaction_manager.pending_transactions['0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890'] = {
        'id': '67890',
        'hash': '0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890',
        'params': {},
        'timestamp': 0,
        'status': 'pending'
    }
    
    # Récupérer les transactions en attente
    txs = await transaction_manager.get_pending_transactions()
    
    # Vérifier que toutes les transactions en attente ont été retournées
    assert len(txs) == 2
    assert '0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef' in txs
    assert '0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890' in txs 