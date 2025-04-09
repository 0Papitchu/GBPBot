#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests unitaires pour le module de backtesting du GBPBot

Ce module teste les fonctionnalités du module de backtesting,
qui permet de simuler et tester les stratégies sur des données historiques.
"""

import os
import sys
import json
import unittest
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Ajout du chemin racine au sys.path pour les imports
ROOT_DIR = Path(__file__).parent.parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Import des modules de test
from gbpbot.tests.setup_test_environment import setup_test_environment, cleanup_test_environment


class TestBacktestingModule(unittest.TestCase):
    """Suite de tests pour le module de backtesting du GBPBot"""
    
    @classmethod
    def setUpClass(cls):
        """
        Préparation de l'environnement de test avant l'exécution des tests
        """
        # Configuration de l'environnement de test
        cls.env_file, cls.wallet_paths = setup_test_environment()
        
        # Configuration de test pour le backtesting
        cls.test_config = {
            "data": {
                "source": "csv",
                "path": "test_data",
                "symbols": ["AVAX-USDC", "AVAX-USDT"],
                "timeframe": "1h",
                "start_date": "2023-01-01",
                "end_date": "2023-01-31"
            },
            "simulation": {
                "initial_balance": 10000,  # USDC
                "fee_rate": 0.1,  # 0.1%
                "slippage": 0.2,  # 0.2%
                "latency": 500,  # 500ms
                "gas_price": 30,  # 30 Gwei
                "max_trade_amount": 1000  # USDC
            },
            "strategy": {
                "name": "arbitrage",
                "min_profit_threshold": 0.5,
                "max_slippage": 1.0,
                "gas_price_multiplier": 1.2,
                "transaction_timeout": 30
            },
            "report": {
                "save_trades": True,
                "save_metrics": True,
                "plot_results": True,
                "output_dir": "backtest_results"
            }
        }
        
        # Création de données historiques fictives pour le test
        cls.start_date = datetime.strptime(cls.test_config["data"]["start_date"], "%Y-%m-%d")
        cls.end_date = datetime.strptime(cls.test_config["data"]["end_date"], "%Y-%m-%d")
        
        # Création des données pour AVAX-USDC
        cls.avax_usdc_data = cls._create_test_price_data(
            start_date=cls.start_date,
            end_date=cls.end_date,
            base_price=30.0,
            volatility=0.05,
            timeframe="1h"
        )
        
        # Création des données pour AVAX-USDT
        cls.avax_usdt_data = cls._create_test_price_data(
            start_date=cls.start_date,
            end_date=cls.end_date,
            base_price=30.2,  # Léger écart pour créer des opportunités d'arbitrage
            volatility=0.05,
            timeframe="1h"
        )
    
    @classmethod
    def tearDownClass(cls):
        """
        Nettoyage après l'exécution de tous les tests
        """
        # Nettoyer l'environnement de test
        cleanup_test_environment(cls.env_file, cls.wallet_paths)
    
    @classmethod
    def _create_test_price_data(cls, start_date, end_date, base_price, volatility, timeframe):
        """
        Crée des données de prix fictives pour les tests
        
        Args:
            start_date: Date de début
            end_date: Date de fin
            base_price: Prix de base
            volatility: Volatilité du prix
            timeframe: Intervalle de temps entre chaque donnée
        
        Returns:
            DataFrame: Données de prix fictives
        """
        # Déterminer le nombre d'heures entre start_date et end_date
        delta = end_date - start_date
        hours = int(delta.total_seconds() / 3600) + 1
        
        # Générer des timestamps
        timestamps = [start_date + timedelta(hours=i) for i in range(hours)]
        
        # Générer des prix avec une marche aléatoire
        np.random.seed(42)  # Pour la reproductibilité
        price_changes = np.random.normal(0, volatility, hours)
        prices = [base_price]
        
        for change in price_changes[1:]:
            new_price = prices[-1] * (1 + change)
            prices.append(new_price)
        
        # Créer des données OHLCV
        data = []
        for i in range(hours):
            # Ajouter un peu de variation aux prix OHLC
            price = prices[i]
            high = price * (1 + np.random.uniform(0, volatility/2))
            low = price * (1 - np.random.uniform(0, volatility/2))
            open_price = price * (1 + np.random.uniform(-volatility/4, volatility/4))
            close = price
            volume = np.random.uniform(1000, 10000)
            
            data.append({
                "timestamp": timestamps[i],
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume
            })
        
        return pd.DataFrame(data)
    
    def setUp(self):
        """
        Préparation avant chaque test
        """
        # Tenter d'importer les modules de backtesting, avec gestion des erreurs
        try:
            from gbpbot.backtesting.backtesting_engine import BacktestingEngine
            from gbpbot.backtesting.data_loader import DataLoader
            from gbpbot.backtesting.market_simulator import MarketSimulator
            from gbpbot.backtesting.performance_analyzer import PerformanceAnalyzer
            from gbpbot.backtesting.parameter_optimizer import ParameterOptimizer
            from gbpbot.backtesting.base_strategy import BaseStrategy
            
            self.backtesting_engine_class = BacktestingEngine
            self.data_loader_class = DataLoader
            self.market_simulator_class = MarketSimulator
            self.performance_analyzer_class = PerformanceAnalyzer
            self.parameter_optimizer_class = ParameterOptimizer
            self.base_strategy_class = BaseStrategy
        except ImportError as e:
            self.skipTest(f"Modules de backtesting non disponibles: {str(e)}")
    
    def test_module_import(self):
        """
        Test de l'importation des modules de backtesting
        """
        # Vérifier que les modules ont été importés correctement
        self.assertIsNotNone(self.backtesting_engine_class, "La classe BacktestingEngine n'a pas pu être importée")
        self.assertIsNotNone(self.data_loader_class, "La classe DataLoader n'a pas pu être importée")
        self.assertIsNotNone(self.market_simulator_class, "La classe MarketSimulator n'a pas pu être importée")
        self.assertIsNotNone(self.performance_analyzer_class, "La classe PerformanceAnalyzer n'a pas pu être importée")
        self.assertIsNotNone(self.parameter_optimizer_class, "La classe ParameterOptimizer n'a pas pu être importée")
        self.assertIsNotNone(self.base_strategy_class, "La classe BaseStrategy n'a pas pu être importée")
    
    @patch("gbpbot.backtesting.data_loader.DataLoader")
    @patch("gbpbot.backtesting.market_simulator.MarketSimulator")
    @patch("gbpbot.backtesting.performance_analyzer.PerformanceAnalyzer")
    def test_backtesting_engine_initialization(self, mock_analyzer, mock_simulator, mock_loader):
        """
        Test de l'initialisation du moteur de backtesting
        """
        # Configurer les mocks
        mock_loader.return_value = MagicMock()
        mock_simulator.return_value = MagicMock()
        mock_analyzer.return_value = MagicMock()
        
        # Instancier le moteur de backtesting
        backtesting_engine = self.backtesting_engine_class(self.test_config)
        
        # Vérifier l'initialisation
        self.assertIsNotNone(backtesting_engine, "Le moteur de backtesting n'a pas été instancié correctement")
        self.assertEqual(backtesting_engine.config, self.test_config, "La configuration n'a pas été correctement assignée")
        
        # Vérifier que les composants ont été initialisés
        self.assertTrue(mock_loader.called, "Le chargeur de données n'a pas été initialisé")
        self.assertTrue(mock_simulator.called, "Le simulateur de marché n'a pas été initialisé")
        self.assertTrue(mock_analyzer.called, "L'analyseur de performances n'a pas été initialisé")
    
    @patch("gbpbot.backtesting.data_loader.DataLoader.load_data")
    def test_data_loader(self, mock_load_data):
        """
        Test du chargeur de données
        """
        # Configurer le mock
        mock_data = {
            "AVAX-USDC": self.avax_usdc_data,
            "AVAX-USDT": self.avax_usdt_data
        }
        mock_load_data.return_value = mock_data
        
        # Instancier le chargeur de données
        data_loader = self.data_loader_class(self.test_config["data"])
        
        # Charger les données
        data = data_loader.load_data()
        
        # Vérifier que les données ont été chargées
        self.assertTrue(mock_load_data.called, "La méthode load_data n'a pas été appelée")
        self.assertEqual(data, mock_data, "Les données n'ont pas été chargées correctement")
        
        # Vérifier la structure des données
        for symbol, df in data.items():
            self.assertIn(symbol, self.test_config["data"]["symbols"], f"Symbole inconnu: {symbol}")
            self.assertIsInstance(df, pd.DataFrame, f"Les données pour {symbol} ne sont pas un DataFrame")
            self.assertIn("timestamp", df.columns, "La colonne 'timestamp' est manquante")
            self.assertIn("open", df.columns, "La colonne 'open' est manquante")
            self.assertIn("high", df.columns, "La colonne 'high' est manquante")
            self.assertIn("low", df.columns, "La colonne 'low' est manquante")
            self.assertIn("close", df.columns, "La colonne 'close' est manquante")
            self.assertIn("volume", df.columns, "La colonne 'volume' est manquante")
    
    def test_market_simulator(self):
        """
        Test du simulateur de marché
        """
        # Instancier le simulateur de marché
        simulator = self.market_simulator_class(self.test_config["simulation"])
        
        # Vérifier l'initialisation
        self.assertIsNotNone(simulator, "Le simulateur de marché n'a pas été instancié correctement")
        self.assertEqual(simulator.initial_balance, self.test_config["simulation"]["initial_balance"], 
                       "Le solde initial n'a pas été correctement assigné")
        self.assertEqual(simulator.fee_rate, self.test_config["simulation"]["fee_rate"]/100, 
                       "Le taux de frais n'a pas été correctement assigné")
        self.assertEqual(simulator.slippage, self.test_config["simulation"]["slippage"]/100, 
                       "Le slippage n'a pas été correctement assigné")
        
        # Tester l'exécution d'un ordre d'achat
        order = {
            "type": "buy",
            "symbol": "AVAX-USDC",
            "price": 30.0,
            "amount": 1.0,  # 1 AVAX
            "timestamp": datetime.now()
        }
        
        trade = simulator.execute_order(order, self.avax_usdc_data)
        
        # Vérifier le résultat de l'exécution
        self.assertIsNotNone(trade, "Le résultat de l'exécution est nul")
        self.assertEqual(trade["type"], "buy", "Le type d'ordre n'a pas été conservé")
        self.assertEqual(trade["symbol"], "AVAX-USDC", "Le symbole n'a pas été conservé")
        self.assertAlmostEqual(trade["price"], 30.0 * (1 + simulator.slippage), 
                              places=2, msg="Le prix n'a pas été ajusté correctement avec le slippage")
        self.assertEqual(trade["amount"], 1.0, "La quantité n'a pas été conservée")
        self.assertIn("cost", trade, "Le coût n'a pas été calculé")
        self.assertIn("fee", trade, "Les frais n'ont pas été calculés")
        
        # Tester la mise à jour du portefeuille
        portfolio = {"USDC": 10000, "AVAX": 0}
        updated_portfolio = simulator.update_portfolio(portfolio, trade)
        
        # Vérifier la mise à jour du portefeuille
        self.assertIsNotNone(updated_portfolio, "Le portefeuille mis à jour est nul")
        self.assertLess(updated_portfolio["USDC"], portfolio["USDC"], "Le solde USDC n'a pas diminué après l'achat")
        self.assertGreater(updated_portfolio["AVAX"], portfolio["AVAX"], "Le solde AVAX n'a pas augmenté après l'achat")
    
    def test_performance_analyzer(self):
        """
        Test de l'analyseur de performances
        """
        # Créer des trades fictifs
        trades = [
            {
                "type": "buy",
                "symbol": "AVAX-USDC",
                "price": 30.0,
                "amount": 1.0,
                "cost": 30.0,
                "fee": 0.03,
                "timestamp": datetime(2023, 1, 1, 10, 0, 0)
            },
            {
                "type": "sell",
                "symbol": "AVAX-USDC",
                "price": 32.0,
                "amount": 1.0,
                "cost": 32.0,
                "fee": 0.032,
                "timestamp": datetime(2023, 1, 1, 14, 0, 0)
            },
            {
                "type": "buy",
                "symbol": "AVAX-USDC",
                "price": 31.0,
                "amount": 1.0,
                "cost": 31.0,
                "fee": 0.031,
                "timestamp": datetime(2023, 1, 2, 10, 0, 0)
            },
            {
                "type": "sell",
                "symbol": "AVAX-USDC",
                "price": 30.0,
                "amount": 1.0,
                "cost": 30.0,
                "fee": 0.03,
                "timestamp": datetime(2023, 1, 2, 14, 0, 0)
            }
        ]
        
        # Créer un historique du portefeuille fictif
        portfolio_history = [
            {"timestamp": datetime(2023, 1, 1, 0, 0, 0), "USDC": 10000, "AVAX": 0, "total_value_usdc": 10000},
            {"timestamp": datetime(2023, 1, 1, 10, 0, 0), "USDC": 9970, "AVAX": 1, "total_value_usdc": 10000},
            {"timestamp": datetime(2023, 1, 1, 14, 0, 0), "USDC": 10002, "AVAX": 0, "total_value_usdc": 10002},
            {"timestamp": datetime(2023, 1, 2, 10, 0, 0), "USDC": 9971, "AVAX": 1, "total_value_usdc": 10002},
            {"timestamp": datetime(2023, 1, 2, 14, 0, 0), "USDC": 10001, "AVAX": 0, "total_value_usdc": 10001}
        ]
        
        # Instancier l'analyseur de performances
        analyzer = self.performance_analyzer_class(self.test_config["report"])
        
        # Analyser les performances
        metrics = analyzer.calculate_metrics(trades, portfolio_history, self.test_config["simulation"]["initial_balance"])
        
        # Vérifier les métriques de base
        self.assertIsNotNone(metrics, "Les métriques sont nulles")
        self.assertIn("total_profit", metrics, "Le profit total est manquant")
        self.assertIn("profit_percent", metrics, "Le pourcentage de profit est manquant")
        self.assertIn("winning_trades", metrics, "Le nombre de trades gagnants est manquant")
        self.assertIn("losing_trades", metrics, "Le nombre de trades perdants est manquant")
        self.assertIn("win_rate", metrics, "Le taux de réussite est manquant")
        self.assertIn("max_drawdown", metrics, "Le drawdown maximum est manquant")
        
        # Vérifier les valeurs des métriques
        self.assertEqual(metrics["total_trades"], 4, "Le nombre total de trades est incorrect")
        self.assertEqual(metrics["winning_trades"], 2, "Le nombre de trades gagnants est incorrect")
        self.assertEqual(metrics["losing_trades"], 2, "Le nombre de trades perdants est incorrect")
        self.assertAlmostEqual(metrics["win_rate"], 0.5, places=2, msg="Le taux de réussite est incorrect")
        
        # Vérifier que le profit est correct
        expected_profit = 1.0  # (32 - 30) + (30 - 31) = +2 - 1 = +1
        expected_profit_percent = expected_profit / self.test_config["simulation"]["initial_balance"] * 100
        self.assertAlmostEqual(metrics["total_profit"], expected_profit, 
                              places=2, msg="Le profit total est incorrect")
        self.assertAlmostEqual(metrics["profit_percent"], expected_profit_percent, 
                              places=2, msg="Le pourcentage de profit est incorrect")
    
    @patch("gbpbot.backtesting.parameter_optimizer.ParameterOptimizer._run_backtest")
    def test_parameter_optimizer(self, mock_run_backtest):
        """
        Test de l'optimiseur de paramètres
        """
        # Configurer le mock
        mock_run_backtest.return_value = {
            "total_profit": 100,
            "profit_percent": 1.0,
            "win_rate": 0.6,
            "max_drawdown": 0.2,
            "sharpe_ratio": 1.5
        }
        
        # Paramètres à optimiser
        params_to_optimize = {
            "min_profit_threshold": [0.3, 0.5, 0.7],
            "max_slippage": [0.5, 1.0, 1.5]
        }
        
        # Instancier l'optimiseur de paramètres
        optimizer = self.parameter_optimizer_class(self.test_config)
        
        # Optimiser les paramètres
        best_params, best_result = optimizer.optimize(params_to_optimize, objective="profit_percent")
        
        # Vérifier que l'optimiseur a fonctionné
        self.assertTrue(mock_run_backtest.called, "La méthode _run_backtest n'a pas été appelée")
        self.assertEqual(mock_run_backtest.call_count, len(params_to_optimize["min_profit_threshold"]) * len(params_to_optimize["max_slippage"]),
                       "Le nombre d'appels à _run_backtest n'est pas correct")
        
        # Vérifier les meilleurs paramètres
        self.assertIsNotNone(best_params, "Les meilleurs paramètres sont nuls")
        self.assertIn("min_profit_threshold", best_params, "Le paramètre min_profit_threshold est manquant")
        self.assertIn("max_slippage", best_params, "Le paramètre max_slippage est manquant")
        
        # Vérifier le meilleur résultat
        self.assertIsNotNone(best_result, "Le meilleur résultat est nul")
        self.assertEqual(best_result, mock_run_backtest.return_value, "Le meilleur résultat n'est pas correct")
    
    @patch("gbpbot.backtesting.base_strategy.BaseStrategy.initialize")
    @patch("gbpbot.backtesting.base_strategy.BaseStrategy.process_tick")
    def test_base_strategy(self, mock_process_tick, mock_initialize):
        """
        Test de la stratégie de base
        """
        # Configurer les mocks
        mock_initialize.return_value = None
        mock_process_tick.return_value = {
            "action": "buy",
            "symbol": "AVAX-USDC",
            "price": 30.0,
            "amount": 1.0,
            "reason": "Test strategy signal"
        }
        
        # Instancier la stratégie de base
        strategy = self.base_strategy_class(self.test_config["strategy"])
        
        # Initialiser la stratégie
        strategy.initialize()
        
        # Vérifier l'initialisation
        self.assertTrue(mock_initialize.called, "La méthode initialize n'a pas été appelée")
        
        # Créer un tick fictif
        tick = {
            "timestamp": datetime.now(),
            "AVAX-USDC": {
                "open": 29.8,
                "high": 30.2,
                "low": 29.7,
                "close": 30.0,
                "volume": 5000
            },
            "AVAX-USDT": {
                "open": 30.0,
                "high": 30.4,
                "low": 29.9,
                "close": 30.2,
                "volume": 4800
            }
        }
        
        # Traiter le tick
        signal = strategy.process_tick(tick)
        
        # Vérifier le traitement du tick
        self.assertTrue(mock_process_tick.called, "La méthode process_tick n'a pas été appelée")
        self.assertEqual(mock_process_tick.call_args[0][0], tick, "Le tick n'a pas été correctement passé à process_tick")
        
        # Vérifier le signal généré
        self.assertIsNotNone(signal, "Le signal est nul")
        self.assertEqual(signal, mock_process_tick.return_value, "Le signal n'est pas correct")
    
    @patch("gbpbot.backtesting.backtesting_engine.BacktestingEngine.run")
    @patch("gbpbot.backtesting.data_loader.DataLoader")
    @patch("gbpbot.backtesting.market_simulator.MarketSimulator")
    @patch("gbpbot.backtesting.performance_analyzer.PerformanceAnalyzer")
    def test_backtesting_run(self, mock_analyzer, mock_simulator, mock_loader, mock_run):
        """
        Test de l'exécution du backtesting
        """
        # Configurer les mocks
        mock_loader.return_value = MagicMock()
        mock_simulator.return_value = MagicMock()
        mock_analyzer.return_value = MagicMock()
        
        mock_run.return_value = {
            "metrics": {
                "total_profit": 100,
                "profit_percent": 1.0,
                "win_rate": 0.6,
                "max_drawdown": 0.2,
                "sharpe_ratio": 1.5
            },
            "trades": [
                {
                    "type": "buy",
                    "symbol": "AVAX-USDC",
                    "price": 30.0,
                    "amount": 1.0,
                    "timestamp": datetime(2023, 1, 1, 10, 0, 0)
                },
                {
                    "type": "sell",
                    "symbol": "AVAX-USDC",
                    "price": 32.0,
                    "amount": 1.0,
                    "timestamp": datetime(2023, 1, 1, 14, 0, 0)
                }
            ],
            "portfolio_history": [
                {"timestamp": datetime(2023, 1, 1, 0, 0, 0), "USDC": 10000, "AVAX": 0, "total_value_usdc": 10000},
                {"timestamp": datetime(2023, 1, 1, 10, 0, 0), "USDC": 9970, "AVAX": 1, "total_value_usdc": 10000},
                {"timestamp": datetime(2023, 1, 1, 14, 0, 0), "USDC": 10002, "AVAX": 0, "total_value_usdc": 10002}
            ]
        }
        
        # Instancier le moteur de backtesting
        backtesting_engine = self.backtesting_engine_class(self.test_config)
        
        # Exécuter le backtesting
        result = backtesting_engine.run()
        
        # Vérifier l'exécution
        self.assertTrue(mock_run.called, "La méthode run n'a pas été appelée")
        
        # Vérifier le résultat
        self.assertIsNotNone(result, "Le résultat du backtesting est nul")
        self.assertEqual(result, mock_run.return_value, "Le résultat du backtesting n'est pas correct")
        self.assertIn("metrics", result, "Les métriques sont manquantes dans le résultat")
        self.assertIn("trades", result, "Les trades sont manquants dans le résultat")
        self.assertIn("portfolio_history", result, "L'historique du portefeuille est manquant dans le résultat")


if __name__ == "__main__":
    unittest.main() 