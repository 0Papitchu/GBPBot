#!/usr/bin/env python
"""
Module d'analyse parallèle - GBPBot

Ce module permet d'exécuter des analyses complexes en parallèle pour réduire
le temps de réponse global et améliorer les performances du bot.
"""

import os
import time
import asyncio
import logging
import concurrent.futures
from typing import Dict, List, Any, Optional, Union, Callable, Tuple, TypeVar, Generic
from dataclasses import dataclass, field
from functools import partial
from enum import Enum

from gbpbot.utils.logger import setup_logger

# Configuration du logger
logger = setup_logger("parallel_analyzer", logging.INFO)

# Type générique pour les résultats d'analyse
T = TypeVar('T')

class AnalysisPriority(Enum):
    """Priorité des tâches d'analyse."""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3

@dataclass
class AnalysisTask(Generic[T]):
    """Tâche d'analyse à exécuter en parallèle."""
    name: str
    func: Callable[..., T]
    args: Tuple = field(default_factory=tuple)
    kwargs: Dict[str, Any] = field(default_factory=dict)
    priority: AnalysisPriority = AnalysisPriority.NORMAL
    timeout: Optional[float] = None
    is_async: bool = False
    fallback_value: Optional[T] = None

@dataclass
class AnalysisResult(Generic[T]):
    """Résultat d'une analyse."""
    name: str
    result: Optional[T] = None
    error: Optional[str] = None
    success: bool = True
    execution_time: float = 0.0

