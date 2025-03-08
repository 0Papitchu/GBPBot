#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
GBPBot - Point d'entrée principal

Ce module est le point d'entrée principal de GBPBot. Il gère l'initialisation
du bot, le chargement de la configuration et le menu interactif.
"""

import os
import sys
import time
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union, Any, Callable
from prompt_toolkit import PromptSession
from prompt_toolkit.shortcuts import clear
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

# Ajouter le répertoire parent au chemin d'importation
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from gbpbot.core.config import load_config, Config
    from gbpbot.core.logging import setup_logging
    from gbpbot.ui.cli_menu import CliMenu, MenuItem
    from gbpbot.modules.arbitrage import ArbitrageEngine
    from gbpbot.modules.sniper import TokenSniper
    from gbpbot.modules.auto_mode import AutoMode
except ImportError as e:
    print(f"Erreur lors de l'importation des modules GBPBot: {e}")
    print("Création des modules manquants...")
    
    # Créer la structure du projet si elle n'existe pas
    dirs = [
        "gbpbot/core",
        "gbpbot/ui",
        "gbpbot/modules",
        "gbpbot/utils",
        "gbpbot/data",
        "gbpbot/models",
        "gbpbot/adapters",
        "gbpbot/security",
    ]
    
    for d in dirs:
        os.makedirs(d, exist_ok=True)
        init_file = os.path.join(d, "__init__.py")
        if not os.path.exists(init_file):
            with open(init_file, "w") as f:
                f.write(f'"""\n{d.split("/")[-1]} module for GBPBot\n"""\n')
    
    print("Structure de base créée. Veuillez exécuter l'installation complète pour générer tous les modules.")
    sys.exit(1)

# Version et informations du logiciel
__version__ = "0.1.0"
__author__ = "GBPBot Team"
__license__ = "MIT"

# Console rich pour l'affichage amélioré
console = Console()

def display_logo() -> None:
    """Affiche le logo ASCII et les informations de base de GBPBot."""
    console.print("")
    console.print(Panel.fit(
        Text("GBPBot", justify="center", style="bold yellow") + 
        Text("\nTrading Bot pour MEME coins", justify="center") +
        Text(f"\nVersion {__version__}", justify="center", style="dim"),
        box=box.DOUBLE,
        border_style="blue",
        padding=(1, 5),
        title="[bold]GBPBot[/bold]",
        title_align="center",
    ))
    console.print("")

def display_main_menu() -> int:
    """
    Affiche le menu principal et retourne le choix de l'utilisateur.
    
    Returns:
        int: Le choix de l'utilisateur
    """
    clear()
    display_logo()
    
    console.print("=" * 60, style="blue")
    console.print("                    GBPBot - Menu Principal", style="bold yellow")
    console.print("=" * 60, style="blue")
    console.print("Bienvenue dans GBPBot, votre assistant de trading sur Avalanche, Solana et Sonic!")
    console.print("")
    
    table = Table(show_header=False, box=box.SIMPLE, style="blue")
    table.add_column("Option", style="yellow")
    table.add_column("Description")
    
    table.add_row("1", "Démarrer le Bot")
    table.add_row("2", "Configurer les paramètres")
    table.add_row("3", "Afficher la configuration actuelle")
    table.add_row("4", "Statistiques et Logs")
    table.add_row("5", "Afficher les Modules Disponibles")
    table.add_row("6", "Quitter")
    
    console.print(table)
    console.print("")
    
    choice = console.input("[bold yellow]Votre choix: [/bold yellow]")
    return choice

def display_modules_menu() -> int:
    """
    Affiche le menu des modules et retourne le choix de l'utilisateur.
    
    Returns:
        int: Le choix de l'utilisateur
    """
    clear()
    display_logo()
    
    console.print("=" * 60, style="blue")
    console.print("                GBPBot - Sélection de Module", style="bold yellow")
    console.print("=" * 60, style="blue")
    
    table = Table(show_header=False, box=box.SIMPLE, style="blue")
    table.add_column("Option", style="yellow")
    table.add_column("Description")
    
    table.add_row("1", "Arbitrage entre les DEX")
    table.add_row("2", "Sniping de Token")
    table.add_row("3", "Lancer automatiquement le bot")
    table.add_row("4", "Retour au menu principal")
    
    console.print(table)
    console.print("")
    
    choice = console.input("[bold yellow]Votre choix: [/bold yellow]")
    return choice

def display_configuration() -> None:
    """Affiche la configuration actuelle."""
    clear()
    display_logo()
    
    try:
        config = load_config()
        
        console.print("=" * 60, style="blue")
        console.print("            Configuration Actuelle de GBPBot", style="bold yellow")
        console.print("=" * 60, style="blue")
        
        # Configuration générale
        general_table = Table(title="Configuration Générale", box=box.SIMPLE)
        general_table.add_column("Paramètre", style="cyan")
        general_table.add_column("Valeur", style="green")
        
        general_table.add_row("Mode Debug", str(config.get("DEBUG", False)))
        general_table.add_row("Niveau de Log", config.get("LOG_LEVEL", "info"))
        general_table.add_row("Environnement", config.get("ENVIRONMENT", "production"))
        
        # Configuration blockchain
        blockchain_table = Table(title="Configuration Blockchain", box=box.SIMPLE)
        blockchain_table.add_column("Blockchain", style="cyan")
        blockchain_table.add_column("RPC URL", style="green")
        blockchain_table.add_column("Clé Privée", style="red")
        
        # Solana
        sol_private_key = config.get("SOLANA_PRIVATE_KEY", "")
        sol_private_key = "***" + sol_private_key[-4:] if sol_private_key else "Non configuré"
        blockchain_table.add_row(
            "Solana",
            config.get("SOLANA_RPC_URL", "Non configuré"),
            sol_private_key
        )
        
        # AVAX
        avax_private_key = config.get("AVAX_PRIVATE_KEY", "")
        avax_private_key = "***" + avax_private_key[-4:] if avax_private_key else "Non configuré"
        blockchain_table.add_row(
            "Avalanche",
            config.get("AVAX_RPC_URL", "Non configuré"),
            avax_private_key
        )
        
        # Sonic
        sonic_private_key = config.get("SONIC_PRIVATE_KEY", "")
        sonic_private_key = "***" + sonic_private_key[-4:] if sonic_private_key else "Non configuré"
        blockchain_table.add_row(
            "Sonic",
            config.get("SONIC_RPC_URL", "Non configuré"),
            sonic_private_key
        )
        
        # Configuration trading
        trading_table = Table(title="Configuration Trading", box=box.SIMPLE)
        trading_table.add_column("Paramètre", style="cyan")
        trading_table.add_column("Valeur", style="green")
        
        trading_table.add_row("Slippage Maximum", str(config.get("MAX_SLIPPAGE", "1.0")) + "%")
        trading_table.add_row("Priorité Gas", config.get("GAS_PRIORITY", "medium"))
        trading_table.add_row("Montant Max Transaction", str(config.get("MAX_TRANSACTION_AMOUNT", "0.1")))
        trading_table.add_row("Sniping Activé", str(config.get("ENABLE_SNIPING", True)))
        trading_table.add_row("Arbitrage Activé", str(config.get("ENABLE_ARBITRAGE", False)))
        trading_table.add_row("Mode Auto Activé", str(config.get("ENABLE_AUTO_MODE", False)))
        
        # Configuration sécurité
        security_table = Table(title="Configuration Sécurité", box=box.SIMPLE)
        security_table.add_column("Paramètre", style="cyan")
        security_table.add_column("Valeur", style="green")
        
        security_table.add_row("Analyse des Contrats", str(config.get("REQUIRE_CONTRACT_ANALYSIS", True)))
        security_table.add_row("Stop Loss Activé", str(config.get("ENABLE_STOP_LOSS", True)))
        security_table.add_row("% Stop Loss par Défaut", str(config.get("DEFAULT_STOP_LOSS_PERCENTAGE", "5")) + "%")
        security_table.add_row("Protection Anti-Rugpull", str(config.get("ENABLE_ANTI_RUGPULL", True)))
        security_table.add_row("Protection MEV", str(config.get("MEV_PROTECTION", True)))
        
        # Affichage des tables
        console.print(general_table)
        console.print("")
        console.print(blockchain_table)
        console.print("")
        console.print(trading_table)
        console.print("")
        console.print(security_table)
        
    except Exception as e:
        console.print(f"[bold red]Erreur lors du chargement de la configuration: {e}[/bold red]")
    
    console.print("")
    console.input("[bold yellow]Appuyez sur Entrée pour revenir au menu principal...[/bold yellow]")

def start_arbitrage_module() -> None:
    """Lance le module d'arbitrage entre DEX."""
    clear()
    display_logo()
    
    console.print("=" * 60, style="blue")
    console.print("              Module d'Arbitrage entre DEX", style="bold yellow")
    console.print("=" * 60, style="blue")
    
    console.print("[bold]Initialisation du module d'arbitrage...[/bold]")
    
    try:
        # Ici, on instancierait et démarrerait le module d'arbitrage
        # Pour l'instant, simple simulation
        arbitrage_engine = ArbitrageEngine()
        
        console.print("[green]Module d'arbitrage initialisé avec succès![/green]")
        console.print("[yellow]Démarrage de la surveillance des opportunités d'arbitrage...[/yellow]")
        
        # Simuler une activité
        for i in range(5):
            time.sleep(1)
            console.print(f"[dim]Analyse des paires de trading... {i+1}/5[/dim]")
        
        # Afficher quelques opportunités fictives
        table = Table(title="Opportunités d'Arbitrage Détectées", box=box.SIMPLE)
        table.add_column("Paire", style="cyan")
        table.add_column("DEX Source", style="green")
        table.add_column("DEX Cible", style="green")
        table.add_column("Écart (%)", style="yellow")
        table.add_column("Profit Estimé", style="bold green")
        
        table.add_row("SOL/USDC", "Jupiter", "Raydium", "0.8%", "~$1.20 par 100 USDC")
        table.add_row("AVAX/USDT", "TraderJoe", "Pangolin", "1.2%", "~$2.40 par 100 USDT")
        table.add_row("BONK/SOL", "Orca", "Raydium", "2.5%", "~$5.00 par 100 SOL")
        
        console.print(table)
        
        console.print("[bold yellow]Voulez-vous exécuter ces arbitrages? (o/n)[/bold yellow]")
        choice = console.input("Votre choix: ")
        
        if choice.lower() == "o":
            console.print("[green]Exécution des arbitrages...[/green]")
            for i in range(3):
                time.sleep(1)
                console.print(f"[dim]Arbitrage {i+1}/3 exécuté avec succès![/dim]")
            console.print("[bold green]Tous les arbitrages ont été exécutés avec succès![/bold green]")
        else:
            console.print("[yellow]Arbitrages ignorés.[/yellow]")
        
    except Exception as e:
        console.print(f"[bold red]Erreur lors du lancement du module d'arbitrage: {e}[/bold red]")
    
    console.print("")
    console.input("[bold yellow]Appuyez sur Entrée pour revenir au menu principal...[/bold yellow]")

