#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Module de gestion des callbacks pour le bot Telegram GBPBot.

Ce module fournit des fonctions utilitaires pour créer, parser et gérer 
les données de callback des boutons inline.
"""

import json
import logging
import re
from typing import Dict, List, Optional, Tuple, Union, Any, Dict, Callable

# Import conditionnel pour gérer les cas où Telegram n'est pas installé
try:
    from telegram import Update, CallbackQuery
    from telegram.ext import CallbackContext
    TELEGRAM_AVAILABLE = True
except ImportError:
    logging.getLogger(__name__).warning("Module python-telegram-bot non disponible")
    TELEGRAM_AVAILABLE = False
    # Types substituts
    class Update:
        pass
    class CallbackQuery:
        pass
    class CallbackContext:
        pass

# Configuration du logger
logger = logging.getLogger("gbpbot.telegram.callbacks")


def create_callback_data(action: str, *args) -> str:
    """
    Crée une chaîne de données de callback encodée pour les boutons inline.
    
    Format: action:param1:param2:...
    
    Args:
        action: Action à exécuter
        *args: Arguments supplémentaires
        
    Returns:
        Chaîne de données de callback
    """
    data = [action]
    data.extend(str(arg) for arg in args if arg is not None)
    return ":".join(data)


def parse_callback_data(data: str) -> Tuple[str, List[str]]:
    """
    Analyse une chaîne de données de callback.
    
    Format attendu: action:param1:param2:...
    
    Args:
        data: Chaîne de données de callback
        
    Returns:
        Tuple (action, liste d'arguments)
    """
    if not data:
        return "", []
        
    parts = data.split(":")
    action = parts[0] if parts else ""
    args = parts[1:] if len(parts) > 1 else []
    return action, args


def get_callback_data(callback_query: Optional[CallbackQuery], 
                     separator: str = ":") -> Tuple[str, List[str]]:
    """
    Extrait les données du callback_query et les analyse.
    
    Args:
        callback_query: Objet CallbackQuery de Telegram
        separator: Séparateur utilisé dans les données (défaut: ":")
        
    Returns:
        Tuple (action, liste d'arguments)
    """
    if not callback_query or not hasattr(callback_query, 'data') or not callback_query.data:
        return "", []
    
    return parse_callback_data(callback_query.data)


def create_json_callback_data(action: str, **kwargs) -> str:
    """
    Crée une chaîne de données de callback au format JSON compressé.
    Utile pour les données complexes qui ne se prêtent pas bien au format séparé par des deux-points.
    
    Args:
        action: Action à exécuter
        **kwargs: Arguments nommés à inclure dans les données
        
    Returns:
        Chaîne de données de callback
    """
    data = {"a": action}
    
    if kwargs:
        data["d"] = kwargs
        
    # Compression du JSON en supprimant les espaces
    json_str = json.dumps(data, separators=(',', ':'))
    
    # Les données de callback Telegram sont limitées à 64 octets
    if len(json_str) > 60:  # Marge de sécurité
        logger.warning(f"Données de callback trop volumineuses: {len(json_str)} octets")
        # Tronquer les données si nécessaire
        return f"error:too_large"
        
    return json_str


def parse_json_callback_data(data: str) -> Tuple[str, Dict[str, Any]]:
    """
    Analyse une chaîne de données de callback au format JSON.
    
    Args:
        data: Chaîne de données de callback JSON
        
    Returns:
        Tuple (action, dictionnaire d'arguments)
    """
    if not data or not data.startswith("{"):
        return "", {}
        
    try:
        json_data = json.loads(data)
        action = json_data.get("a", "")
        args = json_data.get("d", {})
        return action, args
    except json.JSONDecodeError as e:
        logger.error(f"Erreur lors de l'analyse des données JSON: {e}")
        return "", {}


class CallbackDataBuilder:
    """
    Constructeur fluide pour les données de callback.
    
    Permet de construire des données de callback de manière plus lisible:
    ```
    data = CallbackDataBuilder("buy").add_param("token", "SOL").add_param("amount", 100).build()
    ```
    """
    
    def __init__(self, action: str):
        """
        Initialise le constructeur avec une action.
        
        Args:
            action: Action à exécuter
        """
        self.action = action
        self.params: List[str] = []
        
    def add_param(self, param: Any) -> "CallbackDataBuilder":
        """
        Ajoute un paramètre aux données de callback.
        
        Args:
            param: Paramètre à ajouter
            
        Returns:
            Le constructeur pour chaînage
        """
        self.params.append(str(param))
        return self
        
    def build(self) -> str:
        """
        Construit la chaîne de données de callback.
        
        Returns:
            Chaîne de données de callback
        """
        return create_callback_data(self.action, *self.params)


def execute_callback_handlers(action: str, 
                            args: List[str], 
                            update: Update, 
                            context: CallbackContext,
                            handlers: Dict[str, Callable]) -> bool:
    """
    Exécute le gestionnaire approprié pour une action de callback.
    
    Args:
        action: Action à exécuter
        args: Arguments de l'action
        update: Objet Update de Telegram
        context: Contexte du callback
        handlers: Dictionnaire des gestionnaires d'actions
        
    Returns:
        True si un gestionnaire a été trouvé et exécuté, False sinon
    """
    # Vérifier si l'action a un gestionnaire
    handler = handlers.get(action)
    
    if handler:
        try:
            # Exécuter le gestionnaire avec les arguments
            handler(update, context, *args)
            return True
        except Exception as e:
            logger.error(f"Erreur lors de l'exécution du gestionnaire pour l'action '{action}': {e}")
            return False
    else:
        logger.warning(f"Aucun gestionnaire trouvé pour l'action: {action}")
        return False


def register_callback_handlers(handlers: Dict[str, Callable]) -> Callable:
    """
    Crée un gestionnaire de callback générique qui dispatche vers les gestionnaires appropriés.
    
    Args:
        handlers: Dictionnaire des gestionnaires d'actions
        
    Returns:
        Fonction de gestion des callbacks
    """
    async def callback_handler(update: Update, context: CallbackContext) -> None:
        """Gestionnaire de callback générique."""
        if not update.callback_query:
            return
            
        # Répondre au callback query pour éviter le spinner
        await update.callback_query.answer()
        
        # Extraire l'action et les arguments
        action, args = get_callback_data(update.callback_query)
        
        if not action:
            logger.warning("Action de callback vide ou invalide")
            return
            
        # Exécuter le gestionnaire approprié
        execute_callback_handlers(action, args, update, context, handlers)
        
    return callback_handler


def create_paginated_data(prefix: str, page: int, item_id: Optional[str] = None) -> str:
    """
    Crée des données de callback pour la pagination.
    
    Args:
        prefix: Préfixe de l'action (ex: "tokens")
        page: Numéro de page
        item_id: ID optionnel de l'élément
        
    Returns:
        Chaîne de données de callback
    """
    if item_id:
        return f"{prefix}:{page}:{item_id}"
    else:
        return f"{prefix}:{page}"


def parse_paginated_data(data: str) -> Tuple[str, int, Optional[str]]:
    """
    Analyse des données de callback paginées.
    
    Args:
        data: Chaîne de données de callback
        
    Returns:
        Tuple (préfixe, page, id_élément)
    """
    parts = data.split(":")
    
    if len(parts) < 2:
        return parts[0] if parts else "", 1, None
        
    prefix = parts[0]
    
    try:
        page = int(parts[1])
    except ValueError:
        page = 1
        
    item_id = parts[2] if len(parts) > 2 else None
    
    return prefix, page, item_id


# Test si exécuté directement
if __name__ == "__main__":
    print("Module de gestion des callbacks Telegram pour GBPBot")
    print("Ce module doit être importé, pas exécuté directement.") 