class ParallelAnalyzer:
    """
    Analyseur parallèle pour exécuter plusieurs tâches d'analyse simultanément.
    
    Cette classe permet d'exécuter efficacement plusieurs analyses en parallèle
    pour réduire le temps de réponse global tout en gérant les priorités,
    les timeouts et les dépendances entre analyses.
    """
    
    def __init__(
        self, 
        max_workers: Optional[int] = None,
        thread_name_prefix: str = "analyzer",
        use_processes: bool = False
    ):
        """
        Initialise l'analyseur parallèle.
        
        Args:
            max_workers: Nombre maximum de workers (None = noyaux CPU * 5).
            thread_name_prefix: Préfixe pour les noms des threads.
            use_processes: Utiliser des processus au lieu de threads (plus sécurisé mais plus lent).
        """
        self.max_workers = max_workers or (os.cpu_count() or 1) * 5
        self.thread_name_prefix = thread_name_prefix
        self.use_processes = use_processes
        
        # Statistiques
        self.stats = {
            "total_tasks": 0,
            "successful_tasks": 0,
            "failed_tasks": 0,
            "total_execution_time": 0.0,
            "timeouts": 0
        }
        
        # Créer l'executor approprié
        self._executor = None
        
        logger.info(f"Analyseur parallèle initialisé avec {self.max_workers} workers")
    
    def _get_executor(self):
        """Crée et retourne l'executor approprié."""
        if self._executor is None:
            if self.use_processes:
                self._executor = concurrent.futures.ProcessPoolExecutor(
                    max_workers=self.max_workers
                )
            else:
                self._executor = concurrent.futures.ThreadPoolExecutor(
                    max_workers=self.max_workers,
                    thread_name_prefix=self.thread_name_prefix
                )
        return self._executor
    
    def add_task(self, task: AnalysisTask) -> int:
        """
        Ajoute une tâche à la file d'attente pour exécution.
        
        Note: Cette méthode est obsolète et n'est maintenue que pour
        la compatibilité. Utilisez plutôt run_tasks ou run_tasks_async.
        
        Args:
            task: La tâche à exécuter.
            
        Returns:
            Identifiant de la tâche (toujours 0).
        """
        logger.warning("add_task est obsolète. Utilisez run_tasks ou run_tasks_async.")
        return 0
    
    def run_tasks(self, tasks: List[AnalysisTask]) -> Dict[str, AnalysisResult]:
        """
        Exécute plusieurs tâches en parallèle (mode synchrone).
        
        Args:
            tasks: Liste des tâches à exécuter.
            
        Returns:
            Dictionnaire des résultats indexés par nom de tâche.
        """
        # Trier les tâches par priorité (décroissante)
        sorted_tasks = sorted(tasks, key=lambda t: t.priority.value, reverse=True)
        
        # Récupérer l'executor
        executor = self._get_executor()
        
        # Dictionnaire pour stocker les résultats
        results = {}
        futures = {}
        
        # Soumettre les tâches à l'executor
        for task in sorted_tasks:
            logger.debug(f"Soumission de la tâche: {task.name}")
            
            if task.is_async:
                # Pour les fonctions asynchrones, nous devons les exécuter dans une boucle asyncio
                future = executor.submit(
                    self._run_async_task,
                    task.func,
                    *task.args,
                    **task.kwargs
                )
            else:
                # Pour les fonctions synchrones, exécution directe
                future = executor.submit(
                    self._run_sync_task,
                    task.func,
                    task.name,
                    task.timeout,
                    task.fallback_value,
                    *task.args,
                    **task.kwargs
                )
            
            futures[future] = task
            self.stats["total_tasks"] += 1
        
        # Attendre la fin de toutes les tâches
        for future in concurrent.futures.as_completed(futures):
            task = futures[future]
            try:
                start_time = time.time()
                if task.timeout:
                    result = future.result(timeout=task.timeout)
                else:
                    result = future.result()
                execution_time = time.time() - start_time
                
                # Créer et stocker le résultat
                analysis_result = AnalysisResult(
                    name=task.name,
                    result=result,
                    success=True,
                    execution_time=execution_time
                )
                results[task.name] = analysis_result
                
                self.stats["successful_tasks"] += 1
                self.stats["total_execution_time"] += execution_time
                
                logger.debug(f"Tâche terminée: {task.name} ({execution_time:.2f}s)")
            except concurrent.futures.TimeoutError:
                logger.warning(f"Timeout pour la tâche: {task.name}")
                
                # Créer un résultat avec le fallback
                results[task.name] = AnalysisResult(
                    name=task.name,
                    result=task.fallback_value,
                    error="Timeout",
                    success=False,
                    execution_time=task.timeout or 0.0
                )
                
                self.stats["failed_tasks"] += 1
                self.stats["timeouts"] += 1
            except Exception as e:
                logger.error(f"Erreur lors de l'exécution de la tâche {task.name}: {str(e)}")
                
                # Créer un résultat avec le fallback
                results[task.name] = AnalysisResult(
                    name=task.name,
                    result=task.fallback_value,
                    error=str(e),
                    success=False,
                    execution_time=0.0
                )
                
                self.stats["failed_tasks"] += 1
        
        return results
    
    async def run_tasks_async(self, tasks: List[AnalysisTask]) -> Dict[str, AnalysisResult]:
        """
        Exécute plusieurs tâches en parallèle (mode asynchrone).
        
        Args:
            tasks: Liste des tâches à exécuter.
            
        Returns:
            Dictionnaire des résultats indexés par nom de tâche.
        """
        # Trier les tâches par priorité (décroissante)
        sorted_tasks = sorted(tasks, key=lambda t: t.priority.value, reverse=True)
        
        # Créer une liste de coroutines pour les tâches asynchrones
        # et une liste de tâches à exécuter dans un pool de threads/processus
        async_tasks = []
        sync_tasks = []
        
        for task in sorted_tasks:
            if task.is_async:
                # Tâche asynchrone native
                async_tasks.append(self._run_async_task_wrapper(task))
            else:
                # Tâche synchrone à exécuter dans le thread/processpool
                sync_tasks.append(task)
        
        # Dictionnaire pour stocker les résultats
        results = {}
        
        # Exécuter les tâches asynchrones
        if async_tasks:
            async_results = await asyncio.gather(*async_tasks, return_exceptions=True)
            for task, result in zip(sorted_tasks[:len(async_tasks)], async_results):
                if isinstance(result, Exception):
                    logger.error(f"Erreur lors de l'exécution de la tâche async {task.name}: {str(result)}")
                    results[task.name] = AnalysisResult(
                        name=task.name,
                        result=task.fallback_value,
                        error=str(result),
                        success=False,
                        execution_time=0.0
                    )
                    self.stats["failed_tasks"] += 1
                else:
                    results[task.name] = result
                    self.stats["successful_tasks"] += 1
        
        # Exécuter les tâches synchrones dans le thread/processpool
        if sync_tasks:
            loop = asyncio.get_running_loop()
            executor = self._get_executor()
            
            # Créer des futures pour les tâches synchrones
            futures = {}
            for task in sync_tasks:
                future = loop.run_in_executor(
                    executor,
                    partial(
                        self._run_sync_task_with_stats,
                        task.func,
                        task.name,
                        task.timeout,
                        task.fallback_value,
                        *task.args,
                        **task.kwargs
                    )
                )
                futures[future] = task
                self.stats["total_tasks"] += 1
            
            # Attendre la fin de toutes les tâches
            pending = list(futures.keys())
            while pending:
                done, pending = await asyncio.wait(
                    pending, 
                    timeout=1.0,
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                for future in done:
                    task = futures[future]
                    try:
                        result = future.result()
                        results[task.name] = result
                        
                        if result.success:
                            self.stats["successful_tasks"] += 1
                            self.stats["total_execution_time"] += result.execution_time
                        else:
                            self.stats["failed_tasks"] += 1
                            if result.error == "Timeout":
                                self.stats["timeouts"] += 1
                        
                        logger.debug(f"Tâche terminée: {task.name} ({result.execution_time:.2f}s)")
                    except Exception as e:
                        logger.error(f"Erreur lors de la récupération du résultat pour {task.name}: {str(e)}")
                        results[task.name] = AnalysisResult(
                            name=task.name,
                            result=task.fallback_value,
                            error=str(e),
                            success=False,
                            execution_time=0.0
                        )
                        self.stats["failed_tasks"] += 1
        
        return results
    
    def _run_sync_task(
        self, 
        func: Callable, 
        name: str, 
        timeout: Optional[float],
        fallback_value: Any,
        *args, 
        **kwargs
    ) -> Any:
        """
        Exécute une tâche synchrone avec timeout.
        
        Args:
            func: La fonction à exécuter.
            name: Nom de la tâche.
            timeout: Timeout en secondes.
            fallback_value: Valeur de repli en cas d'erreur.
            *args: Arguments positionnels.
            **kwargs: Arguments nommés.
            
        Returns:
            Résultat de la fonction ou fallback_value en cas d'erreur.
        """
        try:
            if timeout:
                # Créer un futur avec timeout
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(func, *args, **kwargs)
                    return future.result(timeout=timeout)
            else:
                # Exécution directe
                return func(*args, **kwargs)
        except concurrent.futures.TimeoutError:
            logger.warning(f"Timeout pour la tâche: {name}")
            return fallback_value
        except Exception as e:
            logger.error(f"Erreur lors de l'exécution de la tâche {name}: {str(e)}")
            return fallback_value
    
    def _run_sync_task_with_stats(
        self, 
        func: Callable, 
        name: str, 
        timeout: Optional[float],
        fallback_value: Any,
        *args, 
        **kwargs
    ) -> AnalysisResult:
        """
        Exécute une tâche synchrone avec timeout et retourne un AnalysisResult.
        
        Args:
            func: La fonction à exécuter.
            name: Nom de la tâche.
            timeout: Timeout en secondes.
            fallback_value: Valeur de repli en cas d'erreur.
            *args: Arguments positionnels.
            **kwargs: Arguments nommés.
            
        Returns:
            AnalysisResult contenant le résultat ou l'erreur.
        """
        start_time = time.time()
        try:
            if timeout:
                # Créer un futur avec timeout
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(func, *args, **kwargs)
                    result = future.result(timeout=timeout)
            else:
                # Exécution directe
                result = func(*args, **kwargs)
            
            execution_time = time.time() - start_time
            return AnalysisResult(
                name=name,
                result=result,
                success=True,
                execution_time=execution_time
            )
        except concurrent.futures.TimeoutError:
            logger.warning(f"Timeout pour la tâche: {name}")
            return AnalysisResult(
                name=name,
                result=fallback_value,
                error="Timeout",
                success=False,
                execution_time=timeout or (time.time() - start_time)
            )
        except Exception as e:
            logger.error(f"Erreur lors de l'exécution de la tâche {name}: {str(e)}")
            execution_time = time.time() - start_time
            return AnalysisResult(
                name=name,
                result=fallback_value,
                error=str(e),
                success=False,
                execution_time=execution_time
            )
    
    async def _run_async_task(self, func, *args, **kwargs):
        """
        Exécute une fonction asynchrone dans une nouvelle boucle d'événements.
        
        Args:
            func: La fonction asynchrone à exécuter.
            *args: Arguments positionnels.
            **kwargs: Arguments nommés.
            
        Returns:
            Résultat de la fonction.
        """
        # Créer une nouvelle boucle d'événements
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # Exécuter la fonction asynchrone
            return loop.run_until_complete(func(*args, **kwargs))
        finally:
            # Fermer la boucle
            loop.close()
    
    async def _run_async_task_wrapper(self, task: AnalysisTask) -> AnalysisResult:
        """
        Wrapper pour exécuter une tâche asynchrone et capturer le résultat.
        
        Args:
            task: La tâche à exécuter.
            
        Returns:
            AnalysisResult contenant le résultat ou l'erreur.
        """
        start_time = time.time()
        try:
            # Créer une tâche asyncio avec timeout si nécessaire
            if task.timeout:
                coro = asyncio.wait_for(
                    task.func(*task.args, **task.kwargs),
                    timeout=task.timeout
                )
            else:
                coro = task.func(*task.args, **task.kwargs)
            
            # Exécuter la coroutine
            result = await coro
            
            execution_time = time.time() - start_time
            return AnalysisResult(
                name=task.name,
                result=result,
                success=True,
                execution_time=execution_time
            )
        except asyncio.TimeoutError:
            logger.warning(f"Timeout pour la tâche asynchrone: {task.name}")
            return AnalysisResult(
                name=task.name,
                result=task.fallback_value,
                error="Timeout",
                success=False,
                execution_time=task.timeout or (time.time() - start_time)
            )
        except Exception as e:
            logger.error(f"Erreur lors de l'exécution de la tâche asynchrone {task.name}: {str(e)}")
            execution_time = time.time() - start_time
            return AnalysisResult(
                name=task.name,
                result=task.fallback_value,
                error=str(e),
                success=False,
                execution_time=execution_time
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Récupère les statistiques d'exécution.
        
        Returns:
            Dictionnaire des statistiques.
        """
        stats = self.stats.copy()
        
        # Calculer des statistiques supplémentaires
        if stats["total_tasks"] > 0:
            stats["success_rate"] = stats["successful_tasks"] / stats["total_tasks"]
            stats["failure_rate"] = stats["failed_tasks"] / stats["total_tasks"]
            stats["timeout_rate"] = stats["timeouts"] / stats["total_tasks"]
        else:
            stats["success_rate"] = 0.0
            stats["failure_rate"] = 0.0
            stats["timeout_rate"] = 0.0
        
        if stats["successful_tasks"] > 0:
            stats["avg_execution_time"] = stats["total_execution_time"] / stats["successful_tasks"]
        else:
            stats["avg_execution_time"] = 0.0
        
        return stats
    
    def shutdown(self, wait: bool = True) -> None:
        """
        Arrête l'executor et libère les ressources.
        
        Args:
            wait: Attendre la fin des tâches en cours.
        """
        if self._executor:
            self._executor.shutdown(wait=wait)
            self._executor = None
            logger.info("Analyseur parallèle arrêté")
    
    def __del__(self):
        """Libère les ressources lors de la destruction de l'objet."""
        self.shutdown(wait=False)

# Instance singleton pour faciliter l'utilisation
_analyzer_instance = None

def get_parallel_analyzer(
    max_workers: Optional[int] = None,
    use_processes: bool = False
) -> ParallelAnalyzer:
    """
    Récupère l'instance singleton de l'analyseur parallèle.
    
    Args:
        max_workers: Nombre maximum de workers.
        use_processes: Utiliser des processus au lieu de threads.
        
    Returns:
        Instance de ParallelAnalyzer.
    """
    global _analyzer_instance
    if _analyzer_instance is None:
        _analyzer_instance = ParallelAnalyzer(
            max_workers=max_workers,
            use_processes=use_processes
        )
    return _analyzer_instance

# Exemple d'utilisation
async def example_usage():
    # Fonctions d'exemple
    def analyze_token(token_address: str) -> Dict[str, Any]:
        # Simuler un traitement long
        time.sleep(1)
        return {"address": token_address, "risk_score": 0.2}
    
    def analyze_liquidity(pool_address: str) -> Dict[str, Any]:
        # Simuler un traitement long
        time.sleep(1.5)
        return {"address": pool_address, "liquidity": 1000000}
    
    async def analyze_price_trend(token_address: str) -> Dict[str, Any]:
        # Simuler un traitement asynchrone
        await asyncio.sleep(0.8)
        return {"address": token_address, "trend": "bullish"}
    
    # Créer des tâches d'analyse
    tasks = [
        AnalysisTask(
            name="token_risk",
            func=analyze_token,
            args=("0x123abc",),
            priority=AnalysisPriority.HIGH,
            timeout=2.0
        ),
        AnalysisTask(
            name="liquidity",
            func=analyze_liquidity,
            args=("0xpool123",),
            priority=AnalysisPriority.NORMAL,
            timeout=2.0
        ),
        AnalysisTask(
            name="price_trend",
            func=analyze_price_trend,
            args=("0x123abc",),
            is_async=True,
            priority=AnalysisPriority.LOW
        )
    ]
    
    # Obtenir l'analyseur et exécuter les tâches
    analyzer = get_parallel_analyzer()
    results = await analyzer.run_tasks_async(tasks)
    
    # Afficher les résultats
    for name, result in results.items():
        print(f"{name}: {'SUCCESS' if result.success else 'FAILURE'}")
        print(f"  Result: {result.result}")
        print(f"  Time: {result.execution_time:.2f}s")
    
    # Afficher les statistiques
    stats = analyzer.get_stats()
    print(f"Success rate: {stats['success_rate']:.2f}")
    print(f"Average execution time: {stats['avg_execution_time']:.2f}s")

if __name__ == "__main__":
    asyncio.run(example_usage()) 