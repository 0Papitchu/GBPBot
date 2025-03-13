"""
Interface CLI interactive pour GBPBot

Ce module fournit une interface en ligne de commande interactive pour contrôler
et surveiller le bot de trading sans avoir à modifier le code source.
"""

import os
import sys
import json
import asyncio
import time
from typing import Dict, Any, List, Optional
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich.text import Text
from rich import box
from loguru import logger
from rich.progress import Progress

from gbpbot.main import GBPBot
from gbpbot.config.trading_config import TradingConfig

# Chemin du fichier de configuration utilisateur
CONFIG_DIR = Path.home() / ".gbpbot"
USER_CONFIG_FILE = CONFIG_DIR / "user_config.json"

# Création du répertoire de configuration s'il n'existe pas
CONFIG_DIR.mkdir(exist_ok=True)

# Console Rich pour l'affichage
console = Console()

class CLIInterface:
    """Interface CLI interactive pour GBPBot"""
    
    def __init__(self):
        """Initialisation de l'interface CLI"""
        self.console = Console()
        self.user_config = self._load_user_config()
        self.bot_instance = None
        self.running = False
        self.mode = None
    
    def _load_user_config(self) -> Dict[str, Any]:
        """Charge la configuration utilisateur depuis le fichier JSON"""
        if USER_CONFIG_FILE.exists():
            try:
                with open(USER_CONFIG_FILE, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                logger.warning(f"Fichier de configuration corrompu: {USER_CONFIG_FILE}")
                return self._create_default_config()
        else:
            return self._create_default_config()
    
    def _create_default_config(self) -> Dict[str, Any]:
        """Crée une configuration par défaut"""
        default_config = {
            "mode": "TEST",  # TEST, SIMULATION ou LIVE
            "simulation": {
                "initial_balance": 5.0,  # AVAX
                "duration": 43200  # 12 heures en secondes
            },
            "trading": {
                "max_amount": 5.0,  # AVAX
                "min_profit": 0.5,  # %
                "max_slippage": 0.3,  # %
                "risk_level": "medium"  # low, medium, high
            },
            "monitoring": {
                "update_interval": 5,  # secondes
                "alert_threshold": 10.0  # % de perte
            },
            "security": {
                "auto_transfer_profits": True,
                "profit_threshold": 10.0,  # USDT
                "transfer_percentage": 30.0  # %
            }
        }
        
        # Sauvegarder la configuration par défaut
        self._save_user_config(default_config)
        return default_config
    
    def _save_user_config(self, config: Dict[str, Any]) -> None:
        """Sauvegarde la configuration utilisateur dans un fichier JSON"""
        try:
            with open(USER_CONFIG_FILE, "w") as f:
                json.dump(config, f, indent=4)
            logger.info(f"Configuration sauvegardée dans {USER_CONFIG_FILE}")
        except Exception as e:
            logger.error(f"Erreur lors de la sauvegarde de la configuration: {str(e)}")
    
    def display_welcome(self) -> None:
        """Affiche le message de bienvenue"""
        self.console.print(Panel.fit(
            "[bold green]GBPBot - Interface de contrôle[/bold green]\n\n"
            "Bienvenue dans l'interface de contrôle de GBPBot, votre assistant de trading sur Avalanche.\n"
            "Cette interface vous permet de configurer et lancer le bot sans modifier le code source.",
            title="🚀 GBPBot",
            border_style="green"
        ))
    
    def display_main_menu(self) -> str:
        """Affiche le menu principal et retourne le choix de l'utilisateur"""
        self.console.print("\n[bold cyan]Menu Principal[/bold cyan]")
        
        table = Table(show_header=False, box=box.ROUNDED)
        table.add_column("Option", style="cyan")
        table.add_column("Description")
        
        table.add_row("1", "Lancer le bot")
        table.add_row("2", "Configurer les paramètres")
        table.add_row("3", "Afficher la configuration actuelle")
        table.add_row("4", "Afficher les statistiques")
        table.add_row("5", "Quitter")
        
        self.console.print(table)
        
        return Prompt.ask("[bold yellow]Choisissez une option[/bold yellow]", choices=["1", "2", "3", "4", "5"])
    
    def display_mode_selection(self) -> str:
        """Affiche le menu de sélection du mode et retourne le choix de l'utilisateur"""
        self.console.print("\n[bold cyan]Sélection du Mode[/bold cyan]")
        
        table = Table(show_header=False, box=box.ROUNDED)
        table.add_column("Option", style="cyan")
        table.add_column("Description")
        
        table.add_row("1", "Test")
        table.add_row("2", "Simulation")
        table.add_row("3", "Réel")
        
        self.console.print(table)
        
        return Prompt.ask("[bold yellow]Choisissez un mode[/bold yellow]", choices=["1", "2", "3"])
    
    def display_module_selection(self) -> str:
        """Affiche le menu de sélection du module et retourne le choix de l'utilisateur"""
        self.console.print("\n[bold cyan]Sélection du Module[/bold cyan]")
        
        table = Table(show_header=True, box=box.ROUNDED)
        table.add_column("Option", style="cyan", justify="center")
        table.add_column("Module", style="white")
        table.add_column("Description", style="white")
        table.add_column("État", style="green", justify="center")
        
        # Ajout des modules avec leur statut de complétion
        table.add_row("1", "Arbitrage", "Arbitrage entre différents DEX et CEX", "✅ 100%")
        table.add_row("2", "Sniping", "Détection et sniping de nouveaux tokens", "✅ 100%")
        table.add_row("3", "MEV/Frontrunning", "Exploitation d'opportunités MEV sur AVAX", "⭐ 80%")
        table.add_row("4", "Mode Automatique", "Combinaison intelligente de stratégies", "✅ 100%")
        table.add_row("5", "AI Assistant", "Analyse et recommendations par IA", "⭐ 90%")
        table.add_row("6", "Backtesting", "Simulation et optimisation de stratégies", "⭐ 85%")
        table.add_row("7", "Retour", "Retour au menu principal", "")
        
        self.console.print(table)
        
        return Prompt.ask(
            "[bold yellow]Choisissez un module[/bold yellow]", 
            choices=["1", "2", "3", "4", "5", "6", "7"]
        )
    
    def display_autonomy_selection(self) -> str:
        """Affiche le menu de sélection du niveau d'autonomie et retourne le choix de l'utilisateur"""
        self.console.print("\n[bold cyan]Niveau d'Autonomie[/bold cyan]")
        
        table = Table(show_header=False, box=box.ROUNDED)
        table.add_column("Option", style="cyan")
        table.add_column("Description")
        
        table.add_row("1", "Semi-autonome (validation humaine des actions critiques)")
        table.add_row("2", "Autonome (l'IA prend toutes les décisions)")
        table.add_row("3", "Hybride (validation humaine seulement pour les opérations à risque)")
        
        self.console.print(table)
        
        return Prompt.ask("[bold yellow]Choisissez un niveau d'autonomie[/bold yellow]", choices=["1", "2", "3"])
    
    def configure_parameters(self) -> None:
        """Interface pour configurer les paramètres du bot"""
        self.console.print("\n[bold cyan]Configuration des Paramètres[/bold cyan]")
        
        # Sélection de la catégorie
        categories = {
            "1": "Simulation",
            "2": "Trading",
            "3": "Monitoring",
            "4": "Sécurité",
            "5": "Retour"
        }
        
        table = Table(show_header=False, box=box.ROUNDED)
        table.add_column("Option", style="cyan")
        table.add_column("Catégorie")
        
        for key, value in categories.items():
            table.add_row(key, value)
        
        self.console.print(table)
        
        choice = Prompt.ask("[bold yellow]Choisissez une catégorie[/bold yellow]", choices=list(categories.keys()))
        
        if choice == "5":
            return
        
        # Configuration spécifique à la catégorie
        if choice == "1":
            self._configure_simulation()
        elif choice == "2":
            self._configure_trading()
        elif choice == "3":
            self._configure_monitoring()
        elif choice == "4":
            self._configure_security()
    
    def _configure_simulation(self) -> None:
        """Configure les paramètres de simulation"""
        self.console.print("\n[bold cyan]Configuration de la Simulation[/bold cyan]")
        
        # Afficher les paramètres actuels
        current = self.user_config["simulation"]
        self.console.print(f"[yellow]Paramètres actuels:[/yellow]")
        self.console.print(f"  • Balance initiale: [bold]{current['initial_balance']} AVAX[/bold]")
        self.console.print(f"  • Durée: [bold]{current['duration']} secondes[/bold] ({current['duration']/3600:.1f} heures)")
        
        # Modifier les paramètres
        try:
            initial_balance = float(Prompt.ask(
                "[bold yellow]Balance initiale (AVAX)[/bold yellow]",
                default=str(current["initial_balance"])
            ))
            
            duration_hours = float(Prompt.ask(
                "[bold yellow]Durée de simulation (heures)[/bold yellow]",
                default=str(current["duration"]/3600)
            ))
            
            # Mettre à jour la configuration
            self.user_config["simulation"]["initial_balance"] = initial_balance
            self.user_config["simulation"]["duration"] = int(duration_hours * 3600)
            
            # Sauvegarder la configuration
            self._save_user_config(self.user_config)
            self.console.print("[bold green]✓ Configuration de simulation mise à jour[/bold green]")
            
        except ValueError:
            self.console.print("[bold red]✗ Erreur: Veuillez entrer des valeurs numériques valides[/bold red]")
    
    def _configure_trading(self) -> None:
        """Configure les paramètres de trading"""
        self.console.print("\n[bold cyan]Configuration du Trading[/bold cyan]")
        
        # Afficher les paramètres actuels
        current = self.user_config["trading"]
        self.console.print(f"[yellow]Paramètres actuels:[/yellow]")
        self.console.print(f"  • Montant maximum par trade: [bold]{current['max_amount']} AVAX[/bold]")
        self.console.print(f"  • Profit minimum: [bold]{current['min_profit']}%[/bold]")
        self.console.print(f"  • Slippage maximum: [bold]{current['max_slippage']}%[/bold]")
        self.console.print(f"  • Niveau de risque: [bold]{current['risk_level']}[/bold]")
        
        # Modifier les paramètres
        try:
            max_amount = float(Prompt.ask(
                "[bold yellow]Montant maximum par trade (AVAX)[/bold yellow]",
                default=str(current["max_amount"])
            ))
            
            min_profit = float(Prompt.ask(
                "[bold yellow]Profit minimum (%)[/bold yellow]",
                default=str(current["min_profit"])
            ))
            
            max_slippage = float(Prompt.ask(
                "[bold yellow]Slippage maximum (%)[/bold yellow]",
                default=str(current["max_slippage"])
            ))
            
            risk_level = Prompt.ask(
                "[bold yellow]Niveau de risque[/bold yellow]",
                choices=["low", "medium", "high"],
                default=current["risk_level"]
            )
            
            # Mettre à jour la configuration
            self.user_config["trading"]["max_amount"] = max_amount
            self.user_config["trading"]["min_profit"] = min_profit
            self.user_config["trading"]["max_slippage"] = max_slippage
            self.user_config["trading"]["risk_level"] = risk_level
            
            # Sauvegarder la configuration
            self._save_user_config(self.user_config)
            self.console.print("[bold green]✓ Configuration de trading mise à jour[/bold green]")
            
        except ValueError:
            self.console.print("[bold red]✗ Erreur: Veuillez entrer des valeurs numériques valides[/bold red]")
    
    def _configure_monitoring(self) -> None:
        """Configure les paramètres de monitoring"""
        self.console.print("\n[bold cyan]Configuration du Monitoring[/bold cyan]")
        
        # Afficher les paramètres actuels
        current = self.user_config["monitoring"]
        self.console.print(f"[yellow]Paramètres actuels:[/yellow]")
        self.console.print(f"  • Intervalle de mise à jour: [bold]{current['update_interval']} secondes[/bold]")
        self.console.print(f"  • Seuil d'alerte: [bold]{current['alert_threshold']}%[/bold]")
        
        # Modifier les paramètres
        try:
            update_interval = int(Prompt.ask(
                "[bold yellow]Intervalle de mise à jour (secondes)[/bold yellow]",
                default=str(current["update_interval"])
            ))
            
            alert_threshold = float(Prompt.ask(
                "[bold yellow]Seuil d'alerte (%)[/bold yellow]",
                default=str(current["alert_threshold"])
            ))
            
            # Mettre à jour la configuration
            self.user_config["monitoring"]["update_interval"] = update_interval
            self.user_config["monitoring"]["alert_threshold"] = alert_threshold
            
            # Sauvegarder la configuration
            self._save_user_config(self.user_config)
            self.console.print("[bold green]✓ Configuration de monitoring mise à jour[/bold green]")
            
        except ValueError:
            self.console.print("[bold red]✗ Erreur: Veuillez entrer des valeurs numériques valides[/bold red]")
    
    def _configure_security(self) -> None:
        """Configure les paramètres de sécurité"""
        self.console.print("\n[bold cyan]Configuration de la Sécurité[/bold cyan]")
        
        # Afficher les paramètres actuels
        current = self.user_config["security"]
        self.console.print(f"[yellow]Paramètres actuels:[/yellow]")
        self.console.print(f"  • Transfert automatique des profits: [bold]{'Activé' if current['auto_transfer_profits'] else 'Désactivé'}[/bold]")
        self.console.print(f"  • Seuil de profit pour transfert: [bold]{current['profit_threshold']} USDT[/bold]")
        self.console.print(f"  • Pourcentage à transférer: [bold]{current['transfer_percentage']}%[/bold]")
        
        # Modifier les paramètres
        auto_transfer = Confirm.ask(
            "[bold yellow]Activer le transfert automatique des profits?[/bold yellow]",
            default=current["auto_transfer_profits"]
        )
        
        try:
            profit_threshold = float(Prompt.ask(
                "[bold yellow]Seuil de profit pour transfert (USDT)[/bold yellow]",
                default=str(current["profit_threshold"])
            ))
            
            transfer_percentage = float(Prompt.ask(
                "[bold yellow]Pourcentage à transférer (%)[/bold yellow]",
                default=str(current["transfer_percentage"])
            ))
            
            # Mettre à jour la configuration
            self.user_config["security"]["auto_transfer_profits"] = auto_transfer
            self.user_config["security"]["profit_threshold"] = profit_threshold
            self.user_config["security"]["transfer_percentage"] = transfer_percentage
            
            # Sauvegarder la configuration
            self._save_user_config(self.user_config)
            self.console.print("[bold green]✓ Configuration de sécurité mise à jour[/bold green]")
            
        except ValueError:
            self.console.print("[bold red]✗ Erreur: Veuillez entrer des valeurs numériques valides[/bold red]")
    
    def display_current_config(self) -> None:
        """Affiche la configuration actuelle"""
        self.console.print("\n[bold cyan]Configuration Actuelle[/bold cyan]")
        
        # Mode
        self.console.print(f"[bold yellow]Mode:[/bold yellow] {self.user_config['mode']}")
        
        # Simulation
        sim = self.user_config["simulation"]
        self.console.print("\n[bold yellow]Simulation:[/bold yellow]")
        self.console.print(f"  • Balance initiale: {sim['initial_balance']} AVAX")
        self.console.print(f"  • Durée: {sim['duration']} secondes ({sim['duration']/3600:.1f} heures)")
        
        # Trading
        trade = self.user_config["trading"]
        self.console.print("\n[bold yellow]Trading:[/bold yellow]")
        self.console.print(f"  • Montant maximum par trade: {trade['max_amount']} AVAX")
        self.console.print(f"  • Profit minimum: {trade['min_profit']}%")
        self.console.print(f"  • Slippage maximum: {trade['max_slippage']}%")
        self.console.print(f"  • Niveau de risque: {trade['risk_level']}")
        
        # Monitoring
        mon = self.user_config["monitoring"]
        self.console.print("\n[bold yellow]Monitoring:[/bold yellow]")
        self.console.print(f"  • Intervalle de mise à jour: {mon['update_interval']} secondes")
        self.console.print(f"  • Seuil d'alerte: {mon['alert_threshold']}%")
        
        # Sécurité
        sec = self.user_config["security"]
        self.console.print("\n[bold yellow]Sécurité:[/bold yellow]")
        self.console.print(f"  • Transfert automatique des profits: {'Activé' if sec['auto_transfer_profits'] else 'Désactivé'}")
        self.console.print(f"  • Seuil de profit pour transfert: {sec['profit_threshold']} USDT")
        self.console.print(f"  • Pourcentage à transférer: {sec['transfer_percentage']}%")
        
        # Attendre que l'utilisateur appuie sur une touche
        self.console.input("\n[bold green]Appuyez sur Entrée pour continuer...[/bold green]")
    
    def display_statistics(self) -> None:
        """Affiche les statistiques du bot"""
        self.console.print("\n[bold cyan]Statistiques[/bold cyan]")
        
        if not os.path.exists("opportunities.csv"):
            self.console.print("[yellow]Aucune donnée disponible. Lancez le bot pour générer des statistiques.[/yellow]")
            self.console.input("\n[bold green]Appuyez sur Entrée pour continuer...[/bold green]")
            return
        
        try:
            import pandas as pd
            
            # Charger les données
            df = pd.read_csv("opportunities.csv")
            
            # Afficher les statistiques
            self.console.print(f"[bold yellow]Nombre total d'opportunités détectées:[/bold yellow] {len(df)}")
            
            if "profit_percent" in df.columns:
                avg_profit = df["profit_percent"].mean()
                max_profit = df["profit_percent"].max()
                self.console.print(f"[bold yellow]Profit moyen:[/bold yellow] {avg_profit:.2f}%")
                self.console.print(f"[bold yellow]Profit maximum:[/bold yellow] {max_profit:.2f}%")
            
            if "timestamp" in df.columns:
                df["timestamp"] = pd.to_datetime(df["timestamp"])
                last_24h = df[df["timestamp"] > pd.Timestamp.now() - pd.Timedelta(days=1)]
                self.console.print(f"[bold yellow]Opportunités des dernières 24h:[/bold yellow] {len(last_24h)}")
            
            # Attendre que l'utilisateur appuie sur une touche
            self.console.input("\n[bold green]Appuyez sur Entrée pour continuer...[/bold green]")
            
        except Exception as e:
            self.console.print(f"[bold red]Erreur lors de l'analyse des statistiques: {str(e)}[/bold red]")
            self.console.input("\n[bold green]Appuyez sur Entrée pour continuer...[/bold green]")
    
    async def start_bot(self) -> None:
        """Lance le bot avec les paramètres configurés"""
        mode_choice = self.display_mode_selection()
        module_choice = self.display_module_selection()
        
        # Si l'utilisateur choisit "Retour"
        if module_choice == "7":
            return
        
        # Convert mode choice to string
        mode = "TEST" if mode_choice == "1" else "SIMULATION" if mode_choice == "2" else "LIVE"
        
        # Mettre à jour le mode dans la configuration
        self.user_config["mode"] = mode
        self._save_user_config(self.user_config)
        
        # Détermine le module à lancer
        module_map = {
            "1": "Arbitrage",
            "2": "Sniping",
            "3": "MEV/Frontrunning",
            "4": "Mode Automatique",
            "5": "AI Assistant", 
            "6": "Backtesting"
        }
        
        # Déterminer si nous utilisons l'Agent IA et son niveau d'autonomie
        use_agent = False
        autonomy_level = "hybrid"  # Par défaut
        
        # Pour l'arbitrage, le sniping et le MEV, proposer le choix d'autonomie
        if module_choice in ["1", "2", "3"]:
            self.console.print(f"\n[bold magenta]Souhaitez-vous utiliser l'Agent IA pour le module {module_map[module_choice]}?[/bold magenta]")
            use_agent = Confirm.ask("[bold yellow]Activer l'Agent IA?[/bold yellow]", default=True)
            
            if use_agent:
                autonomy_choice = self.display_autonomy_selection()
                if autonomy_choice == "1":
                    autonomy_level = "semi_autonomous"
                elif autonomy_choice == "2":
                    autonomy_level = "autonomous"
                else:  # autonomy_choice == "3"
                    autonomy_level = "hybrid"
        
        # Pour le mode automatique, l'Agent IA est toujours utilisé
        elif module_choice == "4":
            use_agent = True
            autonomy_choice = self.display_autonomy_selection()
            if autonomy_choice == "1":
                autonomy_level = "semi_autonomous"
            elif autonomy_choice == "2":
                autonomy_level = "autonomous"
            else:  # autonomy_choice == "3"
                autonomy_level = "hybrid"
        
        # Pour l'AI Assistant, l'IA est toujours activée
        elif module_choice == "5":
            use_agent = True
            autonomy_level = "autonomous"  # L'assistant est toujours autonome
        
        # Pour le Backtesting, l'IA est optionnelle mais recommandée
        elif module_choice == "6":
            self.console.print("\n[bold magenta]Souhaitez-vous utiliser l'IA pour optimiser les paramètres de backtesting?[/bold magenta]")
            use_agent = Confirm.ask("[bold yellow]Activer l'IA pour l'optimisation?[/bold yellow]", default=True)
            autonomy_level = "hybrid"  # Toujours hybride pour le backtesting
        
        # Afficher le résumé de la configuration avant de démarrer
        module_name = module_map.get(module_choice, "Inconnu")
        agent_status = f"avec Agent IA ({autonomy_level})" if use_agent else "sans Agent IA"
        
        # Panneau d'information avec le résumé de la configuration
        self.console.print(Panel.fit(
            f"[bold white]Module:[/bold white] [cyan]{module_name}[/cyan]\n"
            f"[bold white]Mode:[/bold white] [cyan]{mode}[/cyan]\n"
            f"[bold white]Agent IA:[/bold white] [cyan]{'Activé - ' + autonomy_level if use_agent else 'Désactivé'}[/cyan]\n"
            f"[bold white]Date/Heure:[/bold white] [cyan]{time.strftime('%d/%m/%Y %H:%M:%S')}[/cyan]",
            title="[bold green]Configuration du Bot[/bold green]",
            border_style="green"
        ))
        
        # Paramètres pour le bot
        is_testnet = (mode == "TEST")
        simulation_mode = (mode != "LIVE")
        
        try:
            # Vérifier si les modules d'agent IA sont disponibles
            agent_available = False
            try:
                from gbpbot.ai.agent_manager import create_agent_manager
                agent_available = True
            except ImportError:
                if use_agent:
                    self.console.print("[bold yellow]Agent IA non disponible. Installation des dépendances nécessaires...[/bold yellow]")
                    
                    # Tenter d'installer les dépendances de l'Agent IA
                    try:
                        import subprocess
                        self.console.print("[bold cyan]Installation des dépendances de l'Agent IA...[/bold cyan]")
                        subprocess.call([sys.executable, "-m", "pip", "install", "-r", "requirements-agent.txt"])
                        
                        # Réessayer l'import après installation
                        try:
                            from gbpbot.ai.agent_manager import create_agent_manager
                            agent_available = True
                            self.console.print("[bold green]Dépendances de l'Agent IA installées avec succès![/bold green]")
                        except ImportError:
                            self.console.print("[bold red]Impossible de charger l'Agent IA même après installation. Le bot sera lancé sans IA.[/bold red]")
                            use_agent = False
                    except Exception as e:
                        self.console.print(f"[bold red]Erreur lors de l'installation des dépendances: {str(e)}[/bold red]")
                        self.console.print("[bold yellow]Le bot sera lancé sans Agent IA.[/bold yellow]")
                        use_agent = False
            
            # Initialiser l'agent si nécessaire
            agent = None
            if use_agent and agent_available:
                self.console.print("[bold cyan]Initialisation de l'Agent IA...[/bold cyan]")
                try:
                    # Callback pour l'approbation des actions
                    async def cli_approval_callback(operation, params):
                        self.console.print(Panel.fit(
                            f"[bold]Opération: [cyan]{operation}[/cyan][/bold]\n\n"
                            f"Paramètres: {json.dumps(params, indent=2)}",
                            title="[bold yellow]Approbation Requise[/bold yellow]",
                            border_style="yellow"
                        ))
                        return Confirm.ask("[bold yellow]Approuver cette action?[/bold yellow]")
                    
                    agent = create_agent_manager(
                        autonomy_level=autonomy_level,
                        max_decision_amount=self.user_config["trading"]["max_amount"] * 0.1,  # 10% du montant max
                        require_approval_callback=cli_approval_callback
                    )
                    self.console.print("[bold green]Agent IA initialisé avec succès![/bold green]")
                except Exception as e:
                    self.console.print(f"[bold red]Erreur lors de l'initialisation de l'Agent IA: {str(e)}[/bold red]")
                    self.console.print("[bold yellow]Le bot sera lancé sans Agent IA.[/bold yellow]")
                    use_agent = False
            
            # Préparation des configurations selon le module
            try:
                # Configuration commune à tous les modules
                common_config = {
                    "mode": mode,
                    "is_testnet": is_testnet,
                    "simulation_mode": simulation_mode,
                    "max_amount": self.user_config["trading"]["max_amount"],
                    "min_profit": self.user_config["trading"]["min_profit"],
                    "max_slippage": self.user_config["trading"]["max_slippage"],
                    "risk_level": self.user_config["trading"]["risk_level"],
                    "agent": agent
                }
                
                # Lancement du module spécifique
                if module_choice == "1":  # Arbitrage
                    from gbpbot.strategies.arbitrage import ArbitrageStrategy
                    
                    # Configuration spécifique à l'arbitrage
                    arbitrage_config = {
                        **common_config,
                        "update_interval": self.user_config["monitoring"]["update_interval"],
                        "dex_list": ["trader_joe", "pangolin", "sushiswap"],  # Configurable dans l'avenir
                        "cex_list": ["binance", "kucoin", "gate_io"] if not is_testnet else []
                    }
                    
                    # Lancement du module d'arbitrage
                    self.console.print("[bold cyan]Lancement du module d'Arbitrage...[/bold cyan]")
                    strategy = ArbitrageStrategy(config=arbitrage_config)
                    await self._run_strategy_with_ui(strategy, "Arbitrage")
                    
                elif module_choice == "2":  # Sniping
                    from gbpbot.strategies.sniping import SnipingStrategy
                    
                    # Configuration spécifique au sniping
                    sniping_config = {
                        **common_config,
                        "update_interval": self.user_config["monitoring"]["update_interval"],
                        "target_blockchains": ["solana", "avax"],  # Configurable dans l'avenir
                        "max_tokens_to_track": 100,
                        "security_level": "high"  # low, medium, high
                    }
                    
                    # Lancement du module de sniping
                    self.console.print("[bold cyan]Lancement du module de Sniping...[/bold cyan]")
                    strategy = SnipingStrategy(config=sniping_config)
                    await self._run_strategy_with_ui(strategy, "Sniping")
                    
                elif module_choice == "3":  # MEV/Frontrunning
                    from gbpbot.strategies.mev import MEVStrategy
                    
                    # Configuration spécifique au MEV
                    mev_config = {
                        **common_config,
                        "blockchain": "avax",  # Actuellement uniquement AVAX est supporté
                        "profit_threshold": 0.001,  # 0.1% minimum de profit
                        "gas_price_boost": 5.0,  # 5% d'augmentation du gas pour priorité
                        "test_mode": is_testnet,
                        "target_pairs_file": "gbpbot/config/target_pairs.json"
                    }
                    
                    # Lancement du module MEV
                    self.console.print("[bold cyan]Lancement du module MEV/Frontrunning...[/bold cyan]")
                    self.console.print("[bold yellow]⚠️ Ce module est en phase de test (80% complété)[/bold yellow]")
                    strategy = MEVStrategy(config=mev_config)
                    await self._run_strategy_with_ui(strategy, "MEV/Frontrunning")
                    
                elif module_choice == "4":  # Mode Automatique
                    from gbpbot.strategies.auto_mode import AutoModeStrategy
                    
                    # Configuration spécifique au mode automatique
                    auto_config = {
                        **common_config,
                        "update_interval": self.user_config["monitoring"]["update_interval"],
                        "strategies": ["arbitrage", "sniping", "mev"],
                        "allocation": {"arbitrage": 0.4, "sniping": 0.4, "mev": 0.2},
                        "auto_adjust": True  # Ajustement automatique des allocations
                    }
                    
                    # Lancement du mode automatique
                    self.console.print("[bold cyan]Lancement du Mode Automatique...[/bold cyan]")
                    strategy = AutoModeStrategy(config=auto_config)
                    await self._run_strategy_with_ui(strategy, "Mode Automatique")
                    
                elif module_choice == "5":  # AI Assistant
                    from gbpbot.ai.assistant import AIAssistant
                    
                    # Configuration spécifique à l'assistant IA
                    assistant_config = {
                        "user_config": self.user_config,
                        "model": "gpt-4" if not is_testnet else "gpt-3.5-turbo",
                        "use_local_llm": True,  # Utiliser LLaMA en local si disponible
                        "history_file": "gbpbot/data/assistant_history.json"
                    }
                    
                    # Lancement de l'assistant IA
                    self.console.print("[bold cyan]Lancement de l'Assistant IA...[/bold cyan]")
                    assistant = AIAssistant(config=assistant_config)
                    await self._run_assistant(assistant)
                    
                elif module_choice == "6":  # Backtesting
                    from gbpbot.backtesting.backtesting_engine import BacktestingEngine
                    
                    # Afficher le menu de configuration du backtesting
                    backtest_config = await self._configure_backtesting()
                    
                    # Lancement du backtesting
                    self.console.print("[bold cyan]Lancement du module de Backtesting...[/bold cyan]")
                    engine = BacktestingEngine(config=backtest_config)
                    await self._run_backtesting(engine)
                
            except ImportError as e:
                self.console.print(f"[bold red]Erreur: Module requis non disponible: {str(e)}[/bold red]")
                self.console.print("[bold yellow]Vérifiez que toutes les dépendances sont installées correctement.[/bold yellow]")
            except Exception as e:
                self.console.print(f"[bold red]Erreur lors du lancement du module: {str(e)}[/bold red]")
                # Afficher le traceback pour le débogage
                import traceback
                self.console.print("[bold red]Détails de l'erreur:[/bold red]")
                self.console.print(traceback.format_exc())
        
        except Exception as e:
            self.console.print(f"[bold red]Erreur globale lors du lancement du bot: {str(e)}[/bold red]")
        
        finally:
            # Afficher un message de fin et attendre l'entrée de l'utilisateur
            self.console.print("\n[bold yellow]Session terminée. Appuyez sur Entrée pour revenir au menu principal.[/bold yellow]")
            input()
            
    async def _run_strategy_with_ui(self, strategy, strategy_name):
        """Exécute une stratégie avec une interface utilisateur en temps réel"""
        # Initialisation de la disposition Rich pour l'affichage en direct
        layout = Layout()
        layout.split(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=3)
        )
        
        # Diviser la section principale en deux colonnes
        layout["main"].split_row(
            Layout(name="stats", ratio=1),
            Layout(name="log", ratio=2)
        )
        
        # Initialiser les composants d'affichage
        header = Panel(f"[bold green]{strategy_name}[/bold green] - En cours d'exécution", border_style="green")
        stats_panel = Panel("Chargement des statistiques...", title="Statistiques", border_style="blue")
        log_panel = Panel("Initialisation...", title="Journal d'activité", border_style="cyan")
        footer = Panel("[bold]Ctrl+C pour arrêter | S pour statistiques détaillées | H pour aide[/bold]", border_style="yellow")
        
        # Assigner les composants à la disposition
        layout["header"].update(header)
        layout["stats"].update(stats_panel)
        layout["log"].update(log_panel)
        layout["footer"].update(footer)
        
        # Créer une file d'événements pour la communication async
        event_queue = asyncio.Queue()
        
        # Fonction pour mettre à jour les statistiques
        async def update_stats():
            while True:
                try:
                    stats = strategy.get_statistics()
                    stats_table = Table(show_header=False, box=box.SIMPLE)
                    stats_table.add_column("Métrique", style="blue")
                    stats_table.add_column("Valeur", style="white")
                    
                    # Ajouter les statistiques à la table
                    for key, value in stats.items():
                        if isinstance(value, dict):
                            formatted_value = "\n".join([f"{k}: {v}" for k, v in value.items()])
                        else:
                            formatted_value = str(value)
                        stats_table.add_row(key, formatted_value)
                    
                    stats_panel = Panel(stats_table, title="Statistiques", border_style="blue")
                    layout["stats"].update(stats_panel)
                    
                    # Attendre avant la prochaine mise à jour
                    await asyncio.sleep(2)
                except Exception as e:
                    layout["stats"].update(Panel(f"Erreur: {str(e)}", title="Statistiques", border_style="red"))
                    await asyncio.sleep(5)
        
        # Fonction pour mettre à jour le journal
        async def update_log():
            logs = []
            while True:
                try:
                    # Simuler la réception de logs (dans une implémentation réelle, cela viendrait de la stratégie)
                    if not event_queue.empty():
                        log_entry = await event_queue.get()
                        logs.append(log_entry)
                        # Garder seulement les 20 derniers logs
                        if len(logs) > 20:
                            logs.pop(0)
                    
                    log_text = "\n".join(logs)
                    log_panel = Panel(log_text, title="Journal d'activité", border_style="cyan")
                    layout["log"].update(log_panel)
                    
                    # Courte pause
                    await asyncio.sleep(0.1)
                except Exception as e:
                    layout["log"].update(Panel(f"Erreur: {str(e)}", title="Journal d'activité", border_style="red"))
                    await asyncio.sleep(5)
        
        # Fonction principale pour exécuter l'interface utilisateur
        async def run_ui():
            # Démarrer la stratégie
            await strategy.start()
            
            # Ajouter un log de démarrage
            await event_queue.put(f"[{time.strftime('%H:%M:%S')}] Stratégie {strategy_name} démarrée")
            
            # Boucle principale de l'interface
            try:
                update_stats_task = asyncio.create_task(update_stats())
                update_log_task = asyncio.create_task(update_log())
                
                # Simuler quelques logs pour démonstration
                for i in range(5):
                    await event_queue.put(f"[{time.strftime('%H:%M:%S')}] Initialisation de la composante {i+1}/5...")
                    await asyncio.sleep(1)
                
                await event_queue.put(f"[{time.strftime('%H:%M:%S')}] [green]✓ Système prêt et en surveillance active[/green]")
                
                # Exécution pendant une durée définie ou jusqu'à interruption
                await asyncio.sleep(60)  # Par défaut, exécution de 60 secondes pour la démonstration
                
            except asyncio.CancelledError:
                await event_queue.put(f"[{time.strftime('%H:%M:%S')}] [yellow]! Arrêt demandé par l'utilisateur[/yellow]")
            finally:
                # Arrêter proprement la stratégie
                await strategy.stop()
                await event_queue.put(f"[{time.strftime('%H:%M:%S')}] [yellow]Stratégie arrêtée[/yellow]")
                
                # Annuler les tâches en cours
                if 'update_stats_task' in locals():
                    update_stats_task.cancel()
                if 'update_log_task' in locals():
                    update_log_task.cancel()
        
        # Exécuter l'interface utilisateur avec Rich Live
        with Live(layout, screen=True, refresh_per_second=10):
            try:
                await run_ui()
            except KeyboardInterrupt:
                self.console.print("[bold yellow]Interruption détectée. Arrêt en cours...[/bold yellow]")
            except Exception as e:
                self.console.print(f"[bold red]Erreur: {str(e)}[/bold red]")
        
        self.console.print("[bold green]Exécution terminée.[/bold green]")
    
    async def _run_assistant(self, assistant):
        """Interface pour interagir avec l'assistant IA"""
        self.console.print("\n[bold cyan]Assistant IA GBPBot[/bold cyan]")
        self.console.print("Tapez vos questions ou commandes. Tapez 'quit' ou 'exit' pour quitter.")
        
        # Démarrer l'assistant
        await assistant.start()
        
        try:
            while True:
                user_input = Prompt.ask("\n[bold green]Vous[/bold green]")
                
                if user_input.lower() in ['quit', 'exit', 'q']:
                    break
                
                # Afficher un indicateur de chargement pendant le traitement
                with self.console.status("[bold green]L'assistant réfléchit...[/bold green]"):
                    response = await assistant.process_input(user_input)
                
                # Afficher la réponse
                self.console.print(f"\n[bold blue]Assistant[/bold blue]: {response}")
        
        finally:
            # Arrêter proprement l'assistant
            await assistant.stop()
            self.console.print("[bold yellow]Session avec l'assistant terminée.[/bold yellow]")
    
    async def _configure_backtesting(self):
        """Interface pour configurer un backtest"""
        self.console.print("\n[bold cyan]Configuration du Backtesting[/bold cyan]")
        
        # Sélection de la stratégie
        self.console.print("\n[bold]Sélectionnez la stratégie à tester:[/bold]")
        strategies = {
            "1": "Arbitrage",
            "2": "Sniping",
            "3": "MEV/Frontrunning",
            "4": "Mode Automatique (Multi-stratégie)"
        }
        
        for key, value in strategies.items():
            self.console.print(f"{key}. {value}")
        
        strategy_choice = Prompt.ask("[bold yellow]Stratégie[/bold yellow]", choices=list(strategies.keys()))
        strategy_name = strategies[strategy_choice]
        
        # Sélection de la période
        self.console.print("\n[bold]Période de test:[/bold]")
        periods = {
            "1": "Dernières 24 heures",
            "2": "Dernière semaine",
            "3": "Dernier mois",
            "4": "Personnalisée"
        }
        
        for key, value in periods.items():
            self.console.print(f"{key}. {value}")
        
        period_choice = Prompt.ask("[bold yellow]Période[/bold yellow]", choices=list(periods.keys()))
        
        # Configuration de la période personnalisée si nécessaire
        start_date = None
        end_date = None
        if period_choice == "4":
            start_date = Prompt.ask("[bold yellow]Date de début (YYYY-MM-DD)[/bold yellow]")
            end_date = Prompt.ask("[bold yellow]Date de fin (YYYY-MM-DD)[/bold yellow]")
        
        # Configuration des paramètres de la stratégie
        self.console.print("\n[bold]Paramètres de la stratégie:[/bold]")
        
        # Paramètres communs à toutes les stratégies
        initial_balance = float(Prompt.ask(
            "[bold yellow]Balance initiale (AVAX/SOL)[/bold yellow]",
            default="10"
        ))
        
        max_slippage = float(Prompt.ask(
            "[bold yellow]Slippage maximum (%)[/bold yellow]",
            default="1.0"
        ))
        
        # Paramètres spécifiques selon la stratégie
        strategy_params = {}
        if strategy_choice == "1":  # Arbitrage
            min_profit = float(Prompt.ask(
                "[bold yellow]Profit minimum (%)[/bold yellow]",
                default="0.5"
            ))
            dex_pairs = Prompt.ask(
                "[bold yellow]Paires de DEX (séparées par des virgules)[/bold yellow]",
                default="trader_joe_pangolin,trader_joe_sushiswap"
            )
            strategy_params = {
                "min_profit": min_profit,
                "dex_pairs": dex_pairs.split(",")
            }
        elif strategy_choice == "2":  # Sniping
            min_liquidity = float(Prompt.ask(
                "[bold yellow]Liquidité minimum (USD)[/bold yellow]",
                default="10000"
            ))
            max_buy = float(Prompt.ask(
                "[bold yellow]Achat maximum par token (% du capital)[/bold yellow]",
                default="5"
            ))
            strategy_params = {
                "min_liquidity": min_liquidity,
                "max_buy_percent": max_buy
            }
        elif strategy_choice == "3":  # MEV
            gas_boost = float(Prompt.ask(
                "[bold yellow]Boost de gas (%)[/bold yellow]",
                default="5.0"
            ))
            profit_threshold = float(Prompt.ask(
                "[bold yellow]Seuil de profit minimum (USD)[/bold yellow]",
                default="1.0"
            ))
            strategy_params = {
                "gas_boost": gas_boost,
                "profit_threshold": profit_threshold
            }
        elif strategy_choice == "4":  # Mode Automatique
            allocation = Prompt.ask(
                "[bold yellow]Allocation entre stratégies (format: arbitrage,sniping,mev)[/bold yellow]",
                default="40,40,20"
            )
            allocations = [int(x) for x in allocation.split(",")]
            strategy_params = {
                "allocation": {
                    "arbitrage": allocations[0] / 100,
                    "sniping": allocations[1] / 100,
                    "mev": allocations[2] / 100
                }
            }
        
        # Compiler la configuration complète
        config = {
            "strategy": strategy_name.lower().replace("/", "_"),
            "initial_balance": initial_balance,
            "max_slippage": max_slippage,
            "period": periods[period_choice].lower().replace(" ", "_"),
            "start_date": start_date,
            "end_date": end_date,
            "strategy_params": strategy_params,
            "test_mode": True,
            "visualize_results": True
        }
        
        # Afficher la configuration finale
        self.console.print("\n[bold cyan]Configuration du backtest:[/bold cyan]")
        self.console.print(json.dumps(config, indent=2))
        
        # Confirmer la configuration
        if not Confirm.ask("[bold yellow]Confirmer cette configuration?[/bold yellow]", default=True):
            self.console.print("[bold yellow]Configuration annulée. Retour au menu...[/bold yellow]")
            return None
        
        return config
    
    async def _run_backtesting(self, engine):
        """Exécute un backtest avec affichage des résultats"""
        self.console.print("\n[bold cyan]Exécution du Backtesting...[/bold cyan]")
        
        # Initialiser le moteur de backtest
        try:
            # Afficher une barre de progression pendant l'initialisation
            with self.console.status("[bold green]Initialisation du backtest...[/bold green]"):
                await engine.initialize()
            
            # Exécuter le backtest avec une barre de progression
            total_steps = engine.get_total_steps()
            
            with Progress() as progress:
                task = progress.add_task("[cyan]Execution du backtest...", total=total_steps)
                
                # Fonction de callback pour mettre à jour la progression
                async def progress_callback(current_step):
                    progress.update(task, completed=current_step)
                
                # Exécuter le backtest avec le callback de progression
                results = await engine.run(progress_callback=progress_callback)
            
            # Afficher les résultats
            self.console.print("\n[bold green]Backtest terminé![/bold green]")
            
            # Créer un tableau des résultats
            results_table = Table(title="Résultats du Backtest", box=box.ROUNDED)
            results_table.add_column("Métrique", style="cyan")
            results_table.add_column("Valeur", style="white")
            
            # Ajouter les métriques de performance
            for key, value in results["performance_metrics"].items():
                # Formatter les valeurs numériques
                if isinstance(value, float):
                    if key.endswith("percent") or key.endswith("rate"):
                        formatted_value = f"{value:.2f}%"
                    else:
                        formatted_value = f"{value:.4f}"
                else:
                    formatted_value = str(value)
                
                results_table.add_row(key.replace("_", " ").title(), formatted_value)
            
            # Afficher le tableau
            self.console.print(results_table)
            
            # Afficher les graphiques si disponibles
            if results.get("charts_path"):
                self.console.print(f"\n[bold cyan]Graphiques générés: [/bold cyan]{results['charts_path']}")
            
            # Enregistrer les résultats
            if Confirm.ask("[bold yellow]Sauvegarder les résultats?[/bold yellow]", default=True):
                save_path = engine.save_results(results)
                self.console.print(f"[bold green]Résultats sauvegardés: [/bold green]{save_path}")
            
        except Exception as e:
            self.console.print(f"[bold red]Erreur lors du backtest: {str(e)}[/bold red]")
            # Afficher le traceback pour le débogage
            import traceback
            self.console.print("[bold red]Détails de l'erreur:[/bold red]")
            self.console.print(traceback.format_exc())
    
    async def run(self) -> None:
        """Exécute l'interface CLI"""
        self.display_welcome()
        
        while True:
            choice = self.display_main_menu()
            
            if choice == "1":  # Lancer le bot
                await self.start_bot()
            elif choice == "2":  # Configurer les paramètres
                self.configure_parameters()
            elif choice == "3":  # Afficher la configuration actuelle
                self.display_current_config()
            elif choice == "4":  # Afficher les statistiques
                self.display_statistics()
            elif choice == "5":  # Quitter
                self.console.print("[bold green]Merci d'avoir utilisé GBPBot. À bientôt![/bold green]")
                break

def main():
    """Point d'entrée principal pour l'interface CLI"""
    try:
        # Configurer le logging
        logger.remove()
        logger.add(
            sys.stderr,
            level="INFO",
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
        )
        logger.add(
            "cli.log",
            level="DEBUG",
            rotation="10 MB",
            retention="7 days"
        )
        
        # Créer et exécuter l'interface CLI
        cli = CLIInterface()
        asyncio.run(cli.run())
        
    except KeyboardInterrupt:
        console.print("[bold yellow]Arrêt de l'interface demandé par l'utilisateur...[/bold yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"[bold red]Erreur lors de l'exécution de l'interface: {str(e)}[/bold red]")
        logger.exception("Erreur non gérée dans l'interface CLI")
        sys.exit(1)

if __name__ == "__main__":
    main() 