#!/usr/bin/env python3
"""
GBPBot - Bot d'arbitrage avancé pour Avalanche et autres blockchains
"""

import argparse
import asyncio
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from loguru import logger

from gbpbot.core.blockchain_factory import BlockchainClientFactory
from gbpbot.core.exceptions import GBPBotBaseException
from gbpbot.core.mev_monitor import MEVMonitor


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None):
    """Configure le système de logging"""
    # Supprimer le handler par défaut
    logger.remove()
    
    # Ajouter un handler pour la console
    logger.add(
        sys.stderr,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=log_level,
        colorize=True,
    )
    
    # Ajouter un handler pour le fichier de log si spécifié
    if log_file:
        logger.add(
            log_file,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            level=log_level,
            rotation="10 MB",
            compression="zip",
        )
    
    # Configurer le logging standard pour les bibliothèques tierces
    logging.basicConfig(handlers=[InterceptHandler()], level=0, force=True)
    
    # Intercepter les logs des bibliothèques tierces
    for _log in ["asyncio", "web3", "urllib3", "eth", "solana"]:
        logging.getLogger(_log).handlers = [InterceptHandler()]
        logging.getLogger(_log).propagate = False


class InterceptHandler(logging.Handler):
    """Handler pour intercepter les logs standard et les rediriger vers loguru"""
    
    def emit(self, record):
        # Récupérer le message original
        logger_opt = logger.opt(depth=6, exception=record.exc_info)
        logger_opt.log(record.levelname, record.getMessage())


def load_config(config_path: str) -> Dict:
    """Charge la configuration depuis un fichier YAML"""
    try:
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        logger.error(f"Erreur lors du chargement de la configuration: {str(e)}")
        sys.exit(1)


async def run_arbitrage_bot(config: Dict, monitor_only: bool = False):
    """Exécute le bot d'arbitrage"""
    try:
        # Créer le client blockchain
        blockchain_client = BlockchainClientFactory.create_client(
            "avalanche", config.get("avalanche", {})
        )
        
        # Récupérer les tokens à surveiller
        tokens_config = config.get("tokens", {})
        base_tokens = [token["address"] for token in tokens_config.get("base_tokens", [])]
        target_tokens = [token["address"] for token in tokens_config.get("target_tokens", [])]
        
        # Récupérer la configuration d'arbitrage
        arbitrage_config = config.get("arbitrage", {})
        min_profit_percentage = arbitrage_config.get("min_profit_percentage", 0.5)
        max_slippage = arbitrage_config.get("max_slippage", 0.5)
        gas_boost = arbitrage_config.get("gas_boost", 1.2)
        
        # Créer le moniteur MEV si la protection est activée
        mev_protection = arbitrage_config.get("mev_protection", False)
        mev_monitor = None
        if mev_protection:
            mev_monitor = MEVMonitor(blockchain_client)
        
        logger.info("Démarrage du bot d'arbitrage GBPBot")
        logger.info(f"Tokens de base: {base_tokens}")
        logger.info(f"Tokens cibles: {target_tokens}")
        
        # Boucle principale
        while True:
            try:
                # Surveiller l'activité MEV si la protection est activée
                if mev_protection:
                    logger.info("Surveillance de l'activité MEV...")
                    all_tokens = base_tokens + target_tokens
                    mev_report = await blockchain_client.monitor_mev_for_tokens(
                        all_tokens, time_window_seconds=300
                    )
                    logger.info(f"Adresses suspectes détectées: {len(mev_report['suspicious_addresses'])}")
                
                # Si mode surveillance uniquement, passer à l'itération suivante
                if monitor_only:
                    logger.info("Mode surveillance uniquement, pas d'exécution d'arbitrage")
                    await asyncio.sleep(30)
                    continue
                
                # Rechercher des opportunités d'arbitrage pour chaque token de base
                for base_token in base_tokens:
                    logger.info(f"Recherche d'opportunités d'arbitrage pour {base_token}...")
                    
                    # Rechercher des opportunités
                    opportunities = await blockchain_client.find_arbitrage_opportunities(
                        base_token=base_token,
                        target_tokens=target_tokens,
                        min_profit_percentage=min_profit_percentage,
                        amount=None,  # Utiliser le montant par défaut
                        max_routes=5
                    )
                    
                    if not opportunities:
                        logger.info(f"Aucune opportunité d'arbitrage trouvée pour {base_token}")
                        continue
                    
                    logger.info(f"Opportunités trouvées: {len(opportunities)}")
                    
                    # Exécuter la meilleure opportunité
                    best_opportunity = opportunities[0]
                    logger.info(f"Meilleure opportunité: {best_opportunity['profit_percentage']:.2f}% de profit")
                    
                    # TODO: Implémenter l'exécution de l'arbitrage avec une clé privée réelle
                    # Pour l'instant, nous simulons l'exécution
                    logger.info(f"Simulation de l'exécution de l'arbitrage: {best_opportunity}")
                
                # Attendre avant la prochaine itération
                await asyncio.sleep(10)
                
            except GBPBotBaseException as e:
                logger.error(f"Erreur GBPBot: {str(e)}")
                await asyncio.sleep(5)
            except Exception as e:
                logger.exception(f"Erreur inattendue: {str(e)}")
                await asyncio.sleep(10)
    
    except KeyboardInterrupt:
        logger.info("Arrêt du bot demandé par l'utilisateur")
    except Exception as e:
        logger.exception(f"Erreur critique: {str(e)}")
        sys.exit(1)


def main():
    """Point d'entrée principal"""
    # Analyser les arguments de la ligne de commande
    parser = argparse.ArgumentParser(description="GBPBot - Bot d'arbitrage avancé")
    parser.add_argument(
        "--config", 
        type=str, 
        default="config.yaml", 
        help="Chemin vers le fichier de configuration"
    )
    parser.add_argument(
        "--log-level", 
        type=str, 
        default="INFO", 
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Niveau de log"
    )
    parser.add_argument(
        "--log-file", 
        type=str, 
        help="Fichier de log (optionnel)"
    )
    parser.add_argument(
        "--debug", 
        action="store_true", 
        help="Activer le mode debug"
    )
    parser.add_argument(
        "--monitor-only", 
        action="store_true", 
        help="Exécuter uniquement la surveillance sans exécuter d'arbitrages"
    )
    
    args = parser.parse_args()
    
    # Configurer le logging
    log_level = "DEBUG" if args.debug else args.log_level
    setup_logging(log_level=log_level, log_file=args.log_file)
    
    # Charger la configuration
    config_path = args.config
    if not os.path.exists(config_path):
        logger.error(f"Le fichier de configuration {config_path} n'existe pas")
        sys.exit(1)
    
    config = load_config(config_path)
    
    # Mettre à jour la configuration avec les arguments de la ligne de commande
    if args.debug:
        config["general"] = config.get("general", {})
        config["general"]["debug_mode"] = True
    
    # Exécuter le bot
    try:
        asyncio.run(run_arbitrage_bot(config, monitor_only=args.monitor_only))
    except KeyboardInterrupt:
        logger.info("Arrêt du bot")
    except Exception as e:
        logger.exception(f"Erreur critique: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main() 