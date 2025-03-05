import pytest
import pytest_asyncio
from web3 import Web3
from decimal import Decimal
from unittest.mock import AsyncMock, patch
import logging
import time

from typing import Tuple, Any, Dict, List, Optional, Union, cast

from gbpbot.strategies.mev import MEVStrategy
from gbpbot.core.blockchain import BlockchainClient
from gbpbot.core.mempool_scanner import MempoolScanner

# Configuration du logging pour les tests
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@pytest_asyncio.fixture
async def setup_test_environment() -> Tuple[Any, AsyncMock]:
    """Prépare l'environnement de test pour le MEV"""
    # Créer un mock du BlockchainClient
    blockchain_mock = AsyncMock(spec=BlockchainClient)
    blockchain_mock.simulation_mode = True
    blockchain_mock.web3 = Web3()
    
    # Configurer les tokens de test
    blockchain_mock.tokens = {
        "WAVAX": "0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7",
        "USDC": "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E"
    }
    
    blockchain_mock.token_addresses = {v: k for k, v in blockchain_mock.tokens.items()}
    
    # Mock du MempoolScanner
    mempool_mock = AsyncMock(spec=MempoolScanner)
    
    # Créer une instance de MEVStrategy avec les mocks
    strategy = MEVStrategy(blockchain_mock, mempool_mock)
    strategy.min_profit = 0.5  # 0.5%
    strategy.max_gas_price = 100  # 100 GWEI
    
    return strategy, blockchain_mock, mempool_mock

class TestMEVStrategy:
    """Tests unitaires pour MEVStrategy"""
    
    @pytest.mark.asyncio
    async def test_sandwich_attack(self, setup_test_environment: Any) -> None:
        """Test de la détection des opportunités sandwich"""
        strategy, blockchain, mempool = setup_test_environment
        
        # Mock d'une transaction dans le mempool
        target_tx = {
            "hash": "0xabcdef1234567890",
            "from": "0x1111111111111111111111111111111111111111",
            "to": "0x2222222222222222222222222222222222222222",
            "value": Web3.to_wei(10, "ether"),
            "gasPrice": Web3.to_wei(50, "gwei"),
            "input": "0x..."  # Données de swap
        }
        
        # Mock de l'analyse de la transaction
        with patch.object(strategy, '_analyze_swap_tx', return_value={
            "token_in": blockchain.tokens["WAVAX"],  # type: ignore
            "token_out": blockchain.tokens["USDC"],  # type: ignore
            "amount_in": Web3.to_wei(10, "ether"),
            "min_amount_out": Web3.to_wei(1000, "ether"),
            "path": [blockchain.tokens["WAVAX"], blockchain.tokens["USDC"]]  # type: ignore
        }):
            opportunity = await strategy.find_sandwich_opportunity(target_tx)
            
            assert opportunity is not None
            assert "front_tx" in opportunity
            assert "back_tx" in opportunity
            assert opportunity["estimated_profit"] > 0
            
    @pytest.mark.asyncio
    async def test_frontrun_detection(self, setup_test_environment: Any) -> None:
        """Test de la détection du frontrunning"""
        strategy, blockchain, mempool = setup_test_environment
        
        # Mock des transactions dans le mempool
        pending_txs = [
            {
                "hash": "0x111...",
                "gasPrice": Web3.to_wei(40, "gwei"),
                "input": "0x..."  # Données de swap AVAX -> USDC
            },
            {
                "hash": "0x222...",
                "gasPrice": Web3.to_wei(45, "gwei"),
                "input": "0x..."  # Données de swap USDC -> AVAX
            }
        ]
        
        mempool.get_pending_transactions.return_value = pending_txs
        
        # Test de détection d'opportunité de frontrun
        opportunities = await strategy.scan_frontrun_opportunities()
        
        assert len(opportunities) > 0
        for opp in opportunities:
            assert "target_tx" in opp
            assert "front_tx" in opp
            assert opp["profit_estimate"] > strategy.min_profit
            
    @pytest.mark.asyncio
    async def test_backrun_detection(self, setup_test_environment: Any) -> None:
        """Test de la détection du backrunning"""
        strategy, blockchain, mempool = setup_test_environment
        
        # Mock d'une grosse transaction qui pourrait créer un déséquilibre
        large_swap = {
            "hash": "0x333...",
            "gasPrice": Web3.to_wei(60, "gwei"),
            "input": "0x...",  # Données de swap pour un gros montant
            "value": Web3.to_wei(1000, "ether")
        }
        
        with patch.object(strategy, '_analyze_price_impact', return_value={
            "price_before": 100,
            "price_after": 95,
            "potential_profit": 2.5
        }):
            opportunity = await strategy.find_backrun_opportunity(large_swap)
            
            assert opportunity is not None
            assert "target_tx" in opportunity
            assert "back_tx" in opportunity
            assert opportunity["profit_estimate"] > strategy.min_profit
            
    @pytest.mark.asyncio
    async def test_gas_optimization(self, setup_test_environment: Any) -> None:
        """Test de l'optimisation du gas"""
        strategy, blockchain, mempool = setup_test_environment
        
        # Test de calcul du gas optimal
        base_gas = Web3.to_wei(50, "gwei")
        
        # Mock des données de congestion réseau
        with patch.object(strategy, '_get_network_congestion', return_value=0.7):
            optimal_gas = await strategy.calculate_optimal_gas(base_gas)
            
            assert optimal_gas > base_gas  # Le gas devrait être plus élevé en cas de congestion
            max_gas_wei = Web3.to_wei(strategy.max_gas_price, "gwei")
            assert optimal_gas <= max_gas_wei  # Mais ne pas dépasser le maximum
            
            # Test avec congestion faible
            with patch.object(strategy, '_get_network_congestion', return_value=0.2):
                optimal_gas_low = await strategy.calculate_optimal_gas(base_gas)
                assert optimal_gas_low <= optimal_gas  # Le gas devrait être plus bas 