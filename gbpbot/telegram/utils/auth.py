#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Module d'authentification pour le bot Telegram GBPBot.

Ce module fournit des fonctions et décorateurs pour vérifier si les utilisateurs 
sont autorisés à interagir avec le bot Telegram.
"""

import os
import time
import logging
from functools import wraps
from typing import Callable, List, Dict, Any, Optional, Union, Set
from datetime import datetime, timedelta

# Import conditionnel pour gérer à la fois les versions synchrones et asynchrones
try:
    from telegram import Update
    from telegram.ext import CallbackContext
    TELEGRAM_AVAILABLE = True
except ImportError:
    logging.getLogger(__name__).warning("Module python-telegram-bot non disponible")
    TELEGRAM_AVAILABLE = False
    # Créer des types substituts pour permettre au code de fonctionner sans dépendance
    class Update:
        pass
    class CallbackContext:
        pass

# Configuration du logger
logger = logging.getLogger("gbpbot.telegram.auth")

# Cache des utilisateurs authentifiés pour éviter les vérifications fréquentes
_auth_cache: Dict[int, float] = {}
_AUTH_CACHE_TTL = 3600  # 1 heure en secondes

class AuthManager:
    """
    Gestionnaire d'authentification pour le bot Telegram.
    
    Gère la liste des utilisateurs autorisés et vérifie les permissions.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialise le gestionnaire d'authentification.
        
        Args:
            config: Configuration contenant les paramètres d'authentification
        """
        self.config = config or {}
        self.allowed_users: Set[int] = set()
        self.admin_users: Set[int] = set()
        self.load_allowed_users()
    
    def load_allowed_users(self) -> None:
        """
        Charge la liste des utilisateurs autorisés depuis la configuration.
        """
        # Depuis la config
        if self.config:
            telegram_config = self.config.get('telegram', {})
            allowed_users_str = telegram_config.get('allowed_user_ids', "")
            admin_users_str = telegram_config.get('admin_user_ids', "")
            
            # Convertir les chaînes en listes d'entiers
            if isinstance(allowed_users_str, str):
                self.allowed_users = set(int(uid.strip()) for uid in allowed_users_str.split(',') if uid.strip().isdigit())
            elif isinstance(allowed_users_str, list):
                self.allowed_users = set(int(uid) for uid in allowed_users_str if str(uid).isdigit())
                
            if isinstance(admin_users_str, str):
                self.admin_users = set(int(uid.strip()) for uid in admin_users_str.split(',') if uid.strip().isdigit())
            elif isinstance(admin_users_str, list):
                self.admin_users = set(int(uid) for uid in admin_users_str if str(uid).isdigit())
                
        # Depuis les variables d'environnement (prioritaires)
        env_allowed = os.environ.get('TELEGRAM_ALLOWED_USERS', '')
        env_admins = os.environ.get('TELEGRAM_ADMIN_USERS', '')
        
        if env_allowed:
            self.allowed_users = set(int(uid.strip()) for uid in env_allowed.split(',') if uid.strip().isdigit())
            
        if env_admins:
            self.admin_users = set(int(uid.strip()) for uid in env_admins.split(',') if uid.strip().isdigit())
        
        # Si aucun admin n'est défini, utiliser le premier utilisateur autorisé comme admin
        if not self.admin_users and self.allowed_users:
            self.admin_users = {min(self.allowed_users)}
            
        logger.info(f"Utilisateurs autorisés: {self.allowed_users}")
        logger.info(f"Administrateurs: {self.admin_users}")
    
    def is_user_allowed(self, user_id: int) -> bool:
        """
        Vérifie si un utilisateur est autorisé à utiliser le bot.
        
        Args:
            user_id: ID Telegram de l'utilisateur
            
        Returns:
            True si l'utilisateur est autorisé, False sinon
        """
        # Vérifier le cache d'authentification
        cache_time = _auth_cache.get(user_id, 0)
        current_time = time.time()
        
        if current_time - cache_time < _AUTH_CACHE_TTL:
            return True
            
        # Vérifier l'autorisation
        is_allowed = (not self.allowed_users) or (user_id in self.allowed_users) or (user_id in self.admin_users)
        
        # Mettre à jour le cache si autorisé
        if is_allowed:
            _auth_cache[user_id] = current_time
            
        return is_allowed
    
    def is_admin(self, user_id: int) -> bool:
        """
        Vérifie si un utilisateur est administrateur du bot.
        
        Args:
            user_id: ID Telegram de l'utilisateur
            
        Returns:
            True si l'utilisateur est administrateur, False sinon
        """
        return user_id in self.admin_users
    
    def add_allowed_user(self, user_id: int, is_admin: bool = False) -> bool:
        """
        Ajoute un utilisateur à la liste des utilisateurs autorisés.
        
        Args:
            user_id: ID Telegram de l'utilisateur
            is_admin: Si True, l'utilisateur est ajouté comme administrateur
            
        Returns:
            True si l'utilisateur a été ajouté avec succès, False sinon
        """
        try:
            self.allowed_users.add(user_id)
            
            if is_admin:
                self.admin_users.add(user_id)
                
            logger.info(f"Utilisateur ajouté: {user_id} (admin: {is_admin})")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de l'ajout de l'utilisateur {user_id}: {e}")
            return False
    
    def remove_user(self, user_id: int) -> bool:
        """
        Supprime un utilisateur de la liste des utilisateurs autorisés.
        
        Args:
            user_id: ID Telegram de l'utilisateur
            
        Returns:
            True si l'utilisateur a été supprimé avec succès, False sinon
        """
        try:
            self.allowed_users.discard(user_id)
            self.admin_users.discard(user_id)
            
            # Supprimer du cache d'authentification
            if user_id in _auth_cache:
                del _auth_cache[user_id]
                
            logger.info(f"Utilisateur supprimé: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la suppression de l'utilisateur {user_id}: {e}")
            return False


# Décorators pour vérifier l'authentification
def check_user_auth(func: Callable) -> Callable:
    """
    Décorateur pour vérifier si l'utilisateur est autorisé à utiliser le bot.
    
    Args:
        func: Fonction à décorer
        
    Returns:
        Fonction décorée avec vérification d'authentification
    """
    @wraps(func)
    async def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        if not update or not update.effective_user:
            logger.warning("Mise à jour invalide ou utilisateur non disponible")
            return None
            
        user_id = update.effective_user.id
        
        # Récupérer le gestionnaire d'authentification du contexte
        auth_manager = context.bot_data.get('auth_manager')
        
        # Si aucun gestionnaire n'est disponible, créer une instance temporaire
        if not auth_manager:
            bot_config = context.bot_data.get('config', {})
            auth_manager = AuthManager(bot_config)
        
        # Vérifier l'autorisation
        if auth_manager.is_user_allowed(user_id):
            return await func(update, context, *args, **kwargs)
        
        # Enregistrer la tentative d'accès non autorisé
        username = update.effective_user.username or "Unknown"
        logger.warning(f"Tentative d'accès non autorisé: user_id={user_id}, username=@{username}")
        
        # Informer l'utilisateur
        if update.message:
            await update.message.reply_text("❌ Accès non autorisé. Contactez l'administrateur du bot.")
            
        return None
    return wrapper


def admin_required(func: Callable) -> Callable:
    """
    Décorateur pour vérifier si l'utilisateur est administrateur du bot.
    
    Args:
        func: Fonction à décorer
        
    Returns:
        Fonction décorée avec vérification des privilèges administrateur
    """
    @wraps(func)
    async def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
        if not update or not update.effective_user:
            logger.warning("Mise à jour invalide ou utilisateur non disponible")
            return None
            
        user_id = update.effective_user.id
        
        # Récupérer le gestionnaire d'authentification du contexte
        auth_manager = context.bot_data.get('auth_manager')
        
        # Si aucun gestionnaire n'est disponible, créer une instance temporaire
        if not auth_manager:
            bot_config = context.bot_data.get('config', {})
            auth_manager = AuthManager(bot_config)
        
        # Vérifier les privilèges administrateur
        if auth_manager.is_admin(user_id):
            return await func(update, context, *args, **kwargs)
        
        # Enregistrer la tentative d'accès administrateur non autorisé
        username = update.effective_user.username or "Unknown"
        logger.warning(f"Tentative d'accès administrateur non autorisé: user_id={user_id}, username=@{username}")
        
        # Informer l'utilisateur
        if update.message:
            await update.message.reply_text("⛔ Accès administrateur requis pour cette commande.")
            
        return None
    return wrapper


# Décorateur pour limiter le taux d'utilisation des commandes
def rate_limit(limit: int = 5, period: int = 60):
    """
    Décorateur pour limiter le taux d'utilisation des commandes.
    
    Args:
        limit: Nombre maximum d'appels autorisés par période
        period: Période en secondes
        
    Returns:
        Décorateur avec les paramètres spécifiés
    """
    # Dictionnaire pour stocker les timestamps des appels par utilisateur
    usage_history: Dict[int, List[float]] = {}
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
            if not update or not update.effective_user:
                return await func(update, context, *args, **kwargs)
                
            user_id = update.effective_user.id
            current_time = time.time()
            
            # Initialiser l'historique d'utilisation pour l'utilisateur
            if user_id not in usage_history:
                usage_history[user_id] = []
                
            # Nettoyer les anciens timestamps
            usage_history[user_id] = [t for t in usage_history[user_id] if current_time - t <= period]
            
            # Vérifier le taux d'utilisation
            if len(usage_history[user_id]) >= limit:
                # Calculer le temps restant
                oldest_call = min(usage_history[user_id])
                wait_time = int(period - (current_time - oldest_call))
                
                if update.message:
                    await update.message.reply_text(
                        f"⏳ Limite de taux dépassée. Veuillez réessayer dans {wait_time} secondes."
                    )
                return None
                
            # Ajouter le timestamp actuel à l'historique
            usage_history[user_id].append(current_time)
            
            # Exécuter la fonction
            return await func(update, context, *args, **kwargs)
        return wrapper
    return decorator


# Test si exécuté directement
if __name__ == "__main__":
    print("Module d'authentification Telegram pour GBPBot")
    print("Ce module doit être importé, pas exécuté directement.") 