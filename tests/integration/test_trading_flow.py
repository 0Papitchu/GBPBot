from typing import Dict, List, Optional
import pytest
import asyncio
from unittest.mock import Mock, patch
from gbpbot.core.mev_executor import MEVExecutor
from gbpbot.strategies.ultra_scalping import UltraScalping
from gbpbot.security.rugpull_defender import RugPullDefender, SecurityCheck

class TestConfig:
    """Configuration de test"""
    WEB3_PROVIDER = "https://api.avax-test.network/ext/bc/C/rpc"
    TEST_TOKEN = "0x1234..."  # Adresse d'un token de test
    
@pytest.fixture
def trading_components():
    """Initialise les composants pour le test"""
    config = {
        "web3_provider": TestConfig.WEB3_PROVIDER
    }
    
    return {
        "mev_executor": MEVExecutor(TestConfig.WEB3_PROVIDER),
        "scalping": UltraScalping(config),
        "security": RugPullDefender(TestConfig.WEB3_PROVIDER)
    }

@pytest.mark.asyncio
async def test_complete_trading_flow(trading_components):
    """Test le flux complet de trading"""
    try:
        # 1. Analyse de sécurité
        security_result = await trading_components["security"].analyze_security(
            TestConfig.TEST_TOKEN
        )
        assert isinstance(security_result, SecurityCheck)
        assert isinstance(security_result.is_safe, bool)
        
        if security_result.is_safe:
            # 2. Analyse de scalping
            scalp_opportunity = await trading_components["scalping"].execute_scalp(
                TestConfig.TEST_TOKEN
            )
            
            if scalp_opportunity:
                # 3. Exécution MEV si opportunité
                mev_result = await trading_components["mev_executor"].execute_frontrun({
                    "to": TestConfig.TEST_TOKEN,
                    "value": 1000000000000000000,
                    "gasPrice": 50000000000
                })
                
                # Vérification des résultats
                if mev_result:
                    assert isinstance(mev_result, str)
                    
    except Exception as e:
        pytest.fail(f"Test failed with error: {str(e)}")

@pytest.mark.asyncio
async def test_error_handling(trading_components):
    """Test la gestion des erreurs"""
    # Test avec une mauvaise adresse
    security_result = await trading_components["security"].analyze_security(
        "0x0000000000000000000000000000000000000000"
    )
    assert isinstance(security_result, SecurityCheck)
    assert security_result.is_safe == False
    
    # Test avec un token invalide
    scalp_result = await trading_components["scalping"].execute_scalp(
        "0x0000000000000000000000000000000000000000"
    )
    assert scalp_result is None 