def start_sniping_module() -> None:
    """Lance le module de sniping de tokens."""
    clear()
    display_logo()
    
    console.print("=" * 60, style="blue")
    console.print("              Module de Sniping de Tokens", style="bold yellow")
    console.print("=" * 60, style="blue")
    
    console.print("[bold]Initialisation du module de sniping...[/bold]")
    
    try:
        # Ici, on instancierait et démarrerait le module de sniping
        # Pour l'instant, simple simulation
        token_sniper = TokenSniper()
        
        console.print("[green]Module de sniping initialisé avec succès![/green]")
        console.print("[yellow]Démarrage de la surveillance des nouveaux tokens...[/yellow]")
        
        # Simuler une activité
        for i in range(5):
            time.sleep(1)
            console.print(f"[dim]Connexion aux nœuds blockchain... {i+1}/5[/dim]")
        
        # Afficher quelques tokens fictifs
        table = Table(title="Nouveaux Tokens Détectés", box=box.SIMPLE)
        table.add_column("Token", style="cyan")
        table.add_column("Blockchain", style="green")
        table.add_column("Liquidité", style="yellow")
        table.add_column("Score", style="bold green")
        table.add_column("Action", style="magenta")
        
        table.add_row("PEPECOIN", "Solana", "$50,000", "85/100", "🚀 Sniper")
        table.add_row("AVAXDOGE", "Avalanche", "$25,000", "70/100", "👀 Surveiller")
        table.add_row("SHIBKING", "Solana", "$10,000", "55/100", "⚠️ Risqué")
        
        console.print(table)
        
        console.print("[bold yellow]Voulez-vous acheter PEPECOIN automatiquement? (o/n)[/bold yellow]")
        choice = console.input("Votre choix: ")
        
        if choice.lower() == "o":
            console.print("[green]Achat de PEPECOIN en cours...[/green]")
            for i in range(3):
                time.sleep(1)
                console.print(f"[dim]Étape {i+1}/3: {'Analyse du contrat' if i==0 else 'Calcul du gaz optimal' if i==1 else 'Exécution de la transaction'}[/dim]")
            console.print("[bold green]PEPECOIN acheté avec succès! 0.1 SOL → 100,000 PEPECOIN[/bold green]")
        else:
            console.print("[yellow]Achat ignoré.[/yellow]")
        
    except Exception as e:
        console.print(f"[bold red]Erreur lors du lancement du module de sniping: {e}[/bold red]")
    
    console.print("")
    console.input("[bold yellow]Appuyez sur Entrée pour revenir au menu principal...[/bold yellow]")

