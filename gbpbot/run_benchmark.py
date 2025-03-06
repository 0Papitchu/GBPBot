#!/usr/bin/env python3
"""
Script facilitant l'exécution des benchmarks pour optimiser GBPBot
"""

import sys
import os
import argparse
import asyncio
import importlib.util
import platform


BENCHMARK_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "benchmarking")


def import_module_from_path(module_name, file_path):
    """Importe dynamiquement un module Python à partir d'un chemin"""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None:
        print(f"Erreur: Impossible de trouver le module {module_name} à {file_path}")
        return None
        
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def ensure_benchmark_modules():
    """Vérifie si les modules de benchmark sont disponibles"""
    if not os.path.exists(BENCHMARK_DIR):
        print(f"Erreur: Répertoire de benchmarking introuvable à {BENCHMARK_DIR}")
        print("Veuillez exécuter ce script depuis le répertoire racine du projet GBPBot")
        return False
        
    required_modules = [
        "run_benchmarks.py",
        "system_benchmark.py",
        "blockchain_benchmark.py",
        "dex_benchmark.py",
        "transaction_benchmark.py"
    ]
    
    for module in required_modules:
        if not os.path.exists(os.path.join(BENCHMARK_DIR, module)):
            print(f"Erreur: Module de benchmark {module} introuvable")
            print("Veuillez vous assurer que les scripts de benchmarking sont correctement installés")
            return False
            
    return True


async def main():
    """Fonction principale"""
    parser = argparse.ArgumentParser(description="Utilitaire de benchmarking pour GBPBot")
    parser.add_argument("--all", action="store_true", help="Exécuter tous les benchmarks")
    parser.add_argument("--system", action="store_true", help="Benchmark du système uniquement")
    parser.add_argument("--blockchain", action="store_true", help="Benchmark de la blockchain uniquement")
    parser.add_argument("--dex", action="store_true", help="Benchmark des DEX uniquement")
    parser.add_argument("--transaction", action="store_true", help="Benchmark des transactions uniquement")
    parser.add_argument("--report", action="store_true", help="Générer uniquement le rapport")
    parser.add_argument("--optimize", action="store_true", help="Optimiser GBPBot en fonction des résultats")
    
    args = parser.parse_args()
    
    # Vérifier que les modules de benchmark sont disponibles
    if not ensure_benchmark_modules():
        return 1
        
    # Importer le module principal de benchmark
    try:
        run_benchmarks_path = os.path.join(BENCHMARK_DIR, "run_benchmarks.py")
        run_benchmarks = import_module_from_path("run_benchmarks", run_benchmarks_path)
        
        if not run_benchmarks or not hasattr(run_benchmarks, "main"):
            print("Erreur: Module run_benchmarks.py invalide ou incomplet")
            return 1
    except Exception as e:
        print(f"Erreur lors de l'importation du module de benchmark: {str(e)}")
        return 1
    
    # Préparer les arguments pour le module de benchmark
    benchmark_args = []
    
    if args.all:
        benchmark_args.append("--all")
    else:
        if args.system:
            benchmark_args.append("--system")
        if args.blockchain:
            benchmark_args.append("--blockchain")
        if args.dex:
            benchmark_args.append("--dex")
        if args.transaction:
            benchmark_args.append("--transaction")
            
    if args.report:
        benchmark_args.append("--report")
        
    # Modifier les arguments système et exécuter le benchmark
    original_argv = sys.argv.copy()
    sys.argv = [run_benchmarks_path] + benchmark_args
    
    try:
        # Exécuter le benchmark
        print(f"Exécution des benchmarks avec arguments: {' '.join(benchmark_args)}")
        await run_benchmarks.main()
        
        # Si l'option --optimize est activée, appliquer les optimisations
        if args.optimize:
            print("\nOptimisation de GBPBot en fonction des résultats de benchmark...")
            await optimize_gbpbot()
            
        print("\nBenchmark terminé avec succès!")
        return 0
    except Exception as e:
        print(f"Erreur lors de l'exécution du benchmark: {str(e)}")
        return 1
    finally:
        # Restaurer les arguments d'origine
        sys.argv = original_argv
        

