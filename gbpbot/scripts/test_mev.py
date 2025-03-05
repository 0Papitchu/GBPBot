#!/usr/bin/env python3
"""
Script de test pour l'optimisation du MEV et du frontrunning
"""
import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime
import random
import json
from loguru import logger
from dotenv import load_dotenv
import pandas as pd
import matplotlib.pyplot as plt
from web3 import Web3

# Ajouter le répertoire parent au path pour pouvoir importer les modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from gbpbot.core.blockchain import BlockchainClient
from gbpbot.core.mev_executor import MEVExecutor, MempoolScanner
from gbpbot.core.stealth_mode import StealthMode

# Configuration du logger
logger.remove()
logger.add(
    sys.stdout,
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)
logger.add("mev_test.log", rotation="100 MB")

class MEVTest:
    """Test d'optimisation du MEV et du frontrunning"""
    
    def __init__(self):
        # Charger la configuration
        load_dotenv(".env")
        
        # Initialiser les composants
        self.blockchain = BlockchainClient(simulation_mode=True, is_testnet=True)
        self.mev_executor = MEVExecutor(self.blockchain.web3.provider.endpoint_uri)
        self.mempool_scanner = MempoolScanner()
        self.stealth_mode = StealthMode()
        
        # Configuration du test
        self.test_config = {
            "scan_duration": 300,  # secondes
            "gas_price_strategies": [
                {"name": "standard", "multiplier": 1.0},
                {"name": "aggressive", "multiplier": 1.2},
                {"name": "very_aggressive", "multiplier": 1.5}
            ],
            "target_transactions": [
                # Simuler des transactions cibles pour le frontrunning
                {
                    "to": "0x60aE616a2155Ee3d9A68541Ba4544862310933d4",  # TraderJoe Router
                    "value": Web3.to_wei(0.1, "ether"),
                    "gasPrice": Web3.to_wei(30, "gwei"),
                    "data": "0x..."  # Données de swap
                },
                {
                    "to": "0xE54Ca86531e17Ef3616d22Ca28b0D458b6C89106",  # Pangolin Router
                    "value": Web3.to_wei(0.2, "ether"),
                    "gasPrice": Web3.to_wei(25, "gwei"),
                    "data": "0x..."  # Données de swap
                }
            ],
            "simulation_iterations": 50
        }
        
        # Métriques de performance
        self.mev_metrics = {
            "scan_results": [],
            "frontrun_attempts": [],
            "success_rate": {},
            "profit_by_strategy": {},
            "gas_costs": {},
            "execution_times": {}
        }
        
    async def run_test(self):
        """Exécute le test d'optimisation MEV"""
        logger.info(f"🚀 Démarrage du test MEV pour {self.test_config['scan_duration']} secondes")
        
        # Vérifier la connexion
        if not self.blockchain.is_connected():
            logger.error("Impossible de se connecter à Avalanche")
            return
            
        # Statistiques du test
        start_time = datetime.now()
        
        # Simuler le scan du mempool
        await self._simulate_mempool_scanning()
        
        # Tester différentes stratégies de gas price
        for strategy in self.test_config["gas_price_strategies"]:
            logger.info(f"Test de la stratégie de gas price: {strategy['name']} (multiplicateur: {strategy['multiplier']})")
            
            # Initialiser les métriques pour cette stratégie
            self.mev_metrics["success_rate"][strategy["name"]] = 0
            self.mev_metrics["profit_by_strategy"][strategy["name"]] = 0
            self.mev_metrics["gas_costs"][strategy["name"]] = 0
            self.mev_metrics["execution_times"][strategy["name"]] = []
            
            # Exécuter plusieurs itérations
            for i in range(self.test_config["simulation_iterations"]):
                # Sélectionner une transaction cible aléatoire
                target_tx = random.choice(self.test_config["target_transactions"])
                
                # Ajuster le gas price selon la stratégie
                adjusted_gas_price = int(int(target_tx["gasPrice"]) * strategy["multiplier"])
                target_tx_copy = target_tx.copy()
                target_tx_copy["gasPrice"] = adjusted_gas_price
                
                # Mesurer le temps d'exécution
                start_exec = datetime.now()
                
                # Analyser le potentiel de profit
                profit_analysis = await self.mev_executor._analyze_profit_potential(target_tx_copy)
                
                if profit_analysis:
                    # Préparer le bundle
                    bundle = await self.mev_executor._prepare_bundle(
                        target_tx_copy,
                        gas_price=adjusted_gas_price,
                        expected_profit=profit_analysis["expected_profit"]
                    )
                    
                    # Simuler l'exécution (en mode test)
                    success = random.random() > (1 - (1 / strategy["multiplier"]))  # Plus le multiplicateur est élevé, plus la chance de succès est grande
                    
                    # Calculer le profit simulé
                    profit = profit_analysis["expected_profit"] if success else 0
                    gas_cost = self.mev_executor._estimate_gas_cost(target_tx_copy)
                    
                    # Enregistrer les résultats
                    execution_time = (datetime.now() - start_exec).total_seconds()
                    self.mev_metrics["execution_times"][strategy["name"]].append(execution_time)
                    
                    if success:
                        self.mev_metrics["success_rate"][strategy["name"]] += 1
                        self.mev_metrics["profit_by_strategy"][strategy["name"]] += profit
                    
                    self.mev_metrics["gas_costs"][strategy["name"]] += gas_cost
                    
                    # Enregistrer la tentative
                    self.mev_metrics["frontrun_attempts"].append({
                        "strategy": strategy["name"],
                        "gas_multiplier": strategy["multiplier"],
                        "target_gas": int(target_tx["gasPrice"]),
                        "adjusted_gas": adjusted_gas_price,
                        "success": success,
                        "profit": profit,
                        "gas_cost": gas_cost,
                        "execution_time": execution_time,
                        "timestamp": datetime.now().isoformat()
                    })
                    
                    logger.info(f"Tentative #{i+1} avec {strategy['name']}: {'✅ Succès' if success else '❌ Échec'}, Profit: {profit:.6f} AVAX, Gas: {gas_cost:.6f} AVAX")
                else:
                    logger.warning(f"Pas de potentiel de profit pour la transaction avec stratégie {strategy['name']}")
            
            # Calculer les statistiques pour cette stratégie
            iterations = self.test_config["simulation_iterations"]
            success_rate = (self.mev_metrics["success_rate"][strategy["name"]] / iterations) * 100
            total_profit = self.mev_metrics["profit_by_strategy"][strategy["name"]]
            total_gas = self.mev_metrics["gas_costs"][strategy["name"]]
            net_profit = total_profit - total_gas
            avg_execution_time = sum(self.mev_metrics["execution_times"][strategy["name"]]) / len(self.mev_metrics["execution_times"][strategy["name"]])
            
            logger.info(f"Résultats pour {strategy['name']}:")
            logger.info(f"  Taux de succès: {success_rate:.2f}%")
            logger.info(f"  Profit total: {total_profit:.6f} AVAX")
            logger.info(f"  Coût gas total: {total_gas:.6f} AVAX")
            logger.info(f"  Profit net: {net_profit:.6f} AVAX")
            logger.info(f"  Temps d'exécution moyen: {avg_execution_time*1000:.2f} ms")
        
        # Analyser les résultats
        self._analyze_results()
        
        # Afficher les résultats
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"✅ Test terminé en {duration:.2f} secondes")
        
        # Sauvegarder les métriques
        self._save_metrics()
        
    async def _simulate_mempool_scanning(self):
        """Simule le scan du mempool"""
        logger.info("Simulation du scan du mempool...")
        
        # Simuler des résultats de scan
        for i in range(20):  # Simuler 20 scans
            # Simuler un délai entre les scans
            await asyncio.sleep(0.5)
            
            # Simuler des transactions trouvées
            num_transactions = random.randint(0, 5)
            transactions = []
            
            for j in range(num_transactions):
                tx = {
                    "hash": f"0x{random.getrandbits(256):064x}",
                    "to": random.choice([
                        "0x60aE616a2155Ee3d9A68541Ba4544862310933d4",  # TraderJoe
                        "0xE54Ca86531e17Ef3616d22Ca28b0D458b6C89106",  # Pangolin
                        "0x1111111254fb6c44bAC0beD2854e76F90643097d"   # 1inch
                    ]),
                    "value": Web3.to_wei(random.uniform(0.01, 1.0), "ether"),
                    "gasPrice": Web3.to_wei(random.randint(20, 50), "gwei"),
                    "profitable": random.random() > 0.7  # 30% de chance d'être profitable
                }
                transactions.append(tx)
            
            # Enregistrer les résultats
            self.mev_metrics["scan_results"].append({
                "timestamp": datetime.now().isoformat(),
                "num_transactions": num_transactions,
                "transactions": transactions,
                "profitable_opportunities": sum(1 for tx in transactions if tx["profitable"])
            })
            
            logger.info(f"Scan #{i+1}: {num_transactions} transactions trouvées, {sum(1 for tx in transactions if tx['profitable'])} opportunités profitables")
    
    def _analyze_results(self):
        """Analyse les résultats du test"""
        try:
            # Trouver la meilleure stratégie
            best_strategy = None
            best_profit = -float("inf")
            
            for strategy in self.test_config["gas_price_strategies"]:
                name = strategy["name"]
                total_profit = self.mev_metrics["profit_by_strategy"][name]
                total_gas = self.mev_metrics["gas_costs"][name]
                net_profit = total_profit - total_gas
                
                if net_profit > best_profit:
                    best_profit = net_profit
                    best_strategy = name
            
            if best_strategy:
                logger.info(f"Meilleure stratégie: {best_strategy} avec un profit net de {best_profit:.6f} AVAX")
                
                # Calculer le ROI
                total_gas = self.mev_metrics["gas_costs"][best_strategy]
                if total_gas > 0:
                    roi = (best_profit / total_gas) * 100
                    logger.info(f"ROI: {roi:.2f}%")
            
            # Analyser les temps d'exécution
            for strategy in self.test_config["gas_price_strategies"]:
                name = strategy["name"]
                times = self.mev_metrics["execution_times"][name]
                if times:
                    avg_time = sum(times) / len(times)
                    min_time = min(times)
                    max_time = max(times)
                    logger.info(f"Temps d'exécution pour {name}: Avg={avg_time*1000:.2f}ms, Min={min_time*1000:.2f}ms, Max={max_time*1000:.2f}ms")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse des résultats: {str(e)}")
    
    def _save_metrics(self):
        """Sauvegarde les métriques dans un fichier"""
        try:
            # Créer le répertoire de rapports s'il n'existe pas
            reports_dir = Path("reports")
            reports_dir.mkdir(exist_ok=True)
            
            # Sauvegarder les métriques brutes
            with open(reports_dir / "mev_metrics.json", "w") as f:
                json.dump(self.mev_metrics, f, indent=2)
            
            # Créer des visualisations
            self._create_visualizations(reports_dir)
            
            logger.info(f"Métriques sauvegardées dans {reports_dir}")
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des métriques: {str(e)}")
    
    def _create_visualizations(self, reports_dir: Path):
        """Crée des visualisations des métriques"""
        try:
            # Taux de succès par stratégie
            strategies = [s["name"] for s in self.test_config["gas_price_strategies"]]
            success_rates = [
                (self.mev_metrics["success_rate"][s] / self.test_config["simulation_iterations"]) * 100
                for s in strategies
            ]
            
            plt.figure(figsize=(10, 6))
            plt.bar(strategies, success_rates)
            plt.title("Taux de succès par stratégie")
            plt.xlabel("Stratégie")
            plt.ylabel("Taux de succès (%)")
            plt.savefig(reports_dir / "success_rates.png")
            plt.close()
            
            # Profit net par stratégie
            net_profits = [
                self.mev_metrics["profit_by_strategy"][s] - self.mev_metrics["gas_costs"][s]
                for s in strategies
            ]
            
            plt.figure(figsize=(10, 6))
            plt.bar(strategies, net_profits)
            plt.title("Profit net par stratégie")
            plt.xlabel("Stratégie")
            plt.ylabel("Profit net (AVAX)")
            plt.savefig(reports_dir / "net_profits.png")
            plt.close()
            
            # Temps d'exécution par stratégie
            avg_times = [
                sum(self.mev_metrics["execution_times"][s]) / len(self.mev_metrics["execution_times"][s]) * 1000
                for s in strategies
            ]
            
            plt.figure(figsize=(10, 6))
            plt.bar(strategies, avg_times)
            plt.title("Temps d'exécution moyen par stratégie")
            plt.xlabel("Stratégie")
            plt.ylabel("Temps (ms)")
            plt.savefig(reports_dir / "execution_times.png")
            plt.close()
            
        except Exception as e:
            logger.error(f"Erreur lors de la création des visualisations: {str(e)}")

async def main():
    """Fonction principale"""
    test = MEVTest()
    await test.run_test()

if __name__ == "__main__":
    asyncio.run(main()) 