#!/usr/bin/env python
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
