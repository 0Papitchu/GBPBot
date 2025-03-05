import requests
import time
import concurrent.futures
import argparse
import statistics
from loguru import logger
import matplotlib.pyplot as plt
import numpy as np
from tqdm import tqdm

# Configuration du logger
logger.add("stress_test.log", rotation="10 MB", retention="7 days", level="INFO")

# Configuration par défaut
DEFAULT_API_URL = "http://127.0.0.1:5000"
DEFAULT_API_KEY = "your_secure_api_key_here"
DEFAULT_CONCURRENT_REQUESTS = 10
DEFAULT_TOTAL_REQUESTS = 1000

class APIStressTester:
    def __init__(self, api_url, api_key, concurrent_requests, total_requests):
        self.api_url = api_url
        self.api_key = api_key
        self.concurrent_requests = concurrent_requests
        self.total_requests = total_requests
        self.headers = {"x-api-key": api_key}
        self.response_times = []
        self.success_count = 0
        self.error_count = 0
        self.error_types = {}
        
    def make_request(self, endpoint):
        """Effectue une requête à l'API et mesure le temps de réponse"""
        start_time = time.time()
        try:
            response = requests.get(f"{self.api_url}/{endpoint}", headers=self.headers, timeout=10)
            elapsed_time = time.time() - start_time
            
            if response.status_code == 200:
                self.success_count += 1
                self.response_times.append(elapsed_time)
                return True, elapsed_time, response.status_code
            else:
                self.error_count += 1
                error_key = f"HTTP {response.status_code}"
                self.error_types[error_key] = self.error_types.get(error_key, 0) + 1
                return False, elapsed_time, response.status_code
                
        except requests.exceptions.Timeout:
            self.error_count += 1
            self.error_types["Timeout"] = self.error_types.get("Timeout", 0) + 1
            return False, time.time() - start_time, "Timeout"
        except requests.exceptions.ConnectionError:
            self.error_count += 1
            self.error_types["ConnectionError"] = self.error_types.get("ConnectionError", 0) + 1
            return False, time.time() - start_time, "ConnectionError"
        except Exception as e:
            self.error_count += 1
            error_type = type(e).__name__
            self.error_types[error_type] = self.error_types.get(error_type, 0) + 1
            return False, time.time() - start_time, error_type
    
    def run_test(self, endpoint="status"):
        """Exécute le test de stress avec des requêtes concurrentes"""
        logger.info(f"Démarrage du test de stress sur {self.api_url}/{endpoint}")
        logger.info(f"Nombre total de requêtes: {self.total_requests}")
        logger.info(f"Requêtes concurrentes: {self.concurrent_requests}")
        
        results = []
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.concurrent_requests) as executor:
            futures = [executor.submit(self.make_request, endpoint) for _ in range(self.total_requests)]
            
            for future in tqdm(concurrent.futures.as_completed(futures), total=self.total_requests, desc="Requêtes"):
                results.append(future.result())
        
        return results
    
    def analyze_results(self):
        """Analyse les résultats du test de stress"""
        if not self.response_times:
            logger.error("Aucune requête réussie, impossible d'analyser les résultats")
            return
            
        # Calcul des statistiques
        avg_response_time = statistics.mean(self.response_times)
        median_response_time = statistics.median(self.response_times)
        min_response_time = min(self.response_times)
        max_response_time = max(self.response_times)
        p95_response_time = np.percentile(self.response_times, 95)
        
        success_rate = (self.success_count / self.total_requests) * 100
        
        # Affichage des résultats
        logger.info("=== Résultats du test de stress ===")
        logger.info(f"Requêtes réussies: {self.success_count}/{self.total_requests} ({success_rate:.2f}%)")
        logger.info(f"Requêtes en erreur: {self.error_count}/{self.total_requests} ({100-success_rate:.2f}%)")
        logger.info(f"Temps de réponse moyen: {avg_response_time:.4f} secondes")
        logger.info(f"Temps de réponse médian: {median_response_time:.4f} secondes")
        logger.info(f"Temps de réponse minimum: {min_response_time:.4f} secondes")
        logger.info(f"Temps de réponse maximum: {max_response_time:.4f} secondes")
        logger.info(f"Temps de réponse P95: {p95_response_time:.4f} secondes")
        
        if self.error_count > 0:
            logger.info("=== Types d'erreurs ===")
            for error_type, count in self.error_types.items():
                logger.info(f"{error_type}: {count} occurrences ({(count/self.error_count)*100:.2f}%)")
        
        # Création des graphiques
        self.create_graphs()
        
        return {
            "success_count": self.success_count,
            "error_count": self.error_count,
            "success_rate": success_rate,
            "avg_response_time": avg_response_time,
            "median_response_time": median_response_time,
            "min_response_time": min_response_time,
            "max_response_time": max_response_time,
            "p95_response_time": p95_response_time,
            "error_types": self.error_types
        }
    
    def create_graphs(self):
        """Crée des graphiques pour visualiser les résultats"""
        plt.figure(figsize=(15, 10))
        
        # Graphique 1: Distribution des temps de réponse
        plt.subplot(2, 2, 1)
        plt.hist(self.response_times, bins=30, alpha=0.7, color='blue')
        plt.axvline(statistics.mean(self.response_times), color='red', linestyle='dashed', linewidth=1, label=f'Moyenne: {statistics.mean(self.response_times):.4f}s')
        plt.axvline(statistics.median(self.response_times), color='green', linestyle='dashed', linewidth=1, label=f'Médiane: {statistics.median(self.response_times):.4f}s')
        plt.axvline(np.percentile(self.response_times, 95), color='orange', linestyle='dashed', linewidth=1, label=f'P95: {np.percentile(self.response_times, 95):.4f}s')
        plt.title('Distribution des temps de réponse')
        plt.xlabel('Temps (secondes)')
        plt.ylabel('Nombre de requêtes')
        plt.legend()
        
        # Graphique 2: Taux de succès vs erreurs
        plt.subplot(2, 2, 2)
        plt.pie([self.success_count, self.error_count], 
                labels=['Succès', 'Erreurs'], 
                autopct='%1.1f%%',
                colors=['green', 'red'],
                startangle=90)
        plt.title('Taux de succès vs erreurs')
        
        # Graphique 3: Types d'erreurs
        if self.error_count > 0:
            plt.subplot(2, 2, 3)
            error_labels = list(self.error_types.keys())
            error_values = list(self.error_types.values())
            plt.bar(error_labels, error_values, color='red')
            plt.title('Types d\'erreurs')
            plt.xlabel('Type d\'erreur')
            plt.ylabel('Nombre d\'occurrences')
            plt.xticks(rotation=45, ha='right')
        
        # Graphique 4: Temps de réponse au fil du temps
        plt.subplot(2, 2, 4)
        plt.plot(range(len(self.response_times)), self.response_times, 'b-')
        plt.title('Temps de réponse au fil du temps')
        plt.xlabel('Numéro de requête')
        plt.ylabel('Temps (secondes)')
        
        plt.tight_layout()
        plt.savefig('stress_test_results.png')
        logger.info("Graphiques sauvegardés dans stress_test_results.png")

def main():
    parser = argparse.ArgumentParser(description='Outil de stress test pour l\'API GBPBot')
    parser.add_argument('--url', type=str, default=DEFAULT_API_URL, help='URL de l\'API')
    parser.add_argument('--key', type=str, default=DEFAULT_API_KEY, help='Clé API')
    parser.add_argument('--concurrent', type=int, default=DEFAULT_CONCURRENT_REQUESTS, help='Nombre de requêtes concurrentes')
    parser.add_argument('--total', type=int, default=DEFAULT_TOTAL_REQUESTS, help='Nombre total de requêtes')
    parser.add_argument('--endpoint', type=str, default='status', help='Endpoint à tester')
    
    args = parser.parse_args()
    
    tester = APIStressTester(args.url, args.key, args.concurrent, args.total)
    tester.run_test(args.endpoint)
    tester.analyze_results()

if __name__ == "__main__":
    main() 