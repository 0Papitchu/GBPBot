#!/usr/bin/env python3
"""
Interface en ligne de commande (CLI) pour GBPBot
===============================================

Ce module fournit une interface en ligne de commande pour interagir avec GBPBot.
"""

import os
import sys
import cmd
import argparse
import logging
import time
import json
from typing import Dict, Any, List, Optional, Tuple, Union, cast

# Configurer le logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("gbpbot.cli")

# Importer les modules GBPBot de manière sécurisée
try:
    from gbpbot.core import config
    from gbpbot import resource_monitor
except ImportError as e:
    logger.error(f"Erreur lors de l'importation des modules GBPBot: {str(e)}")
    logger.error("Assurez-vous que GBPBot est correctement installé")
    sys.exit(1)


class GBPBotCLI(cmd.Cmd):
    """Interface en ligne de commande interactive pour GBPBot"""
    
    intro = r"""
 _____  ____  _____  ____            
/ ____||  _ \|  __ \|  _ \           
| |  __ | |_) | |__) | |_) | ___  ___ 
| | |_ ||  _ <|  ___/|  _ < / _ \/ __|
| |__| || |_) | |    | |_) | (_) \__ \
 \_____||____/|_|    |____/ \___/|___/
                                      
Bot de Trading Optimisé pour PC Local - v0.1.0
Tapez 'help' ou '?' pour afficher la liste des commandes.
Tapez 'quit' ou 'exit' pour quitter.
"""
    prompt = "gbpbot> "
    
    def __init__(self):
        """Initialisation de l'interface CLI"""
        super().__init__()
        
        # Charger la configuration
        self.config = {}
        try:
            # Vérifier si config possède la méthode load_config
            if hasattr(config, 'load_config'):
                self.config = config.load_config()
            elif hasattr(config, 'config_manager'):
                self.config = config.config_manager
            else:
                logger.warning("Module config incomplet, utilisation d'une configuration par défaut")
        except Exception as e:
            logger.warning(f"Impossible de charger la configuration: {str(e)}")
        
        # Définir les stratégies disponibles
        self.available_strategies = [
            "arbitrage",
            "sniping",
            "scalping",
            "mev"
        ]
        
        # Initialiser les stratégies actives
        self.active_strategies = {}
        
        # Initialiser l'état du moniteur de ressources
        self.resource_monitor_active = False
        
    def emptyline(self) -> bool:
        """Ne rien faire quand l'utilisateur appuie sur Entrée sans rien saisir"""
        return False
        
    def do_exit(self, arg):
        """Quitter l'application"""
        print("Arrêt des services en cours...")
        self._stop_all_services()
        print("Au revoir!")
        return True
    
    def do_quit(self, arg):
        """Quitter l'application (alias de exit)"""
        return self.do_exit(arg)
    
    def do_EOF(self, arg):
        """Quitter l'application (Ctrl+D)"""
        print()  # Ajouter une ligne vide
        return self.do_exit(arg)
    
    def do_status(self, arg):
        """Afficher l'état actuel du système"""
        print("\nÉtat du système:")
        print("----------------")
        
        # Afficher l'état des ressources
        print("\nUtilisation des ressources:")
        try:
            if hasattr(resource_monitor, 'get_current_state'):
                state = resource_monitor.get_current_state()
                
                # Récupérer les seuils de manière sécurisée
                cpu_threshold = 80  # Valeur par défaut
                memory_threshold = 80  # Valeur par défaut
                disk_threshold = 80  # Valeur par défaut
                
                # Différentes méthodes possibles pour obtenir les seuils
                if hasattr(resource_monitor, 'get_thresholds'):
                    thresholds = resource_monitor.get_thresholds()
                    cpu_threshold = thresholds.get('cpu', 80)
                    memory_threshold = thresholds.get('memory', 80)
                    disk_threshold = thresholds.get('disk', 80)
                elif hasattr(resource_monitor, 'resource_monitor') and hasattr(resource_monitor.resource_monitor, 'cpu_threshold'):
                    # Ancienne structure
                    cpu_threshold = resource_monitor.resource_monitor.cpu_threshold
                    memory_threshold = resource_monitor.resource_monitor.memory_threshold
                    disk_threshold = resource_monitor.resource_monitor.disk_threshold
                
                print(f"CPU: {state['cpu_usage']:.1f}% (seuil: {cpu_threshold}%)")
                print(f"Mémoire: {state['memory_usage']:.1f}% (seuil: {memory_threshold}%)")
                print(f"Disque: {state['disk_usage']:.1f}% (seuil: {disk_threshold}%)")
            else:
                print("Informations sur les ressources non disponibles")
        except Exception as e:
            print(f"Erreur lors de la récupération des ressources: {str(e)}")
            
        # Afficher les stratégies actives
        if self.active_strategies:
            print("\nStratégies actives:")
            for name, info in self.active_strategies.items():
                status = info.get("status", "inconnu")
                start_time = info.get("start_time", 0)
                duration = self._format_duration(time.time() - start_time)
                print(f"- {name}: {status} (en cours depuis {duration})")
        else:
            print("\nAucune stratégie active")
        
        # Afficher les connexions blockchain
        print("\nConnexions blockchain:")
        # TODO: Implémenter la vérification des connexions blockchain
        print("- Solana: Non connecté")
        print("- Avalanche: Non connecté")
        print("- Ethereum: Non connecté")
        
        print("\n")
        return False
        
    def do_start(self, arg):
        """
        Démarrer une stratégie ou un service
        
        Usage:
          start resource_monitor - Démarrer le moniteur de ressources
          start sniping <token_address> [--amount=<amount>] [--slippage=<slippage>] - Démarrer le sniping
          start arbitrage [--threshold=<threshold>] [--max-pairs=<max_pairs>] - Démarrer l'arbitrage
          start monitor [--min-liquidity=<min_liquidity>] - Démarrer le monitoring des nouveaux tokens
        """
        args = arg.split()
        if not args:
            print("Erreur: Aucun service ou stratégie spécifié")
            print("Utilisez 'help start' pour plus d'informations")
            return
            
        service = args[0].lower()
        
        if service == "resource_monitor":
            if not self.resource_monitor_active:
                resource_monitor.start()
                self.resource_monitor_active = True
                logger.info("Moniteur de ressources démarré")
            else:
                logger.warning("Le moniteur de ressources est déjà actif")
                
        elif service in self.available_strategies:
            # Traiter les arguments
            parser = argparse.ArgumentParser(prog=f"start {service}")
            
            if service == "sniping":
                parser.add_argument("token_address", help="Adresse du token à sniper")
                parser.add_argument("--amount", type=float, default=0.1, help="Montant à investir")
                parser.add_argument("--slippage", type=float, default=10, help="Slippage maximum en pourcentage")
                
            elif service == "arbitrage":
                parser.add_argument("--threshold", type=float, default=1.5, help="Seuil de profit en pourcentage")
                parser.add_argument("--max-pairs", type=int, default=10, help="Nombre maximum de paires à surveiller")
                
            elif service == "monitor":
                parser.add_argument("--min-liquidity", type=float, default=5, help="Liquidité minimale en SOL")
                
            # Analyser les arguments
            try:
                # Ignorer le premier argument (nom du service)
                service_args = parser.parse_args(args[1:])
                service_args_dict = vars(service_args)
                
                # Vérifier si la stratégie est déjà active
                if service in self.active_strategies:
                    logger.warning(f"La stratégie {service} est déjà active")
                    return
                    
                # Démarrer la stratégie
                logger.info(f"Démarrage de la stratégie {service} avec arguments: {service_args_dict}")
                
                # Ici, nous simulons le démarrage de la stratégie
                # Dans une implémentation réelle, nous lancerions la stratégie
                self.active_strategies[service] = {
                    "status": "actif",
                    "start_time": time.time(),
                    "args": service_args_dict
                }
                
                # Afficher un message spécifique à la stratégie
                if service == "sniping":
                    logger.info(f"Sniping démarré pour le token {service_args.token_address}")
                    logger.info(f"Montant: {service_args.amount} SOL, Slippage: {service_args.slippage}%")
                    
                elif service == "arbitrage":
                    logger.info(f"Arbitrage démarré avec seuil de profit: {service_args.threshold}%")
                    logger.info(f"Surveillance de {service_args.max_pairs} paires maximum")
                    
                elif service == "monitor":
                    logger.info(f"Monitoring démarré avec liquidité minimale: {service_args.min_liquidity} SOL")
                    
            except SystemExit:
                # Gérer l'erreur d'analyse des arguments
                pass
        else:
            logger.error(f"Service ou stratégie inconnu: {service}")
            print("Services disponibles: resource_monitor")
            print(f"Stratégies disponibles: {', '.join(self.available_strategies)}")
            
    def do_stop(self, arg):
        """
        Arrêter une stratégie ou un service
        
        Usage:
          stop resource_monitor - Arrêter le moniteur de ressources
          stop sniping - Arrêter le sniping
          stop arbitrage - Arrêter l'arbitrage
          stop monitor - Arrêter le monitoring des nouveaux tokens
          stop all - Arrêter tous les services et stratégies
        """
        args = arg.split()
        if not args:
            print("Erreur: Aucun service ou stratégie spécifié")
            print("Utilisez 'help stop' pour plus d'informations")
            return
            
        service = args[0].lower()
        
        if service == "all":
            self._stop_all_services()
            logger.info("Tous les services et stratégies ont été arrêtés")
            return
            
        if service == "resource_monitor":
            if self.resource_monitor_active:
                resource_monitor.stop()
                self.resource_monitor_active = False
                logger.info("Moniteur de ressources arrêté")
            else:
                logger.warning("Le moniteur de ressources n'est pas actif")
                
        elif service in self.active_strategies:
            # Simuler l'arrêt de la stratégie
            logger.info(f"Arrêt de la stratégie {service}")
            del self.active_strategies[service]
            
        else:
            logger.error(f"Service ou stratégie inconnu ou inactif: {service}")
            
    def do_config(self, arg):
        """
        Afficher ou modifier la configuration
        
        Usage:
          config show - Afficher la configuration actuelle
          config set <key> <value> - Définir une valeur de configuration
          config save - Sauvegarder la configuration
          config reload - Recharger la configuration depuis le fichier
        """
        args = arg.split()
        if not args:
            print("Erreur: Aucune action spécifiée")
            print("Utilisez 'help config' pour plus d'informations")
            return
            
        action = args[0].lower()
        
        if action == "show":
            print("\n=== Configuration ===")
            print(json.dumps(self.config, indent=2))
            
        elif action == "set" and len(args) >= 3:
            key = args[1]
            value = " ".join(args[2:])
            
            # Essayer de convertir la valeur en type approprié
            try:
                if value.lower() == "true":
                    value = True
                elif value.lower() == "false":
                    value = False
                elif value.isdigit():
                    value = int(value)
                elif value.replace(".", "", 1).isdigit():
                    value = float(value)
            except Exception:
                pass
                
            self.config[key] = value
            logger.info(f"Configuration mise à jour: {key} = {value}")
            
        elif action == "save":
            success = self.config.save_config()
            if success:
                logger.info("Configuration sauvegardée avec succès")
            else:
                logger.error("Erreur lors de la sauvegarde de la configuration")
                
        elif action == "reload":
            success = self.config.load_config()
            if success:
                logger.info("Configuration rechargée avec succès")
            else:
                logger.error("Erreur lors du rechargement de la configuration")
                
        else:
            print("Erreur: Action ou paramètres invalides")
            print("Utilisez 'help config' pour plus d'informations")
            
    def do_benchmark(self, arg):
        """
        Exécuter les benchmarks pour optimiser GBPBot
        
        Usage:
          benchmark all - Exécuter tous les benchmarks
          benchmark system - Exécuter le benchmark système
          benchmark blockchain - Exécuter le benchmark blockchain
          benchmark dex - Exécuter le benchmark des DEX
          benchmark transaction - Exécuter le benchmark des transactions
        """
        args = arg.split()
        if not args:
            print("Erreur: Aucun type de benchmark spécifié")
            print("Utilisez 'help benchmark' pour plus d'informations")
            return
            
        benchmark_type = args[0].lower()
        
        try:
            # Importer le module de benchmark
            from gbpbot.run_benchmark import main as run_benchmark
            import asyncio
            
            # Préparer les arguments pour le benchmark
            sys_args = ["--" + benchmark_type]
            
            # Ajouter l'option --optimize pour appliquer les optimisations
            if "--optimize" in args or "-o" in args:
                sys_args.append("--optimize")
                
            # Exécuter le benchmark de manière asynchrone
            if asyncio.run(run_benchmark()) == 0:
                logger.info("Benchmark terminé avec succès")
                
                # Recharger la configuration après le benchmark
                self.config.load_config()
            else:
                logger.error("Erreur lors de l'exécution du benchmark")
                
        except ImportError:
            logger.error("Module de benchmark non disponible")
            logger.error("Assurez-vous que le module benchmarking est correctement installé")
            
    def do_performance(self, arg):
        """
        Définir le mode de performance
        
        Usage:
          performance high - Mode de performance élevée
          performance balanced - Mode de performance équilibrée
          performance economy - Mode d'économie de ressources
          performance auto - Mode de performance automatique
        """
        args = arg.split()
        if not args:
            # Afficher le mode actuel
            mode = self.config.get_performance_mode()
            print(f"Mode de performance actuel: {mode}")
            return
            
        mode = args[0].lower()
        valid_modes = ["high", "balanced", "economy", "auto"]
        
        if mode in valid_modes:
            self.config.set("performance_mode", mode)
            logger.info(f"Mode de performance défini sur: {mode}")
            
            # Mettre à jour les limites de ressources en fonction du mode
            resource_limits = self.config.get_resource_limits()
            
            if mode == "high":
                resource_limits.update({
                    "max_threads": 8,
                    "max_ram_usage_percent": 75,
                    "cache_size_mb": 500
                })
            elif mode == "balanced":
                resource_limits.update({
                    "max_threads": 4,
                    "max_ram_usage_percent": 60,
                    "cache_size_mb": 250
                })
            elif mode == "economy":
                resource_limits.update({
                    "max_threads": 2,
                    "max_ram_usage_percent": 40,
                    "cache_size_mb": 100
                })
                
            # Ne pas mettre à jour les limites en mode auto
            if mode != "auto":
                self.config.set("resource_limits", resource_limits)
                
            # Mettre à jour les seuils du moniteur de ressources
            if self.resource_monitor_active:
                if mode == "high":
                    resource_monitor.update_thresholds(cpu=85, memory=80, disk=90)
                elif mode == "balanced":
                    resource_monitor.update_thresholds(cpu=75, memory=70, disk=85)
                elif mode == "economy":
                    resource_monitor.update_thresholds(cpu=60, memory=50, disk=80)
                    
        else:
            logger.error(f"Mode de performance invalide: {mode}")
            print(f"Modes disponibles: {', '.join(valid_modes)}")
            
    def do_help(self, arg):
        """Afficher l'aide pour une commande"""
        if arg:
            # Afficher l'aide spécifique pour la commande
            super().do_help(arg)
        else:
            # Afficher l'aide générale
            print("\n=== Commandes disponibles ===")
            print("status       - Afficher l'état actuel du système")
            print("start        - Démarrer une stratégie ou un service")
            print("stop         - Arrêter une stratégie ou un service")
            print("config       - Afficher ou modifier la configuration")
            print("benchmark    - Exécuter les benchmarks pour optimiser GBPBot")
            print("performance  - Définir le mode de performance")
            print("exit, quit   - Quitter l'interface en ligne de commande")
            print("help         - Afficher cette aide")
            print()
            print("Pour plus d'informations sur une commande spécifique, tapez 'help <commande>'")
            print()
            
    def _stop_all_services(self):
        """Arrêter tous les services et stratégies"""
        # Arrêter le moniteur de ressources
        if self.resource_monitor_active:
            resource_monitor.stop()
            self.resource_monitor_active = False
            
        # Arrêter toutes les stratégies actives
        for strategy in list(self.active_strategies.keys()):
            logger.info(f"Arrêt de la stratégie {strategy}")
            del self.active_strategies[strategy]
            
    def _format_duration(self, seconds):
        """Formater une durée en secondes en format lisible"""
        if seconds < 60:
            return f"{seconds:.1f} secondes"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.1f} minutes"
        else:
            hours = seconds / 3600
            return f"{hours:.1f} heures"


