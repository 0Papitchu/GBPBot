import time
import json
import aiohttp
import asyncio
import statistics
from datetime import datetime

class BlockchainBenchmark:
    def __init__(self):
        self.results = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "solana": {
                "rpc_endpoints": {},
                "comparison": {}
            }
        }
        
        # Liste des endpoints RPC Solana à tester
        self.solana_endpoints = {
            "public_rpc": "https://api.mainnet-beta.solana.com",
            "quicknode": "https://solana-mainnet.quicknode.com", # Remplacer par votre endpoint si vous en avez un
            "genesysgo": "https://ssc-dao.genesysgo.net",
            "serum": "https://solana-api.projectserum.com",
            "ankr": "https://rpc.ankr.com/solana"
        }
        
    async def test_endpoint(self, name, url, method="getHealth", params=None):
        """Teste la vitesse et la fiabilité d'un endpoint RPC"""
        if params is None:
            params = []
            
        headers = {
            "Content-Type": "application/json"
        }
        
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params
        }
        
        results = {
            "url": url,
            "success": False,
            "response_times": [],
            "errors": []
        }
        
        # Effectuer 5 tests par endpoint
        for i in range(5):
            try:
                start_time = time.time()
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, json=payload, headers=headers, timeout=10) as response:
                        await response.json()
                        
                end_time = time.time()
                response_time = end_time - start_time
                results["response_times"].append(response_time)
                results["success"] = True
                
                # Petite pause pour ne pas surcharger l'API
                await asyncio.sleep(0.5)
                
            except Exception as e:
                results["errors"].append(str(e))
                
        # Calculer les statistiques si nous avons des temps de réponse
        if results["response_times"]:
            results["avg_response_time"] = statistics.mean(results["response_times"])
            results["min_response_time"] = min(results["response_times"])
            results["max_response_time"] = max(results["response_times"])
            results["median_response_time"] = statistics.median(results["response_times"])
            
        return name, results
    
    async def test_solana_getblockheight(self, name, url):
        """Test spécifique pour obtenir la hauteur du bloc sur Solana"""
        return await self.test_endpoint(name, url, method="getBlockHeight", params=[])
    
    async def test_solana_getaccountinfo(self, name, url):
        """Test pour obtenir les informations d'un compte Solana connu"""
        # Utilise l'adresse du compte Serum comme exemple
        serum_program_id = "9xQeWvG816bUx9EPjHmaT23yvVM2ZWbrrpZb9PusVFin"
        return await self.test_endpoint(
            name, url, 
            method="getAccountInfo", 
            params=[serum_program_id, {"encoding": "base64"}]
        )
        
    async def benchmark_solana(self):
        """Exécute tous les benchmarks Solana"""
        print("Benchmarking des endpoints RPC Solana...")
        
        # Test du statut de santé de base
        print("  Testant getHealth...")
        health_tasks = [
            self.test_endpoint(name, url) 
            for name, url in self.solana_endpoints.items()
        ]
        health_results = await asyncio.gather(*health_tasks)
        
        # Test de la hauteur de bloc
        print("  Testant getBlockHeight...")
        blockheight_tasks = [
            self.test_solana_getblockheight(name, url) 
            for name, url in self.solana_endpoints.items()
        ]
        blockheight_results = await asyncio.gather(*blockheight_tasks)
        
        # Test d'obtention d'informations d'un compte
        print("  Testant getAccountInfo...")
        account_tasks = [
            self.test_solana_getaccountinfo(name, url) 
            for name, url in self.solana_endpoints.items()
        ]
        account_results = await asyncio.gather(*account_tasks)
        
        # Traitement des résultats
        for name, results in health_results:
            if name not in self.results["solana"]["rpc_endpoints"]:
                self.results["solana"]["rpc_endpoints"][name] = {}
            self.results["solana"]["rpc_endpoints"][name]["health"] = results
            
        for name, results in blockheight_results:
            if name not in self.results["solana"]["rpc_endpoints"]:
                self.results["solana"]["rpc_endpoints"][name] = {}
            self.results["solana"]["rpc_endpoints"][name]["blockheight"] = results
            
        for name, results in account_results:
            if name not in self.results["solana"]["rpc_endpoints"]:
                self.results["solana"]["rpc_endpoints"][name] = {}
            self.results["solana"]["rpc_endpoints"][name]["account_info"] = results
            
        # Analyse comparative
        self.compare_endpoints()
        
    def compare_endpoints(self):
        """Compare les endpoints et identifie le meilleur"""
        endpoints = self.results["solana"]["rpc_endpoints"]
        comparison = {
            "fastest_health": {"name": None, "time": float('inf')},
            "fastest_blockheight": {"name": None, "time": float('inf')},
            "fastest_accountinfo": {"name": None, "time": float('inf')},
            "overall_ranking": []
        }
        
        # Trouver les plus rapides pour chaque test
        for name, data in endpoints.items():
            if "health" in data and "avg_response_time" in data["health"]:
                if data["health"]["avg_response_time"] < comparison["fastest_health"]["time"]:
                    comparison["fastest_health"] = {
                        "name": name,
                        "time": data["health"]["avg_response_time"]
                    }
                    
            if "blockheight" in data and "avg_response_time" in data["blockheight"]:
                if data["blockheight"]["avg_response_time"] < comparison["fastest_blockheight"]["time"]:
                    comparison["fastest_blockheight"] = {
                        "name": name,
                        "time": data["blockheight"]["avg_response_time"]
                    }
                    
            if "account_info" in data and "avg_response_time" in data["account_info"]:
                if data["account_info"]["avg_response_time"] < comparison["fastest_accountinfo"]["time"]:
                    comparison["fastest_accountinfo"] = {
                        "name": name,
                        "time": data["account_info"]["avg_response_time"]
                    }
        
        # Calculer un score global
        scores = {}
        for name in endpoints.keys():
            score = 0
            count = 0
            
            if "health" in endpoints[name] and "avg_response_time" in endpoints[name]["health"]:
                score += 1 / endpoints[name]["health"]["avg_response_time"]
                count += 1
                
            if "blockheight" in endpoints[name] and "avg_response_time" in endpoints[name]["blockheight"]:
                score += 1 / endpoints[name]["blockheight"]["avg_response_time"]
                count += 1
                
            if "account_info" in endpoints[name] and "avg_response_time" in endpoints[name]["account_info"]:
                score += 1 / endpoints[name]["account_info"]["avg_response_time"]
                count += 1
                
            if count > 0:
                scores[name] = score / count
        
        # Trier les endpoints par score
        sorted_endpoints = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        comparison["overall_ranking"] = [
            {"name": name, "score": score} for name, score in sorted_endpoints
        ]
        
        self.results["solana"]["comparison"] = comparison
        
    async def run_benchmark(self):
        """Exécute tous les benchmarks"""
        await self.benchmark_solana()
        return self.results
        
    def save_results(self, filename="blockchain_benchmark_results.json"):
        """Sauvegarde les résultats dans un fichier JSON"""
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=4)
        print(f"Résultats sauvegardés dans {filename}")
        
    def print_summary(self):
        """Affiche un résumé des résultats"""
        print("\n" + "="*50)
        print("RÉSUMÉ DU BENCHMARK BLOCKCHAIN")
        print("="*50)
        
        # Afficher le classement global des endpoints Solana
        if "comparison" in self.results["solana"] and "overall_ranking" in self.results["solana"]["comparison"]:
            print("\nClassement des endpoints RPC Solana:")
            for i, endpoint in enumerate(self.results["solana"]["comparison"]["overall_ranking"]):
                print(f"{i+1}. {endpoint['name']} (score: {endpoint['score']:.2f})")
                
        # Afficher les endpoints les plus rapides par type de requête
        if "comparison" in self.results["solana"]:
            comp = self.results["solana"]["comparison"]
            
            if "fastest_health" in comp and comp["fastest_health"]["name"]:
                print(f"\nEndpoint le plus rapide pour getHealth: {comp['fastest_health']['name']} "
                      f"({comp['fastest_health']['time']:.4f}s)")
                
            if "fastest_blockheight" in comp and comp["fastest_blockheight"]["name"]:
                print(f"Endpoint le plus rapide pour getBlockHeight: {comp['fastest_blockheight']['name']} "
                      f"({comp['fastest_blockheight']['time']:.4f}s)")
                
            if "fastest_accountinfo" in comp and comp["fastest_accountinfo"]["name"]:
                print(f"Endpoint le plus rapide pour getAccountInfo: {comp['fastest_accountinfo']['name']} "
                      f"({comp['fastest_accountinfo']['time']:.4f}s)")
                
        print("\nRecommandation: Utiliser l'endpoint classé #1 pour des performances optimales.")
        print("="*50)

async def main():
    benchmark = BlockchainBenchmark()
    await benchmark.run_benchmark()
    benchmark.save_results("benchmarking/blockchain_benchmark_results.json")
    benchmark.print_summary()

if __name__ == "__main__":
    asyncio.run(main()) 