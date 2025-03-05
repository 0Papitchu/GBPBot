#!/usr/bin/env python
"""
Point d'entrée pour exécuter le bot GBPBot dans un processus séparé.
Ce script est appelé par run_bot.py pour lancer le bot dans une fenêtre séparée.
"""

import os
import sys
import asyncio
import argparse
from dotenv import load_dotenv
from loguru import logger

def setup_logger():
    """Configure le logger pour afficher les messages dans la console"""
    logger.remove()  # Supprimer les handlers par défaut
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO"
    )
    logger.add(
        "logs/bot_{time}.log",
        rotation="500 MB",
        retention="10 days",
        compression="zip",
        level="DEBUG"
    )

def parse_arguments():
    """Parse les arguments de ligne de commande"""
    parser = argparse.ArgumentParser(description="GBPBot Runner")
    parser.add_argument("--simulation", type=str, default="true", help="Mode simulation (true/false)")
    parser.add_argument("--testnet", type=str, default="true", help="Utiliser le réseau de test (true/false)")
    parser.add_argument("--module", type=str, default="arbitrage", help="Module à exécuter (arbitrage, sniping, sandwich)")
    
    args = parser.parse_args()
    
    # Convertir les arguments string en booléens
    simulation_mode = args.simulation.lower() in ["true", "1", "yes", "y"]
    is_testnet = args.testnet.lower() in ["true", "1", "yes", "y"]
    
    # Afficher les paramètres reçus pour le débogage
    print(f"Arguments reçus: simulation={args.simulation}, testnet={args.testnet}, module={args.module}")
    print(f"Paramètres interprétés: simulation_mode={simulation_mode}, is_testnet={is_testnet}, module={args.module}")
    
    return simulation_mode, is_testnet, args.module

async def run_bot(simulation_mode, is_testnet, module):
    """Exécute le bot avec les paramètres spécifiés"""
    try:
        # Importer le bot
        from gbpbot.main import GBPBot
        
        # Afficher la configuration
        mode_str = "TEST" if is_testnet else ("SIMULATION" if simulation_mode else "RÉEL")
        logger.info(f"Démarrage du bot en mode {mode_str}")
        logger.info(f"Réseau: {'Testnet' if is_testnet else 'Mainnet'}")
        logger.info(f"Module: {module}")
        
        # Créer et démarrer le bot
        logger.info(f"Création de l'instance du bot avec simulation_mode={simulation_mode}, is_testnet={is_testnet}")
        bot = GBPBot(simulation_mode=simulation_mode, is_testnet=is_testnet)
        
        # Définir le solde initial si en mode simulation
        if simulation_mode:
            bot.blockchain.simulated_balances = {
                "WAVAX": float(os.getenv("INITIAL_WAVAX", "5.0")),
                "USDT": float(os.getenv("INITIAL_USDT", "0.0")),
                "USDC": float(os.getenv("INITIAL_USDC", "0.0")),
                "WETH": float(os.getenv("INITIAL_WETH", "0.0"))
            }
            logger.info("Soldes initiaux configurés:")
            for token, amount in bot.blockchain.simulated_balances.items():
                logger.info(f"- {token}: {amount}")
        
        # Lancer le bot
        logger.info(f"Bot initialisé avec succès")
        logger.info(f"Appuyez sur Ctrl+C pour arrêter le bot")
        
        await bot.start()
        
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution du bot: {e}")
        raise

def main():
    """Fonction principale"""
    # Configurer le logger
    setup_logger()
    
    # Charger les variables d'environnement
    load_dotenv()
    
    # Parser les arguments
    simulation_mode, is_testnet, module = parse_arguments()
    
    # Configuration de l'event loop pour Windows (résout le problème aiodns)
    if os.name == 'nt':  # Windows
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        logger.info("Event loop configuré pour Windows")
    
    try:
        # Exécuter le bot
        asyncio.run(run_bot(simulation_mode, is_testnet, module))
    except KeyboardInterrupt:
        logger.warning("Bot arrêté par l'utilisateur")
    except Exception as e:
        logger.error(f"Erreur inattendue: {e}")
    finally:
        logger.info("Bot arrêté")

if __name__ == "__main__":
    main() 