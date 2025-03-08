"""
Module de base pour le système d'optimisation unifié de GBPBot
============================================================

Ce module définit l'interface commune pour tous les optimiseurs dans GBPBot.
Il établit le contrat que tous les optimiseurs spécifiques doivent respecter.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, List, Optional, Union, Tuple, Set

# Configuration du logging
logger = logging.getLogger("gbpbot.optimization")

# Types pour les optimisations
OptimizationResult = Dict[str, Any]
OptimizationConfig = Dict[str, Any]

class OptimizationException(Exception):
    """Exception personnalisée pour les erreurs d'optimisation"""
    pass

class BaseOptimizer(ABC):
    """
    Classe abstraite définissant l'interface commune pour tous les optimiseurs.
    
    Tous les optimiseurs spécifiques doivent hériter de cette classe et implémenter
    ses méthodes abstraites. Cela assure une interface cohérente pour tous les
    systèmes d'optimisation dans GBPBot.
    """
    
    def __init__(self, name: str, config: OptimizationConfig = None):
        """
        Initialise un optimiseur de base.
        
        Args:
            name: Nom unique de l'optimiseur
            config: Configuration initiale de l'optimiseur
        """
        self.name = name
        self.config = config or {}
        self.last_run = None
        self.enabled = True
        self.results_history = []
        self.optimizations_applied = set()
        self.priority = 50  # Priorité par défaut (1-100, où 100 est la plus élevée)
        self.dependencies = set()  # Autres optimiseurs dont celui-ci dépend
        
    def can_optimize(self) -> bool:
        """
        Vérifie si l'optimiseur peut être exécuté dans l'état actuel.
        
        Returns:
            bool: True si l'optimiseur peut être exécuté, False sinon
        """
        return self.enabled
    
    @abstractmethod
    def optimize(self) -> OptimizationResult:
        """
        Applique les optimisations.
        
        Cette méthode doit être implémentée par les classes dérivées pour appliquer
        les optimisations spécifiques.
        
        Returns:
            OptimizationResult: Résultats de l'optimisation
        """
        pass
    
    @abstractmethod
    def validate(self) -> bool:
        """
        Valide que les optimisations sont correctement appliquées.
        
        Cette méthode doit être implémentée par les classes dérivées pour vérifier
        que les optimisations ont été correctement appliquées.
        
        Returns:
            bool: True si les optimisations sont valides, False sinon
        """
        pass
    
    def run(self, force: bool = False) -> OptimizationResult:
        """
        Exécute l'optimiseur si possible.
        
        Args:
            force: Forcer l'exécution même si les conditions ne sont pas remplies
            
        Returns:
            OptimizationResult: Résultats de l'optimisation ou erreur
        """
        if not self.enabled and not force:
            return {"status": "skipped", "reason": "optimizer_disabled"}
        
        if not self.can_optimize() and not force:
            return {"status": "skipped", "reason": "cannot_optimize"}
        
        try:
            start_time = datetime.now()
            results = self.optimize()
            end_time = datetime.now()
            
            # Ajouter les méta-informations
            results["optimizer"] = self.name
            results["start_time"] = start_time.isoformat()
            results["end_time"] = end_time.isoformat()
            results["duration"] = (end_time - start_time).total_seconds()
            results["status"] = results.get("status", "success")
            
            # Valider les optimisations
            results["validated"] = self.validate()
            
            # Mettre à jour l'historique
            self.last_run = start_time
            self.results_history.append(results)
            if len(self.results_history) > 10:  # Garder seulement les 10 dernières exécutions
                self.results_history = self.results_history[-10:]
                
            # Mettre à jour les optimisations appliquées
            if "optimizations_applied" in results and isinstance(results["optimizations_applied"], list):
                self.optimizations_applied.update(results["optimizations_applied"])
                
            return results
            
        except Exception as e:
            logger.error(f"Erreur lors de l'optimisation {self.name}: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "optimizer": self.name,
                "timestamp": datetime.now().isoformat()
            }
    
    def set_config(self, config: OptimizationConfig) -> None:
        """
        Met à jour la configuration de l'optimiseur.
        
        Args:
            config: Nouvelle configuration
        """
        self.config.update(config)
    
    def add_dependency(self, optimizer_name: str) -> None:
        """
        Ajoute une dépendance à un autre optimiseur.
        
        Args:
            optimizer_name: Nom de l'optimiseur dont dépend celui-ci
        """
        self.dependencies.add(optimizer_name)
    
    def get_dependencies(self) -> Set[str]:
        """
        Récupère les dépendances de cet optimiseur.
        
        Returns:
            Set[str]: Ensemble des noms des optimiseurs dont dépend celui-ci
        """
        return self.dependencies.copy()
    
    def enable(self) -> None:
        """Active l'optimiseur."""
        self.enabled = True
    
    def disable(self) -> None:
        """Désactive l'optimiseur."""
        self.enabled = False
    
    def set_priority(self, priority: int) -> None:
        """
        Définit la priorité de l'optimiseur.
        
        Args:
            priority: Priorité (1-100, où 100 est la plus élevée)
        """
        if not 1 <= priority <= 100:
            raise ValueError("La priorité doit être comprise entre 1 et 100")
        self.priority = priority
    
    def get_status(self) -> Dict[str, Any]:
        """
        Récupère l'état actuel de l'optimiseur.
        
        Returns:
            Dict[str, Any]: État actuel de l'optimiseur
        """
        last_result = self.results_history[-1] if self.results_history else None
        return {
            "name": self.name,
            "enabled": self.enabled,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "priority": self.priority,
            "dependencies": list(self.dependencies),
            "optimizations_applied": list(self.optimizations_applied),
            "last_result": last_result
        }
    
    def reset(self) -> None:
        """Réinitialise l'état de l'optimiseur."""
        self.last_run = None
        self.results_history = []
        self.optimizations_applied = set()


