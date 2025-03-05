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
        
        table = Table(show_header=False, box=box.ROUNDED)
        table.add_column("Option", style="cyan")
        table.add_column("Description")
        
        table.add_row("1", "Arbitrage")
        table.add_row("2", "Sniping de Token")
        table.add_row("3", "Sandwich Attack")
        
        self.console.print(table)
        
        return Prompt.ask("[bold yellow]Choisissez un module[/bold yellow]", choices=["1", "2", "3"])
    
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
        
        # Convert mode choice to string
        mode = "TEST" if mode_choice == "1" else "SIMULATION" if mode_choice == "2" else "LIVE"
        
        # Mettre à jour le mode dans la configuration
        self.user_config["mode"] = mode
        self._save_user_config(self.user_config)
        
        self.console.print(f"\n[bold green]Démarrage du bot en mode {mode} avec le module {module_choice}...[/bold green]")
        
        # Paramètres pour le bot
        is_testnet = False
        simulation_mode = (mode != "LIVE")
        
        try:
            # Lancer le bot avec le module sélectionné
            if module_choice == "1":
                # Code pour lancer l'arbitrage
                pass
            elif module_choice == "2":
                # Code pour lancer le sniping de token
                pass
            elif module_choice == "3":
                # Code pour lancer le sandwich attack
                pass
            
            # Placeholder for actual bot start logic
            self.running = True
            self.bot_instance = "Bot instance started"
            self.console.print("[bold green]Bot démarré avec succès![/bold green]")
        except Exception as e:
            self.console.print(f"[bold red]Erreur lors du démarrage du bot: {str(e)}[/bold red]")
            self.running = False
            self.bot_instance = None
    
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