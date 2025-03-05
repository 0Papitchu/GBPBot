#!/usr/bin/env python3
"""
Point d'entrée principal pour l'interface en ligne de commande de GBPBot
"""

import os
import sys
import argparse
from loguru import logger
from gbpbot.cli.simulation import setup_parser as setup_simulation_parser

def setup_parser():
    """Configure le parseur d'arguments principal"""
    parser = argparse.ArgumentParser(description="Interface en ligne de commande pour GBPBot")
    
    # Commandes principales
    subparsers = parser.add_subparsers(dest="command", help="Commande à exécuter")
    
    # Commande run
    run_parser = subparsers.add_parser("run", help="Exécuter le bot")
    run_parser.add_argument("--config", "-c", help="Chemin vers le fichier de configuration")
    run_parser.add_argument("--simulation", "-s", action="store_true", help="Exécuter en mode simulation")
    run_parser.add_argument("--debug", "-d", action="store_true", help="Activer le mode debug")
    
    # Commande simulation (sous-parseur)
    simulation_parser = subparsers.add_parser("simulation", help="Gérer le mode simulation")
    simulation_subparsers = simulation_parser.add_subparsers(dest="simulation_command")
    
    # Ajouter les sous-commandes de simulation
    sim_parser = setup_simulation_parser()
    for action in sim_parser._subparsers._actions:
        if isinstance(action, argparse._SubParsersAction):
            for choice, subparser in action.choices.items():
                simulation_subparsers.add_parser(choice, help=subparser.description)
    
    # Commande version
    version_parser = subparsers.add_parser("version", help="Afficher la version")
    
    return parser

def handle_simulation_command(args):
    """Gère les commandes de simulation en les transmettant au module de simulation"""
    from gbpbot.cli.simulation import main as simulation_main
    
    # Recréer les arguments pour le module de simulation
    simulation_args = argparse.Namespace()
    simulation_args.command = args.simulation_command
    
    # Copier les autres arguments si nécessaire
    if hasattr(args, "rpc"):
        simulation_args.rpc = args.rpc
    if hasattr(args, "price"):
        simulation_args.price = args.price
    if hasattr(args, "wallet"):
        simulation_args.wallet = args.wallet
    
    # Exécuter la commande de simulation
    return simulation_main(simulation_args)

def run_bot(args):
    """Exécute le bot"""
    # Configurer le mode simulation si spécifié
    if args.simulation:
        from gbpbot.core.simulation import setup_simulation_mode, init_simulation_modules
        setup_simulation_mode(True)
        logger.info("Mode simulation activé pour l'exécution")
        
        # Initialiser les modules de simulation
        init_simulation_modules()
    
    # Charger la configuration si spécifiée
    if args.config:
        from gbpbot.config.config_manager import config_manager
        config_manager.load_config_file(args.config)
    
    # Configurer le niveau de log
    if args.debug:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")
    
    # TODO: Ajouter le code pour exécuter le bot
    logger.info("Exécution du bot...")
    
    return 0

def show_version():
    """Affiche la version du bot"""
    from gbpbot import __version__
    print(f"GBPBot version {__version__}")
    return 0

def main():
    """Point d'entrée principal pour la CLI"""
    parser = setup_parser()
    args = parser.parse_args()
    
    if args.command == "run":
        return run_bot(args)
    elif args.command == "simulation":
        return handle_simulation_command(args)
    elif args.command == "version":
        return show_version()
    else:
        parser.print_help()
        return 0

if __name__ == "__main__":
    sys.exit(main()) 