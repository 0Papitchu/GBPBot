#!/usr/bin/env python3
"""
Module d'optimisation des paramètres pour le backtesting de GBPBot.

Ce module fournit des fonctionnalités pour optimiser les paramètres des stratégies
de trading en utilisant diverses techniques d'optimisation, comme la recherche par grille,
l'optimisation bayésienne et les algorithmes génétiques.
"""

import os
import json
import time
import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple, Union, Callable
from datetime import datetime, timedelta
import itertools
from concurrent.futures import ProcessPoolExecutor, as_completed

# Essayer d'importer les bibliothèques d'optimisation
try:
    from skopt import gp_minimize, forest_minimize, gbrt_minimize
    from skopt.space import Real, Integer, Categorical
    SKOPT_AVAILABLE = True
except ImportError:
    SKOPT_AVAILABLE = False
    logging.warning("scikit-optimize non disponible. Installez-le avec 'pip install scikit-optimize'")

try:
    import optuna
    OPTUNA_AVAILABLE = True
except ImportError:
    OPTUNA_AVAILABLE = False
    logging.warning("optuna non disponible. Installez-le avec 'pip install optuna'")

# Configuration du logger
logger = logging.getLogger(__name__)

class ParameterOptimizer:
    """
    Classe pour optimiser les paramètres des stratégies de trading.
    
    Cette classe fournit des méthodes pour optimiser les paramètres des stratégies
    en utilisant diverses techniques d'optimisation.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialise l'optimiseur de paramètres.
        
        Args:
            config: Configuration pour l'optimiseur de paramètres
        """
        self.config = config
        
        # Paramètres d'optimisation
        self.optimization_method = config.get("OPTIMIZATION_METHOD", "grid")
        self.n_jobs = int(config.get("N_JOBS", -1))  # -1 pour utiliser tous les cœurs disponibles
        self.random_state = int(config.get("RANDOM_STATE", 42))
        self.n_calls = int(config.get("N_CALLS", 100))  # Nombre d'appels pour l'optimisation bayésienne
        self.n_initial_points = int(config.get("N_INITIAL_POINTS", 10))
        self.results_dir = config.get("RESULTS_DIR", "optimization_results")
        
        # Créer le répertoire de résultats s'il n'existe pas
        os.makedirs(self.results_dir, exist_ok=True)
        
        logger.info("Optimiseur de paramètres initialisé")
    
    def optimize_grid_search(self, param_grid: Dict[str, List[Any]], 
                           objective_function: Callable[[Dict[str, Any]], float],
                           maximize: bool = True) -> Tuple[Dict[str, Any], float]:
        """
        Optimise les paramètres en utilisant la recherche par grille.
        
        Args:
            param_grid: Grille de paramètres à explorer
            objective_function: Fonction objectif à optimiser
            maximize: True pour maximiser, False pour minimiser
            
        Returns:
            Tuple (meilleurs paramètres, meilleure valeur)
        """
        # Générer toutes les combinaisons de paramètres
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        param_combinations = list(itertools.product(*param_values))
        
        logger.info(f"Recherche par grille: {len(param_combinations)} combinaisons à évaluer")
        
        # Initialiser les meilleurs paramètres
        best_params = None
        best_value = float('-inf') if maximize else float('inf')
        
        # Fonction pour évaluer une combinaison de paramètres
        def evaluate_params(params_tuple):
            params = dict(zip(param_names, params_tuple))
            value = objective_function(params)
            return params, value
        
        # Évaluer les combinaisons de paramètres en parallèle
        with ProcessPoolExecutor(max_workers=self.n_jobs if self.n_jobs > 0 else None) as executor:
            futures = [executor.submit(evaluate_params, params_tuple) for params_tuple in param_combinations]
            
            # Collecter les résultats
            results = []
            for future in as_completed(futures):
                try:
                    params, value = future.result()
                    results.append((params, value))
                    
                    # Mettre à jour les meilleurs paramètres
                    if maximize and value > best_value:
                        best_params = params
                        best_value = value
                    elif not maximize and value < best_value:
                        best_params = params
                        best_value = value
                        
                    logger.debug(f"Évaluation: {params}, valeur: {value}")
                except Exception as e:
                    logger.error(f"Erreur lors de l'évaluation des paramètres: {e}")
        
        # Trier les résultats
        results.sort(key=lambda x: x[1], reverse=maximize)
        
        # Sauvegarder les résultats
        self._save_results(results, "grid_search")
        
        logger.info(f"Recherche par grille terminée. Meilleurs paramètres: {best_params}, valeur: {best_value}")
        
        return best_params, best_value
    
    def optimize_random_search(self, param_distributions: Dict[str, Any], 
                             objective_function: Callable[[Dict[str, Any]], float],
                             n_iter: int = 100, maximize: bool = True) -> Tuple[Dict[str, Any], float]:
        """
        Optimise les paramètres en utilisant la recherche aléatoire.
        
        Args:
            param_distributions: Distributions des paramètres
            objective_function: Fonction objectif à optimiser
            n_iter: Nombre d'itérations
            maximize: True pour maximiser, False pour minimiser
            
        Returns:
            Tuple (meilleurs paramètres, meilleure valeur)
        """
        logger.info(f"Recherche aléatoire: {n_iter} itérations")
        
        # Initialiser les meilleurs paramètres
        best_params = None
        best_value = float('-inf') if maximize else float('inf')
        
        # Fonction pour générer des paramètres aléatoires
        def generate_random_params():
            params = {}
            for param_name, param_dist in param_distributions.items():
                if isinstance(param_dist, list):
                    # Choix aléatoire dans une liste
                    params[param_name] = np.random.choice(param_dist)
                elif isinstance(param_dist, tuple) and len(param_dist) == 2:
                    # Intervalle continu
                    low, high = param_dist
                    if isinstance(low, int) and isinstance(high, int):
                        params[param_name] = np.random.randint(low, high + 1)
                    else:
                        params[param_name] = np.random.uniform(low, high)
                else:
                    raise ValueError(f"Distribution non supportée pour {param_name}: {param_dist}")
            return params
        
        # Fonction pour évaluer des paramètres
        def evaluate_params():
            params = generate_random_params()
            value = objective_function(params)
            return params, value
        
        # Évaluer les paramètres en parallèle
        with ProcessPoolExecutor(max_workers=self.n_jobs if self.n_jobs > 0 else None) as executor:
            futures = [executor.submit(evaluate_params) for _ in range(n_iter)]
            
            # Collecter les résultats
            results = []
            for future in as_completed(futures):
                try:
                    params, value = future.result()
                    results.append((params, value))
                    
                    # Mettre à jour les meilleurs paramètres
                    if maximize and value > best_value:
                        best_params = params
                        best_value = value
                    elif not maximize and value < best_value:
                        best_params = params
                        best_value = value
                        
                    logger.debug(f"Évaluation: {params}, valeur: {value}")
                except Exception as e:
                    logger.error(f"Erreur lors de l'évaluation des paramètres: {e}")
        
        # Trier les résultats
        results.sort(key=lambda x: x[1], reverse=maximize)
        
        # Sauvegarder les résultats
        self._save_results(results, "random_search")
        
        logger.info(f"Recherche aléatoire terminée. Meilleurs paramètres: {best_params}, valeur: {best_value}")
        
        return best_params, best_value
    
    def optimize_bayesian(self, param_space: List[Any], 
                        objective_function: Callable[[List[Any]], float],
                        maximize: bool = True) -> Tuple[Dict[str, Any], float]:
        """
        Optimise les paramètres en utilisant l'optimisation bayésienne.
        
        Args:
            param_space: Espace des paramètres (liste d'objets skopt.space)
            objective_function: Fonction objectif à optimiser
            maximize: True pour maximiser, False pour minimiser
            
        Returns:
            Tuple (meilleurs paramètres, meilleure valeur)
        """
        if not SKOPT_AVAILABLE:
            raise ImportError("scikit-optimize est requis pour l'optimisation bayésienne")
        
        logger.info(f"Optimisation bayésienne: {self.n_calls} appels")
        
        # Adapter la fonction objectif pour minimiser
        def objective_wrapper(params):
            value = objective_function(params)
            return -value if maximize else value
        
        # Effectuer l'optimisation bayésienne
        result = gp_minimize(
            objective_wrapper,
            param_space,
            n_calls=self.n_calls,
            n_initial_points=self.n_initial_points,
            random_state=self.random_state,
            n_jobs=self.n_jobs
        )
        
        # Extraire les meilleurs paramètres
        best_params_list = result.x
        best_value = -result.fun if maximize else result.fun
        
        # Convertir la liste de paramètres en dictionnaire
        param_names = [param.name for param in param_space]
        best_params = dict(zip(param_names, best_params_list))
        
        # Sauvegarder les résultats
        results = [(dict(zip(param_names, x)), -y if maximize else y) for x, y in zip(result.x_iters, result.func_vals)]
        results.sort(key=lambda x: x[1], reverse=maximize)
        self._save_results(results, "bayesian_optimization")
        
        logger.info(f"Optimisation bayésienne terminée. Meilleurs paramètres: {best_params}, valeur: {best_value}")
        
        return best_params, best_value
    
    def optimize_optuna(self, create_study_params: Dict[str, Any], 
                       objective_function: Callable[[Any], float],
                       n_trials: int = 100, maximize: bool = True) -> Tuple[Dict[str, Any], float]:
        """
        Optimise les paramètres en utilisant Optuna.
        
        Args:
            create_study_params: Paramètres pour créer l'étude Optuna
            objective_function: Fonction objectif à optimiser
            n_trials: Nombre d'essais
            maximize: True pour maximiser, False pour minimiser
            
        Returns:
            Tuple (meilleurs paramètres, meilleure valeur)
        """
        if not OPTUNA_AVAILABLE:
            raise ImportError("optuna est requis pour l'optimisation avec Optuna")
        
        logger.info(f"Optimisation Optuna: {n_trials} essais")
        
        # Créer l'étude
        direction = "maximize" if maximize else "minimize"
        study = optuna.create_study(direction=direction, **create_study_params)
        
        # Optimiser
        study.optimize(objective_function, n_trials=n_trials, n_jobs=self.n_jobs)
        
        # Extraire les meilleurs paramètres
        best_params = study.best_params
        best_value = study.best_value
        
        # Sauvegarder les résultats
        results = [(trial.params, trial.value) for trial in study.trials]
        results.sort(key=lambda x: x[1], reverse=maximize)
        self._save_results(results, "optuna_optimization")
        
        logger.info(f"Optimisation Optuna terminée. Meilleurs paramètres: {best_params}, valeur: {best_value}")
        
        return best_params, best_value
    
    def optimize_genetic_algorithm(self, param_bounds: Dict[str, Tuple[Any, Any]],
                                 objective_function: Callable[[Dict[str, Any]], float],
                                 population_size: int = 50, n_generations: int = 20,
                                 maximize: bool = True) -> Tuple[Dict[str, Any], float]:
        """
        Optimise les paramètres en utilisant un algorithme génétique.
        
        Args:
            param_bounds: Bornes des paramètres
            objective_function: Fonction objectif à optimiser
            population_size: Taille de la population
            n_generations: Nombre de générations
            maximize: True pour maximiser, False pour minimiser
            
        Returns:
            Tuple (meilleurs paramètres, meilleure valeur)
        """
        logger.info(f"Algorithme génétique: {population_size} individus, {n_generations} générations")
        
        # Initialiser les meilleurs paramètres
        best_params = None
        best_value = float('-inf') if maximize else float('inf')
        
        # Fonction pour générer un individu aléatoire
        def generate_individual():
            params = {}
            for param_name, (low, high) in param_bounds.items():
                if isinstance(low, int) and isinstance(high, int):
                    params[param_name] = np.random.randint(low, high + 1)
                else:
                    params[param_name] = np.random.uniform(low, high)
            return params
        
        # Générer la population initiale
        population = [generate_individual() for _ in range(population_size)]
        
        # Évaluer la population initiale
        fitness_values = []
        for individual in population:
            fitness = objective_function(individual)
            fitness_values.append(fitness)
            
            # Mettre à jour les meilleurs paramètres
            if maximize and fitness > best_value:
                best_params = individual
                best_value = fitness
            elif not maximize and fitness < best_value:
                best_params = individual
                best_value = fitness
        
        # Boucle principale de l'algorithme génétique
        for generation in range(n_generations):
            logger.info(f"Génération {generation + 1}/{n_generations}")
            
            # Sélection des parents
            parents_indices = self._selection(fitness_values, population_size // 2, maximize)
            parents = [population[i] for i in parents_indices]
            
            # Croisement et mutation
            offspring = []
            for i in range(0, len(parents), 2):
                if i + 1 < len(parents):
                    child1, child2 = self._crossover(parents[i], parents[i + 1])
                    child1 = self._mutation(child1, param_bounds)
                    child2 = self._mutation(child2, param_bounds)
                    offspring.extend([child1, child2])
            
            # Compléter la population avec de nouveaux individus aléatoires
            while len(offspring) < population_size:
                offspring.append(generate_individual())
            
            # Évaluer la nouvelle population
            population = offspring
            fitness_values = []
            for individual in population:
                fitness = objective_function(individual)
                fitness_values.append(fitness)
                
                # Mettre à jour les meilleurs paramètres
                if maximize and fitness > best_value:
                    best_params = individual
                    best_value = fitness
                elif not maximize and fitness < best_value:
                    best_params = individual
                    best_value = fitness
        
        # Sauvegarder les résultats
        results = [(individual, fitness) for individual, fitness in zip(population, fitness_values)]
        results.sort(key=lambda x: x[1], reverse=maximize)
        self._save_results(results, "genetic_algorithm")
        
        logger.info(f"Algorithme génétique terminé. Meilleurs paramètres: {best_params}, valeur: {best_value}")
        
        return best_params, best_value
    
    def _selection(self, fitness_values: List[float], n_parents: int, maximize: bool) -> List[int]:
        """
        Sélectionne les parents pour la reproduction.
        
        Args:
            fitness_values: Valeurs de fitness
            n_parents: Nombre de parents à sélectionner
            maximize: True pour maximiser, False pour minimiser
            
        Returns:
            Indices des parents sélectionnés
        """
        # Sélection par tournoi
        selected_indices = []
        
        for _ in range(n_parents):
            # Sélectionner deux individus aléatoires
            idx1, idx2 = np.random.choice(len(fitness_values), 2, replace=False)
            
            # Sélectionner le meilleur
            if maximize:
                selected_idx = idx1 if fitness_values[idx1] > fitness_values[idx2] else idx2
            else:
                selected_idx = idx1 if fitness_values[idx1] < fitness_values[idx2] else idx2
            
            selected_indices.append(selected_idx)
        
        return selected_indices
    
    def _crossover(self, parent1: Dict[str, Any], parent2: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Effectue un croisement entre deux parents.
        
        Args:
            parent1: Premier parent
            parent2: Deuxième parent
            
        Returns:
            Deux enfants
        """
        # Croisement uniforme
        child1 = {}
        child2 = {}
        
        for param_name in parent1.keys():
            if np.random.random() < 0.5:
                child1[param_name] = parent1[param_name]
                child2[param_name] = parent2[param_name]
            else:
                child1[param_name] = parent2[param_name]
                child2[param_name] = parent1[param_name]
        
        return child1, child2
    
    def _mutation(self, individual: Dict[str, Any], param_bounds: Dict[str, Tuple[Any, Any]]) -> Dict[str, Any]:
        """
        Effectue une mutation sur un individu.
        
        Args:
            individual: Individu à muter
            param_bounds: Bornes des paramètres
            
        Returns:
            Individu muté
        """
        # Mutation gaussienne
        mutated = individual.copy()
        
        for param_name, value in individual.items():
            # Probabilité de mutation
            if np.random.random() < 0.1:
                low, high = param_bounds[param_name]
                
                if isinstance(low, int) and isinstance(high, int):
                    # Paramètre entier
                    mutated[param_name] = np.random.randint(low, high + 1)
                else:
                    # Paramètre continu
                    # Mutation gaussienne avec écart-type proportionnel à la plage
                    std = (high - low) * 0.1
                    new_value = value + np.random.normal(0, std)
                    # Limiter à l'intervalle
                    new_value = max(low, min(high, new_value))
                    mutated[param_name] = new_value
        
        return mutated
    
    def _save_results(self, results: List[Tuple[Dict[str, Any], float]], method: str):
        """
        Sauvegarde les résultats de l'optimisation.
        
        Args:
            results: Résultats de l'optimisation
            method: Méthode d'optimisation
        """
        # Créer un nom de fichier unique
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{method}_{timestamp}.json"
        filepath = os.path.join(self.results_dir, filename)
        
        # Convertir les résultats en format JSON
        json_results = []
        for params, value in results:
            json_results.append({
                "params": params,
                "value": value
            })
        
        # Sauvegarder les résultats
        with open(filepath, "w") as f:
            json.dump(json_results, f, indent=4)
        
        logger.info(f"Résultats sauvegardés dans {filepath}")
    
    def load_results(self, filepath: str) -> List[Tuple[Dict[str, Any], float]]:
        """
        Charge les résultats d'une optimisation précédente.
        
        Args:
            filepath: Chemin du fichier de résultats
            
        Returns:
            Résultats de l'optimisation
        """
        with open(filepath, "r") as f:
            json_results = json.load(f)
        
        results = [(item["params"], item["value"]) for item in json_results]
        
        logger.info(f"Résultats chargés depuis {filepath}")
        
        return results
    
    def get_best_params(self, results: List[Tuple[Dict[str, Any], float]], maximize: bool = True) -> Tuple[Dict[str, Any], float]:
        """
        Récupère les meilleurs paramètres à partir des résultats.
        
        Args:
            results: Résultats de l'optimisation
            maximize: True pour maximiser, False pour minimiser
            
        Returns:
            Tuple (meilleurs paramètres, meilleure valeur)
        """
        if not results:
            logger.warning("Aucun résultat à analyser")
            return {}, 0.0
        
        # Trier les résultats
        sorted_results = sorted(results, key=lambda x: x[1], reverse=maximize)
        
        # Récupérer les meilleurs paramètres
        best_params, best_value = sorted_results[0]
        
        return best_params, best_value 