#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tests pour l'analyseur de contrats de tokens Solana avec IA
==========================================================

Ce module teste les fonctionnalités d'analyse de contrats Solana
pour s'assurer que le système peut correctement identifier les
risques dans les contrats de tokens.
"""

import os
import sys
import pytest
import asyncio
import json
from typing import Dict, Any, Optional
from unittest.mock import patch, MagicMock

# Ajouter le répertoire parent au path pour les imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import conditionnel qui ne devrait pas échouer le test si les modules ne sont pas disponibles
try:
    from gbpbot.ai.token_contract_analyzer import (
        SolanaTokenContractAnalyzer, 
        ContractAnalysisResult,
        create_token_contract_analyzer
    )
    ANALYZER_IMPORTS_OK = True
except ImportError:
    ANALYZER_IMPORTS_OK = False

# Fixture pour les exemples de contrats
@pytest.fixture
def sample_contracts():
    """Fournit des exemples de contrats pour les tests."""
    return {
        "safe_contract": """
            use anchor_lang::prelude::*;
            use anchor_spl::token::{Mint, Token, TokenAccount};
            
            declare_id!("SampleSafeToken1111111111111111111111111");
            
            #[program]
            pub mod safe_token {
                use super::*;
                
                pub fn initialize(ctx: Context<Initialize>, total_supply: u64) -> Result<()> {
                    // Standard initialization logic
                    Ok(())
                }
                
                pub fn transfer(ctx: Context<Transfer>, amount: u64) -> Result<()> {
                    // Standard transfer logic
                    Ok(())
                }
            }
        """,
        "honeypot_contract": """
            use anchor_lang::prelude::*;
            use anchor_spl::token::{Mint, Token, TokenAccount};
            
            declare_id!("HoneypotTokenAddress111111111111111111111");
            
            #[program]
            pub mod honeypot_token {
                use super::*;
                
                pub fn initialize(ctx: Context<Initialize>, total_supply: u64) -> Result<()> {
                    // Standard initialization logic
                    Ok(())
                }
                
                pub fn transfer(ctx: Context<Transfer>, amount: u64) -> Result<()> {
                    // Verify if the sender is allowed to transfer
                    if !ctx.accounts.from.is_in_whitelist() && !ctx.accounts.from.is_owner() {
                        // Block transfer from non-whitelisted accounts
                        return Err(ErrorCode::TransferDisabled.into());
                    }
                    
                    // This is a classic honeypot pattern - only whitelist and owner can transfer
                    // The disable_transfer function is called after initial liquidity is added
                    
                    Ok(())
                }
                
                pub fn disable_transfer(ctx: Context<OwnerOnly>) -> Result<()> {
                    // Only owner can call this to disable transfers
                    require!(ctx.accounts.authority.is_owner(), ErrorCode::Unauthorized);
                    
                    // Disable transfers for non-whitelisted accounts
                    ctx.accounts.config.only_whitelist = true;
                    
                    Ok(())
                }
            }
        """,
        "rug_pull_contract": """
            use anchor_lang::prelude::*;
            use anchor_spl::token::{Mint, Token, TokenAccount};
            
            declare_id!("RugPullTokenAddress1111111111111111111111");
            
            #[program]
            pub mod rug_pull_token {
                use super::*;
                
                pub fn initialize(ctx: Context<Initialize>, total_supply: u64) -> Result<()> {
                    // Standard initialization logic
                    Ok(())
                }
                
                pub fn withdraw_liquidity(ctx: Context<OwnerOnly>) -> Result<()> {
                    // Only owner can call this function
                    require!(ctx.accounts.authority.is_owner(), ErrorCode::Unauthorized);
                    
                    // Owner can drain all liquidity - classic rug pull pattern
                    // This function is typically called after sufficient buys
                    drain_liquidity(ctx)?;
                    
                    Ok(())
                }
                
                pub fn unlimited_mint(ctx: Context<OwnerOnly>, amount: u64) -> Result<()> {
                    // Allow owner to mint unlimited tokens
                    require!(ctx.accounts.authority.is_owner(), ErrorCode::Unauthorized);
                    
                    mint_to_owner(ctx, amount)?;
                    
                    Ok(())
                }
            }
        """
    }

# Test de base pour vérifier que l'analyseur peut être instancié
@pytest.mark.skipif(not ANALYZER_IMPORTS_OK, reason="Modules d'analyse de contrats non disponibles")
def test_analyzer_initialization():
    """Teste l'initialisation de base de l'analyseur de contrats."""
    analyzer = SolanaTokenContractAnalyzer()
    assert analyzer is not None
    assert analyzer.has_ai is False  # Sans client IA fourni
    
    # Vérification des paramètres par défaut
    assert analyzer.min_analysis_confidence == 70
    assert analyzer.max_analysis_time_ms == 300
    assert analyzer.strict_mode is True

# Test pour l'analyse de contrats sans IA
@pytest.mark.skipif(not ANALYZER_IMPORTS_OK, reason="Modules d'analyse de contrats non disponibles")
@pytest.mark.asyncio
async def test_basic_contract_analysis(sample_contracts):
    """Teste l'analyse de base des contrats sans IA."""
    analyzer = SolanaTokenContractAnalyzer()
    
    # Test avec un contrat sécurisé
    safe_result = await analyzer.quick_analyze_contract(
        contract_address="SampleSafeToken1111111111111111111111111",
        contract_code=sample_contracts["safe_contract"]
    )
    
    assert safe_result.is_safe is True
    assert safe_result.risk_score > 70
    assert len(safe_result.risk_factors) == 0
    
    # Test avec un contrat honeypot
    honeypot_result = await analyzer.quick_analyze_contract(
        contract_address="HoneypotTokenAddress111111111111111111111",
        contract_code=sample_contracts["honeypot_contract"]
    )
    
    assert honeypot_result.is_safe is False
    assert honeypot_result.risk_score < 50
    assert honeypot_result.potential_honeypot is True
    assert len(honeypot_result.risk_factors) > 0
    
    # Test avec un contrat rug pull
    rugpull_result = await analyzer.quick_analyze_contract(
        contract_address="RugPullTokenAddress1111111111111111111111",
        contract_code=sample_contracts["rug_pull_contract"]
    )
    
    assert rugpull_result.is_safe is False
    assert rugpull_result.risk_score < 50
    assert rugpull_result.potential_rug_pull is True
    assert len(rugpull_result.risk_factors) > 0

