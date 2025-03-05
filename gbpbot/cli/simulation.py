#!/usr/bin/env python3
"""
Module d'interface en ligne de commande pour le mode simulation
"""

import os
import sys
import argparse
import json
from loguru import logger
from gbpbot.core.simulation import setup_simulation_mode, is_simulation_mode
from gbpbot.config.config_manager import config_manager

def setup_parser():
    """Configure le parseur d'arguments pour la simulation"""
    parser = argparse.ArgumentParser(description="Gestion du mode simulation pour GBPBot")
    
    # Commandes principales
    subparsers = parser.add_subparsers(dest="command", help="Commande à exécuter")
    
    # Commande status
    status_parser = subparsers.add_parser("status", help="Affiche l'état actuel du mode simulation")
    
    # Commande enable
    enable_parser = subparsers.add_parser("enable", help="Active le mode simulation")
    
    # Commande disable
    disable_parser = subparsers.add_parser("disable", help="Désactive le mode simulation")
    
    # Commande setup
    setup_parser = subparsers.add_parser("setup", help="Configure les paramètres de simulation")
    setup_parser.add_argument("--rpc", action="store_true", help="Configure les paramètres RPC simulés")
    setup_parser.add_argument("--price", action="store_true", help="Configure les prix simulés")
    setup_parser.add_argument("--wallet", action="store_true", help="Configure les portefeuilles simulés")
    
    return parser

def show_status():
    """Affiche l'état actuel du mode simulation"""
    sim_status = is_simulation_mode()
    
    print(f"Mode simulation: {'✅ Activé' if sim_status else '❌ Désactivé'}")
    
    # Afficher la configuration si le mode est activé
    if sim_status:
        sim_config = config_manager.get_config("simulation")
        
        print("\nConfiguration de simulation:")
        print(json.dumps(sim_config, indent=2))
        
        # Vérifier chaque composant
        rpc_config = {"active": False}
        price_config = {"active": False}
        wallet_config = {"active": False}
        
        try:
            from gbpbot.core.rpc.rpc_simulation import simulated_rpc_manager
            rpc_config["active"] = True
            rpc_config["providers"] = len(simulated_rpc_manager.providers)
        except ImportError:
            pass
        
        print("\nComposants activés:")
        print(f"- RPC simulé: {'✅' if rpc_config['active'] else '❌'}")
        print(f"- Prix simulés: {'✅' if price_config.get('active') else '❌'}")
        print(f"- Portefeuille simulé: {'✅' if wallet_config.get('active') else '❌'}")
    
    return 0

def enable_simulation():
    """Active le mode simulation"""
    setup_simulation_mode(True)
    print("✅ Mode simulation activé")
    
    # Sauvegarder la configuration
    config_manager.save_config()
    
    return 0

def disable_simulation():
    """Désactive le mode simulation"""
    setup_simulation_mode(False)
    print("❌ Mode simulation désactivé")
    
    # Sauvegarder la configuration
    config_manager.save_config()
    
    return 0

def setup_simulation(args):
    """Configure les paramètres de simulation"""
    if not is_simulation_mode():
        print("⚠️ Le mode simulation est désactivé. Activation automatique...")
        setup_simulation_mode(True)
    
    if args.rpc:
        setup_rpc_simulation()
    
    if args.price:
        setup_price_simulation()
    
    if args.wallet:
        setup_wallet_simulation()
    
    if not any([args.rpc, args.price, args.wallet]):
        print("❓ Veuillez spécifier au moins un composant à configurer (--rpc, --price, --wallet)")
        return 1
    
    # Sauvegarder la configuration
    config_manager.save_config()
    
    return 0

def setup_rpc_simulation():
    """Configure les paramètres RPC simulés"""
    print("Configuration des paramètres RPC simulés...")
    
    # S'assurer que la section simulation existe
    config = config_manager.get_config()
    if "simulation" not in config:
        config["simulation"] = {}
    
    if "rpc" not in config["simulation"]:
        config["simulation"]["rpc"] = {}
    
    # Configurer les paramètres RPC par défaut
    config["simulation"]["rpc"]["enabled"] = True
    config["simulation"]["rpc"]["latency_ms"] = 50
    config["simulation"]["rpc"]["error_rate"] = 0.01
    
    print("✅ Configuration RPC simulée activée")
    
    return 0

def setup_price_simulation():
    """Configure les prix simulés"""
    print("Configuration des prix simulés...")
    
    # S'assurer que la section simulation existe
    config = config_manager.get_config()
    if "simulation" not in config:
        config["simulation"] = {}
    
    if "price" not in config["simulation"]:
        config["simulation"]["price"] = {}
    
    # Configurer les paramètres de prix par défaut
    config["simulation"]["price"]["enabled"] = True
    config["simulation"]["price"]["volatility"] = 0.005
    config["simulation"]["price"]["update_interval_sec"] = 10
    
    print("✅ Configuration des prix simulés activée")
    
    return 0

def setup_wallet_simulation():
    """Configure les portefeuilles simulés"""
    print("Configuration des portefeuilles simulés...")
    
    # S'assurer que la section simulation existe
    config = config_manager.get_config()
    if "simulation" not in config:
        config["simulation"] = {}
    
    if "wallet" not in config["simulation"]:
        config["simulation"]["wallet"] = {}
    
    # Configurer les paramètres de portefeuille par défaut
    config["simulation"]["wallet"]["enabled"] = True
    config["simulation"]["wallet"]["initial_balance"] = {
        "AVAX": 10.0,
        "USDC": 1000.0,
        "USDT": 1000.0,
        "WAVAX": 5.0,
        "WETH.e": 0.1,
        "BTC.b": 0.01,
        "JOE": 100.0,
        "PNG": 100.0
    }
    
    print("✅ Configuration du portefeuille simulé activée")
    
    # Initialiser le gestionnaire de portefeuille simulé
    try:
        # Importer ici pour éviter les imports circulaires
        from gbpbot.core.simulation.wallet_simulation import wallet_manager
        
        # Réinitialiser le portefeuille avec les nouveaux soldes
        for token, balance in config["simulation"]["wallet"]["initial_balance"].items():
            wallet_manager.update_balance(token, balance)
        
        print(f"✅ Soldes de portefeuille simulés initialisés pour {len(config['simulation']['wallet']['initial_balance'])} tokens")
    except ImportError:
        print("⚠️ Module de simulation de portefeuille non disponible")
    
    return 0

def main():
    """Point d'entrée principal pour la CLI de simulation"""
    parser = setup_parser()
    args = parser.parse_args()
    
    if args.command == "status":
        return show_status()
    elif args.command == "enable":
        return enable_simulation()
    elif args.command == "disable":
        return disable_simulation()
    elif args.command == "setup":
        return setup_simulation(args)
    else:
        parser.print_help()
        return 0

if __name__ == "__main__":
    sys.exit(main()) 