#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Module de gestion des claviers pour le bot Telegram GBPBot.

Ce module fournit des fonctions utilitaires pour créer différents types de claviers
pour l'interface Telegram.
"""

import logging
from typing import Dict, List, Optional, Tuple, Union, Any, Callable

# Import conditionnel pour gérer les cas où Telegram n'est pas installé
try:
    from telegram import (
        InlineKeyboardButton, InlineKeyboardMarkup,
        ReplyKeyboardMarkup, ReplyKeyboardRemove, KeyboardButton
    )
    TELEGRAM_AVAILABLE = True
except ImportError:
    logging.getLogger(__name__).warning("Module python-telegram-bot non disponible")
    TELEGRAM_AVAILABLE = False
    # Créer des types substituts pour permettre au code de fonctionner sans dépendance
    class InlineKeyboardButton:
        def __init__(self, text, **kwargs):
            self.text = text
            for key, value in kwargs.items():
                setattr(self, key, value)

    class InlineKeyboardMarkup:
        def __init__(self, inline_keyboard):
            self.inline_keyboard = inline_keyboard

    class KeyboardButton:
        def __init__(self, text, **kwargs):
            self.text = text
            for key, value in kwargs.items():
                setattr(self, key, value)

    class ReplyKeyboardMarkup:
        def __init__(self, keyboard, **kwargs):
            self.keyboard = keyboard
            for key, value in kwargs.items():
                setattr(self, key, value)

    class ReplyKeyboardRemove:
        def __init__(self, remove_keyboard=True):
            self.remove_keyboard = remove_keyboard


# Configuration du logger
logger = logging.getLogger("gbpbot.telegram.keyboards")


def create_menu_keyboard(
    items: List[Tuple[str, str]], 
    columns: int = 1,
    footer_items: Optional[List[Tuple[str, str]]] = None
) -> Optional[InlineKeyboardMarkup]:
    """
    Crée un clavier de menu à partir d'une liste de tuples (texte, callback).
    
    Args:
        items: Liste de tuples (texte, callback_data)
        columns: Nombre de colonnes pour le clavier
        footer_items: Éléments à ajouter en bas du clavier (optionnel)
        
    Returns:
        Clavier inline ou None si Telegram n'est pas disponible
    """
    if not TELEGRAM_AVAILABLE:
        logger.warning("Tentative de création de clavier sans dépendance Telegram")
        return None
        
    if not items:
        logger.warning("Tentative de création d'un clavier vide")
        return None
        
    keyboard = []
    row = []
    
    # Ajouter les éléments principaux
    for text, callback in items:
        row.append(InlineKeyboardButton(text, callback_data=callback))
        if len(row) >= columns:
            keyboard.append(row)
            row = []
    
    # Ajouter la dernière ligne si non vide
    if row:
        keyboard.append(row)
    
    # Ajouter les éléments de pied de page
    if footer_items:
        for text, callback in footer_items:
            keyboard.append([InlineKeyboardButton(text, callback_data=callback)])
    
    return InlineKeyboardMarkup(keyboard)


def create_confirmation_keyboard(
    confirm_callback: str, 
    cancel_callback: str,
    confirm_text: str = "✅ Confirmer",
    cancel_text: str = "❌ Annuler"
) -> Optional[InlineKeyboardMarkup]:
    """
    Crée un clavier de confirmation avec des boutons Confirmer/Annuler.
    
    Args:
        confirm_callback: Callback pour la confirmation
        cancel_callback: Callback pour l'annulation
        confirm_text: Texte du bouton de confirmation
        cancel_text: Texte du bouton d'annulation
        
    Returns:
        Clavier inline ou None si Telegram n'est pas disponible
    """
    if not TELEGRAM_AVAILABLE:
        logger.warning("Tentative de création de clavier sans dépendance Telegram")
        return None
        
    keyboard = [
        [
            InlineKeyboardButton(confirm_text, callback_data=confirm_callback),
            InlineKeyboardButton(cancel_text, callback_data=cancel_callback)
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def create_navigation_keyboard(
    current_page: int,
    total_pages: int,
    base_callback: str,
    item_callbacks: Optional[List[Tuple[str, str]]] = None,
    back_callback: Optional[str] = None
) -> Optional[InlineKeyboardMarkup]:
    """
    Crée un clavier de navigation paginée.
    
    Args:
        current_page: Page actuelle (base 1)
        total_pages: Nombre total de pages
        base_callback: Callback de base pour la navigation (ex: "page:")
        item_callbacks: Liste de tuples (texte, callback) pour les éléments de la page
        back_callback: Callback pour le bouton retour (optionnel)
        
    Returns:
        Clavier inline ou None si Telegram n'est pas disponible
    """
    if not TELEGRAM_AVAILABLE:
        logger.warning("Tentative de création de clavier sans dépendance Telegram")
        return None
        
    keyboard = []
    
    # Ajouter les éléments de la page
    if item_callbacks:
        for text, callback in item_callbacks:
            keyboard.append([InlineKeyboardButton(text, callback_data=callback)])
    
    # Créer la barre de navigation
    nav_row = []
    
    # Bouton précédent
    if current_page > 1:
        nav_row.append(InlineKeyboardButton("◀️", callback_data=f"{base_callback}{current_page-1}"))
    else:
        nav_row.append(InlineKeyboardButton("•", callback_data="noop"))
    
    # Indicateur de page
    nav_row.append(InlineKeyboardButton(f"{current_page}/{total_pages}", callback_data="noop"))
    
    # Bouton suivant
    if current_page < total_pages:
        nav_row.append(InlineKeyboardButton("▶️", callback_data=f"{base_callback}{current_page+1}"))
    else:
        nav_row.append(InlineKeyboardButton("•", callback_data="noop"))
    
    keyboard.append(nav_row)
    
    # Ajouter le bouton retour si nécessaire
    if back_callback:
        keyboard.append([InlineKeyboardButton("🔙 Retour", callback_data=back_callback)])
    
    return InlineKeyboardMarkup(keyboard)


def create_grid_keyboard(
    items: List[Dict[str, Any]],
    text_key: str,
    callback_key: str,
    columns: int = 2,
    footer_items: Optional[List[Tuple[str, str]]] = None
) -> Optional[InlineKeyboardMarkup]:
    """
    Crée un clavier en grille à partir d'une liste d'objets.
    
    Args:
        items: Liste d'objets contenant les données des boutons
        text_key: Clé pour extraire le texte des boutons
        callback_key: Clé pour extraire les callbacks des boutons
        columns: Nombre de colonnes pour le clavier
        footer_items: Éléments à ajouter en bas du clavier (optionnel)
        
    Returns:
        Clavier inline ou None si Telegram n'est pas disponible
    """
    if not TELEGRAM_AVAILABLE:
        logger.warning("Tentative de création de clavier sans dépendance Telegram")
        return None
        
    if not items:
        logger.warning("Tentative de création d'un clavier vide")
        return None
        
    # Convertir les objets en tuples (texte, callback)
    button_tuples = []
    for item in items:
        try:
            text = str(item.get(text_key, "Unknown"))
            callback = str(item.get(callback_key, "noop"))
            button_tuples.append((text, callback))
        except (KeyError, AttributeError) as e:
            logger.error(f"Erreur lors de la création du bouton: {e}")
            continue
    
    return create_menu_keyboard(button_tuples, columns, footer_items)


def create_settings_keyboard(
    settings: Dict[str, Union[bool, str, int, float]],
    callback_prefix: str = "set:",
    back_callback: Optional[str] = None
) -> Optional[InlineKeyboardMarkup]:
    """
    Crée un clavier pour les paramètres avec indicateurs d'état.
    
    Args:
        settings: Dictionnaire des paramètres avec leurs valeurs
        callback_prefix: Préfixe pour les callbacks
        back_callback: Callback pour le bouton retour (optionnel)
        
    Returns:
        Clavier inline ou None si Telegram n'est pas disponible
    """
    if not TELEGRAM_AVAILABLE:
        logger.warning("Tentative de création de clavier sans dépendance Telegram")
        return None
        
    if not settings:
        logger.warning("Tentative de création d'un clavier de paramètres vide")
        return None
        
    keyboard = []
    
    for key, value in settings.items():
        # Formater le texte selon le type de valeur
        if isinstance(value, bool):
            status = "✅" if value else "❌"
            text = f"{key}: {status}"
        else:
            text = f"{key}: {value}"
        
        # Créer le bouton
        callback = f"{callback_prefix}{key}"
        keyboard.append([InlineKeyboardButton(text, callback_data=callback)])
    
    # Ajouter le bouton retour si nécessaire
    if back_callback:
        keyboard.append([InlineKeyboardButton("🔙 Retour", callback_data=back_callback)])
    
    return InlineKeyboardMarkup(keyboard)


def create_trading_actions_keyboard(
    token_symbol: str,
    token_address: Optional[str] = None,
    include_monitoring: bool = True,
    include_auto_sell: bool = True
) -> Optional[InlineKeyboardMarkup]:
    """
    Crée un clavier avec des actions de trading pour un token spécifique.
    
    Args:
        token_symbol: Symbole du token
        token_address: Adresse du contrat du token (optionnel)
        include_monitoring: Inclure les options de surveillance
        include_auto_sell: Inclure les options de vente automatique
        
    Returns:
        Clavier inline ou None si Telegram n'est pas disponible
    """
    if not TELEGRAM_AVAILABLE:
        logger.warning("Tentative de création de clavier sans dépendance Telegram")
        return None
        
    keyboard = []
    token_data = token_address if token_address else token_symbol
    
    # Actions de base
    row1 = [
        InlineKeyboardButton("🟢 Acheter", callback_data=f"buy:{token_data}"),
        InlineKeyboardButton("🔴 Vendre", callback_data=f"sell:{token_data}")
    ]
    keyboard.append(row1)
    
    # Actions avancées
    row2 = [
        InlineKeyboardButton("📊 Charts", callback_data=f"chart:{token_data}"),
        InlineKeyboardButton("ℹ️ Info", callback_data=f"info:{token_data}")
    ]
    keyboard.append(row2)
    
    # Options de surveillance
    if include_monitoring:
        row3 = [
            InlineKeyboardButton("🔔 Alerte", callback_data=f"alert:{token_data}"),
            InlineKeyboardButton("👁️ Surveiller", callback_data=f"watch:{token_data}")
        ]
        keyboard.append(row3)
    
    # Options de vente automatique
    if include_auto_sell:
        keyboard.append([
            InlineKeyboardButton("🤖 Auto-vente", callback_data=f"auto_sell:{token_data}")
        ])
    
    # Bouton retour
    keyboard.append([
        InlineKeyboardButton("🔙 Retour", callback_data="menu:main")
    ])
    
    return InlineKeyboardMarkup(keyboard)


def create_yes_no_keyboard(
    yes_callback: str,
    no_callback: str,
    yes_text: str = "✅ Oui",
    no_text: str = "❌ Non"
) -> Optional[InlineKeyboardMarkup]:
    """
    Crée un clavier simple avec des boutons Oui/Non.
    
    Args:
        yes_callback: Callback pour le bouton Oui
        no_callback: Callback pour le bouton Non
        yes_text: Texte du bouton Oui
        no_text: Texte du bouton Non
        
    Returns:
        Clavier inline ou None si Telegram n'est pas disponible
    """
    if not TELEGRAM_AVAILABLE:
        logger.warning("Tentative de création de clavier sans dépendance Telegram")
        return None
        
    keyboard = [
        [
            InlineKeyboardButton(yes_text, callback_data=yes_callback),
            InlineKeyboardButton(no_text, callback_data=no_callback)
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def create_amount_selection_keyboard(
    action: str,
    token: str,
    amounts: List[float] = None,
    custom_callback: str = None
) -> Optional[InlineKeyboardMarkup]:
    """
    Crée un clavier pour la sélection de montants.
    
    Args:
        action: Action (buy/sell)
        token: Symbole du token
        amounts: Liste des montants prédéfinis (par défaut: [25, 50, 75, 100])
        custom_callback: Callback pour le montant personnalisé
        
    Returns:
        Clavier inline ou None si Telegram n'est pas disponible
    """
    if not TELEGRAM_AVAILABLE:
        logger.warning("Tentative de création de clavier sans dépendance Telegram")
        return None
        
    if amounts is None:
        amounts = [25, 50, 75, 100]
        
    if not custom_callback:
        custom_callback = f"custom_amount:{action}:{token}"
        
    keyboard = []
    row = []
    
    # Créer les boutons pour les montants prédéfinis
    for i, amount in enumerate(amounts):
        row.append(InlineKeyboardButton(
            f"{amount}$", 
            callback_data=f"amount:{action}:{token}:{amount}"
        ))
        
        if (i + 1) % 2 == 0 or i == len(amounts) - 1:
            keyboard.append(row)
            row = []
    
    # Ajouter les boutons pour montant personnalisé et retour
    keyboard.append([
        InlineKeyboardButton("💰 Montant personnalisé", callback_data=custom_callback)
    ])
    
    keyboard.append([
        InlineKeyboardButton("🔙 Retour", callback_data=f"cancel:{action}:{token}")
    ])
    
    return InlineKeyboardMarkup(keyboard)


def create_remove_keyboard() -> Optional[ReplyKeyboardRemove]:
    """
    Crée un clavier vide pour supprimer un clavier de réponse.
    
    Returns:
        Objet ReplyKeyboardRemove ou None si Telegram n'est pas disponible
    """
    if not TELEGRAM_AVAILABLE:
        logger.warning("Tentative de création de clavier sans dépendance Telegram")
        return None
        
    return ReplyKeyboardRemove()


def create_reply_keyboard(
    options: List[List[str]],
    one_time: bool = False,
    resize: bool = True,
    selective: bool = False
) -> Optional[ReplyKeyboardMarkup]:
    """
    Crée un clavier de réponse standard.
    
    Args:
        options: Liste de listes de chaînes pour les boutons
        one_time: Si True, le clavier disparaît après utilisation
        resize: Si True, redimensionne le clavier
        selective: Si True, affiche le clavier uniquement pour certains utilisateurs
        
    Returns:
        Clavier de réponse ou None si Telegram n'est pas disponible
    """
    if not TELEGRAM_AVAILABLE:
        logger.warning("Tentative de création de clavier sans dépendance Telegram")
        return None
        
    if not options:
        logger.warning("Tentative de création d'un clavier vide")
        return None
        
    # Convertir les chaînes en boutons
    keyboard = []
    for row in options:
        keyboard_row = []
        for option in row:
            keyboard_row.append(KeyboardButton(option))
        keyboard.append(keyboard_row)
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        one_time_keyboard=one_time,
        resize_keyboard=resize,
        selective=selective
    )


# Test si exécuté directement
if __name__ == "__main__":
    print("Module de claviers Telegram pour GBPBot")
    print("Ce module doit être importé, pas exécuté directement.") 