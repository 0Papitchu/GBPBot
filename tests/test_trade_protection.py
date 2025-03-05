#!/usr/bin/env python3
"""
Tests unitaires pour le module TradeProtection.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from decimal import Decimal

from gbpbot.core.security.trade_protection import TradeProtection

class TestTradeProtection:
    """Tests pour la classe TradeProtection."""

    @pytest.fixture
    def mock_web3(self):
        """Crée un mock de l'objet Web3."""
        mock = MagicMock()
        mock.eth.get_block_number = MagicMock(return_value=12345)
        mock.eth.get_transaction_count = MagicMock(return_value=10)
        return mock

    @pytest.fixture
    def mock_config(self):
        """Crée un mock de la configuration."""
        return {
            "security": {
                "stop_loss": 0.05,
                "take_profit": 0.03,
                "max_slippage": 0.01,
                "max_gas_price": 100,
                "min_priority_fee": 1,
                "base_fee_multiplier": 1.2
            }
        }

    @pytest.fixture
    def trade_protection(self, mock_web3, mock_config):
        """Crée une instance de TradeProtection avec des mocks."""
        with patch('asyncio.create_task'):
            return TradeProtection(mock_config, mock_web3)

    def test_init(self, trade_protection, mock_config):
        """Teste l'initialisation de TradeProtection."""
        assert trade_protection.stop_loss == mock_config["security"]["stop_loss"]
        assert trade_protection.take_profit == mock_config["security"]["take_profit"]
        assert trade_protection.max_slippage == mock_config["security"]["max_slippage"]
        assert isinstance(trade_protection.positions, dict)
        assert trade_protection.monitoring_task is not None

    @pytest.mark.asyncio
    async def test_add_position(self, trade_protection):
        """Teste l'ajout d'une position."""
        # Arrange
        position_id = "test_position"
        entry_price = Decimal("100.0")
        size = Decimal("1.0")
        
        # Act
        trade_protection.add_position(position_id, entry_price, size)
        
        # Assert
        assert position_id in trade_protection.positions
        assert trade_protection.positions[position_id]["entry_price"] == entry_price
        assert trade_protection.positions[position_id]["size"] == size
        assert trade_protection.positions[position_id]["stop_loss_price"] == entry_price * (1 - trade_protection.stop_loss)
        assert trade_protection.positions[position_id]["take_profit_price"] == entry_price * (1 + trade_protection.take_profit)
        assert "current_price" in trade_protection.positions[position_id]
        assert "status" in trade_protection.positions[position_id]

    @pytest.mark.asyncio
    async def test_update_position_price(self, trade_protection):
        """Teste la mise à jour du prix d'une position."""
        # Arrange
        position_id = "test_position"
        entry_price = Decimal("100.0")
        size = Decimal("1.0")
        new_price = Decimal("105.0")
        
        trade_protection.add_position(position_id, entry_price, size)
        trade_protection._check_exit_conditions = AsyncMock()
        
        # Act
        await trade_protection.update_position_price(position_id, new_price)
        
        # Assert
        assert trade_protection.positions[position_id]["current_price"] == new_price
        trade_protection._check_exit_conditions.assert_called_once_with(position_id)

    @pytest.mark.asyncio
    async def test_remove_position(self, trade_protection):
        """Teste la suppression d'une position."""
        # Arrange
        position_id = "test_position"
        entry_price = Decimal("100.0")
        size = Decimal("1.0")
        
        trade_protection.add_position(position_id, entry_price, size)
        assert position_id in trade_protection.positions
        
        # Act
        trade_protection.remove_position(position_id)
        
        # Assert
        assert position_id not in trade_protection.positions

    @pytest.mark.asyncio
    async def test_check_exit_conditions_stop_loss(self, trade_protection):
        """Teste la vérification des conditions de sortie (stop loss)."""
        # Arrange
        position_id = "test_position"
        entry_price = Decimal("100.0")
        size = Decimal("1.0")
        stop_loss_price = entry_price * (1 - trade_protection.stop_loss)
        
        trade_protection.add_position(position_id, entry_price, size)
        
        # Simuler un prix en dessous du stop loss
        trade_protection.positions[position_id]["current_price"] = stop_loss_price - Decimal("1.0")
        
        # Act
        result = await trade_protection._check_exit_conditions(position_id)
        
        # Assert
        assert result is True
        assert trade_protection.positions[position_id]["status"] == "stop_loss"

    @pytest.mark.asyncio
    async def test_check_exit_conditions_take_profit(self, trade_protection):
        """Teste la vérification des conditions de sortie (take profit)."""
        # Arrange
        position_id = "test_position"
        entry_price = Decimal("100.0")
        size = Decimal("1.0")
        take_profit_price = entry_price * (1 + trade_protection.take_profit)
        
        trade_protection.add_position(position_id, entry_price, size)
        
        # Simuler un prix au-dessus du take profit
        trade_protection.positions[position_id]["current_price"] = take_profit_price + Decimal("1.0")
        
        # Act
        result = await trade_protection._check_exit_conditions(position_id)
        
        # Assert
        assert result is True
        assert trade_protection.positions[position_id]["status"] == "take_profit"

    @pytest.mark.asyncio
    async def test_check_exit_conditions_no_exit(self, trade_protection):
        """Teste la vérification des conditions de sortie (pas de sortie)."""
        # Arrange
        position_id = "test_position"
        entry_price = Decimal("100.0")
        size = Decimal("1.0")
        stop_loss_price = entry_price * (1 - trade_protection.stop_loss)
        take_profit_price = entry_price * (1 + trade_protection.take_profit)
        
        trade_protection.add_position(position_id, entry_price, size)
        
        # Simuler un prix entre stop loss et take profit
        trade_protection.positions[position_id]["current_price"] = entry_price
        
        # Act
        result = await trade_protection._check_exit_conditions(position_id)
        
        # Assert
        assert result is False
        assert trade_protection.positions[position_id]["status"] == "active"

    @pytest.mark.asyncio
    async def test_check_mev_protection(self, trade_protection):
        """Teste la protection contre les attaques MEV."""
        # Arrange
        tx = {
            "from": "0x1234567890123456789012345678901234567890",
            "to": "0x0987654321098765432109876543210987654321",
            "value": 1000000000000000000,
            "gas": 200000,
            "maxFeePerGas": 50000000000,
            "maxPriorityFeePerGas": 2000000000,
            "nonce": 10
        }
        
        trade_protection._calculate_optimal_gas = MagicMock(return_value=(60000000000, 3000000000))
        
        # Act
        result = trade_protection.check_mev_protection(tx)
        
        # Assert
        assert result["maxFeePerGas"] == 60000000000
        assert result["maxPriorityFeePerGas"] == 3000000000
        assert "validity" in result
        assert result["gas"] >= tx["gas"]

    @pytest.mark.asyncio
    async def test_get_position_status(self, trade_protection):
        """Teste la récupération du statut d'une position."""
        # Arrange
        position_id = "test_position"
        entry_price = Decimal("100.0")
        size = Decimal("1.0")
        current_price = Decimal("102.0")
        
        trade_protection.add_position(position_id, entry_price, size)
        trade_protection.positions[position_id]["current_price"] = current_price
        trade_protection.positions[position_id]["status"] = "active"
        
        # Act
        status = trade_protection.get_position_status(position_id)
        
        # Assert
        assert status["position_id"] == position_id
        assert status["entry_price"] == entry_price
        assert status["current_price"] == current_price
        assert status["stop_loss_price"] == trade_protection.positions[position_id]["stop_loss_price"]
        assert status["take_profit_price"] == trade_protection.positions[position_id]["take_profit_price"]
        assert status["status"] == "active"
        assert "profit_loss" in status

    @pytest.mark.asyncio
    async def test_get_position_status_not_found(self, trade_protection):
        """Teste la récupération du statut d'une position inexistante."""
        # Act & Assert
        with pytest.raises(KeyError):
            trade_protection.get_position_status("non_existent_position")

    @pytest.mark.asyncio
    async def test_monitor_positions(self, trade_protection):
        """Teste le monitoring des positions."""
        # Arrange
        position_id = "test_position"
        entry_price = Decimal("100.0")
        size = Decimal("1.0")
        
        trade_protection.add_position(position_id, entry_price, size)
        trade_protection._check_exit_conditions = AsyncMock(return_value=False)
        
        # Simuler une exception dans la boucle pour qu'elle se termine
        def side_effect(*args, **kwargs):
            trade_protection._running = False
            return False
            
        trade_protection._check_exit_conditions.side_effect = side_effect
        
        # Act
        await trade_protection._monitor_positions()
        
        # Assert
        trade_protection._check_exit_conditions.assert_called_once_with(position_id) 