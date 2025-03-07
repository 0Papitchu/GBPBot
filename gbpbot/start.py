#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Module de démarrage principal pour GBPBot.

Ce module initialise les composants nécessaires et démarre GBPBot
avec une gestion correcte de la boucle d'événements asyncio.
"""

import os
import sys
import asyncio
import logging
import argparse
from pathlib import Path

# Configurer le logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join("logs", f"gbpbot.log"))
    ]
)

logger = logging.getLogger(__name__)

# Créer le répertoire logs s'il n'existe pas
os.makedirs("logs", exist_ok=True)

async def main():
    """
    Fonction principale asynchrone pour démarrer GBPBot.
    
    Cette fonction initialise et démarre tous les composants nécessaires
    dans le bon ordre et avec une gestion correcte des coroutines.
    """
    # Importer les modules après la configuration de logging
    from gbpbot.core.rpc.rpc_manager import rpc_manager
    from gbpbot.core.bot import GBPBot
    
    try:
        # Démarrer la tâche d'optimisation du gestionnaire RPC
        await rpc_manager.start_optimization_task()
        
        # Initialiser le bot
        logger.info("Initialisation de GBPBot...")
        bot = GBPBot()
        
        # Démarrer le bot
        logger.info("Démarrage de GBPBot...")
        await bot.start()
        
        # Maintenir le bot en exécution
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Arrêt demandé par l'utilisateur...")
    except Exception as e:
        logger.exception(f"Erreur lors de l'exécution de GBPBot: {e}")
    finally:
        # Nettoyage et fermeture propre
        logger.info("Nettoyage et fermeture...")
        if 'bot' in locals():
            await bot.stop()
        
        # Arrêter toutes les tâches asyncio en cours
        for task in asyncio.all_tasks():
            if task is not asyncio.current_task():
                task.cancel()
                
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.error(f"Erreur lors de l'annulation d'une tâche: {e}")
        
        logger.info("GBPBot arrêté.")

if __name__ == "__main__":
    # Analyser les arguments de ligne de commande
    parser = argparse.ArgumentParser(description="GBPBot - Trading Bot")
    parser.add_argument("--minimal", action="store_true", help="Démarrer en mode minimal (sniping uniquement)")
    parser.add_argument("--log-level", choices=["debug", "info", "warning", "error", "critical"],
                       default="info", help="Niveau de logging")
    args = parser.parse_args()
    
    # Configurer le niveau de logging
    log_level = getattr(logging, args.log_level.upper())
    logging.getLogger().setLevel(log_level)
    
    # Afficher l'en-tête
    print("=" * 60)
    print("                      GBPBot")
    print("=" * 60)
    
    # Exécuter la fonction principale avec asyncio.run()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nArrêt demandé par l'utilisateur.")
    except Exception as e:
        logger.exception(f"Erreur fatale: {e}")
        sys.exit(1) 