async def optimize_gbpbot():
    """Optimise la configuration de GBPBot en fonction des résultats de benchmark"""
    import json
    
    # Dossier contenant les résultats
    results_dir = os.path.join(os.path.dirname(BENCHMARK_DIR), "benchmark_results")
    consolidated_results_path = os.path.join(results_dir, "consolidated_results.json")
    
    if not os.path.exists(consolidated_results_path):
        print(f"Erreur: Fichier de résultats consolidés introuvable à {consolidated_results_path}")
        return
        
    # Charger les résultats
    try:
        with open(consolidated_results_path, 'r') as f:
            results = json.load(f)
    except Exception as e:
        print(f"Erreur lors de la lecture des résultats: {str(e)}")
        return
        
    # Créer le répertoire de configuration s'il n'existe pas
    config_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "core")
    os.makedirs(config_dir, exist_ok=True)
    
    # Générer la configuration optimisée
    config = {
        "version": "1.0.0",
        "optimized_at": results.get("timestamp", ""),
        "system_specs": {},
        "blockchain": {
            "solana": {
                "rpc_endpoints": []
            }
        },
        "dex": {
            "preferred_dex": []
        },
        "resource_limits": {},
        "performance_mode": "auto"
    }
    
    # Extraire les informations système
    if "benchmarks" in results and "system" in results["benchmarks"]:
        system_data = results["benchmarks"]["system"]
        
        if "system" in system_data:
            config["system_specs"] = {
                "platform": system_data["system"].get("platform", ""),
                "cpu_cores": system_data["system"].get("cpu_cores_logical", 0),
                "ram_gb": system_data["system"].get("ram_total_gb", 0),
                "architecture": system_data["system"].get("architecture", "")
            }
            
        # Configurer les limites de ressources
        if "cpu" in system_data and "memory" in system_data:
            max_threads = max(1, min(8, config["system_specs"].get("cpu_cores", 1) - 1))
            
            config["resource_limits"] = {
                "max_threads": max_threads,
                "max_ram_usage_percent": min(75, max(50, 90 - (8 / config["system_specs"].get("ram_gb", 8) * 20))),
                "cache_size_mb": min(500, max(50, config["system_specs"].get("ram_gb", 8) * 50)),
                "log_level": "INFO"
            }
            
            # Déterminer le mode de performance
            if config["system_specs"].get("cpu_cores", 0) >= 8 and config["system_specs"].get("ram_gb", 0) >= 16:
                config["performance_mode"] = "high"
            elif config["system_specs"].get("cpu_cores", 0) >= 4 and config["system_specs"].get("ram_gb", 0) >= 8:
                config["performance_mode"] = "balanced"
            else:
                config["performance_mode"] = "economy"
                
    # Extraire les meilleurs endpoints RPC
    if "benchmarks" in results and "blockchain" in results["benchmarks"]:
        blockchain_data = results["benchmarks"]["blockchain"]
        
        if "solana" in blockchain_data and "endpoints" in blockchain_data["solana"]:
            # Trier les endpoints par temps de réponse
            endpoints = []
            for name, data in blockchain_data["solana"]["endpoints"].items():
                if "average_response_time" in data and data.get("status") == "online":
                    endpoints.append({
                        "name": name,
                        "url": data.get("url", ""),
                        "response_time": data["average_response_time"],
                        "success_rate": data.get("success_rate", 0)
                    })
                    
            # Sélectionner les 3 meilleurs endpoints
            endpoints.sort(key=lambda x: x["response_time"])
            for endpoint in endpoints[:3]:
                config["blockchain"]["solana"]["rpc_endpoints"].append({
                    "name": endpoint["name"],
                    "url": endpoint["url"],
                    "priority": endpoints.index(endpoint) + 1
                })
                
    # Extraire les meilleurs DEX
    if "benchmarks" in results and "dex" in results["benchmarks"]:
        dex_data = results["benchmarks"]["dex"]
        
        if "solana" in dex_data and "comparison" in dex_data["solana"]:
            if "overall_ranking" in dex_data["solana"]["comparison"]:
                for dex_name, score in dex_data["solana"]["comparison"]["overall_ranking"]:
                    config["dex"]["preferred_dex"].append({
                        "name": dex_name,
                        "score": score,
                        "priority": dex_data["solana"]["comparison"]["overall_ranking"].index([dex_name, score]) + 1
                    })
                    
    # Sauvegarder la configuration
    config_path = os.path.join(config_dir, "optimized_config.json")
    try:
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)
        print(f"Configuration optimisée sauvegardée dans {config_path}")
    except Exception as e:
        print(f"Erreur lors de la sauvegarde de la configuration: {str(e)}")
        

if __name__ == "__main__":
    # Gérer les différences entre Windows et Unix pour les coroutines
    if platform.system() == "Windows":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    exit_code = asyncio.run(main())
    sys.exit(exit_code) 