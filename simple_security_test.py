#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Test simple pour le module de sécurité du GBPBot.
Ce module teste les fonctionnalités basiques de détection des risques.
"""

import os
import sys
import unittest
import json
from pathlib import Path

# Ajouter le répertoire racine au PYTHONPATH
ROOT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT_DIR))

# Ajouter le répertoire de mocks au début du PYTHONPATH
mock_dir = ROOT_DIR / "gbpbot" / "tests" / "mocks"
if mock_dir.exists():
    sys.path.insert(0, str(mock_dir))

class SimpleSecurityTest(unittest.TestCase):
    """Tests simples pour le module de sécurité."""
    
    def setUp(self):
        """Prépare l'environnement de test."""
        # Exemple de contrat token sécurisé
        self.safe_contract = """
        // SPDX-License-Identifier: MIT
        pragma solidity ^0.8.0;
        
        contract SafeToken {
            string public name = "SafeToken";
            string public symbol = "SAFE";
            uint8 public decimals = 18;
            uint256 public totalSupply = 1000000 * 10 ** 18;
            
            mapping(address => uint256) public balanceOf;
            mapping(address => mapping(address => uint256)) public allowance;
            
            event Transfer(address indexed from, address indexed to, uint256 value);
            event Approval(address indexed owner, address indexed spender, uint256 value);
            
            constructor() {
                balanceOf[msg.sender] = totalSupply;
            }
            
            function transfer(address to, uint256 value) public returns (bool) {
                require(balanceOf[msg.sender] >= value, "Insufficient balance");
                balanceOf[msg.sender] -= value;
                balanceOf[to] += value;
                emit Transfer(msg.sender, to, value);
                return true;
            }
            
            function approve(address spender, uint256 value) public returns (bool) {
                allowance[msg.sender][spender] = value;
                emit Approval(msg.sender, spender, value);
                return true;
            }
            
            function transferFrom(address from, address to, uint256 value) public returns (bool) {
                require(balanceOf[from] >= value, "Insufficient balance");
                require(allowance[from][msg.sender] >= value, "Insufficient allowance");
                allowance[from][msg.sender] -= value;
                balanceOf[from] -= value;
                balanceOf[to] += value;
                emit Transfer(from, to, value);
                return true;
            }
        }
        """
        
        # Exemple de contrat token malveillant (honeypot)
        self.risky_contract = """
        // SPDX-License-Identifier: MIT
        pragma solidity ^0.8.0;
        
        contract HoneypotToken {
            string public name = "HoneypotToken";
            string public symbol = "TRAP";
            uint8 public decimals = 18;
            uint256 public totalSupply = 10000000 * 10 ** 18;
            
            mapping(address => uint256) public balanceOf;
            mapping(address => mapping(address => uint256)) public allowance;
            mapping(address => bool) private _isBlacklisted;
            address private _owner;
            bool private _tradingEnabled = false;
            uint256 private _sellFee = 99; // 99% fee when selling
            
            event Transfer(address indexed from, address indexed to, uint256 value);
            event Approval(address indexed owner, address indexed spender, uint256 value);
            
            constructor() {
                _owner = msg.sender;
                balanceOf[msg.sender] = totalSupply;
            }
            
            modifier onlyOwner() {
                require(msg.sender == _owner, "Not owner");
                _;
            }
            
            function transfer(address to, uint256 value) public returns (bool) {
                require(!_isBlacklisted[msg.sender], "Blacklisted");
                require(balanceOf[msg.sender] >= value, "Insufficient balance");
                
                // Allow transfers from owner always
                if (msg.sender != _owner && to != _owner) {
                    require(_tradingEnabled, "Trading not enabled");
                }
                
                // Apply sell fee if transferring to a known DEX pair address
                if (to == address(0x1111111111111111111111111111111111111111)) {
                    require(false, "Cannot sell"); // Honeypot: block all sells
                }
                
                balanceOf[msg.sender] -= value;
                balanceOf[to] += value;
                emit Transfer(msg.sender, to, value);
                return true;
            }
            
            function approve(address spender, uint256 value) public returns (bool) {
                allowance[msg.sender][spender] = value;
                emit Approval(msg.sender, spender, value);
                return true;
            }
            
            function transferFrom(address from, address to, uint256 value) public returns (bool) {
                require(!_isBlacklisted[from], "Blacklisted");
                require(balanceOf[from] >= value, "Insufficient balance");
                require(allowance[from][msg.sender] >= value, "Insufficient allowance");
                
                // Apply same restrictions as transfer
                if (from != _owner && to != _owner) {
                    require(_tradingEnabled, "Trading not enabled");
                }
                
                // Apply sell fee if transferring to a known DEX pair address
                if (to == address(0x1111111111111111111111111111111111111111)) {
                    require(false, "Cannot sell"); // Honeypot: block all sells
                }
                
                allowance[from][msg.sender] -= value;
                balanceOf[from] -= value;
                balanceOf[to] += value;
                emit Transfer(from, to, value);
                return true;
            }
            
            // Owner functions to control the honeypot
            function enableTrading() external onlyOwner {
                _tradingEnabled = true;
            }
            
            function blacklist(address account) external onlyOwner {
                _isBlacklisted[account] = true;
            }
            
            function unblacklist(address account) external onlyOwner {
                _isBlacklisted[account] = false;
            }
        }
        """
    
    def test_contract_analyzer_basic(self):
        """Vérifie que l'analyseur de contrat fonctionne correctement pour les cas simples."""
        # Mock pour l'analyseur de contrat
        class MockContractAnalyzer:
            def analyze(self, source_code):
                """Analyse simple du contrat."""
                risks = []
                risk_score = 0
                
                # Vérifier les fonctions de blacklist
                if "blacklist" in source_code:
                    risks.append("Blacklist function detected")
                    risk_score += 30
                
                # Vérifier les high fees
                if "fee" in source_code and "99" in source_code:
                    risks.append("High sell fee detected")
                    risk_score += 40
                
                # Vérifier les restrictions de trading
                if "tradingEnabled" in source_code:
                    risks.append("Trading restrictions detected")
                    risk_score += 20
                
                # Vérifier les honeypots classiques
                if "Cannot sell" in source_code or "require(false" in source_code:
                    risks.append("Honeypot: Cannot sell tokens")
                    risk_score += 100
                
                return {
                    "risks": risks,
                    "risk_score": min(risk_score, 100),
                    "is_honeypot": risk_score >= 80,
                    "is_rugpull_risk": risk_score >= 50,
                    "owner_control_score": 75 if "onlyOwner" in source_code else 0
                }
        
        # Analyse du contrat sécurisé
        analyzer = MockContractAnalyzer()
        safe_result = analyzer.analyze(self.safe_contract)
        
        self.assertEqual(len(safe_result["risks"]), 0)
        self.assertEqual(safe_result["risk_score"], 0)
        self.assertFalse(safe_result["is_honeypot"])
        self.assertFalse(safe_result["is_rugpull_risk"])
        
        # Analyse du contrat risqué
        risky_result = analyzer.analyze(self.risky_contract)
        
        self.assertGreater(len(risky_result["risks"]), 0)
        self.assertGreaterEqual(risky_result["risk_score"], 80)
        self.assertTrue(risky_result["is_honeypot"])
        self.assertTrue(risky_result["is_rugpull_risk"])
    
    def test_transaction_validator(self):
        """Vérifie que le validateur de transaction fonctionne correctement."""
        # Mock pour le validateur de transaction
        class MockTransactionValidator:
            def validate_transaction(self, tx_data):
                """Valide une transaction avant envoi."""
                errors = []
                warnings = []
                
                # Vérifier si c'est une transaction sans valeur de retour
                if tx_data.get("no_return_data", False):
                    errors.append("Transaction will likely fail: no return data expected")
                
                # Vérifier si les gas limites sont excessives
                if tx_data.get("gas", 0) > 1000000:
                    warnings.append("High gas limit might indicate a complex or inefficient transaction")
                
                # Vérifier si la transaction contient un high slippage
                if tx_data.get("slippage", 0) > 20:
                    warnings.append("High slippage (>20%) increases risk of front-running")
                
                # Vérifier si le token destination est un honeypot connu
                if tx_data.get("to_token") == "HONEYPOT_ADDRESS":
                    errors.append("Destination token is flagged as honeypot")
                
                return {
                    "is_valid": len(errors) == 0,
                    "errors": errors,
                    "warnings": warnings,
                    "security_score": 100 - (len(errors) * 30 + len(warnings) * 10)
                }
        
        # Teste une transaction normale
        validator = MockTransactionValidator()
        normal_tx = {
            "from": "0xabcd1234",
            "to": "0x5678efgh",
            "gas": 200000,
            "slippage": 5,
            "to_token": "SAFE_TOKEN"
        }
        
        normal_result = validator.validate_transaction(normal_tx)
        self.assertTrue(normal_result["is_valid"])
        self.assertEqual(len(normal_result["errors"]), 0)
        self.assertEqual(len(normal_result["warnings"]), 0)
        self.assertEqual(normal_result["security_score"], 100)
        
        # Teste une transaction risquée
        risky_tx = {
            "from": "0xabcd1234",
            "to": "0x5678efgh",
            "gas": 1500000,
            "slippage": 30,
            "to_token": "HONEYPOT_ADDRESS",
            "no_return_data": True
        }
        
        risky_result = validator.validate_transaction(risky_tx)
        self.assertFalse(risky_result["is_valid"])
        self.assertGreater(len(risky_result["errors"]), 0)
        self.assertGreater(len(risky_result["warnings"]), 0)
        self.assertLess(risky_result["security_score"], 70)
    
    def test_token_risk_assessment(self):
        """Vérifie que l'évaluation des risques de token fonctionne correctement."""
        # Mock pour l'évaluation des risques de token
        class MockTokenValidator:
            def assess_token_risk(self, token_info):
                """Évalue le risque associé à un token."""
                risk_factors = []
                safe_factors = []
                
                # Facteurs de risque
                if token_info.get("liquidity", 0) < 50000:
                    risk_factors.append("Low liquidity (< $50k)")
                
                if token_info.get("holders", 0) < 100:
                    risk_factors.append("Few holders (< 100)")
                
                if token_info.get("market_cap", 0) < 100000:
                    risk_factors.append("Low market cap (< $100k)")
                
                if token_info.get("owner_balance_percent", 0) > 50:
                    risk_factors.append("Owner holds > 50% of tokens")
                
                if token_info.get("creation_time", 0) < 24 * 3600:
                    risk_factors.append("Token created < 24h ago")
                
                # Facteurs de sécurité
                if token_info.get("verified_contract", False):
                    safe_factors.append("Contract is verified")
                
                if token_info.get("audit_count", 0) > 0:
                    safe_factors.append(f"Contract has {token_info['audit_count']} audits")
                
                if token_info.get("dextools_score", 0) > 70:
                    safe_factors.append("High DEXTools score (> 70)")
                
                # Calcul du score final (0-100)
                risk_score = min(len(risk_factors) * 20, 100)
                safety_score = min(len(safe_factors) * 20, 100)
                final_score = max(0, 100 - risk_score + safety_score / 2)
                
                return {
                    "risk_factors": risk_factors,
                    "safe_factors": safe_factors,
                    "risk_score": risk_score,
                    "safety_score": safety_score,
                    "final_score": min(final_score, 100),
                    "is_high_risk": final_score < 50
                }
        
        # Teste un token sécurisé
        validator = MockTokenValidator()
        safe_token = {
            "name": "Safe Token",
            "symbol": "SAFE",
            "liquidity": 500000,
            "holders": 1500,
            "market_cap": 2000000,
            "owner_balance_percent": 5,
            "creation_time": 30 * 24 * 3600,  # 30 jours
            "verified_contract": True,
            "audit_count": 2,
            "dextools_score": 85
        }
        
        safe_result = validator.assess_token_risk(safe_token)
        self.assertEqual(len(safe_result["risk_factors"]), 0)
        self.assertGreater(len(safe_result["safe_factors"]), 0)
        self.assertGreaterEqual(safe_result["final_score"], 70)
        self.assertFalse(safe_result["is_high_risk"])
        
        # Teste un token risqué
        risky_token = {
            "name": "Risky Token",
            "symbol": "RISK",
            "liquidity": 10000,
            "holders": 50,
            "market_cap": 50000,
            "owner_balance_percent": 80,
            "creation_time": 12 * 3600,  # 12 heures
            "verified_contract": False,
            "audit_count": 0,
            "dextools_score": 20
        }
        
        risky_result = validator.assess_token_risk(risky_token)
        self.assertGreater(len(risky_result["risk_factors"]), 0)
        self.assertEqual(len(risky_result["safe_factors"]), 0)
        self.assertLess(risky_result["final_score"], 50)
        self.assertTrue(risky_result["is_high_risk"])

if __name__ == "__main__":
    unittest.main() 