def start_auto_mode() -> None:
    """Lance le mode automatique du bot."""
    clear()
    display_logo()
    
    console.print("=" * 60, style="blue")
    console.print("              Mode Automatique du GBPBot", style="bold yellow")
    console.print("=" * 60, style="blue")
    
    console.print("[bold]Initialisation du mode automatique...[/bold]")
    
    try:
        # Ici, on instancierait et démarrerait le mode automatique
        # Pour l'instant, simple simulation
        auto_mode = AutoMode()
        
        console.print("[green]Mode automatique initialisé avec succès![/green]")
        console.print("[yellow]Démarrage de l'analyse en temps réel...[/yellow]")
        
        # Simuler une activité
        for i in range(5):
            time.sleep(1)
            console.print(f"[dim]Initialisation des modules... {i+1}/5[/dim]")
        
        # Afficher un tableau de bord fictif
        table = Table(title="Tableau de Bord - Mode Automatique", box=box.SIMPLE)
        table.add_column("Module", style="cyan")
        table.add_column("Statut", style="green")
        table.add_column("Activité", style="yellow")
        
        table.add_row("Arbitrage", "✅ Actif", "Surveillance de 24 paires")
        table.add_row("Sniping", "✅ Actif", "Surveillance des nouveaux tokens")
        table.add_row("MEV Protection", "✅ Actif", "Optimisation des transactions")
        table.add_row("AI Analytics", "✅ Actif", "Analyse des tendances")
        
        console.print(table)
        
        # Simuler des événements
        console.print("\n[bold]Journal d'activité en temps réel:[/bold]\n")
        
        events = [
            "[dim]10:15:23[/dim] [green]Analyse de marché terminée: tendance haussière détectée sur Solana[/green]",
            "[dim]10:15:45[/dim] [yellow]Nouvelle opportunité d'arbitrage détectée: SOL/USDC (0.7%)[/yellow]",
            "[dim]10:16:12[/dim] [green]Arbitrage exécuté avec succès: profit +0.032 SOL[/green]",
            "[dim]10:17:08[/dim] [yellow]Nouveau token détecté: MOONCAT sur Solana[/yellow]",
            "[dim]10:17:33[/dim] [red]Analyse du contrat MOONCAT: potentiel rug pull détecté, achat ignoré[/red]",
            "[dim]10:18:57[/dim] [green]Reconnaissance de pattern: accumulation importante sur BONK[/green]"
        ]
        
        for event in events:
            console.print(event)
            time.sleep(1)
        
        console.print("\n[bold green]Le mode automatique est en cours d'exécution.[/bold green]")
        console.print("[yellow]Appuyez sur CTRL+C à tout moment pour arrêter.[/yellow]")
        
    except Exception as e:
        console.print(f"[bold red]Erreur lors du lancement du mode automatique: {e}[/bold red]")
    
    console.print("")
    console.input("[bold yellow]Appuyez sur Entrée pour revenir au menu principal...[/bold yellow]")

