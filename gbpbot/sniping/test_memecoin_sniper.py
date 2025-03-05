#!/usr/bin/env python3
"""
Test script for validating the SolanaMemecoinSniper implementation
"""

import os
import sys
import asyncio
import unittest
import json
from unittest.mock import MagicMock, patch, AsyncMock
from typing import Dict, List, Optional

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from gbpbot.sniping.memecoin_sniper import SolanaMemecoinSniper
from gbpbot.core.transaction.transaction_status import TransactionStatus

class TestSolanaMemecoinSniper(unittest.TestCase):
    """Test case for SolanaMemecoinSniper"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create a minimal config for testing
        self.test_config = {
            "solana": {
                "network": "mainnet-beta",
                "rpc": {
                    "providers": [
                        {
                            "name": "Test RPC",
                            "url": "https://test-rpc.example.com",
                            "weight": 1,
                            "type": "public"
                        }
                    ]
                },
                "wallet": {
                    "private_key": "test_private_key",
                    "use_burner_wallets": False
                },
                "tokens": {
                    "usdc": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
                },
                "dex": {
                    "jupiter": {
                        "api_url": "https://quote-api.jup.ag/v6",
                        "default_slippage": 0.5
                    }
                },
                "sniping": {
                    "trade_settings": {
                        "default_slippage": 0.5,
                        "min_liquidity_usd": 50000,
                        "min_volume_usd": 100000
                    },
                    "gas_priority": {
                        "default": "high"
                    },
                    "profitability": {
                        "take_profit_levels": [
                            {"multiplier": 2.0, "percentage": 50},
                            {"multiplier": 5.0, "percentage": 100}
                        ],
                        "stop_loss": {
                            "enabled": True,
                            "percentage": 30
                        }
                    }
                },
                "security": {
                    "max_allocation_per_token_usd": 100
                }
            }
        }
        
        # Save test config to a temporary file
        self.config_path = "temp_test_config.json"
        with open(self.config_path, "w") as f:
            json.dump(self.test_config, f)
        
        # Create patches for dependencies
        self.client_mock = AsyncMock()
        self.detector_mock = AsyncMock()
        self.wallet_tracker_mock = AsyncMock()
        self.dex_adapter_mock = AsyncMock()
        
        # Configure client mock
        self.client_mock.wallet.public_key = "test_wallet_address"
        
        # Configure detector mock
        self.detector_mock.get_detected_tokens.return_value = []
        self.detector_mock.on = MagicMock()
        
        # Configure wallet tracker mock
        self.wallet_tracker_mock.check_smart_money_involvement.return_value = False
        self.wallet_tracker_mock.record_transaction.return_value = True
        
        # Configure dex adapter mock
        self.dex_adapter_mock.get_token_info.return_value = {
            "symbol": "TEST",
            "name": "Test Token",
            "price_usd": 0.00001,
            "liquidity": {"usd": 100000},
            "volume": {"h24": 150000},
            "price_change": {"h24": 20},
            "age_hours": 5,
            "holders": 100
        }
        
        # Apply patches
        self.patches = [
            patch("gbpbot.sniping.memecoin_sniper.SolanaBlockchainClient", return_value=self.client_mock),
            patch("gbpbot.sniping.memecoin_sniper.MemecoinDetector", return_value=self.detector_mock),
            patch("gbpbot.sniping.memecoin_sniper.WalletTracker", return_value=self.wallet_tracker_mock),
            patch("gbpbot.sniping.memecoin_sniper.DexScreenerAdapter", return_value=self.dex_adapter_mock)
        ]
        
        for p in self.patches:
            p.start()
    
    def tearDown(self):
        """Tear down test fixtures"""
        # Stop all patches
        for p in self.patches:
            p.stop()
        
        # Remove temporary config file
        if os.path.exists(self.config_path):
            os.remove(self.config_path)
    
    async def test_initialization(self):
        """Test initialization of the sniper"""
        sniper = SolanaMemecoinSniper(self.config_path)
        
        self.assertIsNotNone(sniper)
        self.assertEqual(sniper.is_running, False)
        self.assertEqual(sniper.paused, False)
        self.assertDictEqual(sniper.active_positions, {})
        self.assertDictEqual(sniper.pending_transactions, {})
    
    async def test_start_stop(self):
        """Test starting and stopping the sniper"""
        sniper = SolanaMemecoinSniper(self.config_path)
        
        # Start the sniper
        await sniper.start()
        
        self.assertEqual(sniper.is_running, True)
        self.assertEqual(sniper.paused, False)
        self.client_mock.connect.assert_called_once()
        self.detector_mock.start.assert_called_once()
        
        # Stop the sniper
        await sniper.stop()
        
        self.assertEqual(sniper.is_running, False)
        self.detector_mock.stop.assert_called_once()
    
    async def test_opportunity_scoring(self):
        """Test token opportunity scoring"""
        sniper = SolanaMemecoinSniper(self.config_path)
        
        # Test token data
        token = {
            "address": "test_token_address",
            "symbol": "TEST",
            "name": "Test Token"
        }
        
        # Test with regular token
        token_info = {
            "liquidity": {"usd": 100000},
            "volume": {"h24": 150000},
            "price_change": {"h24": 20},
            "age_hours": 5,
            "holders": 100
        }
        score = sniper._calculate_opportunity_score(token, token_info, False)
        self.assertTrue(50 <= score <= 70)  # Score should be reasonable
        
        # Test with smart money involvement
        score_smart_money = sniper._calculate_opportunity_score(token, token_info, True)
        self.assertTrue(score_smart_money > score)  # Smart money should boost score
        
        # Test with low liquidity
        low_liquidity_info = token_info.copy()
        low_liquidity_info["liquidity"] = {"usd": 10000}
        score_low_liquidity = sniper._calculate_opportunity_score(token, low_liquidity_info, False)
        self.assertTrue(score_low_liquidity < score)  # Low liquidity should reduce score
        
        # Test with very new token
        new_token_info = token_info.copy()
        new_token_info["age_hours"] = 0.5
        score_new_token = sniper._calculate_opportunity_score(token, new_token_info, False)
        self.assertTrue(score_new_token > score)  # New tokens should have higher score
    
    async def test_execute_snipe(self):
        """Test executing a token snipe"""
        sniper = SolanaMemecoinSniper(self.config_path)
        
        # Mock analyze_contract return value
        self.client_mock.analyze_contract.return_value = {
            "is_honeypot": False,
            "risk_level": "medium",
            "liquidity": {"usd": 100000}
        }
        
        # Mock execute_swap return value
        self.client_mock.execute_swap.return_value = {
            "transaction_hash": "test_tx_hash",
            "success": True
        }
        
        # Test token data
        token = {
            "address": "test_token_address",
            "symbol": "TEST",
            "name": "Test Token"
        }
        
        token_info = {
            "price_usd": 0.00001,
            "liquidity": {"usd": 100000},
            "volume": {"h24": 150000},
            "price_change": {"h24": 20},
            "age_hours": 5,
            "holders": 100
        }
        
        analysis = {
            "is_honeypot": False,
            "risk_level": "medium",
            "liquidity": {"usd": 100000}
        }
        
        # Execute snipe
        await sniper._execute_snipe(token, token_info, analysis, 80)
        
        # Verify execute_swap was called
        self.client_mock.execute_swap.assert_called_once()
        
        # Verify token was added to active positions
        self.assertTrue(token["address"] in sniper.active_positions)
        
        # Verify transaction was added to pending transactions
        self.assertTrue("test_tx_hash" in sniper.pending_transactions)
        
        # Verify wallet tracker was called
        self.wallet_tracker_mock.record_transaction.assert_called_once()
    
    async def test_handle_confirmed_transaction(self):
        """Test handling confirmed transactions"""
        sniper = SolanaMemecoinSniper(self.config_path)
        
        # Set up active position
        token_address = "test_token_address"
        sniper.active_positions[token_address] = {
            "symbol": "TEST",
            "entry_transaction": "test_tx_hash",
            "entry_price_usd": 0.00001,
            "entry_time": "2023-01-01T00:00:00",
            "position_size_usd": 100,
            "amount_in": 100,
            "token_amount": 0,
            "current_price_usd": 0.00001,
            "current_value_usd": 100,
            "profit_loss_pct": 0,
            "take_profit_targets": [],
            "stop_loss_price": 0.000007,
            "score": 80,
            "last_updated": 123456789
        }
        
        # Set up pending transaction
        tx_hash = "test_tx_hash"
        sniper.pending_transactions[tx_hash] = {
            "type": "buy",
            "token_address": token_address,
            "symbol": "TEST",
            "amount_in": 100,
            "timestamp": 123456789,
            "timeout": 60,
            "score": 80,
            "entry_time": "2023-01-01T00:00:00"
        }
        
        # Mock get_token_balance return value
        self.client_mock.get_token_balance.return_value = 10000000
        
        # Set up transaction status
        tx_status = {
            "status": TransactionStatus.CONFIRMED,
            "value_out": 0
        }
        
        # Handle confirmed transaction
        await sniper._handle_confirmed_transaction(tx_hash, sniper.pending_transactions[tx_hash], tx_status)
        
        # Verify token amount was updated
        self.assertEqual(sniper.active_positions[token_address]["token_amount"], 10000000)
        
        # Verify successful trades counter was incremented
        self.assertEqual(sniper.successful_trades, 1)
    
    async def test_evaluate_token_for_sniping(self):
        """Test evaluating a token for sniping"""
        sniper = SolanaMemecoinSniper(self.config_path)
        
        # Mock functions
        self.wallet_tracker_mock.check_smart_money_involvement.return_value = True
        self.client_mock.analyze_contract.return_value = {
            "is_honeypot": False,
            "risk_level": "low",
            "liquidity": {"usd": 200000}
        }
        self.client_mock.execute_swap.return_value = {
            "transaction_hash": "test_tx_hash",
            "success": True
        }
        
        # Test token
        token = {
            "address": "test_token_address",
            "symbol": "TEST",
            "name": "Test Token"
        }
        
        # Evaluate token
        await sniper._evaluate_token_for_sniping(token)
        
        # Verify functions were called
        self.dex_adapter_mock.get_token_info.assert_called_once()
        self.wallet_tracker_mock.check_smart_money_involvement.assert_called_once()
        self.client_mock.analyze_contract.assert_called_once()
        
        # Since we mocked a good token with smart money involvement,
        # the score should be high and snipe should be executed
        self.client_mock.execute_swap.assert_called_once()
    
    async def test_position_size_calculation(self):
        """Test position size calculation logic"""
        sniper = SolanaMemecoinSniper(self.config_path)
        
        # Test different score and risk levels
        size_high_score_low_risk = sniper._calculate_position_size(95, "low")
        size_high_score_high_risk = sniper._calculate_position_size(95, "high")
        size_medium_score = sniper._calculate_position_size(75, "medium")
        size_low_score = sniper._calculate_position_size(55, "low")
        
        # Verify size relationships
        self.assertTrue(size_high_score_low_risk > size_high_score_high_risk)
        self.assertTrue(size_high_score_low_risk > size_medium_score)
        self.assertTrue(size_medium_score > size_low_score)
        
        # Verify minimum size constraint
        very_low_score = sniper._calculate_position_size(10, "high")
        self.assertTrue(very_low_score >= 10)  # Minimum should be $10


async def run_tests():
    """Run all tests asynchronously"""
    test_cases = [
        TestSolanaMemecoinSniper("test_initialization"),
        TestSolanaMemecoinSniper("test_start_stop"),
        TestSolanaMemecoinSniper("test_opportunity_scoring"),
        TestSolanaMemecoinSniper("test_execute_snipe"),
        TestSolanaMemecoinSniper("test_handle_confirmed_transaction"),
        TestSolanaMemecoinSniper("test_evaluate_token_for_sniping"),
        TestSolanaMemecoinSniper("test_position_size_calculation")
    ]
    
    for test_case in test_cases:
        print(f"Running {test_case._testMethodName}...")
        await getattr(test_case, test_case._testMethodName)()
        print(f"{test_case._testMethodName} - PASSED")


if __name__ == "__main__":
    asyncio.run(run_tests()) 