#!/usr/bin/env python3
"""
Script de test pour simuler un volume élevé de transactions
"""
import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime
import random
from loguru import logger
from dotenv import load_dotenv

# Ajouter le répertoire parent au path pour pouvoir importer les modules
sys.path.append(str(Path(__file__).parent.parent.parent))

from gbpbot.core.blockchain import BlockchainClient
from gbpbot.strategies.arbitrage import ArbitrageStrategy
from gbpbot.core.mev_executor import MEVExecutor
from gbpbot.core.stealth_mode import StealthMode

# Configuration du logger
logger.remove()
logger.add(
    sys.stdout,
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
)
logger.add("high_volume_test.log", rotation="100 MB")

class HighVolumeTest:
    """Test de volume élevé pour le bot"""
    
    def __init__(self):
        # Charger la configuration
        load_dotenv(".env")
        
        # Initialiser les composants
        self.blockchain = BlockchainClient(simulation_mode=True, is_testnet=True)
        self.arbitrage = ArbitrageStrategy(self.blockchain)
        self.mev_executor = MEVExecutor(self.blockchain.web3.provider.endpoint_uri)
        self.stealth_mode = StealthMode()
        
        # Configuration du test
        self.test_config = {
            "num_concurrent_trades": 10,
            "total_trades": 100,
            "trade_interval_min": 1,  # secondes
            "trade_interval_max": 5,  # secondes
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
            "amount_range": (0.1, 2.0)  # AVAX
        }
        
    async def run_test(self):
        """Exécute le test de volume élevé"""
        logger.info(f"🚀 Démarrage du test de volume élevé avec {self.test_config['num_concurrent_trades']} trades concurrents")
        
        # Vérifier la connexion
        if not self.blockchain.is_connected():
            logger.error("Impossible de se connecter à Avalanche")
            return
            
        # Statistiques du test
        start_time = datetime.now()
        successful_trades = 0
        failed_trades = 0
        
        # Créer les tâches de trading
        tasks = []
        for i in range(self.test_config["total_trades"]):
            # Ajouter un délai aléatoire
            await asyncio.sleep(random.uniform(
                self.test_config["trade_interval_min"],
                self.test_config["trade_interval_max"]
            ))
            
            # Limiter le nombre de trades concurrents
            while len(tasks) >= self.test_config["num_concurrent_trades"]:
                # Attendre qu'une tâche se termine
                done, pending = await asyncio.wait(
                    tasks, 
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                # Traiter les résultats
                for task in done:
                    result = task.result()
                    if result:
                        successful_trades += 1
                    else:
                        failed_trades += 1
                
                # Mettre à jour la liste des tâches
                tasks = list(pending)
            
            # Créer une nouvelle tâche de trading
            task = asyncio.create_task(self._execute_trade())
            tasks.append(task)
            
            logger.info(f"Trade #{i+1} lancé. En cours: {len(tasks)}, Réussis: {successful_trades}, Échoués: {failed_trades}")
        
        # Attendre que toutes les tâches restantes se terminent
        if tasks:
            results = await asyncio.gather(*tasks)
            successful_trades += sum(1 for r in results if r)
            failed_trades += sum(1 for r in results if not r)
        
        # Afficher les résultats
        duration = (datetime.now() - start_time).total_seconds()
        logger.info(f"✅ Test terminé en {duration:.2f} secondes")
        logger.info(f"Trades réussis: {successful_trades}/{self.test_config['total_trades']} ({successful_trades/self.test_config['total_trades']*100:.2f}%)")
        logger.info(f"Trades échoués: {failed_trades}/{self.test_config['total_trades']} ({failed_trades/self.test_config['total_trades']*100:.2f}%)")
        logger.info(f"Trades par seconde: {self.test_config['total_trades']/duration:.2f}")
        
    async def _execute_trade(self) -> bool:
        """Exécute un trade aléatoire"""
        try:
            # Sélectionner une paire aléatoire
            pair = random.choice(self.test_config["token_pairs"])
            
            # Montant aléatoire
            amount = random.uniform(*self.test_config["amount_range"])
            amount_wei = self.blockchain.web3.to_wei(amount, "ether")
            
            # Ajouter un délai aléatoire (mode furtif)
            await self.stealth_mode.add_transaction_delay()
            
            # Analyser la paire
            opportunity = await self.arbitrage.analyze_pair(
                pair["token_in"],
                pair["token_out"],
                amount_wei,
                pair["symbol"]
            )
            
            if not opportunity:
                logger.warning(f"Pas d'opportunité trouvée pour {pair['symbol']}")
                return False
                
            # Exécuter le trade
            success = await self.arbitrage.execute_trade(opportunity)
            
            return success
            
        except Exception as e:
            logger.error(f"Erreur lors de l'exécution du trade: {str(e)}")
            return False

async def main():
    """Fonction principale"""
    test = HighVolumeTest()
    await test.run_test()

if __name__ == "__main__":
    asyncio.run(main()) 