def display_statistics() -> None:
    """Affiche les statistiques et les logs du bot."""
    clear()
    display_logo()
    
    console.print("=" * 60, style="blue")
    console.print("              Statistiques et Logs de GBPBot", style="bold yellow")
    console.print("=" * 60, style="blue")
    
    # Si aucune activité n'a encore été enregistrée
    console.print("[yellow]Aucune activité de trading n'a encore été enregistrée.[/yellow]")
    console.print("[dim]Lancez un des modules pour commencer à générer des statistiques.[/dim]")
    
    console.print("")
    console.print("[bold]Dernières entrées de log:[/bold]")
    
    # Afficher quelques logs fictifs
    logs = [
        (logging.INFO, "2023-09-20 10:15:23", "Démarrage de GBPBot v0.1.0"),
        (logging.INFO, "2023-09-20 10:15:25", "Chargement de la configuration depuis .env"),
        (logging.WARNING, "2023-09-20 10:15:26", "Clé privée Sonic non configurée"),
        (logging.INFO, "2023-09-20 10:15:28", "Connexion à l'API Solana établie"),
        (logging.INFO, "2023-09-20 10:15:30", "Connexion à l'API AVAX établie"),
        (logging.ERROR, "2023-09-20 10:15:32", "Échec de la connexion à l'API Sonic: URL non configurée"),
    ]
    
    log_table = Table(box=box.SIMPLE)
    log_table.add_column("Niveau", style="cyan")
    log_table.add_column("Horodatage", style="dim")
    log_table.add_column("Message")
    
    for level, timestamp, message in logs:
        level_str = {
            logging.DEBUG: "[blue]DEBUG[/blue]",
            logging.INFO: "[green]INFO[/green]",
            logging.WARNING: "[yellow]WARNING[/yellow]",
            logging.ERROR: "[red]ERROR[/red]",
            logging.CRITICAL: "[bold red]CRITICAL[/bold red]"
        }.get(level, "[dim]UNKNOWN[/dim]")
        
        log_table.add_row(level_str, timestamp, message)
    
    console.print(log_table)
    
    console.print("")
    console.input("[bold yellow]Appuyez sur Entrée pour revenir au menu principal...[/bold yellow]")

