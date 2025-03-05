"""
Tests for the BlockchainClientFactory.
"""

import pytest
from unittest.mock import patch, MagicMock

from gbpbot.core.blockchain.base import BlockchainClientFactory
from gbpbot.core.blockchain.ethereum import EthereumClient
from gbpbot.core.blockchain.solana import SolanaClient
from gbpbot.utils.exceptions import UnsupportedBlockchainError


@pytest.fixture
def config():
    """Fixture for blockchain client configuration."""
    return {
        "rpc_url": "https://example.com",
        "private_key": "0x123456789abcdef"
    }


def test_get_ethereum_client(config):
    """Test getting an Ethereum client."""
    with patch("gbpbot.core.blockchain.base.EthereumClient") as mock_eth_client:
        mock_instance = MagicMock()
        mock_eth_client.return_value = mock_instance
        
        client = BlockchainClientFactory.get_client("ethereum", config)
        
        mock_eth_client.assert_called_once_with(config)
        assert client == mock_instance


def test_get_solana_client(config):
    """Test getting a Solana client."""
    with patch("gbpbot.core.blockchain.base.SolanaClient") as mock_solana_client:
        mock_instance = MagicMock()
        mock_solana_client.return_value = mock_instance
        
        client = BlockchainClientFactory.get_client("solana", config)
        
        mock_solana_client.assert_called_once_with(config)
        assert client == mock_instance


def test_get_evm_compatible_clients(config):
    """Test getting clients for EVM-compatible chains."""
    with patch("gbpbot.core.blockchain.base.EthereumClient") as mock_eth_client:
        mock_instance = MagicMock()
        mock_eth_client.return_value = mock_instance
        
        # Test all EVM-compatible chains
        for chain in ["polygon", "avalanche", "arbitrum", "optimism", "bsc"]:
            client = BlockchainClientFactory.get_client(chain, config)
            
            mock_eth_client.assert_called_with(config)
            assert client == mock_instance


def test_unsupported_blockchain(config):
    """Test getting a client for an unsupported blockchain."""
    with pytest.raises(UnsupportedBlockchainError):
        BlockchainClientFactory.get_client("unsupported_chain", config)


def test_case_insensitivity(config):
    """Test that blockchain type is case-insensitive."""
    with patch("gbpbot.core.blockchain.base.EthereumClient") as mock_eth_client:
        mock_instance = MagicMock()
        mock_eth_client.return_value = mock_instance
        
        # Test with different cases
        for chain_type in ["ETHEREUM", "Ethereum", "ethereum"]:
            client = BlockchainClientFactory.get_client(chain_type, config)
            
            mock_eth_client.assert_called_with(config)
            assert client == mock_instance 