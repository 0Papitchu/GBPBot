"""
Tests for the Solana blockchain client.
"""

import asyncio
import base64
import json
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from gbpbot.core.blockchain.solana import SolanaClient
from gbpbot.utils.exceptions import ConnectionError, TransactionError, BalanceError


@pytest.fixture
def solana_config():
    """Fixture for Solana client configuration."""
    return {
        "rpc_url": "https://api.mainnet-beta.solana.com",
        "private_key": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32],
        "default_compute_units": 200000
    }


@pytest.fixture
def mock_solana_dependencies():
    """Fixture for mocked Solana dependencies."""
    # Mock AsyncClient
    with patch("gbpbot.core.blockchain.solana.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        # Mock get_version
        mock_client.get_version = AsyncMock(return_value={"solana-core": "1.10.0"})
        
        # Mock get_balance
        mock_client.get_balance = AsyncMock(return_value={
            "result": {"value": 1000000000}  # 1 SOL
        })
        
        # Mock get_token_accounts_by_owner
        mock_client.get_token_accounts_by_owner = AsyncMock(return_value={
            "result": {
                "value": [
                    {
                        "pubkey": "TokenAccountAddress123",
                        "account": {
                            "data": [
                                base64.b64encode(
                                    # Mock token account data structure
                                    # 32 bytes for mint
                                    bytes([0] * 32) + 
                                    # 32 bytes for owner
                                    bytes([0] * 32) + 
                                    # 8 bytes for amount (1000000000 in little endian)
                                    (1000000000).to_bytes(8, byteorder="little")
                                ).decode("utf-8"),
                                "base64"
                            ]
                        }
                    }
                ]
            }
        })
        
        # Mock get_recent_blockhash
        mock_client.get_recent_blockhash = AsyncMock(return_value={
            "result": {
                "value": {
                    "blockhash": "11111111111111111111111111111111"
                }
            }
        })
        
        # Mock send_raw_transaction
        mock_client.send_raw_transaction = AsyncMock(return_value={
            "result": "TransactionSignature123"
        })
        
        # Mock get_signature_statuses
        mock_client.get_signature_statuses = AsyncMock(return_value={
            "result": {
                "value": [
                    {
                        "slot": 12345678,
                        "confirmations": 32,
                        "confirmationStatus": "finalized"
                    }
                ]
            }
        })
        
        yield mock_client


@pytest.fixture
def mock_keypair():
    """Fixture for mocked Solana Keypair."""
    with patch("gbpbot.core.blockchain.solana.Keypair") as mock_keypair_class:
        mock_keypair = MagicMock()
        mock_keypair_class.from_secret_key.return_value = mock_keypair
        
        # Mock public_key
        mock_public_key = MagicMock()
        mock_public_key.to_base58.return_value = "SolanaPublicKey123"
        mock_keypair.public_key = mock_public_key
        
        yield mock_keypair


@pytest.fixture
def mock_public_key():
    """Fixture for mocked Solana PublicKey."""
    with patch("gbpbot.core.blockchain.solana.PublicKey") as mock_pubkey_class:
        mock_pubkey = MagicMock()
        mock_pubkey_class.return_value = mock_pubkey
        mock_pubkey.to_base58.return_value = "SolanaPublicKey123"
        
        yield mock_pubkey


@pytest.fixture
def mock_transaction():
    """Fixture for mocked Solana Transaction."""
    with patch("gbpbot.core.blockchain.solana.Transaction") as mock_tx_class:
        mock_tx = MagicMock()
        mock_tx_class.return_value = mock_tx
        
        # Mock add method
        mock_tx.add = MagicMock()
        
        # Mock sign method
        mock_tx.sign = MagicMock()
        
        # Mock serialize method
        mock_tx.serialize = MagicMock(return_value=bytes([0, 1, 2, 3, 4]))
        
        yield mock_tx


@pytest.fixture
async def solana_client(solana_config, mock_solana_dependencies, mock_keypair, mock_public_key, mock_transaction):
    """Fixture for Solana client instance."""
    client = SolanaClient(solana_config)
    await client.connect()
    yield client
    await client.disconnect()


@pytest.mark.asyncio
async def test_connect(solana_config, mock_solana_dependencies, mock_keypair, mock_public_key):
    """Test connecting to Solana."""
    client = SolanaClient(solana_config)
    
    # Test successful connection
    result = await client.connect()
    assert result is True
    assert client.connected is True
    
    # Test connection with invalid private key
    client = SolanaClient({**solana_config, "private_key": "invalid_format"})
    result = await client.connect()
    assert result is False


@pytest.mark.asyncio
async def test_disconnect(solana_client):
    """Test disconnecting from Solana."""
    result = await solana_client.disconnect()
    assert result is True
    assert solana_client.connected is False


@pytest.mark.asyncio
async def test_get_balance_sol(solana_client, mock_solana_dependencies):
    """Test getting SOL balance."""
    balance = await solana_client.get_balance("SOL")
    assert balance == 1.0  # 1 SOL


@pytest.mark.asyncio
async def test_get_balance_token(solana_client, mock_solana_dependencies):
    """Test getting SPL token balance."""
    balance = await solana_client.get_balance("TokenMintAddress123")
    assert balance == 1.0  # Assuming 9 decimals for the token


@pytest.mark.asyncio
async def test_execute_transaction(solana_client, mock_transaction, mock_solana_dependencies):
    """Test executing a transaction."""
    tx_params = {
        "transaction": mock_transaction,
        "wait_for_confirmation": True
    }
    
    result = await solana_client.execute_transaction(tx_params)
    assert result["tx_hash"] == "TransactionSignature123"
    assert result["status"] == "success"


@pytest.mark.asyncio
async def test_wait_for_transaction(solana_client, mock_solana_dependencies):
    """Test waiting for a transaction."""
    result = await solana_client.wait_for_transaction("TransactionSignature123")
    assert result["confirmed"] is True
    assert result["slot"] == 12345678


@pytest.mark.asyncio
async def test_get_transaction_status(solana_client, mock_solana_dependencies):
    """Test getting transaction status."""
    result = await solana_client.get_transaction_status("TransactionSignature123")
    assert result["status"] == "finalized"
    assert result["confirmed"] is True
    assert result["slot"] == 12345678 