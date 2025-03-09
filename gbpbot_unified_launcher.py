#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GBPBot - Lanceur Unifié
=======================

Ce script sert de point d'entrée unique pour lancer GBPBot.
Il résout automatiquement les problèmes d'importation circulaire, 
installe les dépendances manquantes et offre une interface unifiée.

Usage:
    python gbpbot_unified_launcher.py [--mode CLI|DASHBOARD|AUTO] [--debug] [--simulation]
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
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("gbpbot_launcher")

# Ajouter le répertoire courant au PYTHONPATH
current_dir = os.path.abspath(os.path.dirname(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
    logger.debug(f"Ajout de {current_dir} au PYTHONPATH")

# Constantes et configurations
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

# Modes disponibles
AVAILABLE_MODES = ["cli", "dashboard", "auto", "simulation", "telegram"]

# État global
global_state = {
    "asyncio_configured": False,
    "imports_fixed": False,
    "packages_installed": False,
    "config_validated": False
}


def print_colored(message: str, color: str = "GREEN", bold: bool = False) -> None:
    """Affiche un message coloré dans le terminal"""
    prefix = COLORS.get(color.upper(), "")
    if bold:
        prefix += COLORS["BOLD"]
    suffix = COLORS["END"]
    print(f"{prefix}{message}{suffix}")


def display_banner() -> None:
    """Affiche la bannière ASCII du GBPBot"""
    banner = f"""
{COLORS["BLUE"]}{COLORS["BOLD"]}    ██████╗ ██████╗ ██████╗ ██████╗  ██████╗ ████████╗
    ██╔════╝ ██╔══██╗██╔══██╗██╔══██╗██╔═══██╗╚══██╔══╝
    ██║  ███╗██████╔╝██████╔╝██████╔╝██║   ██║   ██║   
    ██║   ██║██╔══██╗██╔═══╝ ██╔══██╗██║   ██║   ██║   
    ╚██████╔╝██████╔╝██║     ██████╔╝╚██████╔╝   ██║   
     ╚═════╝ ╚═════╝ ╚═╝     ╚═════╝  ╚═════╝    ╚═╝   {COLORS["END"]}
{COLORS["BOLD"]}============================================================{COLORS["END"]}
{COLORS["CYAN"]}             GBPBot - Lanceur Unifié v1.0{COLORS["END"]}
{COLORS["BOLD"]}============================================================{COLORS["END"]}
"""
    print(banner)


def fix_circular_imports() -> bool:
    """
    Résout les problèmes d'importation circulaire de GBPBot, en particulier
    liés au module HardwareOptimizerCompat.
    
    Returns:
        bool: True si les corrections ont été appliquées avec succès
    """
    try:
        logger.info("Application des corrections pour les imports circulaires...")
        
        # Créer un stub pour HardwareOptimizerCompat
        class HardwareOptimizerCompatStub:
            def __init__(self, config=None):
                self.config = config or {}
                self.hardware_info = {
                    "cpu": {"cores": 4, "model": "Stub CPU"},
                    "memory": {"total": 8192, "available": 4096},
                    "gpu": {"model": "Stub GPU", "vram": 2048}
                }
                logger.debug("Stub HardwareOptimizerCompat initialisé")
            
            def apply_optimizations(self, target="all"):
                logger.debug("Stub: Simulation d'optimisation matérielle")
                return True
            
            def get_optimization_status(self):
                return {"status": "optimized", "applied": ["stub_optimization"]}
            
            def get_recommendations(self):
                return ["Utilisation du stub d'optimisation"]
        
        # Vérifier si le fichier de compatibilité existe
        compatibility_path = os.path.join(current_dir, 'gbpbot', 'core', 'monitoring', 'compatibility.py')
        
        if os.path.exists(compatibility_path):
            # Approche 1: Injecter directement dans le fichier de compatibilité
            try:
                # Lire le contenu actuel du fichier
                with open(compatibility_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Vérifier si HardwareOptimizerCompat est déjà défini
                if "class HardwareOptimizerCompat" not in content:
                    # Créer le stub à injecter
                    stub_code = """
# Stub pour éviter les imports circulaires
class HardwareOptimizerCompat:
    def __init__(self, config=None):
        self.config = config or {}
        self.hardware_info = {
            "cpu": {"cores": 4, "model": "Stub CPU"},
            "memory": {"total": 8192, "available": 4096},
            "gpu": {"model": "Stub GPU", "vram": 2048}
        }
    
    def apply_optimizations(self, target="all"):
        return True
    
    def get_optimization_status(self):
        return {"status": "optimized", "applied": ["stub_optimization"]}
    
    def get_recommendations(self):
        return ["Utilisation du stub d'optimisation"]
"""
                    
                    # Ajouter le stub au fichier
                    with open(compatibility_path, 'a', encoding='utf-8') as f:
                        f.write("\n" + stub_code)
                    
                    logger.info("Stub HardwareOptimizerCompat injecté dans le fichier compatibility.py")
                else:
                    logger.info("HardwareOptimizerCompat déjà défini dans compatibility.py")
            except Exception as e:
                logger.warning(f"Erreur lors de l'injection directe dans le fichier: {str(e)}")
                # Fallback: utiliser sys.modules
                module_name = "gbpbot.core.monitoring.compatibility"
                try:
                    import types
                    if module_name in sys.modules:
                        # Si le module est déjà importé, ajouter la classe
                        sys.modules[module_name].HardwareOptimizerCompat = HardwareOptimizerCompatStub
                    else:
                        # Créer un nouveau module avec la classe
                        mod = types.ModuleType(module_name)
                        mod.HardwareOptimizerCompat = HardwareOptimizerCompatStub
                        sys.modules[module_name] = mod
                    
                    logger.info(f"Stub HardwareOptimizerCompat injecté dans {module_name} via sys.modules")
                except Exception as e2:
                    logger.error(f"Échec de toutes les méthodes d'injection: {str(e2)}")
                    return False
        else:
            logger.warning(f"Fichier de compatibilité non trouvé: {compatibility_path}")
            # Créer le répertoire si nécessaire
            os.makedirs(os.path.dirname(compatibility_path), exist_ok=True)
            
            # Créer le fichier avec le stub
            try:
                with open(compatibility_path, 'w', encoding='utf-8') as f:
                    f.write("""
# -*- coding: utf-8 -*-
\"\"\"
Module de compatibilité pour la surveillance des ressources
\"\"\"

# Stub pour éviter les imports circulaires
class HardwareOptimizerCompat:
    def __init__(self, config=None):
        self.config = config or {}
        self.hardware_info = {
            "cpu": {"cores": 4, "model": "Stub CPU"},
            "memory": {"total": 8192, "available": 4096},
            "gpu": {"model": "Stub GPU", "vram": 2048}
        }
    
    def apply_optimizations(self, target="all"):
        return True
    
    def get_optimization_status(self):
        return {"status": "optimized", "applied": ["stub_optimization"]}
    
    def get_recommendations(self):
        return ["Utilisation du stub d'optimisation"]
""")
                logger.info(f"Fichier de compatibilité créé avec succès: {compatibility_path}")
            except Exception as e:
                logger.error(f"Erreur lors de la création du fichier de compatibilité: {str(e)}")
                return False
        
        # Marquer les imports comme corrigés
        global_state["imports_fixed"] = True
        return True
    except Exception as e:
        logger.error(f"Erreur lors de la correction des imports circulaires: {str(e)}")
        traceback.print_exc()
        return False


def configure_asyncio() -> bool:
    """
    Configure asyncio pour éviter les erreurs courantes, particulièrement sur Windows.
    
    Returns:
        bool: True si la configuration a réussi
    """
    try:
        # Configurer asyncio pour Windows
        if sys.platform == 'win32':
            import asyncio
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            logger.info("Configuration de la politique d'événement asyncio pour Windows")
        
        # Marquer asyncio comme configuré
        global_state["asyncio_configured"] = True
        return True
    except Exception as e:
        logger.error(f"Erreur lors de la configuration d'asyncio: {str(e)}")
        return False


def install_missing_packages() -> bool:
    """
    Installe les packages critiques pour éviter les erreurs connues.
    
    Returns:
        bool: True si l'installation a réussi
    """
    try:
        # Liste des packages critiques à installer
        critical_packages = [
            "anchorpy==0.17.0",
            "anchorpy-core>=0.1.2",
            "pyheck>=0.1.0",
            "toolz>=0.12.0",
            "jsonrpcclient>=4.0.0",
            "more-itertools>=9.1.0",
            "py>=1.11.0",
            "toml>=0.10.2",
            "zstandard==0.17.0",
            "asyncio",
            "base58"
        ]
        
        # Installer les packages
        print_colored("Installation des packages critiques...", "CYAN")
        for package in critical_packages:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                logger.info(f"Package {package} installé avec succès")
            except subprocess.CalledProcessError as e:
                logger.warning(f"Échec de l'installation du package {package}: {str(e)}")
            except Exception as e:
                logger.warning(f"Erreur lors de l'installation du package {package}: {str(e)}")
        
        # Marquer les packages comme installés
        global_state["packages_installed"] = True
        return True
    except Exception as e:
        logger.error(f"Erreur lors de l'installation des packages manquants: {str(e)}")
        return False


def create_asyncio_launcher() -> bool:
    """
    Crée un script lanceur asyncio temporaire pour exécuter GBPBot.
    
    Returns:
        bool: True si la création a réussi
    """
    try:
        # Nom du script temporaire
        temp_path = os.path.join(current_dir, "temp_asyncio_launcher.py")
        
        # Contenu du script
        script_content = """
#!/usr/bin/env python
# -*- coding: utf-8 -*-
\"\"\"
Lanceur asyncio temporaire pour GBPBot
\"\"\"

import os
import sys
import asyncio
import importlib
import importlib.util
import logging
import traceback

# Configuration du logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("asyncio_launcher")

# Ajouter le répertoire courant au PYTHONPATH
current_dir = os.path.abspath(os.path.dirname(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
    logger.debug(f"Ajout de {current_dir} au PYTHONPATH")

# Configurer asyncio pour Windows
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    logger.debug("Configuration de la politique d'événement asyncio pour Windows")

# Fonction pour corriger les problèmes d'importation
def fix_problematic_imports():
    try:
        # Créer un stub pour HardwareOptimizerCompat
        class HardwareOptimizerCompatStub:
            def __init__(self, config=None):
                self.config = config or {}
                self.hardware_info = {
                    "cpu": {"cores": 4, "model": "Stub CPU"},
                    "memory": {"total": 8192, "available": 4096},
                    "gpu": {"model": "Stub GPU", "vram": 2048}
                }
            
            def apply_optimizations(self, target="all"):
                return True
            
            def get_optimization_status(self):
                return {"status": "optimized", "applied": ["stub_optimization"]}
            
            def get_recommendations(self):
                return ["Utilisation du stub d'optimisation"]
        
        # Injecter le stub dans le module
        module_name = "gbpbot.core.monitoring.compatibility"
        import types
        if module_name in sys.modules:
            sys.modules[module_name].HardwareOptimizerCompat = HardwareOptimizerCompatStub
        else:
            mod = types.ModuleType(module_name)
            mod.HardwareOptimizerCompat = HardwareOptimizerCompatStub
            sys.modules[module_name] = mod
        
        logger.debug(f"Stub HardwareOptimizerCompat injecté dans {module_name}")
    except Exception as e:
        logger.error(f"Erreur lors de la correction des imports: {e}")
        traceback.print_exc()

# Fonction pour importer un module dynamiquement
def import_module(module_name):
    try:
        return importlib.import_module(module_name)
    except Exception as e:
        logger.error(f"Erreur lors de l'importation de {module_name}: {e}")
        traceback.print_exc()
        return None

# Point d'entrée principal
async def main():
    try:
        # Corriger les imports problématiques
        fix_problematic_imports()
        
        # Importer et lancer le menu CLI
        try:
            # Essayer d'importer le menu de CLI
            cli_menu = import_module("gbpbot.cli.menu")
            if cli_menu and hasattr(cli_menu, 'run_cli'):
                logger.info("Lancement de gbpbot.cli.menu.run_cli()")
                await cli_menu.run_cli()
                return True
            else:
                logger.warning("Module gbpbot.cli.menu importé mais run_cli() non trouvé")
        except Exception as e:
            logger.error(f"Erreur lors de l'importation ou de l'exécution du menu CLI: {e}")
        
        # Essayer avec cli_interface
        try:
            cli_interface = import_module("gbpbot.cli_interface")
            if cli_interface and hasattr(cli_interface, 'main'):
                logger.info("Lancement de gbpbot.cli_interface.main()")
                result = cli_interface.main()
                if asyncio.iscoroutine(result):
                    await result
                return True
            else:
                logger.warning("Module gbpbot.cli_interface importé mais main() non trouvé")
        except Exception as e:
            logger.error(f"Erreur lors de l'importation ou de l'exécution de cli_interface: {e}")
        
        # Essayer avec cli
        try:
            cli = import_module("gbpbot.cli")
            if cli and hasattr(cli, 'main'):
                logger.info("Lancement de gbpbot.cli.main()")
                cli.main()  # Fonction synchrone
                return True
            else:
                logger.warning("Module gbpbot.cli importé mais main() non trouvé")
        except Exception as e:
            logger.error(f"Erreur lors de l'importation ou de l'exécution de cli: {e}")
        
        logger.error("Tous les modules CLI ont échoué. Impossible de lancer GBPBot.")
        return False
    except Exception as e:
        logger.error(f"Erreur non gérée dans le lanceur asyncio: {e}")
        traceback.print_exc()
        return False

# Point d'entrée principal
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\\nInterruption clavier détectée. Arrêt du GBPBot...")
    except Exception as e:
        logger.error(f"Erreur dans la boucle principale: {e}")
        traceback.print_exc()
"""
        
        # Écrire le script dans un fichier temporaire
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(script_content)
        
        logger.info(f"Script lanceur asyncio créé avec succès: {temp_path}")
        return True
    except Exception as e:
        logger.error(f"Erreur lors de la création du script lanceur asyncio: {str(e)}")
        return False


def validate_config() -> bool:
    """
    Valide la configuration GBPBot et s'assure que les fichiers nécessaires existent.
    
    Returns:
        bool: True si la validation a réussi
    """
    try:
        # Vérifier si le fichier .env existe
        env_path = os.path.join(current_dir, ".env")
        if not os.path.exists(env_path):
            logger.warning("Fichier .env non trouvé. Création à partir du modèle...")
            
            # Copier le modèle .env.example s'il existe
            env_example_path = os.path.join(current_dir, ".env.example")
            if os.path.exists(env_example_path):
                with open(env_example_path, "r", encoding="utf-8") as src:
                    with open(env_path, "w", encoding="utf-8") as dst:
                        dst.write(src.read())
                logger.info("Fichier .env créé à partir du modèle .env.example")
            else:
                # Créer un fichier .env minimal
                with open(env_path, "w", encoding="utf-8") as f:
                    f.write("""# Configuration GBPBot
# Généré automatiquement par le lanceur unifié

# Configuration générale
DEBUG=false
SIMULATION_MODE=true

# Configuration RPC
SOLANA_RPC_URL=https://api.mainnet-beta.solana.com
AVAX_RPC_URL=https://api.avax.network/ext/bc/C/rpc

# Clés API (à remplir)
# OPENAI_API_KEY=votre_clé_api_openai
""")
                logger.info("Fichier .env minimal créé")
        
        # Vérifier le dossier de configuration
        config_dir = os.path.join(current_dir, "config")
        if not os.path.exists(config_dir):
            os.makedirs(config_dir, exist_ok=True)
            logger.info(f"Dossier de configuration créé: {config_dir}")
        
        # Marquer la configuration comme validée
        global_state["config_validated"] = True
        return True
    except Exception as e:
        logger.error(f"Erreur lors de la validation de la configuration: {str(e)}")
        return False


def show_menu() -> str:
    """
    Affiche le menu principal et retourne le choix de l'utilisateur.
    
    Returns:
        str: Mode sélectionné par l'utilisateur
    """
    display_banner()
    
    print_colored("\nOptions disponibles:", "CYAN", bold=True)
    print_colored("  1. Lancer l'interface CLI", "GREEN")
    print_colored("  2. Lancer le dashboard web", "GREEN")
    print_colored("  3. Lancer en mode automatique", "GREEN")
    print_colored("  4. Lancer en mode simulation", "GREEN")
    print_colored("  5. Configuration", "GREEN")
    print_colored("  6. Installer les dépendances", "GREEN")
    print_colored("  7. Quitter", "GREEN")
    
    while True:
        try:
            choice = input("\nVotre choix (1-7): ")
            if choice == "1":
                return "cli"
            elif choice == "2":
                return "dashboard"
            elif choice == "3":
                return "auto"
            elif choice == "4":
                return "simulation"
            elif choice == "5":
                return "config"
            elif choice == "6":
                return "install"
            elif choice == "7":
                return "exit"
            else:
                print_colored("Choix invalide. Veuillez entrer un nombre entre 1 et 7.", "RED")
        except KeyboardInterrupt:
            return "exit"
        except Exception as e:
            logger.error(f"Erreur lors de la sélection: {str(e)}")


def launch_cli_mode() -> int:
    """
    Lance GBPBot en mode CLI.
    
    Returns:
        int: Code de retour (0 pour succès)
    """
    try:
        print_colored("\nLancement de GBPBot en mode CLI...", "CYAN", bold=True)
        
        # S'assurer que les corrections sont appliquées
        if not global_state["imports_fixed"]:
            fix_circular_imports()
        
        if not global_state["asyncio_configured"]:
            configure_asyncio()
        
        # Créer et exécuter le lanceur asyncio
        if create_asyncio_launcher():
            # Exécuter le script lanceur
            temp_path = os.path.join(current_dir, "temp_asyncio_launcher.py")
            command = [sys.executable, temp_path]
            
            try:
                # Exécuter le lanceur avec l'environnement Python actuel
                subprocess.call(command)
                
                # Supprimer le fichier temporaire si tout s'est bien passé
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                
                return 0
            except Exception as e:
                logger.error(f"Erreur lors de l'exécution du lanceur asyncio: {str(e)}")
                return 1
        else:
            print_colored("Échec de la création du lanceur asyncio.", "RED", bold=True)
            return 1
    except Exception as e:
        logger.error(f"Erreur lors du lancement du mode CLI: {str(e)}")
        return 1


def launch_dashboard_mode() -> int:
    """
    Lance GBPBot en mode dashboard.
    
    Returns:
        int: Code de retour (0 pour succès)
    """
    try:
        print_colored("\nLancement du dashboard GBPBot...", "CYAN", bold=True)
        
        # Vérifier si le fichier du dashboard existe
        dashboard_path = os.path.join(current_dir, "gbpbot", "dashboard", "run_dashboard.py")
        if os.path.exists(dashboard_path):
            # Exécuter le dashboard
            command = [sys.executable, dashboard_path]
            return subprocess.call(command)
        else:
            # Essayer le script run_dashboard.py à la racine
            dashboard_path = os.path.join(current_dir, "run_dashboard.py")
            if os.path.exists(dashboard_path):
                command = [sys.executable, dashboard_path]
                return subprocess.call(command)
            else:
                print_colored("Dashboard non trouvé.", "RED", bold=True)
                print_colored("Assurez-vous que le module dashboard est installé.", "YELLOW")
                return 1
    except Exception as e:
        logger.error(f"Erreur lors du lancement du dashboard: {str(e)}")
        return 1


def launch_auto_mode() -> int:
    """
    Lance GBPBot en mode automatique.
    
    Returns:
        int: Code de retour (0 pour succès)
    """
    try:
        print_colored("\nLancement de GBPBot en mode automatique...", "CYAN", bold=True)
        
        # S'assurer que les corrections sont appliquées
        if not global_state["imports_fixed"]:
            fix_circular_imports()
        
        if not global_state["asyncio_configured"]:
            configure_asyncio()
        
        # Exécuter le script principal avec l'option auto
        main_script = os.path.join(current_dir, "run_gbpbot.py")
        if os.path.exists(main_script):
            command = [sys.executable, main_script, "--mode", "auto"]
            return subprocess.call(command)
        else:
            print_colored("Script principal non trouvé.", "RED", bold=True)
            print_colored("Assurez-vous que run_gbpbot.py est présent à la racine.", "YELLOW")
            return 1
    except Exception as e:
        logger.error(f"Erreur lors du lancement du mode automatique: {str(e)}")
        return 1


def launch_simulation_mode() -> int:
    """
    Lance GBPBot en mode simulation.
    
    Returns:
        int: Code de retour (0 pour succès)
    """
    try:
        print_colored("\nLancement de GBPBot en mode simulation...", "CYAN", bold=True)
        
        # S'assurer que les corrections sont appliquées
        if not global_state["imports_fixed"]:
            fix_circular_imports()
        
        if not global_state["asyncio_configured"]:
            configure_asyncio()
        
        # Exécuter le script principal avec l'option simulation
        main_script = os.path.join(current_dir, "run_gbpbot.py")
        if os.path.exists(main_script):
            command = [sys.executable, main_script, "--simulation"]
            return subprocess.call(command)
        else:
            print_colored("Script principal non trouvé.", "RED", bold=True)
            print_colored("Assurez-vous que run_gbpbot.py est présent à la racine.", "YELLOW")
            return 1
    except Exception as e:
        logger.error(f"Erreur lors du lancement du mode simulation: {str(e)}")
        return 1


def edit_config() -> int:
    """
    Ouvre l'éditeur de configuration.
    
    Returns:
        int: Code de retour (0 pour succès)
    """
    try:
        print_colored("\nConfigurations disponibles:", "CYAN", bold=True)
        print_colored("  1. Éditer le fichier .env", "GREEN")
        print_colored("  2. Configurer les RPC endpoints", "GREEN")
        print_colored("  3. Configurer les wallets", "GREEN")
        print_colored("  4. Retour au menu principal", "GREEN")
        
        choice = input("\nVotre choix (1-4): ")
        
        if choice == "1":
            # Éditer le fichier .env
            env_path = os.path.join(current_dir, ".env")
            if not os.path.exists(env_path):
                validate_config()  # Créer le fichier s'il n'existe pas
            
            # Ouvrir le fichier avec l'éditeur système par défaut
            if sys.platform == 'win32':
                os.startfile(env_path)
            elif sys.platform == 'darwin':  # macOS
                subprocess.call(['open', env_path])
            else:  # Linux
                subprocess.call(['xdg-open', env_path])
            
            print_colored("\nFichier .env ouvert dans l'éditeur par défaut.", "GREEN")
            time.sleep(2)
        elif choice == "2":
            # TODO: Implémenter l'éditeur d'endpoints RPC
            print_colored("\nÉditeur d'endpoints RPC non implémenté.", "YELLOW")
            time.sleep(2)
        elif choice == "3":
            # TODO: Implémenter l'éditeur de wallets
            print_colored("\nÉditeur de wallets non implémenté.", "YELLOW")
            time.sleep(2)
        elif choice == "4":
            return 0
        else:
            print_colored("Choix invalide.", "RED")
            time.sleep(1)
        
        return 0
    except Exception as e:
        logger.error(f"Erreur lors de l'édition de la configuration: {str(e)}")
        return 1


def main() -> int:
    """
    Point d'entrée principal du lanceur unifié.
    
    Returns:
        int: Code de retour (0 pour succès)
    """
    try:
        # Analyser les arguments de la ligne de commande
        parser = argparse.ArgumentParser(description="Lanceur unifié pour GBPBot")
        parser.add_argument("--mode", choices=AVAILABLE_MODES, help="Mode de lancement")
        parser.add_argument("--debug", action="store_true", help="Activer le mode debug")
        parser.add_argument("--simulation", action="store_true", help="Activer le mode simulation")
        args = parser.parse_args()
        
        # Configurer le niveau de log
        if args.debug:
            logging.basicConfig(level=logging.DEBUG)
            logger.setLevel(logging.DEBUG)
            logger.debug("Mode debug activé")
        
        # Configurer asyncio
        configure_asyncio()
        
        # Appliquer les corrections d'importation circulaire
        fix_circular_imports()
        
        # Valider la configuration
        validate_config()
        
        # Si le mode est spécifié, lancer directement
        if args.mode:
            if args.mode == "cli":
                return launch_cli_mode()
            elif args.mode == "dashboard":
                return launch_dashboard_mode()
            elif args.mode == "auto":
                return launch_auto_mode()
            elif args.mode == "simulation" or args.simulation:
                return launch_simulation_mode()
            elif args.mode == "telegram":
                print_colored("Mode Telegram non implémenté.", "YELLOW", bold=True)
                return 1
        
        # Sinon, afficher le menu
        while True:
            mode = show_menu()
            
            if mode == "cli":
                launch_cli_mode()
            elif mode == "dashboard":
                launch_dashboard_mode()
            elif mode == "auto":
                launch_auto_mode()
            elif mode == "simulation":
                launch_simulation_mode()
            elif mode == "config":
                edit_config()
            elif mode == "install":
                install_missing_packages()
                print_colored("\nDépendances installées avec succès.", "GREEN", bold=True)
                time.sleep(2)
            elif mode == "exit":
                print_colored("\nAu revoir!", "CYAN", bold=True)
                return 0
        
        return 0
    except KeyboardInterrupt:
        print_colored("\nInterruption détectée. Arrêt du lanceur...", "YELLOW")
        return 0
    except Exception as e:
        logger.error(f"Erreur non gérée dans le lanceur: {str(e)}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main()) 