# Test pour l'analyse avec IA simulée
@pytest.mark.skipif(not ANALYZER_IMPORTS_OK, reason="Modules d'analyse de contrats non disponibles")
@pytest.mark.asyncio
async def test_ai_enhanced_analysis(sample_contracts):
    """Teste l'analyse de contrats avec IA simulée."""
    # Créer un mock de client IA
    mock_ai_client = MagicMock()
    mock_ai_client.generate = MagicMock()
    
    # Configurer la réponse du mock
    ai_response_honeypot = json.dumps({
        "is_safe": False,
        "risk_score": 15,
        "potential_honeypot": True,
        "potential_rug_pull": False,
        "confidence": 85,
        "risk_factors": [
            {
                "category": "honeypot",
                "pattern": "disable_transfer",
                "severity": "high",
                "description": "Function to disable transfers after liquidity is added"
            },
            {
                "category": "honeypot",
                "pattern": "only_whitelist",
                "severity": "high",
                "description": "Only whitelisted addresses can transfer tokens"
            }
        ],
        "recommendation": "ÉVITER - Caractéristiques de honeypot confirmées"
    })
    
    ai_response_rugpull = json.dumps({
        "is_safe": False,
        "risk_score": 10,
        "potential_honeypot": False,
        "potential_rug_pull": True,
        "confidence": 90,
        "risk_factors": [
            {
                "category": "rug_pull",
                "pattern": "withdraw_liquidity",
                "severity": "high",
                "description": "Owner can drain all liquidity"
            },
            {
                "category": "rug_pull",
                "pattern": "unlimited_mint",
                "severity": "high",
                "description": "Owner can mint unlimited tokens"
            }
        ],
        "recommendation": "ÉVITER - Caractéristiques de rug pull confirmées"
    })
    
    # Configurer les réponses du mock en fonction de l'input
    async def mock_generate_side_effect(prompt, **kwargs):
        if "HoneypotTokenAddress" in prompt:
            return f"```json\n{ai_response_honeypot}\n```"
        elif "RugPullTokenAddress" in prompt:
            return f"```json\n{ai_response_rugpull}\n```"
        else:
            return '{"is_safe": true, "risk_score": 85, "confidence": 75}'
    
    mock_ai_client.generate.side_effect = mock_generate_side_effect
    
    # Créer un mock pour get_prompt_manager
    mock_prompt_manager = MagicMock()
    mock_prompt_manager.get_prompt_template.return_value = "Analyze this contract: {contract_info}"
    mock_prompt_manager.format_prompt.return_value = "Analyze this contract: {sample_json}"
    
    # Patcher les fonctions nécessaires
    with patch("gbpbot.ai.token_contract_analyzer.get_prompt_manager", return_value=mock_prompt_manager):
        # Créer l'analyseur avec le mock
        analyzer = SolanaTokenContractAnalyzer(ai_client=mock_ai_client)
        assert analyzer.has_ai is True
        
        # Test avec un contrat honeypot
        honeypot_result = await analyzer.quick_analyze_contract(
            contract_address="HoneypotTokenAddress111111111111111111111",
            contract_code=sample_contracts["honeypot_contract"]
        )
        
        assert honeypot_result.is_safe is False
        assert honeypot_result.risk_score < 30
        assert honeypot_result.potential_honeypot is True
        assert len(honeypot_result.risk_factors) >= 2
        assert "honeypot" in honeypot_result.recommendation.lower()
        
        # Test avec un contrat rug pull
        rugpull_result = await analyzer.quick_analyze_contract(
            contract_address="RugPullTokenAddress1111111111111111111111",
            contract_code=sample_contracts["rug_pull_contract"]
        )
        
        assert rugpull_result.is_safe is False
        assert rugpull_result.risk_score < 30
        assert rugpull_result.potential_rug_pull is True
        assert len(rugpull_result.risk_factors) >= 2
        assert "rug pull" in rugpull_result.recommendation.lower()