class OptimizationManager:
    """
    Gestionnaire pour tous les optimiseurs dans le système.
    
    Cette classe gère l'enregistrement, l'exécution et la coordination
    des différents optimiseurs.
    """
    
    def __init__(self):
        """Initialise le gestionnaire d'optimisation."""
        self.optimizers = {}  # Dictionnaire des optimiseurs par nom
        self.global_config = {}  # Configuration globale partagée entre optimiseurs
    
    def register_optimizer(self, optimizer: BaseOptimizer) -> bool:
        """
        Enregistre un nouvel optimiseur.
        
        Args:
            optimizer: Instance d'optimiseur à enregistrer
            
        Returns:
            bool: True si l'enregistrement a réussi, False sinon
        """
        if optimizer.name in self.optimizers:
            logger.warning(f"Un optimiseur du nom '{optimizer.name}' est déjà enregistré")
            return False
        
        self.optimizers[optimizer.name] = optimizer
        return True
    
    def get_optimizer(self, name: str) -> Optional[BaseOptimizer]:
        """
        Récupère un optimiseur par son nom.
        
        Args:
            name: Nom de l'optimiseur
            
        Returns:
            Optional[BaseOptimizer]: L'optimiseur ou None s'il n'existe pas
        """
        return self.optimizers.get(name)
    
    def run_optimizer(self, name: str, force: bool = False) -> OptimizationResult:
        """
        Exécute un optimiseur spécifique.
        
        Args:
            name: Nom de l'optimiseur à exécuter
            force: Forcer l'exécution même si les conditions ne sont pas remplies
            
        Returns:
            OptimizationResult: Résultats de l'optimisation
        """
        optimizer = self.get_optimizer(name)
        if optimizer is None:
            return {"status": "error", "error": f"Optimiseur '{name}' non trouvé"}
        
        return optimizer.run(force=force)
    
    def run_all(self, force: bool = False) -> Dict[str, OptimizationResult]:
        """
        Exécute tous les optimiseurs enregistrés, en respectant les dépendances.
        
        Args:
            force: Forcer l'exécution même si les conditions ne sont pas remplies
            
        Returns:
            Dict[str, OptimizationResult]: Résultats de tous les optimiseurs
        """
        results = {}
        
        # Trier les optimiseurs par priorité et dépendances
        sorted_optimizers = self._sort_optimizers()
        
        # Exécuter les optimiseurs dans l'ordre
        for name in sorted_optimizers:
            optimizer = self.optimizers[name]
            results[name] = optimizer.run(force=force)
        
        return results
    
    def _sort_optimizers(self) -> List[str]:
        """
        Trie les optimiseurs en fonction de leurs dépendances et priorités.
        
        Returns:
            List[str]: Liste des noms d'optimiseurs triés
        """
        # Construire un graphe de dépendances
        graph = {name: optimizer.get_dependencies() for name, optimizer in self.optimizers.items()}
        
        # Vérifier les dépendances circulaires
        visited = set()
        temp_visited = set()
        
        def has_cycle(node):
            if node in temp_visited:
                return True
            if node in visited:
                return False
            
            temp_visited.add(node)
            
            for neighbor in graph.get(node, set()):
                if has_cycle(neighbor):
                    return True
            
            temp_visited.remove(node)
            visited.add(node)
            return False
        
        # Vérifier les cycles pour chaque nœud
        for node in graph:
            if node not in visited:
                if has_cycle(node):
                    raise OptimizationException("Dépendances circulaires détectées dans les optimiseurs")
        
        # Tri topologique
        visited = set()
        result = []
        
        def topo_sort(node):
            if node in visited:
                return
            
            visited.add(node)
            
            for neighbor in graph.get(node, set()):
                if neighbor in self.optimizers:  # Vérifier que la dépendance existe
                    topo_sort(neighbor)
            
            result.append(node)
        
        # Trier tous les optimiseurs
        for node in graph:
            if node not in visited:
                topo_sort(node)
        
        # Inverser le résultat pour avoir l'ordre correct
        result.reverse()
        
        # Tri secondaire par priorité
        # Pour les optimiseurs sans dépendances entre eux, prioriser ceux avec la priorité la plus élevée
        priority_sorted = sorted(
            result,
            key=lambda name: -self.optimizers[name].priority if name in self.optimizers else 0
        )
        
        return priority_sorted
    
    def set_global_config(self, config: Dict[str, Any]) -> None:
        """
        Définit la configuration globale partagée entre tous les optimiseurs.
        
        Args:
            config: Configuration globale
        """
        self.global_config.update(config)
        
        # Propager la configuration aux optimiseurs
        for optimizer in self.optimizers.values():
            optimizer.set_config(self.global_config)
    
    def get_status(self) -> Dict[str, Any]:
        """
        Récupère l'état du gestionnaire d'optimisation.
        
        Returns:
            Dict[str, Any]: État du gestionnaire
        """
        return {
            "optimizers_count": len(self.optimizers),
            "optimizers": {name: optimizer.get_status() for name, optimizer in self.optimizers.items()},
            "global_config": self.global_config
        }
    
    def enable_optimizer(self, name: str) -> bool:
        """
        Active un optimiseur.
        
        Args:
            name: Nom de l'optimiseur
            
        Returns:
            bool: True si l'activation a réussi, False sinon
        """
        optimizer = self.get_optimizer(name)
        if optimizer is None:
            return False
        
        optimizer.enable()
        return True
    
    def disable_optimizer(self, name: str) -> bool:
        """
        Désactive un optimiseur.
        
        Args:
            name: Nom de l'optimiseur
            
        Returns:
            bool: True si la désactivation a réussi, False sinon
        """
        optimizer = self.get_optimizer(name)
        if optimizer is None:
            return False
        
        optimizer.disable()
        return True

# Instance singleton pour un accès facile
_instance = None

def get_optimization_manager() -> OptimizationManager:
    """
    Récupère l'instance singleton du gestionnaire d'optimisation.
    
    Returns:
        OptimizationManager: Instance du gestionnaire d'optimisation
    """
    global _instance
    if _instance is None:
        _instance = OptimizationManager()
    return _instance 