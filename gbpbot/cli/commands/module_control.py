#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Contrôle des modules pour le CLI de GBPBot
========================================

Ce module fournit des fonctions pour contrôler (démarrer, arrêter, surveiller)
les différents modules du GBPBot via l'interface CLI.
"""

import os
import logging
import asyncio
from typing import Dict, Any, Optional, List

# Configuration du logging
logger = logging.getLogger("gbpbot.cli.commands.module_control")

# Importer les fonctions d'affichage
from gbpbot.cli.display import (
    clear_screen,
    print_banner,
    print_header,
    print_menu_option,
    print_status,
    Colors
)

# État simulé des modules
active_modules = {}

async def stop_module(module_name: str = None):
    """
    Arrête un module spécifique ou propose une liste de modules à arrêter
    
    Args:
        module_name: Nom du module à arrêter (optionnel)
    """
    global active_modules
    
    if not module_name:
        # Afficher la liste des modules actifs et demander lequel arrêter
        clear_screen()
        print_banner()
        
        print_header("ARRÊT DE MODULE")
        
        if not active_modules:
            print(f"\n{Colors.YELLOW}Aucun module n'est actuellement actif.{Colors.ENDC}")
            input("\nAppuyez sur Entrée pour revenir au menu principal...")
            
            # Retourner au menu principal
            from gbpbot.cli.menu import display_main_menu
            await display_main_menu()
            return
        
        print("\nModules actuellement actifs:\n")
        
        # Afficher les modules actifs
        for i, (module, status) in enumerate(active_modules.items(), 1):
            print_menu_option(i, f"{module} (Actif depuis {status['start_time']})")
        
        print_menu_option(len(active_modules) + 1, "Arrêter tous les modules")
        print_menu_option(len(active_modules) + 2, "Retour au menu principal")
        
        # Demander quel module arrêter
        choice = input("\nVeuillez choisir un module à arrêter (1-{}): ".format(len(active_modules) + 2))
        
        try:
            choice_num = int(choice)
            if 1 <= choice_num <= len(active_modules):
                # Arrêter le module spécifique
                module_name = list(active_modules.keys())[choice_num - 1]
                await stop_specific_module(module_name)
            elif choice_num == len(active_modules) + 1:
                # Arrêter tous les modules
                await stop_all_modules()
            elif choice_num == len(active_modules) + 2:
                # Retour au menu principal
                from gbpbot.cli.menu import display_main_menu
                await display_main_menu()
            else:
                print("\nOption invalide. Veuillez réessayer.")
                input("Appuyez sur Entrée pour continuer...")
                await stop_module()
        except ValueError:
            print("\nOption invalide. Veuillez entrer un numéro.")
            input("Appuyez sur Entrée pour continuer...")
            await stop_module()
    else:
        # Arrêter le module spécifié
        await stop_specific_module(module_name)

async def stop_specific_module(module_name: str):
    """
    Arrête un module spécifique
    
    Args:
        module_name: Nom du module à arrêter
    """
    global active_modules
    
    if module_name not in active_modules:
        print(f"\n{Colors.YELLOW}Le module {module_name} n'est pas actif.{Colors.ENDC}")
        input("\nAppuyez sur Entrée pour continuer...")
        await stop_module()
        return
    
    # Simuler l'arrêt du module
    print(f"\nArrêt du module {module_name}...")
    await asyncio.sleep(1)
    
    # Supprimer le module de la liste des modules actifs
    del active_modules[module_name]
    
    print(f"\n{Colors.GREEN}Module {module_name} arrêté avec succès!{Colors.ENDC}")
    input("\nAppuyez sur Entrée pour continuer...")
    
    # Retourner au menu principal
    from gbpbot.cli.menu import display_main_menu
    await display_main_menu()

async def stop_all_modules():
    """
    Arrête tous les modules actifs
    """
    global active_modules
    
    if not active_modules:
        print(f"\n{Colors.YELLOW}Aucun module n'est actuellement actif.{Colors.ENDC}")
        input("\nAppuyez sur Entrée pour continuer...")
        await stop_module()
        return
    
    # Simuler l'arrêt de tous les modules
    print("\nArrêt de tous les modules...")
    
    module_count = len(active_modules)
    module_names = list(active_modules.keys())
    
    for i, module_name in enumerate(module_names, 1):
        print(f"Arrêt du module {module_name} ({i}/{module_count})...")
        await asyncio.sleep(0.5)
    
    # Vider la liste des modules actifs
    active_modules.clear()
    
    print(f"\n{Colors.GREEN}Tous les modules ont été arrêtés avec succès!{Colors.ENDC}")
    input("\nAppuyez sur Entrée pour continuer...")
    
    # Retourner au menu principal
    from gbpbot.cli.menu import display_main_menu
    await display_main_menu()

def register_active_module(module_name: str):
    """
    Enregistre un module comme actif
    
    Args:
        module_name: Nom du module à enregistrer
    """
    global active_modules
    
    from datetime import datetime
    
    active_modules[module_name] = {
        "start_time": datetime.now().strftime("%H:%M:%S"),
        "status": "running"
    }
    
    logger.info(f"Module {module_name} enregistré comme actif")

def is_module_active(module_name: str) -> bool:
    """
    Vérifie si un module est actif
    
    Args:
        module_name: Nom du module à vérifier
        
    Returns:
        bool: True si le module est actif, False sinon
    """
    global active_modules
    
    return module_name in active_modules 