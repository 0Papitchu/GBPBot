#!/usr/bin/env python
"""
GBPBot Agent IA - Interface de démonstration pour l'Agent IA
Ce module démontre les capacités de l'agent IA de GBPBot avec un menu interactif.
"""
import os
import sys
import asyncio
import argparse
from time import sleep
from typing import Callable, Dict, Optional, Any
from pathlib import Path

# Assurer que gbpbot est dans le path
PROJECT_ROOT = str(Path(__file__).parent.parent.absolute())
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

try:
    from colorama import init, Fore, Style
    init()  # Initialiser colorama
except ImportError:
    # Fallback si colorama n'est pas installé
    class DummyColor:
        def __getattr__(self, name):
            return ""
    class DummyStyle:
        def __getattr__(self, name):
            return ""
    Fore = DummyColor()
    Style = DummyStyle()

# Import conditionnel pour gérer l'absence de LangChain
try:
    from gbpbot.ai.agent_manager import (
        create_agent_manager, 
        AgentManager, 
        AgentAutonomyLevel
    )
    is_langchain_available = True
except ImportError:
    is_langchain_available = False

# Fonctions utilitaires d'affichage
def print_title(title: str) -> None:
    """Affiche un titre formaté."""
    print(f"\n{Fore.CYAN}{Style.BRIGHT}{title}{Style.RESET_ALL}")

def print_error(message: str) -> None:
    """Affiche un message d'erreur."""
    print(f"{Fore.RED}{Style.BRIGHT}[ERREUR] {message}{Style.RESET_ALL}")

def print_success(message: str) -> None:
    """Affiche un message de succès."""
    print(f"{Fore.GREEN}{Style.BRIGHT}{message}{Style.RESET_ALL}")

def print_info(message: str) -> None:
    """Affiche un message d'information."""
    print(f"{Fore.BLUE}{message}{Style.RESET_ALL}")

def clear_screen() -> None:
    """Nettoie l'écran du terminal."""
    os.system('cls' if os.name == 'nt' else 'clear')

# Fonction de callback pour approbation utilisateur
async def user_approval_callback(operation: str, params: Dict[str, Any]) -> bool:
    """
    Demande l'approbation de l'utilisateur pour une opération.
    
    Args:
        operation: Description de l'opération à approuver
        params: Paramètres de l'opération
        
    Returns:
        bool: True si approuvé, False sinon
    """
    print_info("\n=== Approbation Requise ===")
    print(f"Opération: {operation}")
    print(f"Paramètres: {params}")
    
    while True:
        response = input(f"{Fore.YELLOW}Approuver cette action? (o/n): {Style.RESET_ALL}").lower()
        if response in ['o', 'oui', 'y', 'yes']:
            return True
        elif response in ['n', 'non', 'no']:
            return False
        print("Veuillez répondre par 'o' (oui) ou 'n' (non)")

# Vérifications initiales
def check_environment() -> bool:
    """
    Vérifie si l'environnement est correctement configuré.
    
    Returns:
        bool: True si l'environnement est correctement configuré
    """
    # Vérifier si LangChain est disponible
    if not is_langchain_available:
        print_error(
            "LangChain n'est pas disponible. Veuillez l'installer avec:\n"
            "pip install -r requirements-agent.txt"
        )
        return False
    
    # Vérifier si les variables d'environnement sont configurées
    env_file = os.path.join(PROJECT_ROOT, '.env.local')
    if not os.path.exists(env_file):
        print_error(
            "Fichier .env.local non trouvé.\n"
            "Veuillez configurer vos variables d'environnement."
        )
        return False
    
    return True

# Fonctions du menu
async def analyze_market(agent: AgentManager) -> None:
    """
    Lance une analyse de marché avec l'Agent IA.
    
    Args:
        agent: Instance de l'Agent IA
    """
    print_title("Analyse du marché en cours...")
    
    try:
        result = await agent.run_agent(
            "Analyse le marché crypto actuel, en particulier SOL, AVAX et les meme coins populaires. "
            "Identifie les tendances principales et fais 2-3 recommandations basées sur les données du marché."
        )
        print_info("\nRésultats de l'analyse:")
        print(result)
    except Exception as e:
        print_error(f"Erreur lors de l'analyse: {str(e)}")

async def find_arbitrage(agent: AgentManager) -> None:
    """
    Recherche des opportunités d'arbitrage.
    
    Args:
        agent: Instance de l'Agent IA
    """
    print_title("Recherche d'opportunités d'arbitrage...")
    
    try:
        result = await agent.run_agent(
            "Identifie les meilleures opportunités d'arbitrage actuelles entre différents DEX "
            "sur Solana et Avalanche. Calcule les profits potentiels et évalue les risques."
        )
        print_info("\nOpportunités d'arbitrage:")
        print(result)
    except Exception as e:
        print_error(f"Erreur lors de la recherche: {str(e)}")

