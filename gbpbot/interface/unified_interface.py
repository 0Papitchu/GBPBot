# Unified Interface for GBPBot
import asyncio
import logging
import os
from typing import Dict, Any, Optional, Tuple, List
import json

# Utilisation du module de compatibilité TensorFlow à la place de l'import direct
try:
    from gbpbot.utils.tensorflow_compat import tf, HAS_TENSORFLOW
    logging.info(f"Module de compatibilité TensorFlow chargé (version: {tf.__version__})")
except ImportError:
    logging.warning("Module de compatibilité TensorFlow non disponible. Certaines fonctionnalités peuvent être limitées.")
    HAS_TENSORFLOW = False

# Import CLIInterface avec gestion des erreurs
try:
    from gbpbot.cli_interface import CLIInterface
except ImportError as e:
    logging.error(f"Erreur lors de l'import de CLIInterface: {str(e)}")
    logging.error("Tentative d'utilisation du mode dégradé...")
    
    # Classe factice pour CLIInterface si elle n'est pas disponible
    class CLIInterface:
        """Interface CLI de secours en cas d'échec d'importation."""
        def __init__(self):
            self.initialized = False
            logging.warning("Utilisation d'une interface CLI de secours. Fonctionnalités limitées.")
        
        def _load_user_config(self):
            return {}
        
        def display_welcome(self):
            logging.info("Bienvenue dans GBPBot (mode dégradé)")
        
        async def run(self):
            logging.error("L'interface complète n'est pas disponible. Veuillez vérifier les dépendances.")
            return 1

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
        self.config_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config")
        os.makedirs(self.config_dir, exist_ok=True)

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
        
    async def configure_wallets(self) -> Tuple[bool, str]:
        """
        Configure les wallets via l'interface unifiée.
        
        Returns:
            Tuple[bool, str]: (Succès, Message d'information ou d'erreur)
        """
        try:
            # Vérifier si les méthodes de l'interface CLI sont disponibles
            if not hasattr(self.cli_interface, "edit_wallets"):
                return False, "Méthode edit_wallets non disponible dans l'interface CLI"
            
            # Appel direct à la méthode de l'interface CLI
            # Note: Cette méthode est synchrone et interactive
            # Une alternative asynchrone serait préférable pour une interface unifiée
            self.cli_interface.edit_wallets()
            return True, "Configuration des wallets terminée"
        except Exception as e:
            logger.error(f"Erreur lors de la configuration des wallets: {str(e)}")
            return False, f"Erreur: {str(e)}"
            
    async def manage_wallet_security(self) -> Tuple[bool, str]:
        """
        Gère la sécurité des wallets via l'interface unifiée.
        
        Returns:
            Tuple[bool, str]: (Succès, Message d'information ou d'erreur)
        """
        try:
            # Vérifier si les méthodes de l'interface CLI sont disponibles
            if not hasattr(self.cli_interface, "manage_wallet_security"):
                return False, "Méthode manage_wallet_security non disponible dans l'interface CLI"
            
            # Appel direct à la méthode de l'interface CLI
            # Note: Cette méthode est synchrone et interactive
            # Une alternative asynchrone serait préférable pour une interface unifiée
            self.cli_interface.manage_wallet_security()
            return True, "Gestion de la sécurité des wallets terminée"
        except Exception as e:
            logger.error(f"Erreur lors de la gestion de la sécurité des wallets: {str(e)}")
            return False, f"Erreur: {str(e)}"
    
    async def verify_wallet_balance(self, wallet_index: int) -> Tuple[bool, str, Optional[float]]:
        """
        Vérifie la balance d'un wallet via l'interface unifiée.
        
        Args:
            wallet_index: Index du wallet à vérifier (base 0)
            
        Returns:
            Tuple[bool, str, Optional[float]]: (Succès, Message d'information ou d'erreur, Balance si disponible)
        """
        try:
            # Charger les wallets
            wallets = await self.get_wallets()
            if not wallets:
                return False, "Aucun wallet configuré", None
                
            if "encrypted_file" in wallets[0]:
                return False, "Les wallets sont chiffrés. Déchiffrez-les d'abord.", None
                
            if wallet_index < 0 or wallet_index >= len(wallets):
                return False, f"Index de wallet invalide: {wallet_index} (sur {len(wallets)} wallets)", None
                
            wallet = wallets[wallet_index]
            chain = wallet.get("chain", "").lower()
            address = wallet.get("address", "")
            
            if not address:
                return False, "Adresse de wallet invalide", None
                
            # Vérifier la balance selon la blockchain
            if chain == "sol":
                # Import ici pour éviter les dépendances circulaires
                try:
                    from solana.rpc.api import Client
                    
                    # Utiliser le RPC configuré ou le RPC public par défaut
                    rpc_url = "https://api.mainnet-beta.solana.com"
                    
                    # Essayer de charger l'URL du RPC depuis la configuration
                    solana_config_path = os.path.join(self.config_dir, "solana_config.json")
                    if os.path.exists(solana_config_path):
                        try:
                            with open(solana_config_path, 'r') as f:
                                config_data = json.load(f)
                                providers = config_data.get("solana", {}).get("rpc", {}).get("providers", [])
                                if providers:
                                    # Utiliser le premier provider
                                    rpc_url = providers[0].get("url", rpc_url)
                        except Exception as e:
                            logger.error(f"Erreur lors de la lecture de la configuration Solana: {str(e)}")
                    
                    # Créer le client RPC
                    client = Client(rpc_url)
                    
                    # Obtenir la balance
                    response = client.get_balance(address)
                    
                    # Traiter la réponse selon sa structure
                    if isinstance(response, dict) and "result" in response:
                        # Format de réponse JSON-RPC
                        result = response.get("result", {})
                        if isinstance(result, dict) and "value" in result:
                            balance = result["value"] / 1_000_000_000  # Convert lamports to SOL
                            return True, f"Balance: {balance:.9f} SOL", balance
                        else:
                            return False, f"Format de réponse inattendu: {result}", None
                    elif hasattr(response, "value"):
                        # Format d'objet de réponse directe
                        balance = response.value / 1_000_000_000  # Convert lamports to SOL
                        return True, f"Balance: {balance:.9f} SOL", balance
                    else:
                        return False, f"Erreur lors de la vérification: {response}", None
                except ImportError:
                    return False, "Module solana-py non installé. Impossible de vérifier la balance.", None
                except Exception as e:
                    return False, f"Erreur lors de la vérification: {str(e)}", None
            
            elif chain == "avax":
                try:
                    from web3 import Web3
                    
                    # Utiliser le RPC configuré ou le RPC public par défaut
                    rpc_url = "https://api.avax.network/ext/bc/C/rpc"
                    
                    # Essayer de charger l'URL du RPC depuis la configuration
                    config_yaml_path = os.path.join(self.config_dir, "config.yaml")
                    if os.path.exists(config_yaml_path):
                        try:
                            import yaml
                            with open(config_yaml_path, 'r') as f:
                                config_data = yaml.safe_load(f)
                                providers = config_data.get("rpc", {}).get("providers", {}).get("avalanche", {}).get("mainnet", [])
                                if providers:
                                    # Utiliser le premier provider
                                    rpc_url = providers[0].get("url", rpc_url)
                        except Exception as e:
                            logger.error(f"Erreur lors de la lecture de la configuration AVAX: {str(e)}")
                    
                    # Créer le client Web3
                    w3 = Web3(Web3.HTTPProvider(rpc_url))
                    
                    if w3.is_connected():
                        # Obtenir la balance en Wei
                        balance_wei = w3.eth.get_balance(address)
                        # Convertir en AVAX
                        balance_avax = w3.from_wei(balance_wei, 'ether')
                        return True, f"Balance: {balance_avax:.9f} AVAX", float(balance_avax)
                    else:
                        return False, "Impossible de se connecter au RPC Avalanche.", None
                except ImportError:
                    return False, "Module web3 non installé. Impossible de vérifier la balance.", None
                except Exception as e:
                    return False, f"Erreur lors de la vérification: {str(e)}", None
            
            elif chain == "sonic":
                return False, "Vérification des wallets Sonic pas encore implémentée.", None
            
            else:
                return False, f"Blockchain non prise en charge: {chain}", None
                
        except Exception as e:
            logger.error(f"Erreur lors de la vérification du wallet: {str(e)}")
            return False, f"Erreur: {str(e)}", None

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
        
    # Nouvelles méthodes pour la gestion des wallets
    
    async def get_wallets(self) -> List[Dict[str, Any]]:
        """
        Récupère la liste des wallets configurés.
        
        Returns:
            List[Dict[str, Any]]: Liste des wallets configurés
        """
        wallets_path = os.path.join(self.config_dir, "wallets.json")
        encrypted_wallets_path = os.path.join(self.config_dir, "wallets.encrypted.json")
        
        # Vérifier si un fichier chiffré existe
        if os.path.exists(encrypted_wallets_path):
            logger.info("Un fichier de wallets chiffrés existe")
            try:
                # Import ici pour éviter les dépendances circulaires
                from gbpbot.security.wallet_encryption import WalletEncryption
                encryption = WalletEncryption(self.config_dir)
                
                # Pour l'interface asynchrone, nous devrions demander le mot de passe ailleurs
                # On retourne juste l'information que le fichier est chiffré
                return [{"encrypted_file": True, "wallet_count": "Fichier chiffré"}]
            except ImportError:
                logger.error("Module de chiffrement non disponible")
                return []
        
        # Sinon, charger les wallets en clair
        if os.path.exists(wallets_path):
            try:
                with open(wallets_path, 'r') as f:
                    wallets = json.load(f)
                    if not isinstance(wallets, list):
                        return []
                    return wallets
            except Exception as e:
                logger.error(f"Erreur lors de la lecture des wallets: {str(e)}")
                return []
        
        return []
    
    async def add_wallet(self, wallet_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Ajoute un nouveau wallet à la configuration.
        
        Args:
            wallet_data: Données du wallet (address, private_key, chain)
            
        Returns:
            Tuple[bool, str]: (Succès, Message d'information ou d'erreur)
        """
        required_fields = ["address", "private_key", "chain"]
        for field in required_fields:
            if field not in wallet_data:
                return False, f"Champ manquant: {field}"
        
        wallets_path = os.path.join(self.config_dir, "wallets.json")
        
        # Charger les wallets existants
        wallets = []
        if os.path.exists(wallets_path):
            try:
                with open(wallets_path, 'r') as f:
                    wallets = json.load(f)
                    if not isinstance(wallets, list):
                        wallets = []
            except Exception as e:
                logger.error(f"Erreur lors de la lecture des wallets: {str(e)}")
                return False, f"Erreur lors de la lecture des wallets: {str(e)}"
        
        # Ajouter le nouveau wallet
        wallets.append(wallet_data)
        
        # Sauvegarder les wallets
        try:
            with open(wallets_path, 'w') as f:
                json.dump(wallets, f, indent=4)
            return True, "Wallet ajouté avec succès"
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde des wallets: {str(e)}")
            return False, f"Erreur lors de la sauvegarde des wallets: {str(e)}"
    
    async def encrypt_wallets(self, password: str) -> Tuple[bool, str]:
        """
        Chiffre les wallets avec un mot de passe.
        
        Args:
            password: Mot de passe pour le chiffrement
            
        Returns:
            Tuple[bool, str]: (Succès, Message d'information ou d'erreur)
        """
        try:
            # Importer le module de chiffrement
            from gbpbot.security.wallet_encryption import WalletEncryption
            
            # Initialiser le gestionnaire de chiffrement
            encryption = WalletEncryption(self.config_dir)
            
            # Définir le mot de passe manuellement (pas d'interaction utilisateur)
            encryption.master_password = password
            
            # Charger les wallets
            wallets_path = os.path.join(self.config_dir, "wallets.json")
            if not os.path.exists(wallets_path):
                return False, "Aucun wallet à chiffrer"
                
            try:
                with open(wallets_path, 'r') as f:
                    wallets = json.load(f)
                    if not isinstance(wallets, list):
                        return False, "Format de wallets invalide"
            except Exception as e:
                logger.error(f"Erreur lors de la lecture des wallets: {str(e)}")
                return False, f"Erreur lors de la lecture des wallets: {str(e)}"
            
            # Chiffrer les wallets
            success = encryption.encrypt_wallets(wallets)
            
            if success:
                return True, "Wallets chiffrés avec succès"
            else:
                return False, "Erreur lors du chiffrement des wallets"
                
        except ImportError:
            return False, "Module de chiffrement non disponible"
        except Exception as e:
            logger.error(f"Erreur lors du chiffrement des wallets: {str(e)}")
            return False, f"Erreur lors du chiffrement des wallets: {str(e)}"
    
    async def decrypt_wallets(self, password: str) -> Tuple[bool, str]:
        """
        Déchiffre les wallets avec un mot de passe.
        
        Args:
            password: Mot de passe pour le déchiffrement
            
        Returns:
            Tuple[bool, str]: (Succès, Message d'information ou d'erreur)
        """
        try:
            # Importer le module de chiffrement
            from gbpbot.security.wallet_encryption import WalletEncryption
            
            # Initialiser le gestionnaire de chiffrement
            encryption = WalletEncryption(self.config_dir)
            
            # Vérifier si un fichier chiffré existe
            encrypted_wallets_path = os.path.join(self.config_dir, "wallets.encrypted.json")
            if not os.path.exists(encrypted_wallets_path):
                return False, "Aucun wallet chiffré trouvé"
            
            # Déchiffrer les wallets
            decrypted_wallets = encryption.decrypt_wallets(password)
            
            if decrypted_wallets:
                # Sauvegarder les wallets déchiffrés
                wallets_path = os.path.join(self.config_dir, "wallets.json")
                try:
                    with open(wallets_path, 'w') as f:
                        json.dump(decrypted_wallets, f, indent=4)
                    return True, "Wallets déchiffrés avec succès"
                except Exception as e:
                    logger.error(f"Erreur lors de la sauvegarde des wallets: {str(e)}")
                    return False, f"Erreur lors de la sauvegarde des wallets: {str(e)}"
            else:
                return False, "Erreur lors du déchiffrement des wallets. Mot de passe incorrect?"
                
        except ImportError:
            return False, "Module de chiffrement non disponible"
        except Exception as e:
            logger.error(f"Erreur lors du déchiffrement des wallets: {str(e)}")
            return False, f"Erreur lors du déchiffrement des wallets: {str(e)}"

# Exemple d'utilisation
if __name__ == "__main__":
    ui = UnifiedInterface()
    asyncio.run(ui.start()) 