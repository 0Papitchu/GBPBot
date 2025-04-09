#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests unitaires pour le module de sécurité du GBPBot

Ce module teste les fonctionnalités de sécurité du GBPBot,
notamment la détection des scams, rug pulls et honeypots.
"""

import os
import sys
import json
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ajout du chemin racine au sys.path pour les imports
ROOT_DIR = Path(__file__).parent.parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Import des modules de test
from gbpbot.tests.setup_test_environment import setup_test_environment, cleanup_test_environment


class TestSecurityModule(unittest.TestCase):
    """Suite de tests pour le module de sécurité du GBPBot"""
    
    @classmethod
    def setUpClass(cls):
        """
        Préparation de l'environnement de test avant l'exécution des tests
        """
        # Configuration de l'environnement de test
        cls.env_file, cls.wallet_paths = setup_test_environment()
        
        # Configuration pour les tests
        cls.test_config = {
            "security": {
                "honeypot_check": True,
                "rug_pull_check": True,
                "scam_check": True,
                "min_liquidity_usd": 10000,
                "min_locked_liquidity_percent": 80,
                "max_owner_percent": 15,
                "max_tax_percent": 10,
                "min_holders": 50,
                "min_age_hours": 24
            },
            "blockchain": {
                "avalanche": {
                    "rpc_url": os.environ.get("AVALANCHE_RPC_URL", "https://api.avax-test.network/ext/bc/C/rpc"),
                    "chain_id": os.environ.get("AVALANCHE_CHAIN_ID", "43113")
                },
                "solana": {
                    "rpc_url": os.environ.get("SOLANA_RPC_URL", "https://api.testnet.solana.com")
                }
            }
        }
        
        # Token de test sûr
        cls.safe_token = {
            "address": "0xSafeTokenAddress123",
            "name": "Safe Token",
            "symbol": "SAFE",
            "decimals": 18,
            "total_supply": "1000000000000000000000000",
            "deployer": "0xDeployerAddress123",
            "creation_tx": "0xTransactionHash123",
            "creation_time": 1680000000,
            "holder_count": 150,
            "liquidity_usd": 50000,
            "locked_liquidity_percent": 95,
            "owner_balance_percent": 5,
            "tax_buy_percent": 5,
            "tax_sell_percent": 5,
            "code_verified": True,
            "has_proxy": False,
            "has_mint_function": False,
            "has_blacklist": False,
            "trading_enabled": True
        }
        
        # Token de test dangereux
        cls.risky_token = {
            "address": "0xRiskyTokenAddress456",
            "name": "Risky Token",
            "symbol": "RISK",
            "decimals": 18,
            "total_supply": "1000000000000000000000000000",
            "deployer": "0xDeployerAddress456",
            "creation_tx": "0xTransactionHash456",
            "creation_time": 1680000000,
            "holder_count": 10,
            "liquidity_usd": 5000,
            "locked_liquidity_percent": 20,
            "owner_balance_percent": 60,
            "tax_buy_percent": 20,
            "tax_sell_percent": 25,
            "code_verified": False,
            "has_proxy": True,
            "has_mint_function": True,
            "has_blacklist": True,
            "trading_enabled": True
        }
        
        # Code source du contrat sûr
        cls.safe_contract_code = """
        // SPDX-License-Identifier: MIT
        pragma solidity ^0.8.0;
        
        import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
        import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
        
        contract SafeToken is ERC20, ReentrancyGuard {
            constructor() ERC20("Safe Token", "SAFE") {
                _mint(msg.sender, 1000000 * 10**decimals());
            }
        }
        """
        
        # Code source du contrat dangereux
        cls.risky_contract_code = """
        // SPDX-License-Identifier: MIT
        pragma solidity ^0.8.0;
        
        contract RiskyToken {
            mapping(address => uint256) private _balances;
            mapping(address => bool) private _blacklist;
            address private _owner;
            bool private _tradingEnabled;
            uint256 private _totalSupply;
            
            constructor() {
                _owner = msg.sender;
                _mint(msg.sender, 1000000000 * 10**18);
            }
            
            function mint(address to, uint256 amount) external {
                require(msg.sender == _owner, "Not owner");
                _mint(to, amount);
            }
            
            function setBlacklist(address account, bool value) external {
                require(msg.sender == _owner, "Not owner");
                _blacklist[account] = value;
            }
            
            function transfer(address to, uint256 amount) external returns (bool) {
                require(!_blacklist[msg.sender], "Blacklisted");
                require(_tradingEnabled || msg.sender == _owner, "Trading not enabled");
                uint256 fee = amount * 25 / 100;  // 25% tax
                _transfer(msg.sender, _owner, fee);
                _transfer(msg.sender, to, amount - fee);
                return true;
            }
            
            function _mint(address account, uint256 amount) private {
                _totalSupply += amount;
                _balances[account] += amount;
            }
            
            function _transfer(address from, address to, uint256 amount) private {
                require(_balances[from] >= amount, "Insufficient balance");
                _balances[from] -= amount;
                _balances[to] += amount;
            }
        }
        """
    
    @classmethod
    def tearDownClass(cls):
        """
        Nettoyage après l'exécution de tous les tests
        """
        # Nettoyer l'environnement de test
        cleanup_test_environment(cls.env_file, cls.wallet_paths)
    
    def setUp(self):
        """
        Préparation avant chaque test
        """
        # Tenter d'importer les modules de sécurité, avec gestion des erreurs
        try:
            from gbpbot.core.security.token_validator import TokenValidator
            from gbpbot.core.security.contract_analyzer import ContractAnalyzer
            from gbpbot.core.security.transaction_validator import TransactionValidator
            
            self.token_validator_class = TokenValidator
            self.contract_analyzer_class = ContractAnalyzer
            self.transaction_validator_class = TransactionValidator
        except ImportError as e:
            self.skipTest(f"Module de sécurité non disponible: {str(e)}")
    
    def test_module_import(self):
        """
        Test de l'importation du module de sécurité
        """
        # Vérifier que les modules ont été importés correctement
        self.assertIsNotNone(self.token_validator_class, "La classe TokenValidator n'a pas pu être importée")
        self.assertIsNotNone(self.contract_analyzer_class, "La classe ContractAnalyzer n'a pas pu être importée")
        self.assertIsNotNone(self.transaction_validator_class, "La classe TransactionValidator n'a pas pu être importée")
    
    @patch("gbpbot.core.security.token_validator.TokenValidator._initialize_blockchain_client")
    def test_token_validator_initialization(self, mock_init_blockchain):
        """
        Test de l'initialisation du validateur de tokens
        """
        # Configurer le mock
        mock_init_blockchain.return_value = True
        
        # Instancier le validateur de tokens
        validator = self.token_validator_class(self.test_config)
        
        # Vérifier l'initialisation
        self.assertIsNotNone(validator, "Le validateur de tokens n'a pas été instancié correctement")
        self.assertEqual(validator.config, self.test_config, "La configuration n'a pas été correctement assignée")
    
    @patch("gbpbot.core.security.token_validator.TokenValidator._check_liquidity")
    @patch("gbpbot.core.security.token_validator.TokenValidator._check_holders")
    @patch("gbpbot.core.security.token_validator.TokenValidator._check_owner_balance")
    @patch("gbpbot.core.security.token_validator.TokenValidator._check_taxes")
    @patch("gbpbot.core.security.token_validator.TokenValidator._initialize_blockchain_client")
    def test_token_validation_safe(self, mock_init_blockchain, mock_check_taxes, 
                                mock_check_owner, mock_check_holders, mock_check_liquidity):
        """
        Test de la validation d'un token sûr
        """
        # Configurer les mocks
        mock_init_blockchain.return_value = True
        mock_check_liquidity.return_value = True
        mock_check_holders.return_value = True
        mock_check_owner.return_value = True
        mock_check_taxes.return_value = True
        
        # Instancier le validateur de tokens
        validator = self.token_validator_class(self.test_config)
        
        # Valider le token sûr
        validation_result = validator.validate_token(self.safe_token)
        
        # Vérifier le résultat de la validation
        self.assertIsNotNone(validation_result, "Le résultat de validation est nul")
        self.assertTrue(validation_result["is_safe"], "Le token sûr a été marqué comme dangereux")
        self.assertFalse(validation_result["is_honeypot"], "Le token sûr a été marqué comme honeypot")
        self.assertFalse(validation_result["is_rug_pull"], "Le token sûr a été marqué comme rug pull")
        self.assertTrue(validation_result["liquidity_ok"], "La liquidité du token sûr a été marquée comme insuffisante")
        self.assertTrue(validation_result["holders_ok"], "Le nombre de holders du token sûr a été marqué comme insuffisant")
        self.assertTrue(validation_result["owner_balance_ok"], "La balance du propriétaire du token sûr a été marquée comme excessive")
        self.assertTrue(validation_result["taxes_ok"], "Les taxes du token sûr ont été marquées comme excessives")
    
    @patch("gbpbot.core.security.token_validator.TokenValidator._check_liquidity")
    @patch("gbpbot.core.security.token_validator.TokenValidator._check_holders")
    @patch("gbpbot.core.security.token_validator.TokenValidator._check_owner_balance")
    @patch("gbpbot.core.security.token_validator.TokenValidator._check_taxes")
    @patch("gbpbot.core.security.token_validator.TokenValidator._initialize_blockchain_client")
    def test_token_validation_risky(self, mock_init_blockchain, mock_check_taxes, 
                                 mock_check_owner, mock_check_holders, mock_check_liquidity):
        """
        Test de la validation d'un token dangereux
        """
        # Configurer les mocks
        mock_init_blockchain.return_value = True
        mock_check_liquidity.return_value = False
        mock_check_holders.return_value = False
        mock_check_owner.return_value = False
        mock_check_taxes.return_value = False
        
        # Instancier le validateur de tokens
        validator = self.token_validator_class(self.test_config)
        
        # Valider le token dangereux
        validation_result = validator.validate_token(self.risky_token)
        
        # Vérifier le résultat de la validation
        self.assertIsNotNone(validation_result, "Le résultat de validation est nul")
        self.assertFalse(validation_result["is_safe"], "Le token dangereux a été marqué comme sûr")
        self.assertTrue(validation_result["is_honeypot"], "Le token dangereux n'a pas été marqué comme honeypot")
        self.assertTrue(validation_result["is_rug_pull"], "Le token dangereux n'a pas été marqué comme rug pull")
        self.assertFalse(validation_result["liquidity_ok"], "La liquidité du token dangereux a été marquée comme suffisante")
        self.assertFalse(validation_result["holders_ok"], "Le nombre de holders du token dangereux a été marqué comme suffisant")
        self.assertFalse(validation_result["owner_balance_ok"], "La balance du propriétaire du token dangereux a été marquée comme acceptable")
        self.assertFalse(validation_result["taxes_ok"], "Les taxes du token dangereux ont été marquées comme acceptables")
    
    @patch("gbpbot.core.security.contract_analyzer.ContractAnalyzer._initialize_blockchain_client")
    def test_contract_analyzer_initialization(self, mock_init_blockchain):
        """
        Test de l'initialisation de l'analyseur de contrats
        """
        # Configurer le mock
        mock_init_blockchain.return_value = True
        
        # Instancier l'analyseur de contrats
        analyzer = self.contract_analyzer_class(self.test_config)
        
        # Vérifier l'initialisation
        self.assertIsNotNone(analyzer, "L'analyseur de contrats n'a pas été instancié correctement")
        self.assertEqual(analyzer.config, self.test_config, "La configuration n'a pas été correctement assignée")
    
    @patch("gbpbot.core.security.contract_analyzer.ContractAnalyzer._analyze_functions")
    @patch("gbpbot.core.security.contract_analyzer.ContractAnalyzer._analyze_modifiers")
    @patch("gbpbot.core.security.contract_analyzer.ContractAnalyzer._analyze_variables")
    @patch("gbpbot.core.security.contract_analyzer.ContractAnalyzer._initialize_blockchain_client")
    def test_contract_analysis_safe(self, mock_init_blockchain, mock_analyze_vars, 
                                 mock_analyze_mods, mock_analyze_funcs):
        """
        Test de l'analyse d'un contrat sûr
        """
        # Configurer les mocks
        mock_init_blockchain.return_value = True
        mock_analyze_vars.return_value = {
            "has_owner": True,
            "has_blacklist": False,
            "has_whitelist": False,
            "has_tax_var": False
        }
        mock_analyze_mods.return_value = {
            "has_onlyowner": True,
            "has_reentrancy_guard": True
        }
        mock_analyze_funcs.return_value = {
            "has_mint": False,
            "has_burn": False,
            "has_blacklist_func": False,
            "has_whitelist_func": False,
            "has_tax_func": False,
            "has_proxy": False
        }
        
        # Instancier l'analyseur de contrats
        analyzer = self.contract_analyzer_class(self.test_config)
        
        # Analyser le contrat sûr
        analysis_result = analyzer.analyze_contract(self.safe_contract_code)
        
        # Vérifier le résultat de l'analyse
        self.assertIsNotNone(analysis_result, "Le résultat d'analyse est nul")
        self.assertTrue(analysis_result["is_safe"], "Le contrat sûr a été marqué comme dangereux")
        self.assertFalse(analysis_result["has_dangerous_functions"], "Le contrat sûr a été marqué comme ayant des fonctions dangereuses")
        self.assertTrue(analysis_result["has_security_features"], "Le contrat sûr a été marqué comme n'ayant pas de fonctionnalités de sécurité")
        self.assertEqual(analysis_result["risk_score"], 0, "Le score de risque du contrat sûr n'est pas 0")
        self.assertEqual(len(analysis_result["risks"]), 0, "Des risques ont été détectés dans le contrat sûr")
    
    @patch("gbpbot.core.security.contract_analyzer.ContractAnalyzer._analyze_functions")
    @patch("gbpbot.core.security.contract_analyzer.ContractAnalyzer._analyze_modifiers")
    @patch("gbpbot.core.security.contract_analyzer.ContractAnalyzer._analyze_variables")
    @patch("gbpbot.core.security.contract_analyzer.ContractAnalyzer._initialize_blockchain_client")
    def test_contract_analysis_risky(self, mock_init_blockchain, mock_analyze_vars, 
                                  mock_analyze_mods, mock_analyze_funcs):
        """
        Test de l'analyse d'un contrat dangereux
        """
        # Configurer les mocks
        mock_init_blockchain.return_value = True
        mock_analyze_vars.return_value = {
            "has_owner": True,
            "has_blacklist": True,
            "has_whitelist": False,
            "has_tax_var": True
        }
        mock_analyze_mods.return_value = {
            "has_onlyowner": True,
            "has_reentrancy_guard": False
        }
        mock_analyze_funcs.return_value = {
            "has_mint": True,
            "has_burn": True,
            "has_blacklist_func": True,
            "has_whitelist_func": False,
            "has_tax_func": True,
            "has_proxy": True
        }
        
        # Instancier l'analyseur de contrats
        analyzer = self.contract_analyzer_class(self.test_config)
        
        # Analyser le contrat dangereux
        analysis_result = analyzer.analyze_contract(self.risky_contract_code)
        
        # Vérifier le résultat de l'analyse
        self.assertIsNotNone(analysis_result, "Le résultat d'analyse est nul")
        self.assertFalse(analysis_result["is_safe"], "Le contrat dangereux a été marqué comme sûr")
        self.assertTrue(analysis_result["has_dangerous_functions"], "Le contrat dangereux a été marqué comme n'ayant pas de fonctions dangereuses")
        self.assertFalse(analysis_result["has_security_features"], "Le contrat dangereux a été marqué comme ayant des fonctionnalités de sécurité")
        self.assertGreater(analysis_result["risk_score"], 50, "Le score de risque du contrat dangereux est trop bas")
        self.assertGreater(len(analysis_result["risks"]), 0, "Aucun risque n'a été détecté dans le contrat dangereux")
    
    @patch("gbpbot.core.security.transaction_validator.TransactionValidator._initialize_blockchain_client")
    def test_transaction_validator_initialization(self, mock_init_blockchain):
        """
        Test de l'initialisation du validateur de transactions
        """
        # Configurer le mock
        mock_init_blockchain.return_value = True
        
        # Instancier le validateur de transactions
        validator = self.transaction_validator_class(self.test_config)
        
        # Vérifier l'initialisation
        self.assertIsNotNone(validator, "Le validateur de transactions n'a pas été instancié correctement")
        self.assertEqual(validator.config, self.test_config, "La configuration n'a pas été correctement assignée")
    
    @patch("gbpbot.core.security.transaction_validator.TransactionValidator._simulate_transaction")
    @patch("gbpbot.core.security.transaction_validator.TransactionValidator._check_gas_price")
    @patch("gbpbot.core.security.transaction_validator.TransactionValidator._check_slippage")
    @patch("gbpbot.core.security.transaction_validator.TransactionValidator._initialize_blockchain_client")
    def test_transaction_validation(self, mock_init_blockchain, mock_check_slippage, 
                                 mock_check_gas, mock_simulate_tx):
        """
        Test de la validation des transactions
        """
        # Configurer les mocks
        mock_init_blockchain.return_value = True
        mock_check_slippage.return_value = True
        mock_check_gas.return_value = True
        mock_simulate_tx.return_value = {
            "success": True,
            "gas_used": 150000,
            "output_amount": 1000,
            "effective_price": 30.0
        }
        
        # Instancier le validateur de transactions
        validator = self.transaction_validator_class(self.test_config)
        
        # Transaction de test
        test_tx = {
            "from": "0xUserAddress123",
            "to": "0xTokenAddress123",
            "value": "1000000000000000000",  # 1 AVAX
            "gas": 200000,
            "gasPrice": "50000000000",  # 50 Gwei
            "data": "0x123456789abcdef"  # Données de la transaction
        }
        
        # Valider la transaction
        validation_result = validator.validate_transaction(test_tx)
        
        # Vérifier le résultat de la validation
        self.assertIsNotNone(validation_result, "Le résultat de validation est nul")
        self.assertTrue(validation_result["is_valid"], "La transaction a été marquée comme invalide")
        self.assertTrue(validation_result["simulation_success"], "La simulation de la transaction a échoué")
        self.assertTrue(validation_result["gas_price_ok"], "Le prix du gas a été marqué comme trop élevé")
        self.assertTrue(validation_result["slippage_ok"], "Le slippage a été marqué comme trop élevé")
        self.assertIn("estimated_gas", validation_result, "L'estimation du gas est manquante")
        self.assertIn("output_amount", validation_result, "Le montant de sortie est manquant")
        self.assertIn("effective_price", validation_result, "Le prix effectif est manquant")


if __name__ == "__main__":
    unittest.main() 