import unittest
import asyncio
import os
import sys
from unittest.mock import patch, MagicMock, AsyncMock
from typing import Dict, List, Any

# Ensure gbpbot can be imported
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from gbpbot.core.blockchain_factory import SonicBlockchainClient, BlockchainFactory


class TestSonicBlockchainClient(unittest.TestCase):
    """Test cases for the SonicBlockchainClient class"""

    def setUp(self):
        """Set up test fixtures before each test method"""
        # Create a test configuration
        self.test_config = {
            "rpc": {
                "providers": {
                    "sonic": {
                        "mainnet": [
                            {"name": "TestRPC", "url": "https://test-sonic-rpc.example.com", "weight": 1}
                        ]
                    }
                },
                "timeout": 30
            },
            "tokens": {
                "icp": "0x123456789abcdef123456789abcdef123456789a",
                "wicp": "0x987654321fedcba987654321fedcba987654321",
                "whitelist": [
                    "0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                    "0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
                ]
            },
            "dex": {
                "sonic": {
                    "router_address": "0xcccccccccccccccccccccccccccccccccccccccc",
                    "factory_address": "0xddddddddddddddddddddddddddddddddddddddd"
                }
            },
            "wallet": {
                "private_key": "0xprivatekeyfortest"
            },
            "notifications": {
                "enabled": False,
                "telegram": {
                    "enabled": False,
                    "bot_token": "",
                    "chat_id": ""
                },
                "discord": {
                    "enabled": False,
                    "webhook_url": ""
                }
            }
        }
        
        # Initialize the client with mocked web3
        with patch('gbpbot.core.blockchain_factory.Web3') as mock_web3_class:
            # Mock the Web3 instance
            self.mock_web3 = MagicMock()
            mock_web3_class.return_value = self.mock_web3
            
            # Mock the HTTPProvider
            mock_provider = MagicMock()
            mock_web3_class.HTTPProvider.return_value = mock_provider
            
            # Mock the is_connected method
            self.mock_web3.is_connected.return_value = True
            
            # Create the client instance
            self.client = SonicBlockchainClient(self.test_config)
            
            # Mock the account instance
            mock_account = MagicMock()
            mock_account.address = "0xTestWalletAddress"
            self.mock_web3.eth.account.from_key.return_value = mock_account
    
    async def async_setUp(self):
        """Async setup for tests that need it"""
        # Connect the client (with mocked connection)
        with patch('gbpbot.core.blockchain_factory.Web3') as mock_web3_class:
            # Ensure the mock returns our existing mock_web3
            mock_web3_class.return_value = self.mock_web3
            mock_web3_class.HTTPProvider.return_value = MagicMock()
            
            # Mock to_checksum_address to return the input
            self.mock_web3.to_checksum_address = lambda addr: addr
            
            # Run connect
            connected = await self.client.connect()
            self.assertTrue(connected)
    
    def test_initialization(self):
        """Test that the client initializes correctly"""
        self.assertIsInstance(self.client, SonicBlockchainClient)
        self.assertEqual(self.client.config, self.test_config)
        self.assertIsNone(self.client.wallet_address)  # Should be set during connect
        self.assertIsNone(self.client.private_key)     # Should be set during connect
        self.assertEqual(self.client.cache_expiry, 60)  # Default cache expiry
    
    def test_factory_creation(self):
        """Test that the factory creates the correct client type"""
        with patch('gbpbot.core.blockchain_factory.SonicBlockchainClient') as mock_sonic_client:
            BlockchainFactory.get_blockchain_client("sonic", self.test_config)
            mock_sonic_client.assert_called_once_with(self.test_config)
    
    @patch('gbpbot.core.blockchain_factory.Web3')
    def test_connect(self, mock_web3_class):
        """Test the connect method"""
        # Setup mocks
        mock_web3 = MagicMock()
        mock_web3_class.return_value = mock_web3
        mock_web3_class.HTTPProvider.return_value = MagicMock()
        mock_web3.is_connected.return_value = True
        
        mock_account = MagicMock()
        mock_account.address = "0xTestWalletAddress"
        mock_web3.eth.account.from_key.return_value = mock_account
        
        # Run the test asynchronously
        async def run_test():
            client = SonicBlockchainClient(self.test_config)
            connected = await client.connect()
            self.assertTrue(connected)
            self.assertIsNotNone(client.web3)
            mock_web3.is_connected.assert_called_once()
        
        asyncio.run(run_test())
    
    def test_load_token_addresses(self):
        """Test loading token addresses from configuration"""
        with patch('gbpbot.core.blockchain_factory.Web3') as mock_web3_class:
            # Mock the to_checksum_address method
            self.mock_web3.to_checksum_address = lambda addr: f"CHECKSUM_{addr}"
            
            # Initialize the client
            client = SonicBlockchainClient(self.test_config)
            client.web3 = self.mock_web3
            
            # Call the method
            client._load_token_addresses()
            
            # Verify results
            self.assertEqual(client.token_addresses["ICP"], f"CHECKSUM_{self.test_config['tokens']['icp']}")
            self.assertEqual(client.token_addresses["WICP"], f"CHECKSUM_{self.test_config['tokens']['wicp']}")
            self.assertEqual(len(client.token_addresses), 4)  # ICP, WICP, and 2 from whitelist
    
    async def test_get_token_price(self):
        """Test getting token price"""
        # Setup
        await self.async_setUp()
        
        # Mock token contract
        mock_token_contract = AsyncMock()
        mock_token_contract.functions.decimals.return_value.call.return_value = 18
        
        # Mock base token contract
        mock_base_contract = AsyncMock()
        mock_base_contract.functions.decimals.return_value.call.return_value = 18
        
        # Mock router contract
        mock_router = AsyncMock()
        mock_router.functions.getAmountsOut.return_value.call.return_value = [10**18, 2*10**18]  # 1:2 ratio
        
        # Setup contract calls
        self.mock_web3.eth.contract.side_effect = lambda address, abi: (
            mock_router if address == self.client.dex_router_address
            else mock_token_contract if address == "0xTOKEN"
            else mock_base_contract
        )
        
        # Call method
        price = await self.client.get_token_price("0xTOKEN", "0xBASE")
        
        # Verify results
        self.assertEqual(price, 2.0)  # Based on the 1:2 ratio we mocked
        mock_router.functions.getAmountsOut.assert_called_once()
    
    async def test_get_token_balance(self):
        """Test getting token balance"""
        # Setup
        await self.async_setUp()
        self.client.wallet_address = "0xWALLET"
        
        # Mock token contract for regular token
        mock_token_contract = AsyncMock()
        mock_token_contract.functions.balanceOf.return_value.call.return_value = 10**18  # 1 token
        mock_token_contract.functions.decimals.return_value.call.return_value = 18
        
        # Mock eth.get_balance for native token
        self.mock_web3.eth.get_balance.return_value = 5 * 10**18  # 5 native tokens
        
        # Setup contract call
        self.mock_web3.eth.contract.return_value = mock_token_contract
        
        # Test regular token
        balance = await self.client.get_token_balance("0xTOKEN")
        self.assertEqual(balance, 1.0)
        mock_token_contract.functions.balanceOf.assert_called_once()
        
        # Test native token
        self.client.token_addresses["ICP"] = "0xNATIVE"
        balance = await self.client.get_token_balance("0xNATIVE")
        self.assertEqual(balance, 5.0)
        self.mock_web3.eth.get_balance.assert_called_once()
    
    async def test_check_token_approval(self):
        """Test checking token approval"""
        # Setup
        await self.async_setUp()
        self.client.wallet_address = "0xWALLET"
        
        # Mock token contract
        mock_token_contract = AsyncMock()
        mock_token_contract.functions.allowance.return_value.call.return_value = 10**18  # 1 token allowed
        
        # Setup contract call
        self.mock_web3.eth.contract.return_value = mock_token_contract
        
        # Test sufficient allowance
        approved = await self.client.check_token_approval("0xTOKEN", "0xSPENDER", 5 * 10**17)  # 0.5 token
        self.assertTrue(approved)
        
        # Test insufficient allowance
        approved = await self.client.check_token_approval("0xTOKEN", "0xSPENDER", 2 * 10**18)  # 2 tokens
        self.assertFalse(approved)
        
        # Test unlimited approval check
        mock_token_contract.functions.allowance.return_value.call.return_value = 2**255  # Very large allowance
        approved = await self.client.check_token_approval("0xTOKEN", "0xSPENDER", None)  # Unlimited
        self.assertTrue(approved)
    
    async def test_approve_token(self):
        """Test token approval"""
        # Setup
        await self.async_setUp()
        self.client.wallet_address = "0xWALLET"
        self.client.private_key = "0xPRIVATEKEY"
        
        # Mock token contract
        mock_token_contract = AsyncMock()
        mock_token_contract.functions.decimals.return_value.call.return_value = 18
        mock_token_contract.functions.approve.return_value.estimate_gas.return_value = 100000
        
        # Mock transaction
        mock_tx_hash = MagicMock()
        mock_tx_hash.hex.return_value = "0xTXHASH"
        
        # Mock receipt
        mock_receipt = {"status": 1, "blockNumber": 123, "gasUsed": 80000}
        
        # Setup eth calls
        self.mock_web3.eth.get_transaction_count.return_value = 5
        self.mock_web3.eth.gas_price = 20000000000  # 20 Gwei
        self.mock_web3.eth.account.sign_transaction.return_value.rawTransaction = b"0xSIGNED"
        self.mock_web3.eth.send_raw_transaction.return_value = mock_tx_hash
        self.mock_web3.eth.get_transaction_receipt.return_value = mock_receipt
        
        # Setup contract call
        self.mock_web3.eth.contract.return_value = mock_token_contract
        
        # Test approval with specified amount
        with patch.object(self.client, 'wait_for_transaction', return_value={"success": True, "block_number": 123, "gas_used": 80000, "tx_hash": "0xTXHASH"}):
            approval = await self.client.approve_token("0xTOKEN", "0xSPENDER", 1.5)
        
        self.assertTrue(approval["success"])
        self.assertEqual(approval["tx_hash"], "0xTXHASH")
        self.assertEqual(approval["token"], "0xTOKEN")
        self.assertEqual(approval["spender"], "0xSPENDER")
        self.assertEqual(approval["amount"], 1.5)
        
        # Test unlimited approval
        with patch.object(self.client, 'wait_for_transaction', return_value={"success": True, "block_number": 123, "gas_used": 80000, "tx_hash": "0xTXHASH"}):
            approval = await self.client.approve_token("0xTOKEN", "0xSPENDER", None)
        
        self.assertTrue(approval["success"])
        self.assertEqual(approval["amount"], "unlimited")
    
    async def test_execute_swap(self):
        """Test executing a token swap"""
        # Setup
        await self.async_setUp()
        self.client.wallet_address = "0xWALLET"
        self.client.private_key = "0xPRIVATEKEY"
        self.client.dex_router_address = "0xROUTER"
        
        # Mock token contracts
        mock_token_in_contract = AsyncMock()
        mock_token_in_contract.functions.decimals.return_value.call.return_value = 18
        
        # Mock router contract
        mock_router_contract = AsyncMock()
        mock_router_contract.functions.getAmountsOut.return_value.call.return_value = [10**18, 2*10**18]  # 1:2 ratio
        mock_router_contract.functions.swapExactTokensForTokens.return_value.estimate_gas.return_value = 200000
        
        # Mock transaction
        mock_tx_hash = MagicMock()
        mock_tx_hash.hex.return_value = "0xTXHASH"
        
        # Mock receipt
        mock_receipt = {"status": 1, "blockNumber": 123, "gasUsed": 180000}
        
        # Setup eth calls
        self.mock_web3.eth.get_transaction_count.return_value = 6
        self.mock_web3.eth.gas_price = 20000000000  # 20 Gwei
        self.mock_web3.eth.account.sign_transaction.return_value.rawTransaction = b"0xSIGNED"
        self.mock_web3.eth.send_raw_transaction.return_value = mock_tx_hash
        self.mock_web3.eth.get_transaction_receipt.return_value = mock_receipt
        
        # Setup contract calls
        self.mock_web3.eth.contract.side_effect = lambda address, abi: (
            mock_router_contract if address == "0xROUTER"
            else mock_token_in_contract
        )
        
        # Mock check_token_approval and wait_for_transaction
        with patch.object(self.client, 'check_token_approval', return_value=True), \
             patch.object(self.client, 'wait_for_transaction', return_value={"success": True, "block_number": 123, "gas_used": 180000, "tx_hash": "0xTXHASH"}):
            
            # Execute swap
            result = await self.client.execute_swap("0xTOKEN_IN", "0xTOKEN_OUT", 1.0, slippage=0.5)
        
        # Verify results
        self.assertTrue(result["success"])
        self.assertEqual(result["tx_hash"], "0xTXHASH")
        self.assertEqual(result["token_in"], "0xTOKEN_IN")
        self.assertEqual(result["token_out"], "0xTOKEN_OUT")
        self.assertEqual(result["amount_in"], 1.0)
        mock_router_contract.functions.swapExactTokensForTokens.assert_called_once()
    
    async def test_analyze_contract(self):
        """Test contract analysis"""
        # Setup
        await self.async_setUp()
        
        # Mock token contract
        mock_token_contract = AsyncMock()
        mock_token_contract.functions.name.return_value.call.return_value = "Safe Token"
        mock_token_contract.functions.symbol.return_value.call.return_value = "SAFE"
        
        # Setup contract call
        self.mock_web3.eth.contract.return_value = mock_token_contract
        
        # Mock bytecode - standard bytecode
        self.mock_web3.eth.get_code.return_value.hex.return_value = "0x608060405260...standardcode"
        
        # Test safe token
        analysis = await self.client.analyze_contract("0xTOKEN")
        self.assertTrue(analysis["is_safe"])
        self.assertEqual(analysis["token_name"], "Safe Token")
        self.assertEqual(analysis["token_symbol"], "SAFE")
        self.assertEqual(len(analysis["risks"]), 0)
        
        # Test suspicious token
        mock_token_contract.functions.name.return_value.call.return_value = "Test Scam Token"
        mock_token_contract.functions.symbol.return_value.call.return_value = "RUG"
        
        analysis = await self.client.analyze_contract("0xTOKEN")
        self.assertFalse(analysis["is_safe"])
        self.assertTrue(any("scam" in risk.lower() for risk in analysis["risks"]))
        self.assertTrue(any("rug" in risk.lower() for risk in analysis["risks"]))
    
    async def test_get_new_tokens(self):
        """Test getting new tokens"""
        # Setup
        await self.async_setUp()
        self.client.dex_factory_address = "0xFACTORY"
        self.client.token_addresses["WICP"] = "0xWICP"
        
        # Mock factory contract and events
        mock_factory_contract = AsyncMock()
        mock_pair_filter = AsyncMock()
        mock_pair_filter.get_all_entries.return_value = [
            {"args": {"token0": "0xWICP", "token1": "0xNEWTOKEN1", "pair": "0xPAIR1"}, "blockNumber": 123},
            {"args": {"token0": "0xNEWTOKEN2", "token1": "0xWICP", "pair": "0xPAIR2"}, "blockNumber": 124}
        ]
        
        mock_factory_contract.events.PairCreated.create_filter.return_value = mock_pair_filter
        
        # Mock token contracts
        mock_token1_contract = AsyncMock()
        mock_token1_contract.functions.name.return_value.call.return_value = "New Token 1"
        mock_token1_contract.functions.symbol.return_value.call.return_value = "NT1"
        mock_token1_contract.functions.decimals.return_value.call.return_value = 18
        
        mock_token2_contract = AsyncMock()
        mock_token2_contract.functions.name.return_value.call.return_value = "New Token 2"
        mock_token2_contract.functions.symbol.return_value.call.return_value = "NT2"
        mock_token2_contract.functions.decimals.return_value.call.return_value = 18
        
        # Mock block
        mock_block = {"timestamp": 1633046400}  # Some timestamp
        
        # Setup calls
        self.mock_web3.eth.block_number = 125
        self.mock_web3.eth.get_block.return_value = mock_block
        self.mock_web3.eth.contract.side_effect = lambda address, abi: (
            mock_factory_contract if address == "0xFACTORY"
            else mock_token1_contract if address == "0xNEWTOKEN1"
            else mock_token2_contract
        )
        
        # Mock analyze_contract to return safe tokens
        with patch.object(self.client, 'analyze_contract', return_value={"is_safe": True, "token_name": "Test", "token_symbol": "TEST", "risks": []}):
            tokens = await self.client.get_new_tokens()
        
        # Verify results
        self.assertEqual(len(tokens), 2)
        token_addresses = [t["address"] for t in tokens]
        self.assertIn("0xNEWTOKEN1", token_addresses)
        self.assertIn("0xNEWTOKEN2", token_addresses)
    
    def test_load_erc20_abi(self):
        """Test loading ERC20 ABI"""
        abi = self.client._load_erc20_abi()
        self.assertIsInstance(abi, list)
        self.assertTrue(any(method.get("name") == "balanceOf" for method in abi))
        self.assertTrue(any(method.get("name") == "allowance" for method in abi))
        self.assertTrue(any(method.get("name") == "approve" for method in abi))
    
    def test_load_router_abi(self):
        """Test loading router ABI"""
        abi = self.client._load_router_abi()
        self.assertIsInstance(abi, list)
        self.assertTrue(any(method.get("name") == "getAmountsOut" for method in abi))
        self.assertTrue(any(method.get("name") == "swapExactTokensForTokens" for method in abi))
        self.assertTrue(any(method.get("name") == "swapExactETHForTokens" for method in abi))


def run_tests():
    unittest.main()


if __name__ == "__main__":
    run_tests() 