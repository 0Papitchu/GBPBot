#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Fonctions d'affichage pour le CLI du GBPBot
==========================================

Ce module fournit des fonctions utilitaires pour l'affichage
dans l'interface en ligne de commande (CLI) du GBPBot.
"""

import os
import sys
import platform
from typing import Dict, Any, Optional

class Colors:
    """Couleurs ANSI pour le terminal"""
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'

def clear_screen():
    """
    Efface l'écran du terminal de manière compatible avec différents OS
    """
    if platform.system() == "Windows":
        os.system("cls")
    else:
        os.system("clear")

def print_banner():
    """
    Affiche la bannière du GBPBot
    """
    banner = f"""
{Colors.CYAN}
  ▄████  ▄▄▄▄    ▄▄▄▄    ▄▄▄▄    ▒█████  ▄▄▄█████▓
 ██▒ ▀█▒▓█████▄ ▓█████▄ ▓█████▄ ▒██▒  ██▒▓  ██▒ ▓▒
▒██░▄▄▄░▒██▒ ▄██▒██▒ ▄██▒██▒ ▄██▒██░  ██▒▒ ▓██░ ▒░
░▓█  ██▓▒██░█▀  ▒██░█▀  ▒██░█▀  ▒██   ██░░ ▓██▓ ░ 
░▒▓███▀▒░▓█  ▀█▓░▓█  ▀█▓░▓█  ▀█▓░ ████▓▒░  ▒██▒ ░ 
 ░▒   ▒ ░▒▓███▀▒░▒▓███▀▒░▒▓███▀▒░ ▒░▒░▒░   ▒ ░░   
  ░   ░ ▒░▒   ░ ▒░▒   ░ ▒░▒   ░   ░ ▒ ▒░     ░    
░ ░   ░  ░    ░  ░    ░  ░    ░ ░ ░ ░ ▒    ░      
      ░  ░       ░       ░          ░ ░           
             ░       ░       ░                    
{Colors.ENDC}
{Colors.BOLD}💰 Trading Bot Ultra-Rapide pour MEME Coins 💰{Colors.ENDC}
"""
    print(banner)

def print_header(text: str):
    """
    Affiche un en-tête formaté
    
    Args:
        text: Texte à afficher
    """
    width = 60
    print(f"\n{Colors.CYAN}{'=' * width}")
    print(f"{text.center(width)}")
    print(f"{'=' * width}{Colors.ENDC}")

def print_menu_option(number: int, text: str):
    """
    Affiche une option de menu formatée
    
    Args:
        number: Numéro de l'option
        text: Texte de l'option
    """
    print(f"{Colors.YELLOW}{number}.{Colors.ENDC} {text}")

def print_status(label: str, status: bool):
    """
    Affiche un statut coloré (succès/échec)
    
    Args:
        label: Libellé du statut
        status: True pour succès, False pour échec
    """
    status_text = f"{Colors.GREEN}✓ Actif{Colors.ENDC}" if status else f"{Colors.RED}✗ Inactif{Colors.ENDC}"
    print(f"{label}: {status_text}")

def print_table(headers: list, data: list, title: Optional[str] = None):
    """
    Affiche un tableau formaté
    
    Args:
        headers: Liste des en-têtes de colonnes
        data: Liste de listes ou de dictionnaires pour les données
        title: Titre du tableau (optionnel)
    """
    if not data:
        print("Aucune donnée à afficher")
        return
    
    # Déterminer la largeur des colonnes
    col_widths = [len(h) for h in headers]
    
    for row in data:
        if isinstance(row, dict):
            row_values = [str(row.get(h, "")) for h in headers]
        else:
            row_values = [str(val) if val is not None else "" for val in row]
        
        for i, val in enumerate(row_values):
            col_widths[i] = max(col_widths[i], len(val))
    
    # Ajouter un peu d'espace pour l'esthétique
    col_widths = [w + 2 for w in col_widths]
    
    # Calculer la largeur totale du tableau
    total_width = sum(col_widths) + len(headers) - 1
    
    # Afficher le titre si fourni
    if title:
        print(f"\n{Colors.BOLD}{title}{Colors.ENDC}")
    
    # Ligne de séparation
    separator = "+" + "+".join("-" * w for w in col_widths) + "+"
    
    # En-têtes
    header_row = "|"
    for i, header in enumerate(headers):
        header_row += f"{Colors.BOLD}{header.center(col_widths[i])}{Colors.ENDC}|"
    
    print(separator)
    print(header_row)
    print(separator)
    
    # Données
    for row in data:
        if isinstance(row, dict):
            row_values = [str(row.get(h, "")) for h in headers]
        else:
            row_values = [str(val) if val is not None else "" for val in row]
        
        row_str = "|"
        for i, val in enumerate(row_values):
            row_str += f"{val.ljust(col_widths[i])}|"
        
        print(row_str)
    
    print(separator)

def format_currency(value: float, currency: str = "USD") -> str:
    """
    Formate un montant en devise
    
    Args:
        value: Valeur à formater
        currency: Code de la devise
        
    Returns:
        Chaîne formatée
    """
    if currency == "USD":
        return f"${value:,.2f}"
    elif currency == "EUR":
        return f"€{value:,.2f}"
    else:
        return f"{value:,.2f} {currency}"

def format_percentage(value: float) -> str:
    """
    Formate un pourcentage
    
    Args:
        value: Valeur à formater (0.1 pour 10%)
        
    Returns:
        Chaîne formatée
    """
    color = Colors.GREEN if value >= 0 else Colors.RED
    return f"{color}{value:.2%}{Colors.ENDC}" 