def parse_args():
    """Analyser les arguments de la ligne de commande"""
    parser = argparse.ArgumentParser(description="GBPBot - Interface en ligne de commande")
    
    # Commandes principales
    subparsers = parser.add_subparsers(dest="command", help="Commande à exécuter")
    
    # Commande 'status'
    status_parser = subparsers.add_parser("status", help="Afficher l'état actuel du système")
    
    # Commande 'snipe'
    snipe_parser = subparsers.add_parser("snipe", help="Sniper un nouveau token")
    snipe_parser.add_argument("token_address", help="Adresse du token à sniper")
    snipe_parser.add_argument("--amount", type=float, default=0.1, help="Montant à investir")
    snipe_parser.add_argument("--slippage", type=float, default=10, help="Slippage maximum en pourcentage")
    
    # Commande 'arbitrage'
    arbitrage_parser = subparsers.add_parser("arbitrage", help="Exécuter l'arbitrage")
    arbitrage_parser.add_argument("--threshold", type=float, default=1.5, help="Seuil de profit en pourcentage")
    arbitrage_parser.add_argument("--max-pairs", type=int, default=10, help="Nombre maximum de paires à surveiller")
    
    # Commande 'monitor-new-tokens'
    monitor_parser = subparsers.add_parser("monitor-new-tokens", help="Surveiller les nouveaux tokens")
    monitor_parser.add_argument("--min-liquidity", type=float, default=5, help="Liquidité minimale en SOL")
    
    # Commande 'benchmark'
    benchmark_parser = subparsers.add_parser("benchmark", help="Exécuter les benchmarks")
    benchmark_parser.add_argument("type", choices=["all", "system", "blockchain", "dex", "transaction"],
                              help="Type de benchmark à exécuter")
    benchmark_parser.add_argument("--optimize", "-o", action="store_true", help="Optimiser en fonction des résultats")
    
    # Commande 'performance'
    performance_parser = subparsers.add_parser("performance", help="Définir le mode de performance")
    performance_parser.add_argument("mode", choices=["high", "balanced", "economy", "auto"],
                                help="Mode de performance")
    
    # Options globales
    parser.add_argument("--interactive", "-i", action="store_true", help="Démarrer en mode interactif")
    parser.add_argument("--verbose", "-v", action="store_true", help="Afficher les messages de débogage")
    
    return parser.parse_args()


