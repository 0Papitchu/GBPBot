import asyncio
import os
import sys
import subprocess
import json
import argparse
from datetime import datetime

# Importer les modules de benchmark une fois les dépendances installées
benchmark_modules = {
    "system": "system_benchmark",
    "blockchain": "blockchain_benchmark",
    "dex": "dex_benchmark",
    "transaction": "transaction_benchmark"
}

def check_and_install_dependencies():
    """Vérifie et installe les dépendances nécessaires"""
    print("Vérification et installation des dépendances...")
    
    # Liste des packages requis
    required_packages = [
        "psutil",         # Pour les métriques système
        "aiohttp",        # Pour les requêtes HTTP asynchrones
        "speedtest-cli",  # Pour les tests de vitesse Internet
        "matplotlib",     # Pour la génération de graphiques
        "pandas"          # Pour l'analyse des données
    ]
    
    # Vérifier quels packages sont déjà installés
    installed = []
    missing = []
    
    for package in required_packages:
        try:
            __import__(package.replace("-", "_"))
            installed.append(package)
        except ImportError:
            missing.append(package)
    
    # Installer les packages manquants
    if missing:
        print(f"Installation des packages manquants: {', '.join(missing)}")
        
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])
            print("Installation des dépendances terminée.")
        except subprocess.CalledProcessError as e:
            print(f"Erreur lors de l'installation des dépendances: {str(e)}")
            print("Veuillez installer manuellement les packages suivants:")
            for package in missing:
                print(f"  - {package}")
            return False
    else:
        print("Toutes les dépendances sont déjà installées.")
    
    return True

async def run_benchmark(benchmark_type):
    """Exécute un benchmark spécifique"""
    if benchmark_type not in benchmark_modules:
        print(f"Benchmark inconnu: {benchmark_type}")
        return False
    
    module_name = benchmark_modules[benchmark_type]
    
    try:
        # Import dynamique du module de benchmark
        module = __import__(module_name)
        
        print(f"\nExécution du benchmark {benchmark_type}...")
        
        # Appel de la fonction main() du module
        if hasattr(module, 'main'):
            if asyncio.iscoroutinefunction(module.main):
                await module.main()
            else:
                module.main()
        else:
            print(f"Erreur: Le module {module_name} n'a pas de fonction main().")
            return False
        
        return True
    except ImportError as e:
        print(f"Erreur lors de l'importation du module {module_name}: {str(e)}")
        return False
    except Exception as e:
        print(f"Erreur lors de l'exécution du benchmark {benchmark_type}: {str(e)}")
        return False

