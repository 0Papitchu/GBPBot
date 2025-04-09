#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests unitaires pour le module de monitoring

Ce module teste les fonctionnalités du système de monitoring du GBPBot,
qui est crucial pour surveiller les performances et les ressources utilisées.
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ajout du chemin racine au sys.path pour les imports
ROOT_DIR = Path(__file__).parent.parent.parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Import des modules de test
from gbpbot.tests.setup_test_environment import setup_test_environment, cleanup_test_environment


class TestMonitoringModule(unittest.TestCase):
    """Suite de tests pour les modules de monitoring du GBPBot"""
    
    @classmethod
    def setUpClass(cls):
        """
        Préparation de l'environnement de test avant l'exécution des tests
        """
        # Configuration de l'environnement de test
        cls.env_file, cls.wallet_paths = setup_test_environment()
        
        # Configuration pour les tests
        cls.test_config = {
            "monitoring": {
                "cpu_threshold": 80.0,    # Seuil CPU en %
                "memory_threshold": 70.0, # Seuil mémoire en %
                "disk_threshold": 85.0,   # Seuil disque en %
                "check_interval": 5.0,    # Intervalle de vérification en secondes
                "enabled": True
            },
            "optimization": {
                "auto_optimize": True,
                "ml_memory_limit": 4096,  # Limite de mémoire en Mo pour le ML
                "tx_history_limit": 1000, # Limite d'historique des transactions
                "connection_pool_size": 10 # Taille du pool de connexions
            }
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
        # Tenter d'importer le module de monitoring, avec gestion des erreurs
        try:
            from gbpbot.core.monitoring.compatibility import ResourceMonitorCompat, PerformanceMonitorCompat, HardwareOptimizerCompat
            self.resource_monitor_class = ResourceMonitorCompat
            self.performance_monitor_class = PerformanceMonitorCompat
            self.hardware_optimizer_class = HardwareOptimizerCompat
        except ImportError as e:
            self.skipTest(f"Module de monitoring non disponible: {str(e)}")
    
    def test_module_import(self):
        """
        Test de l'importation du module de monitoring
        """
        # Vérifier que les modules ont été importés correctement
        self.assertIsNotNone(self.resource_monitor_class, "La classe ResourceMonitorCompat n'a pas pu être importée")
        self.assertIsNotNone(self.performance_monitor_class, "La classe PerformanceMonitorCompat n'a pas pu être importée")
        self.assertIsNotNone(self.hardware_optimizer_class, "La classe HardwareOptimizerCompat n'a pas pu être importée")
    
    def test_resource_monitor_initialization(self):
        """
        Test de l'initialisation du moniteur de ressources
        """
        # Instancier le moniteur de ressources
        resource_monitor = self.resource_monitor_class()
        
        # Vérifier l'initialisation
        self.assertIsNotNone(resource_monitor, "Le moniteur de ressources n'a pas été instancié correctement")
        
        # Vérifier l'état initial
        self.assertFalse(resource_monitor._running, "Le moniteur ne devrait pas être en cours d'exécution à l'initialisation")
    
    def test_resource_monitor_start_stop(self):
        """
        Test du démarrage et de l'arrêt du moniteur de ressources
        """
        # Instancier le moniteur de ressources
        resource_monitor = self.resource_monitor_class()
        
        # Tester le démarrage
        resource_monitor.start()
        self.assertTrue(resource_monitor._running, "Le moniteur devrait être en cours d'exécution après démarrage")
        
        # Tester l'arrêt
        resource_monitor.stop()
        self.assertFalse(resource_monitor._running, "Le moniteur ne devrait pas être en cours d'exécution après arrêt")
    
    @patch("gbpbot.core.monitoring.compatibility.ResourceMonitorCompat._check_resources")
    def test_resource_monitor_callback(self, mock_check_resources):
        """
        Test des callbacks du moniteur de ressources
        """
        # Instancier le moniteur de ressources
        resource_monitor = self.resource_monitor_class()
        
        # Créer un mock pour le callback
        callback_mock = MagicMock()
        
        # Enregistrer le callback
        resource_monitor.subscribe("cpu", callback_mock)
        
        # Vérifier que le callback a été enregistré
        self.assertIn(callback_mock, resource_monitor._callbacks, "Le callback n'a pas été correctement enregistré")
        
        # Désinscrire le callback
        result = resource_monitor.unsubscribe("cpu", callback_mock)
        
        # Vérifier que le callback a été désinscrit
        self.assertTrue(result, "La désinscription du callback a échoué")
        self.assertNotIn(callback_mock, resource_monitor._callbacks, "Le callback n'a pas été correctement désinscrit")
    
    def test_resource_monitor_thresholds(self):
        """
        Test de la mise à jour des seuils du moniteur de ressources
        """
        # Instancier le moniteur de ressources
        resource_monitor = self.resource_monitor_class()
        
        # Mettre à jour les seuils
        resource_monitor.update_thresholds(cpu=90.0, memory=80.0, disk=95.0, interval=10.0)
        
        # Vérifier les nouveaux seuils dans la configuration
        state = resource_monitor.get_current_state()
        
        self.assertEqual(state["thresholds"]["cpu"], 90.0, "Le seuil CPU n'a pas été correctement mis à jour")
        self.assertEqual(state["thresholds"]["memory"], 80.0, "Le seuil mémoire n'a pas été correctement mis à jour")
        self.assertEqual(state["thresholds"]["disk"], 95.0, "Le seuil disque n'a pas été correctement mis à jour")
        self.assertEqual(state["check_interval"], 10.0, "L'intervalle de vérification n'a pas été correctement mis à jour")
    
    def test_performance_monitor_initialization(self):
        """
        Test de l'initialisation du moniteur de performances
        """
        # Instancier le moniteur de performances
        performance_monitor = self.performance_monitor_class()
        
        # Vérifier l'initialisation
        self.assertIsNotNone(performance_monitor, "Le moniteur de performances n'a pas été instancié correctement")
    
    def test_performance_monitor_start_stop(self):
        """
        Test du démarrage et de l'arrêt du moniteur de performances
        """
        # Instancier le moniteur de performances
        performance_monitor = self.performance_monitor_class()
        
        # Tester le démarrage
        result = performance_monitor.start_monitoring()
        self.assertTrue(result, "Le démarrage du moniteur de performances a échoué")
        
        # Tester l'arrêt
        result = performance_monitor.stop_monitoring()
        self.assertTrue(result, "L'arrêt du moniteur de performances a échoué")
    
    def test_performance_monitor_track_metric(self):
        """
        Test du suivi des métriques du moniteur de performances
        """
        # Instancier le moniteur de performances
        performance_monitor = self.performance_monitor_class()
        
        # Démarrer le monitoring
        performance_monitor.start_monitoring()
        
        # Suivre une métrique
        performance_monitor.track_metric("test_metric", 42.0)
        
        # Récupérer le rapport des métriques
        metrics_report = performance_monitor.get_metrics_report()
        
        # Vérifier que la métrique est présente dans le rapport
        self.assertIn("custom", metrics_report, "La section 'custom' est absente du rapport de métriques")
        self.assertIn("test_metric", metrics_report["custom"], "La métrique de test n'est pas présente dans le rapport")
        self.assertEqual(metrics_report["custom"]["test_metric"], 42.0, "La valeur de la métrique de test est incorrecte")
        
        # Arrêter le monitoring
        performance_monitor.stop_monitoring()
    
    def test_hardware_optimizer_initialization(self):
        """
        Test de l'initialisation de l'optimiseur matériel
        """
        # Instancier l'optimiseur matériel
        hardware_optimizer = self.hardware_optimizer_class(config=self.test_config)
        
        # Vérifier l'initialisation
        self.assertIsNotNone(hardware_optimizer, "L'optimiseur matériel n'a pas été instancié correctement")
        self.assertEqual(hardware_optimizer.config, self.test_config, "La configuration n'a pas été correctement assignée")
    
    def test_hardware_optimizer_info(self):
        """
        Test de la récupération des informations matérielles
        """
        # Instancier l'optimiseur matériel
        hardware_optimizer = self.hardware_optimizer_class(config=self.test_config)
        
        # Récupérer les informations matérielles
        hw_info = hardware_optimizer.hardware_info
        
        # Vérifier les informations de base
        self.assertIsNotNone(hw_info, "Les informations matérielles sont nulles")
        self.assertIn("cpu", hw_info, "Les informations CPU sont absentes")
        self.assertIn("memory", hw_info, "Les informations mémoire sont absentes")
        self.assertIn("disk", hw_info, "Les informations disque sont absentes")
    
    def test_hardware_optimizer_apply_optimizations(self):
        """
        Test de l'application des optimisations matérielles
        """
        # Instancier l'optimiseur matériel
        hardware_optimizer = self.hardware_optimizer_class(config=self.test_config)
        
        # Appliquer les optimisations
        result = hardware_optimizer.apply_optimizations(target="cpu")
        
        # Vérifier le résultat
        self.assertTrue(result, "L'application des optimisations CPU a échoué")
        
        # Tester avec une cible différente
        result = hardware_optimizer.apply_optimizations(target="memory")
        self.assertTrue(result, "L'application des optimisations mémoire a échoué")
        
        # Tester avec toutes les cibles
        result = hardware_optimizer.apply_optimizations(target="all")
        self.assertTrue(result, "L'application de toutes les optimisations a échoué")
    
    def test_hardware_optimizer_recommendations(self):
        """
        Test de la récupération des recommandations d'optimisation
        """
        # Instancier l'optimiseur matériel
        hardware_optimizer = self.hardware_optimizer_class(config=self.test_config)
        
        # Récupérer les recommandations
        recommendations = hardware_optimizer.get_recommendations()
        
        # Vérifier les recommandations
        self.assertIsNotNone(recommendations, "Les recommandations sont nulles")
        self.assertIsInstance(recommendations, list, "Les recommandations devraient être une liste")


if __name__ == "__main__":
    unittest.main() 