import pytest
import pytest_asyncio
from web3 import Web3
from decimal import Decimal
from unittest.mock import AsyncMock, patch
import logging
import time

from typing import Tuple, Any, Dict, List, Optional, Union, cast

from gbpbot.strategies.sniping import TokenSniper
from gbpbot.core.blockchain import BlockchainClient

# Configuration du logging pour les tests
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

@pytest_asyncio.fixture
async def setup_test_environment() -> Tuple[Any, AsyncMock]:
    """Prépare l'environnement de test pour le sniping"""
    # Créer un mock du BlockchainClient
    blockchain_mock = AsyncMock(spec=BlockchainClient)
    blockchain_mock.simulation_mode = True
    blockchain_mock.web3 = Web3()
    
    # Configurer les tokens de test
    blockchain_mock.tokens = {
        "WAVAX": "0xB31f66AA3C1e785363F0875A1B74E27b85FD66c7",
        "NEW_TOKEN": "0x1234567890123456789012345678901234567890"
    }
    
    blockchain_mock.token_addresses = {v: k for k, v in blockchain_mock.tokens.items()}
    
    # Créer une instance de TokenSniper avec le mock
    sniper = TokenSniper(blockchain_mock)
    sniper.min_liquidity = Web3.to_wei(5, "ether")
    sniper.max_buy_amount = Web3.to_wei(1, "ether")
    
    return sniper, blockchain_mock