def generate_report(output_dir="benchmark_results"):
    """Génère un rapport consolidé à partir des résultats de benchmark"""
    print("\nGénération du rapport consolidé...")
    
    # Créer le répertoire de sortie s'il n'existe pas
    os.makedirs(output_dir, exist_ok=True)
    
    # Collecter tous les fichiers de résultats
    result_files = {
        "system": "benchmarking/system_benchmark_results.json",
        "blockchain": "benchmarking/blockchain_benchmark_results.json",
        "dex": "benchmarking/dex_benchmark_results.json",
        "transaction": "benchmarking/transaction_benchmark_results.json"
    }
    
    consolidated_results = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "benchmarks": {}
    }
    
    # Charger les données de chaque fichier de résultats
    for benchmark_type, file_path in result_files.items():
        try:
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    consolidated_results["benchmarks"][benchmark_type] = data
                    print(f"Résultats du benchmark {benchmark_type} chargés.")
            else:
                print(f"Fichier de résultats non trouvé: {file_path}")
        except Exception as e:
            print(f"Erreur lors de la lecture de {file_path}: {str(e)}")
    
    # Sauvegarder les résultats consolidés
    output_file = os.path.join(output_dir, "consolidated_results.json")
    with open(output_file, 'w') as f:
        json.dump(consolidated_results, f, indent=4)
    
    print(f"Rapport consolidé sauvegardé dans: {output_file}")
    
    # Générer un rapport HTML si matplotlib est disponible
    try:
        import matplotlib.pyplot as plt
        import pandas as pd
        
        print("Génération des graphiques...")
        
        # Créer un répertoire pour les graphiques
        charts_dir = os.path.join(output_dir, "charts")
        os.makedirs(charts_dir, exist_ok=True)
        
        # Exemple: Graphique de temps de bloc Solana
        if "blockchain" in consolidated_results["benchmarks"] and \
           "solana" in consolidated_results["benchmarks"]["blockchain"]:
            
            solana_data = consolidated_results["benchmarks"]["blockchain"]["solana"]
            
            if "endpoints" in solana_data:
                # Graphique des temps de réponse des endpoints
                endpoints = []
                response_times = []
                
                for endpoint, data in solana_data["endpoints"].items():
                    if "average_response_time" in data:
                        endpoints.append(endpoint)
                        response_times.append(data["average_response_time"])
                
                if endpoints and response_times:
                    plt.figure(figsize=(10, 6))
                    plt.bar(endpoints, response_times)
                    plt.title('Temps de réponse moyen des endpoints Solana')
                    plt.xlabel('Endpoint')
                    plt.ylabel('Temps (ms)')
                    plt.xticks(rotation=45, ha='right')
                    plt.tight_layout()
                    plt.savefig(os.path.join(charts_dir, 'solana_endpoint_response_times.png'))
                    plt.close()
        
        # Exemple: Créer un tableau HTML des résultats DEX
        if "dex" in consolidated_results["benchmarks"] and \
           "solana" in consolidated_results["benchmarks"]["dex"]["solana"]:
            
            dex_data = consolidated_results["benchmarks"]["dex"]["solana"]
            
            if "comparison" in dex_data and "overall_ranking" in dex_data["comparison"]:
                # Créer un DataFrame pour le classement des DEX
                dex_ranking = []
                
                for dex_name, score in dex_data["comparison"]["overall_ranking"]:
                    dex_ranking.append({
                        "DEX": dex_name,
                        "Score global": score
                    })
                
                if dex_ranking:
                    df = pd.DataFrame(dex_ranking)
                    html_table = df.to_html(index=False)
                    
                    with open(os.path.join(output_dir, "dex_ranking.html"), 'w') as f:
                        f.write("<html><head><title>Classement des DEX Solana</title></head><body>")
                        f.write("<h1>Classement des DEX Solana</h1>")
                        f.write(html_table)
                        f.write("</body></html>")
        
        print(f"Graphiques et tableaux sauvegardés dans: {charts_dir}")
        
    except ImportError:
        print("matplotlib ou pandas non disponible, pas de génération de graphiques.")
    except Exception as e:
        print(f"Erreur lors de la génération des graphiques: {str(e)}")
    
    return output_file

async def main():
    parser = argparse.ArgumentParser(description='Exécute des benchmarks pour GBPBot')
    parser.add_argument('--all', action='store_true', help='Exécuter tous les benchmarks')
    parser.add_argument('--system', action='store_true', help='Exécuter le benchmark système')
    parser.add_argument('--blockchain', action='store_true', help='Exécuter le benchmark blockchain')
    parser.add_argument('--dex', action='store_true', help='Exécuter le benchmark DEX')
    parser.add_argument('--transaction', action='store_true', help='Exécuter le benchmark des transactions')
    parser.add_argument('--report', action='store_true', help='Générer uniquement le rapport')
    
    args = parser.parse_args()
    
    # Si aucun argument n'est fourni, exécuter tous les benchmarks
    if not any(vars(args).values()):
        args.all = True
    
    # Vérifier et installer les dépendances
    if not args.report:
        if not check_and_install_dependencies():
            return
    
    # Déterminer les benchmarks à exécuter
    benchmarks_to_run = []
    
    if args.all:
        benchmarks_to_run = list(benchmark_modules.keys())
    else:
        if args.system:
            benchmarks_to_run.append("system")
        if args.blockchain:
            benchmarks_to_run.append("blockchain")
        if args.dex:
            benchmarks_to_run.append("dex")
        if args.transaction:
            benchmarks_to_run.append("transaction")
    
    # Exécuter les benchmarks sélectionnés
    if benchmarks_to_run and not args.report:
        print(f"Benchmarks à exécuter: {', '.join(benchmarks_to_run)}")
        
        for benchmark_type in benchmarks_to_run:
            success = await run_benchmark(benchmark_type)
            if not success:
                print(f"Le benchmark {benchmark_type} a échoué.")
    
    # Générer le rapport
    if args.report or args.all or len(benchmarks_to_run) > 0:
        report_path = generate_report()
        print(f"\nRapport final disponible à: {report_path}")
        print("Benchmarking terminé!")

if __name__ == "__main__":
    asyncio.run(main()) 