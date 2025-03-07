#!/usr/bin/env python3
"""
Module d'intégration pour le système de backtesting de GBPBot.

Ce module fournit une interface unifiée pour exécuter des backtests complets
en intégrant les différents composants du système de backtesting :
- Chargement des données historiques
- Simulation du marché
- Exécution des stratégies
- Analyse des performances
- Optimisation des paramètres
"""

import os
import json
import logging
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from datetime import datetime, timedelta
import concurrent.futures
import matplotlib.pyplot as plt
from pathlib import Path

# Importation des composants du système de backtesting
from gbpbot.backtesting.data_loader import DataLoader
from gbpbot.backtesting.market_simulator import MarketSimulator
from gbpbot.backtesting.performance_analyzer import PerformanceAnalyzer
from gbpbot.backtesting.parameter_optimizer import ParameterOptimizer
from gbpbot.utils.exceptions import BacktestingError
from gbpbot.utils.config import Config

# Configuration du logger
logger = logging.getLogger(__name__)

class BacktestingEngine:
    """
    Moteur de backtesting principal qui intègre tous les composants.
    
    Cette classe fournit une interface unifiée pour exécuter des backtests
    complets et analyser les résultats.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialise le moteur de backtesting.
        
        Args:
            config: Configuration pour le moteur de backtesting
        """
        self.config = config
        
        # Paramètres de base
        self.results_dir = config.get("RESULTS_DIR", "backtest_results")
        self.data_dir = config.get("DATA_DIR", "historical_data")
        self.report_dir = config.get("REPORT_DIR", "backtest_reports")
        
        # Créer les répertoires s'ils n'existent pas
        for directory in [self.results_dir, self.data_dir, self.report_dir]:
            os.makedirs(directory, exist_ok=True)
        
        # Initialiser les composants
        self.data_loader = DataLoader(config)
        self.market_simulator = MarketSimulator(config)
        self.performance_analyzer = PerformanceAnalyzer(config)
        self.parameter_optimizer = ParameterOptimizer(config)
        
        # État du backtest
        self.current_backtest_id = None
        self.current_results = None
        
        logger.info("Moteur de backtesting initialisé")
    
    def run_backtest(self, strategy_class, strategy_params: Dict[str, Any], 
                   symbols: List[str], start_date: str, end_date: str,
                   initial_balance: Dict[str, float], timeframe: str = "1m",
                   data_source: str = "binance") -> Dict[str, Any]:
        """
        Exécute un backtest complet pour une stratégie donnée.
        
        Args:
            strategy_class: Classe de la stratégie à tester
            strategy_params: Paramètres de la stratégie
            symbols: Liste des symboles à trader
            start_date: Date de début du backtest (format: "YYYY-MM-DD")
            end_date: Date de fin du backtest (format: "YYYY-MM-DD")
            initial_balance: Solde initial pour chaque actif
            timeframe: Intervalle de temps pour les données
            data_source: Source des données historiques
            
        Returns:
            Résultats du backtest
        """
        try:
            # Générer un ID unique pour ce backtest
            self.current_backtest_id = f"backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            backtest_dir = os.path.join(self.results_dir, self.current_backtest_id)
            os.makedirs(backtest_dir, exist_ok=True)
            
            logger.info(f"Démarrage du backtest {self.current_backtest_id}")
            logger.info(f"Stratégie: {strategy_class.__name__}, Symboles: {symbols}, Période: {start_date} à {end_date}")
            
            # 1. Charger les données historiques
            logger.info("Chargement des données historiques...")
            data = {}
            for symbol in symbols:
                data[symbol] = self.data_loader.load_data(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    timeframe=timeframe,
                    source=data_source
                )
                
                # Sauvegarder les données pour référence
                data_path = os.path.join(backtest_dir, f"{symbol}_{timeframe}.csv")
                data[symbol].to_csv(data_path)
                logger.info(f"Données sauvegardées dans {data_path}")
            
            # 2. Initialiser le simulateur de marché
            logger.info("Initialisation du simulateur de marché...")
            self.market_simulator.initialize_balances(initial_balance)
            for symbol, df in data.items():
                self.market_simulator.load_market_data(symbol, df)
            
            # 3. Initialiser la stratégie
            logger.info("Initialisation de la stratégie...")
            strategy = strategy_class(self.market_simulator, **strategy_params)
            
            # 4. Exécuter la simulation
            logger.info("Exécution de la simulation...")
            simulation_results = self.market_simulator.run_simulation(
                strategy=strategy,
                start_date=datetime.strptime(start_date, "%Y-%m-%d"),
                end_date=datetime.strptime(end_date, "%Y-%m-%d")
            )
            
            # 5. Analyser les performances
            logger.info("Analyse des performances...")
            performance_results = self.performance_analyzer.analyze(
                trades=simulation_results["trades"],
                equity_curve=simulation_results["equity_curve"],
                initial_balance=initial_balance
            )
            
            # 6. Générer un rapport
            logger.info("Génération du rapport...")
            report_path = os.path.join(self.report_dir, f"{self.current_backtest_id}_report.html")
            self.performance_analyzer.generate_report(
                trades=simulation_results["trades"],
                equity_curve=simulation_results["equity_curve"],
                performance_metrics=performance_results,
                strategy_name=strategy_class.__name__,
                strategy_params=strategy_params,
                symbols=symbols,
                start_date=start_date,
                end_date=end_date,
                timeframe=timeframe,
                report_path=report_path
            )
            
            # 7. Sauvegarder les résultats complets
            results = {
                "backtest_id": self.current_backtest_id,
                "strategy": strategy_class.__name__,
                "strategy_params": strategy_params,
                "symbols": symbols,
                "start_date": start_date,
                "end_date": end_date,
                "timeframe": timeframe,
                "initial_balance": initial_balance,
                "final_balance": simulation_results["final_balance"],
                "trades": simulation_results["trades"],
                "equity_curve": simulation_results["equity_curve"].to_dict(),
                "performance_metrics": performance_results,
                "report_path": report_path
            }
            
            results_path = os.path.join(backtest_dir, "results.json")
            with open(results_path, "w") as f:
                json.dump(results, f, indent=4, default=str)
            
            logger.info(f"Backtest terminé. Résultats sauvegardés dans {results_path}")
            logger.info(f"Rapport généré dans {report_path}")
            
            # Stocker les résultats actuels
            self.current_results = results
            
            return results
            
        except Exception as e:
            logger.error(f"Erreur lors du backtest: {e}", exc_info=True)
            raise BacktestingError(f"Erreur lors du backtest: {e}")
    
    def compare_strategies(self, strategies: List[Tuple[Any, Dict[str, Any]]], 
                         symbols: List[str], start_date: str, end_date: str,
                         initial_balance: Dict[str, float], timeframe: str = "1m",
                         data_source: str = "binance") -> Dict[str, Any]:
        """
        Compare plusieurs stratégies sur les mêmes données.
        
        Args:
            strategies: Liste de tuples (classe de stratégie, paramètres)
            symbols: Liste des symboles à trader
            start_date: Date de début du backtest
            end_date: Date de fin du backtest
            initial_balance: Solde initial pour chaque actif
            timeframe: Intervalle de temps pour les données
            data_source: Source des données historiques
            
        Returns:
            Résultats de la comparaison
        """
        try:
            # Générer un ID unique pour cette comparaison
            comparison_id = f"comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            comparison_dir = os.path.join(self.results_dir, comparison_id)
            os.makedirs(comparison_dir, exist_ok=True)
            
            logger.info(f"Démarrage de la comparaison {comparison_id}")
            logger.info(f"Nombre de stratégies: {len(strategies)}, Symboles: {symbols}, Période: {start_date} à {end_date}")
            
            # Exécuter les backtests pour chaque stratégie
            results = []
            for strategy_class, strategy_params in strategies:
                backtest_result = self.run_backtest(
                    strategy_class=strategy_class,
                    strategy_params=strategy_params,
                    symbols=symbols,
                    start_date=start_date,
                    end_date=end_date,
                    initial_balance=initial_balance,
                    timeframe=timeframe,
                    data_source=data_source
                )
                results.append(backtest_result)
            
            # Comparer les résultats
            comparison_results = self._compare_results(results)
            
            # Générer un rapport de comparaison
            report_path = os.path.join(self.report_dir, f"{comparison_id}_comparison_report.html")
            self._generate_comparison_report(results, report_path)
            
            # Sauvegarder les résultats de la comparaison
            comparison_data = {
                "comparison_id": comparison_id,
                "strategies": [r["strategy"] for r in results],
                "symbols": symbols,
                "start_date": start_date,
                "end_date": end_date,
                "timeframe": timeframe,
                "initial_balance": initial_balance,
                "comparison_results": comparison_results,
                "individual_results": [r["backtest_id"] for r in results],
                "report_path": report_path
            }
            
            results_path = os.path.join(comparison_dir, "comparison_results.json")
            with open(results_path, "w") as f:
                json.dump(comparison_data, f, indent=4, default=str)
            
            logger.info(f"Comparaison terminée. Résultats sauvegardés dans {results_path}")
            logger.info(f"Rapport de comparaison généré dans {report_path}")
            
            return comparison_data
            
        except Exception as e:
            logger.error(f"Erreur lors de la comparaison: {e}", exc_info=True)
            raise BacktestingError(f"Erreur lors de la comparaison: {e}")
    
    def optimize_strategy(self, strategy_class, param_grid: Dict[str, List[Any]],
                        symbols: List[str], start_date: str, end_date: str,
                        initial_balance: Dict[str, float], timeframe: str = "1m",
                        data_source: str = "binance", optimization_method: str = "grid",
                        maximize_metric: str = "total_return", n_iter: int = 100) -> Dict[str, Any]:
        """
        Optimise les paramètres d'une stratégie.
        
        Args:
            strategy_class: Classe de la stratégie à optimiser
            param_grid: Grille de paramètres à explorer
            symbols: Liste des symboles à trader
            start_date: Date de début du backtest
            end_date: Date de fin du backtest
            initial_balance: Solde initial pour chaque actif
            timeframe: Intervalle de temps pour les données
            data_source: Source des données historiques
            optimization_method: Méthode d'optimisation ("grid", "random", "bayesian", "genetic")
            maximize_metric: Métrique à maximiser
            n_iter: Nombre d'itérations pour les méthodes aléatoires
            
        Returns:
            Résultats de l'optimisation
        """
        try:
            # Générer un ID unique pour cette optimisation
            optimization_id = f"optimization_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            optimization_dir = os.path.join(self.results_dir, optimization_id)
            os.makedirs(optimization_dir, exist_ok=True)
            
            logger.info(f"Démarrage de l'optimisation {optimization_id}")
            logger.info(f"Stratégie: {strategy_class.__name__}, Méthode: {optimization_method}, Métrique: {maximize_metric}")
            
            # Fonction objectif pour l'optimisation
            def objective_function(params):
                try:
                    # Exécuter un backtest avec les paramètres donnés
                    backtest_result = self.run_backtest(
                        strategy_class=strategy_class,
                        strategy_params=params,
                        symbols=symbols,
                        start_date=start_date,
                        end_date=end_date,
                        initial_balance=initial_balance,
                        timeframe=timeframe,
                        data_source=data_source
                    )
                    
                    # Extraire la métrique à maximiser
                    if maximize_metric in backtest_result["performance_metrics"]:
                        return backtest_result["performance_metrics"][maximize_metric]
                    else:
                        logger.warning(f"Métrique {maximize_metric} non trouvée, utilisation du rendement total")
                        return backtest_result["performance_metrics"]["total_return"]
                except Exception as e:
                    logger.error(f"Erreur lors de l'évaluation des paramètres: {e}")
                    return float("-inf")  # Valeur très basse en cas d'erreur
            
            # Exécuter l'optimisation selon la méthode choisie
            if optimization_method == "grid":
                best_params, best_value = self.parameter_optimizer.optimize_grid_search(
                    param_grid=param_grid,
                    objective_function=objective_function,
                    maximize=True
                )
            elif optimization_method == "random":
                best_params, best_value = self.parameter_optimizer.optimize_random_search(
                    param_distributions=param_grid,
                    objective_function=objective_function,
                    n_iter=n_iter,
                    maximize=True
                )
            elif optimization_method == "genetic":
                # Convertir la grille de paramètres en bornes pour l'algorithme génétique
                param_bounds = {}
                for param_name, param_values in param_grid.items():
                    if isinstance(param_values, list):
                        if all(isinstance(v, (int, float)) for v in param_values):
                            param_bounds[param_name] = (min(param_values), max(param_values))
                        else:
                            logger.warning(f"Paramètre {param_name} non numérique, utilisation de la première et dernière valeur")
                            param_bounds[param_name] = (param_values[0], param_values[-1])
                    elif isinstance(param_values, tuple) and len(param_values) == 2:
                        param_bounds[param_name] = param_values
                
                best_params, best_value = self.parameter_optimizer.optimize_genetic_algorithm(
                    param_bounds=param_bounds,
                    objective_function=objective_function,
                    population_size=min(50, n_iter // 2),
                    n_generations=min(20, n_iter // 5),
                    maximize=True
                )
            else:
                logger.warning(f"Méthode d'optimisation {optimization_method} non supportée, utilisation de la recherche par grille")
                best_params, best_value = self.parameter_optimizer.optimize_grid_search(
                    param_grid=param_grid,
                    objective_function=objective_function,
                    maximize=True
                )
            
            # Exécuter un backtest final avec les meilleurs paramètres
            final_backtest = self.run_backtest(
                strategy_class=strategy_class,
                strategy_params=best_params,
                symbols=symbols,
                start_date=start_date,
                end_date=end_date,
                initial_balance=initial_balance,
                timeframe=timeframe,
                data_source=data_source
            )
            
            # Sauvegarder les résultats de l'optimisation
            optimization_results = {
                "optimization_id": optimization_id,
                "strategy": strategy_class.__name__,
                "param_grid": param_grid,
                "optimization_method": optimization_method,
                "maximize_metric": maximize_metric,
                "n_iter": n_iter,
                "best_params": best_params,
                "best_value": best_value,
                "final_backtest_id": final_backtest["backtest_id"],
                "symbols": symbols,
                "start_date": start_date,
                "end_date": end_date,
                "timeframe": timeframe,
                "initial_balance": initial_balance
            }
            
            results_path = os.path.join(optimization_dir, "optimization_results.json")
            with open(results_path, "w") as f:
                json.dump(optimization_results, f, indent=4, default=str)
            
            logger.info(f"Optimisation terminée. Résultats sauvegardés dans {results_path}")
            logger.info(f"Meilleurs paramètres: {best_params}, Valeur: {best_value}")
            
            return optimization_results
            
        except Exception as e:
            logger.error(f"Erreur lors de l'optimisation: {e}", exc_info=True)
            raise BacktestingError(f"Erreur lors de l'optimisation: {e}")
    
    def _compare_results(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Compare les résultats de plusieurs backtests.
        
        Args:
            results: Liste des résultats de backtest
            
        Returns:
            Résultats de la comparaison
        """
        comparison = {}
        
        # Extraire les noms des stratégies
        strategy_names = [r["strategy"] for r in results]
        
        # Comparer les métriques de performance
        for metric in ["total_return", "sharpe_ratio", "sortino_ratio", "max_drawdown", "win_rate"]:
            comparison[metric] = {}
            for i, result in enumerate(results):
                if metric in result["performance_metrics"]:
                    comparison[metric][strategy_names[i]] = result["performance_metrics"][metric]
        
        # Déterminer la meilleure stratégie pour chaque métrique
        best_strategies = {}
        for metric in comparison:
            if metric in ["max_drawdown"]:  # Métriques à minimiser
                best_strategy = min(comparison[metric].items(), key=lambda x: x[1])
            else:  # Métriques à maximiser
                best_strategy = max(comparison[metric].items(), key=lambda x: x[1])
            best_strategies[metric] = best_strategy[0]
        
        comparison["best_strategies"] = best_strategies
        
        return comparison
    
    def _generate_comparison_report(self, results: List[Dict[str, Any]], report_path: str):
        """
        Génère un rapport de comparaison des stratégies.
        
        Args:
            results: Liste des résultats de backtest
            report_path: Chemin du rapport à générer
        """
        try:
            # Extraire les noms des stratégies
            strategy_names = [r["strategy"] for r in results]
            
            # Créer un DataFrame pour les métriques de performance
            metrics = ["total_return", "sharpe_ratio", "sortino_ratio", "max_drawdown", "win_rate", "profit_factor"]
            performance_data = []
            
            for i, result in enumerate(results):
                row = {"Strategy": strategy_names[i]}
                for metric in metrics:
                    if metric in result["performance_metrics"]:
                        row[metric] = result["performance_metrics"][metric]
                performance_data.append(row)
            
            performance_df = pd.DataFrame(performance_data)
            
            # Créer un DataFrame pour les courbes d'équité
            equity_curves = []
            for result in results:
                if isinstance(result["equity_curve"], dict):
                    equity_df = pd.DataFrame.from_dict(result["equity_curve"], orient="index")
                    equity_df.index = pd.to_datetime(equity_df.index)
                    equity_df.sort_index(inplace=True)
                    equity_curves.append(equity_df)
                else:
                    equity_curves.append(result["equity_curve"])
            
            # Générer le rapport HTML
            with open(report_path, "w") as f:
                f.write("<html>\n")
                f.write("<head>\n")
                f.write("<title>Comparison Report</title>\n")
                f.write("<style>\n")
                f.write("body { font-family: Arial, sans-serif; margin: 20px; }\n")
                f.write("table { border-collapse: collapse; width: 100%; }\n")
                f.write("th, td { border: 1px solid #ddd; padding: 8px; text-align: right; }\n")
                f.write("th { background-color: #f2f2f2; }\n")
                f.write("tr:nth-child(even) { background-color: #f9f9f9; }\n")
                f.write("</style>\n")
                f.write("</head>\n")
                f.write("<body>\n")
                
                f.write("<h1>Strategy Comparison Report</h1>\n")
                
                # Tableau des métriques de performance
                f.write("<h2>Performance Metrics</h2>\n")
                f.write(performance_df.to_html(index=False))
                
                # Graphique des courbes d'équité
                f.write("<h2>Equity Curves</h2>\n")
                
                # Sauvegarder le graphique des courbes d'équité
                plt.figure(figsize=(12, 6))
                for i, equity_curve in enumerate(equity_curves):
                    plt.plot(equity_curve.index, equity_curve["equity"], label=strategy_names[i])
                plt.title("Equity Curves Comparison")
                plt.xlabel("Date")
                plt.ylabel("Equity")
                plt.legend()
                plt.grid(True)
                
                # Créer le répertoire pour les images si nécessaire
                img_dir = os.path.join(os.path.dirname(report_path), "images")
                os.makedirs(img_dir, exist_ok=True)
                
                img_path = os.path.join(img_dir, "equity_curves.png")
                plt.savefig(img_path)
                
                # Ajouter l'image au rapport
                f.write(f'<img src="images/equity_curves.png" alt="Equity Curves" width="800">\n')
                
                f.write("</body>\n")
                f.write("</html>\n")
            
            logger.info(f"Rapport de comparaison généré dans {report_path}")
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération du rapport de comparaison: {e}", exc_info=True)
            raise BacktestingError(f"Erreur lors de la génération du rapport de comparaison: {e}")
    
    def load_backtest_results(self, backtest_id: str) -> Dict[str, Any]:
        """
        Charge les résultats d'un backtest précédent.
        
        Args:
            backtest_id: ID du backtest à charger
            
        Returns:
            Résultats du backtest
        """
        try:
            results_path = os.path.join(self.results_dir, backtest_id, "results.json")
            
            if not os.path.exists(results_path):
                raise BacktestingError(f"Résultats du backtest {backtest_id} non trouvés")
            
            with open(results_path, "r") as f:
                results = json.load(f)
            
            logger.info(f"Résultats du backtest {backtest_id} chargés depuis {results_path}")
            
            return results
            
        except Exception as e:
            logger.error(f"Erreur lors du chargement des résultats: {e}", exc_info=True)
            raise BacktestingError(f"Erreur lors du chargement des résultats: {e}")
    
    def list_backtests(self) -> List[str]:
        """
        Liste tous les backtests disponibles.
        
        Returns:
            Liste des IDs de backtest
        """
        try:
            # Lister tous les sous-répertoires du répertoire de résultats
            backtest_ids = []
            for item in os.listdir(self.results_dir):
                if os.path.isdir(os.path.join(self.results_dir, item)) and item.startswith("backtest_"):
                    backtest_ids.append(item)
            
            return sorted(backtest_ids)
            
        except Exception as e:
            logger.error(f"Erreur lors de la liste des backtests: {e}", exc_info=True)
            raise BacktestingError(f"Erreur lors de la liste des backtests: {e}")
    
    def delete_backtest(self, backtest_id: str) -> bool:
        """
        Supprime un backtest.
        
        Args:
            backtest_id: ID du backtest à supprimer
            
        Returns:
            True si la suppression a réussi, False sinon
        """
        try:
            backtest_dir = os.path.join(self.results_dir, backtest_id)
            
            if not os.path.exists(backtest_dir):
                logger.warning(f"Backtest {backtest_id} non trouvé")
                return False
            
            # Supprimer le répertoire et son contenu
            import shutil
            shutil.rmtree(backtest_dir)
            
            logger.info(f"Backtest {backtest_id} supprimé")
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la suppression du backtest: {e}", exc_info=True)
            raise BacktestingError(f"Erreur lors de la suppression du backtest: {e}") 