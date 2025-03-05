"""
Tests for the Ethereum blockchain client.
"""

import asyncio
import json
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from gbpbot.core.blockchain.ethereum import EthereumClient
from gbpbot.utils.exceptions import ConnectionError, TransactionError


@pytest.fixture
def ethereum_config():
    """Fixture for Ethereum client configuration."""
    return {
        "rpc_url": "https://mainnet.infura.io/v3/your-api-key",
        "private_key": "0x0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",
        "chain_id": 1,
        "gas_limit": 200000,
        "gas_price_strategy": "medium"
    }


@pytest.fixture
def mock_web3():
    """Fixture for mocked Web3 instance."""
    with patch("gbpbot.core.blockchain.ethereum.Web3") as mock_web3_class:
        mock_web3 = MagicMock()
        mock_web3_class.return_value = mock_web3
        
        # Mock eth module
        mock_web3.eth = MagicMock()
        mock_web3.eth.chain_id = 1
        mock_web3.eth.get_balance = AsyncMock(return_value=1000000000000000000)  # 1 ETH
        mock_web3.eth.get_transaction_count = AsyncMock(return_value=10)
        mock_web3.eth.send_raw_transaction = AsyncMock(return_value=b"0x123456789abcdef")
        mock_web3.eth.wait_for_transaction_receipt = AsyncMock(return_value={
            "status": 1,
            "transactionHash": b"0x123456789abcdef",
            "blockNumber": 12345678
        })
        
        # Mock middleware
        mock_web3.middleware_onion = MagicMock()
        
        yield mock_web3


@pytest.fixture
async def ethereum_client(ethereum_config, mock_web3):
    """Fixture for Ethereum client instance."""
    client = EthereumClient(ethereum_config)
    await client.connect()
    yield client
    await client.disconnect()


@pytest.mark.asyncio
async def test_connect(ethereum_config, mock_web3):
    """Test connecting to Ethereum."""
    client = EthereumClient(ethereum_config)
    
    # Test successful connection
    result = await client.connect()
    assert result is True
    assert client.connected is True
    
    # Test connection with invalid private key
    client = EthereumClient({**ethereum_config, "private_key": "invalid"})
    with pytest.raises(ConnectionError):
        await client.connect()


@pytest.mark.asyncio
async def test_disconnect(ethereum_client):
    """Test disconnecting from Ethereum."""
    result = await ethereum_client.disconnect()
    assert result is True
    assert ethereum_client.connected is False


@pytest.mark.asyncio
async def test_get_balance(ethereum_client, mock_web3):
    """Test getting token balance."""
    # Test ETH balance
    balance = await ethereum_client.get_balance("ETH")
    assert balance == 1.0
    
    # Test ERC20 token balance
    with patch("gbpbot.core.blockchain.ethereum.Contract") as mock_contract:
        mock_token = MagicMock()
        mock_token.functions.balanceOf = MagicMock()
        mock_token.functions.balanceOf().call = AsyncMock(return_value=1000000000)
        mock_token.functions.decimals = MagicMock()
        mock_token.functions.decimals().call = AsyncMock(return_value=18)
        mock_contract.return_value = mock_token
        
        balance = await ethereum_client.get_balance("0x1234567890123456789012345678901234567890")
        assert balance == 0.000000001


@pytest.mark.asyncio
async def test_execute_transaction(ethereum_client, mock_web3):
    """Test executing a transaction."""
    tx_params = {
        "to": "0x1234567890123456789012345678901234567890",
        "value": 1000000000000000000,  # 1 ETH
        "gas": 21000,
        "gas_priority": "normal"
    }
    
    result = await ethereum_client.execute_transaction(tx_params)
    assert result["tx_hash"] == "0x123456789abcdef"
    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_wait_for_transaction(ethereum_client, mock_web3):
    """Test waiting for a transaction."""
    result = await ethereum_client.wait_for_transaction("0x123456789abcdef")
    assert result["confirmed"] is True
    assert result["block_number"] == 12345678


@pytest.mark.asyncio
async def test_get_transaction_status(ethereum_client, mock_web3):
    """Test getting transaction status."""
    mock_web3.eth.get_transaction = AsyncMock(return_value={
        "blockNumber": 12345678,
        "hash": b"0x123456789abcdef"
    })
    
    result = await ethereum_client.get_transaction_status("0x123456789abcdef")
    assert result["status"] == "confirmed"
    assert result["block_number"] == 12345678 