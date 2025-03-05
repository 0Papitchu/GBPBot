#!/usr/bin/env python3
"""
Script de test pour évaluer la furtivité du bot
"""
import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import random
import json
from loguru import logger
from dotenv import load_dotenv
import pandas as pd
import matplotlib.pyplot as plt

# Ajouter le répertoire parent au path pour pouvoir importer les modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from gbpbot.core.blockchain import BlockchainClient
from gbpbot.core.stealth_mode import StealthMode
from gbpbot.core.transaction_obfuscation import TransactionObfuscator
from gbpbot.strategies.arbitrage import ArbitrageStrategy

# Configuration du logger
logger.remove()
logger.add(
    sys.stdout,
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)
logger.add("stealth_test.log", rotation="100 MB")

class StealthTest:
    """Test de furtivité pour le bot"""
    
    def __init__(self):
        # Charger la configuration
        load_dotenv(".env")
        
        # Initialiser les composants
        self.blockchain = BlockchainClient(simulation_mode=True, is_testnet=True)
        self.stealth_mode = StealthMode()
        self.obfuscator = TransactionObfuscator(self.blockchain.web3)
        self.arbitrage = ArbitrageStrategy(self.blockchain)
        
        # Configuration du test
        self.test_config = {
            "num_trades": 50,
            "trade_interval_min": 30,  # secondes
            "trade_interval_max": 300,  # secondes
            "amount_variance": 0.2,  # 20% de variance
            "base_amount": 0.5,  # AVAX
            "token_pairs": [
                {
                    "token_in": self.blockchain.tokens["WAVAX"],
                    "token_out": self.blockchain.tokens["USDT"],
                    "symbol": "AVAX/USDT"
                },
                {
                    "token_in": self.blockchain.tokens["WAVAX"],
                    "token_out": self.blockchain.tokens["USDC"],
                    "symbol": "AVAX/USDC"
                }
            ],
            "wallet_rotation_interval": 10,  # Rotation tous les 10 trades
            "gas_price_variance": 0.15,  # 15% de variance
            "transaction_delay_enabled": True
        }
        
        # Métriques de furtivité
        self.stealth_metrics = {
            "transaction_times": [],
            "transaction_amounts": [],
            "gas_prices": [],
            "wallets_used": [],
            "transaction_patterns": []
        }
        
    async def run_test(self):
        """Exécute le test de furtivité"""
        logger.info(f"🕵️ Démarrage du test de furtivité avec {self.test_config['num_trades']} trades")
        
        # Vérifier la connexion
        if not self.blockchain.is_connected():
            logger.error("Impossible de se connecter à Avalanche")
            return
            
        # Statistiques du test
        start_time = datetime.now()
        
        # Exécuter les trades
        for i in range(self.test_config["num_trades"]):
            # Ajouter un délai aléatoire entre les trades
            delay = random.uniform(
                self.test_config["trade_interval_min"],
                self.test_config["trade_interval_max"]
            )
            logger.info(f"Attente de {delay:.2f} secondes avant le prochain trade")
            await asyncio.sleep(delay)
            
            # Rotation du wallet si nécessaire
            if i % self.test_config["wallet_rotation_interval"] == 0 and i > 0:
                logger.info("Rotation du wallet")
                wallet = await self.stealth_mode.get_active_wallet("avax")
                if wallet:
                    self.stealth_metrics["wallets_used"].append(wallet.address)
            
            # Exécuter le trade
            await self._execute_stealth_trade(i)
            
        # Analyser les résultats
        await self._analyze_stealth_metrics()
        
        # Afficher les résultats
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"✅ Test terminé en {duration:.2f} secondes")
        logger.info(f"Nombre de wallets utilisés: {len(set(self.stealth_metrics['wallets_used']))}")
        
        # Sauvegarder les métriques
        self._save_metrics()
        
    async def _execute_stealth_trade(self, trade_index: int):
        """Exécute un trade avec des techniques de furtivité"""
        try:
            # Sélectionner une paire aléatoire
            pair = random.choice(self.test_config["token_pairs"])
            
            # Montant avec variance
            base_amount = self.test_config["base_amount"]
            variance = random.uniform(
                -self.test_config["amount_variance"],
                self.test_config["amount_variance"]
            )
            amount = base_amount * (1 + variance)
            amount_wei = self.blockchain.web3.to_wei(amount, "ether")
            
            # Enregistrer le montant
            self.stealth_metrics["transaction_amounts"].append(amount)
            
            # Ajouter un délai aléatoire si activé
            if self.test_config["transaction_delay_enabled"]:
                await self.stealth_mode.add_transaction_delay()
            
            # Enregistrer l'heure de la transaction
            tx_time = datetime.now()
            self.stealth_metrics["transaction_times"].append(tx_time)
            
            # Gas price avec variance
            gas_price = self.blockchain.web3.eth.gas_price
            variance = random.uniform(
                -self.test_config["gas_price_variance"],
                self.test_config["gas_price_variance"]
            )
            adjusted_gas_price = int(gas_price * (1 + variance))
            
            # Enregistrer le gas price
            self.stealth_metrics["gas_prices"].append(adjusted_gas_price)
            
            # Obfusquer la transaction
            obfuscation_method = random.choice(["split", "route", "delay"])
            logger.info(f"Utilisation de la méthode d'obfuscation: {obfuscation_method}")
            
            # Enregistrer le pattern de transaction
            self.stealth_metrics["transaction_patterns"].append({
                "trade_index": trade_index,
                "pair": pair["symbol"],
                "amount": amount,
                "gas_price": adjusted_gas_price,
                "obfuscation": obfuscation_method,
                "timestamp": tx_time.isoformat()
            })
            
            # Simuler l'exécution du trade (en mode test)
            logger.info(f"Trade #{trade_index+1}: {amount:.4f} AVAX sur {pair['symbol']} avec gas {adjusted_gas_price}")
            
            # En mode réel, on exécuterait le trade ici
            # await self.arbitrage.execute_trade(...)
            
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de l'exécution du trade furtif: {str(e)}")
            return False
    
    async def _analyze_stealth_metrics(self):
        """Analyse les métriques de furtivité"""
        try:
            # Analyser les intervalles entre transactions
            if len(self.stealth_metrics["transaction_times"]) > 1:
                intervals = []
                for i in range(1, len(self.stealth_metrics["transaction_times"])):
                    interval = (self.stealth_metrics["transaction_times"][i] - 
                               self.stealth_metrics["transaction_times"][i-1]).total_seconds()
                    intervals.append(interval)
                
                avg_interval = sum(intervals) / len(intervals)
                std_interval = (sum((x - avg_interval) ** 2 for x in intervals) / len(intervals)) ** 0.5
                
                logger.info(f"Intervalle moyen entre transactions: {avg_interval:.2f}s (écart-type: {std_interval:.2f}s)")
                logger.info(f"Entropie des intervalles: {self._calculate_entropy(intervals):.4f}")
            
            # Analyser la distribution des montants
            amounts = self.stealth_metrics["transaction_amounts"]
            avg_amount = sum(amounts) / len(amounts)
            std_amount = (sum((x - avg_amount) ** 2 for x in amounts) / len(amounts)) ** 0.5
            
            logger.info(f"Montant moyen: {avg_amount:.4f} AVAX (écart-type: {std_amount:.4f} AVAX)")
            logger.info(f"Entropie des montants: {self._calculate_entropy(amounts):.4f}")
            
            # Analyser la distribution des gas prices
            gas_prices = self.stealth_metrics["gas_prices"]
            avg_gas = sum(gas_prices) / len(gas_prices)
            std_gas = (sum((x - avg_gas) ** 2 for x in gas_prices) / len(gas_prices)) ** 0.5
            
            logger.info(f"Gas price moyen: {avg_gas:.0f} (écart-type: {std_gas:.0f})")
            
            # Score de furtivité global (plus élevé = plus furtif)
            if len(intervals) > 0:
                interval_entropy = self._calculate_entropy(intervals)
                amount_entropy = self._calculate_entropy(amounts)
                gas_entropy = self._calculate_entropy(gas_prices)
                wallet_diversity = len(set(self.stealth_metrics["wallets_used"])) / max(1, len(self.stealth_metrics["wallets_used"]))
                
                stealth_score = (interval_entropy * 0.4 + 
                                amount_entropy * 0.3 + 
                                gas_entropy * 0.2 + 
                                wallet_diversity * 0.1) * 100
                
                logger.info(f"Score de furtivité global: {stealth_score:.2f}/100")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'analyse des métriques: {str(e)}")
    
    def _calculate_entropy(self, values):
        """Calcule l'entropie d'une liste de valeurs (mesure de randomness)"""
        if not values:
            return 0
            
        # Normaliser les valeurs
        min_val = min(values)
        max_val = max(values)
        if max_val == min_val:
            return 0
            
        normalized = [(x - min_val) / (max_val - min_val) for x in values]
        
        # Discrétiser en 10 bins
        bins = [0] * 10
        for val in normalized:
            bin_index = min(9, int(val * 10))
            bins[bin_index] += 1
        
        # Calculer l'entropie
        entropy = 0
        for count in bins:
            if count > 0:
                p = count / len(values)
                entropy -= p * (pd.np.log(p) / pd.np.log(10))
                
        # Normaliser l'entropie (0-1)
        return entropy / 1.0
    
    def _save_metrics(self):
        """Sauvegarde les métriques dans un fichier"""
        try:
            # Créer le répertoire de rapports s'il n'existe pas
            reports_dir = Path("reports")
            reports_dir.mkdir(exist_ok=True)
            
            # Sauvegarder les métriques brutes
            with open(reports_dir / "stealth_metrics.json", "w") as f:
                # Convertir les datetime en strings
                metrics_copy = self.stealth_metrics.copy()
                metrics_copy["transaction_times"] = [t.isoformat() for t in self.stealth_metrics["transaction_times"]]
                json.dump(metrics_copy, f, indent=2)
            
            # Créer des visualisations
            self._create_visualizations(reports_dir)
            
            logger.info(f"Métriques sauvegardées dans {reports_dir}")
            
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des métriques: {str(e)}")
    
    def _create_visualizations(self, reports_dir: Path):
        """Crée des visualisations des métriques"""
        try:
            # Intervalles entre transactions
            if len(self.stealth_metrics["transaction_times"]) > 1:
                intervals = []
                for i in range(1, len(self.stealth_metrics["transaction_times"])):
                    interval = (self.stealth_metrics["transaction_times"][i] - 
                               self.stealth_metrics["transaction_times"][i-1]).total_seconds()
                    intervals.append(interval)
                
                plt.figure(figsize=(10, 6))
                plt.plot(intervals)
                plt.title("Intervalles entre transactions")
                plt.xlabel("Numéro de transaction")
                plt.ylabel("Intervalle (secondes)")
                plt.savefig(reports_dir / "intervals.png")
                plt.close()
            
            # Distribution des montants
            plt.figure(figsize=(10, 6))
            plt.hist(self.stealth_metrics["transaction_amounts"], bins=20)
            plt.title("Distribution des montants")
            plt.xlabel("Montant (AVAX)")
            plt.ylabel("Fréquence")
            plt.savefig(reports_dir / "amounts.png")
            plt.close()
            
            # Distribution des gas prices
            plt.figure(figsize=(10, 6))
            plt.hist(self.stealth_metrics["gas_prices"], bins=20)
            plt.title("Distribution des gas prices")
            plt.xlabel("Gas price")
            plt.ylabel("Fréquence")
            plt.savefig(reports_dir / "gas_prices.png")
            plt.close()
            
        except Exception as e:
            logger.error(f"Erreur lors de la création des visualisations: {str(e)}")

async def main():
    """Fonction principale"""
    test = StealthTest()
    await test.run_test()

if __name__ == "__main__":
    asyncio.run(main()) 