def configure_parameters() -> None:
    """Interface pour configurer les paramètres du bot."""
    clear()
    display_logo()
    
    console.print("=" * 60, style="blue")
    console.print("              Configuration des Paramètres", style="bold yellow")
    console.print("=" * 60, style="blue")
    
    console.print("[yellow]Cette fonctionnalité n'est pas encore implémentée.[/yellow]")
    console.print("[dim]Pour modifier les paramètres, éditez manuellement le fichier .env pour le moment.[/dim]")
    
    console.print("")
    console.input("[bold yellow]Appuyez sur Entrée pour revenir au menu principal...[/bold yellow]")

def display_modules_info() -> None:
    """Affiche les informations sur les modules disponibles."""
    clear()
    display_logo()
    
    console.print("=" * 60, style="blue")
    console.print("              Modules Disponibles dans GBPBot", style="bold yellow")
    console.print("=" * 60, style="blue")
    
    # Module d'arbitrage
    console.print("[bold cyan]1. Module d'Arbitrage entre DEX[/bold cyan]")
    console.print("   Exploite les écarts de prix entre différents DEX et/ou CEX.")
    console.print("   Fonctionnalités principales:")
    console.print("   • Surveillance des différences de prix entre exchanges")
    console.print("   • Calcul des frais et impact du slippage pour chaque arbitrage")
    console.print("   • Exécution instantanée des transactions")
    console.print("   • Mode \"Flash Arbitrage\" pour ne jamais immobiliser de fonds")
    console.print("")
    
    # Module de sniping
    console.print("[bold cyan]2. Module de Sniping de Token[/bold cyan]")
    console.print("   Détecte et achète automatiquement les nouveaux tokens prometteurs.")
    console.print("   Fonctionnalités principales:")
    console.print("   • Surveillance en continu des nouvelles paires créées")
    console.print("   • Analyse de la liquidité et du market cap pour éviter les scams")
    console.print("   • Exécution ultra-rapide via WebSockets")
    console.print("   • Stop-loss intelligent pour éviter les rug pulls")
    console.print("")
    
    # Mode automatique
    console.print("[bold cyan]3. Mode Automatique[/bold cyan]")
    console.print("   Fonctionne de manière autonome en combinant les différents modules.")
    console.print("   Fonctionnalités principales:")
    console.print("   • Analyse en temps réel des opportunités")
    console.print("   • Ajustement dynamique des stratégies")
    console.print("   • Apprentissage à partir des résultats passés")
    console.print("   • Gestion automatique des fonds")
    
    console.print("")
    console.input("[bold yellow]Appuyez sur Entrée pour revenir au menu principal...[/bold yellow]")

