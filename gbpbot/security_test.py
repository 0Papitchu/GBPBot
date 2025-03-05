#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Script pour tester la sécurité de l'API GBPBot.
Ce script effectue une série de tests pour vérifier que les mesures de sécurité
sont correctement implémentées et fonctionnent comme prévu.
"""

import os
import sys
import time
import json
import argparse
import requests
from dotenv import load_dotenv
from loguru import logger
from concurrent.futures import ThreadPoolExecutor
import ipaddress
import socket
import random
import string

# Charger les variables d'environnement
load_dotenv()

# Configurer le logger
logger.remove()
logger.add(sys.stderr, level="INFO")
logger.add("security_test.log", rotation="10 MB", level="DEBUG")

class SecurityTester:
    """Classe pour tester la sécurité de l'API GBPBot."""
    
    def __init__(self, api_url=None, api_key=None):
        """
        Initialiser le testeur de sécurité.
        
        Args:
            api_url: URL de l'API à tester
            api_key: Clé API valide pour l'authentification
        """
        self.api_url = api_url or os.getenv("GBPBOT_API_URL", "http://127.0.0.1:5000")
        self.api_key = api_key or os.getenv("GBPBOT_API_KEY", "your_secure_api_key_here")
        self.timeout = 5
        self.results = {
            "auth_tests": [],
            "ip_tests": [],
            "rate_limit_tests": [],
            "input_validation_tests": [],
            "ssl_tests": []
        }
    
    def run_all_tests(self):
        """Exécuter tous les tests de sécurité."""
        logger.info("Démarrage des tests de sécurité pour l'API GBPBot")
        logger.info(f"URL de l'API: {self.api_url}")
        
        # Tester la connexion de base
        if not self._test_basic_connection():
            logger.error("Impossible de se connecter à l'API. Arrêt des tests.")
            return False
        
        # Exécuter les tests
        self._test_authentication()
        self._test_ip_restrictions()
        self._test_rate_limiting()
        self._test_input_validation()
        self._test_ssl()
        
        # Afficher le résumé
        self._print_summary()
        
        return True
    
    def _test_basic_connection(self):
        """Tester la connexion de base à l'API."""
        logger.info("Test de connexion de base à l'API...")
        try:
            response = requests.get(f"{self.api_url}/health", timeout=self.timeout)
            if response.status_code == 200:
                logger.info("Connexion de base réussie")
                return True
            else:
                logger.error(f"Échec de la connexion de base: {response.status_code}")
                return False
        except requests.RequestException as e:
            logger.error(f"Erreur de connexion: {e}")
            return False
    
    def _test_authentication(self):
        """Tester l'authentification de l'API."""
        logger.info("Test d'authentification...")
        
        # Test 1: Sans clé API
        test_result = {"name": "Sans clé API", "passed": False, "details": ""}
        try:
            response = requests.get(f"{self.api_url}/status", timeout=self.timeout)
            if response.status_code == 401:
                test_result["passed"] = True
                test_result["details"] = "Accès refusé comme prévu"
            else:
                test_result["details"] = f"Accès autorisé sans clé API: {response.status_code}"
        except requests.RequestException as e:
            test_result["details"] = f"Erreur: {e}"
        self.results["auth_tests"].append(test_result)
        logger.info(f"Test sans clé API: {'Réussi' if test_result['passed'] else 'Échoué'}")
        
        # Test 2: Avec clé API invalide
        test_result = {"name": "Clé API invalide", "passed": False, "details": ""}
        try:
            headers = {"x-api-key": "invalid_key_" + ''.join(random.choices(string.ascii_letters + string.digits, k=10))}
            response = requests.get(f"{self.api_url}/status", headers=headers, timeout=self.timeout)
            if response.status_code == 401:
                test_result["passed"] = True
                test_result["details"] = "Accès refusé comme prévu"
            else:
                test_result["details"] = f"Accès autorisé avec clé API invalide: {response.status_code}"
        except requests.RequestException as e:
            test_result["details"] = f"Erreur: {e}"
        self.results["auth_tests"].append(test_result)
        logger.info(f"Test avec clé API invalide: {'Réussi' if test_result['passed'] else 'Échoué'}")
        
        # Test 3: Avec clé API valide
        test_result = {"name": "Clé API valide", "passed": False, "details": ""}
        try:
            headers = {"x-api-key": self.api_key}
            response = requests.get(f"{self.api_url}/status", headers=headers, timeout=self.timeout)
            if response.status_code == 200:
                test_result["passed"] = True
                test_result["details"] = "Accès autorisé comme prévu"
            else:
                test_result["details"] = f"Accès refusé avec clé API valide: {response.status_code}"
        except requests.RequestException as e:
            test_result["details"] = f"Erreur: {e}"
        self.results["auth_tests"].append(test_result)
        logger.info(f"Test avec clé API valide: {'Réussi' if test_result['passed'] else 'Échoué'}")
    
    def _test_ip_restrictions(self):
        """Tester les restrictions d'IP."""
        logger.info("Test des restrictions d'IP...")
        
        # Test 1: Vérifier si les restrictions d'IP sont activées
        # Note: Ce test est informatif et ne peut pas être automatisé complètement
        test_result = {"name": "Vérification des restrictions d'IP", "passed": None, "details": ""}
        try:
            # Vérifier si l'IP locale est autorisée
            headers = {"x-api-key": self.api_key}
            response = requests.get(f"{self.api_url}/status", headers=headers, timeout=self.timeout)
            if response.status_code == 200:
                test_result["details"] = "L'IP locale est autorisée"
                test_result["passed"] = True
            else:
                test_result["details"] = f"L'IP locale n'est pas autorisée: {response.status_code}"
                test_result["passed"] = False
        except requests.RequestException as e:
            test_result["details"] = f"Erreur: {e}"
            test_result["passed"] = False
        self.results["ip_tests"].append(test_result)
        logger.info(f"Test de l'IP locale: {test_result['details']}")
        
        # Note: Pour tester avec différentes IPs, il faudrait utiliser un proxy ou un VPN
        # Ce qui n'est pas implémenté ici pour des raisons de simplicité
        logger.info("Pour tester avec différentes IPs, utilisez un proxy ou un VPN")
    
    def _test_rate_limiting(self):
        """Tester les limites de taux de requêtes."""
        logger.info("Test des limites de taux de requêtes...")
        
        # Test 1: Envoyer plusieurs requêtes en parallèle
        test_result = {"name": "Limite de taux de requêtes", "passed": False, "details": ""}
        headers = {"x-api-key": self.api_key}
        
        # Nombre de requêtes à envoyer
        num_requests = 20
        
        # Fonction pour envoyer une requête
        def send_request(i):
            try:
                response = requests.get(f"{self.api_url}/status", headers=headers, timeout=self.timeout)
                return response.status_code
            except requests.RequestException:
                return None
        
        # Envoyer les requêtes en parallèle
        status_codes = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            for status_code in executor.map(send_request, range(num_requests)):
                status_codes.append(status_code)
        
        # Vérifier si certaines requêtes ont été limitées (code 429)
        if 429 in status_codes:
            test_result["passed"] = True
            test_result["details"] = f"Limite de taux détectée après {status_codes.count(200)} requêtes réussies"
        else:
            test_result["details"] = f"Aucune limite de taux détectée après {num_requests} requêtes"
        
        self.results["rate_limit_tests"].append(test_result)
        logger.info(f"Test de limite de taux: {'Réussi' if test_result['passed'] else 'Échoué'}")
    
    def _test_input_validation(self):
        """Tester la validation des entrées."""
        logger.info("Test de validation des entrées...")
        
        # Test 1: Envoyer un mode invalide
        test_result = {"name": "Mode invalide", "passed": False, "details": ""}
        headers = {"x-api-key": self.api_key, "Content-Type": "application/json"}
        data = {"mode": "INVALID_MODE"}
        
        try:
            response = requests.post(f"{self.api_url}/change_mode", headers=headers, json=data, timeout=self.timeout)
            if response.status_code == 400:
                test_result["passed"] = True
                test_result["details"] = "Mode invalide rejeté comme prévu"
            else:
                test_result["details"] = f"Mode invalide accepté: {response.status_code}"
        except requests.RequestException as e:
            test_result["details"] = f"Erreur: {e}"
        
        self.results["input_validation_tests"].append(test_result)
        logger.info(f"Test de mode invalide: {'Réussi' if test_result['passed'] else 'Échoué'}")
        
        # Test 2: Envoyer une injection SQL basique
        test_result = {"name": "Injection SQL", "passed": False, "details": ""}
        headers = {"x-api-key": self.api_key, "Content-Type": "application/json"}
        data = {"mode": "TEST'; DROP TABLE users; --"}
        
        try:
            response = requests.post(f"{self.api_url}/change_mode", headers=headers, json=data, timeout=self.timeout)
            if response.status_code == 400:
                test_result["passed"] = True
                test_result["details"] = "Injection SQL rejetée comme prévu"
            else:
                test_result["details"] = f"Injection SQL potentiellement acceptée: {response.status_code}"
        except requests.RequestException as e:
            test_result["details"] = f"Erreur: {e}"
        
        self.results["input_validation_tests"].append(test_result)
        logger.info(f"Test d'injection SQL: {'Réussi' if test_result['passed'] else 'Échoué'}")
    
    def _test_ssl(self):
        """Tester la configuration SSL."""
        logger.info("Test de la configuration SSL...")
        
        # Test 1: Vérifier si HTTPS est utilisé
        test_result = {"name": "Utilisation de HTTPS", "passed": False, "details": ""}
        
        if self.api_url.startswith("https://"):
            try:
                response = requests.get(f"{self.api_url}/health", timeout=self.timeout, verify=True)
                if response.status_code == 200:
                    test_result["passed"] = True
                    test_result["details"] = "HTTPS configuré et fonctionnel"
                else:
                    test_result["details"] = f"HTTPS configuré mais erreur: {response.status_code}"
            except requests.RequestException as e:
                test_result["details"] = f"Erreur HTTPS: {e}"
        else:
            test_result["details"] = "HTTPS non configuré, utilisation de HTTP"
        
        self.results["ssl_tests"].append(test_result)
        logger.info(f"Test HTTPS: {test_result['details']}")
    
    def _print_summary(self):
        """Afficher un résumé des résultats des tests."""
        logger.info("\n=== RÉSUMÉ DES TESTS DE SÉCURITÉ ===")
        
        total_tests = 0
        passed_tests = 0
        
        for category, tests in self.results.items():
            category_name = category.replace("_", " ").title()
            logger.info(f"\n--- {category_name} ---")
            
            for test in tests:
                if test["passed"] is not None:
                    total_tests += 1
                    if test["passed"]:
                        passed_tests += 1
                        logger.info(f"✅ {test['name']}: {test['details']}")
                    else:
                        logger.info(f"❌ {test['name']}: {test['details']}")
                else:
                    logger.info(f"ℹ️ {test['name']}: {test['details']}")
        
        if total_tests > 0:
            success_rate = (passed_tests / total_tests) * 100
            logger.info(f"\nTaux de réussite: {success_rate:.1f}% ({passed_tests}/{total_tests})")
        
        logger.info("\nRecommandations:")
        if "auth_tests" in self.results and any(not test["passed"] for test in self.results["auth_tests"] if test["passed"] is not None):
            logger.info("- Renforcer l'authentification par clé API")
        
        if "ip_tests" in self.results and any(not test["passed"] for test in self.results["ip_tests"] if test["passed"] is not None):
            logger.info("- Configurer correctement les restrictions d'IP")
        
        if "rate_limit_tests" in self.results and any(not test["passed"] for test in self.results["rate_limit_tests"] if test["passed"] is not None):
            logger.info("- Améliorer les limites de taux de requêtes")
        
        if "input_validation_tests" in self.results and any(not test["passed"] for test in self.results["input_validation_tests"] if test["passed"] is not None):
            logger.info("- Renforcer la validation des entrées")
        
        if "ssl_tests" in self.results and any(not test["passed"] for test in self.results["ssl_tests"] if test["passed"] is not None):
            logger.info("- Configurer HTTPS correctement")
        
        logger.info("\n=== FIN DU RÉSUMÉ ===")

def main():
    """Fonction principale."""
    parser = argparse.ArgumentParser(description="Tester la sécurité de l'API GBPBot")
    parser.add_argument("--url", help="URL de l'API à tester", default=None)
    parser.add_argument("--key", help="Clé API valide pour l'authentification", default=None)
    args = parser.parse_args()
    
    tester = SecurityTester(api_url=args.url, api_key=args.key)
    tester.run_all_tests()

if __name__ == "__main__":
    main() 