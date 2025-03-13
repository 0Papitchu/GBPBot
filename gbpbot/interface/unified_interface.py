# Unified Interface for GBPBot
import asyncio
import logging
import os
from typing import Dict, Any, Optional, Tuple

from gbpbot.cli_interface import CLIInterface

logger = logging.getLogger(__name__)

class UnifiedInterface:
    """
    Interface unifiée pour GBPBot.
    
    Cette classe fournit une interface simplifiée pour interagir avec les différents
    modules de GBPBot. Elle utilise l'interface CLI existante pour la compatibilité.
    """
    
    def __init__(self):
        """Initialisation de l'interface unifiée."""
        self.cli_interface = CLIInterface()
        self.config = {}
        self.running_modules = {}
        self.initialized = False

    async def initialize(self):
        """Initialise la configuration."""
        logger.info("Initialisation de l'interface unifiée...")
        
        # Chargement de la configuration
        self.config = self.cli_interface._load_user_config()
        
        # Initialisation de l'interface CLI
        self.cli_interface.display_welcome()
        
        self.initialized = True
        logger.info("Interface unifiée initialisée avec succès")

    async def start(self):
        """Démarre l'interface unifiée."""
        if not self.initialized:
            await self.initialize()
        await self.cli_interface.run()

    async def launch_module(self, module_name: str, mode: str = "live", autonomy_level: str = "semi-autonome") -> Tuple[bool, str]:
        """
        Lance un module spécifique via l'interface CLI.
        
        Cette méthode utilise directement les fonctionnalités de l'interface CLI
        pour démarrer un module spécifique sans nécessiter d'interaction utilisateur.
        
        Args:
            module_name: Nom du module à lancer ("Arbitrage", "Sniping", "MEV/Frontrunning", etc.)
            mode: Mode d'exécution ("test", "simulation", "live")
            autonomy_level: Niveau d'autonomie ("semi-autonome", "autonome", "hybride")
            
        Returns:
            Tuple[bool, str]: (Succès, Message d'information ou d'erreur)
        """
        logger.info(f"Lancement du module {module_name} en mode {mode}")
        
        if not self.initialized:
            await self.initialize()
        
        # Mapping des noms de modules aux valeurs numériques utilisées par CLI
        module_mapping = {
            "Arbitrage": 1,
            "Sniping": 2,
            "Mode Automatique": 3,
            "MEV/Frontrunning": 4,
            "AI Assistant": 5,
            "Backtesting": 6
        }
        
        # Mapping des modes
        mode_mapping = {
            "test": 1,
            "simulation": 2,
            "live": 3
        }
        
        # Mapping des niveaux d'autonomie
        autonomy_mapping = {
            "semi-autonome": 1,
            "autonome": 2,
            "hybride": 3
        }
        
        if module_name not in module_mapping:
            return False, f"Module inconnu: {module_name}"
            
        if mode not in mode_mapping:
            return False, f"Mode inconnu: {mode}"
            
        if autonomy_level not in autonomy_mapping:
            return False, f"Niveau d'autonomie inconnu: {autonomy_level}"
        
        # Configuration temporaire pour ce lancement
        temp_config = self.config.copy()
        temp_config["mode"] = mode.upper()
        
        try:
            # Cette partie est normalement gérée par l'interface CLI
            # Mais nous allons implémenter cela directement ici pour éviter les dépendances
            module_id = module_mapping[module_name]
            mode_id = mode_mapping[mode]
            autonomy_id = autonomy_mapping[autonomy_level]
            
            # Initialisons directement le bot sans passer par l'interface CLI
            # Nous utilisons les importations ici pour éviter les dépendances circulaires
            
            # Cette partie lance directement le module sans passer par le menu
            instance = None
            
            if module_id == 1:  # Arbitrage
                from gbpbot.modules.arbitrage_engine import ArbitrageEngine
                instance = ArbitrageEngine(config=temp_config)
            
            elif module_id == 2:  # Sniping
                from gbpbot.modules.token_sniper import TokenSniper
                instance = TokenSniper(config=temp_config)
            
            elif module_id == 3:  # Mode Automatique
                from gbpbot.ai.agent_manager import create_agent_manager
                
                # Pour le mode automatique, nous avons besoin de gérer l'approbation
                # de l'utilisateur en fonction du niveau d'autonomie
                if autonomy_id == 1:  # Semi-autonome
                    require_approval = True
                elif autonomy_id == 2:  # Autonome
                    require_approval = False
                else:  # Hybride
                    require_approval = "hybrid"
                
                instance = create_agent_manager(
                    autonomy_level=autonomy_level,
                    require_approval_callback=lambda op, params: True if not require_approval else None
                )
            
            elif module_id == 4:  # MEV/Frontrunning
                from gbpbot.strategies.mev import MEVStrategy
                instance = MEVStrategy(config=temp_config)
            
            elif module_id == 5:  # AI Assistant
                # On suppose que ce module existe mais nous ne l'importons pas pour éviter
                # des erreurs si le module n'est pas encore implémenté
                return False, "Module AI Assistant pas encore implémenté dans l'interface unifiée"
            
            elif module_id == 6:  # Backtesting
                # Pour le backtesting, nous allons simplement retourner un message de succès
                return True, "Configuration du backtesting terminée"
            
            # Enregistrement du module en cours d'exécution
            if instance:
                self.running_modules[module_name] = instance
                
                # Démarrage avec le mode approprié
                if hasattr(instance, "start"):
                    await instance.start()
                    return True, f"Module {module_name} exécuté avec succès"
                
                # Si start n'existe pas, essayons run
                if hasattr(instance, "run"):
                    await instance.run()
                    return True, f"Module {module_name} exécuté avec succès"
                
                return True, f"Module {module_name} initialisé avec succès, mais aucune méthode start/run trouvée"
            
            return False, "Échec d'initialisation du module"
        
        except Exception as e:
            logger.error(f"Erreur lors du lancement du module {module_name}: {str(e)}")
            return False, f"Erreur: {str(e)}"

    async def stop_module(self, module_name: str) -> Tuple[bool, str]:
        """
        Arrête un module en cours d'exécution.
        
        Args:
            module_name: Nom du module à arrêter
            
        Returns:
            Tuple[bool, str]: (Succès, Message d'information ou d'erreur)
        """
        if module_name not in self.running_modules:
            return False, f"Module {module_name} non actif"
        
        try:
            instance = self.running_modules[module_name]
            if hasattr(instance, "stop"):
                await instance.stop()
            
            del self.running_modules[module_name]
            return True, f"Module {module_name} arrêté avec succès"
        except Exception as e:
            logger.error(f"Erreur lors de l'arrêt du module {module_name}: {str(e)}")
            return False, f"Erreur: {str(e)}"

    async def configure(self):
        """Configure les paramètres du bot."""
        # Utilisation directe des méthodes de l'interface CLI
        self.cli_interface.configure_parameters()

    async def display_config(self):
        """Affiche la configuration actuelle."""
        self.cli_interface.display_current_config()

    async def display_statistics(self):
        """Affiche les statistiques actuelles."""
        self.cli_interface.display_statistics()
        
    async def get_running_modules(self) -> Dict[str, Any]:
        """
        Retourne la liste des modules en cours d'exécution.
        
        Returns:
            Dict[str, Any]: Dictionnaire des modules actifs avec leur statut
        """
        result = {}
        for name, instance in self.running_modules.items():
            status = "Running"
            if hasattr(instance, "get_status"):
                status = instance.get_status()
            
            result[name] = {
                "status": status,
                "start_time": getattr(instance, "start_time", None)
            }
        
        return result

# Exemple d'utilisation
if __name__ == "__main__":
    ui = UnifiedInterface()
    asyncio.run(ui.start()) 