def process_command(args):
    """Traiter une commande non interactive"""
    if args.verbose:
        logging.getLogger("gbpbot").setLevel(logging.DEBUG)
        
    # Commande 'status'
    if args.command == "status":
        cli = GBPBotCLI()
        cli.do_status("")
        
    # Commande 'snipe'
    elif args.command == "snipe":
        cli = GBPBotCLI()
        cmd = f"start sniping {args.token_address} --amount={args.amount} --slippage={args.slippage}"
        cli.do_start(cmd.split("start ")[1])
        
    # Commande 'arbitrage'
    elif args.command == "arbitrage":
        cli = GBPBotCLI()
        cmd = f"start arbitrage --threshold={args.threshold} --max-pairs={args.max_pairs}"
        cli.do_start(cmd.split("start ")[1])
        
    # Commande 'monitor-new-tokens'
    elif args.command == "monitor-new-tokens":
        cli = GBPBotCLI()
        cmd = f"start monitor --min-liquidity={args.min_liquidity}"
        cli.do_start(cmd.split("start ")[1])
        
    # Commande 'benchmark'
    elif args.command == "benchmark":
        cli = GBPBotCLI()
        cmd = f"benchmark {args.type}"
        if args.optimize:
            cmd += " --optimize"
        cli.do_benchmark(cmd.split("benchmark ")[1])
        
    # Commande 'performance'
    elif args.command == "performance":
        cli = GBPBotCLI()
        cli.do_performance(args.mode)
        

def main():
    """Fonction principale"""
    # Analyser les arguments de la ligne de commande
    args = parse_args()
    
    # Mode interactif
    if args.interactive or not args.command:
        cli = GBPBotCLI()
        if args.verbose:
            logging.getLogger("gbpbot").setLevel(logging.DEBUG)
        try:
            cli.cmdloop()
        except KeyboardInterrupt:
            print("\nInterruption détectée. Arrêt de GBPBot...")
            cli._stop_all_services()
    else:
        # Mode non interactif
        process_command(args)


if __name__ == "__main__":
    main()
