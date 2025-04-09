#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GBPBot - Lanceur Unifié
=======================

Point d'entrée unique pour lancer le GBPBot avec toutes ses fonctionnalités.
Ce script gère automatiquement :
- Vérification de l'environnement
- Installation des dépendances manquantes
- Configuration de l'environnement
- Lancement du bot dans différents modes

Usage:
    python gbpbot_launcher.py [options]

Options:
    --mode MODE     Mode de lancement: cli, dashboard, auto, simulation
    --debug         Active les logs détaillés 
    --no-checks     Ignore les vérifications d'environnement
    --config PATH   Utilise un fichier de configuration spécifique
"""

import os
import sys
import time
import logging
import platform
import subprocess
import importlib
import importlib.util
import traceback
import argparse
import shutil
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple, Callable

# Détection du répertoire de base
BASE_DIR = Path(__file__).parent.absolute()

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("gbpbot_launcher")

# Constantes
REQUIRED_PACKAGES = [
    "web3",
    "python-dotenv",
    "loguru",
    "pyyaml",
    "pandas",
    "requests",
    "pytest-asyncio"
]

COLORS = {
    "GREEN": "\033[92m",
    "YELLOW": "\033[93m",
    "RED": "\033[91m",
    "BLUE": "\033[94m",
    "CYAN": "\033[96m",
    "MAGENTA": "\033[95m",
    "BOLD": "\033[1m",
    "END": "\033[0m"
}

# Fonctions utilitaires
def print_colored(message: str, color: str = "GREEN", bold: bool = False, end: str = "\n") -> None:
    """Affiche un message coloré dans le terminal"""
    prefix = COLORS.get(color.upper(), "")
    if bold:
        prefix += COLORS["BOLD"]
    suffix = COLORS["END"]
    print(f"{prefix}{message}{suffix}", end=end)
    
def clear_screen() -> None:
    """Efface l'écran du terminal"""
    if platform.system() == "Windows":
        os.system("cls")
    else:
        os.system("clear")

def display_banner() -> None:
    """Affiche la bannière ASCII du GBPBot"""
    clear_screen()
    print_colored("""
    ██████╗ ██████╗ ██████╗ ██████╗  ██████╗ ████████╗
    ██╔════╝ ██╔══██╗██╔══██╗██╔══██╗██╔═══██╗╚══██╔══╝
    ██║  ███╗██████╔╝██████╔╝██████╔╝██║   ██║   ██║   
    ██║   ██║██╔══██╗██╔═══╝ ██╔══██╗██║   ██║   ██║   
    ╚██████╔╝██████╔╝██║     ██████╔╝╚██████╔╝   ██║   
     ╚═════╝ ╚═════╝ ╚═╝     ╚═════╝  ╚═════╝    ╚═╝   
    ================================================
                GBPBot - Trading Bot v1.0
    ================================================
    """, color="BLUE", bold=True)

# Fonctions de vérification et d'installation
def check_python_version() -> bool:
    """Vérifie que la version de Python est compatible"""
    version_info = sys.version_info
    is_compatible = version_info.major == 3 and version_info.minor >= 8
    
    if is_compatible:
        print_colored(f"✅ Version Python: {platform.python_version()} (compatible)", "GREEN")
    else:
        print_colored(f"❌ Version Python: {platform.python_version()} (incompatible)", "RED")
        print_colored("   Python 3.8+ requis pour GBPBot", "YELLOW")
    
    return is_compatible

def configure_asyncio() -> bool:
    """Configure asyncio pour éviter les erreurs sur Windows"""
    try:
        if platform.system() == "Windows":
            import asyncio
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            logger.info("Configuration asyncio pour Windows réalisée avec succès")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de la configuration d'asyncio: {e}")
        return False

def check_env_file() -> bool:
    """Vérifie si un fichier .env existe et le crée à partir de .env.example si nécessaire"""
    env_file = BASE_DIR / ".env"
    env_local_file = BASE_DIR / ".env.local"
    env_example_file = BASE_DIR / ".env.example"
    
    # Si .env.local existe, il a priorité
    if env_local_file.exists():
        print_colored(f"✅ Fichier .env.local trouvé", "GREEN")
        # Si .env n'existe pas ou est différent de .env.local, le copier
        if not env_file.exists():
            shutil.copy2(env_local_file, env_file)
            print_colored(f"✅ Fichier .env créé à partir de .env.local", "GREEN")
        return True
    
    # Si .env existe
    if env_file.exists():
        print_colored(f"✅ Fichier .env trouvé", "GREEN")
        return True
    
    # Si ni .env ni .env.local n'existent mais .env.example existe
    if env_example_file.exists():
        print_colored(f"ℹ️ Fichier .env non trouvé", "YELLOW")
        print_colored(f"ℹ️ Création à partir de .env.example", "YELLOW")
        shutil.copy2(env_example_file, env_file)
        print_colored(f"✅ Fichier .env créé", "GREEN")
        print_colored(f"⚠️ Veuillez éditer le fichier .env avec vos informations personnelles", "YELLOW", bold=True)
        return True
    
    # Aucun fichier .env ni modèle
    print_colored(f"❌ Aucun fichier .env ou .env.example trouvé", "RED")
    return False