async def snipe_tokens(agent: AgentManager) -> None:
    """
    Analyse les tokens à sniper.
    
    Args:
        agent: Instance de l'Agent IA
    """
    print_title("Analyse des nouveaux tokens...")
    
    try:
        result = await agent.run_agent(
            "Identifie les nouveaux tokens les plus prometteurs à surveiller ou sniper "
            "dans les prochaines heures. Évalue leurs métriques, communauté et risques."
        )
        print_info("\nTokens à potentiel:")
        print(result)
    except Exception as e:
        print_error(f"Erreur lors de l'analyse: {str(e)}")

async def autonomous_mode(agent: AgentManager) -> None:
    """
    Lance le mode autonome pour une courte démo.
    
    Args:
        agent: Instance de l'Agent IA
    """
    print_title("Lancement du mode autonome (démo 5min)...")
    print_info("L'agent va exécuter des analyses et proposer des actions pendant 5 minutes.")
    print_info("Appuyez sur Ctrl+C pour arrêter à tout moment.")
    
    try:
        # Créer un agent plus autonome pour cette démo
        demo_agent = create_agent_manager(
            autonomy_level="autonomous",
            require_approval_callback=user_approval_callback
        )
        
        start_time = asyncio.get_event_loop().time()
        while asyncio.get_event_loop().time() - start_time < 300:  # 5 minutes
            task = asyncio.create_task(demo_agent.run_agent(
                "Surveille le marché et les opportunités en temps réel. "
                "Si tu trouves quelque chose d'intéressant, analyse-le et propose une action."
            ))
            result = await task
            print_info("\nRésultat de l'analyse autonome:")
            print(result)
            await asyncio.sleep(30)  # Pause de 30 secondes entre les analyses
            
        print_success("Démonstration du mode autonome terminée.")
    except KeyboardInterrupt:
        print_info("\nMode autonome interrompu par l'utilisateur.")
    except Exception as e:
        print_error(f"Erreur en mode autonome: {str(e)}")

# Menu principal
async def show_menu(agent: Optional[AgentManager] = None) -> None:
    """
    Affiche le menu interactif de l'Agent IA.
    
    Args:
        agent: Instance de l'Agent IA (optionnel)
    """
    if not agent and is_langchain_available:
        # Créer l'agent s'il n'est pas fourni
        agent = create_agent_manager(
            autonomy_level="hybrid",
            require_approval_callback=user_approval_callback
        )
    
    if not agent:
        print_error("Impossible de créer l'agent IA. Vérifiez votre configuration.")
        return
    
    while True:
        clear_screen()
        print_title("=== Menu Agent IA ===")
        print("1. Analyse du marché et recommandation")
        print("2. Recherche d'opportunités d'arbitrage")
        print("3. Détection et sniping de nouveaux tokens")
        print("4. Mode autonome (démo 5min)")
        print("5. Quitter")
        
        choice = input(f"\n{Fore.YELLOW}Choisissez une option: {Style.RESET_ALL}")
        
        try:
            if choice == "1":
                await analyze_market(agent)
            elif choice == "2":
                await find_arbitrage(agent)
            elif choice == "3":
                await snipe_tokens(agent)
            elif choice == "4":
                await autonomous_mode(agent)
            elif choice == "5":
                print_info("Au revoir!")
                break
            else:
                print_error("Option invalide. Veuillez réessayer.")
            
            input("\nAppuyez sur Entrée pour continuer...")
        except Exception as e:
            print_error(f"Erreur: {str(e)}")
            input("\nAppuyez sur Entrée pour continuer...")

def main() -> None:
    """Fonction principale."""
    # Configuration des arguments de ligne de commande
    parser = argparse.ArgumentParser(description="Interface pour l'Agent IA du GBPBot")
    parser.add_argument(
        "--autonomy", 
        choices=["semi_autonomous", "autonomous", "hybrid"],
        default="hybrid",
        help="Niveau d'autonomie de l'agent (défaut: hybrid)"
    )
    args = parser.parse_args()
    
    # Vérification de l'environnement
    if not check_environment():
        print_error("Configuration requise non satisfaite. Sortie du programme.")
        return
    
    try:
        # Lancer le menu avec asyncio
        asyncio.run(show_menu())
    except KeyboardInterrupt:
        print_info("\nProgramme interrompu par l'utilisateur.")
    except Exception as e:
        print_error(f"Erreur inattendue: {str(e)}")

if __name__ == "__main__":
    main() 