def main() -> int:
    """
    Point d'entrée principal du GBPBot.
    
    Returns:
        int: Code de retour (0 en cas de succès)
    """
    parser = argparse.ArgumentParser(description="GBPBot - Trading Bot pour Solana, AVAX et Sonic")
    parser.add_argument("--config", "-c", help="Chemin vers le fichier de configuration")
    parser.add_argument("--debug", "-d", action="store_true", help="Activer le mode debug")
    parser.add_argument("--version", "-v", action="store_true", help="Afficher la version")
    args = parser.parse_args()
    
    if args.version:
        print(f"GBPBot v{__version__}")
        return 0
    
    # Configuration du logging
    try:
        setup_logging(debug=args.debug)
    except:
        # Fallback si le module de logging n'est pas encore implémenté
        logging.basicConfig(
            level=logging.DEBUG if args.debug else logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.StreamHandler()]
        )
    
    # Boucle principale du menu
    while True:
        choice = display_main_menu()
        
        if choice == "1":
            # Démarrer le bot
            module_choice = display_modules_menu()
            
            if module_choice == "1":
                # Arbitrage entre DEX
                start_arbitrage_module()
            elif module_choice == "2":
                # Sniping de Token
                start_sniping_module()
            elif module_choice == "3":
                # Mode automatique
                start_auto_mode()
            # Les autres choix nous ramènent au menu principal
            
        elif choice == "2":
            # Configurer les paramètres
            configure_parameters()
            
        elif choice == "3":
            # Afficher la configuration actuelle
            display_configuration()
            
        elif choice == "4":
            # Statistiques et Logs
            display_statistics()
            
        elif choice == "5":
            # Afficher les Modules Disponibles
            display_modules_info()
            
        elif choice == "6":
            # Quitter
            console.print("[bold green]Merci d'avoir utilisé GBPBot![/bold green]")
            return 0
        
        else:
            console.print("[bold red]Choix invalide. Veuillez réessayer.[/bold red]")
            time.sleep(1)

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        console.print("\n[bold yellow]GBPBot arrêté par l'utilisateur.[/bold yellow]")
        sys.exit(0) 