# Test pour l'analyse de base sans code de contrat
@pytest.mark.skipif(not ANALYZER_IMPORTS_OK, reason="Modules d'analyse de contrats non disponibles")
@pytest.mark.asyncio
async def test_analysis_without_contract_code():
    """Teste l'analyse avec seulement l'adresse du contrat."""
    analyzer = SolanaTokenContractAnalyzer()
    
    # Test avec une adresse valide mais sans code
    result = await analyzer.quick_analyze_contract(
        contract_address="SolanaValidAddress111111111111111111111111",
        contract_code=None
    )
    
    # Doit recommander la prudence sans code à analyser
    assert result.unknown_risks is True
    assert result.confidence < 50
    assert "prudence" in result.recommendation.lower()
    
    # Test avec une adresse invalide
    invalid_result = await analyzer.quick_analyze_contract(
        contract_address="InvalidAddress",
        contract_code=None
    )
    
    assert invalid_result.is_safe is False
    assert "adresse" in invalid_result.recommendation.lower()

# Test pour la fonction de création d'analyseur
@pytest.mark.skipif(not ANALYZER_IMPORTS_OK, reason="Modules d'analyse de contrats non disponibles")
def test_create_analyzer_function():
    """Teste la fonction create_token_contract_analyzer."""
    # Test de création simple sans AI client
    analyzer = create_token_contract_analyzer()
    assert analyzer is not None
    assert isinstance(analyzer, SolanaTokenContractAnalyzer)
    
    # Test avec config personnalisée
    custom_config = {
        "MIN_ANALYSIS_CONFIDENCE": 80,
        "MAX_ANALYSIS_TIME_MS": 200,
        "STRICT_CONTRACT_ANALYSIS": False
    }
    
    analyzer_with_config = create_token_contract_analyzer(config=custom_config)
    assert analyzer_with_config.min_analysis_confidence == 80
    assert analyzer_with_config.max_analysis_time_ms == 200
    assert analyzer_with_config.strict_mode is False

if __name__ == "__main__":
    pytest.main(["-xvs", __file__]) 