#!/usr/bin/env python
"""
Script pont pour GBPBot CLI
===========================

Ce script sert de pont pour lancer l'interface CLI de GBPBot quand l'interface complète
ne peut pas être chargée en raison de dépendances manquantes.

Il propose un menu limité mais fonctionnel pour interagir avec le système.
"""

import os
import sys
import platform
import subprocess
from pathlib import Path
import importlib
import asyncio
import importlib.util
import traceback

# Configuration des couleurs pour le terminal
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

def print_colored(message, color="GREEN", bold=False):
    """Affiche un message coloré dans le terminal"""
    prefix = COLORS.get(color.upper(), "")
    if bold:
        prefix += COLORS["BOLD"]
    suffix = COLORS["END"]
    print(f"{prefix}{message}{suffix}")

def display_banner():
    """Affiche la bannière ASCII du GBPBot"""
    banner = f"""
{COLORS["BLUE"]}{COLORS["BOLD"]}    ██████╗ ██████╗ ██████╗ ██████╗  ██████╗ ████████╗
    ██╔════╝ ██╔══██╗██╔══██╗██╔══██╗██╔═══██╗╚══██╔══╝
    ██║  ███╗██████╔╝██████╔╝██████╔╝██║   ██║   ██║   
    ██║   ██║██╔══██╗██╔═══╝ ██╔══██╗██║   ██║   ██║   
    ╚██████╔╝██████╔╝██║     ██████╔╝╚██████╔╝   ██║   
     ╚═════╝ ╚═════╝ ╚═╝     ╚═════╝  ╚═════╝    ╚═╝   {COLORS["END"]}
{COLORS["CYAN"]}    ================================================
    Trading Bot Ultra-Rapide pour MEME Coins
    Solana | AVAX | Sonic
    ================================================{COLORS["END"]}
    """
    print(banner)

def clear_screen():
    """Efface l'écran du terminal selon le système d'exploitation"""
    if platform.system() == "Windows":
        os.system("cls")
    else:
        os.system("clear")

