#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests unitaires pour le module d'IA du GBPBot

Ce module teste les fonctionnalités d'intelligence artificielle du GBPBot,
y compris l'intégration avec les modèles de langage et les capacités d'analyse.
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


class TestAIModule(unittest.TestCase):
    """Suite de tests pour le module d'IA du GBPBot"""
    
    @classmethod
    def setUpClass(cls):
        """
        Préparation de l'environnement de test avant l'exécution des tests
        """
        # Configuration de l'environnement de test
        cls.env_file, cls.wallet_paths = setup_test_environment()
        
        # Configuration de test pour l'IA
        cls.test_ai_config = {
            "providers": {
                "openai": {
                    "api_key": "sk-test-key-not-real",
                    "model": "gpt-3.5-turbo",
                    "enabled": True,
                    "timeout": 30,
                    "max_tokens": 1000
                },
                "llama": {
                    "model_path": "/path/to/test/model.bin",
                    "enabled": False,
                    "context_length": 2048,
                    "temperature": 0.7
                }
            },
            "analysis": {
                "token_analysis_threshold": 0.7,
                "market_analysis_interval": 300,
                "risk_evaluation_enabled": True,
                "embedding_dimension": 384
            }
        }
        
        # Exemples de données pour les tests
        cls.test_token_data = {
            "address": "0xTestTokenAddress123",
            "name": "TestToken",
            "symbol": "TTK",
            "decimals": 18,
            "total_supply": "1000000000000000000000000",
            "deployer": "0xDeployerAddress123",
            "creation_tx": "0xTransactionHash123",
            "creation_time": 1680000000,
            "holder_count": 120,
            "liquidity_usd": 50000,
            "market_cap": 200000,
            "price_usd": 0.2,
            "code_verified": True,
            "has_antiwhale": False,
            "has_blacklist": True,
            "has_mint_function": False,
            "trading_enabled": True
        }
        
        # Exemple de contexte de marché
        cls.test_market_context = {
            "market_sentiment": "bullish",
            "btc_dominance": 45.2,
            "total_market_cap": 1.8,  # en trillions
            "defi_tvl": 42.5,  # en milliards
            "gas_price_gwei": 25,
            "recent_trends": ["memecoins", "layer2", "ai"],
            "top_gainers_24h": [
                {"symbol": "TOKEN1", "price_change": 32.5},
                {"symbol": "TOKEN2", "price_change": 28.7}
            ]
        }
    
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
        # Tenter d'importer les modules d'IA, avec gestion des erreurs
        try:
            from gbpbot.ai.llm_provider import LLMProvider
            from gbpbot.ai.token_analyzer import TokenAnalyzer
            from gbpbot.ai.market_analyzer import MarketAnalyzer
            from gbpbot.ai.risk_evaluator import RiskEvaluator
            
            self.llm_provider_class = LLMProvider
            self.token_analyzer_class = TokenAnalyzer
            self.market_analyzer_class = MarketAnalyzer
            self.risk_evaluator_class = RiskEvaluator
        except ImportError as e:
            self.skipTest(f"Modules d'IA non disponibles: {str(e)}")
    
    def test_module_import(self):
        """
        Test de l'importation des modules d'IA
        """
        # Vérifier que les modules ont été importés correctement
        self.assertIsNotNone(self.llm_provider_class, "La classe LLMProvider n'a pas pu être importée")
        self.assertIsNotNone(self.token_analyzer_class, "La classe TokenAnalyzer n'a pas pu être importée")
        self.assertIsNotNone(self.market_analyzer_class, "La classe MarketAnalyzer n'a pas pu être importée")
        self.assertIsNotNone(self.risk_evaluator_class, "La classe RiskEvaluator n'a pas pu être importée")
    
    @patch("gbpbot.ai.llm_provider.LLMProvider._initialize_providers")
    def test_llm_provider_initialization(self, mock_initialize_providers):
        """
        Test de l'initialisation du fournisseur de modèles de langage
        """
        # Configurer le mock
        mock_initialize_providers.return_value = True
        
        # Instancier le fournisseur de LLM
        llm_provider = self.llm_provider_class(self.test_ai_config)
        
        # Vérifier l'initialisation
        self.assertIsNotNone(llm_provider, "Le fournisseur de LLM n'a pas été instancié correctement")
        self.assertTrue(mock_initialize_providers.called, "La méthode d'initialisation des fournisseurs n'a pas été appelée")
        self.assertEqual(llm_provider.config, self.test_ai_config, "La configuration n'a pas été correctement assignée")
    
    @patch("gbpbot.ai.llm_provider.LLMProvider._call_openai_api")
    @patch("gbpbot.ai.llm_provider.LLMProvider._initialize_providers")
    def test_llm_provider_query(self, mock_initialize_providers, mock_call_openai_api):
        """
        Test de l'envoi de requêtes au fournisseur de LLM
        """
        # Configurer les mocks
        mock_initialize_providers.return_value = True
        mock_call_openai_api.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "Voici une réponse de test du modèle d'IA."
                    }
                }
            ]
        }
        
        # Instancier le fournisseur de LLM
        llm_provider = self.llm_provider_class(self.test_ai_config)
        
        # Simuler une requête au LLM
        prompt = "Analyser ce token: $TTK"
        response = llm_provider.query(prompt)
        
        # Vérifier la réponse
        self.assertIsNotNone(response, "La réponse du LLM est nulle")
        self.assertTrue(mock_call_openai_api.called, "L'API OpenAI n'a pas été appelée")
        self.assertEqual(mock_call_openai_api.call_args[0][0], prompt, "Le prompt n'a pas été correctement passé à l'API")
    
    @patch("gbpbot.ai.token_analyzer.TokenAnalyzer._initialize_model")
    def test_token_analyzer_initialization(self, mock_initialize_model):
        """
        Test de l'initialisation de l'analyseur de tokens
        """
        # Configurer le mock
        mock_initialize_model.return_value = True
        
        # Instancier l'analyseur de tokens
        token_analyzer = self.token_analyzer_class(self.test_ai_config, llm_provider=MagicMock())
        
        # Vérifier l'initialisation
        self.assertIsNotNone(token_analyzer, "L'analyseur de tokens n'a pas été instancié correctement")
        self.assertTrue(mock_initialize_model.called, "La méthode d'initialisation du modèle n'a pas été appelée")
    
    @patch("gbpbot.ai.token_analyzer.TokenAnalyzer._analyze_contract_code")
    @patch("gbpbot.ai.token_analyzer.TokenAnalyzer._check_token_metrics")
    @patch("gbpbot.ai.token_analyzer.TokenAnalyzer._initialize_model")
    def test_token_analyzer_analyze(self, mock_initialize_model, mock_check_metrics, mock_analyze_code):
        """
        Test de l'analyse d'un token
        """
        # Configurer les mocks
        mock_initialize_model.return_value = True
        mock_check_metrics.return_value = {
            "liquidity_score": 0.8,
            "age_score": 0.6,
            "holder_score": 0.7,
            "overall_metric_score": 0.7
        }
        mock_analyze_code.return_value = {
            "has_honeypot_features": False,
            "has_rug_pull_features": False,
            "security_score": 0.85,
            "risks": []
        }
        
        # Instancier l'analyseur de tokens
        token_analyzer = self.token_analyzer_class(self.test_ai_config, llm_provider=MagicMock())
        
        # Analyser un token de test
        analysis_result = token_analyzer.analyze_token(self.test_token_data)
        
        # Vérifier les résultats de l'analyse
        self.assertIsNotNone(analysis_result, "Le résultat d'analyse est nul")
        self.assertIn("security_score", analysis_result, "Score de sécurité manquant dans l'analyse")
        self.assertIn("overall_score", analysis_result, "Score global manquant dans l'analyse")
        self.assertIn("risks", analysis_result, "Risques manquants dans l'analyse")
        self.assertIn("recommendation", analysis_result, "Recommandation manquante dans l'analyse")
    
    @patch("gbpbot.ai.market_analyzer.MarketAnalyzer._initialize_model")
    def test_market_analyzer_initialization(self, mock_initialize_model):
        """
        Test de l'initialisation de l'analyseur de marché
        """
        # Configurer le mock
        mock_initialize_model.return_value = True
        
        # Instancier l'analyseur de marché
        market_analyzer = self.market_analyzer_class(self.test_ai_config, llm_provider=MagicMock())
        
        # Vérifier l'initialisation
        self.assertIsNotNone(market_analyzer, "L'analyseur de marché n'a pas été instancié correctement")
        self.assertTrue(mock_initialize_model.called, "La méthode d'initialisation du modèle n'a pas été appelée")
    
    @patch("gbpbot.ai.market_analyzer.MarketAnalyzer._predict_trend")
    @patch("gbpbot.ai.market_analyzer.MarketAnalyzer._analyze_market_conditions")
    @patch("gbpbot.ai.market_analyzer.MarketAnalyzer._initialize_model")
    def test_market_analyzer_analyze(self, mock_initialize_model, mock_analyze_conditions, mock_predict_trend):
        """
        Test de l'analyse du marché
        """
        # Configurer les mocks
        mock_initialize_model.return_value = True
        mock_analyze_conditions.return_value = {
            "market_sentiment_score": 0.8,
            "liquidity_score": 0.7,
            "volume_score": 0.9,
            "overall_market_score": 0.8
        }
        mock_predict_trend.return_value = {
            "predicted_direction": "up",
            "confidence": 0.75,
            "timeframe": "24h"
        }
        
        # Instancier l'analyseur de marché
        market_analyzer = self.market_analyzer_class(self.test_ai_config, llm_provider=MagicMock())
        
        # Analyser le marché de test
        analysis_result = market_analyzer.analyze_market_context(self.test_market_context)
        
        # Vérifier les résultats de l'analyse
        self.assertIsNotNone(analysis_result, "Le résultat d'analyse est nul")
        self.assertIn("market_score", analysis_result, "Score de marché manquant dans l'analyse")
        self.assertIn("trend_prediction", analysis_result, "Prédiction de tendance manquante dans l'analyse")
        self.assertIn("opportunities", analysis_result, "Opportunités manquantes dans l'analyse")
        self.assertIn("recommendation", analysis_result, "Recommandation manquante dans l'analyse")
    
    @patch("gbpbot.ai.risk_evaluator.RiskEvaluator._initialize_model")
    def test_risk_evaluator_initialization(self, mock_initialize_model):
        """
        Test de l'initialisation de l'évaluateur de risques
        """
        # Configurer le mock
        mock_initialize_model.return_value = True
        
        # Instancier l'évaluateur de risques
        risk_evaluator = self.risk_evaluator_class(self.test_ai_config, llm_provider=MagicMock())
        
        # Vérifier l'initialisation
        self.assertIsNotNone(risk_evaluator, "L'évaluateur de risques n'a pas été instancié correctement")
        self.assertTrue(mock_initialize_model.called, "La méthode d'initialisation du modèle n'a pas été appelée")
    
    @patch("gbpbot.ai.risk_evaluator.RiskEvaluator._analyze_contract_risks")
    @patch("gbpbot.ai.risk_evaluator.RiskEvaluator._evaluate_social_signals")
    @patch("gbpbot.ai.risk_evaluator.RiskEvaluator._initialize_model")
    def test_risk_evaluator_evaluate(self, mock_initialize_model, mock_evaluate_social, mock_analyze_risks):
        """
        Test de l'évaluation des risques d'un token
        """
        # Configurer les mocks
        mock_initialize_model.return_value = True
        mock_evaluate_social.return_value = {
            "social_sentiment": "positive",
            "community_strength": 0.7,
            "developer_activity": 0.6,
            "social_score": 0.75
        }
        mock_analyze_risks.return_value = {
            "code_risks": ["moderate_risk_of_fee_changes"],
            "ownership_risks": ["single_owner_controls_50_percent"],
            "liquidity_risks": ["low_liquidity_for_market_cap"],
            "risk_score": 0.4
        }
        
        # Instancier l'évaluateur de risques
        risk_evaluator = self.risk_evaluator_class(self.test_ai_config, llm_provider=MagicMock())
        
        # Évaluer les risques d'un token de test
        risk_assessment = risk_evaluator.evaluate_token_risks(self.test_token_data, self.test_market_context)
        
        # Vérifier les résultats de l'évaluation
        self.assertIsNotNone(risk_assessment, "L'évaluation des risques est nulle")
        self.assertIn("risk_score", risk_assessment, "Score de risque manquant dans l'évaluation")
        self.assertIn("identified_risks", risk_assessment, "Risques identifiés manquants dans l'évaluation")
        self.assertIn("safety_level", risk_assessment, "Niveau de sécurité manquant dans l'évaluation")
        self.assertIn("recommendation", risk_assessment, "Recommandation manquante dans l'évaluation")


if __name__ == "__main__":
    unittest.main() 