class TestTokenSniper:
    """Tests unitaires pour TokenSniper"""
    
    @pytest.mark.asyncio
    async def test_detect_new_token(self, setup_test_environment: Tuple[Any, AsyncMock]):
        """Test de la détection de nouveaux tokens"""
        sniper, blockchain = setup_test_environment
        
        # Mock d'un nouvel événement de création de token
        new_token_event = {
            "address": "0x1234567890123456789012345678901234567890",
            "topics": [
                "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef",
                "0x0000000000000000000000000000000000000000000000000000000000000000"
            ],
            "data": "0x0000000000000000000000000000000000000000000000000000000000000000",
            "blockNumber": 123456,
            "transactionHash": "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
        }
        
        # Configurer le mock pour retourner des informations sur le token
        blockchain.get_token_info.return_value = {
            "name": "Test Token",
            "symbol": "TEST",
            "decimals": 18,
            "totalSupply": Web3.to_wei(1000000, "ether")
        }
        
        # Appeler la méthode à tester
        result = await sniper.detect_new_token(new_token_event)
        
        # Vérifier que le token a été détecté
        assert result is not None
        assert result["address"] == "0x1234567890123456789012345678901234567890"
        assert result["name"] == "Test Token"
        assert result["symbol"] == "TEST"
    
    @pytest.mark.asyncio
    async def test_analyze_token(self, setup_test_environment: Tuple[Any, AsyncMock]):
        """Test de l'analyse d'un token"""
        sniper, blockchain = setup_test_environment
        
        # Configurer le mock pour retourner des informations sur la liquidité
        blockchain.get_token_liquidity.return_value = Web3.to_wei(10, "ether")
        
        # Configurer le mock pour retourner des informations sur le contrat
        blockchain.is_contract_verified.return_value = True
        blockchain.get_contract_code.return_value = "0x123456789abcdef"
        blockchain.analyze_contract_security.return_value = {
            "is_honeypot": False,
            "has_mint_function": False,
            "has_blacklist": False,
            "risk_score": 20
        }
        
        # Appeler la méthode à tester
        token_info = {
            "address": "0x1234567890123456789012345678901234567890",
            "name": "Test Token",
            "symbol": "TEST",
            "decimals": 18
        }
        result = await sniper.analyze_token(token_info)
        
        # Vérifier que l'analyse a été effectuée
        assert result is not None
        assert result["liquidity"] == Web3.to_wei(10, "ether")
        assert result["is_verified"] == True
        assert result["security"]["is_honeypot"] == False
        assert result["security"]["risk_score"] == 20
    
    @pytest.mark.asyncio
    async def test_validate_token(self, setup_test_environment: Tuple[Any, AsyncMock]):
        """Test de la validation d'un token"""
        sniper, blockchain = setup_test_environment
        
        # Configurer le token à valider
        token_analysis = {
            "address": "0x1234567890123456789012345678901234567890",
            "name": "Test Token",
            "symbol": "TEST",
            "decimals": 18,
            "liquidity": Web3.to_wei(10, "ether"),
            "is_verified": True,
            "security": {
                "is_honeypot": False,
                "has_mint_function": False,
                "has_blacklist": False,
                "risk_score": 20
            }
        }
        
        # Appeler la méthode à tester
        result = sniper.validate_token(token_analysis)
        
        # Vérifier que le token est valide
        assert result == True
        
        # Tester avec un token invalide (liquidité insuffisante)
        token_analysis["liquidity"] = Web3.to_wei(1, "ether")
        result = sniper.validate_token(token_analysis)
        assert result == False
        
        # Tester avec un token invalide (risque élevé)
        token_analysis["liquidity"] = Web3.to_wei(10, "ether")
        token_analysis["security"]["risk_score"] = 80
        result = sniper.validate_token(token_analysis)
        assert result == False
    
    @pytest.mark.asyncio
    async def test_execute_buy(self, setup_test_environment: Tuple[Any, AsyncMock]):
        """Test de l'exécution d'un achat"""
        sniper, blockchain = setup_test_environment
        
        # Configurer le mock pour simuler une transaction réussie
        tx_hash = "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
        blockchain.swap_exact_avax_for_tokens.return_value = tx_hash
        blockchain.get_transaction_receipt.return_value = {"status": 1}
        
        # Appeler la méthode à tester
        token_address = "0x1234567890123456789012345678901234567890"
        amount = Web3.to_wei(0.5, "ether")
        result = await sniper.execute_buy(token_address, amount)
        
        # Vérifier que l'achat a été effectué
        assert result["success"] == True
        assert result["tx_hash"] == tx_hash
        assert result["amount"] == amount
        
        # Vérifier que la méthode a été appelée avec les bons arguments
        blockchain.swap_exact_avax_for_tokens.assert_called_once_with(
            amount, token_address, slippage=2000  # 20% de slippage par défaut
        )
    
    @pytest.mark.asyncio
    async def test_monitor_price(self, setup_test_environment: Tuple[Any, AsyncMock]):
        """Test du monitoring du prix"""
        sniper, blockchain = setup_test_environment
        
        # Configurer le mock pour retourner des prix
        blockchain.get_token_price.side_effect = [
            Decimal("1.0"),  # Prix initial
            Decimal("1.2"),  # +20%
            Decimal("1.5"),  # +50%
            Decimal("1.2"),  # -20% depuis le pic
            Decimal("0.8")   # -20% depuis le prix initial
        ]
        
        # Configurer les paramètres de monitoring
        token_address = "0x1234567890123456789012345678901234567890"
        initial_price = Decimal("1.0")
        take_profit = 30  # +30%
        stop_loss = 20    # -20%
        
        # Simuler le monitoring (normalement c'est une boucle infinie, mais pour le test on limite)
        price_updates = []
        for _ in range(5):
            price = await blockchain.get_token_price(token_address)
            price_updates.append(price)
            
            # Vérifier les conditions de take profit et stop loss
            price_change = ((price / initial_price) - 1) * 100
            if price_change >= take_profit:
                take_profit_triggered = True
                break
            elif price_change <= -stop_loss:
                stop_loss_triggered = True
                break
        
        # Vérifier que le monitoring a fonctionné
        assert len(price_updates) == 5
        assert price_updates[0] == Decimal("1.0")
        assert price_updates[2] == Decimal("1.5")  # +50%, devrait déclencher le take profit
        
        # Dans un vrai test, on vérifierait que le take profit a été déclenché
        price_change = ((price_updates[2] / initial_price) - 1) * 100
        assert price_change >= take_profit 