def install_dependencies():
    """Propose d'installer les dépendances essentielles"""
    print_colored("\n=== Installation des dépendances ===", "BLUE", True)
    print_colored("Choisissez une option d'installation:", "CYAN")
    print_colored("1. Installation minimale (strict minimum pour lancer l'interface)", "CYAN")
    print_colored("2. Installation standard (pour la plupart des fonctionnalités)", "CYAN") 
    print_colored("3. Installation complète (incluant l'Agent IA et toutes les dépendances)", "CYAN")
    print_colored("4. Installation du package gbpbot (résout les problèmes d'import)", "CYAN")
    print_colored("5. Retour au menu principal", "CYAN")
    
    print("\n")
    option = input("Votre choix: ")
    
    if option == "5":
        return False
    
    if option not in ["1", "2", "3", "4"]:
        print_colored("Option invalide!", "RED")
        input("\nAppuyez sur Entrée pour continuer...")
        return False
    
    # Option 4: Installer le package gbpbot en mode développement
    if option == "4":
        print_colored("\nInstallation du package GBPBot en mode développement...", "BLUE")
        print_colored("Cette opération va installer le package directement depuis le dossier courant.", "CYAN")
        print_colored("Cela résoudra les problèmes d'importation de modules.", "CYAN")
        
        choice = input("Voulez-vous continuer? (o/n): ").lower()
        if choice != 'o' and choice != 'oui':
            print_colored("Installation annulée.", "YELLOW")
            return False
        
        try:
            print_colored("\nInstallation du package GBPBot...", "BLUE")
            
            # Créer un environnement Python avec les variables d'environnement nécessaires
            env = os.environ.copy()
            current_dir = os.path.abspath(os.path.dirname(__file__))
            
            # Ajouter le répertoire courant au PYTHONPATH pour l'installation
            if "PYTHONPATH" in env:
                env["PYTHONPATH"] = current_dir + os.pathsep + env["PYTHONPATH"]
            else:
                env["PYTHONPATH"] = current_dir
            
            # Essayer d'installer le package en mode développement
            result = subprocess.call([sys.executable, "-m", "pip", "install", "-e", ".", "--no-deps"], env=env)
            
            if result == 0:
                print_colored("\nPackage GBPBot installé avec succès!", "GREEN")
                print_colored("Les problèmes d'importation devraient maintenant être résolus.", "GREEN")
                return True
            else:
                print_colored("\nÉchec de l'installation du package.", "RED")
                print_colored("Tentative d'installation des dépendances essentielles...", "YELLOW")
                # Continuer avec l'installation des dépendances essentielles
        except Exception as e:
            print_colored(f"\nErreur lors de l'installation du package: {e}", "RED")
            print_colored("Tentative d'installation des dépendances essentielles...", "YELLOW")
    
    # Définir les packages selon l'option choisie
    if option == "1":
        # Installation minimale (strict minimum pour fonctionner)
        essential_deps = [
            "python-dotenv", 
            "web3", 
            "solana==0.30.2", 
            "rich", 
            "loguru", 
            "requests", 
            "websockets<11.0,>=9.0", 
            "asyncio", 
            "psutil",
            "anchorpy==0.17.0",
            "base58"
        ]
        desc = "minimale"
    elif option == "2":
        # Installation standard
        essential_deps = [
            "python-dotenv", 
            "web3", 
            "solana==0.30.2", 
            "rich", 
            "loguru", 
            "requests", 
            "websockets<11.0,>=9.0", 
            "click", 
            "psutil", 
            "numpy", 
            "pandas",
            "matplotlib", 
            "schedule", 
            "pytz", 
            "python-dateutil", 
            "tqdm", 
            "retry",
            "tenacity", 
            "cryptography", 
            "pyyaml",
            "anchorpy==0.17.0",
            "base58",
            "asyncio"
        ]
        desc = "standard"
    else:  # option 3 - Installation complète
        # Vérifier si requirements.txt existe
        if os.path.exists("requirements.txt"):
            print_colored("\nInstallation des dépendances principales depuis requirements.txt...", "BLUE")
            try:
                result = subprocess.call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
                if result == 0:
                    print_colored("Dépendances principales installées avec succès!", "GREEN")
                else:
                    print_colored("Échec de l'installation de certaines dépendances principales.", "YELLOW")
            except Exception as e:
                print_colored(f"Erreur lors de l'installation des dépendances principales: {str(e)}", "RED")
        
        # Vérifier si requirements-agent.txt existe
        if os.path.exists("requirements-agent.txt"):
            print_colored("\nInstallation des dépendances de l'Agent IA depuis requirements-agent.txt...", "BLUE")
            try:
                result = subprocess.call([sys.executable, "-m", "pip", "install", "-r", "requirements-agent.txt"])
                if result == 0:
                    print_colored("Dépendances de l'Agent IA installées avec succès!", "GREEN")
                else:
                    print_colored("Échec de l'installation de certaines dépendances de l'Agent IA.", "YELLOW")
            except Exception as e:
                print_colored(f"Erreur lors de l'installation des dépendances de l'Agent IA: {str(e)}", "RED")
        
        input("\nAppuyez sur Entrée pour continuer...")
        return True
    
    print_colored(f"\nInstallation {desc} des dépendances...", "BLUE")
    print_colored("Cette opération va installer les packages Python nécessaires au fonctionnement du GBPBot.", "CYAN")
    
    choice = input("Voulez-vous continuer? (o/n): ").lower()
    if choice != 'o' and choice != 'oui':
        print_colored("Installation annulée.", "YELLOW")
        return False
    
    # Installer en deux étapes pour garantir les plus importants
    try:
        # Étape 1 : installer les packages critiques individuellement
        critical_packages = ["python-dotenv", "web3", "solana==0.30.2", "rich", "loguru", "asyncio", "anchorpy==0.17.0", "base58"]
        for package in critical_packages:
            print_colored(f"Installation de {package}...", "BLUE")
            try:
                # Ignorer les erreurs par package pour continuer même si certains échouent
                subprocess.call([sys.executable, "-m", "pip", "install", package, "--no-deps"])
                try:
                    # Vérifier si le module peut être importé
                    module_name = package.split("==")[0].split("<")[0].split(">=")[0].strip()
                    importlib.import_module(module_name)
                    print_colored(f"✓ {package} installé et importé avec succès", "GREEN")
                except ImportError:
                    # Si l'import échoue, essayer d'installer avec les dépendances
                    print_colored(f"! {package} nécessite des dépendances, tentative d'installation complète...", "YELLOW")
                    subprocess.call([sys.executable, "-m", "pip", "install", package])
                    try:
                        importlib.import_module(module_name)
                        print_colored(f"✓ {package} maintenant installé et importé avec succès", "GREEN")
                    except ImportError:
                        print_colored(f"⚠ Impossible d'importer {module_name} malgré l'installation", "RED")
            except Exception as e:
                print_colored(f"Erreur lors de l'installation de {package}: {e}", "RED")
        
        # Étape 2 : installer les autres packages
        other_packages = [p for p in essential_deps if p not in critical_packages]
        if other_packages:
            print_colored("\nInstallation des dépendances secondaires...", "BLUE")
            try:
                for package in other_packages:
                    print_colored(f"Installation de {package}...", "CYAN")
                    try:
                        subprocess.call([sys.executable, "-m", "pip", "install", package])
                    except Exception as e:
                        print_colored(f"Erreur lors de l'installation de {package}: {e}", "YELLOW")
            except Exception as e:
                print_colored(f"Erreur lors de l'installation des dépendances secondaires: {e}", "RED")
        
        print_colored("\nInstallation des dépendances terminée!", "GREEN")
        return True
    except Exception as e:
        print_colored(f"Erreur lors de l'installation des dépendances: {e}", "RED")
        return False