def install_missing_packages() -> bool:
    """Vérifie et installe les packages Python manquants"""
    print_colored("\nVérification des dépendances requises...", "BLUE")
    
    missing_packages = []
    for package in REQUIRED_PACKAGES:
        try:
            __import__(package.replace("-", "_"))
            print_colored(f"✅ {package} est déjà installé", "GREEN")
        except ImportError:
            missing_packages.append(package)
            print_colored(f"❌ {package} n'est pas installé", "RED")
    
    # Installation des packages manquants
    if missing_packages:
        print_colored(f"\nInstallation des {len(missing_packages)} dépendances manquantes...", "YELLOW")
        try:
            for package in missing_packages:
                print_colored(f"Installation de {package}...", "CYAN", end=" ")
                subprocess.check_call(
                    [sys.executable, "-m", "pip", "install", package],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                print_colored("OK", "GREEN")
            
            print_colored("\n✅ Toutes les dépendances sont maintenant installées!", "GREEN")
            return True
        except Exception as e:
            print_colored(f"\n❌ Erreur lors de l'installation des dépendances: {e}", "RED")
            return False
    else:
        print_colored("\n✅ Toutes les dépendances sont déjà installées!", "GREEN")
        return True

def fix_circular_imports() -> bool:
    """Résout les problèmes d'importation circulaire connus"""
    try:
        # Vérifier si des modules problématiques sont présents
        hardware_optimizer_path = BASE_DIR / "gbpbot" / "core" / "monitoring" / "hardware_optimizer.py"
        compatibility_path = BASE_DIR / "gbpbot" / "core" / "monitoring" / "compatibility.py"
        
        if hardware_optimizer_path.exists() and compatibility_path.exists():
            logger.info("Résolution des imports circulaires potentiels...")
            
            # Créer un stub pour contourner les imports circulaires
            class HardwareOptimizerCompatStub:
                def __init__(self, config=None):
                    self.config = config or {}
                
                def apply_optimizations(self, target="all"):
                    logger.info(f"Stub: Simulation d'optimisation matérielle pour {target}")
                    return True
                
                def get_optimization_status(self):
                    return {"status": "optimized", "applied": ["stub_optimization"]}
                
                def get_recommendations(self):
                    return ["Stub: Aucune recommandation disponible"]
            
            # Injecter le stub dans sys.modules
            import sys
            module_name = "gbpbot.core.monitoring.compatibility"
            if module_name in sys.modules:
                sys.modules[module_name].HardwareOptimizerCompat = HardwareOptimizerCompatStub
                logger.info(f"Stub injecté dans {module_name} existant")
            else:
                import types
                mod = types.ModuleType(module_name)
                mod.HardwareOptimizerCompat = HardwareOptimizerCompatStub
                sys.modules[module_name] = mod
                logger.info(f"Nouveau module {module_name} créé avec stub")
            
            return True
    except Exception as e:
        logger.error(f"Erreur lors de la résolution des imports circulaires: {e}")
        traceback.print_exc()
    
    return False

def check_environment() -> bool:
    """Effectue toutes les vérifications d'environnement nécessaires"""
    print_colored("\nVérification de l'environnement...", "BLUE", bold=True)
    
    # Vérification de la version de Python
    if not check_python_version():
        return False
    
    # Configuration d'asyncio
    configure_asyncio()
    
    # Vérification du fichier .env
    if not check_env_file():
        return False
    
    # Vérification et installation des dépendances
    if not install_missing_packages():
        return False
    
    # Résolution des problèmes d'importation circulaire
    fix_circular_imports()
    
    print_colored("\n✅ Environnement correctement configuré!", "GREEN", bold=True)
    return True

# Fonctions de lancement
def launch_cli_mode() -> int:
    """Lance le bot en mode CLI"""
    logger.info("Lancement du mode CLI...")
    
    # Importation sécurisée du module CLI
    try:
        # D'abord, essayons d'importer notre module de compatibilité TensorFlow
        try:
            from gbpbot.utils.tensorflow_compat import tf, HAS_TENSORFLOW
            logger.info(f"Module de compatibilité TensorFlow chargé (disponible: {HAS_TENSORFLOW})")
        except ImportError:
            logger.warning("Module de compatibilité TensorFlow non disponible. Mode dégradé activé.")
        
        # Ensuite, importons le module CLI
        try:
            # Essai d'importation directe
            from gbpbot.interface.unified_interface import UnifiedInterface
            logger.info("Interface unifiée importée avec succès")
            
            # Lancement de l'interface unifiée en mode asynchrone
            async def run_unified_interface():
                interface = UnifiedInterface()
                await interface.initialize()
                return await interface.start()
            
            import asyncio
            return asyncio.run(run_unified_interface())
            
        except ImportError as e:
            logger.warning(f"Impossible d'importer l'interface unifiée: {str(e)}")
            
            # Essayons d'importer directement l'interface CLI
            try:
                from gbpbot.cli_interface import CLIInterface
                logger.info("Interface CLI importée avec succès")
                
                # Lancement de l'interface CLI en mode asynchrone
                async def run_cli_interface():
                    interface = CLIInterface()
                    interface.display_welcome()
                    return await interface.run()
                
                import asyncio
                return asyncio.run(run_cli_interface())
                
            except ImportError as e2:
                logger.error(f"Impossible d'importer l'interface CLI: {str(e2)}")
                if "tensorflow" in str(e2).lower() or "pywrap_tensorflow" in str(e2).lower():
                    logger.error("Erreur liée à TensorFlow. Essayez d'installer TensorFlow ou de créer le module de compatibilité.")
                    logger.info("Commande recommandée: pip install tensorflow")
                    logger.info("Ou lancez avec: python gbpbot_launcher.py --no-checks --bypass-imports")
    except Exception as e:
        logger.error(f"Erreur lors du lancement du mode CLI: {str(e)}")
        traceback.print_exc()
    
    # En cas d'échec, affiche un message d'erreur
    print_colored("\nErreur lors du lancement de l'interface CLI. Vérifiez les logs pour plus de détails.", "RED", True)
    print_colored("Vous pouvez essayer les solutions suivantes:", "YELLOW")
    print_colored("1. Installer les dépendances manquantes (pip install -r requirements.txt)", "YELLOW")
    print_colored("2. Utiliser le mode sans vérification: python gbpbot_launcher.py --no-checks", "YELLOW")
    print_colored("3. Vérifier les logs pour des erreurs spécifiques", "YELLOW")
    
    return 1

def launch_dashboard_mode() -> int:
    """Lance le GBPBot en mode dashboard"""
    print_colored("\nLancement du GBPBot en mode dashboard...", "BLUE", bold=True)
    
    try:
        # Vérifier et installer les dépendances spécifiques au dashboard
        dashboard_deps = ["fastapi", "uvicorn", "websockets"]
        for dep in dashboard_deps:
            try:
                __import__(dep)
            except ImportError:
                print_colored(f"Installation de {dep} pour le dashboard...", "YELLOW")
                subprocess.check_call([sys.executable, "-m", "pip", "install", dep])
        
        # Tenter de lancer le dashboard
        try:
            from gbpbot.dashboard import run_dashboard
            run_dashboard.start()
            return 0
        except ImportError:
            dashboard_path = BASE_DIR / "gbpbot" / "dashboard" / "run_dashboard.py"
            if dashboard_path.exists():
                result = subprocess.run([sys.executable, str(dashboard_path)])
                return result.returncode
            
            print_colored("❌ Module de dashboard non trouvé!", "RED")
            return 1
    except Exception as e:
        print_colored(f"❌ Erreur lors du lancement du dashboard: {e}", "RED")
        logger.error(f"Erreur lors du lancement du dashboard: {e}")
        traceback.print_exc()
        return 1

def launch_auto_mode() -> int:
    """Lance le GBPBot en mode automatique"""
    print_colored("\nLancement du GBPBot en mode automatique (tous modules)...", "BLUE", bold=True)
    
    try:
        # Définir la variable d'environnement pour le mode auto
        os.environ["BOT_MODE"] = "auto"
        
        # Tenter de lancer en mode auto
        try:
            from gbpbot.core.bot import GBPBot
            bot = GBPBot(mode="auto")
            bot.run()
            return 0
        except ImportError as e:
            logger.warning(f"Impossible d'importer gbpbot.core.bot: {e}")
            
            # Si échec, revenir au mode CLI
            print_colored("Lancement via l'interface CLI en mode AUTO...", "YELLOW")
            return launch_cli_mode()
    except Exception as e:
        print_colored(f"❌ Erreur lors du lancement du mode automatique: {e}", "RED")
        logger.error(f"Erreur lors du lancement du mode automatique: {e}")
        traceback.print_exc()
        return 1

def launch_simulation_mode() -> int:
    """Lance le GBPBot en mode simulation"""
    print_colored("\nLancement du GBPBot en mode simulation...", "BLUE", bold=True)
    
    try:
        # Définir la variable d'environnement pour le mode simulation
        os.environ["SIMULATION_MODE"] = "TRUE"
        
        # Tenter d'importer et lancer le mode simulation
        try:
            from gbpbot.core.bot import GBPBot
            bot = GBPBot(mode="simulation")
            bot.run()
            return 0
        except ImportError:
            # Si échec, revenir au mode CLI avec simulation activée
            print_colored("Lancement via l'interface CLI en mode SIMULATION...", "YELLOW")
            return launch_cli_mode()
    except Exception as e:
        print_colored(f"❌ Erreur lors du lancement du mode simulation: {e}", "RED")
        logger.error(f"Erreur lors du lancement du mode simulation: {e}")
        traceback.print_exc()
        return 1

def show_menu() -> str:
    """Affiche le menu principal et retourne le choix de l'utilisateur"""
    display_banner()
    
    print_colored("\nVeuillez choisir une option:", "CYAN")
    
    print_colored("  1. Démarrer le Bot", "BLUE")
    print_colored("  2. Configurer les paramètres", "BLUE")
    print_colored("  3. Afficher la configuration actuelle", "BLUE")
    print_colored("  4. Statistiques et Logs", "BLUE")
    print_colored("  5. Afficher les Modules Disponibles", "BLUE")
    print_colored("  6. Quitter", "BLUE")
    
    choice = input("\nVotre choix (1-6): ")
    return choice

def show_modules_menu() -> str:
    """Affiche le menu des modules et retourne le choix de l'utilisateur"""
    display_banner()
    
    print_colored("\nGBPBot - Sélection de Module", "CYAN", bold=True)
    print_colored("============================================================\n", "CYAN")
    
    print_colored("  1. Arbitrage entre les DEX", "BLUE")
    print_colored("  2. Sniping de Token", "BLUE")
    print_colored("  3. Lancer automatiquement le bot", "BLUE")
    print_colored("  4. AI Assistant", "BLUE")
    print_colored("  5. Backtesting et Simulation", "BLUE")
    print_colored("  6. Retour au menu principal", "BLUE")
    
    choice = input("\nVotre choix (1-6): ")
    return choice

def edit_configuration():
    """Menu d'édition de la configuration"""
    display_banner()
    
    print_colored("\nConfiguration du fichier .env", "CYAN", bold=True)
    print_colored("============================================================\n", "CYAN")
    
    print_colored("  1. Voir la configuration actuelle", "BLUE")
    print_colored("  2. Modifier la blockchain par défaut", "BLUE")
    print_colored("  3. Ouvrir le fichier .env dans l'éditeur par défaut", "BLUE")
    print_colored("  4. Retour au menu principal", "BLUE")
    
    choice = input("\nVotre choix (1-4): ")
    
    if choice == "1":
        # Afficher la configuration
        display_banner()
        print_colored("\nConfiguration actuelle:", "CYAN", bold=True)
        print_colored("============================================================\n", "CYAN")
        
        env_file = BASE_DIR / ".env"
        if env_file.exists():
            with open(env_file, "r") as f:
                config_content = f.read()
            print(config_content)
        else:
            print_colored("❌ Fichier .env non trouvé!", "RED")
        
        input("\nAppuyez sur Entrée pour continuer...")
        return show_menu()
    
    elif choice == "2":
        # Modifier la blockchain par défaut
        display_banner()
        print_colored("\nSélection de la blockchain par défaut:", "CYAN", bold=True)
        print_colored("============================================================\n", "CYAN")
        
        print_colored("  1. Avalanche", "BLUE")
        print_colored("  2. Solana", "BLUE")
        
        blockchain_choice = input("\nVotre choix (1-2): ")
        
        blockchain = "avalanche" if blockchain_choice == "1" else "solana"
        
        # Modifier le fichier .env
        env_file = BASE_DIR / ".env"
        if env_file.exists():
            with open(env_file, "r") as f:
                lines = f.readlines()
            
            with open(env_file, "w") as f:
                for line in lines:
                    if line.startswith("DEFAULT_BLOCKCHAIN="):
                        f.write(f"DEFAULT_BLOCKCHAIN={blockchain}          # avalanche, solana\n")
                    else:
                        f.write(line)
            
            print_colored(f"\n✅ Blockchain par défaut modifiée: {blockchain}", "GREEN")
        else:
            print_colored("❌ Fichier .env non trouvé!", "RED")
        
        input("\nAppuyez sur Entrée pour continuer...")
        return show_menu()
    
    elif choice == "3":
        # Ouvrir le fichier .env dans l'éditeur par défaut
        env_file = BASE_DIR / ".env"
        if env_file.exists():
            print_colored(f"\nOuverture du fichier {env_file}...", "CYAN")
            
            if platform.system() == "Windows":
                os.startfile(env_file)
            elif platform.system() == "Darwin":  # macOS
                subprocess.run(["open", str(env_file)])
            else:  # Linux
                subprocess.run(["xdg-open", str(env_file)])
            
            print_colored("\n✅ N'oubliez pas de sauvegarder vos modifications!", "GREEN")
        else:
            print_colored("❌ Fichier .env non trouvé!", "RED")
        
        input("\nAppuyez sur Entrée pour continuer...")
        return show_menu()
    
    elif choice == "4":
        # Retour au menu principal
        return show_menu()
    
    else:
        print_colored("❌ Option invalide!", "RED")
        time.sleep(1)
        return edit_configuration()

def show_stats():
    """Affiche les statistiques et logs"""
    display_banner()
    
    print_colored("\nStatistiques et Logs", "CYAN", bold=True)
    print_colored("============================================================\n", "CYAN")
    
    print_colored("  1. Afficher les derniers logs", "BLUE")
    print_colored("  2. Afficher les statistiques de trading", "BLUE")
    print_colored("  3. Vérifier l'état des connexions blockchain", "BLUE")
    print_colored("  4. Retour au menu principal", "BLUE")
    
    choice = input("\nVotre choix (1-4): ")
    
    if choice == "1":
        # Afficher les derniers logs
        display_banner()
        print_colored("\nDerniers logs:", "CYAN", bold=True)
        print_colored("============================================================\n", "CYAN")
        
        log_dir = BASE_DIR / "logs"
        if log_dir.exists():
            log_files = list(log_dir.glob("*.log"))
            log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            if log_files:
                latest_log = log_files[0]
                print_colored(f"Fichier: {latest_log.name}\n", "YELLOW")
                
                with open(latest_log, "r") as f:
                    # Lire les 50 dernières lignes
                    lines = f.readlines()
                    for line in lines[-50:]:
                        print(line, end="")
            else:
                print_colored("❌ Aucun fichier de log trouvé!", "RED")
        else:
            print_colored("❌ Répertoire de logs non trouvé!", "RED")
        
        input("\nAppuyez sur Entrée pour continuer...")
        return show_stats()
    
    elif choice == "2":
        # Afficher les statistiques de trading
        display_banner()
        print_colored("\nStatistiques de trading:", "CYAN", bold=True)
        print_colored("============================================================\n", "CYAN")
        
        try:
            # Importer le moniteur de performance
            from gbpbot.monitoring.performance_monitor import get_performance_monitor
            
            # Obtenir le moniteur de performance
            monitor = get_performance_monitor()
            
            # Demander la période pour les statistiques
            print_colored("Choisissez la période pour les statistiques:", "YELLOW")
            print_colored("  1. Dernières 24 heures", "BLUE")
            print_colored("  2. Derniers 7 jours", "BLUE")
            print_colored("  3. Dernier mois", "BLUE")
            print_colored("  4. Tous les temps", "BLUE")
            
            period_choice = input("\nVotre choix (1-4): ")
            
            # Définir la période en heures
            hours = {
                "1": 24,
                "2": 24*7,
                "3": 24*30,
                "4": 24*365  # Pratiquement tous les temps
            }.get(period_choice, 24)  # Par défaut 24h si choix invalide
            
            # Obtenir les statistiques
            stats = monitor.get_stats(hours)
            
            if stats["total_trades"] == 0:
                print_colored("\n❌ Aucune transaction trouvée pour cette période!", "YELLOW")
            else:
                # Afficher les statistiques générales
                print_colored("\n🔹 Statistiques Générales:", "GREEN", bold=True)
                print_colored(f"  Période: {stats['period_hours']} heures", "WHITE")
                print_colored(f"  Transactions totales: {stats['total_trades']}", "WHITE")
                print_colored(f"  Transactions profitables: {stats['profit_trades']}", "WHITE")
                print_colored(f"  Transactions en perte: {stats['loss_trades']}", "WHITE")
                print_colored(f"  Taux de réussite: {stats['win_rate']:.2f}%", "WHITE")
                
                # Afficher les profits/pertes
                print_colored("\n🔹 Profits et Pertes:", "GREEN", bold=True)
                print_colored(f"  Profit total: ${stats['profit_total']:.2f}", "WHITE" if stats['profit_total'] == 0 else "GREEN" if stats['profit_total'] > 0 else "RED")
                print_colored(f"  Perte totale: ${stats['loss_total']:.2f}", "WHITE" if stats['loss_total'] == 0 else "RED")
                print_colored(f"  Profit net: ${stats['net_profit']:.2f}", "WHITE" if stats['net_profit'] == 0 else "GREEN" if stats['net_profit'] > 0 else "RED")
                print_colored(f"  Profit moyen: ${stats['avg_profit']:.2f}", "GREEN")
                print_colored(f"  Perte moyenne: ${stats['avg_loss']:.2f}", "RED")
                print_colored(f"  Profit maximum: ${stats['max_profit']:.2f}", "GREEN")
                print_colored(f"  Perte maximum: ${stats['max_loss']:.2f}", "RED")
                print_colored(f"  Facteur de profit: {stats['profit_factor']:.2f}", "WHITE")
                
                # Afficher les statistiques par blockchain
                if stats["blockchain_stats"]:
                    print_colored("\n🔹 Statistiques par Blockchain:", "GREEN", bold=True)
                    for blockchain, bc_stats in stats["blockchain_stats"].items():
                        print_colored(f"  {blockchain}:", "BLUE")
                        print_colored(f"    Transactions: {bc_stats['trades']}", "WHITE")
                        print_colored(f"    Profit: ${bc_stats['profit']:.2f}", "WHITE" if bc_stats['profit'] == 0 else "GREEN" if bc_stats['profit'] > 0 else "RED")
                        print_colored(f"    Taux de réussite: {bc_stats['success_rate']:.2f}%", "WHITE")
                
                # Afficher les statistiques par stratégie
                if stats["strategy_stats"]:
                    print_colored("\n🔹 Statistiques par Stratégie:", "GREEN", bold=True)
                    for strategy, st_stats in stats["strategy_stats"].items():
                        print_colored(f"  {strategy}:", "BLUE")
                        print_colored(f"    Transactions: {st_stats['trades']}", "WHITE")
                        print_colored(f"    Profit: ${st_stats['profit']:.2f}", "WHITE" if st_stats['profit'] == 0 else "GREEN" if st_stats['profit'] > 0 else "RED")
                        print_colored(f"    Taux de réussite: {st_stats['success_rate']:.2f}%", "WHITE")
        except ImportError as e:
            print_colored(f"\n❌ Erreur d'importation: {str(e)}", "RED")
            print_colored("Le module de surveillance des performances n'est pas disponible.", "YELLOW")
        except Exception as e:
            print_colored(f"\n❌ Erreur lors de l'affichage des statistiques: {str(e)}", "RED")
        
        input("\nAppuyez sur Entrée pour continuer...")
        return show_stats()
    
    elif choice == "3":
        # Vérifier l'état des connexions blockchain
        display_banner()
        print_colored("\nÉtat des connexions blockchain:", "CYAN", bold=True)
        print_colored("============================================================\n", "CYAN")
        
        # Importer dotenv pour charger les variables d'environnement
        try:
            from dotenv import load_dotenv
            load_dotenv()
            
            import requests
            
            # Vérifier la connexion Avalanche
            avax_rpc = os.getenv("AVALANCHE_RPC_URL")
            if avax_rpc:
                print_colored("Connexion Avalanche:", "YELLOW")
                try:
                    response = requests.post(
                        avax_rpc,
                        json={"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1},
                        timeout=5
                    )
                    if response.status_code == 200:
                        block = int(response.json().get("result", "0x0"), 16)
                        print_colored(f"  ✅ Connecté (block: {block})", "GREEN")
                    else:
                        print_colored(f"  ❌ Erreur: {response.status_code}", "RED")
                except Exception as e:
                    print_colored(f"  ❌ Erreur: {str(e)}", "RED")
            
            # Vérifier la connexion Solana
            solana_rpc = os.getenv("SOLANA_RPC_URL")
            if solana_rpc:
                print_colored("\nConnexion Solana:", "YELLOW")
                try:
                    response = requests.post(
                        solana_rpc,
                        json={"jsonrpc": "2.0", "method": "getHealth", "params": [], "id": 1},
                        timeout=5
                    )
                    if response.status_code == 200:
                        health = response.json().get("result", "unknown")
                        print_colored(f"  ✅ Connecté (santé: {health})", "GREEN")
                    else:
                        print_colored(f"  ❌ Erreur: {response.status_code}", "RED")
                except Exception as e:
                    print_colored(f"  ❌ Erreur: {str(e)}", "RED")
            
        except ImportError:
            print_colored("❌ Module dotenv ou requests non disponible!", "RED")
        
        input("\nAppuyez sur Entrée pour continuer...")
        return show_stats()
    
    elif choice == "4":
        # Retour au menu principal
        return show_menu()
    
    else:
        print_colored("❌ Option invalide!", "RED")
        time.sleep(1)
        return show_stats()

def show_modules_info():
    """Affiche les informations sur les modules disponibles"""
    display_banner()
    
    print_colored("\nModules Disponibles", "CYAN", bold=True)
    print_colored("============================================================\n", "CYAN")
    
    # 1. Arbitrage entre les DEX
    print_colored("1. Arbitrage entre les DEX", "MAGENTA", bold=True)
    print_colored("--------------------------------------------------", "MAGENTA")
    print_colored("🔹 Objectif : Exploiter les écarts de prix entre différents DEX", "CYAN")
    print_colored("✅ Surveillance des différences de prix entre exchanges", "GREEN")
    print_colored("✅ Calcul des frais et impact du slippage pour chaque arbitrage", "GREEN")
    print_colored("✅ Exécution instantanée des transactions pour profiter des écarts", "GREEN")
    print_colored("✅ Front-run des grosses transactions en achetant avant elles", "GREEN")
    print_colored("✅ Gestion intelligente des stop-loss et take-profit", "GREEN")
    print()
    
    # 2. Sniping de Token
    print_colored("2. Sniping de Token", "MAGENTA", bold=True)
    print_colored("--------------------------------------------------", "MAGENTA")
    print_colored("🔹 Objectif : Sniper les nouveaux tokens prometteurs", "CYAN")
    print_colored("✅ Surveillance en continue des nouvelles paires créées sur les DEX", "GREEN")
    print_colored("✅ Détection des whales qui achètent massivement un nouveau token", "GREEN")
    print_colored("✅ Génération d'un score de confiance pour éviter les scams", "GREEN")
    print_colored("✅ Prendre des profits progressivement avant le dump", "GREEN")
    print_colored("✅ Stop-loss intelligent pour éviter les rug pulls et les honeypots", "GREEN")
    print()
    
    # 3. Mode Automatique
    print_colored("3. Mode Automatique", "MAGENTA", bold=True)
    print_colored("--------------------------------------------------", "MAGENTA")
    print_colored("🔹 Objectif : Combiner toutes les stratégies de manière intelligente", "CYAN")
    print_colored("✅ Analyse en temps réel des opportunités", "GREEN")
    print_colored("✅ Calcul des meilleures probabilités de gain", "GREEN")
    print_colored("✅ Ajustement intelligent des stratégies", "GREEN")
    print_colored("✅ Gestion automatique des fonds", "GREEN")
    print_colored("✅ Analyse de la microstructure du marché", "GREEN")
    print()
    
    # 4. AI Assistant
    print_colored("4. AI Assistant", "MAGENTA", bold=True)
    print_colored("--------------------------------------------------", "MAGENTA")
    print_colored("🔹 Objectif : Analyser le marché, les tokens et les contrats intelligents", "CYAN")
    print_colored("✅ Analyse du sentiment du marché et des réseaux sociaux", "GREEN")
    print_colored("✅ Évaluation détaillée des tokens spécifiques", "GREEN")
    print_colored("✅ Analyse de sécurité des contrats intelligents", "GREEN")
    print_colored("✅ Génération de rapports de marché personnalisés", "GREEN")
    print_colored("✅ Recommandations de trading basées sur l'IA", "GREEN")
    print()
    
    # 5. Backtesting et Simulation
    print_colored("5. Backtesting et Simulation", "MAGENTA", bold=True)
    print_colored("--------------------------------------------------", "MAGENTA")
    print_colored("🔹 Objectif : Tester les stratégies sur des données historiques", "CYAN")
    print_colored("✅ Configuration flexible des paramètres de test", "GREEN")
    print_colored("✅ Chargement de données historiques précises", "GREEN")
    print_colored("✅ Simulation avec différentes conditions de marché", "GREEN")
    print_colored("✅ Analyse détaillée des résultats et des performances", "GREEN")
    print_colored("✅ Optimisation des stratégies basée sur les résultats", "GREEN")
    
    input("\nAppuyez sur Entrée pour continuer...")
    return 0

def process_cli_interaction() -> int:
    """Gère l'interaction via l'interface en ligne de commande"""
    
    while True:
        choice = show_menu()
        
        if choice == "1":
            # Démarrer le Bot
            modules_choice = show_modules_menu()
            
            if modules_choice == "1":
                # Arbitrage entre les DEX
                os.environ["BOT_MODE"] = "arbitrage"
                return launch_cli_mode()
            elif modules_choice == "2":
                # Sniping de Token
                os.environ["BOT_MODE"] = "sniping"
                return launch_cli_mode()
            elif modules_choice == "3":
                # Lancer automatiquement le bot
                return launch_auto_mode()
            elif modules_choice == "4":
                # AI Assistant
                os.environ["BOT_MODE"] = "ai_assistant"
                return launch_cli_mode()
            elif modules_choice == "5":
                # Backtesting et Simulation
                os.environ["BOT_MODE"] = "backtesting"
                return launch_simulation_mode()
            elif modules_choice == "6":
                # Retour au menu principal
                continue
            else:
                print_colored("❌ Option invalide!", "RED")
                time.sleep(1)
        
        elif choice == "2":
            # Configurer les paramètres
            edit_configuration()
        
        elif choice == "3":
            # Afficher la configuration actuelle
            display_banner()
            print_colored("\nConfiguration actuelle:", "CYAN", bold=True)
            print_colored("============================================================\n", "CYAN")
            
            env_file = BASE_DIR / ".env"
            if env_file.exists():
                with open(env_file, "r") as f:
                    config_content = f.read()
                print(config_content)
            else:
                print_colored("❌ Fichier .env non trouvé!", "RED")
            
            input("\nAppuyez sur Entrée pour continuer...")
        
        elif choice == "4":
            # Statistiques et Logs
            show_stats()
        
        elif choice == "5":
            # Afficher les Modules Disponibles
            show_modules_info()
            # Après avoir affiché les informations des modules, nous continuons la boucle
            continue
        
        elif choice == "6":
            # Quitter
            print_colored("\nAu revoir!", "BLUE")
            return 0
        
        else:
            print_colored("❌ Option invalide!", "RED")
            time.sleep(1)
    
    # Cette ligne ne devrait jamais être atteinte, mais pour éviter l'erreur de linter
    # nous retournons une valeur par défaut
    return 0

def check_ai_capabilities():
    """Vérifie et affiche les fonctionnalités d'IA disponibles sur le système."""
    display_banner()
    
    print_colored("\nVérification des fonctionnalités d'IA disponibles", "CYAN", bold=True)
    print_colored("============================================================\n", "CYAN")
    
    # Vérifier TensorFlow
    try:
        import tensorflow as tf
        version = tf.__version__
        tensorflow_available = True
        print_colored(f"✅ TensorFlow {version} disponible", "GREEN")
    except ImportError:
        tensorflow_available = False
        print_colored("❌ TensorFlow non disponible", "RED")
    
    # Vérifier PyTorch
    try:
        import torch
        version = torch.__version__
        pytorch_available = True
        print_colored(f"✅ PyTorch {version} disponible", "GREEN")
    except ImportError:
        pytorch_available = False
        print_colored("❌ PyTorch non disponible", "RED")
    
    # Vérifier ONNX Runtime
    try:
        import onnxruntime
        version = onnxruntime.__version__
        onnx_available = True
        print_colored(f"✅ ONNX Runtime {version} disponible", "GREEN")
    except ImportError:
        onnx_available = False
        print_colored("❌ ONNX Runtime non disponible", "RED")
    
    # Vérifier LLaMA
    try:
        import llama_cpp
        llama_available = True
        print_colored("✅ LLaMA disponible", "GREEN")
    except ImportError:
        llama_available = False
        print_colored("❌ LLaMA non disponible", "RED")
    
    # Vérifier scikit-learn (pour les modèles de base)
    try:
        import sklearn
        version = sklearn.__version__
        sklearn_available = True
        print_colored(f"✅ scikit-learn {version} disponible", "GREEN")
    except ImportError:
        sklearn_available = False
        print_colored("❌ scikit-learn non disponible", "RED")
    
    print()
    print_colored("Fonctionnalités disponibles selon les bibliothèques installées:", "YELLOW", bold=True)
    
    if tensorflow_available or pytorch_available:
        print_colored("✅ Assistant IA: Disponible", "GREEN") if tensorflow_available and llama_available else print_colored("⚠️ Assistant IA: Limité (certaines fonctionnalités indisponibles)", "YELLOW")
        print_colored("✅ Analyse de contrats: Complète", "GREEN") if pytorch_available else print_colored("⚠️ Analyse de contrats: Basique", "YELLOW")
        print_colored("✅ Prédictions de marché: Disponibles", "GREEN") if tensorflow_available else print_colored("⚠️ Prédictions de marché: Basiques", "YELLOW")
        print_colored("✅ Optimisation de stratégie: Disponible", "GREEN") if tensorflow_available and pytorch_available else print_colored("⚠️ Optimisation de stratégie: Limitée", "YELLOW")
        print_colored("✅ Statistiques avancées: Disponibles", "GREEN") if tensorflow_available else print_colored("⚠️ Statistiques avancées: Basiques", "YELLOW")
    else:
        print_colored("⚠️ Fonctionnalités d'IA: Mode dégradé (fonctionnalités limitées)", "YELLOW")
    
    print()
    print_colored("Recommandations:", "CYAN", bold=True)
    
    if not tensorflow_available:
        print_colored("- Installation de TensorFlow: pip install tensorflow", "BLUE")
    if not pytorch_available:
        print_colored("- Installation de PyTorch: pip install torch torchvision torchaudio", "BLUE")
    if not onnx_available:
        print_colored("- Installation d'ONNX Runtime: pip install onnxruntime", "BLUE")
    if not llama_available:
        print_colored("- Installation de LLaMA: pip install llama-cpp-python", "BLUE")
    
    print()
    print_colored("Note: Le GBPBot s'adaptera automatiquement aux bibliothèques disponibles.", "YELLOW")
    print_colored("      Les fonctionnalités avancées d'IA seront limitées sans ces bibliothèques.", "YELLOW")
    print()

def parse_arguments():
    """Analyse les arguments de ligne de commande"""
    parser = argparse.ArgumentParser(description="GBPBot - Lanceur Unifié")
    
    # Mode de lancement
    parser.add_argument(
        "--mode",
        choices=["cli", "dashboard", "auto", "simulation", "production", "config"],
        default="cli",
        help="Mode de lancement"
    )
    
    # Options diverses
    parser.add_argument("--debug", action="store_true", help="Active les logs détaillés")
    parser.add_argument("--no-checks", action="store_true", help="Ignore les vérifications d'environnement")
    parser.add_argument("--config", help="Utilise un fichier de configuration spécifique")
    parser.add_argument("--check-ai", action="store_true", help="Vérifie les capacités IA disponibles et quitte")
    parser.add_argument("--bypass-imports", action="store_true", 
                        help="Contourne les erreurs d'importation liées à TensorFlow et autres dépendances")
    
    return parser.parse_args()

def main() -> int:
    """Point d'entrée principal"""
    try:
        # Parser les arguments
        args = parse_arguments()
        
        # Configurer le niveau de log
        if args.debug:
            logging.getLogger().setLevel(logging.DEBUG)
            logger.setLevel(logging.DEBUG)
            logger.debug("Mode debug activé")
        
        # Vérifier les capacités IA si demandé
        if args.check_ai:
            return check_ai_capabilities()
        
        # Afficher la bannière
        display_banner()
        
        # Si --bypass-imports est utilisé, installer le bouchon TensorFlow si nécessaire
        if args.bypass_imports:
            logger.info("Mode contournement d'imports activé. Configuration du bouchon TensorFlow...")
            tensorflow_compat_path = os.path.join(BASE_DIR, "gbpbot", "utils", "tensorflow_compat.py")
            
            # Créer le répertoire utils s'il n'existe pas
            os.makedirs(os.path.join(BASE_DIR, "gbpbot", "utils"), exist_ok=True)
            
            # Vérifier si le module existe déjà
            if not os.path.exists(tensorflow_compat_path):
                logger.info("Création du module de compatibilité TensorFlow...")
                with open(tensorflow_compat_path, "w") as f:
                    f.write("""\"\"\"
Module de compatibilité pour TensorFlow.

Ce module permet au GBPBot de fonctionner même si TensorFlow n'est pas installé.
\"\"\"

import logging
import sys

logger = logging.getLogger(__name__)

# Initialisation des variables
HAS_TENSORFLOW = False
tf = None

try:
    # Tenter d'importer TensorFlow
    import tensorflow as _tf
    tf = _tf
    HAS_TENSORFLOW = True
    logger.info(f"TensorFlow importé avec succès (version: {tf.__version__})")
except ImportError:
    logger.warning("TensorFlow n'est pas disponible. Mode dégradé activé.")
    
    # Créer un module factice pour TensorFlow
    class TensorFlowMock:
        \"\"\"Classe factice pour simuler TensorFlow.\"\"\"
        
        def __init__(self):
            self.__version__ = "0.0.0-mock"
            self.keras = TensorFlowKerasMock()
            self.python = TensorFlowPythonMock()
            
        def __getattr__(self, name):
            logger.debug(f"Accès à l'attribut non-implémenté de TensorFlow: {name}")
            return MockAttribute()
    
    class TensorFlowKerasMock:
        \"\"\"Classe factice pour simuler tf.keras.\"\"\"
        
        def __getattr__(self, name):
            logger.debug(f"Accès à l'attribut non-implémenté de tf.keras: {name}")
            return MockAttribute()
    
    class TensorFlowPythonMock:
        \"\"\"Classe factice pour simuler tf.python.\"\"\"
        
        def __init__(self):
            # simuler le module pywrap_tensorflow qui cause l'erreur
            self.pywrap_tensorflow = MockAttribute()
            
        def __getattr__(self, name):
            logger.debug(f"Accès à l'attribut non-implémenté de tf.python: {name}")
            return MockAttribute()
    
    class MockAttribute:
        \"\"\"Classe générique pour simuler des attributs.\"\"\"
        
        def __init__(self, return_value=None):
            self.return_value = return_value
        
        def __call__(self, *args, **kwargs):
            logger.debug(f"Appel d'une fonction TensorFlow mocquée")
            return self.return_value if self.return_value is not None else self
        
        def __getattr__(self, name):
            logger.debug(f"Accès à l'attribut {name} sur un objet TensorFlow mocqué")
            return self
    
    # Créer l'instance factice de TensorFlow
    tf = TensorFlowMock()
""")
                logger.info("Module de compatibilité TensorFlow créé avec succès")
            else:
                logger.info("Module de compatibilité TensorFlow déjà présent")
            
            # Créer un fichier __init__.py s'il n'existe pas
            init_path = os.path.join(BASE_DIR, "gbpbot", "utils", "__init__.py")
            if not os.path.exists(init_path):
                with open(init_path, "w") as f:
                    f.write("# Module d'utilitaires pour GBPBot\n")
        
        # Vérifier l'environnement sauf si --no-checks est utilisé
        env_ok = True
        if not args.no_checks:
            env_ok = check_environment()
            if not env_ok:
                logger.warning("Problèmes détectés dans l'environnement. Le bot pourrait ne pas fonctionner correctement.")
                if not Confirm.ask("Continuer malgré les problèmes détectés?"):
                    return 1
        
        # Déterminer et lancer le mode approprié
        if not args.mode:
            # Mode interactif
            choice = show_menu()
            return process_cli_interaction()
        elif args.mode == "cli":
            return launch_cli_mode()
        elif args.mode == "dashboard":
            return launch_dashboard_mode()
        elif args.mode == "auto":
            return launch_auto_mode()
        elif args.mode == "simulation":
            return launch_simulation_mode()
        else:
            logger.error(f"Mode non reconnu: {args.mode}")
            return 1
    
    except KeyboardInterrupt:
        print_colored("\nOpération annulée par l'utilisateur.", "YELLOW")
        return 0
    except Exception as e:
        logger.error(f"Erreur inattendue: {str(e)}")
        traceback.print_exc()
        print_colored(f"\nUne erreur inattendue s'est produite: {str(e)}", "RED", True)
        return 1

if __name__ == "__main__":
    sys.exit(main()) 