def setup_env_file():
    """Crée ou configure le fichier .env"""
    env_path = Path(".env")
    env_example_path = Path(".env.example")
    
    # Si le fichier .env existe déjà, proposer des options
    if env_path.exists():
        clear_screen()
        print_colored("\n=== Configuration du fichier .env ===", "BLUE", True)
        print_colored("Le fichier .env existe déjà. Que souhaitez-vous faire?\n", "CYAN")
        
        print_colored("1. Afficher le contenu du fichier .env", "CYAN")
        print_colored("2. Réinitialiser le fichier .env à partir de .env.example", "CYAN")
        print_colored("3. Ouvrir le fichier .env dans l'éditeur par défaut", "CYAN")
        print_colored("4. Retour au menu principal", "CYAN")
        
        print("\n")
        option = input("Votre choix: ")
        
        if option == "1":
            try:
                with open(env_path, "r") as f:
                    content = f.read()
                
                clear_screen()
                print_colored("\n=== Contenu du fichier .env ===", "BLUE", True)
                print("\n" + content + "\n")
                input("Appuyez sur Entrée pour continuer...")
                return True
            except Exception as e:
                print_colored(f"Erreur lors de la lecture du fichier: {e}", "RED")
                input("Appuyez sur Entrée pour continuer...")
                return False
        
        elif option == "2":
            if not env_example_path.exists():
                print_colored("Erreur: Le fichier .env.example n'existe pas!", "RED")
                input("Appuyez sur Entrée pour continuer...")
                return False
            
            confirm = input("Êtes-vous sûr de vouloir réinitialiser le fichier .env? (o/n): ").lower()
            if confirm != 'o' and confirm != 'oui':
                print_colored("Opération annulée.", "YELLOW")
                input("Appuyez sur Entrée pour continuer...")
                return False
            
            try:
                # Créer une sauvegarde du fichier .env actuel
                from datetime import datetime
                backup_path = f".env.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                with open(env_path, "r") as src, open(backup_path, "w") as dst:
                    dst.write(src.read())
                
                # Réinitialiser à partir de .env.example
                with open(env_example_path, "r") as example, open(env_path, "w") as env:
                    env.write(example.read())
                
                print_colored(f"Fichier .env réinitialisé avec succès. Une sauvegarde a été créée: {backup_path}", "GREEN")
                input("Appuyez sur Entrée pour continuer...")
                return True
            except Exception as e:
                print_colored(f"Erreur lors de la réinitialisation du fichier: {e}", "RED")
                input("Appuyez sur Entrée pour continuer...")
                return False
        
        elif option == "3":
            try:
                # Ouvrir le fichier .env avec l'éditeur par défaut
                if platform.system() == "Windows":
                    os.system(f"notepad {env_path}")
                elif platform.system() == "Darwin":  # macOS
                    subprocess.run(["open", str(env_path)])
                else:  # Linux et autres
                    editors = ["nano", "vim", "vi", "gedit"]
                    for editor in editors:
                        try:
                            subprocess.run(["which", editor], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                            subprocess.run([editor, str(env_path)])
                            break
                        except subprocess.CalledProcessError:
                            continue
                
                print_colored("Fichier .env ouvert dans l'éditeur.", "GREEN")
                input("Appuyez sur Entrée pour continuer...")
                return True
            except Exception as e:
                print_colored(f"Erreur lors de l'ouverture du fichier: {e}", "RED")
                input("Appuyez sur Entrée pour continuer...")
                return False
        
        elif option == "4":
            return True
        
        else:
            print_colored("Option invalide!", "RED")
            input("Appuyez sur Entrée pour continuer...")
            return False
    
    # Si le fichier .env n'existe pas, le créer
    print_colored("Le fichier .env n'existe pas. Création en cours...", "YELLOW")
    
    if env_example_path.exists():
        try:
            with open(env_example_path, "r") as example, open(env_path, "w") as env:
                env.write(example.read())
            print_colored("Fichier .env créé à partir de .env.example.", "GREEN")
            
            # Proposer d'ouvrir le fichier dans l'éditeur
            edit = input("Souhaitez-vous ouvrir le fichier pour l'éditer? (o/n): ").lower()
            if edit == 'o' or edit == 'oui':
                if platform.system() == "Windows":
                    os.system(f"notepad {env_path}")
                elif platform.system() == "Darwin":  # macOS
                    subprocess.run(["open", str(env_path)])
                else:  # Linux et autres
                    editors = ["nano", "vim", "vi", "gedit"]
                    for editor in editors:
                        try:
                            subprocess.run(["which", editor], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                            subprocess.run([editor, str(env_path)])
                            break
                        except subprocess.CalledProcessError:
                            continue
            
            return True
        except Exception as e:
            print_colored(f"Erreur lors de la création du fichier .env: {e}", "RED")
            return False
    else:
        try:
            # Créer un fichier .env minimal
            with open(env_path, "w") as f:
                f.write("# Configuration GBPBot\n")
                f.write("DEBUG=false\n")
                f.write("LOG_LEVEL=INFO\n")
                f.write("MODE=TEST\n")
                f.write("SOLANA_ENABLED=true\n")
                f.write("AVALANCHE_ENABLED=true\n")
                f.write("SONIC_ENABLED=false\n")
                f.write("\n# Clés API (à remplacer par vos propres clés)\n")
                f.write("SOLANA_RPC_URL=https://api.mainnet-beta.solana.com\n")
                f.write("AVALANCHE_RPC_URL=https://api.avax.network/ext/bc/C/rpc\n")
                f.write("TELEGRAM_BOT_TOKEN=\n")
                f.write("TELEGRAM_CHAT_ID=\n")
            
            print_colored("Fichier .env minimal créé.", "YELLOW")
            print_colored("Vous devrez le configurer avec vos propres clés API.", "YELLOW")
            
            # Proposer d'ouvrir le fichier dans l'éditeur
            edit = input("Souhaitez-vous ouvrir le fichier pour l'éditer? (o/n): ").lower()
            if edit == 'o' or edit == 'oui':
                if platform.system() == "Windows":
                    os.system(f"notepad {env_path}")
                elif platform.system() == "Darwin":  # macOS
                    subprocess.run(["open", str(env_path)])
                else:  # Linux et autres
                    editors = ["nano", "vim", "vi", "gedit"]
                    for editor in editors:
                        try:
                            subprocess.run(["which", editor], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                            subprocess.run([editor, str(env_path)])
                            break
                        except subprocess.CalledProcessError:
                            continue
            
            return True
        except Exception as e:
            print_colored(f"Erreur lors de la création du fichier .env: {e}", "RED")
            return False

def show_menu():
    """Affiche le menu principal"""
    clear_screen()
    display_banner()
    
    print_colored("\n" + "=" * 60, "BLUE", True)
    print_colored("                    GBPBot - Menu Simplifié", "BLUE", True)
    print_colored("=" * 60 + "\n", "BLUE", True)
    
    print_colored("1. Installer les dépendances essentielles", "CYAN")
    print_colored("2. Configurer le fichier .env", "CYAN")
    print_colored("3. Lancer le bot standard (CLI complet)", "CYAN")
    print_colored("4. Visualiser les informations système", "CYAN")
    print_colored("5. Quitter", "CYAN")
    
    print("\n")
    return input("Votre choix: ")

def show_system_info():
    """Affiche les informations système"""
    clear_screen()
    print_colored("\n=== Informations Système ===", "BLUE", True)
    
    # Informations sur Python
    print_colored("\n[Python]", "CYAN", True)
    print_colored(f"Version: {platform.python_version()}", "CYAN")
    print_colored(f"Implémentation: {platform.python_implementation()}", "CYAN")
    print_colored(f"Chemin: {sys.executable}", "CYAN")
    
    # Informations sur le système d'exploitation
    print_colored("\n[Système d'exploitation]", "CYAN", True)
    print_colored(f"Système: {platform.system()}", "CYAN")
    print_colored(f"Version: {platform.version()}", "CYAN")
    print_colored(f"Architecture: {platform.architecture()[0]}", "CYAN")
    
    # Informations sur le répertoire de travail
    print_colored("\n[Répertoire de travail]", "CYAN", True)
    print_colored(f"Répertoire actuel: {os.getcwd()}", "CYAN")
    
    # Présence des fichiers importants
    print_colored("\n[Fichiers importants]", "CYAN", True)
    files_to_check = [".env", "gbpbot_cli.py", "gbpbot/cli_interface.py", "gbpbot/main.py"]
    for file in files_to_check:
        if os.path.exists(file):
            print_colored(f"{file}: ✓", "GREEN")
        else:
            print_colored(f"{file}: ✗", "RED")
    
    input("\nAppuyez sur Entrée pour revenir au menu...")

def create_asyncio_launcher():
    """Crée un script temporaire qui lance le CLI avec une boucle asyncio correctement configurée"""
    launcher_code = """#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import asyncio
import importlib.util
import traceback

# Configuration des logs 
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("gbpbot_launcher")

# Ajouter le répertoire courant au PYTHONPATH
current_dir = os.path.abspath(os.path.dirname(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)
    logger.info(f"Ajout de {current_dir} au PYTHONPATH")

# Configurer asyncio pour Windows
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    logger.info("Configuration de la politique d'événement WindowsSelectorEventLoopPolicy")

# Fonction pour corriger les imports problématiques
def fix_problematic_imports():
    try:
        # Vérifier si compatibility.py existe
        compat_file = os.path.join(current_dir, 'gbpbot', 'core', 'monitoring', 'compatibility.py')
        if os.path.exists(compat_file):
            # Créer un HardwareOptimizerCompat stub pour éviter l'erreur d'import circulaire
            module_name = "gbpbot.core.monitoring.compatibility"
            
            # Définir la classe stub
            class HardwareOptimizerCompatStub:
                def __init__(self, config=None):
                    self.config = config or {}
                    print("Stub HardwareOptimizerCompat initialisé")
                
                def apply_optimizations(self, target="all"):
                    print("Stub: Simulation d'optimisation matérielle")
                    return True
                
                def get_optimization_status(self):
                    return {"status": "optimized", "applied": ["stub_optimization"]}
                
                def get_recommendations(self):
                    return ["Stub: Aucune recommandation disponible"]
                
                @property
                def hardware_info(self):
                    return {
                        "cpu": {"cores": 4, "model": "Stub CPU"},
                        "memory": {"total": 8192, "available": 4096},
                        "gpu": {"model": "Stub GPU", "vram": 2048}
                    }
            
            # Injecter directement dans le module
            import types
            if module_name in sys.modules:
                # Si le module est déjà importé, ajouter la classe
                sys.modules[module_name].HardwareOptimizerCompat = HardwareOptimizerCompatStub
            else:
                # Créer un nouveau module avec la classe
                mod = types.ModuleType(module_name)
                mod.HardwareOptimizerCompat = HardwareOptimizerCompatStub
                sys.modules[module_name] = mod
            
            logger.info(f"Stub HardwareOptimizerCompat créé et injecté dans {module_name}")
    except Exception as e:
        logger.error(f"Erreur lors de la correction des imports: {e}")
        traceback.print_exc()

# Fonction pour importer dynamiquement un module
def import_module(module_path):
    try:
        spec = importlib.util.spec_from_file_location("module", module_path)
        if spec is None:
            logger.error(f"Impossible de créer une spécification pour {module_path}")
            return None
        module = importlib.util.module_from_spec(spec)
        if spec.loader:
            spec.loader.exec_module(module)
            return module
        logger.error(f"Le chargeur est None pour {module_path}")
        return None
    except Exception as e:
        logger.error(f"Erreur lors de l'importation de {module_path}: {e}")
        traceback.print_exc()
        return None

# Fonction principale asynchrone
async def main():
    # Corriger les imports problématiques avant d'importer gbpbot
    fix_problematic_imports()
    
    try:
        # Essayer d'abord avec cli.py
        if os.path.exists('gbpbot/cli.py'):
            logger.info("Tentative d'import de gbpbot.cli")
            import gbpbot.cli
            logger.info("Appel de gbpbot.cli.main()")
            gbpbot.cli.main()  # Fonction synchrone, pas besoin de await
            return True
        else:
            logger.warning("Module gbpbot.cli non trouvé")
    except ImportError as e:
        logger.error(f"Erreur d'importation: {e}")
        traceback.print_exc()
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution de gbpbot.cli: {e}")
        traceback.print_exc()
    
    # Essayer avec cli_interface.py
    try:
        if os.path.exists('gbpbot/cli_interface.py'):
            logger.info("Tentative d'import de gbpbot.cli_interface")
            import gbpbot.cli_interface
            logger.info("Appel de gbpbot.cli_interface.main()")
            gbpbot.cli_interface.main()  # Fonction synchrone, pas besoin de await
            return True
        else:
            logger.warning("Aucun module d'interface CLI trouvé.")
    except ImportError as e:
        logger.error(f"Erreur d'importation de cli_interface: {e}")
        traceback.print_exc()
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution de gbpbot.cli_interface: {e}")
        traceback.print_exc()
    
    # Si toutes les tentatives échouent, essayer le chargement dynamique
    logger.info("Tentative de chargement dynamique des modules")
    cli_path = os.path.join(current_dir, 'gbpbot', 'cli.py')
    if os.path.exists(cli_path):
        logger.info(f"Chargement dynamique de {cli_path}")
        cli_module = import_module(cli_path)
        if cli_module and hasattr(cli_module, 'main'):
            logger.info("Appel dynamique de cli_module.main()")
            cli_module.main()
            return True
    
    cli_interface_path = os.path.join(current_dir, 'gbpbot', 'cli_interface.py')
    if os.path.exists(cli_interface_path):
        logger.info(f"Chargement dynamique de {cli_interface_path}")
        cli_interface_module = import_module(cli_interface_path)
        if cli_interface_module and hasattr(cli_interface_module, 'main'):
            logger.info("Appel dynamique de cli_interface_module.main()")
            cli_interface_module.main()
            return True
    
    logger.error("Impossible de charger les modules CLI. Vérifiez l'installation.")
    return False

# Lancer la boucle asyncio
if __name__ == "__main__":
    try:
        logger.info("Démarrage de la boucle asyncio...")
        asyncio.run(main())
    except Exception as e:
        logger.error(f"Erreur lors de l'exécution de la boucle asyncio: {e}")
        traceback.print_exc()
"""
    
    # Créer le fichier temporaire
    launcher_path = "gbpbot_async_launcher.py"
    with open(launcher_path, "w", encoding="utf-8") as f:
        f.write(launcher_code)
    
    return launcher_path

def fix_missing_packages():
    """Installe les packages critiques pour éviter les erreurs connues"""
    print_colored("Installation des packages critiques pour éviter les erreurs connues...", "BLUE")
    
    # Packages critiques à installer
    critical_packages = [
        "anchorpy==0.17.0",
        "anchorpy-core>=0.1.2",  # Dépendance essentielle pour anchorpy
        "pyheck",                # Requis pour anchorpy
        "toolz",                 # Requis pour anchorpy
        "jsonrpcclient",         # Requis pour anchorpy
        "more-itertools",        # Requis pour anchorpy
        "py",                    # Requis pour anchorpy
        "toml"                   # Requis pour anchorpy
    ]
    
    for package in critical_packages:
        print_colored(f"Installation de {package}...", "CYAN")
        try:
            subprocess.call([sys.executable, "-m", "pip", "install", package])
        except Exception as e:
            print_colored(f"Erreur lors de l'installation de {package}: {e}", "YELLOW")
    
    # Essayer d'installer zstandard (souvent problématique sur Windows sans les outils de build)
    try:
        print_colored("Installation de zstandard==0.17.0...", "CYAN")
        subprocess.call([sys.executable, "-m", "pip", "install", "zstandard==0.17.0"])
    except:
        print_colored("L'installation de zstandard a échoué, certaines fonctionnalités peuvent ne pas être disponibles", "YELLOW")
    
    # Packages essentiels pour le fonctionnement minimal
    essential_packages = [
        "asyncio",
        "base58",
    ]
    
    for package in essential_packages:
        print_colored(f"Installation de {package}...", "CYAN")
        try:
            subprocess.call([sys.executable, "-m", "pip", "install", package])
        except:
            pass
    
    print_colored("Création d'un stub pour les fonctions manquantes...", "BLUE")

def fix_circular_imports():
    """
    Crée et utilise des stubs pour résoudre les importations circulaires.
    Particulièrement utile pour résoudre les problèmes d'importation de HardwareOptimizerCompat
    et ResourceMonitorCompat.
    """
    print_colored("Création d'un stub pour les fonctions manquantes...", "GREEN")
    
    # Vérifier si le dossier stubs existe
    stubs_dir = Path(os.path.abspath(".")) / "stubs"
    if not stubs_dir.exists():
        try:
            os.makedirs(stubs_dir, exist_ok=True)
            print_colored("Dossier 'stubs' créé avec succès", "GREEN")
        except Exception as e:
            print_colored(f"Erreur lors de la création du dossier 'stubs': {e}", "RED")
            return False
    
    # Vérifier si le fichier stub existe déjà
    stub_file = stubs_dir / "compatibility_stub.py"
    if not stub_file.exists():
        print_colored("Le fichier stub n'existe pas, veuillez le créer manuellement", "YELLOW")
        return False
    
    # Approche 1: Ajouter le dossier stubs au chemin d'importation
    if stubs_dir.as_posix() not in sys.path:
        sys.path.insert(0, stubs_dir.as_posix())
        print_colored(f"Dossier 'stubs' ajouté au chemin d'importation: {stubs_dir}", "GREEN")
    
    # Approche 2: Importer les stubs et les injecter dans sys.modules
    try:
        # Importer les stubs
        from stubs.compatibility_stub import (
            HardwareOptimizerCompat, ResourceMonitorCompat, 
            PerformanceMonitorCompat, get_resource_monitor,
            get_performance_monitor, get_hardware_optimizer
        )
        
        # Injecter les stubs dans sys.modules
        import types
        
        # Créer un module stub pour compatibility
        stub_module = types.ModuleType("gbpbot.core.monitoring.compatibility")
        
        # Ajouter les classes de stub au module
        stub_module.HardwareOptimizerCompat = HardwareOptimizerCompat
        stub_module.ResourceMonitorCompat = ResourceMonitorCompat
        stub_module.PerformanceMonitorCompat = PerformanceMonitorCompat
        
        # Ajouter les fonctions d'accès
        stub_module.get_resource_monitor = get_resource_monitor
        stub_module.get_performance_monitor = get_performance_monitor
        stub_module.get_hardware_optimizer = get_hardware_optimizer
        
        # Enregistrer le module dans sys.modules
        sys.modules["gbpbot.core.monitoring.compatibility"] = stub_module
        
        print_colored("Stubs injectés avec succès dans sys.modules", "GREEN")
        return True
    except Exception as e:
        print_colored(f"Erreur lors de l'injection des stubs: {e}", "RED")
        
        # Approche 3: Fallback - Injecter directement dans le fichier de compatibilité existant
        compat_file = Path(os.path.abspath(".")) / "gbpbot" / "core" / "monitoring" / "compatibility.py"
        if compat_file.exists():
            print_colored("Tentative de résolution directe des importations circulaires...", "YELLOW")
            
            try:
                # Lire le contenu actuel du fichier
                with open(compat_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Définir les classes minimales requises
                stub_code = '''
# Ces classes sont des stubs pour éviter les importations circulaires
class ResourceMonitorCompat:
    """Stub pour la classe ResourceMonitorCompat"""
    def __init__(self):
        pass
    
    def get_current_state(self):
        return {"cpu_usage": 0, "memory_usage": 0, "disk_usage": 0}
    
    def monitor_resources(self):
        return {"cpu": 0, "memory": 0}

class HardwareOptimizerCompat:
    """Stub pour la classe HardwareOptimizerCompat"""
    def __init__(self, config=None):
        self.config = config or {}
    
    def apply_optimizations(self, target="all"):
        return True
    
    def get_optimization_status(self):
        return {"status": "optimized"}
    
    def get_recommendations(self):
        return ["Aucune recommandation disponible"]
    
    @property
    def hardware_info(self):
        return {"cpu": {}, "memory": {}, "gpu": {}}

# Enregistrer ces classes comme disponibles globalement
globals()["ResourceMonitorCompat"] = ResourceMonitorCompat
globals()["HardwareOptimizerCompat"] = HardwareOptimizerCompat
'''
                
                # Si les stubs ne sont pas déjà dans le fichier, les ajouter
                if "class HardwareOptimizerCompat:" not in content:
                    # Ajouter les stubs au début du fichier (après les importations)
                    import_end = content.find('"""', content.find('"""') + 3) + 3
                    modified_content = content[:import_end] + "\n\n" + stub_code + content[import_end:]
                    
                    # Sauvegarder le fichier modifié
                    with open(compat_file, 'w', encoding='utf-8') as f:
                        f.write(modified_content)
                    
                    print_colored("Stubs injectés directement dans le fichier de compatibilité", "GREEN")
                    return True
                else:
                    print_colored("Stubs déjà présents dans le fichier de compatibilité", "CYAN")
                    return True
            except Exception as e:
                print_colored(f"Erreur lors de l'injection directe des stubs: {e}", "RED")
                return False
        
        return False

def check_and_install_missing_dependencies():
    """Vérifie et installe automatiquement les dépendances manquantes"""
    print_colored("Vérification des dépendances essentielles...", "BLUE")
    
    # Liste des dépendances critiques à vérifier
    critical_modules = [
        "dotenv", "web3", "solana", "rich", "loguru", 
        "asyncio", "websockets", "pandas", "numpy"
    ]
    
    # Vérifier les dépendances de l'Agent IA si requirements-agent.txt existe
    agent_dependencies_needed = False
    if os.path.exists("requirements-agent.txt"):
        print_colored("Vérification des dépendances de l'Agent IA...", "BLUE")
        try:
            with open("requirements-agent.txt", "r") as f:
                agent_deps = [line.strip().split(">=")[0].split("==")[0] for line in f if line.strip() and not line.startswith("#")]
            
            for module in agent_deps:
                try:
                    importlib.import_module(module)
                except ImportError:
                    agent_dependencies_needed = True
                    break
        except Exception as e:
            print_colored(f"Erreur lors de la vérification des dépendances de l'Agent IA: {str(e)}", "RED")
    
    # Vérifier les dépendances principales
    missing_modules = []
    for module in critical_modules:
        try:
            importlib.import_module(module)
        except ImportError:
            missing_modules.append(module)
    
    # Si des dépendances sont manquantes ou si les dépendances de l'Agent IA sont nécessaires
    if missing_modules or agent_dependencies_needed:
        print_colored("Certaines dépendances sont manquantes. Installation automatique...", "YELLOW")
        
        if missing_modules:
            print_colored(f"Modules manquants: {', '.join(missing_modules)}", "YELLOW")
            
            # Installer les dépendances principales
            try:
                if os.path.exists("requirements.txt"):
                    subprocess.call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
                else:
                    for module in missing_modules:
                        subprocess.call([sys.executable, "-m", "pip", "install", module])
            except Exception as e:
                print_colored(f"Erreur lors de l'installation des dépendances principales: {str(e)}", "RED")
                return False
        
        # Installer les dépendances de l'Agent IA si nécessaire
        if agent_dependencies_needed:
            print_colored("Installation des dépendances de l'Agent IA...", "YELLOW")
            try:
                subprocess.call([sys.executable, "-m", "pip", "install", "-r", "requirements-agent.txt"])
            except Exception as e:
                print_colored(f"Erreur lors de l'installation des dépendances de l'Agent IA: {str(e)}", "RED")
                print_colored("Le mode Agent IA pourrait ne pas fonctionner correctement.", "YELLOW")
        
        print_colored("Installation des dépendances terminée.", "GREEN")
        
        # Vérifier à nouveau
        still_missing = []
        for module in critical_modules:
            try:
                importlib.import_module(module)
            except ImportError:
                still_missing.append(module)
        
        if still_missing:
            print_colored(f"Attention: certains modules sont toujours manquants: {', '.join(still_missing)}", "RED")
            print_colored("Utilisez l'option 'Installer les dépendances' du menu principal pour une installation complète.", "YELLOW")
            input("\nAppuyez sur Entrée pour continuer...")
            return False
    else:
        print_colored("Toutes les dépendances essentielles sont installées.", "GREEN")
    
    return True

def main():
    """Fonction principale"""
    try:
        # Vérifier et installer automatiquement les dépendances manquantes au démarrage
        check_and_install_missing_dependencies()
        
        while True:
            choice = show_menu()
            
            if choice == "1":
                install_dependencies()
                input("\nAppuyez sur Entrée pour continuer...")
            elif choice == "2":
                setup_env_file()
                input("\nAppuyez sur Entrée pour continuer...")
            elif choice == "3":
                clear_screen()
                print_colored("\nLancement du CLI complet...", "BLUE")
                try:
                    # Configurer l'environnement Python correctement
                    current_dir = os.path.abspath(os.path.dirname(__file__))
                    
                    # Créer un environnement Python avec les variables d'environnement nécessaires
                    env = os.environ.copy()
                    
                    # Ajouter le répertoire courant au PYTHONPATH
                    if "PYTHONPATH" in env:
                        env["PYTHONPATH"] = current_dir + os.pathsep + env["PYTHONPATH"]
                    else:
                        env["PYTHONPATH"] = current_dir
                    
                    # Essayer de configurer le mode asyncio pour Windows
                    if platform.system() == "Windows":
                        env["PYTHONASYNCIODEBUG"] = "1"
                        env["PYTHONTRACEMALLOC"] = "1"
                    
                    # Lancer le script principal avec le PYTHONPATH configuré
                    print_colored("Configuration de l'environnement Python...", "BLUE")
                    print_colored(f"PYTHONPATH: {env['PYTHONPATH']}", "CYAN")
                    
                    # Installer les packages manquants et créer des stubs pour éviter les erreurs
                    fix_missing_packages()
                    
                    # Résoudre les importations circulaires
                    fix_circular_imports()
                    
                    # Créer un lanceur asynchrone temporaire
                    launcher_path = create_asyncio_launcher()
                    
                    # Lancer le script avec asyncio correctement configuré
                    print_colored("Lancement du bot avec gestion asyncio...", "BLUE")
                    result = subprocess.call([sys.executable, launcher_path], env=env)
                    
                    if result != 0:
                        print_colored("Échec du lancement du bot avec le lanceur asyncio.", "RED")
                        
                        # Tenter d'installer le package pour résoudre les problèmes d'import
                        print_colored("Installation temporaire du package gbpbot...", "BLUE")
                        try:
                            subprocess.call([sys.executable, "-m", "pip", "install", "-e", "."], env=env)
                            print_colored("Package gbpbot installé temporairement, nouveau lancement...", "GREEN")
                            subprocess.call([sys.executable, launcher_path], env=env)
                        except Exception as e:
                            print_colored(f"Erreur lors de l'installation du package: {e}", "RED")
                
                except Exception as e:
                    print_colored(f"Erreur lors du lancement: {e}", "RED")
                    print_colored("Diagnostic:", "YELLOW")
                    
                    # Vérifier que gbpbot existe
                    if not os.path.exists("gbpbot"):
                        print_colored("Le dossier gbpbot n'existe pas dans le répertoire courant!", "RED")
                    elif not os.path.exists("gbpbot/cli.py") and not os.path.exists("gbpbot/cli_interface.py"):
                        print_colored("Les fichiers d'interface CLI sont introuvables dans le dossier gbpbot!", "RED")
                    else:
                        print_colored("Structure du projet correcte, le problème vient probablement des dépendances.", "YELLOW")
                
                input("\nAppuyez sur Entrée pour continuer...")
            elif choice == "4":
                show_system_info()
            elif choice == "5":
                print_colored("\nAu revoir!", "BLUE")
                break
            else:
                print_colored("\nOption invalide! Veuillez réessayer.", "RED")
                input("\nAppuyez sur Entrée pour continuer...")
    except KeyboardInterrupt:
        print_colored("\n\nInterruption détectée. Fermeture du programme.", "YELLOW")
    except Exception as e:
        print_colored(f"\nUne erreur inattendue s'est produite: {e}", "RED")

if __name__ == "__main__":
    main() 